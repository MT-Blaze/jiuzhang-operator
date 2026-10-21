# plugins/

每个插件独占一个目录，目录名必须等于其 `plugin.json` 中的 `id`。

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
