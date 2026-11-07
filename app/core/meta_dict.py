"""工作区级元数据字典：学校、主场景与带权重的交叉标签。

字典住 ``<工作区>/pending.db``，与中转站同一份文件、同一套边界（AGENTS §2）：
插件拿不到数据库，只能经 Host API 读写；题目文档里只落 ``school_id``，
学校名永远留在字典表里，改一次名不必回写每一道题。

三张表：
- ``schools``：``sch_xxx`` / 全称 / 简称。简称唯一，冲突时按主公裁定的原话拦截；
- ``scene_types``：11 个主场景，场景名就是题目 ``source.scene_type`` 的值；
- ``exam_types``：交叉标签 ``(name, scene)`` 复合主键，权重决定下拉次序；
  老师手打的新标签按回车就进库，下次在同一个场景里优先弹出。

查 AI 补全学校全称时只把简称与地区发出去，密钥始终留在底座进程里。
"""

from __future__ import annotations

import re
import secrets
from typing import Any

from app.core import ai_client, pending_db, pinyin, questions, wire


class MetaDictError(Exception):
    """字典操作失败（输入不合规、编号不存在等）。"""


class SchoolShortNameConflict(MetaDictError):
    """简称已被另一所学校占用。消息按主公裁定的原话，一字不改。"""

    def __init__(self, short_name: str, existing_full_name: str) -> None:
        super().__init__(f"❌ 简称冲突，已被【{existing_full_name}】占用")
        self.short_name = short_name
        self.existing_full_name = existing_full_name


SCHOOL_ID_RE = re.compile(r"^sch_[A-Za-z0-9_-]{4,40}$")
SCHOOL_LIMIT = 30
TAG_LIMIT = 20


def _clean(value: Any, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def _like(term: str) -> str:
    """把用户输入包成 LIKE 模式：``\\``、``%``、``_`` 先转义。

    老师手打的通配符不该悄悄变成「什么都匹配」——声明了 ESCAPE 就得照规矩转义。
    """
    escaped = str(term).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _school(row: Any) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "full_name": str(row["full_name"]),
        "short_name": str(row["short_name"]),
    }


# ---------------------------------------------------------------- 学校


def list_schools(query: str = "", limit: int = SCHOOL_LIMIT) -> dict[str, Any]:
    """按全称/简称模糊查学校；最近改过的排前面。"""
    text = _clean(query, 60)
    size = max(1, min(int(limit or SCHOOL_LIMIT), 100))
    con = pending_db.connect()
    try:
        if text:
            pattern = _like(text)
            rows = con.execute(
                "SELECT id, full_name, short_name FROM schools"
                " WHERE full_name LIKE ? ESCAPE '\\' OR short_name LIKE ? ESCAPE '\\'"
                " ORDER BY updated_at DESC, full_name ASC LIMIT ?",
                (pattern, pattern, size),
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT id, full_name, short_name FROM schools"
                " ORDER BY updated_at DESC, full_name ASC LIMIT ?",
                (size,),
            ).fetchall()
    finally:
        con.close()
    return {"schools": [_school(row) for row in rows], "query": text}


def get_schools(school_ids: list[str], *, strict: bool = True) -> list[dict[str, Any]]:
    """按 ID 批量取学校；顺序照入参。``strict`` 时未知 ID 直接报错。"""
    wanted = [str(item).strip() for item in school_ids if str(item).strip()]
    if not wanted:
        return []
    for school_id in wanted:
        if not SCHOOL_ID_RE.match(school_id):
            raise MetaDictError(f"学校编号不合法：{school_id[:40]}")
    unique = list(dict.fromkeys(wanted))
    placeholders = ",".join("?" for _ in unique)
    con = pending_db.connect()
    try:
        rows = con.execute(
            f"SELECT id, full_name, short_name FROM schools WHERE id IN ({placeholders})",
            unique,
        ).fetchall()
    finally:
        con.close()
    found = {str(row["id"]): _school(row) for row in rows}
    if strict:
        missing = [school_id for school_id in unique if school_id not in found]
        if missing:
            raise MetaDictError(f"学校字典里没有编号：{missing[0]}")
    return [found[school_id] for school_id in wanted if school_id in found]


def _insert_school(con: Any, full_name: str, short_name: str) -> dict[str, Any]:
    now = questions.now_iso()
    for _ in range(5):
        school_id = "sch_" + secrets.token_hex(8)
        if con.execute("SELECT 1 FROM schools WHERE id = ?", (school_id,)).fetchone():
            continue
        con.execute(
            "INSERT INTO schools (id, full_name, short_name, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (school_id, full_name, short_name, now, now),
        )
        return {"id": school_id, "full_name": full_name, "short_name": short_name}
    raise MetaDictError("签发学校编号失败，请重试")


