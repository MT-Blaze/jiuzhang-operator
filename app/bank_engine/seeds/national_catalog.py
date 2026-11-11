"""全国教材版本目录：只落版本与每版每学段一个真实册次锚点。

本模块不写 ``dim_textbook_chapters``，一个章节都不造。
册次锚点只用于把版本挂到学段（版本表本身没有学段列，学段由册次年级反推），
每版每学段只取该版本真实存在的首册，例如「西师大版·一年级上册」「大象版·一年级上册」。
新增版本 id 从 201 起、册次 id 从 12001 起，避开旧种子的 1..19 / 101..109 与 1xxx / 9xxx 号段。
"""

from __future__ import annotations

from typing import Iterable

from app.bank_engine.textbook_versions import version_code

SUBJECT_IDS: dict[str, int] = {
    "chinese": 1,
    "mathematics": 2,
    "english": 3,
    "physics": 4,
    "chemistry": 5,
    "biology": 6,
    "politics": 7,
    "history": 8,
    "geography": 9,
    "science": 10,
    "information_technology": 11,
    "physical_education": 12,
    "music": 13,
    "art": 14,
    "labor": 15,
}

SUBJECT_ABBR: dict[str, str] = {
    "chinese": "chn",
    "mathematics": "math",
    "english": "eng",
    "physics": "phy",
    "chemistry": "chem",
    "biology": "bio",
    "politics": "pol",
    "history": "his",
    "geography": "geo",
    "science": "sci",
    "information_technology": "it",
    "physical_education": "pe",
    "music": "mus",
    "art": "art",
    "labor": "lab",
}

STAGE_NAMES = {"P": "小学", "J": "初中", "S": "高中"}

