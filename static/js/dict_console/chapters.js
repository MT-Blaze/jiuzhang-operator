/**
 * 实体维度 · 教材章节：保留“左树右表”左右布局。
 * 左侧按 版本 → 册次 → 章 → 节 展开（数据来自 linkage/version-tree，真实章节）；
 * 右侧跟随选中节点：选册次看本册章表，选章节看章节明细与下级节点表。
 * 未选教材版本时如实提示，绝不拿假树占位。
 * 整块下架：删本文件与 dict_console_subtabs.css 的 dcc-* 段即可。
 */
(function () {
  "use strict";

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function countNodes(nodes) {
    return (nodes || []).reduce(function (sum, node) {
      return sum + 1 + countNodes(node.children);
    }, 0);
  }

  function mount(host, ctx) {
    var wrap = el("section", "dc-chapters");

    var state = el("p", "dcc-state", "");
    state.setAttribute("role", "status");
    state.setAttribute("aria-live", "polite");
    wrap.appendChild(state);

    var layout = el("div", "dcc-layout");
    var left = el("section", "dcc-pane");
    left.setAttribute("aria-label", "教材章节树");
    left.appendChild(el("h3", "dcc-title", "版本 · 册次 · 章节"));
    var tree = el("div", "dcc-tree");
    left.appendChild(tree);

    var right = el("section", "dcc-pane");
    right.setAttribute("aria-label", "章节明细");
    var detailTitle = el("h3", "dcc-title", "章节明细");
    right.appendChild(detailTitle);
    var detail = el("div", "dcc-detail");
    right.appendChild(detail);

    layout.appendChild(left);
    layout.appendChild(right);
    wrap.appendChild(layout);
    host.appendChild(wrap);

    var selectedButton = null;
    var books = [];

    function select(button) {
      if (selectedButton) selectedButton.classList.remove("is-selected");
      selectedButton = button || null;
      if (button) button.classList.add("is-selected");
    }

    function actionButton(text, label, onClick) {
      var btn = el("button", "dcc-op", text);
      btn.type = "button";
      btn.setAttribute("aria-label", label);
      btn.title = label;
      btn.addEventListener("click", onClick);
      return btn;
    }

    function opsBar(buttons) {
      var bar = el("div", "dcc-ops");
      buttons.forEach(function (btn) { bar.appendChild(btn); });
      return bar;
    }

    function detailTable(headers, rows) {
      var scroll = el("div", "dcc-table-scroll");
      var table = el("table", "dcc-table");
      var thead = document.createElement("thead");
      var tr = document.createElement("tr");
      headers.forEach(function (label) {
        var th = el("th", "", label);
        th.scope = "col";
        tr.appendChild(th);
      });
      thead.appendChild(tr);
      var tbody = document.createElement("tbody");
      rows.forEach(function (cells) {
        var row = document.createElement("tr");
        cells.forEach(function (cell) { row.appendChild(el("td", "", String(cell))); });
        tbody.appendChild(row);
      });
      table.appendChild(thead);
      table.appendChild(tbody);
      scroll.appendChild(table);
      if (!rows.length) scroll.appendChild(el("p", "dcc-empty", "该节点下没有更多章节。"));
      return scroll;
    }

    function showChapter(chapter, children) {
      detail.textContent = "";
      detail.appendChild(opsBar([
        actionButton("＋ 子章节", "在「" + chapter.name + "」下新增章节", function () {
          window.DcChapterOps.add(chapter, children, chapter.textbook_id, load);
        }),
        actionButton("改名", "修改「" + chapter.name + "」的名称", function () {
          window.DcChapterOps.rename(chapter, load);
        }),
        actionButton("删除", "删除章节「" + chapter.name + "」", function () {
          window.DcChapterOps.remove(chapter, load);
        })
      ]));
      detail.appendChild(el("p", "dcc-detail-name", chapter.name));
      var meta = [
        ["ID", chapter.id], ["编码", chapter.code], ["排序", chapter.sort_order],
        ["所属教材ID", chapter.textbook_id],
        ["父级章节ID", chapter.parent_id == null ? "—" : chapter.parent_id]
      ];
      var kv = el("dl", "dcc-kv");
      meta.forEach(function (pair) {
        kv.appendChild(el("dt", "", pair[0]));
        kv.appendChild(el("dd", "", String(pair[1])));
      });
      detail.appendChild(kv);
      var list = children || [];
      detail.appendChild(el("h4", "dcc-subtitle", "下级节点（" + list.length + "）"));
      detail.appendChild(detailTable(
        ["名称", "编码", "排序"],
        list.map(function (node) {
          return [node.chapter.name, node.chapter.code, node.chapter.sort_order];
        })
      ));
    }

    function showBook(book, chapters) {
      detail.textContent = "";
      detail.appendChild(opsBar([
        actionButton("＋ 新增章", "给「" + (book.volume_name || book.name) + "」新增顶层章节",
          function () { window.DcChapterOps.add(null, chapters, book.id, load); })
      ]));
      detail.appendChild(el("p", "dcc-detail-name", book.volume_name || book.name));
      detail.appendChild(el("p", "dcc-detail-meta",
        "共 " + chapters.length + " 章 · " + countNodes(chapters) + " 个节点"));
      detail.appendChild(detailTable(
        ["章", "编码", "下级节点"],
        chapters.map(function (node) {
          return [node.chapter.name, node.chapter.code, countNodes(node.children)];
        })
      ));
    }

    function renderNodes(nodes, container, depth) {
      var ul = el("ul", "dcc-list");
      (nodes || []).forEach(function (node) {
        var chapter = node.chapter;
        var li = el("li", "dcc-item");
        var row = el("div", "dcc-row");
        row.style.paddingLeft = 2 + depth * 16 + "px";
        var children = node.children || [];
        if (children.length) {
          var caret = el("button", "dcc-caret", "▾");
          caret.type = "button";
          caret.setAttribute("aria-label", "展开或折叠「" + chapter.name + "」");
          caret.setAttribute("aria-expanded", "true");
          caret.addEventListener("click", function () {
            var open = caret.getAttribute("aria-expanded") === "true";
            caret.setAttribute("aria-expanded", open ? "false" : "true");
            caret.textContent = open ? "▸" : "▾";
            li.querySelector(".dcc-children").hidden = open;
          });
          row.appendChild(caret);
        } else {
          row.appendChild(el("span", "dcc-spacer", ""));
        }
        var button = el("button", "dcc-node", chapter.name);
        button.type = "button";
        button.addEventListener("click", function () {
          select(button);
          showChapter(chapter, children);
        });
        button.addEventListener("dblclick", function () {
          window.DcChapterOps.rename(chapter, load);
        });
        row.appendChild(button);
        li.appendChild(row);
        if (children.length) {
          var box = el("div", "dcc-children");
          renderNodes(children, box, depth + 1);
          li.appendChild(box);
        }
        ul.appendChild(li);
      });
      container.appendChild(ul);
    }

    function renderBooks() {
      tree.textContent = "";
      if (!books.length) {
        tree.appendChild(el("p", "dcc-empty", "该版本下没有册次。"));
        return;
      }
      var ul = el("ul", "dcc-list");
      books.forEach(function (item) {
        var book = item.textbook || {};
        var chapters = item.chapters || [];
        var li = el("li", "dcc-item dcc-book");
        var row = el("div", "dcc-row");
        if (chapters.length) {
          var caret = el("button", "dcc-caret", "▾");
          caret.type = "button";
          caret.setAttribute("aria-label", "展开或折叠「" + (book.volume_name || book.name) + "」");
          caret.setAttribute("aria-expanded", "true");
          caret.addEventListener("click", function () {
            var open = caret.getAttribute("aria-expanded") === "true";
            caret.setAttribute("aria-expanded", open ? "false" : "true");
            caret.textContent = open ? "▸" : "▾";
            li.querySelector(".dcc-children").hidden = open;
          });
          row.appendChild(caret);
        } else {
          row.appendChild(el("span", "dcc-spacer", ""));
        }
        var button = el("button", "dcc-node dcc-volume", book.volume_name || book.name);
        button.type = "button";
        button.addEventListener("click", function () {
          select(button);
          showBook(book, chapters);
        });
        row.appendChild(button);
        li.appendChild(row);
        var box = el("div", "dcc-children");
        renderNodes(chapters, box, 1);
        li.appendChild(box);
        ul.appendChild(li);
      });
      tree.appendChild(ul);
    }

    function reset() {
      books = [];
      tree.textContent = "";
      detail.textContent = "";
      detailTitle.textContent = "章节明细";
      detail.appendChild(el("p", "dcc-empty", "请先选择左侧册次或章节。"));
      select(null);
    }

    function load() {
      var versionId = ctx.globals.query().version_id;
      reset();
      if (!versionId) {
        state.textContent = "请先在右侧全局设置选择教材版本；选定后左侧立即展开真实章节树。";
        return;
      }
      state.textContent = "正在读取章节树…";
      window.DcClient.fetchJson(
        "/api/bank/engine/linkage/version-tree?version_id=" + encodeURIComponent(versionId)
      ).then(function (data) {
        if (!wrap.isConnected) return;
        books = data.items || [];
        var chapters = books.reduce(function (sum, item) {
          return sum + countNodes(item.chapters);
        }, 0);
        renderBooks();
        state.textContent = "共 " + books.length + " 册 · " + chapters + " 个章节节点";
      }).catch(function (error) {
        if (!wrap.isConnected) return;
        state.textContent = "章节树加载失败：" + error.message;
      });
    }

    function onGlobals() {
      if (!wrap.isConnected) {
        document.removeEventListener(window.DcGlobals.EVENT_NAME, onGlobals);
        return;
      }
      load();
    }
    document.addEventListener(window.DcGlobals.EVENT_NAME, onGlobals);
    load();
  }

  window.DcChapterTree = { mount: mount };
})();
