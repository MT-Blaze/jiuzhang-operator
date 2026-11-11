"""高中数学与高中物理主流教材版本、册次骨架。

只落「版本 → 册次」两层（dim_textbook_versions / dim_textbooks）；
章节留给真实教材目录，不生成占位节点。
版本 id 从 101 起、册 id 从 9501/9601 起，避开旧种子自动切出的 1..19 与 1xxx/9xxx 号段。
"""

from __future__ import annotations

from app.bank_engine.textbook_versions import version_code

MATH_SUBJECT_ID = 2
PHYSICS_SUBJECT_ID = 4

CATALOG_VERSION_ROWS: tuple[tuple[int, str, str, int, str, int], ...] = (
    (101, "人教B版", version_code("rjb", MATH_SUBJECT_ID), 101, "人民教育出版社", MATH_SUBJECT_ID),
    (102, "北师大版", version_code("bsd", MATH_SUBJECT_ID), 102, "北京师范大学出版社", MATH_SUBJECT_ID),
    (103, "苏教版", version_code("sj", MATH_SUBJECT_ID), 103, "江苏凤凰教育出版社", MATH_SUBJECT_ID),
    (104, "湘教版", version_code("xj", MATH_SUBJECT_ID), 104, "湖南教育出版社", MATH_SUBJECT_ID),
    (105, "沪教版", version_code("hj", MATH_SUBJECT_ID), 105, "上海教育出版社", MATH_SUBJECT_ID),
    (106, "鲁科版", version_code("lk", PHYSICS_SUBJECT_ID), 106, "山东科学技术出版社", PHYSICS_SUBJECT_ID),
    (107, "沪科版", version_code("hk", PHYSICS_SUBJECT_ID), 107, "上海科学技术出版社", PHYSICS_SUBJECT_ID),
    (108, "粤教版", version_code("yj", PHYSICS_SUBJECT_ID), 108, "广东教育出版社", PHYSICS_SUBJECT_ID),
    (109, "教科版", version_code("jk", PHYSICS_SUBJECT_ID), 109, "教育科学出版社", PHYSICS_SUBJECT_ID),
)

