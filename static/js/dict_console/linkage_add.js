/**
 * 知识点与考向树 · 六级行内新增（2026-11-13）：
 * 版本 → 册次 → 章 → 节 → 知识点 → 考向，点 + 直接在父节点下长出一行输入框，
 * 不再弹 Modal；编码不上界面，版本 / 册次 / 章由前端签发 custom_*，
 * 知识点 / 考向由后端签发；排序一律取同级最大值 + 1，界面按 sort_order 渲染。
 * 整块下架：删本文件、linkage_tree.js 的 DcLinkageAdd 调用与 node-add 样式即可。
 */
(function () {
  "use strict";

  var VERSION_URL = "/api/bank/engine/dict/dim_textbook_versions";
  var BOOK_URL = "/api/bank/engine/dict/dim_textbooks";
  var CHAPTER_URL = "/api/bank/engine/dict/dim_textbook_chapters";

  function T() { return window.DcTreeAdd; }

  function guide(prefix) {
    return function () {
      return window.DcLinkGuide.span(prefix || [], true, false, true);
    };
  }

  function rowClass(extra) {
    return "dkl-row dc-inline-row" + (extra ? " " + extra : "");
  }

  /** 顶层：新建教材版本；成功回执交给树决定是否立刻选中该版本。 */
  function version(spec) {
    var subjectId = Number(window.DcGlobals.query().subject_id || 0);
    if (!subjectId) {
      T().fail(
        "还不能新增教材版本",
        new Error("请先在右侧全局设置选择学科，再新增教材版本。"),
        spec.anchor
      );
      return null;
    }
    return T().inlineAdd({
      host: spec.host,
      before: spec.before,
      anchor: spec.anchor,
      rowClass: rowClass(),
      placeholder: "新版本名，如 人教A版",
      defaultValue: "新版本",
      label: "版本名称",
      url: VERSION_URL,
      payload: function (name) {
        return {
          name: name, code: T().timestampCode(), publisher: "",
          subject_id: subjectId, sort_order: T().nextOrder(spec.versions)
        };
      },
      onSaved: spec.onDone,
      failTitle: "新增版本失败"
    });
  }

  function book(spec) {
    var versionRow = spec.version;
    return T().inlineAdd({
      host: spec.host,
      before: spec.before,
      anchor: spec.anchor,
      guide: guide(spec.prefix),
      rowClass: rowClass("dkl-row-book"),
      placeholder: "册次名，如 必修一",
      defaultValue: "新册次",
      label: "册次名称",
      url: BOOK_URL,
      payload: function (name) {
        return {
          name: name, volume_name: name, code: T().timestampCode(), publisher: "",
          version_id: versionRow.id, subject_id: versionRow.subject_id,
          sort_order: T().nextOrder(spec.books, function (item) {
            return item && item.textbook ? item.textbook.sort_order : 0;
          })
        };
      },
      onSaved: spec.onDone,
      failTitle: "新增册次失败"
    });
  }

  /** parent 为空 = 给册次加顶层章；否则在该章下加节。 */
  function chapter(spec) {
    var parent = spec.parent || null;
    return T().inlineAdd({
      host: spec.host,
      before: spec.before,
      anchor: spec.anchor,
      guide: guide(spec.prefix),
      rowClass: rowClass(parent ? "dkl-row-chapter dkl-section" : "dkl-row-chapter"),
      placeholder: parent ? "新节名，如 集合的概念" : "新章名，如 第一章 集合",
      defaultValue: parent ? "新节" : "新章",
      label: parent ? "节名称" : "章名称",
      url: CHAPTER_URL,
      payload: function (name) {
        var payload = {
          name: name, code: T().timestampCode(),
          textbook_id: spec.book.id,
          sort_order: T().nextOrder(spec.siblings, function (node) {
            return node && node.chapter ? node.chapter.sort_order : 0;
          })
        };
        if (parent) payload.parent_id = parent.id;
        return payload;
      },
      onSaved: spec.onDone,
      failTitle: parent ? "新增节失败" : "新增章失败"
    });
  }

  /** 知识点挂在章节下：编码与排序都由后端签发 / 续排，前端只交名称。 */
  function point(spec) {
    return T().inlineAdd({
      host: spec.host,
      before: spec.before,
      anchor: spec.anchor,
      guide: guide(spec.prefix),
      rowClass: rowClass("dkl-row-point"),
      placeholder: "新知识点名，如 集合的概念",
      defaultValue: "新知识点",
      label: "知识点名称",
      url: "/api/bank/engine/linkage/chapters/" + spec.chapter.id + "/points",
      payload: function (name) { return { name: name }; },
      onSaved: spec.onDone,
      failTitle: "新增知识点失败"
    });
  }

  /** 考向挂在知识点下：编码与排序同样由后端签发 / 续排。 */
  function direction(spec) {
    return T().inlineAdd({
      host: spec.host,
      before: spec.before,
      anchor: spec.anchor,
      guide: guide(spec.prefix),
      rowClass: rowClass(),
      placeholder: "新考向名，如 判断函数奇偶性",
      defaultValue: "新考向",
      label: "考向名称",
      url: "/api/bank/engine/linkage/points/" + spec.point.id + "/directions",
      payload: function (name) { return { name: name }; },
      onSaved: spec.onDone,
      failTitle: "新增考向失败"
    });
  }

  window.DcLinkageAdd = {
    version: version, book: book, chapter: chapter, point: point, direction: direction
  };
})();
