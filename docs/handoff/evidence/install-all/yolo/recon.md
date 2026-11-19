# 座1 yolo（DocLayout-YOLO 满血版）侦查

## 结论：已接线＋权重已在位，剩 UI 真点安装实证＋版面冒烟

- 权重实物：`jiuzhang-plugins/src/org.jiuzhang.editor/models/doclayout_yolo_full_v1.0.onnx`
  - size = 75,324,598 bytes（与 model_config.toml [full].size_bytes 逐字一致）
  - sha256 = `fece9af02f618b603ff7921ccec6861d13e7e1f9830e091dfb7e8ad9311e5b21`
  - 远端核验：hf-mirror `wybxc/DocLayout-YOLO-DocStructBench-onnx` 的
    `doclayout_yolo_docstructbench_imgsz1024.onnx` lfs.oid 与本地 sha256 **逐字一致**，size 同。
- license：Apache-2.0（model_config.toml [full].license）。
- 下载源（model_config.toml [full].urls，国内镜像，禁 GitHub 直连）：
  1. gh-proxy.com 代理 MT-Blaze/jiuzhang-models release v1.0
  2. gitee.com jiuzhang-operator/jiuzhang-models release v1.0
  3. hf-mirror.com wybxc/DocLayout-YOLO-DocStructBench-onnx
- 接线现状：`app/core/ingest/layout/yolo.py`＋`model_store.py`＋`yolo_runtime.py` 已全接线；
  catalog `yolo` 条目 rule=weight_present store=full action=download 已正确，**无需改 catalog**。
- 显存：YOLO 走 onnxruntime CPU/GPU 版面检测，非 VLM，无 6G 显存门槛问题。

## 偏离登记（择一合规路径）

- 权重落点是**插件目录 models/**（既有接线如此），不是 engines/<store>/。
  这是 yolo 座既有 wiring 的固有路径，沿用不改道；回单注明此偏离。
- 既有 model_store 用 **size 闸**（min_bytes=70000000）非 sha256 闸；本侦查已补 sha256 逐字核验留证。

## 待办

- 隔离副本 UI 真点「下载」发起 75MB 真下载（副本无权重）→ sha256 校验 → 版面冒烟 3–5 页。
- 定向 unittest（test_layout_models 等）＋快门禁＋三查 0 → commit。