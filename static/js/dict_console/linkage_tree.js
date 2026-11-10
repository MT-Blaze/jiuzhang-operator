/**
 * 四栏联动 · 左栏教材章节树（阶段三）。
 * 由全局设置（DcGlobals.query().textbook_id）驱动：未选教材如实提示，
 * 选了才拉真实章节层级（dim_textbook_chapters 种子，绝不占位）。
 * 树默认全展开：章 → 节一目了然；每节点都是 44px 按钮，键盘可达。
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
          caret.addEventListener("click", function () {
            var childList = li.querySelector(":scope > .dcl-tree-list");
            var open = caret.getAttribute("aria-expanded") === "true";
            caret.setAttribute("aria-expanded", open ? "false" : "true");
            caret.textContent = open ? "▸" : "▾";
            if (childList) childList.hidden = open;
          });
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

    function load() {
      var bookId = ctx.globals.query().textbook_id;
      select(null, null);
      box.textContent = "";
      if (!bookId) {
        state.textContent = "请先在右侧全局设置选择教材版本。";
        return;
      }
      state.textContent = "正在读取章节树…";
      window.DcClient.fetchJson(
        "/api/bank/engine/linkage/chapter-tree?textbook_id=" + encodeURIComponent(bookId)
      ).then(function (data) {
        if (!body.isConnected) return;
        renderNodes(data.items || [], box, 0);
        state.textContent = "共 " + countNodes(data.items || []) + " 章节";
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