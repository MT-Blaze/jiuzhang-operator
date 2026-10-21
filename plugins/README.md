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
- 底座 `v0.1.0` 尚未实现插件宿主，本目录仅作占位；插件不会在未声明权限的情况下被加载。
