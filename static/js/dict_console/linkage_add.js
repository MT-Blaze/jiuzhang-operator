/**
 * 知识点与考向树 · 六级统一新增（2026-11-13）：
 * 版本 → 册次 → 章 → 节 → 知识点 → 考向，每一行只保留一个「+」，
 * 点击后按行所在层级自动选接口，不再出现「新增知识点 / 新增考向」两种文案。
 * 弹窗统一收名称 / 编码 / 排序号；编码留空由后端签发，排序留空自动排末尾。
 * 整块下架：删本文件、linkage_tree.js 的 DcLinkageAdd 调用与 node-add 样式即可。
 */
(function () {
  "use strict";

  var VERSION_URL = "/api/bank/engine/dict/dim_textbook_versions";
  var BOOK_URL = "/api/bank/engine/dict/dim_textbooks";
  var CHAPTER_URL = "/api/bank/engine/dict/dim_textbook_chapters";

  function chapterOrder(nodes) {
    return (nodes || []).reduce(function (max, node) {
      var value = node && node.chapter ? Number(node.chapter.sort_order) || 0 : 0;
      return Math.max(max, value);
    }, 0) + 1;
  }

  function bookOrder(items) {
    return (items || []).reduce(function (max, item) {
      var value = item && item.textbook ? Number(item.textbook.sort_order) || 0 : 0;
      return Math.max(max, value);
    }, 0) + 1;
  }

  /** 顶层：新建教材版本；成功回执交给树决定是否立刻选中该版本。 */
  function version(anchor, nextSort, onDone) {
    var subjectId = Number(window.DcGlobals.query().subject_id || 0);
    if (!subjectId) {
      window.DcTreeAdd.fail(
        "还不能新增教材版本",
        new Error("请先在右侧全局设置选择学科，再新增教材版本。"),
        anchor
      );
      return;
    }
    window.DcTreeAdd.open({
      title: "新增教材版本",
      message: "版本名只填「人教A版」这类出版社版本；册次在版本行点 + 继续加。",
      anchor: anchor,
      url: VERSION_URL,
      fields: [
        { key: "name", label: "版本名称", required: true, placeholder: "如 人教A版" },
        { key: "code", label: "版本编码", required: true, placeholder: "如 rja_math" },
        { key: "publisher", label: "出版社", placeholder: "如 人民教育出版社" },
        window.DcTreeAdd.sortField(nextSort)
      ],
      build: function (values) {
        return {
          name: values.name, code: values.code, publisher: values.publisher,
          subject_id: subjectId,
          sort_order: window.DcTreeAdd.sortValue(values.sort_order, nextSort)
        };
      },
      onDone: onDone
    });
  }

  function book(versionRow, items, anchor, onDone) {
    var nextSort = bookOrder(items);
    window.DcTreeAdd.open({
      title: "在「" + versionRow.name + "」下新增册次",
      message: "册次名只填「必修一 / 七年级上册」，完整书名保留版本与册次全称。",
      anchor: anchor,
      url: BOOK_URL,
      fields: [
        { key: "volume_name", label: "册次名", required: true, placeholder: "如 必修一" },
        { key: "name", label: "完整书名", required: true, placeholder: "如 人教A版数学必修一" },
        { key: "code", label: "册次编码", required: true, placeholder: "如 rja_m_1" },
        window.DcTreeAdd.sortField(nextSort)
      ],
      build: function (values) {
        return {
          name: values.name, code: values.code, volume_name: values.volume_name,
          version_id: versionRow.id, subject_id: versionRow.subject_id,
          sort_order: window.DcTreeAdd.sortValue(values.sort_order, nextSort)
        };
      },
      onDone: onDone
    });
  }

  /** parent 为空 = 给册次加顶层章；否则在该章下加节。 */
  function chapter(bookRow, parent, siblings, anchor, onDone) {
    var nextSort = chapterOrder(siblings);
    var under = parent ? "在「" + parent.name + "」下新增节" : "给「" + bookRow.volume_name + "」新增章";
    window.DcTreeAdd.open({
      title: under,
      message: "名称与编码都要填；编码全局唯一，可填章节号（如 1.2）。",
      anchor: anchor,
      url: CHAPTER_URL,
      fields: [
        { key: "name", label: "名称", required: true, placeholder: "如 函数的概念" },
        { key: "code", label: "编码", required: true, placeholder: "如 1.2" },
        window.DcTreeAdd.sortField(nextSort)
      ],
      build: function (values) {
        var payload = {
          name: values.name, code: values.code,
          textbook_id: bookRow.id,
          sort_order: window.DcTreeAdd.sortValue(values.sort_order, nextSort)
        };
        if (parent) payload.parent_id = parent.id;
        return payload;
      },
      onDone: onDone
    });
  }

  /** 知识点挂在章节下：学科由后端沿章节 → 册次继承，编码可留空自动签发。 */
  function point(chapterRow, siblingCount, anchor, onDone) {
    var nextSort = Number(siblingCount) || 0;
    window.DcTreeAdd.open({
      title: "在「" + chapterRow.name + "」下新增知识点",
      message: "编码可留空，系统会自动签发；排序号决定它在当前章节里的位置。",
      anchor: anchor,
      url: "/api/bank/engine/linkage/chapters/" + chapterRow.id + "/points",
      fields: [
        { key: "name", label: "知识点名称", required: true, placeholder: "如 函数的奇偶性" },
        { key: "code", label: "知识点编码", placeholder: "留空自动生成" },
        window.DcTreeAdd.sortField(nextSort)
      ],
      build: function (values) {
        return {
          name: values.name,
          code: values.code || "",
          sort_order: window.DcTreeAdd.sortValue(values.sort_order, nextSort)
        };
      },
      onDone: onDone
    });
  }

  /** 考向挂在知识点下：排序留空由后端按学科排到末尾。 */
  function direction(pointRow, anchor, onDone) {
    window.DcTreeAdd.open({
      title: "为「" + pointRow.name + "」新增考向",
      message: "考向名称同学科内唯一；排序号留空会自动排到末尾。",
      anchor: anchor,
      url: "/api/bank/engine/linkage/points/" + pointRow.id + "/directions",
      fields: [
        { key: "name", label: "考向名称", required: true, placeholder: "如 判断函数奇偶性" },
        window.DcTreeAdd.sortField("")
      ],
      build: function (values) {
        var payload = { name: values.name };
        var sort = window.DcTreeAdd.sortValue(values.sort_order, null);
        if (sort != null) payload.sort_order = sort;
        return payload;
      },
      onDone: onDone
    });
  }

  window.DcLinkageAdd = {
    version: version, book: book, chapter: chapter, point: point, direction: direction
  };
})();
