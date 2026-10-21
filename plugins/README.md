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

- 接入契约：[../PLUGIN_SPEC.md](../PLUGIN_SPEC.md)
- 题目数据结构：[../schemas/question.json](../schemas/question.json)
- 底座 `v0.2.0` 已实现前端渲染插件宿主：清单校验、沙箱加载、消息封包、净化与故障兜底。插件不会在未声明权限的情况下被加载。
- `dist/` 是插件的运行时载荷，需随仓库提交（本项目无构建链）；请勿在其中放入符号链接、可执行文件、数据库或密钥。
- 插件不得要求注册、卡密、试用到期或任何联网回连校验，也不得加水印与数量限制（PLUGIN_SPEC §1.1）。缺密钥、断网、超时一律显式降级并给出可读提示。
