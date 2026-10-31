# plugins/

每个插件独占一个目录，目录名必须等于其 `plugin.json` 中的 `id`。分发格式是**标准 zip 包**（无 `.jzo` 之类专属后缀，任何压缩软件都能打开）：用户拿到 zip 后解压，把整个目录放进 `plugins/` 即完成安装，无需注册、无需联网、无需重启（PLUGIN_SPEC §1.2）。

想在国内可达的地方挂一份「有哪些插件」的清单，格式是 `plugins.json` 索引（PLUGIN_SPEC §1.3）：把它放到任意 http(s) 地址，用户在底座的 `/plugins` 页粘贴该地址即可拉取列表。底座**不写死任何源地址**，也不会替你下载或安装任何东西——它只读一份 JSON，剩下的下载与解压仍由用户亲手做。

```text
plugins/
└── com.example.classic-card/
    ├── plugin.json
    ├── LICENSE
    ├── README.md
    └── dist/
        ├── index.html
        ├── plugin.js
        └── plugin.css
```

- 接入契约：[../docs/PLUGIN_SPEC.md](../docs/PLUGIN_SPEC.md)（**从零上手直接看 §2.3**：五步流程、`plugin.json` 字段全表、消息协议、可照抄的 `plugin.js` 骨架）
- 题目数据结构：[../schemas/question.json](../schemas/question.json)
- 最小样板：[../examples/template-plugin/](../examples/template-plugin/)——整个目录复制出来，改目录名、`plugin.json` 的 `id` 与 `plugin.js` 里的 `PLUGIN_ID`，压成 zip 即可安装。
- 清单硬要求：`schema_version` 固定 `"1.0"`；`entry.frontend` 必须指向 `dist/` 下的真实文件；插件根目录必须有 `LICENSE`（Apache-2.0 全文）；`backend` 字段出现即拒装。
- 底座 `v0.5.4` 已实现清单发现与校验、沙箱资源分发与隔离；题卡渲染宿主将在后续版本接回（PLUGIN_SPEC §2.3.5）。
- `dist/` 是插件的运行时载荷，需随仓库提交（本项目无构建链）；请勿在其中放入符号链接、可执行文件、数据库或密钥。
- 插件不得要求注册、卡密、试用到期或任何联网回连校验，也不得加水印与数量限制（PLUGIN_SPEC §1.1）。缺密钥、断网、超时一律显式降级并给出可读提示。
