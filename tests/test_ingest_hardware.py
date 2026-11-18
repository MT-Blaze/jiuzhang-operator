"""只读显存探针（四合一卡 §3）：nvidia-smi 优先、WMI 兜底、读不到如实报。

运行：``.venv/Scripts/python.exe -m unittest tests.test_ingest_hardware``
"""

from __future__ import annotations

import unittest
from unittest import mock

from app.core.ingest import hardware


class ProbeTest(unittest.TestCase):
    def test_nvidia_smi_parsed_to_gb(self) -> None:
        with mock.patch.object(hardware, "_run_text",
                               return_value=(0, "测试卡, 16384\n")):
            info = hardware.probe()
        self.assertEqual(info["vram_gb"], 16.0)
        self.assertEqual(info["vram_label"], "16.0G")
        self.assertEqual(info["vram_source"], "nvidia-smi")
        self.assertEqual(info["gpu_name"], "测试卡")

    def test_multi_gpu_takes_the_largest(self) -> None:
        with mock.patch.object(hardware, "_run_text",
                               return_value=(0, "小卡, 6144\n大卡, 24576\n")):
            info = hardware.probe()
        self.assertEqual(info["vram_gb"], 24.0)
        self.assertEqual(info["gpu_name"], "大卡")

    def test_wmi_fallback_discloses_cap(self) -> None:
        with mock.patch.object(hardware, "_nvidia", return_value=None), \
                mock.patch.object(hardware, "_wmi", return_value=(4.0, "")):
            info = hardware.probe()
        self.assertEqual(info["vram_gb"], 4.0)
        self.assertEqual(info["vram_source"], "wmi")
        self.assertIn("低估", info["detail"])

    def test_no_probe_reports_unknown_not_a_guess(self) -> None:
        with mock.patch.object(hardware, "_nvidia", return_value=None), \
                mock.patch.object(hardware, "_wmi", return_value=None):
            info = hardware.probe()
        self.assertEqual(info["vram_gb"], 0.0)
        self.assertEqual(info["vram_label"], "读不到")
        self.assertIn("按不支持处理", info["detail"])

    def test_probe_is_not_cached(self) -> None:
        with mock.patch.object(hardware, "_nvidia",
                               side_effect=[(8.0, "卡"), (48.0, "换机卡")]) as probe:
            first = hardware.probe()["vram_gb"]
            second = hardware.probe()["vram_gb"]
        self.assertEqual((first, second), (8.0, 48.0))
        self.assertEqual(probe.call_count, 2)

    def test_nvidia_failure_falls_through_to_wmi(self) -> None:
        with mock.patch.object(hardware, "_run_text",
                               side_effect=[(1, ""), (0, "8589934592\n")]), \
                mock.patch.object(hardware.sys, "platform", "win32"):
            info = hardware.probe()
        self.assertEqual(info["vram_source"], "wmi")
        self.assertEqual(info["vram_gb"], 8.0)


class TierTest(unittest.TestCase):
    TIERS = [{"min_gb": 6, "fits": "甲"}, {"min_gb": 8, "fits": "乙"},
             {"min_gb": 16, "fits": "丙"}, {"min_gb": 48, "fits": "丁"}]

    def test_boundaries_pick_the_highest_fitting_tier(self) -> None:
        for vram, fits in ((5.9, None), (6.0, "甲"), (7.9, "甲"), (8.0, "乙"),
                           (16.0, "丙"), (47.9, "丙"), (48.0, "丁"), (96.0, "丁")):
            tier = hardware.tier_for(vram, self.TIERS)
            self.assertEqual(tier["fits"] if tier else None, fits,
                             "显存 %s 落档错" % vram)

    def test_empty_table_returns_none(self) -> None:
        self.assertIsNone(hardware.tier_for(16.0, []))


if __name__ == "__main__":
    unittest.main()