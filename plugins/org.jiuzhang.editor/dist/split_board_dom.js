/**
 * split_board_dom.js —— 切题画板的骨架 DOM：遮罩、纸带页、总框层。
 *
 * 只造节点不记状态。跨页框选的前提在这里：所有页只是纸带上的竖段，
 * 所有框统一挂到覆盖整条纸带的 .ed-sb-layer，没有任何单页图层去裁剪它们。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var el = deps.el;
    var HANDLES = ["nw", "n", "ne", "e", "se", "s", "sw", "w"];

    function buildShell(pages) {
      var mask = el("div", "ed-sb-mask");
      mask.id = "edSbMask";
      var board = el("div", "ed-sb-board");
      board.id = "edSbBoard";
      board.setAttribute("role", "dialog");
      board.setAttribute("aria-modal", "true");
      board.setAttribute("aria-labelledby", "edSbTitle");
      board.tabIndex = -1;

      var head = el("header", "ed-sb-head");
      var title = el("h2", "ed-sb-title", "重新切题");
      title.id = "edSbTitle";
      var zoom = el("span", "ed-sb-zoom", "100%");
      var closeBtn = el("button", "ed-sb-close", "×");
      closeBtn.type = "button";
      closeBtn.title = "放弃修改并关闭（Esc）";
      closeBtn.setAttribute("aria-label", "放弃修改并关闭");
      head.appendChild(title);
      head.appendChild(el("span", "ed-sb-head-note", pages.length + " 页原卷"));
      head.appendChild(zoom);
      head.appendChild(closeBtn);
      var scroll = el("div", "ed-sb-scroll");
      scroll.id = "edSbScroll";
      scroll.tabIndex = 0;
      scroll.setAttribute("aria-label", "原卷长图：滚轮滚动，Ctrl+滚轮缩放");
      var pagesEl = el("div", "ed-sb-pages");
      pagesEl.id = "edSbPages";
      scroll.appendChild(pagesEl);

      var foot = el("footer", "ed-sb-foot");
      var count = el("p", "ed-sb-count", "没有改动");
      var actions = el("div", "ed-sb-actions");
      var cancel = el("button", "ed-sb-cancel", "放弃");
      cancel.type = "button";
      cancel.title = "放弃本次所有改动（Esc）";
      var ok = el("button", "ed-sb-ok", "⏎ 确认切分");
      ok.type = "button";
      ok.setAttribute("aria-label", "确认切分并提交");
      actions.appendChild(cancel);
      actions.appendChild(ok);
      foot.appendChild(el("p", "ed-sb-hint",
        "空白处拖拽新增 · 可跨页框 · 拖框移动 · 角上手柄缩放 · Delete 删框"));
      foot.appendChild(count);
      foot.appendChild(actions);
      board.appendChild(head);
      board.appendChild(scroll);
      board.appendChild(foot);
      mask.appendChild(board);
      return {
        mask: mask, board: board, head: head, scroll: scroll, pagesEl: pagesEl,
        zoom: zoom, close: closeBtn, cancel: cancel, ok: ok, count: count,
        layer: null
      };
    }

    /** 每页只负责撑出自己那段高度；框层之后统一铺满整条纸带。 */
    function buildPages(shell, pages) {
      var out = [];
      pages.forEach(function (page, index) {
        var pageRec = {
          index: index, page: page, pageNo: Number(page.page) || index + 1,
          width: Number(page.width), height: Number(page.height)
        };
        pageRec.wrap = el("div", "ed-sb-page");
        pageRec.wrap.setAttribute("data-page", String(pageRec.pageNo));
        pageRec.wrap.setAttribute("data-page-index", String(index));
        pageRec.wrap.style.aspectRatio = pageRec.width + " / " + pageRec.height;
        pageRec.img = el("img", "ed-sb-img");
        pageRec.img.src = String(page.uri || "");
        pageRec.img.alt = "原卷第 " + pageRec.pageNo + " 页";
        pageRec.img.draggable = false;
        pageRec.wrap.appendChild(pageRec.img);
        shell.pagesEl.appendChild(pageRec.wrap);
        out.push(pageRec);
      });
      var layer = el("div", "ed-sb-layer");
      layer.id = "edSbLayer";
      shell.pagesEl.appendChild(layer);
      shell.layer = layer;
      return out;
    }

    function boxTag(rec) {
      if (rec.isNew) return rec.crossPage ? "跨页待切" : "待切";
      if (rec.pending_id) return rec.crossPage ? "跨页题" : "已入池";
      return "仅坐标";
    }

    function buildBox(shell, rec, onRemove) {
      var box = el("div", "ed-sb-box");
      box.setAttribute("data-no", String(rec.no || ""));
      box.setAttribute("data-pending", rec.pending_id ? "on" : "off");
      box.setAttribute("data-new", rec.isNew ? "on" : "off");
      box.setAttribute("data-cross", rec.crossPage ? "on" : "off");
      if (rec.isNew) box.classList.add("is-new");
      var chip = el("span", "ed-sb-box-no", rec.isNew ? "新" : String(rec.no || "?"));
      var tag = el("span", "ed-sb-box-tag", boxTag(rec));
      var remove = el("button", "ed-sb-box-x", "×");
      remove.type = "button";
      remove.setAttribute("aria-label", "删除这个框（Delete）");
      remove.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        onRemove(rec);
      });
      box.appendChild(chip);
      box.appendChild(tag);
      box.appendChild(remove);
      HANDLES.forEach(function (key) {
        var handle = el("span", "ed-sb-handle");
        handle.setAttribute("data-handle", key);
        box.appendChild(handle);
      });
      shell.layer.appendChild(box);
      return box;
    }

    return {
      buildBox: buildBox,
      buildPages: buildPages,
      buildShell: buildShell,
      boxTag: boxTag
    };
  }

  global.JzoEditorSplitBoardDom = { create: create };
})(window);
