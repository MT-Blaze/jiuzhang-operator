#!/usr/bin/env python3
"""学校简称清洗：默认 Dry-Run 只读，`--apply` 才落库。

规则：
1. 去掉尾部行政区后缀（市/县/区/旗/盟/州/省，含「X族自治县」）。
2. 中文数字去掉「第」：第二十三 -> 二十三。
3. 级别缩写：高级中学 -> 高中，初级中学 -> 初中，中学 -> 中。
4. 组合：地名 + 数字 + 中/高中/初中，如「绥化市第二中学」->「绥化二中」。
5. 专名（实验/附属/外国语/民族/职业/企业办校等）保持原简称，不硬改。
6. 同地区重名强制带行政区前缀（本溪市/本溪县、阜新市/阜新县）。

用法：
    python scripts/clean_school_short_names.py            # 默认库，Dry-Run
    python scripts/clean_school_short_names.py --db xxx.db
    python scripts/clean_school_short_names.py --sample 30
    python scripts/clean_school_short_names.py --apply    # 落库（先自动备份）
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "banks" / "org.jiuzhang.bank-engine.v2.db"

ADMIN_CHARS = "省市县区旗盟"
ETHNIC_NAMES = (
    "满|蒙古|回|朝鲜|达斡尔|鄂温克|鄂伦春|锡伯|赫哲|土家|苗|彝|壮|侗|白|傣|"
    "布依|哈尼|傈僳|拉祜|佤|纳西|景颇|柯尔克孜|维吾尔|哈萨克|塔吉克|乌孜别克|"
    "俄罗斯|塔塔尔|撒拉|保安|裕固|仡佬|羌|普米|怒|阿昌|德昂|基诺|水|仫佬|"
    "毛南|京|高山|独龙|门巴|珞巴|瑶|黎|畲"
)
AUTONOMY_CORE_RE = re.compile(r"自治(?:县|旗|州)$")
ETHNIC_TAIL_RE = re.compile(rf"(?:{ETHNIC_NAMES})族$")


def strip_autonomy(text: str) -> str:
    stripped = AUTONOMY_CORE_RE.sub("", text)
    if stripped != text:
        stripped = ETHNIC_TAIL_RE.sub("", stripped)
    return stripped
SEGMENT_RE = re.compile(rf"[^{ADMIN_CHARS}]*[{ADMIN_CHARS}]|[^{ADMIN_CHARS}]+$")
NUMBERED_RE = re.compile(
    r"^(?P<prefix>.+?)"
    r"(?P<num>第[一二三四五六七八九十百零〇两]+|第[0-9]+|[0-9]+|[一二三四五六七八九十百零〇两]+)"
    r"(?P<level>高级中学|初级中学|中学|高中|初中|中)$"
)
# 带编号的高中按存量口径缩成「X中」（如 四平市第一高级中学 -> 四平一中）
NUMBERED_LEVEL = {
    "高级中学": "中",
    "高中": "高中",
    "初级中学": "初中",
    "初中": "初中",
    "中学": "中",
    "中": "中",
}

# 出现这些词说明名字里带专名/机构/企业，不能靠地名规则硬缩
PROPER_TOKENS = (
    "实验", "附属", "附中", "师范", "大学", "学院", "外国语", "外语",
    "职业", "民族", "回民", "族", "育才", "私立", "学校",
    "公司", "集团", "局", "厂", "矿", "钢", "机械", "化工", "化纤",
    "铁路", "油田", "林业", "农垦", "农场", "子弟", "职工",
    "开发区", "分校", "校区", "管理局",
)

PROVINCES = ("内蒙古", "黑龙江", "吉林", "辽宁", "河北", "山东", "河南", "山西")

# 老师拍板的人工口径：3 组重名强制带行政区前缀；150 中按中文读法缩写。
OVERRIDES: dict[int, str] = {
    197: "本溪市二中",
    228: "本溪县二中",
    248: "本溪县高中",
    270: "本溪市高中",
    175: "阜新市高中",
    281: "阜新县高中",
    302: "长春150中",
}


@dataclass
class School:
    id: int
    name: str
    short_name: str
    region: str
    region_id: int


@dataclass
class Proposal:
    school: School
    candidate: str | None
    action: str  # CHANGE / KEEP / MANUAL / EXISTING
    reason: str = ""


def load_schools(db_path: Path) -> list[School]:
    """只读打开数据库，禁止任何写操作。"""
    uri = f"file:{db_path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        rows = conn.execute(
            "SELECT id, name, short_name, region, region_id FROM dim_schools ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
    return [
        School(id=r[0], name=(r[1] or "").strip(),
               short_name=(r[2] or "").strip(), region=r[3] or "",
               region_id=r[4] or 0)
        for r in rows
    ]


def normalize_tail(name: str) -> str:
    n = name.strip()
    n = re.sub(r"高级中学校$", "高级中学", n)
    n = re.sub(r"初级中学校$", "初级中学", n)
    n = re.sub(r"中学校$", "中学", n)
    return n


def clean_place(prefix: str) -> tuple[str, bool]:
    """返回 (地名核心, 是否残留非行政区专名段)。"""
    p = prefix.strip()
    p = strip_autonomy(p)
    if not p:
        return "", False
    segments = SEGMENT_RE.findall(p)
    if not segments:
        return p, False
    last = segments[-1]
    if last.endswith("旗") and len(last) > 1 and last[-2] in "前后左右中东西南北":
        # 「鄂托克前旗 / 新巴尔虎右旗」去掉旗字会留下悬空的方位字
        return last, False
    if re.search(rf"[{ADMIN_CHARS}]$", last):
        return re.sub(rf"[{ADMIN_CHARS}]$", "", last), False
    if len(segments) > 1:
        # 行政层级之后还有一段专名，如「北票市尹湛纳希」「哈尔滨市双城区兆麟」
        return last, True
    return last, False


def has_proper_token(text: str) -> bool:
    return any(tok in text for tok in PROPER_TOKENS)


def proper_probe(prefix: str) -> str:
    """自治县里的族名属于行政区，先剥掉再判断专名。"""
    return strip_autonomy(prefix)


def limit_candidate(text: str | None) -> str | None:
    if text is None or len(text) > 10 or "（" in text or "(" in text:
        return None
    return text


def convert_number(num: str) -> tuple[str, bool]:
    """去掉「第」；阿拉伯数字返回需人工确认标记。"""
    if num.startswith("第"):
        num = num[1:]
    if num.isdigit():
        return num, True
    return num, False


def build_candidate(raw_name: str) -> tuple[str | None, str]:
    """根据规则给出建议简称；无法安全处理时返回 (None 或候选, 人工原因)。"""
    name = normalize_tail(raw_name)

    if "分校" in name or "校区" in name:
        return None, "含分校/校区，简称需保留校区专名"

    m = NUMBERED_RE.match(name)
    if m:
        prefix, num = m.group("prefix"), m.group("num")
        level = NUMBERED_LEVEL[m.group("level")]
        core, leftover = clean_place(prefix)
        chinese_num, arabic = convert_number(num)
        if leftover:
            return limit_candidate(core + chinese_num + level), f"地名后含专名「{core}」，不宜自动缩写"
        if has_proper_token(proper_probe(prefix)):
            return limit_candidate(core + chinese_num + level), f"前缀含专名/机构词「{prefix}」，不宜自动缩写"
        if arabic:
            return core + chinese_num + level, "含阿拉伯数字，中文写法需人工确认"
        if not core:
            return None, "缺少地名前缀"
        return core + chinese_num + level, ""

    # 无数字的「高级中学 / 高中」
    m = re.match(r"^(?P<prefix>.+?)(?P<level>高级中学|高中)$", name)
    if m:
        prefix = m.group("prefix")
        core, leftover = clean_place(prefix)
        if leftover:
            return limit_candidate(core + "高中"), f"地名后含专名「{core}」，不宜自动缩写"
        if has_proper_token(proper_probe(prefix)):
            return limit_candidate(core + "高中"), f"前缀含专名/机构词「{prefix}」，不宜自动缩写"
        if not core:
            return None, "缺少地名前缀"
        return core + "高中", ""

    # 无数字的「初级中学 / 初中」
    m = re.match(r"^(?P<prefix>.+?)(?P<level>初级中学|初中)$", name)
    if m:
        prefix = m.group("prefix")
        core, leftover = clean_place(prefix)
        if leftover or has_proper_token(proper_probe(prefix)):
            return limit_candidate(core + "初中"), "无数字初中，简称读感需人工定夺"
        return core + "初中", "无数字初中，简称读感需人工定夺"

    # 无数字的「中学」：缩写为「X中」读感不稳定，一律人工
    m = re.match(r"^(?P<prefix>.+?)中学$", name)
    if m:
        prefix = m.group("prefix")
        core, leftover = clean_place(prefix)
        if has_proper_token(proper_probe(prefix)) or leftover:
            return None, "含专名/机构词，无数字，不建议自动缩写"
        return core + "中", "无数字中学，缩写读感存疑，需人工定名"

    # 外国语学校：只去掉「学校」二字
    m = re.match(r"^(?P<prefix>.+?)外国语学校$", name)
    if m:
        core, leftover = clean_place(m.group("prefix"))
        return core + "外国语", ""

    return None, "规则无法安全识别学校类型"


def classify(school: School) -> Proposal:
    override = OVERRIDES.get(school.id)
    if override is not None:
        if override == school.short_name:
            return Proposal(school, override, "KEEP", "已是老师指定简称")
        return Proposal(school, override, "CHANGE", "老师指定口径")
    if school.short_name and school.short_name != school.name:
        return Proposal(school, school.short_name, "EXISTING", "已有简称，按规则不重复处理")
    candidate, reason = build_candidate(school.name)
    if reason:
        return Proposal(school, candidate, "MANUAL", reason)
    if candidate is None:
        return Proposal(school, None, "MANUAL", "规则无法安全识别学校类型")
    if candidate == school.short_name:
        return Proposal(school, candidate, "KEEP", "简称已符合规则")
    return Proposal(school, candidate, "CHANGE", "")


def province_of(region: str) -> str:
    for p in PROVINCES:
        if region.startswith(p):
            return p
    return region[:2] or "其他"


def pick_samples(changes: list[Proposal], limit: int) -> list[Proposal]:
    """按省份轮转、省份内按地区轮转抽样，保证地域分散。"""
    buckets: dict[str, dict[str, list[Proposal]]] = defaultdict(lambda: defaultdict(list))
    for p in changes:
        buckets[province_of(p.school.region)][p.school.region].append(p)
    queues = {
        prov: [q for _, q in sorted(regions.items())]
        for prov, regions in buckets.items()
    }
    picked: list[Proposal] = []
    round_no = 0
    while len(picked) < limit:
        progressed = False
        for prov in sorted(queues):
            qs = queues[prov]
            for offset in range(len(qs)):
                q = qs[(round_no + offset) % len(qs)]
                if q:
                    picked.append(q.pop(0))
                    progressed = True
                    break
            if len(picked) >= limit:
                break
        if not progressed:
            break
        round_no += 1
    return picked


def fmt_row(p: Proposal) -> str:
    return f"{p.school.name}  ->  {p.school.short_name or '（空）'}  ->  {p.candidate or '（无）'}"


def backup_db(db_path: Path) -> Path:
    target = db_path.with_name(db_path.name + ".pre-school-shortname.bak")
    if target.exists():
        return target
    src = sqlite3.connect(str(db_path), timeout=30.0)
    dest = sqlite3.connect(str(target), timeout=30.0)
    try:
        src.backup(dest)
    finally:
        dest.close()
        src.close()
    return target


def apply_changes(db_path: Path, changes: list[Proposal]) -> None:
    backup = backup_db(db_path)
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    try:
        with conn:
            conn.executemany(
                "UPDATE dim_schools SET short_name = ? WHERE id = ?",
                [(p.candidate, p.school.id) for p in changes],
            )
        verified = sum(
            1 for p in changes
            if (conn.execute(
                "SELECT short_name FROM dim_schools WHERE id = ?", (p.school.id,)
            ).fetchone() or [None])[0] == p.candidate
        )
    finally:
        conn.close()
    print(f"已备份：{backup}")
    print(f"落库完成：提交 {len(changes)} 条，复核一致 {verified} 条。")
    print()
    print(f"-- 落库明细（{len(changes)} 条）--")
    for p in changes:
        print(f"{p.school.id:>3} {p.school.region} | {p.school.name}  ->  {p.candidate}")


def main() -> int:
    parser = argparse.ArgumentParser(description="学校简称清洗（默认 Dry-Run，--apply 落库）")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="引擎库路径")
    parser.add_argument("--sample", type=int, default=24, help="抽样对比条数")
    parser.add_argument("--apply", action="store_true", help="真正写库（默认只读 Dry-Run）")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"库不存在：{db_path}")
        return 1

    schools = load_schools(db_path)
    proposals = [classify(s) for s in schools]
    changes = [p for p in proposals if p.action == "CHANGE"]
    keeps = [p for p in proposals if p.action == "KEEP"]
    manuals = [p for p in proposals if p.action == "MANUAL"]
    existings = [p for p in proposals if p.action == "EXISTING"]

    # 存量简称审计：已有简称但仍带行政区/完整级别词，提示老师复核
    audit = [
        p for p in existings
        if re.search(rf"[{ADMIN_CHARS}]", p.school.short_name)
        or p.school.short_name.endswith(("高级中学", "初级中学", "学校"))
        or len(p.school.short_name) > 12
    ]

    print("=" * 78)
    print("学校简称清洗 Dry-Run（只读，不写库）")
    print(f"库：{db_path}")
    print("=" * 78)
    print(f"总校数：{len(schools)}")
    print(f"实际会变更：{len(changes)}")
    print(f"未变更：{len(schools) - len(changes) - len(manuals)}"
          f"（已有简称保留 {len(existings)} + 已符合规则 {len(keeps)}）")
    print(f"需人工确认：{len(manuals)}")
    print(f"存量简称疑似未规范（仅提示，不改）：{len(audit)}")

    # 重名检测：按 region_id + 最终简称
    final: dict[tuple[int, str], list[Proposal]] = defaultdict(list)
    for p in proposals:
        label = p.candidate if p.action in ("CHANGE", "KEEP") else p.school.short_name
        if label:
            final[(p.school.region_id, label)].append(p)
    dup_groups = [(k, v) for k, v in sorted(final.items()) if len(v) > 1]
    print(f"疑似重名组：{len(dup_groups)}")

    sample = pick_samples(changes, max(args.sample, 20))
    print()
    print(f"-- 抽样对比（{len(sample)} 条，跨省份/地区分散）--")
    for i, p in enumerate(sample, 1):
        print(f"[{i:02d}] {p.school.region} | {fmt_row(p)}")

    print()
    print(f"-- 全量变更清单（{len(changes)} 条）--")
    for p in changes:
        print(f"{p.school.id:>3} {p.school.region} | {fmt_row(p)}")

    print()
    print(f"-- 需人工确认（{len(manuals)} 条，未硬改）--")
    for p in manuals:
        print(f"{p.school.id:>3} {p.school.region} | {p.school.name}  ->  旧：{p.school.short_name}"
              f"  ->  候选：{p.candidate or '（无）'}  |  {p.reason}")

    if audit:
        print()
        print(f"-- 存量简称疑似未规范（{len(audit)} 条，保留现状）--")
        for p in audit:
            print(f"{p.school.id:>3} {p.school.region} | {p.school.name}  ->  {p.school.short_name}")

    if dup_groups:
        print()
        print(f"-- 疑似重名组（同一地区，{len(dup_groups)} 组）--")
        for (region_id, label), items in dup_groups:
            print(f"地区#{region_id}「{label}」：")
            for p in items:
                print(f"    {p.school.id:>3} {p.school.name}（旧简称：{p.school.short_name}）")

    if args.apply:
        if dup_groups:
            print()
            print("存在重名组，拒绝落库；请先处理重名口径。")
            return 2
        print()
        apply_changes(db_path, changes)
        after = load_schools(db_path)
        grouped: dict[tuple[int, str], list[School]] = defaultdict(list)
        for s in after:
            if s.short_name:
                grouped[(s.region_id, s.short_name)].append(s)
        remaining = [key for key, items in grouped.items() if len(items) > 1]
        print()
        print(f"重名复核：{len(remaining)} 组")
        for region_id, label in remaining:
            print(f"地区#{region_id}「{label}」："
                  + "、".join(s.name for s in grouped[(region_id, label)]))
        print()
        print("落库结束：数据库已更新，未生成 JSON、未提交。")
    else:
        print()
        print("Dry-Run 结束：未写库、未生成 JSON、未提交。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
