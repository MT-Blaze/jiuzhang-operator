# 录题工作台（org.jiuzhang.editor）

九章算子的官方录题插件：拖入试卷 → 立批次 → 自动切题 → 逐题审核 → 存库。

本插件把「版面切框」与「正文识别」拆成两个彼此独立、可分别选择的引擎。
文件收集筐上方并排放着两个下拉框：

| 位置 | 下拉框 | 管什么 | 选项 |
| --- | --- | --- | --- |
| 左 | **版面引擎** | 题块画在哪、按什么顺序编号 | 自动 / YOLO / 云端 |
| 右 | **识别引擎** | 框里的字怎么变成题干与答案 | 自动 / 全量OCR / MinerU |

每个选项都带原生 HTML `title`：鼠标悬停会显示一行极淡的说明。
选择只对**下一次【开始解析】**生效，不会重跑已经立起来的批次。

---

## 一、版面引擎

版面引擎只负责「切框」，从不编造正文；正文始终由识别引擎或本地文本层负责。

无论选哪一个，**纯 Python 探路永远排在第一位**：先读 PDF 自带文本层，
按行坐标做标准单栏 / 双栏重排。文本层缺失、加密、或读不出足够行时才进入下一步。

| 选择 | 瀑布顺序 | 说明 |
| --- | --- | --- |
| **自动** | Python → YOLO → 云端 | 本地文本层失败先试本机 YOLO，仍失败才把页图交云端视觉模型。 |
| **YOLO** | Python → **强制 YOLO** → 云端 | 本地文本层失败后不再犹豫，直接交本机 YOLO；YOLO 不可用/超时再交云端。 |
| **云端** | Python → **跳过 YOLO** → 云端 | 本地文本层失败后直接交云端视觉模型，不经过本机 YOLO。 |

补充规则：

- 三档都不会因为「选了云端」就跳过 Python；文本层能读出标准版面时一次网络请求都不发。
- YOLO 只允许回环地址（`127.0.0.1` / `localhost` / `[::1]`），避免把整卷页图发到未知主机。
- 云端版面把每页图片按 0–1000 归一化坐标返回，后端再换算成页面像素；最多处理 20 页。
- 全部引擎都失败时，批次仍保留页图与绿框；左栏绿框只读，切题改动统一走顶部【重新切题】悬浮画板。

### 本地 YOLO 模型（按需下载）

模型**不进插件包**：插件目录只有一份 `model_config.json`，老师第一次选【YOLO】
且本机没有模型时，界面弹窗二选一，点哪一个才下载哪一个。

| 版本 | 用途 | 下载源 |
| --- | --- | --- |
| **满血版** | 显卡加速下追求精度；加载失败（显存不足）自动降级 | `gh-proxy.com` / Gitee 镜像 / `hf-mirror.com` |
| **轻量量化版** | 网络慢或配置低时使用；显卡失败后由 CPU 兜底 | `gh-proxy.com` / Gitee 镜像 |

- 下载先写 `models/<文件名>.tmp`，大小与完整性校验通过后才原子改名为 `.onnx`；
  半截文件直接丢弃，绝不进入加载环节。
- 模型只落在当前工作区的 `plugins/org.jiuzhang.editor/models/`，打包脚本按目录名
  与后缀双重排除，插件 zip 始终小于 10MB。
- 加载顺序：满血 + GPU → 量化 + GPU → 量化 + CPU → 云端版面 API；每一级都把
  「版本 / 硬件」写进批次路由，宿主播报到【运行日志】。
- 本地推理需要可选的 `onnxruntime`：Windows 通用显卡加速装 `onnxruntime-directml`，
  NVIDIA 装 `onnxruntime-gpu`；Python 3.14 暂无官方轮子，未安装时自动降云端。
- 旧的 HTTP 服务变量 `JZO_YOLO_LAYOUT_URL` 已退役，仅保留在文档里供历史部署对照；
  当前版本不再向任何本机 HTTP 服务转发页图。