CATALOG_BOOK_ROWS: tuple[tuple[int, str, str, int, str, int, int, int, str], ...] = (
    # 数学 · 人教A版（沿用已有版本 3；旧册 1..5，新册排在其后）
    (9501, "人教A版·必修第一册", "hs_math_rja_b1", 6, "人民教育出版社", MATH_SUBJECT_ID, 10, 3, "必修第一册"),
    (9502, "人教A版·必修第二册", "hs_math_rja_b2", 7, "人民教育出版社", MATH_SUBJECT_ID, 10, 3, "必修第二册"),
    (9503, "人教A版·选择性必修第一册", "hs_math_rja_x1", 8, "人民教育出版社", MATH_SUBJECT_ID, 11, 3, "选择性必修第一册"),
    (9504, "人教A版·选择性必修第二册", "hs_math_rja_x2", 9, "人民教育出版社", MATH_SUBJECT_ID, 11, 3, "选择性必修第二册"),
    (9505, "人教A版·选择性必修第三册", "hs_math_rja_x3", 10, "人民教育出版社", MATH_SUBJECT_ID, 11, 3, "选择性必修第三册"),
    # 数学 · 人教B版（版本 101）
    (9506, "人教B版·必修第一册", "hs_math_rjb_b1", 1, "人民教育出版社", MATH_SUBJECT_ID, 10, 101, "必修第一册"),
    (9507, "人教B版·必修第二册", "hs_math_rjb_b2", 2, "人民教育出版社", MATH_SUBJECT_ID, 10, 101, "必修第二册"),
    (9508, "人教B版·选择性必修第一册", "hs_math_rjb_x1", 3, "人民教育出版社", MATH_SUBJECT_ID, 11, 101, "选择性必修第一册"),
    (9509, "人教B版·选择性必修第二册", "hs_math_rjb_x2", 4, "人民教育出版社", MATH_SUBJECT_ID, 11, 101, "选择性必修第二册"),
    (9510, "人教B版·选择性必修第三册", "hs_math_rjb_x3", 5, "人民教育出版社", MATH_SUBJECT_ID, 11, 101, "选择性必修第三册"),
    # 数学 · 北师大版（版本 102）
    (9511, "北师大版·必修第一册", "hs_math_bsd_b1", 1, "北京师范大学出版社", MATH_SUBJECT_ID, 10, 102, "必修第一册"),
    (9512, "北师大版·必修第二册", "hs_math_bsd_b2", 2, "北京师范大学出版社", MATH_SUBJECT_ID, 10, 102, "必修第二册"),
    (9513, "北师大版·选择性必修第一册", "hs_math_bsd_x1", 3, "北京师范大学出版社", MATH_SUBJECT_ID, 11, 102, "选择性必修第一册"),
    (9514, "北师大版·选择性必修第二册", "hs_math_bsd_x2", 4, "北京师范大学出版社", MATH_SUBJECT_ID, 11, 102, "选择性必修第二册"),
    (9515, "北师大版·选择性必修第三册", "hs_math_bsd_x3", 5, "北京师范大学出版社", MATH_SUBJECT_ID, 11, 102, "选择性必修第三册"),
    # 数学 · 苏教版（版本 103）
    (9516, "苏教版·必修第一册", "hs_math_sj_b1", 1, "江苏凤凰教育出版社", MATH_SUBJECT_ID, 10, 103, "必修第一册"),
    (9517, "苏教版·必修第二册", "hs_math_sj_b2", 2, "江苏凤凰教育出版社", MATH_SUBJECT_ID, 10, 103, "必修第二册"),
    (9518, "苏教版·选择性必修第一册", "hs_math_sj_x1", 3, "江苏凤凰教育出版社", MATH_SUBJECT_ID, 11, 103, "选择性必修第一册"),
    (9519, "苏教版·选择性必修第二册", "hs_math_sj_x2", 4, "江苏凤凰教育出版社", MATH_SUBJECT_ID, 11, 103, "选择性必修第二册"),
    (9520, "苏教版·选择性必修第三册", "hs_math_sj_x3", 5, "江苏凤凰教育出版社", MATH_SUBJECT_ID, 11, 103, "选择性必修第三册"),
    # 数学 · 湘教版（版本 104）
    (9521, "湘教版·必修第一册", "hs_math_xj_b1", 1, "湖南教育出版社", MATH_SUBJECT_ID, 10, 104, "必修第一册"),
    (9522, "湘教版·必修第二册", "hs_math_xj_b2", 2, "湖南教育出版社", MATH_SUBJECT_ID, 10, 104, "必修第二册"),
    (9523, "湘教版·选择性必修第一册", "hs_math_xj_x1", 3, "湖南教育出版社", MATH_SUBJECT_ID, 11, 104, "选择性必修第一册"),
    (9524, "湘教版·选择性必修第二册", "hs_math_xj_x2", 4, "湖南教育出版社", MATH_SUBJECT_ID, 11, 104, "选择性必修第二册"),
    (9525, "湘教版·选择性必修第三册", "hs_math_xj_x3", 5, "湖南教育出版社", MATH_SUBJECT_ID, 11, 104, "选择性必修第三册"),
    # 数学 · 沪教版（版本 105）
    (9526, "沪教版·必修第一册", "hs_math_hj_b1", 1, "上海教育出版社", MATH_SUBJECT_ID, 10, 105, "必修第一册"),
    (9527, "沪教版·必修第二册", "hs_math_hj_b2", 2, "上海教育出版社", MATH_SUBJECT_ID, 10, 105, "必修第二册"),
    (9528, "沪教版·选择性必修第一册", "hs_math_hj_x1", 3, "上海教育出版社", MATH_SUBJECT_ID, 11, 105, "选择性必修第一册"),
    (9529, "沪教版·选择性必修第二册", "hs_math_hj_x2", 4, "上海教育出版社", MATH_SUBJECT_ID, 11, 105, "选择性必修第二册"),
    (9530, "沪教版·选择性必修第三册", "hs_math_hj_x3", 5, "上海教育出版社", MATH_SUBJECT_ID, 11, 105, "选择性必修第三册"),
    # 物理 · 人教版（沿用已有版本 9；旧初中册 30..32，新高中册排在其前）
    (9601, "人教版·必修第一册", "hs_phys_rj_b1", 1, "人民教育出版社", PHYSICS_SUBJECT_ID, 10, 9, "必修第一册"),
    (9602, "人教版·必修第二册", "hs_phys_rj_b2", 2, "人民教育出版社", PHYSICS_SUBJECT_ID, 10, 9, "必修第二册"),
    (9603, "人教版·必修第三册", "hs_phys_rj_b3", 3, "人民教育出版社", PHYSICS_SUBJECT_ID, 10, 9, "必修第三册"),
    (9604, "人教版·选择性必修第一册", "hs_phys_rj_x1", 4, "人民教育出版社", PHYSICS_SUBJECT_ID, 11, 9, "选择性必修第一册"),
    (9605, "人教版·选择性必修第二册", "hs_phys_rj_x2", 5, "人民教育出版社", PHYSICS_SUBJECT_ID, 11, 9, "选择性必修第二册"),
    (9606, "人教版·选择性必修第三册", "hs_phys_rj_x3", 6, "人民教育出版社", PHYSICS_SUBJECT_ID, 11, 9, "选择性必修第三册"),
    # 物理 · 鲁科版（版本 106）
    (9607, "鲁科版·必修第一册", "hs_phys_lk_b1", 1, "山东科学技术出版社", PHYSICS_SUBJECT_ID, 10, 106, "必修第一册"),
    (9608, "鲁科版·必修第二册", "hs_phys_lk_b2", 2, "山东科学技术出版社", PHYSICS_SUBJECT_ID, 10, 106, "必修第二册"),
    (9609, "鲁科版·必修第三册", "hs_phys_lk_b3", 3, "山东科学技术出版社", PHYSICS_SUBJECT_ID, 10, 106, "必修第三册"),
    (9610, "鲁科版·选择性必修第一册", "hs_phys_lk_x1", 4, "山东科学技术出版社", PHYSICS_SUBJECT_ID, 11, 106, "选择性必修第一册"),
    (9611, "鲁科版·选择性必修第二册", "hs_phys_lk_x2", 5, "山东科学技术出版社", PHYSICS_SUBJECT_ID, 11, 106, "选择性必修第二册"),
    (9612, "鲁科版·选择性必修第三册", "hs_phys_lk_x3", 6, "山东科学技术出版社", PHYSICS_SUBJECT_ID, 11, 106, "选择性必修第三册"),
    # 物理 · 沪科版（版本 107）
    (9613, "沪科版·必修第一册", "hs_phys_hk_b1", 1, "上海科学技术出版社", PHYSICS_SUBJECT_ID, 10, 107, "必修第一册"),
    (9614, "沪科版·必修第二册", "hs_phys_hk_b2", 2, "上海科学技术出版社", PHYSICS_SUBJECT_ID, 10, 107, "必修第二册"),
    (9615, "沪科版·必修第三册", "hs_phys_hk_b3", 3, "上海科学技术出版社", PHYSICS_SUBJECT_ID, 10, 107, "必修第三册"),
    (9616, "沪科版·选择性必修第一册", "hs_phys_hk_x1", 4, "上海科学技术出版社", PHYSICS_SUBJECT_ID, 11, 107, "选择性必修第一册"),
    (9617, "沪科版·选择性必修第二册", "hs_phys_hk_x2", 5, "上海科学技术出版社", PHYSICS_SUBJECT_ID, 11, 107, "选择性必修第二册"),
    (9618, "沪科版·选择性必修第三册", "hs_phys_hk_x3", 6, "上海科学技术出版社", PHYSICS_SUBJECT_ID, 11, 107, "选择性必修第三册"),
    # 物理 · 粤教版（版本 108）
    (9619, "粤教版·必修第一册", "hs_phys_yj_b1", 1, "广东教育出版社", PHYSICS_SUBJECT_ID, 10, 108, "必修第一册"),
    (9620, "粤教版·必修第二册", "hs_phys_yj_b2", 2, "广东教育出版社", PHYSICS_SUBJECT_ID, 10, 108, "必修第二册"),
    (9621, "粤教版·必修第三册", "hs_phys_yj_b3", 3, "广东教育出版社", PHYSICS_SUBJECT_ID, 10, 108, "必修第三册"),
    (9622, "粤教版·选择性必修第一册", "hs_phys_yj_x1", 4, "广东教育出版社", PHYSICS_SUBJECT_ID, 11, 108, "选择性必修第一册"),
    (9623, "粤教版·选择性必修第二册", "hs_phys_yj_x2", 5, "广东教育出版社", PHYSICS_SUBJECT_ID, 11, 108, "选择性必修第二册"),
    (9624, "粤教版·选择性必修第三册", "hs_phys_yj_x3", 6, "广东教育出版社", PHYSICS_SUBJECT_ID, 11, 108, "选择性必修第三册"),
    # 物理 · 教科版（版本 109）
    (9625, "教科版·必修第一册", "hs_phys_jk_b1", 1, "教育科学出版社", PHYSICS_SUBJECT_ID, 10, 109, "必修第一册"),
    (9626, "教科版·必修第二册", "hs_phys_jk_b2", 2, "教育科学出版社", PHYSICS_SUBJECT_ID, 10, 109, "必修第二册"),
    (9627, "教科版·必修第三册", "hs_phys_jk_b3", 3, "教育科学出版社", PHYSICS_SUBJECT_ID, 10, 109, "必修第三册"),
    (9628, "教科版·选择性必修第一册", "hs_phys_jk_x1", 4, "教育科学出版社", PHYSICS_SUBJECT_ID, 11, 109, "选择性必修第一册"),
    (9629, "教科版·选择性必修第二册", "hs_phys_jk_x2", 5, "教育科学出版社", PHYSICS_SUBJECT_ID, 11, 109, "选择性必修第二册"),
    (9630, "教科版·选择性必修第三册", "hs_phys_jk_x3", 6, "教育科学出版社", PHYSICS_SUBJECT_ID, 11, 109, "选择性必修第三册"),
)

__all__ = ["CATALOG_BOOK_ROWS", "CATALOG_VERSION_ROWS"]