# 字段：学科 code、版本名、出版社、编码片段、学段（P 小学 / J 初中 / S 高中）
# 同版本的多个学段合并一行；已存在的版本由 build 按 (subject_id, name) 复用 id。
SPECS: tuple[tuple[str, str, str, str, str], ...] = (
    # ── 语文：统编为主，保留仍在题库中出现的历史版本 ──
    ("chinese", "统编版", "人民教育出版社", "tb", "PJ"),
    ("chinese", "统编版（2019）", "人民教育出版社", "tb2019", "S"),
    ("chinese", "人教版", "人民教育出版社", "rj", "PJS"),
    ("chinese", "语文S版", "语文出版社", "yws", "PJ"),
    ("chinese", "语文A版", "语文出版社", "ywa", "P"),
    ("chinese", "语文版", "语文出版社", "yw", "S"),
    ("chinese", "苏教版", "江苏凤凰教育出版社", "sj", "PJS"),
    ("chinese", "北师大版", "北京师范大学出版社", "bsd", "PJS"),
    ("chinese", "鄂教版", "湖北教育出版社", "ej", "PJ"),
    ("chinese", "冀教版", "河北教育出版社", "jj", "PJ"),
    ("chinese", "河大版", "河南大学出版社", "hd", "PJ"),
    ("chinese", "长春版", "长春出版社", "cc", "PJ"),
    ("chinese", "鲁人版", "山东人民出版社", "lr", "S"),
    ("chinese", "粤教版", "广东教育出版社", "yj", "S"),
    ("chinese", "鲁教版", "山东教育出版社", "lj", "J"),
    ("chinese", "沪教版", "上海教育出版社", "hj", "PJS"),
    # ── 数学：小学 10 版、初中 14 版、高中 6 版 ──
    ("mathematics", "人教版", "人民教育出版社", "rj", "PJ"),
    ("mathematics", "人教A版", "人民教育出版社", "rja", "S"),
    ("mathematics", "人教B版", "人民教育出版社", "rjb", "S"),
    ("mathematics", "北师大版", "北京师范大学出版社", "bsd", "PJS"),
    ("mathematics", "苏教版", "江苏凤凰教育出版社", "sj", "PJS"),
    ("mathematics", "湘教版", "湖南教育出版社", "xj", "JS"),
    ("mathematics", "沪教版", "上海教育出版社", "hj", "PJS"),
    ("mathematics", "西师大版", "西南师范大学出版社", "xsd", "P"),
    ("mathematics", "青岛版", "青岛出版社", "qd", "PJ"),
    ("mathematics", "青岛版（五四制）", "青岛出版社", "qd54", "PJ"),
    ("mathematics", "冀教版", "河北教育出版社", "jj", "PJ"),
    ("mathematics", "北京版", "北京出版社", "bj", "PJ"),
    ("mathematics", "浙教版", "浙江教育出版社", "zj", "PJ"),
    ("mathematics", "华师大版", "华东师范大学出版社", "hsd", "J"),
    ("mathematics", "苏科版", "江苏凤凰科学技术出版社", "sk", "J"),
    ("mathematics", "沪科版", "上海科学技术出版社", "hk", "J"),
    ("mathematics", "鲁教版（五四制）", "山东教育出版社", "lj54", "J"),
    # ── 英语：小学以三起为主，初中/高中覆盖主流版本 ──
    ("english", "人教版PEP", "人民教育出版社", "rjpep", "P"),
    ("english", "人教版", "人民教育出版社", "rj", "J"),
    ("english", "人教版（2019）", "人民教育出版社", "rj2019", "S"),
    ("english", "人教精通版", "人民教育出版社", "rjjt", "P"),
    ("english", "人教新起点", "人民教育出版社", "rjqd", "P"),
    ("english", "外研版", "外语教学与研究出版社", "wy", "PJS"),
    ("english", "译林版", "译林出版社", "yl", "PJS"),
    ("english", "牛津上海版", "上海教育出版社", "njsh", "PJS"),
    ("english", "冀教版", "河北教育出版社", "jj", "PJS"),
    ("english", "北师大版", "北京师范大学出版社", "bsd", "PJS"),
    ("english", "湘少版", "湖南少年儿童出版社", "xs", "P"),
    ("english", "闽教版", "福建教育出版社", "mj", "P"),
    ("english", "粤人版", "广东人民出版社", "yr", "P"),
    ("english", "陕旅版", "陕西旅游出版社", "sl", "P"),
    ("english", "北京版", "北京出版社", "bj", "P"),
    ("english", "沪教版", "上海教育出版社", "hj", "PJ"),
    ("english", "教科版", "教育科学出版社", "jk", "P"),
    ("english", "川教版", "四川教育出版社", "cj", "P"),
    ("english", "辽师大版", "辽宁师范大学出版社", "lsd", "P"),
    ("english", "重大版", "重庆大学出版社", "zd", "PS"),
    ("english", "科普版", "科学普及出版社", "kp", "PJ"),
    ("english", "接力版", "接力出版社", "jl", "P"),
    ("english", "清华版", "清华大学出版社", "qh", "P"),
    ("english", "鲁科版（五四制）", "山东科学技术出版社", "lk54", "P"),
    ("english", "仁爱版", "北京市仁爱教育研究所", "ra", "J"),
    ("english", "沪外版", "上海外语教育出版社", "hw", "S"),
    ("english", "鲁教版", "山东教育出版社", "lj", "J"),
    # ── 物理：初中 6 版（含五四制），高中 6 版 ──
    ("physics", "人教版", "人民教育出版社", "rj", "JS"),
    ("physics", "鲁科版", "山东科学技术出版社", "lk", "S"),
    ("physics", "沪科版", "上海科学技术出版社", "hk", "JS"),
    ("physics", "粤教版", "广东教育出版社", "yj", "S"),
    ("physics", "教科版", "教育科学出版社", "jk", "JS"),
    ("physics", "苏科版", "江苏凤凰科学技术出版社", "sk", "J"),
    ("physics", "北师大版", "北京师范大学出版社", "bsd", "J"),
    ("physics", "沪粤版", "上海科学技术出版社、广东教育出版社", "hy", "J"),
    ("physics", "鲁教版（五四制）", "山东教育出版社", "lj54", "J"),
    ("physics", "苏教版", "江苏凤凰教育出版社", "sj", "S"),
    ("physics", "沪科技版", "上海科技教育出版社", "hkj", "S"),
    # ── 化学：初中 6 版、高中 4 版 ──
    ("chemistry", "人教版", "人民教育出版社", "rj", "J"),
    ("chemistry", "人教版（2019）", "人民教育出版社", "rj2019", "S"),
    ("chemistry", "鲁教版", "山东教育出版社", "lj", "J"),
    ("chemistry", "沪教版", "上海教育出版社", "hj", "J"),
    ("chemistry", "科粤版", "科学普及出版社、广东教育出版社", "ky", "J"),
    ("chemistry", "北京版", "北京出版社", "bj", "J"),
    ("chemistry", "科普版", "科学普及出版社", "kp", "J"),
    ("chemistry", "鲁科版", "山东科学技术出版社", "lk", "S"),
    ("chemistry", "苏教版", "江苏凤凰教育出版社", "sj", "S"),
    ("chemistry", "沪科版", "上海科学技术出版社", "hk", "S"),
    # ── 生物：初中 8 版、高中 5 版 ──
    ("biology", "人教版", "人民教育出版社", "rj", "J"),
    ("biology", "人教版（2019）", "人民教育出版社", "rj2019", "S"),
    ("biology", "北京版", "北京出版社", "bj", "J"),
    ("biology", "北师大版", "北京师范大学出版社", "bsd", "JS"),
    ("biology", "冀少版", "河北少年儿童出版社", "js", "J"),
    ("biology", "济南版", "济南出版社", "jn", "J"),
    ("biology", "苏教版", "江苏凤凰教育出版社", "sj", "JS"),
    ("biology", "苏科版", "江苏凤凰科学技术出版社", "sk", "J"),
    ("biology", "沪教版", "上海教育出版社", "hj", "J"),
    ("biology", "浙科版", "浙江科学技术出版社", "zk", "S"),
    ("biology", "沪科版", "上海科学技术出版社", "hk", "S"),
    # ── 政治：小学道德与法治与初中同为统编版，高中为统编版（2019） ──
    ("politics", "统编版", "人民教育出版社", "tb", "PJ"),
    ("politics", "统编版（2019）", "人民教育出版社", "tb2019", "S"),
    # ── 历史：统编为主，保留旧版初中/高中版本 ──
    ("history", "统编版", "人民教育出版社", "tb", "J"),
    ("history", "统编版（2019）", "人民教育出版社", "tb2019", "S"),
    ("history", "人教版", "人民教育出版社", "rj", "JS"),
    ("history", "北师大版", "北京师范大学出版社", "bsd", "J"),
    ("history", "岳麓版", "岳麓书社", "yl", "JS"),
    ("history", "中华书局版", "中华书局", "zh", "J"),
    ("history", "川教版", "四川教育出版社", "cj", "J"),
    ("history", "华东师大版", "华东师范大学出版社", "hsd", "J"),
    ("history", "人民版", "人民出版社", "rm", "S"),
    # ── 地理：初中 7 版、高中 5 版 ──
    ("geography", "人教版", "人民教育出版社", "rj", "J"),
    ("geography", "人教版（2019）", "人民教育出版社", "rj2019", "S"),
    ("geography", "湘教版", "湖南教育出版社", "xj", "JS"),
    ("geography", "中图版", "中国地图出版社", "zt", "JS"),
    ("geography", "商务星球版", "商务印书馆、星球地图出版社", "sw", "JS"),
    ("geography", "粤教版", "广东教育出版社", "yj", "J"),
    ("geography", "晋教版", "山西教育出版社", "jj", "J"),
    ("geography", "仁爱版", "北京市仁爱教育研究所", "ra", "J"),
    ("geography", "鲁教版", "山东教育出版社", "lj", "S"),
    # ── 科学：小学 13 版、初中 2 版 ──
    ("science", "教科版", "教育科学出版社", "jk", "P"),
    ("science", "苏教版", "江苏凤凰教育出版社", "sj", "P"),
    ("science", "湘科版", "湖南科学技术出版社", "xk", "P"),
    ("science", "大象版", "大象出版社", "dx", "P"),
    ("science", "青岛版", "青岛出版社", "qd", "P"),
    ("science", "青岛版（五四制）", "青岛出版社", "qd54", "P"),
    ("science", "粤教粤科版", "广东教育出版社、广东科技出版社", "yjyk", "P"),
    ("science", "人教鄂教版", "人民教育出版社、湖北教育出版社", "rjej", "P"),
    ("science", "冀人版", "河北人民出版社", "jr", "P"),
    ("science", "沪教版", "上海教育出版社", "hj", "PJ"),
    ("science", "沪科技版（五四制）", "上海科技教育出版社", "hkj54", "P"),
    ("science", "首师大版", "首都师范大学出版社", "ssd", "P"),
    ("science", "北京版", "北京出版社", "bj", "P"),
    ("science", "浙教版", "浙江教育出版社", "zj", "J"),
    ("science", "华东师大版", "华东师范大学出版社", "hsd", "J"),
    # ── 信息科技：地方课程版本多，取国家平台与主流省市版本 ──
    ("information_technology", "人教版", "人民教育出版社", "rj", "PJS"),
    ("information_technology", "浙教版", "浙江教育出版社", "zj", "PJS"),
    ("information_technology", "苏科版", "江苏凤凰科学技术出版社", "sk", "PJ"),
    ("information_technology", "粤教版", "广东教育出版社", "yj", "PJS"),
    ("information_technology", "川教版", "四川教育出版社", "cj", "PJ"),
    ("information_technology", "教科版", "教育科学出版社", "jk", "PJS"),
    ("information_technology", "沪科版", "上海科学技术出版社", "hk", "PJ"),
    ("information_technology", "沪教版", "上海教育出版社", "hj", "PJS"),
    ("information_technology", "闽教版", "福建教育出版社", "mj", "PJ"),
    ("information_technology", "冀教版", "河北教育出版社", "jj", "PJ"),
    ("information_technology", "北京版", "北京出版社", "bj", "PJ"),
    ("information_technology", "清华版", "清华大学出版社", "qh", "PJ"),
    ("information_technology", "电子工业版", "电子工业出版社", "dz", "PJ"),
    ("information_technology", "河南大学版", "河南大学出版社", "hd", "PJ"),
    ("information_technology", "西师大版", "西南师范大学出版社", "xsd", "PJ"),
    ("information_technology", "桂科版", "广西科学技术出版社", "gk", "PJ"),
    ("information_technology", "黔教版", "贵州教育出版社", "qj", "PJ"),
    ("information_technology", "泰山版", "泰山出版社", "ts", "PJ"),
    ("information_technology", "青岛版", "青岛出版社", "qd", "PJ"),
    ("information_technology", "鲁教版", "山东教育出版社", "lj", "PJ"),
    ("information_technology", "中图版", "中国地图出版社", "zt", "S"),
    ("information_technology", "华东师大版", "华东师范大学出版社", "hsd", "S"),
    # ── 体育与健康：2024 国家目录 10 版 ──
    ("physical_education", "人教版", "人民教育出版社", "rj", "PJS"),
    ("physical_education", "北京版", "北京出版社", "bj", "PJ"),
    ("physical_education", "华东师大版", "华东师范大学出版社", "hsd", "PJS"),
    ("physical_education", "冀教版", "河北教育出版社", "jj", "PJS"),
    ("physical_education", "教科版", "教育科学出版社", "jk", "PJ"),
    ("physical_education", "科学版", "科学出版社", "kx", "PJ"),
    ("physical_education", "未来版", "未来出版社", "wl", "PJ"),
    ("physical_education", "地质版", "地质出版社", "dz", "PJ"),
    ("physical_education", "华中师大版", "华中师范大学出版社", "hz", "PJ"),
    ("physical_education", "沪教版（五四制）", "上海教育出版社", "hj54", "PJ"),
    # ── 音乐：人音、人教、湘艺、花城等主流版本 ──
    ("music", "人音版", "人民音乐出版社", "ry", "PJS"),
    ("music", "人教版", "人民教育出版社", "rj", "PJS"),
    ("music", "湘艺版", "湖南文艺出版社", "xy", "PJS"),
    ("music", "花城版", "广东教育出版社、花城出版社", "hc", "PJS"),
    ("music", "苏少版", "江苏凤凰少年儿童出版社", "ss", "PJS"),
    ("music", "鄂教版", "湖北教育出版社", "ej", "PJ"),
    ("music", "冀少版", "河北少年儿童出版社", "js", "PJ"),
    ("music", "沪教版", "上海教育出版社", "hj", "PJ"),
    ("music", "辽海版", "辽海出版社", "lh", "PJ"),
    ("music", "西师大版", "西南师范大学出版社", "xsd", "PJ"),
    ("music", "鲁教版（五四制）", "山东教育出版社", "lj54", "PJ"),
    ("music", "接力版", "接力出版社", "jl", "PJ"),
    ("music", "教科版", "教育科学出版社", "jk", "PJ"),
    ("music", "北京版", "北京出版社", "bj", "PJ"),
    # ── 美术：人美、湘美、人教、苏少、岭南等主流版本 ──
    ("art", "人美版", "人民美术出版社", "rm", "PJS"),
    ("art", "人教版", "人民教育出版社", "rj", "PJS"),
    ("art", "湘美版", "湖南美术出版社", "xm", "PJS"),
    ("art", "苏少版", "江苏凤凰少年儿童出版社", "ss", "PJS"),
    ("art", "岭南美版", "岭南美术出版社", "ln", "PJ"),
    ("art", "赣美版", "江西美术出版社", "gm", "PJ"),
    ("art", "冀美版", "河北美术出版社", "jm", "PJ"),
    ("art", "辽海版", "辽海出版社", "lh", "PJ"),
    ("art", "浙人美版", "浙江人民美术出版社", "zrm", "PJ"),
    ("art", "桂美版", "广西美术出版社", "gmui", "PJ"),
    ("art", "鲁美版", "山东美术出版社", "lm", "PJ"),
    ("art", "沪书画版", "上海书画出版社", "hsh", "PJ"),
    # ── 劳动：地方课程，取主流省市版本 ──
    ("labor", "人教版", "人民教育出版社", "rj", "PJ"),
    ("labor", "北师大版（深圳报业版）", "北京师范大学出版社、深圳报业集团出版社", "bsd", "PJ"),
    ("labor", "粤教版", "广东教育出版社", "yj", "PJ"),
    ("labor", "浙教版", "浙江教育出版社", "zj", "PJ"),
    ("labor", "湘教版", "湖南教育出版社", "xj", "PJ"),
    ("labor", "苏教版", "江苏凤凰教育出版社", "sj", "PJ"),
    ("labor", "鄂教版", "湖北教育出版社", "ej", "PJ"),
    ("labor", "川民版", "四川民族出版社", "cm", "PJ"),
    ("labor", "人民版", "人民出版社", "rm", "PJ"),
    ("labor", "长江版", "长江出版社", "cj", "PJ"),
    ("labor", "东北师大版", "东北师范大学出版社", "dbsd", "PJ"),
)

