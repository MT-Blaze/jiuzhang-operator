/**
 * 教材与章节树 · 行内新增（2026-11-13 从 entity_textbooks.js 拆出）：
 * 版本 / 册次 / 章 / 节点 + 后直接在该行下长出输入框，不再弹 Modal；
 * 编码由前端签发 custom_*，排序取同级最大值 + 1，保存后整树重载。
 * 整块下架：删本文件、dict_console.html 引用行与 entity_textbooks.js 的 DcTextbookAdd 调用。
 */
(function () {
  "use strict";

  var S = window.DcEntityShared;
  var VERSION_URL = "/api/bank/engine/dict/dim_textbook_versions";
  var BOOK_URL = "/api/bank/engine/dict/dim_textbooks";
  var CHAPTER_URL = "/api/bank/engine/dict/dim_textbook_chapters";

  /** opts = {tree, state, ctx, refresh(message)}；返回四个层级的新增入口。 */
  function mount(opts) {
    var tree = opts.tree;
    var state = opts.state;
    var refresh = opts.refresh;

    function rowOf(anchor) {
      return anchor && anchor.closest ? anchor.closest("li.det-item") : null;
    }

    function chapterNext(siblings) {
      return S.nextOrder(siblings, function (node) {
        return node && node.chapter ? node.chapter.sort_order : 0;
      });
    }

    function addBook(version, anchor) {
      var siblings = state.books[version.id] || [];
      S.addInline(rowOf(anchor), {
        anchor: anchor, label: "册次名称", defaultValue: "新册次",
        placeholder: "册次名，如 必修一",
        url: BOOK_URL,
        payload: function (name) {
          return {
            name: name, volume_name: name,
            code: window.DcTreeAdd.timestampCode(),
            version_id: version.id, subject_id: version.subject_id,
            sort_order: S.nextOrder(siblings)
          };
        },
        onSaved: function () {
          state.expanded.add("v:" + version.id);
          refresh("已新增册次。");
        },
        failTitle: "新增册次失败"
      });
    }

    function subjectLi(subjectId) {
      var rows = tree.querySelectorAll(".det-stage-subject");
      for (var i = 0; i < rows.length; i += 1) {
        if (rows[i].dataset.subjectId === String(subjectId)) return rows[i];
      }
      return null;
    }

    function addVersionRow(anchor) {
      var subjectId = opts.ctx.globals.query().subject_id;
      if (!subjectId) {
        S.fail("还不能新增版本", new Error("请先在右侧全局设置选择学科，再新增教材版本。"), anchor);
        return;
      }
      var li = subjectLi(subjectId);
      var host = null;
      if (!li) {
        host = S.el("ul", "det-children");
        tree.insertBefore(host, tree.firstChild);
      }
      S.addInline(li, {
        host: host, anchor: anchor, label: "版本名称", defaultValue: "新版本",
        placeholder: "版本名，如 人教A版",
        url: VERSION_URL,
        payload: function (name) {
          return {
            name: name, code: window.DcTreeAdd.timestampCode(), publisher: "",
            subject_id: subjectId, sort_order: S.nextOrder(state.versions)
          };
        },
        onSaved: function () { refresh("已新增版本。"); },
        failTitle: "新增版本失败"
      });
    }

    function addChapterUnderBook(book, anchor) {
      state.expanded.add("b:" + book.id);
      var roots = state.chapters[book.id] || [];
      S.addInline(rowOf(anchor), {
        anchor: anchor, label: "章名称", defaultValue: "新章",
        placeholder: "章名，如 第一章 集合",
        url: CHAPTER_URL,
        payload: function (name) {
          return {
            name: name, code: window.DcTreeAdd.timestampCode(),
            textbook_id: book.id, sort_order: chapterNext(roots)
          };
        },
        onSaved: function () { refresh("已新增章。"); },
        failTitle: "新增章失败"
      });
    }

    function addChapterUnderNode(book, node, anchor) {
      state.expanded.add("b:" + book.id);
      state.expanded.add("h:" + node.chapter.id);
      var kids = node.children || [];
      S.addInline(rowOf(anchor), {
        anchor: anchor, label: "节名称", defaultValue: "新节",
        placeholder: "节名，如 集合的概念",
        url: CHAPTER_URL,
        payload: function (name) {
          return {
            name: name, code: window.DcTreeAdd.timestampCode(),
            textbook_id: book.id, parent_id: node.chapter.id,
            sort_order: chapterNext(kids)
          };
        },
        onSaved: function () { refresh("已新增子章节。"); },
        failTitle: "新增节失败"
      });
    }

    return {
      addBook: addBook, addVersionRow: addVersionRow,
      addChapterUnderBook: addChapterUnderBook, addChapterUnderNode: addChapterUnderNode
    };
  }

  window.DcTextbookAdd = { mount: mount };
})();
