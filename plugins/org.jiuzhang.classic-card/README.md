# 经典题卡（org.jiuzhang.classic-card）

九章算子的首个 `question.card` 渲染插件。

- 类型：`renderer`
- 插槽：`question.card`
- 能力：`question.render`
- 权限：`questions:read`、`assets:read`
- 协议：`jzo-plugin/1`

插件运行在无 `allow-same-origin` 的沙箱 iframe 中，只接收宿主投递的题目快照，
返回经过 HTML 转义的片段；不联网、不读存储、不接触宿主 DOM。

公式当前按 Markdown + LaTeX 源码显示（`render_mode: "math-source"`），
公式排版将由后续插件接管。
