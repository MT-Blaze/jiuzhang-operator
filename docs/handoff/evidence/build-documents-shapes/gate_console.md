── [命名规约 R00]
[PASS] check-naming: .qoder 资产命名合规（R00）
   ok: 命名规约 R00
── [插件三查与依赖方向]
[PASS] 插件侧三查：fetch( 命中 0
[PASS] 插件侧三查：parent.document 命中 0
[PASS] 插件侧三查：localStorage 命中 0
[PASS] 插件源码内无 Python 文件
[INFO] 宿主侧 static/js 中带 fetch( 的文件数：17（出网必须由用户当场点击发起，见 docs/AGENTS.md §2）
check-plugin-boundary: PASS（三查 0 命中、插件零 Python 依赖）
   ok: 插件三查与依赖方向
── [插件包结构红线]
check-plugin-package: PASS（官方插件 5 支，结构红线全部通过）
   ok: 插件包结构红线
── [索引全等与 Schema]
check-plugin-index-parity: PASS（两份索引语义一致、条目版本一致、示例题过契约校验）
   ok: 索引全等与 Schema
── [静态红线审计]
[WARN] host-innerhtml static\index.html:18  box.innerHTML = '<div style="max-width:34em"><p style="margin:0 0 12px;font-size:20px;font-weight:700">请使用现代浏览器</p><p style="margin:0;font-size:15px">九章算子需要 Chr
[WARN] sql-fstring tests\test_bank_api.py:1228  counts = {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables}
[WARN] sql-fstring tests\test_bank_multiversion.py:138  counts = {table: con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
[WARN] sql-fstring tests\test_bank_multiversion.py:225  self.assertEqual(count, con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0],
[WARN] sql-fstring tests\test_bank_multiversion.py:362  before = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
[WARN] sql-fstring tests\test_bank_multiversion.py:369  after = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
[WARN] absolute-windows-path tests\test_workspace_restart.py:117  pid=4321, root=Path("C:\\jzo"), python_exe="C:\\jzo\\.venv\\Scripts\\python.exe",
[WARN] absolute-windows-path tests\test_workspace_restart.py:143  pid=1, root=Path("C:\\jzo"), python_exe="python", host="127.0.0.1", port="8123")  # type: ignore[arg-type]
[WARN] sql-fstring tools\build_bank_schema.py:64  con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
[WARN] sql-fstring tools\build_bank_schema.py:98  for c in con.execute(f'PRAGMA table_info("{name}")')
[WARN] sql-fstring tools\build_bank_schema.py:100  fks = [dict(f) for f in con.execute(f'PRAGMA foreign_key_list("{name}")')]
[WARN] sql-fstring tools\build_bank_schema.py:101  counts = con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
[INFO] interval-without-clear static\js\app.js:0  setInterval×1, clearInterval×0（常驻轮询需人工确认）
[INFO] interval-without-clear static\js\version.js:0  setInterval×1, clearInterval×0（常驻轮询需人工确认）
[INFO] interval-without-clear static\js\ws_ctxmenu.js:0  setInterval×1, clearInterval×0（常驻轮询需人工确认）
[WARN] host-innerhtml examples\template-plugin\dist\ui_render.js:46  if (row.html) card.innerHTML = escapeHtml(row.text ? row.text + " " : "") + row.html;
[WARN] sql-fstring app\bank_engine\migrate_legacy.py:220  conn.execute(f"ALTER TABLE {table} ADD COLUMN stage TEXT")
[WARN] sql-fstring app\bank_engine\migrate_legacy.py:234  conn.execute(f"ALTER TABLE {table} DROP COLUMN grade_id")
[WARN] sql-fstring app\core\db.py:178  con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
[WARN] sql-fstring app\core\bank\questions.py:265  con.execute(f"SELECT COUNT(*) FROM questions {clause}", params).fetchone()[0]
[WARN] sql-fstring app\core\bank\questions.py:324  cursor = con.execute(f"UPDATE questions SET {assignments} WHERE id = ?", [*values, question_id])
[WARN] sql-fstring app\core\content\latex_norm.py:141  con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
[WARN] sql-fstring app\core\pending\db.py:391  have = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
[WARN] sql-fstring app\core\pending\db.py:395  con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
[WARN] sql-fstring app\core\pending\db.py:448  con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
[WARN] sql-fstring app\core\pending\db.py:577  have = {str(row[1]) for row in con.execute(f"PRAGMA table_info({table})")}
[WARN] sql-fstring app\core\pending\db.py:580  con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
[WARN] sql-fstring app\core\bank\engine\dedupe.py:422  con.execute(f"DELETE FROM questions WHERE id IN ({copy_marks})", copies)
[WARN] sql-fstring app\core\bank\engine\fts.py:114  connection.execute(f"DELETE FROM {TABLE}")
[WARN] sql-fstring app\core\bank\engine\fts.py:123  cursor = connection.execute(f"SELECT id, stem FROM {source_table}")
[WARN] sql-fstring app\core\bank\engine\fts.py:151  row = connection.execute(f"SELECT count(*) FROM {TABLE}").fetchone()
[WARN] sql-fstring app\core\bank\engine\query.py:122  con.execute(f"DELETE FROM {bank_fts.TABLE}")
[WARN] sql-fstring app\core\bank\engine\query.py:263  total = int(con.execute(f"SELECT COUNT(*) FROM questions q {clause}", params).fetchone()[0])
[WARN] sql-fstring app\core\bank\engine\schema.py:362  con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
[WARN] sql-fstring app\core\bank\engine\schema.py:462  after = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
[WARN] sql-fstring app\core\bank\engine\schema.py:539  snapshot = {table: con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
[WARN] sql-fstring app\core\bank\engine\schema.py:589  con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
[WARN] sql-fstring app\core\bank\engine\write.py:415  con.execute(f'DELETE FROM "{table}"')

检查完成：ERROR 0 · WARN 35 · INFO 3
   ok: 静态红线审计
── [版本单源与 bat 编码]
.............................
----------------------------------------------------------------------
Ran 29 tests in 0.032s

OK
   ok: 版本单源与 bat 编码
── [体积预警 451–550 行（只看不拦）]
[WARN] 接近上限：app/api/bank_engine.py=463 行（451–550 区间，须排队拆）
[WARN] 接近上限：app/api/pending.py=485 行（451–550 区间，须排队拆）
[WARN] 接近上限：app/api/plugins.py=482 行（451–550 区间，须排队拆）
[WARN] 接近上限：app/api/workspaces.py=497 行（451–550 区间，须排队拆）
[WARN] 接近上限：app/bank_engine/dao_console.py=499 行（451–550 区间，须排队拆）
[WARN] 接近上限：app/bank_engine/service.py=482 行（451–550 区间，须排队拆）
[WARN] 接近上限：app/core/ai/platform/center.py=459 行（451–550 区间，须排队拆）
[WARN] 接近上限：app/core/bank/engine/dedupe.py=456 行（451–550 区间，须排队拆）
[WARN] 接近上限：app/core/content/question_parser.py=481 行（451–550 区间，须排队拆）
[WARN] 接近上限：app/core/ingest/render/regions.py=466 行（451–550 区间，须排队拆）
[WARN] 接近上限：app/core/pending/batch/bank_batches.py=491 行（451–550 区间，须排队拆）
[WARN] 接近上限：app/core/pending/meta/rules.py=498 行（451–550 区间，须排队拆）
[WARN] 接近上限：app/core/plugins/index/search.py=472 行（451–550 区间，须排队拆）
[WARN] 接近上限：static/css/workspace.css=497 行（451–550 区间，须排队拆）
[WARN] 接近上限：static/js/dict_console/linkage_tree.js=481 行（451–550 区间，须排队拆）
[WARN] 接近上限：static/js/st_plugins.js=463 行（451–550 区间，须排队拆）
[WARN] 接近上限：static/js/stage_relay_bank.js=467 行（451–550 区间，须排队拆）
[WARN] 接近上限：static/js/workspace.js=497 行（451–550 区间，须排队拆）
[WARN] 接近上限：plugins/org.jiuzhang.dashboard/dist/plugin.css=460 行（451–550 区间，须排队拆）
[WARN] 接近上限：plugins/org.jiuzhang.editor/dist/panel_meta.css=469 行（451–550 区间，须排队拆）
[WARN] 接近上限：plugins/org.jiuzhang.editor/dist/split_board.css=492 行（451–550 区间，须排队拆）
[WARN] 接近上限：plugins/org.jiuzhang.editor/dist/ui_approve.js=454 行（451–550 区间，须排队拆）
[WARN] 接近上限：plugins/org.jiuzhang.editor/dist/ui_illustration.js=477 行（451–550 区间，须排队拆）
体积预警：23 份文件处于 451–550 行区间，须排队拆
════════════════════════════════════════
check-quick-gate: PASS（6 项全过）