def create_school(full_name: Any, short_name: Any = "") -> dict[str, Any]:
    """新建学校；同全称视为幂等命中，简称冲突按原话拦截。

    全称必填：老师只写了一个简称时，先走 AI 补全、确认后再落到这里。
    """
    full = _clean(full_name, 120)
    short = _clean(short_name, 60)
    if not full:
        raise MetaDictError("学校全称不能为空")
    if not short:
        short = full[:60]
    if len(full) < 2 or len(short) < 1:
        raise MetaDictError("学校名称太短，请写全")
    con = pending_db.connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        existing = con.execute(
            "SELECT id, full_name, short_name FROM schools WHERE full_name = ?", (full,)
        ).fetchone()
        if existing is not None:
            con.commit()
            return {"school": _school(existing), "created": False}
        conflict = con.execute(
            "SELECT full_name FROM schools WHERE short_name = ?", (short,)
        ).fetchone()
        if conflict is not None:
            raise SchoolShortNameConflict(short, str(conflict["full_name"]))
        school = _insert_school(con, full, short)
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
    return {"school": school, "created": True}


def find_or_create_by_name(name: Any) -> dict[str, Any]:
    """按全称或简称找一个学校，找不到就以这个名字建档。

    给老插件/旧数据留的兼容口：它们只会送校名，字典仍要替它们把 ID 补上，
    这样题目文档从第一天起就不必存校名。
    """
    text = _clean(name, 120)
    if not text:
        raise MetaDictError("学校名不能为空")
    con = pending_db.connect()
    try:
        row = con.execute(
            "SELECT id, full_name, short_name FROM schools"
            " WHERE full_name = ? OR short_name = ? LIMIT 1",
            (text, text[:60]),
        ).fetchone()
    finally:
        con.close()
    if row is not None:
        return _school(row)
    return create_school(text, text[:60])["school"]


async def suggest_school_full_name(short_name: Any, region: Any = "") -> dict[str, Any]:
    """AI 补全学校全称；只输出建议，不落库——老师确认后才建档。"""
    short = _clean(short_name, 60)
    area = _clean(region, 60)
    if not short:
        raise MetaDictError("先填一个简称或别名，才能让 AI 补全")
    system_prompt = (
        "你是中国中学名称补全助手。老师会给一个学校简称或别名，"
        "请给出最可能的规范全称。只输出一行 JSON，格式："
        '{"full_name": "学校规范全称", "confidence": 0.0}。'
        "无法判断时 full_name 留空字符串，绝不编造。"
    )
    user_message = f"简称：{short}\n地区：{area or '未填写'}"
    try:
        result = await ai_client.chat_completion(
            system_prompt, user_message, temperature=0.2, max_tokens=200
        )
    except Exception as exc:  # noqa: BLE001 - 模型/网络故障要变成可读提示
        raise MetaDictError(f"AI 补全失败：{exc}") from exc
    content = str(result.get("content") or "").strip()
    full, confidence = _parse_suggestion(content)
    if not full:
        raise MetaDictError("AI 没有给出可用的全称，请手工填写后确认")
    return {
        "short_name": short,
        "full_name": full,
        "confidence": confidence,
        "mock": bool(result.get("mock")),
    }


