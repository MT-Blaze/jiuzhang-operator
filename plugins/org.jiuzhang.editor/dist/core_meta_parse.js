/**
 * core_meta_parse.js —— 原文件名的正则解析（军令：失焦即自动填表）。
 *
 * 只认字典里真的有的词：年级/学科/地区从字典挑最长命中，学校与机构按后缀认。
 * 解析结果只做「加法」——没认出来的字段一律不碰，绝不清空老师已经填好的值。
 */
(function (global) {
  "use strict";

  var CN_DIGITS = { "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
    "七": 7, "八": 8, "九": 9, "十": 10 };

  var EXAM_RULES = [
    ["模拟考", /模拟考|模拟考试|[一二三四五六七八九十\d]+模/],
    ["高考", /高考|全国卷|新高考/],
    ["学业水平", /学业水平|会考|学考/],
    ["期中", /期中/],
    ["期末", /期末/],
    ["月考", /月考|月测|月度考/],
    ["周测", /周测|周考/],
    ["开学考", /开学考|开学考试|摸底考/]
  ];

  var SCHOOL_RE = /([\u4e00-\u9fa5]{2,12}?(?:高级中学|实验中学|第[一二三四五六七八九十\d]+中学|中学|附中|小学|学校|[一二三四五六七八九十\d]+中))/;
  var ORG_RE = /([A-Za-z0-9\u4e00-\u9fa5]{2,14}?(?:教育科学研究院|教科院|考试中心|考试院|教育局|教研室|联盟|联合体|协作体))/;

  function text(value) { return String(value == null ? "" : value); }

  /** 去扩展名与括号里的杂项，空白压平；保留年份与序号里的数字。 */
  function clean(raw) {
    return text(raw)
      .replace(/\.[A-Za-z0-9]{1,6}\s*$/, "")
      .replace(/[（(][^）)]*[）)]/g, " ")
      .replace(/[_\-—]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function flatOf(raw) { return clean(raw).replace(/\s+/g, ""); }

  function longestHit(haystack, names) {
    var hay = text(haystack);
    if (!hay) return "";
    var pool = (names || []).map(text).filter(Boolean)
      .sort(function (a, b) { return b.length - a.length; });
    for (var i = 0; i < pool.length; i += 1) {
      if (hay.indexOf(pool[i]) >= 0) return pool[i];
    }
    return "";
  }

  function toNumber(raw) {
    var value = text(raw);
    if (/^\d+$/.test(value)) return Number(value);
    var total = 0;
    for (var i = 0; i < value.length; i += 1) {
      var digit = CN_DIGITS[value.charAt(i)];
      if (!digit) return 0;
      total += digit;
    }
    return total;
  }

  function examTypeOf(flat) {
    for (var i = 0; i < EXAM_RULES.length; i += 1) {
      if (EXAM_RULES[i][1].test(flat)) return EXAM_RULES[i][0];
    }
    return "";
  }

  /** 学校名前面常挂一个「届」或年份，剪掉它，别把噪音带进主体。 */
  function trimSchool(name) {
    return text(name).replace(/^[届年月日\d]+/, "");
  }

  /**
   * dict: { grades, subjects, regions } —— 全部是字典里的规范名。
   * 返回只包含认出来的键；没认出来的不出现。
   */
  function parseSourceName(raw, dict) {
    var source = dict || {};
    var flat = flatOf(raw);
    var out = {};
    if (!flat) return out;

    var year = flat.match(/(?:19|20)\d{2}/);
    if (year) out.year = year[0];

    var month = flat.match(/(?:^|[^\d])(\d{1,2})月/);
    if (month) out.month = String(Number(month[1]));

    var round = flat.match(/([一二三四五六七八九十\d]+)模/);
    var examType = examTypeOf(flat);
    if (round) {
      var roundNo = toNumber(round[1]);
      if (roundNo >= 1 && roundNo <= 10) out.mock_round = String(roundNo);
      if (!examType) examType = "模拟考";
    }
    if (examType) out.exam_type = examType;

    var semester = flat.match(/下学期|下期|第二学期/);
    if (semester) out.semester = "下学期";
    else if (/上学期|上期|第一学期/.test(flat)) out.semester = "上学期";

    var grade = longestHit(flat, source.grades);
    if (grade) out.grade = grade;
    var subject = longestHit(flat, source.subjects);
    if (subject) out.subject = subject;

    // 地区只认字典里的真名：全国/东三省由底座字典给，前端不再自己补。
    var region = longestHit(flat, source.regions);
    if (region) out.region = region;

    var school = trimSchool((flat.match(SCHOOL_RE) || [])[0]);
    var org = (flat.match(ORG_RE) || [])[0];
    if (org) {
      out.body = org;
      if (school && school !== org) out.school = school;
    } else if (school) {
      out.body = school;
      out.body_kind = "school";
    }
    return out;
  }

  global.JzoEditorMetaParse = { parseSourceName: parseSourceName, toNumber: toNumber };
})(window);
