# -*- coding: utf-8 -*-
"""本地 YOLO 模型按需下载、多级降级与打包隔离。

运行：``.venv/Scripts/python.exe -m unittest tests.test_layout_models``
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from app.core.layout import layout_model_store as store
from app.core.layout import layout_router, layout_yolo, layout_yolo_runtime
from app.core import ingest_route
from tools import build_plugin as builder

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "plugins" / "org.jiuzhang.editor"


def write_config(plugin_dir: Path, *, full_min: int = 16, quant_min: int = 8) -> None:
    document = {
        "schema_version": "1.0",
        "plugin_id": "org.jiuzhang.editor",
        "models_dir": "models",
        "models": {
            "full": {
                "label": "满血版", "version": "v1.0", "filename": "full_v1.0.onnx",
                "display_size": "约 16B", "size_bytes": full_min, "min_bytes": full_min,
                "urls": ["https://mirror.invalid/full_v1.0.onnx"],
            },
            "quantized": {
                "label": "量化版", "version": "v1.0", "filename": "quant_v1.0.onnx",
                "display_size": "约 8B", "size_bytes": quant_min, "min_bytes": quant_min,
                "urls": ["https://mirror.invalid/quant_v1.0.onnx"],
            },
        },
    }
    (plugin_dir / "model_config.json").write_text(
        json.dumps(document, ensure_ascii=False), encoding="utf-8")


class ModelStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.plugin = self.root / "org.jiuzhang.editor"
        self.plugin.mkdir()
        write_config(self.plugin)
        env = mock.patch.dict(os.environ, {"JZO_PLUGINS_DIR": str(self.root)})
        env.start()
        self.addCleanup(env.stop)
        self.addCleanup(self.temp.cleanup)
        store._DOWNLOADS.clear()
        store._THREADS.clear()

    def test_01_real_config_has_mirrors_and_versions(self) -> None:
        document = json.loads((PLUGIN_DIR / "model_config.json").read_text(encoding="utf-8"))
        for kind in ("full", "quantized"):
            entry = document["models"][kind]
            self.assertEqual(entry["version"], "v1.0")
            self.assertGreater(entry["min_bytes"], 0)
            joined = " ".join(entry["urls"])
            self.assertIn("gitee.com", joined)
            self.assertIn("gh-proxy.com", joined)

    def test_02_undersized_file_is_not_loadable(self) -> None:
        target = store.model_path("full")
        target.write_bytes(b"x" * 4)
        self.assertFalse(store.present("full"))
        self.assertFalse(store.status()["models"]["full"]["present"])

    def test_03_download_uses_tmp_then_renames(self) -> None:
        def fake_stream(kind, url, part):
            part.write_bytes(b"x" * 16)
            return 16, 16

        with mock.patch.object(store, "_stream", side_effect=fake_stream):
            store._download("full", store._entry("full"), store.model_path("full"))
        target = store.model_path("full")
        self.assertTrue(target.is_file())
        self.assertFalse(target.with_name(target.name + store.PART_SUFFIX).exists())
        self.assertTrue(store.present("full"))
        self.assertEqual(store._DOWNLOADS["full"]["state"], "done")

    def test_04_short_download_is_discarded(self) -> None:
        def short_stream(kind, url, part):
            part.write_bytes(b"x" * 4)
            return 4, 4

        with mock.patch.object(store, "_stream", side_effect=short_stream):
            store._download("full", store._entry("full"), store.model_path("full"))
        target = store.model_path("full")
        self.assertFalse(target.exists())
        self.assertFalse(target.with_name(target.name + store.PART_SUFFIX).exists())
        self.assertEqual(store._DOWNLOADS["full"]["state"], "error")
        self.assertIn("文件过小", store._DOWNLOADS["full"]["message"])

    def test_05_truncated_download_is_discarded(self) -> None:
        def truncated(kind, url, part):
            part.write_bytes(b"x" * 16)
            return 16, 20

        with mock.patch.object(store, "_stream", side_effect=truncated):
            store._download("full", store._entry("full"), store.model_path("full"))
        self.assertFalse(store.model_path("full").exists())
        self.assertIn("下载不完整", store._DOWNLOADS["full"]["message"])

    def test_06_corrupt_file_is_replaced_before_download(self) -> None:
        target = store.model_path("quantized")
        target.write_bytes(b"bad")
        with mock.patch.object(store, "_download", lambda *args: None):
            store.start_download("quantized")
        self.assertFalse(target.exists())


class HardwareTest(unittest.TestCase):
    def _fake_ort(self, providers: list[str]) -> types.ModuleType:
        module = types.ModuleType("onnxruntime")
        module.get_available_providers = lambda: list(providers)
        return module

    def test_01_cuda_and_directml_mapping(self) -> None:
        for provider, gpu, label in (
            ("CUDAExecutionProvider", "cuda", "CUDA显卡加速"),
            ("DmlExecutionProvider", "directml", "DirectML显卡加速"),
        ):
            with mock.patch.dict(sys.modules, {"onnxruntime": self._fake_ort([provider])}):
                info = store.hardware()
            self.assertTrue(info["ready"])
            self.assertEqual(info["gpu"], gpu)
            self.assertEqual(info["hardware_label"], label)

    def test_02_cpu_only(self) -> None:
        with mock.patch.dict(sys.modules, {"onnxruntime": self._fake_ort(["CPUExecutionProvider"])}):
            info = store.hardware()
        self.assertEqual(info["gpu"], "")
        self.assertEqual(info["hardware_label"], "CPU运行")

    def test_03_missing_runtime_is_not_ready(self) -> None:
        with mock.patch.dict(sys.modules, {"onnxruntime": None}):
            info = store.hardware()
        self.assertFalse(info["ready"])


class YoloFallbackTest(unittest.TestCase):
    def _run(self, hardware: dict, present: dict, load_side_effect, page=True):
        describe = lambda kind: {"kind": kind, "label": "满血版" if kind == "full" else "量化版",
                                 "version": "v1.0", "display_size": ""}
        with mock.patch.object(store, "hardware", return_value=hardware), \
                mock.patch.object(store, "present", side_effect=lambda kind: present.get(kind, False)), \
                mock.patch.object(store, "model_path", return_value=Path("model.onnx")), \
                mock.patch.object(store, "describe", side_effect=describe), \
                mock.patch.object(layout_yolo_runtime, "load_session",
                                  side_effect=load_side_effect), \
                mock.patch.object(layout_yolo, "_page_image", return_value=b"png"), \
                mock.patch.object(layout_yolo_runtime, "infer_regions",
                                  return_value=[{"no": 1, "x": 1, "y": 1, "w": 10, "h": 10}]):
            return layout_yolo.detect({"pages": [
                {"page": 1, "width": 100, "height": 100, "name": "p.png"}]})

    def test_01_full_gpu_success_line(self) -> None:
        result = self._run(
            {"ready": True, "gpu": "cuda", "hardware_label": "CUDA显卡加速"},
            {"full": True, "quantized": True}, lambda path, providers: "session")
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"][-1]["text"],
                         "[INFO] 版面分析：已启用本地 YOLO（满血版 / CUDA显卡加速）")
        self.assertEqual(result["model"]["provider"], "CUDAExecutionProvider")

    def test_02_oom_degrades_to_quantized_gpu(self) -> None:
        errors = [layout_yolo_runtime.RuntimeErrorYolo("CUDA_ERROR_OUT_OF_MEMORY: cudaMalloc failed")]
        result = self._run(
            {"ready": True, "gpu": "directml", "hardware_label": "DirectML显卡加速"},
            {"full": True, "quantized": True},
            lambda path, providers: (_ for _ in ()).throw(errors.pop(0)) if errors else "session")
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"][0]["text"], layout_yolo.OOM_WARNING)
        self.assertEqual(result["status"][1]["text"],
                         "[INFO] 版面分析：显存不足，已降级为本地 YOLO（量化版 / DirectML显卡加速）")

    def test_03_oom_then_cpu_line(self) -> None:
        errors = [layout_yolo_runtime.RuntimeErrorYolo("out of memory"),
                  layout_yolo_runtime.RuntimeErrorYolo("DML provider failed")]

        def load(path, providers):
            if errors:
                raise errors.pop(0)
            return "session"

        result = self._run(
            {"ready": True, "gpu": "directml", "hardware_label": "DirectML显卡加速"},
            {"full": True, "quantized": True}, load)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"][-1]["text"],
                         "[INFO] 版面分析：显存不足，已降级为本地 YOLO（量化版 / CPU运行）")
        self.assertEqual(result["model"]["provider"], "CPUExecutionProvider")

    def test_04_no_gpu_uses_quantized_cpu(self) -> None:
        result = self._run(
            {"ready": True, "gpu": "", "hardware_label": "CPU运行"},
            {"quantized": True}, lambda path, providers: "session")
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"][-1]["text"],
                         "[INFO] 版面分析：已启用本地 YOLO（量化版 / CPU运行）")

    def test_05_all_local_fails_reports_cloud(self) -> None:
        def load(path, providers):
            raise layout_yolo_runtime.RuntimeErrorYolo("not enough memory")

        result = self._run(
            {"ready": True, "gpu": "cuda", "hardware_label": "CUDA显卡加速"},
            {"full": True, "quantized": True}, load)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"][-1]["text"], layout_yolo.CLOUD_WARNING)

    def test_06_missing_runtime_fails_without_crash(self) -> None:
        result = self._run(
            {"ready": False, "gpu": "", "hardware_label": "CPU运行",
             "detail": "未安装 onnxruntime"}, {}, lambda path, providers: "session")
        self.assertFalse(result["ok"])
        self.assertIn("onnxruntime", result["detail"])
        self.assertEqual(result["status"][-1]["text"], layout_yolo.CLOUD_WARNING)

    def test_07_memoryerror_counts_as_oom(self) -> None:
        self.assertTrue(layout_yolo._is_oom(MemoryError("boom")))
        wrapped = RuntimeError("load failed")
        wrapped.__cause__ = MemoryError("vram")
        self.assertTrue(layout_yolo._is_oom(wrapped))
        self.assertFalse(layout_yolo._is_oom(ValueError("bad shape")))


class RouteStatusTest(unittest.TestCase):
    def test_01_router_collects_status_from_failed_attempts(self) -> None:
        def yolo(_request):
            return {"ok": False, "detail": "no model",
                    "status": [{"level": "error", "text": layout_yolo.OOM_WARNING}]}

        def cloud(_request):
            return {"ok": True, "pages": {1: [{"no": 1}]}, "columns": {1: 1}, "detail": ""}

        result = asyncio.run(layout_router.run(
            "a.pdf", b"", [{"page": 1}], "yolo",
            providers={"python": lambda _r: {"ok": False}, "yolo": yolo, "cloud": cloud}))
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"][0]["text"], layout_yolo.OOM_WARNING)

    def test_02_attach_layout_writes_status_and_model(self) -> None:
        route = {}
        ingest_route.attach_layout(route, {
            "status": [{"level": "info", "text": "[INFO] x"}],
            "model": {"kind": "quantized", "version": "v1.0"},
        })
        self.assertEqual(route["layout_status"][0]["text"], "[INFO] x")
        self.assertEqual(route["layout_model"]["kind"], "quantized")


class PackagingIsolationTest(unittest.TestCase):
    def test_01_payload_skips_models_and_model_suffixes(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            plugin = Path(name)
            (plugin / "dist").mkdir()
            (plugin / "models").mkdir()
            (plugin / "dist" / "app.js").write_text("x", encoding="utf-8")
            (plugin / "dist" / "weights.onnx").write_bytes(b"x")
            (plugin / "models" / "full_v1.0.onnx").write_bytes(b"x")
            names = [relative.as_posix() for relative, _ in builder._iter_payload(plugin)]
        self.assertEqual(names, ["dist/app.js"])

    def test_02_editor_zip_is_light_and_has_no_model(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            target = builder.build_plugin(PLUGIN_DIR, Path(name))
            self.assertLess(target.stat().st_size, builder.MAX_PACKAGE_BYTES)
            with zipfile.ZipFile(target) as archive:
                names = archive.namelist()
        self.assertFalse([item for item in names if item.endswith(".onnx")])
        self.assertFalse([item for item in names if "/models/" in item])

    def test_03_oversized_package_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as name, \
                mock.patch.object(builder, "MAX_PACKAGE_BYTES", 1):
            with self.assertRaises(builder.BuildError):
                builder.build_plugin(PLUGIN_DIR, Path(name))
            self.assertFalse((Path(name) / "org.jiuzhang.editor.zip").exists())


if __name__ == "__main__":
    unittest.main()