def _parse_suggestion(content: str) -> tuple[str, float]:
    """模型回包可能是纯 JSON，也可能夹着 ``` 围栏；能认出就认，认不出就取首行。"""
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[A-Za-z]*\s*|\s*```$", "", text).strip()
    try:
        data = wire.loads(text)
    except (TypeError, ValueError):
        data = None
    if isinstance(data, dict):
        full = _clean(data.get("full_name"), 120)
        try:
            confidence = float(data.get("confidence") or 0)
        except (TypeError, ValueError):
            confidence = 0.0
        return full, max(0.0, min(confidence, 1.0))
    line = next((row.strip() for row in text.splitlines() if row.strip()), "")
    return _clean(line, 120), 0.0


# ---------------------------------------------------------------- 场景


def list_scenes() -> dict[str, Any]:
    con = pending_db.connect()
    try:
        rows = con.execute(
            "SELECT id, name, sort_order FROM scene_types ORDER BY sort_order ASC, name ASC"
        ).fetchall()
    finally:
        con.close()
    return {
        "scenes": [
            {"id": str(row["id"]), "name": str(row["name"]), "order": int(row["sort_order"])}
            for row in rows
        ]
    }


def normalize_scene(value: Any) -> str:
    """场景只收字典里的 11 个；空串表示还没选。"""
    name = _clean(value, 64)
    if not name:
        return ""
    if name not in pending_db.SCENE_BY_NAME:
        raise MetaDictError(
            "不认识的场景「" + name + "」，可选：" + "、".join(pending_db.SCENE_NAMES)
        )
    return name


# ---------------------------------------------------------------- 交叉标签


def list_tags(scene: Any = "", query: Any = "", limit: int = TAG_LIMIT) -> dict[str, Any]:
    """模糊匹配标签，按「当前场景权重 → 总权重 → 最近使用」排序。

    场景专属权重排第一：选【外国题】时 AMC / A-Level / IB 冒头，选【校考题】
    时 9月月考 / 一模冒头；打一个「模」字，零到七模一次带出来。

    拼音首字母也算一条路：敲 ``J`` 能捞出「集合」「九模」，敲 ``js`` 能捞出
    「竞赛」——命中的是标签自带的拼音列，不是在库里做全表扫描。
    """
    scene_name = _clean(scene, 64)
    text = _clean(query, 32)
    size = max(1, min(int(limit or TAG_LIMIT), 50))
    con = pending_db.connect()
    try:
        if text:
            # 原文一条路、拼音首字母一条路：敲「J」捞集合。
            # 只有老师打的全是字母数字才开第二条路——打了汉字还顺拼音捞，
            # 「模」会把 AMC 端上桌（amc 里也有个 m），那是噪声不是命中。
            clause = "name LIKE ? ESCAPE '\\'"
            args: list[Any] = [scene_name, _like(text)]
            key = pinyin.initials(text) if text.isascii() else ""
            if key:
                clause += " OR pinyin LIKE ? ESCAPE '\\'"
                args.append(_like(key))
            args.append(size)
            rows = con.execute(
                "SELECT name, SUM(weight) AS total,"
                " MAX(CASE WHEN scene = ? THEN weight ELSE 0 END) AS scene_weight,"
                " MAX(updated_at) AS updated_at,"
                " MAX(pinyin) AS pinyin"
                f" FROM exam_types WHERE {clause}"
                " GROUP BY name"
                " ORDER BY scene_weight DESC, total DESC, updated_at DESC, name ASC"
                " LIMIT ?",
                args,
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT name, SUM(weight) AS total,"
                " MAX(CASE WHEN scene = ? THEN weight ELSE 0 END) AS scene_weight,"
                " MAX(updated_at) AS updated_at,"
                " MAX(pinyin) AS pinyin"
                " FROM exam_types"
                " GROUP BY name"
                " ORDER BY scene_weight DESC, total DESC, updated_at DESC, name ASC"
                " LIMIT ?",
                (scene_name, size),
            ).fetchall()
    finally:
        con.close()
    return {
        "tags": [
            {
                "name": str(row["name"]),
                "weight": int(row["total"] or 0),
                "scene_weight": int(row["scene_weight"] or 0),
                "scene": scene_name,
                "pinyin": str(row["pinyin"] or ""),
            }
            for row in rows
        ],
        "query": text,
        "scene": scene_name,
    }


def remember_tag(name: Any, scene: Any = "") -> dict[str, Any]:
    """老师手打/选用的标签记一笔：同一个标签在同场景里的权重 +1。

    新标签同时记下自己的拼音首字母——下次老师敲首字母就能把它捞出来。
    """
    text = _clean(name, 32)
    if not text:
        raise MetaDictError("标签不能为空")
    scene_name = normalize_scene(scene)
    now = questions.now_iso()
    con = pending_db.connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            "INSERT INTO exam_types (name, scene, weight, pinyin, updated_at)"
            " VALUES (?, ?, 1, ?, ?)"
            " ON CONFLICT(name, scene) DO UPDATE SET"
            " weight = weight + 1, pinyin = excluded.pinyin, updated_at = excluded.updated_at",
            (text, scene_name, pinyin.initials(text), now),
        )
        row = con.execute(
            "SELECT weight FROM exam_types WHERE name = ? AND scene = ?",
            (text, scene_name),
        ).fetchone()
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
    return {"tag": {"name": text, "scene": scene_name, "weight": int(row["weight"] or 0)}}


# ---------------------------------------------------------------- 响应装饰


def decorate_meta(meta: Any) -> dict[str, Any]:
    """给批次元数据补上学校明细：存储只留 ID，展示时才把名字查出来。"""
    data = dict(meta) if isinstance(meta, dict) else {}
    ids = [str(item) for item in (data.get("school_ids") or []) if str(item)]
    details = get_schools(ids, strict=False)
    data["school_details"] = details
    data["schools"] = [item["short_name"] for item in details]
    data.setdefault("name_mode", "auto")
    return data
