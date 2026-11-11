/**
 * 字典分类目录：三大分类与每张表的中文名、一句话说明。
 * 侧栏导航徽标与分类总览面板共用这一份，改口径只改这里。
 * 行数的实时值来自 /api/bank/engine/status 的 counts，不在这里写死。
 * subs 是分类页签内的二级标签：一个标签只对应一张表 / 一棵树 / 一组联动，
 * key 同时作为 URL 参数 sub 的值，刷新可还原。
 */
(function () {
  "use strict";

  var CATEGORIES = [
    {
      key: "foundation",
      title: "系统基石字典",
      desc: "录题与检索共用的基础枚举：学科、年级、题型、难度、质量、考试类型。",
      stage: 2,
      items: [
        { table: "dict_subjects", name: "学科", desc: "语数英等 15 个一级学科。" },
        { table: "dict_grades", name: "年级", desc: "小学到高三 12 个年级，含学段归属。" },
        { table: "dict_question_types", name: "题型", desc: "选择 / 填空 / 解答三类。" },
        { table: "dict_difficulties", name: "难度", desc: "L1–L5 五级难度。" },
        { table: "dict_question_qualities", name: "题目质量", desc: "正常 / 待审 / 精品等质量标记。" },
        { table: "dict_exam_types", name: "考试类型", desc: "月考、期中、期末、模考等 16 类。" }
      ],
      subs: [
        { key: "dict_subjects", label: "学科", table: "dict_subjects" },
        { key: "dict_grades", label: "年级", table: "dict_grades" },
        { key: "dict_question_types", label: "题型", table: "dict_question_types" },
        { key: "dict_difficulties", label: "难度", table: "dict_difficulties" },
        { key: "dict_question_qualities", label: "题目质量", table: "dict_question_qualities" },
        { key: "dict_exam_types", label: "考试类型", table: "dict_exam_types" }
      ]
    },
    {
      key: "entity",
      title: "实体维度字典",
      desc: "真实世界的实体：行政区划、学校、教材与教材章节。",
      stage: 2,
      items: [
        { table: "dim_regions", name: "行政区划", desc: "省 / 市两级区划树。" },
        { table: "dim_schools", name: "学校", desc: "学校全称 / 简称，挂靠区划与教材。" },
        { table: "dim_textbook_versions", name: "教材版本", desc: "各出版社教材版本，按学科区分。" },
        { table: "dim_textbook_chapters", name: "教材章节", desc: "章 / 节目录树，四栏联动的左栏。" }
      ],
      subs: [
        { key: "dim_textbook_versions", label: "教材版本", table: "dim_textbook_versions" },
        { key: "dim_schools", label: "学校", table: "dim_schools" },
        { key: "dim_textbook_chapters", label: "教材章节", mode: "chapters" },
        { key: "dim_regions", label: "行政区划", table: "dim_regions" }
      ]
    },
    {
      key: "teaching",
      title: "教研属性字典",
      desc: "教研核心：知识点、考向、思想方法、核心素养，以及章节—知识点—考向的联动映射。",
      stage: 3,
      items: [
        { table: "dim_knowledge_points", name: "知识点", desc: "四栏联动中栏：双击改名、拖拽排序。", linkage: true },
        { table: "dim_exam_directions", name: "考向", desc: "四栏联动右栏：新增 / 改名 / 删除防呆。", linkage: true },
        { table: "dict_subject_thoughts", name: "学科思想", desc: "数形结合、分类讨论等思想标签。" },
        { table: "dict_solution_methods", name: "解题方法", desc: "配方法、换元法等 method 标签。" },
        { table: "dict_core_competencies", name: "核心素养", desc: "三会导向的核心素养表现。" }
      ],
      subs: [
        { key: "knowledge-linkage", label: "知识点与考向", mode: "linkage" },
        { key: "dict_subject_thoughts", label: "学科思想", table: "dict_subject_thoughts" },
        { key: "dict_solution_methods", label: "解题方法", table: "dict_solution_methods" },
        { key: "dict_core_competencies", label: "核心素养", table: "dict_core_competencies" }
      ]
    }
  ];

  function byKey(key) {
    for (var i = 0; i < CATEGORIES.length; i += 1) {
      if (CATEGORIES[i].key === key) return CATEGORIES[i];
    }
    return null;
  }

  function itemOf(category, table) {
    if (!category || !table) return null;
    for (var i = 0; i < category.items.length; i += 1) {
      if (category.items[i].table === table) return category.items[i];
    }
    return null;
  }

  function subsOf(category) {
    if (!category) return [];
    if (category.subs && category.subs.length) return category.subs;
    return category.items.map(function (item) {
      return { key: item.table, label: item.name, table: item.table };
    });
  }

  window.DcCatalog = {
    CATEGORIES: CATEGORIES, byKey: byKey, itemOf: itemOf, subsOf: subsOf
  };
})();