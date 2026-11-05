"""中转站（待审核池）Host API：给沙箱插件提供受控的批次暂存通道。

插件不直接碰数据库、不直接碰文件系统（AGENTS §2）；它把题目交给宿主，
宿主落进与主库物理隔离的中转站（``app/core/pending_bank.py``），老师审核
通过后才转成正式题目写进主库。

- 写接口（存草稿 / 通过入库 / 彻底删除 / 剔除重复）必须带一次性写令牌（AGENTS §5）；
- 读接口（批次列表 / 批次题目）开放，与题目列表同口径；
- **入库到哪个题库由底座定**：活跃题库 provider 由服务端解析，插件自报的一律
  不认——否则插件就能往任意一个已装题库里塞题。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from app.core import bank, pending_bank, pending_dedupe, pending_pool, questions
from app.core import bank_provider as provider
from app.core.pending_db import BATCH_ID_RE
from app.core.security import require_write_token

router = APIRouter(tags=["pending"])


@router.get("/api/pending/batches", summary="拉取所有批次（卡片视图）")
def pending_batches() -> dict[str, Any]:
    """批次卡片：时间、编号、未审数 / 总题数。

    有未审的批次在前，已审完的沉在最后——老师一眼看见「还欠多少」。
    """
    try:
        return pending_bank.batch_list()
    except pending_bank.PendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/api/pending/batches/{batch_id}/questions",
    summary="按批次拉取待审题目",
)
def pending_batch_questions(batch_id: str) -> dict[str, Any]:
    """返回的每一条都带完整题目文档，审核界面拿到就能直接渲染。"""
    try:
        return pending_bank.list_batch_questions(batch_id)
    except pending_bank.PendingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except pending_bank.PendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete(
    "/api/pending/batches/{batch_id}",
    summary="彻底删除整批（待审题与原卷资产一并清理）",
    dependencies=[Depends(require_write_token)],
)
def pending_delete_batch(batch_id: str) -> dict[str, Any]:
    """只删中转站里这一批，主库一个字节都不碰。"""
    try:
        return pending_bank.delete_batch(batch_id)
    except pending_bank.PendingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except pending_bank.PendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/api/pending/meta/history",
    summary="公共元数据的历史值",
)
def pending_meta_history() -> dict[str, Any]:
    """最近用过的地区 / 主体 / 考试类型 / 学科 / 明细学校，开新批次时自动带出。"""
    try:
        return pending_bank.meta_history()
    except pending_bank.PendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch(
    "/api/pending/batches/{batch_id}/meta",
    summary="改批次公共元数据，并立刻同步这一批所有题",
    dependencies=[Depends(require_write_token)],
)
def pending_set_meta(batch_id: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """请求体形如 ``{"year": 2024, "region": "黑吉辽", "body": "三省六校",
    "exam_type": "高三联考", "subject": "数学", "schools": ["哈三中"]}``。

    标准名不收：它是底座按 ``年份-地区-主体-类型-学科`` 拼出来的，客户端说了不算。

    改完立刻同步两处：池子里的待审题（``source`` 与隐藏标签），
    以及这一批已经进主库的题（补写主库 ``sources``）。同步不上的题一条也不动，
    并在 ``warnings`` 里如实报出原因。
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    try:
        return pending_bank.set_batch_meta(batch_id, payload)
    except pending_bank.PendingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except pending_bank.PendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/pending/batches",
    status_code=201,
    summary="存为待审：单题或批量题进中转站",
    dependencies=[Depends(require_write_token)],
)
def pending_save_draft(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """请求体形如 ``{"questions": [{"question": {...}, "assets": [...]}], "source_backup": "..."}``。

    ``id`` 与 ``meta`` 由底座签发，插件带来的作废；暂存题的 id 走 ``p_`` 号段，
    与主库的 ``q_`` 号段永不相交。``assets`` 可省略：给了就把配图字节落进
    ``pending_assets/``，题目在池子里期间配图不碰 ``uploads/``。
    ``batch_id`` 给了就并进那一批；不给就新开一批（``B-001`` 起）。
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    items = payload.get("questions")
    if items is None and isinstance(payload.get("question"), dict):
        items = [{
            "question": payload.get("question"),
            "assets": payload.get("assets"),
        }]
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=400, detail="缺少 questions 数组")
    try:
        return pending_bank.save_draft(
            items,
            batch_id=payload.get("batch_id"),
            source_backup=payload.get("source_backup"),
            source_name=payload.get("source_name"),
            origin=str(payload.get("origin") or ""),
            position=payload.get("position"),
        )
    except questions.QuestionValidationError as exc:
        raise HTTPException(
            status_code=422, detail={"message": "题目不符合 Schema", "errors": exc.errors}
        ) from exc
    except pending_bank.PendingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except pending_bank.PendingConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except pending_bank.PendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/api/pending/items/{pending_id}/duplicate",
    summary="入库前的后台查重：主库里的同题 / 高度相似题",
)
def pending_duplicate(pending_id: str) -> dict[str, Any]:
    """回一张可供老师裁决的报告，附带**两侧完整题目文档**（``incoming`` / ``existing``）。

    插件拿这两份去做左右**渲染**对比（不对比源码）。``level`` 为 ``identical`` 表示
    指纹全等，``high`` 表示高度相似，``none`` 表示主库里没有；``answer.same`` 为
    ``null`` 表示有一边没写答案，此时不作任何裁决。命中且答案不同时
    ``blocked`` 为真——界面必须红字拦截，只留「放弃」这一条路。
    """
    try:
        plugin_id = provider.resolve()["plugin_id"]
        report = pending_bank.duplicate_report(pending_id, plugin_id)
    except pending_bank.PendingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except pending_bank.PendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    report["blocked"] = bool(report.get("hit")) and report["answer"]["same"] is False
    return report


@router.post(
    "/api/pending/items/{pending_id}/approve",
    summary="存入主库：中转站的题转成正式题入库",
    dependencies=[Depends(require_write_token)],
)
def pending_approve(pending_id: str, payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
    """``p_`` 号段换成底座新签发的 ``q_``，配图搬进 ``uploads/``，池子里删干净。

    入哪个题库由服务端按**活跃题库 provider** 决定，插件无权指定。

    ``action`` 决定主库已有同题时怎么处置：``overwrite`` 以池子里这条为准覆盖，
    ``merge_solution`` 把这条的解析并成主库那题的「解法二」。不传 ``action`` 且
    ``force`` 不为真时保持老口径——回 **409** 并在 ``detail`` 里带上主库那道题的 id。

    ``action`` 取 ``overwrite`` / ``merge_solution`` 时若两边**答案不同**，一律回
    **409** 且 ``detail.answer_mismatch`` 为真：这一条只许放弃，覆盖与合并都封死
    （见 ``pending_bank`` 里的说明）。
    """
    body = payload if isinstance(payload, dict) else {}
    force = body.get("force") is True
    action = body.get("action")
    try:
        plugin_id = provider.resolve()["plugin_id"]
        return pending_bank.approve(pending_id, plugin_id, force=force,
                                    action=str(action or ""))
    except pending_bank.PendingDuplicateAnswer as exc:
        raise HTTPException(
            status_code=409,
            detail={"message": str(exc), "existing_id": exc.existing_id, "duplicate": True,
                    "answer_mismatch": True, "code": "duplicate_answer_mismatch",
                    "existing_answer": exc.existing_answer,
                    "incoming_answer": exc.incoming_answer},
        ) from exc
    except pending_bank.PendingDuplicate as exc:
        raise HTTPException(
            status_code=409,
            detail={"message": str(exc), "existing_id": exc.existing_id, "duplicate": True},
        ) from exc
    except pending_bank.PendingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except pending_bank.PendingConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except questions.QuestionValidationError as exc:
        raise HTTPException(
            status_code=422, detail={"message": "题目不符合 Schema", "errors": exc.errors}
        ) from exc
    except bank.BankNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bank.BankError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except pending_bank.PendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/pending/items/{pending_id}/delete",
    summary="彻底删除：从中转站删掉这一条",
    dependencies=[Depends(require_write_token)],
)
def pending_delete(pending_id: str) -> dict[str, Any]:
    """连同它在 ``pending_assets/`` 里的配图一起删；主库一个字节都不碰。"""
    try:
        return pending_bank.delete_pending(pending_id)
    except pending_bank.PendingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except pending_bank.PendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/api/pending/batches/{batch_id}/duplicates",
    summary="一键剔除前的清单：批内重复 + 与主库重复",
)
def pending_batch_duplicates(batch_id: str) -> dict[str, Any]:
    """只读清单（dry-run）：``groups`` 里每组带 ``reason``（``batch`` / ``bank``）。

    ``redundant`` 是两组 ``drop`` 的并集条数，``drop_ids`` 只是**默认勾选集**
    （``batch`` 组的 ``drop`` 并集、升序），``live_after`` 与 ``will_empty`` 都按默认
    勾选集算；老师改勾选后由前端按 ``scanned - 勾选数`` 实时重算。``main_scanned``
    是主库快照的实读行数，``main_snapshot_at`` 是快照时刻。

    ``batch_id`` 格式不合法与批次不存在同走 404（与 ``list_batch_questions`` 同口径）；
    主库读不通就如实报 404 / 400，**不降级**成「本批没有与主库重复的题」——那样老师
    按清单执行会漏剔。

    **配套的写口 ``POST .../purge-duplicates`` 需要 questions:write 令牌（宿主代持）**：
    插件永远看不到令牌，写动作由宿主按当前页签的 ``plugin.id`` 代发。
    """
    text_batch = str(batch_id or "").strip()
    if not BATCH_ID_RE.match(text_batch):
        raise HTTPException(
            status_code=404,
            detail={"code": "batch_purge_batch_not_found", "message": "批次编号不合法",
                    "retryable": False},
        )
    try:
        plugin_id = provider.resolve()["plugin_id"]
        return pending_dedupe.batch_duplicate_groups(text_batch, plugin_id)
    except pending_bank.PendingNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "batch_purge_batch_not_found", "message": str(exc),
                    "retryable": False},
        ) from exc
    except bank.BankNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "batch_purge_bank_not_found", "message": str(exc),
                    "retryable": False},
        ) from exc
    except bank.BankError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "batch_purge_bank_unavailable", "message": str(exc),
                    "retryable": True},
        ) from exc
    except pending_bank.PendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/pending/batches/{batch_id}/purge-duplicates",
    summary="一键剔除本批次重复题（按勾选集逐条判重）",
    dependencies=[Depends(require_write_token)],
)
def pending_purge_duplicates(batch_id: str,
                             payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """请求体 ``{"drop_ids": ["p_..."], "expected_drop_ids": ["p_..."], "allow_empty": false}``。

    ``drop_ids`` 是老师勾选集（升序），``expected_drop_ids`` 是同一集合的宿主回显，
    只做载荷自洽校验（防截断 / 中间层改写）；真正的护栏是服务端按**本次请求的主库
    快照**逐条重算——勾的条目已不再重复回 409 ``batch_purge_selection_stale``，勾到
    ``batch`` 组的保留者回 409 ``batch_purge_keep_selected``，都整批不动。把这一批剔空
    必须 ``allow_empty=true``，否则回 400 ``batch_purge_empty_not_confirmed``。

    删的只有池内条目与 ``pending_assets/`` 里的切图，主库一个字节都不碰；
    ``new_redundant`` 是重算重复全集里本次没剔的条数（只报数、不阻断）。

    **写口需 questions:write 令牌（宿主代持）**：插件不接触令牌，由宿主按当前页签的
    ``plugin.id`` 代发；``require_write_token`` 挡无令牌与错令牌。
    """
    body = payload if isinstance(payload, dict) else {}
    try:
        plugin_id = provider.resolve()["plugin_id"]
        return pending_bank.purge_batch_duplicates(
            batch_id, plugin_id,
            body.get("drop_ids"), body.get("expected_drop_ids"),
            allow_empty=body.get("allow_empty") is True,
        )
    except pending_bank.BatchPurgeError as exc:
        raise HTTPException(
            status_code=exc.status,
            detail={"code": exc.code, "message": str(exc), "retryable": exc.retryable},
        ) from exc
    except bank.BankNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bank.BankError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except pending_bank.PendingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except pending_bank.PendingConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except pending_bank.PendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------------------------------------------------------- 重题池（军令 #32 · 第四步）


@router.get(
    "/api/pending/pool",
    summary="重题池列表：一条一题，按像的程度降序",
)
def pending_pool_list(tier: str = "") -> dict[str, Any]:
    """只装「与主库有原题」的那一类候选。

    ``tier`` 是**读侧过滤**（``strict`` / ``standard`` / ``loose``），不落盘、不写配置：
    第五步的画布拖档时带着它重新取一次即可；不传就是全给。
    """
    try:
        return pending_pool.list_pool(tier=tier or None)
    except pending_bank.PendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/api/pending/pool/{pool_id}",
    summary="重题池单条：左右两侧完整文档＋置信度明细＋被锁动作",
)
def pending_pool_item(pool_id: str, tier: str = "") -> dict[str, Any]:
    """``incoming`` / ``existing`` 两份都是标准题目文档，供画布做**纯渲染**对比。

    ``locked_actions`` 是答案明确不同时要灰掉的那两个动作（判据 4.8）：
    前端只认这个数组，不许自己再算一遍答案像不像。
    """
    try:
        return pending_pool.get_entry(pool_id, tier=tier or None)
    except pending_bank.PendingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bank.BankNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except pending_bank.PendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except bank.BankError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/pending/pool/collect",
    summary="抽走：把一批初查命中的题从待审池搬进重题池（一条一题、已裁决不复活）",
    dependencies=[Depends(require_write_token)],
)
def pending_pool_collect(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """请求体 ``{"batch_id": "B-001", "tier": "loose"}``；``tier`` 可省（跟随初查结论的档）。

    只读已落盘的初查结论（``dedupe_findings``），不在这儿判重。初查失败或还没扫
    就照实回 ``admitted=0`` 并把 ``status`` / ``code`` / ``message`` 带回去，
    绝不伪装成「本批没有重题」。

    **这个接口是补拉，不是主路径**：正常链路是落池即扫的后台线程——初查算出的结论
    **不单独发布**，而是随抽走一并落库（``pending_dedupe.warm_batch_scan(admit=True)``
    → ``pending_pool.admit_from_scan``，判据 3.5；军令 #32 · S6 缺陷 2 的收口）。
    前端不需要等它、也不该靠它才让题消失。一条事务里「写池行＋删待审行＋刷新批次未审数
    ＋落 ``dedupe_scans``/``dedupe_findings``」四件事同时成立、一次提交，所以对外读得到
    ``done`` 的那一刻，卡片账目与池表已经是抽完的样子；``admitted`` 与 ``evicted`` 永远
    相等，``dedupe_findings`` 的行数与 ``reason="bank"`` 的候选条数、与实际搬进的池行数
    逐条对得上（不存在「一组只抽一条」那种去重键）。``skipped_missing_asset`` 列出因
    图文件缺失而整条没搬的题号（它们仍在待审池），批次未审数在同一事务里重算并随
    ``batches`` 回投。
    """
    body = payload if isinstance(payload, dict) else {}
    batch_id = str(body.get("batch_id") or "")
    if not BATCH_ID_RE.match(batch_id):
        raise HTTPException(status_code=400, detail="批次号不合法")
    try:
        plugin_id = provider.resolve()["plugin_id"]
        return pending_pool.admit_from_scan(
            batch_id, provider_id=plugin_id, tier=body.get("tier") or None,
        )
    except bank.BankNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except pending_bank.PendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/pending/pool/{pool_id}/act",
    summary="重题池四个动作：合并元数据 / 新增解析 / 不重复 / 删除",
    dependencies=[Depends(require_write_token)],
)
def pending_pool_act(pool_id: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """请求体 ``{"action": "merge_metadata" | "add_solution" | "keep_separate" | "delete"}``。

    动作名走**显式参数**，没有默认值，也没有「覆盖」「放弃」这两条退役的路。
    成功的那条一律从池里退场并留一行裁决记录（既是审计，也挡重扫复活）。

    - 答案明确不同 → 前两项回 **409** ``answer_mismatch``，后两项照走（判据 4.8）；
    - ``keep_separate`` 校验不过 → **200** 且 ``ok=false`` / ``written=false`` /
      ``kept_in_pool=true`` / ``missing`` 列出缺什么——缺项不是异常，是老师要补的活；
    - 池里没有这条 → 404；没有配主库原题却要并入库 → 400。
    """
    body = payload if isinstance(payload, dict) else {}
    try:
        return pending_pool.act(pool_id, body.get("action"))
    except pending_pool.PoolActionRefused as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": exc.code, "message": str(exc), "action": exc.action, **exc.detail},
        ) from exc
    except pending_bank.PendingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except pending_bank.PendingConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except questions.QuestionValidationError as exc:
        raise HTTPException(
            status_code=422, detail={"message": "题目不符合 Schema", "errors": exc.errors}
        ) from exc
    except bank.BankNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bank.BankError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except pending_bank.PendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
