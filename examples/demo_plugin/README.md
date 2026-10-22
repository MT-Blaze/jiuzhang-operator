# 示例题库（org.jiuzhang.demo-bank）

九章算子的种子题库插件：随包内置 5 道高中数学示例题，让新用户打开工作台就有事可做。

- 类型：`importer`（兼带 `question.card` 渲染）
- 插槽：`question.card`
- 能力：`question.import`、`question.render`
- 权限：`questions:read`
- 协议：`jzo-plugin/1`
- 题目数据：`seed/questions.json`，逐题通过 `schemas/question.json`（Question 1.0）校验

插件运行在无 `allow-same-origin` 的沙箱 iframe 中：只接收宿主投递的题目快照，
返回经过转义的 HTML 片段；不联网、不读宿主存储、不接触宿主 DOM。
公式按 Markdown + LaTeX 源码显示（`render_mode: "math-source"`），排版由后续插件接管。

直接打开 `dist/index.html`（或经宿主 `/plugin-assets/` 访问）时，页面会自渲染
5 道示例题的清单预览，方便不装任何宿主也能看到内容。

## 重新打包

```
python examples/build_demo_plugin.py
```

脚本会重新校验 `seed/questions.json`、把题目内联进 `dist/plugin.js` 的构建副本，
并生成 `examples/demo_plugin.zip`（底座首次运行时静默安装的就是这个包）。