NEXT_VERSION_ID = 201
NEXT_BOOK_ID = 12001


def _anchor(subject_code: str, stage: str) -> tuple[int, str]:
    """每版每学段只取一册真实首册，作为版本→学段的绑定锚点。"""
    if stage == "P":
        if subject_code == "english":
            return 3, "三年级上册"
        if subject_code == "information_technology":
            return 3, "三年级上册"
        if subject_code == "physical_education":
            return 1, "一年级全一册"
        return 1, "一年级上册"
    if stage == "J":
        if subject_code == "physics":
            return 8, "八年级上册"
        if subject_code == "chemistry":
            return 9, "九年级上册"
        if subject_code == "physical_education":
            return 7, "七年级全一册"
        return 7, "七年级上册"
    if subject_code in ("chinese", "history", "politics"):
        return 10, "必修上册"
    if subject_code == "music":
        return 10, "音乐鉴赏（必修）"
    if subject_code == "art":
        return 10, "美术鉴赏（必修）"
    if subject_code == "physical_education":
        return 10, "必修全一册"
    if subject_code == "information_technology":
        return 10, "必修1"
    return 10, "必修第一册"


def build(
    existing_versions: dict[tuple[int, str], int],
    covered_stages: dict[int, Iterable[str]],
    *,
    next_version_id: int = NEXT_VERSION_ID,
    next_book_id: int = NEXT_BOOK_ID,
) -> tuple[tuple[tuple, ...], tuple[tuple, ...]]:
    """按现有版本与学段覆盖，只产出缺失的版本行与册次锚点行。"""
    version_rows: list[tuple] = []
    book_rows: list[tuple] = []
    for subject_code, name, publisher, slug, stages in SPECS:
        subject_id = SUBJECT_IDS[subject_code]
        version_id = existing_versions.get((subject_id, name))
        covered = set(covered_stages.get(version_id, ())) if version_id else set()
        if version_id is None:
            version_id = next_version_id
            next_version_id += 1
            version_rows.append((
                version_id, name, version_code(slug, subject_id),
                version_id, publisher, subject_id,
            ))
        for stage in stages:
            if stage in covered:
                continue
            grade_id, volume = _anchor(subject_code, stage)
            book_id = next_book_id
            next_book_id += 1
            code = f"nc_{SUBJECT_ABBR[subject_code]}_{slug}_{stage}{grade_id}"
            book_rows.append((
                book_id, f"{name}·{volume}", code, 1, publisher,
                subject_id, grade_id, version_id, volume,
            ))
    return tuple(version_rows), tuple(book_rows)


__all__ = [
    "NEXT_BOOK_ID",
    "NEXT_VERSION_ID",
    "SPECS",
    "STAGE_NAMES",
    "SUBJECT_ABBR",
    "SUBJECT_IDS",
    "build",
]