## 二、识别引擎

识别引擎只负责「填字」，题图始终以原卷为准，识别失败也不会丢题。

| 选择 | 瀑布顺序 | 说明 |
| --- | --- | --- |
| **自动** | 本地提取 → AI 局部/全量 → MinerU 兜底 | 先本地提取；坏题交 AI 修补；坏题率达到 30% 转整批全量 OCR；最后 MinerU 兜底。 |
| **全量OCR** | 本地提取 → **整批 AI** → MinerU 兜底 | 不看坏题率，整批单题截图并发交视觉模型（默认 5 路），失败再交 MinerU。 |
| **MinerU** | 本地提取 → **逐题 MinerU** | 本地切好单题截图后逐题发送，单题最长等待 900 秒；失败的那道题保留本地切图。 |

坏题四特征：连续空选项、掉变量句式、内联小图多但无公式、长文无符号。
坏题率低于 30% 只补坏题；达到或越过 30% 自动改走整批全量 OCR。

### 识别账号配置

识别引擎的云端能力统一走【API 配置】里指派的任务账号：

- **AI 识别**：指派「视觉识别(OCR)」任务；未指派时 AI 档会如实报错并保留本地切图。
- **MinerU**：在账号池里配置 MinerU 地址与 Key；未配置时 MinerU 档会提示去【API 配置】指派。

## 三、请求契约

插件经宿主转发 `ingest.files`，宿主最终调用：

```http
POST /api/ingest/files
```

```json
{
  "files": [
    { "name": "期中卷.pdf", "data_url": "data:application/pdf;base64,..." }
  ],
  "layout_engine": "auto",
  "recognize_engine": "auto"
}
```

- `layout_engine`：`auto` / `yolo` / `cloud`
- `recognize_engine`：`auto` / `full_ocr` / `mineru`
- 旧客户端仍可只发 `channel`（`auto` / `local_ai` / `full_ocr` / `mineru`），
  后端会映射到新的识别引擎并忽略未知值。

响应先返回已立起的批次；页图渲染、切题与识别在后台任务里继续，
批次路由上的 `note` 会逐条写进插件底部日志。

## 四、后端模块边界

| 模块 | 职责 | 行数上限 |
| --- | --- | --- |
| `app/core/layout/layout_router.py` | 只按瀑布顺序分发 | < 100 |
| `app/core/layout/layout_python.py` | 本地文本层探路、单/双栏重排 | < 300 |
| `app/core/layout/layout_yolo.py` | 本机 ONNX 四级瀑布与状态播报 | < 400 |
| `app/core/layout/layout_cloud.py` | 云端视觉模型兜底 | < 200 |
| `app/core/recognize/recognize_router.py` | 只按瀑布顺序分发 | < 100 |
| `app/core/recognize/recognize_local.py` | 纯本地文本提取 | < 300 |
| `app/core/recognize/recognize_ai.py` | 局部或全量大模型识别 | < 200 |
| `app/core/recognize/recognize_mineru.py` | MinerU 逐题云端识别 | < 200 |

调度层不写算法，算法层不决定降级顺序；两层都通过普通 JSON 字典传参，
新增引擎只需实现 `detect` / `run` 并注册进对应路由即可。

## 五、可下架说明

双引擎选择器是一整块独立 UI：删掉 `dist/index.html` 里的 `.ed-basket-engines`
及 `dist/layout.css` 中对应规则即可下架；后端缺失这两个字段时默认按
`auto` 处理，不影响老批次与老客户端。

## 六、测试

```bash
.venv/Scripts/python.exe -m unittest tests.test_layout_router
.venv/Scripts/python.exe -m unittest tests.test_recognize_router
.venv/Scripts/python.exe -m unittest tests.test_ingest_triage
```

全量回归：`tools/run_all_tests.py`。

## 许可证

Apache-2.0，见同目录 `LICENSE`。
