/**
 * 四栏联动 · 左栏教材章节树（阶段三，v9 起按版本分层）。
 * 由全局设置（DcGlobals.query().version_id）驱动：未选版本如实提示；
 * 选定版本后按「册次 → 章 → 节」展开（dim_textbook_versions → dim_textbooks
 * → dim_textbook_chapters，全部真实种子，绝不占位）。
 * 树默认全展开：册次 → 章 → 节一目了然；每个节点都是 44px 按钮，键盘可达。
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
    return nodes.reduce(function (sum, node) {
      return sum + 1 + countNodes(node.children || []);
    }, 0);
  }

  function toggle(li, caret) {
    var childList = li.querySelector(":scope > .dcl-tree-list");
    var open = caret.getAttribute("aria-expanded") === "true";
    caret.setAttribute("aria-expanded", open ? "false" : "true");
    caret.textContent = open ? "▸" : "▾";
    if (childList) childList.hidden = open;
  }

  function mount(body, ctx, hooks) {
    body.textContent = "";
    var state = el("p", "dcl-state", "");
    state.setAttribute("role", "status");
    state.setAttribute("aria-live", "polite");
    var box = el("div", "dcl-tree");
    body.appendChild(state);
    body.appendChild(box);
    var selectedButton = null;

    function select(chapterId, button) {
      if (selectedButton) {
        selectedButton.classList.remove("dcl-selected");
        selectedButton.setAttribute("aria-pressed", "false");
      }
      selectedButton = button || null;
      if (button) {
        button.classList.add("dcl-selected");
        button.setAttribute("aria-pressed", "true");
      }
      hooks.onSelect(chapterId);
    }

    function renderNodes(nodes, container, depth) {
      var ul = el("ul", "dcl-tree-list");
      ul.setAttribute("role", depth === 0 ? "tree" : "group");
      nodes.forEach(function (node) {
        var chapter = node.chapter;
        var li = el("li", "dcl-tree-li");
        li.setAttribute("role", "treeitem");
        var row = el("div", "dcl-tree-row");
        row.style.paddingLeft = 6 + depth * 16 + "px";
        var hasChildren = (node.children || []).length > 0;
        if (hasChildren) {
          var caret = el("button", "dcl-tree-caret", "▾");
          caret.type = "button";
          caret.setAttribute("aria-label", "展开或折叠「" + chapter.name + "」");
          caret.setAttribute("aria-expanded", "true");
          caret.addEventListener("click", function () { toggle(li, caret); });
          row.appendChild(caret);
        } else {
          row.appendChild(el("span", "dcl-tree-spacer", ""));
        }
        var button = el("button", "dcl-tree-node", chapter.name);
        button.type = "button";
        button.setAttribute("data-id", String(chapter.id));
        button.setAttribute("aria-pressed", "false");
        button.addEventListener("click", function () { select(chapter.id, button); });
        row.appendChild(button);
        li.appendChild(row);
        if (hasChildren) renderNodes(node.children, li, depth + 1);
        ul.appendChild(li);
      });
      container.appendChild(ul);
    }

    function renderBooks(books, container) {
      var ul = el("ul", "dcl-tree-list");
      ul.setAttribute("role", "tree");
      books.forEach(function (item) {
        var book = item.textbook || {};
        var chapters = item.chapters || [];
        var li = el("li", "dcl-tree-li dcl-tree-book");
        li.setAttribute("role", "treeitem");
        var row = el("div", "dcl-tree-row");
        row.style.paddingLeft = "6px";
        if (chapters.length) {
          var caret = el("button", "dcl-tree-caret", "▾");
          caret.type = "button";
          caret.setAttribute("aria-label", "展开或折叠「" + (book.volume_name || book.name) + "」");
          caret.setAttribute("aria-expanded", "true");
          caret.addEventListener("click", function () { toggle(li, caret); });
          row.appendChild(caret);
        } else {
          row.appendChild(el("span", "dcl-tree-spacer", ""));
        }
        var button = el("button", "dcl-tree-node dcl-tree-volume",
          book.volume_name || book.name);
        button.type = "button";
        button.setAttribute("data-textbook-id", String(book.id));
        if (chapters.length) {
          button.addEventListener("click", function () {
            toggle(li, li.querySelector(":scope > .dcl-tree-row > .dcl-tree-caret"));
          });
        }
        row.appendChild(button);
        li.appendChild(row);
        if (chapters.length) renderNodes(chapters, li, 1);
        ul.appendChild(li);
      });
      container.appendChild(ul);
    }

    function load() {
      var versionId = ctx.globals.query().version_id;
      select(null, null);
      box.textContent = "";
      if (!versionId) {
        state.textContent = "请先在右侧全局设置选择教材版本。";
        return;
      }
      state.textContent = "正在读取章节树…";
      window.DcClient.fetchJson(
        "/api/bank/engine/linkage/version-tree?version_id=" + encodeURIComponent(versionId)
      ).then(function (data) {
        if (!body.isConnected) return;
        var books = data.items || [];
        renderBooks(books, box);
        var chapters = books.reduce(function (sum, item) {
          return sum + countNodes(item.chapters || []);
        }, 0);
        state.textContent = "共 " + books.length + " 册 · " + chapters + " 章节";
      }).catch(function (error) {
        if (!body.isConnected) return;
        state.textContent = "章节树加载失败：" + error.message;
      });
    }

    function onGlobals() {
      if (!body.isConnected) {
        document.removeEventListener(window.DcGlobals.EVENT_NAME, onGlobals);
        return;
      }
      load();
    }
    document.addEventListener(window.DcGlobals.EVENT_NAME, onGlobals);
    load();
    return { load: load };
  }

  window.DcLinkTree = { mount: mount };
})();