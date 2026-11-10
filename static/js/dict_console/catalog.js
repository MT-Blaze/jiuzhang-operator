/**
 * 字典分类目录：三大分类与每张表的中文名、一句话说明。
 * 侧栏导航徽标与分类总览面板共用这一份，改口径只改这里。
 * 行数的实时值来自 /api/bank/engine/status 的 counts，不在这里写死。
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
        { table: "dict_subjects", name: "学科", desc: "语数英等 15 个一级学科。", editable: true },
        { table: "dict_grades", name: "年级", desc: "小学到高三 12 个年级，含学段归属。", editable: true },
        { table: "dict_question_types", name: "题型", desc: "选择 / 填空 / 解答三类。" },
        { table: "dict_difficulties", name: "难度", desc: "L1–L5 五级难度。" },
        { table: "dict_question_qualities", name: "题目质量", desc: "正常 / 待审 / 精品等质量标记。" },
        { table: "dict_exam_types", name: "考试类型", desc: "月考、期中、期末、模考等 16 类。", editable: true }
      ]
    },
    {
      key: "entity",
      title: "实体维度字典",
      desc: "真实世界的实体：行政区划、学校、教材与教材章节。",
      stage: 2,
      items: [
        { table: "dim_regions", name: "行政区划", desc: "省 / 市两级区划树。", editable: true },
        { table: "dim_schools", name: "学校", desc: "学校全称 / 简称，挂靠区划与教材。", editable: true },
        { table: "dim_textbooks", name: "教材版本", desc: "各出版社教材，按学科与年级分册。" },
        { table: "dim_textbook_chapters", name: "教材章节", desc: "章 / 节目录树，四栏联动的左栏。" }
      ]
    },
    {
      key: "teaching",
      title: "教研属性字典",
      desc: "教研核心：知识点、考向、思想方法、核心素养，以及章节—知识点—考向的联动映射。",
      stage: 3,
      items: [
        { table: "dim_knowledge_points", name: "知识点", desc: "全学科知识点树，四栏联动的中栏。" },
        { table: "dim_exam_directions", name: "考向", desc: "考向清单，四栏联动的右栏。" },
        { table: "dict_subject_thoughts", name: "学科思想", desc: "数形结合、分类讨论等思想标签。" },
        { table: "dict_solution_methods", name: "解题方法", desc: "配方法、换元法等 method 标签。" },
        { table: "dict_core_competencies", name: "核心素养", desc: "三会导向的核心素养表现。" }
      ]
    }
  ];

  function byKey(key) {
    for (var i = 0; i < CATEGORIES.length; i += 1) {
      if (CATEGORIES[i].key === key) return CATEGORIES[i];
    }
    return null;
  }

  window.DcCatalog = { CATEGORIES: CATEGORIES, byKey: byKey };
})();