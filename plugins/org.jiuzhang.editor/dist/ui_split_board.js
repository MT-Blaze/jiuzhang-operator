/**
 * ui_split_board.js —— 悬浮切题画板：整页长图 + 框选编辑 + 确认/放弃。
 *
 * 老师点【重新切题】，遮罩落下、画板居中；空白拉框新增，框内拖动移动，
 * 角上手柄缩放，Delete/× 删框；Enter/【确认切分】提交，Esc/点遮罩放弃。
 * 坐标按原卷页图像素记账、框按百分比摆放：Ctrl+滚轮缩放时框线与题图无损同步。
 * 整块独立：删掉 index.html 那颗按钮、本脚本与 split_board.css 即下架。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var el = deps.el;
    var state = deps.coreState.state;
    var dock = deps.dock;
    var dockWarn = deps.dockWarn;
    var errorDetail = deps.errorDetail;
    var hostCall = deps.hostCall;
    var renderAll = deps.renderAll;
    var refreshBatches = deps.refreshBatches;
    var splitPageRegion = deps.splitPageRegion;
    var updatePageRegion = deps.updatePageRegion;
    var closeCrop = deps.closeCrop || function () {};
    var toast = deps.toast;
    var openButton = deps.dom.splitBoardBtnEl;

    var HANDLES = ["nw", "n", "ne", "e", "se", "s", "sw", "w"];
    var MIN_BOX_CSS = 6;          // 新框最小屏幕边长：手抖点一下不算框
    var MIN_REGION = 6;           // 画板上的框最小原图像素边长
    var ZOOM_MIN = 0.5;
    var ZOOM_MAX = 5;
    var session = null;

    function clamp(value, min, max) {
      if (max < min) return min;
      return Math.min(max, Math.max(min, value));
    }

    function round1(value) { return Math.round(value * 10) / 10; }

    function copyRegion(region) {
      return {
        no: Number(region && region.no) || 0,
        x: Number(region && region.x) || 0,
        y: Number(region && region.y) || 0,
        w: Number(region && region.w) || 0,
        h: Number(region && region.h) || 0,
        label: String((region && region.label) || ""),
        text: String((region && region.text) || ""),
        pending_id: String((region && region.pending_id) || "")
      };
    }

    function itemOf(pendingId) {
      if (!pendingId) return null;
      var items = Array.isArray(state.items) ? state.items : [];
      for (var index = 0; index < items.length; index += 1) {
        if (String(items[index].pendingId || "") === pendingId) return items[index];
      }
      return null;
    }
    // ---------- 画板骨架 ----------

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
        "空白处拖拽新增 · 拖框移动 · 角上手柄缩放 · Delete 删框"));
      foot.appendChild(count);
      foot.appendChild(actions);
      board.appendChild(head);
      board.appendChild(scroll);
      board.appendChild(foot);
      mask.appendChild(board);
      return {
        mask: mask, board: board, head: head, scroll: scroll, pagesEl: pagesEl,
        zoom: zoom, close: closeBtn, cancel: cancel, ok: ok, count: count
      };
    }

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
        pageRec.img = el("img", "ed-sb-img");
        pageRec.img.src = String(page.uri || "");
        pageRec.img.alt = "原卷第 " + pageRec.pageNo + " 页";
        pageRec.img.draggable = false;
        pageRec.img.style.aspectRatio = pageRec.width + " / " + pageRec.height;
        pageRec.layer = el("div", "ed-sb-layer");
        pageRec.wrap.appendChild(pageRec.img);
        pageRec.wrap.appendChild(pageRec.layer);
        shell.pagesEl.appendChild(pageRec.wrap);
        out.push(pageRec);
      });
      return out;
    }

    function open() {
      if (session) return;
      var pages = Array.isArray(state.pageImages) ? state.pageImages : [];
      if (!state.batchId) { toast("当前不在批次里，切不了题。", "error"); return; }
      if (!pages.length) { toast("这一批没有原卷页图，切题画板打不开。", "error"); return; }
      for (var index = 0; index < pages.length; index += 1) {
        if (!(Number(pages[index].width) > 0) || !(Number(pages[index].height) > 0)) {
          toast("原卷页图缺少像素尺寸，切题画板打不开。", "error"); return;
        }
      }
      closeCrop();
      // 插件在沙箱里只占中间一栏，先请宿主把本页签临时铺满工作区，遮罩才盖得住全屏。
      hostCall("stage.overlay", { on: true });
      var shell = buildShell(pages);
      var htmlEl = document.documentElement, bodyEl = document.body;
      var boardSession = {
        shell: shell, pages: buildPages(shell, pages),
        live: [], removed: [], selected: null, drag: null,
        scale: 1, baseWidth: 0, scrollTarget: 0, scrollFrame: 0,
        busy: false, partial: false, partialWarned: false, justMovedAt: 0,
        prevFocus: document.activeElement, prevHtmlOverflow: htmlEl.style.overflow,
        prevBodyOverflow: bodyEl.style.overflow, prevBodyPadding: bodyEl.style.paddingRight
      };
      session = boardSession;
      document.body.appendChild(shell.mask);
      // 锁死底层滚动：遮罩盖满视口，body/html 同时收走滚动条，滚轮只许画板吃。
      var gap = window.innerWidth - htmlEl.clientWidth;
      htmlEl.style.overflow = "hidden";
      bodyEl.style.overflow = "hidden";
      if (gap > 0) bodyEl.style.paddingRight = gap + "px";
      document.body.classList.add("ed-sb-locked");
      var rect = shell.board.getBoundingClientRect();
      shell.board.style.left = Math.max(8, (window.innerWidth - rect.width) / 2) + "px";
      shell.board.style.top = Math.max(8, (window.innerHeight - rect.height) / 2) + "px";
      shell.board.style.transform = "none";
      boardSession.baseWidth = fitWidth(boardSession);
      applyScale(boardSession);
      boardSession.pages.forEach(function (pageRec) {
        var regions = Array.isArray(pageRec.page.regions) ? pageRec.page.regions : [];
        regions.forEach(function (region) {
          var copy = copyRegion(region);
          if (copy.w > 0 && copy.h > 0) addBox(boardSession, pageRec, copy, false);
        });
      });
      refreshState(boardSession);
      bindBoard(boardSession);
      shell.board.focus();
    }

    function fitWidth(boardSession) {
      return Math.max(260, boardSession.shell.scroll.clientWidth - 44);
    }

    function applyScale(boardSession) {
      boardSession.shell.pagesEl.style.width =
        Math.round(boardSession.baseWidth * boardSession.scale) + "px";
      boardSession.shell.zoom.textContent = Math.round(boardSession.scale * 100) + "%";
      var max = boardSession.shell.scroll.scrollHeight - boardSession.shell.scroll.clientHeight;
      boardSession.scrollTarget = clamp(boardSession.scrollTarget, 0, Math.max(0, max));
    }
    // ---------- 框 ----------

    function paintBox(rec) {
      var page = rec.page;
      var region = rec.region;
      rec.el.style.left = (region.x / page.width * 100) + "%";
      rec.el.style.top = (region.y / page.height * 100) + "%";
      rec.el.style.width = (region.w / page.width * 100) + "%";
      rec.el.style.height = (region.h / page.height * 100) + "%";
    }

    function buildBox(rec) {
      var box = el("div", "ed-sb-box");
      box.setAttribute("data-no", String(rec.region.no || ""));
      box.setAttribute("data-pending", rec.region.pending_id ? "on" : "off");
      box.setAttribute("data-new", rec.isNew ? "on" : "off");
      if (rec.isNew) box.classList.add("is-new");
      var chip = el("span", "ed-sb-box-no", rec.isNew ? "新" : String(rec.region.no || "?"));
      var tag = el("span", "ed-sb-box-tag",
        rec.isNew ? "待切" : (rec.region.pending_id ? "已入池" : "仅坐标"));
      var remove = el("button", "ed-sb-box-x", "×");
      remove.type = "button";
      remove.setAttribute("aria-label", "删除这个框（Delete）");
      remove.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        removeBox(session, rec);
      });
      box.appendChild(chip);
      box.appendChild(tag);
      box.appendChild(remove);
      HANDLES.forEach(function (key) {
        var handle = el("span", "ed-sb-handle");
        handle.setAttribute("data-handle", key);
        box.appendChild(handle);
      });
      rec.el = box;
      rec.page.layer.appendChild(box);
      paintBox(rec);
    }

    function addBox(boardSession, pageRec, region, isNew) {
      var rec = { page: pageRec, pageIndex: pageRec.index, region: region,
        isNew: Boolean(isNew), modified: Boolean(isNew), deleted: false, el: null };
      buildBox(rec);
      boardSession.live.push(rec);
      return rec;
    }

    function removeBox(boardSession, rec) {
      if (!boardSession || !rec || rec.deleted) return;
      rec.deleted = true;
      if (rec.el && rec.el.parentNode) rec.el.parentNode.removeChild(rec.el);
      boardSession.live = boardSession.live.filter(function (item) { return item !== rec; });
      if (!rec.isNew) boardSession.removed.push(rec);
      if (boardSession.selected === rec) boardSession.selected = null;
      refreshState(boardSession);
    }

    function selectBox(boardSession, rec) {
      var previous = boardSession.selected;
      if (previous && previous.el) previous.el.classList.remove("is-selected");
      boardSession.selected = rec || null;
      if (rec && rec.el) rec.el.classList.add("is-selected");
    }

    function refreshState(boardSession) {
      var added = 0, adjusted = 0;
      boardSession.live.forEach(function (rec) {
        if (rec.isNew) added += 1;
        else if (rec.modified) adjusted += 1;
      });
      var removed = boardSession.removed.length;
      var shell = boardSession.shell;
      shell.count.textContent = (added || adjusted || removed)
        ? ("新增 " + added + " · 删除 " + removed + " · 微调 " + adjusted)
        : "没有改动";
      shell.count.setAttribute("data-added", String(added));
      shell.count.setAttribute("data-removed", String(removed));
      shell.count.setAttribute("data-adjusted", String(adjusted));
      if (!boardSession.busy) shell.ok.disabled = false;
    }

    function hasChanges(boardSession) {
      if (boardSession.removed.length) return true;
      return boardSession.live.some(function (rec) { return rec.isNew || rec.modified; });
    }
    // ---------- 坐标换算 ----------

    function pagePoint(pageRec, clientX, clientY) {
      var rect = pageRec.img.getBoundingClientRect();
      if (!rect.width || !rect.height) return null;
      return {
        x: clamp((clientX - rect.left) / rect.width * pageRec.width, 0, pageRec.width),
        y: clamp((clientY - rect.top) / rect.height * pageRec.height, 0, pageRec.height)
      };
    }

    function pageOfNode(node) {
      if (!session || !node || !node.closest) return null;
      var pageNode = node.closest(".ed-sb-page");
      if (!pageNode) return null;
      var index = Number(pageNode.getAttribute("data-page-index"));
      return isNaN(index) ? null : (session.pages[index] || null);
    }
    function recOfNode(node) {
      if (!session || !node || !node.closest) return null;
      var box = node.closest(".ed-sb-box");
      if (!box) return null;
      for (var index = 0; index < session.live.length; index += 1) {
        if (session.live[index].el === box) return session.live[index];
      }
      return null;
    }
    // ---------- 手势 ----------

    function bindBoard(boardSession) {
      var shell = boardSession.shell;
      shell.mask.addEventListener("wheel", function (event) {
        event.preventDefault();   // 遮罩上的滚轮也不许漏到底层页面
      }, { passive: false });
      shell.scroll.addEventListener("wheel", function (event) {
        onWheel(boardSession, event);
      }, { passive: false });
      shell.mask.addEventListener("click", function (event) {
        if (event.target === shell.mask && Date.now() - boardSession.justMovedAt > 250) {
          discard(boardSession);
        }
      });
      shell.close.addEventListener("click", function () { discard(boardSession); });
      shell.cancel.addEventListener("click", function () { discard(boardSession); });
      shell.ok.addEventListener("click", function () { save(boardSession); });
      shell.head.addEventListener("pointerdown", function (event) {
        if (event.button !== 0 || event.target.closest("button")) return;
        var rect = shell.board.getBoundingClientRect();
        boardSession.drag = {
          kind: "board",
          offsetX: event.clientX - rect.left,
          offsetY: event.clientY - rect.top
        };
        shell.board.classList.add("is-moving");
        event.preventDefault();
      });
      shell.pagesEl.addEventListener("pointerdown", function (event) {
        onPointerDown(boardSession, event);
      });
      window.addEventListener("pointermove", onPointerMove, true);
      window.addEventListener("pointerup", onPointerUp, true);
      window.addEventListener("pointercancel", onPointerUp, true);
      document.addEventListener("keydown", onKey, true);
      window.addEventListener("resize", onResize);
    }

    function unbindBoard(boardSession) {
      if (boardSession.shell.mask && boardSession.shell.mask.parentNode) {
        boardSession.shell.mask.parentNode.removeChild(boardSession.shell.mask);
      }
      document.body.classList.remove("ed-sb-locked");
      window.removeEventListener("pointermove", onPointerMove, true);
      window.removeEventListener("pointerup", onPointerUp, true);
      window.removeEventListener("pointercancel", onPointerUp, true);
      document.removeEventListener("keydown", onKey, true);
      window.removeEventListener("resize", onResize);
    }

    function onPointerDown(boardSession, event) {
      if (event.button !== 0 || boardSession.busy) return;
      var pageRec = pageOfNode(event.target);
      if (!pageRec) return;
      var rec = recOfNode(event.target);
      if (rec) {
        if (event.target.closest(".ed-sb-box-x")) {
          event.preventDefault();
          event.stopPropagation();
          removeBox(boardSession, rec);
          return;
        }
        selectBox(boardSession, rec);
        var point = pagePoint(pageRec, event.clientX, event.clientY);
        if (!point) return;
        var handle = event.target.closest(".ed-sb-handle");
        boardSession.drag = {
          kind: handle ? "resize" : "move",
          handle: handle ? String(handle.getAttribute("data-handle") || "") : "",
          rec: rec, page: pageRec,
          start: copyRegion(rec.region), startPoint: point, moved: false
        };
        event.preventDefault();
        return;
      }
      selectBox(boardSession, null);
      var start = pagePoint(pageRec, event.clientX, event.clientY);
      if (!start) return;
      var temp = el("div", "ed-sb-box is-new is-drawing");
      pageRec.layer.appendChild(temp);
      boardSession.drag = {
        kind: "create", page: pageRec, startPoint: start, el: temp, rect: null
      };
      event.preventDefault();
    }

    function onPointerMove(event) {
      if (!session || !session.drag) return;
      var drag = session.drag;
      if (drag.kind === "board") {
        var boardRect = session.shell.board.getBoundingClientRect();
        session.moved = true;
        session.shell.board.style.left = clamp(event.clientX - drag.offsetX,
          -(boardRect.width - 160), window.innerWidth - 160) + "px";
        session.shell.board.style.top = clamp(event.clientY - drag.offsetY,
          0, window.innerHeight - 60) + "px";
        return;
      }
      var point = pagePoint(drag.page, event.clientX, event.clientY);
      if (!point) return;
      if (drag.kind === "create") {
        drag.rect = {
          x: Math.min(drag.startPoint.x, point.x),
          y: Math.min(drag.startPoint.y, point.y),
          w: Math.abs(point.x - drag.startPoint.x),
          h: Math.abs(point.y - drag.startPoint.y)
        };
        paintRect(drag.el, drag.page, drag.rect);
        return;
      }
      if (drag.kind === "move") {
        var start = drag.start;
        drag.rec.region.x = clamp(start.x + point.x - drag.startPoint.x,
          0, drag.page.width - start.w);
        drag.rec.region.y = clamp(start.y + point.y - drag.startPoint.y,
          0, drag.page.height - start.h);
      } else {
        resizeRegion(drag, point);
      }
      drag.moved = true;
      if (!drag.rec.isNew) drag.rec.modified = true;
      paintBox(drag.rec);
      refreshState(session);
      event.preventDefault();
    }

    function paintRect(node, pageRec, rect) {
      node.style.left = (rect.x / pageRec.width * 100) + "%";
      node.style.top = (rect.y / pageRec.height * 100) + "%";
      node.style.width = (rect.w / pageRec.width * 100) + "%";
      node.style.height = (rect.h / pageRec.height * 100) + "%";
    }

    function resizeRegion(drag, point) {
      var start = drag.start;
      var page = drag.page;
      var handle = drag.handle;
      var left = start.x;
      var top = start.y;
      var right = start.x + start.w;
      var bottom = start.y + start.h;
      if (handle.indexOf("w") >= 0) left = clamp(point.x, 0, right - MIN_REGION);
      if (handle.indexOf("e") >= 0) right = clamp(point.x, left + MIN_REGION, page.width);
      if (handle.indexOf("n") >= 0) top = clamp(point.y, 0, bottom - MIN_REGION);
      if (handle.indexOf("s") >= 0) bottom = clamp(point.y, top + MIN_REGION, page.height);
      drag.rec.region.x = left;
      drag.rec.region.y = top;
      drag.rec.region.w = right - left;
      drag.rec.region.h = bottom - top;
    }

    function onPointerUp(event) {
      if (!session || !session.drag) return;
      var drag = session.drag;
      session.drag = null;
      session.shell.board.classList.remove("is-moving");
      if (drag.kind === "board") {
        session.justMovedAt = Date.now();
        return;
      }
      if (drag.kind === "create") {
        var rect = drag.el.getBoundingClientRect();
        if (drag.el.parentNode) drag.el.parentNode.removeChild(drag.el);
        if (!drag.rect || rect.width < MIN_BOX_CSS || rect.height < MIN_BOX_CSS) return;
        addBox(session, drag.page, {
          no: 0, x: round1(drag.rect.x), y: round1(drag.rect.y),
          w: round1(drag.rect.w), h: round1(drag.rect.h),
          label: "", text: "", pending_id: ""
        }, true);
        refreshState(session);
        return;
      }
      if (!drag.moved) return;
      // 手一松就把坐标收成一位小数：与底座落库口径一致，也免得浮点尾数乱跳。
      var region = drag.rec.region;
      region.x = round1(clamp(region.x, 0, drag.page.width - region.w));
      region.y = round1(clamp(region.y, 0, drag.page.height - region.h));
      region.w = round1(region.w);
      region.h = round1(region.h);
      paintBox(drag.rec);
      event.preventDefault();
    }

    function onWheel(boardSession, event) {
      event.preventDefault();
      if (boardSession.busy) return;
      if (event.ctrlKey || event.metaKey) {
        zoomAt(boardSession, Math.exp(-event.deltaY * 0.0015),
          event.clientX, event.clientY);
        return;
      }
      var delta = event.deltaY;
      if (event.deltaMode === 1) delta *= 16;
      else if (event.deltaMode === 2) delta *= boardSession.shell.scroll.clientHeight;
      if (!boardSession.scrollFrame) {
        boardSession.scrollTarget = boardSession.shell.scroll.scrollTop;
      }
      var max = boardSession.shell.scroll.scrollHeight - boardSession.shell.scroll.clientHeight;
      boardSession.scrollTarget = clamp(boardSession.scrollTarget + delta, 0, Math.max(0, max));
      startScroll(boardSession);
    }

    function startScroll(boardSession) {
      if (boardSession.scrollFrame) return;
      var step = function () {
        boardSession.scrollFrame = 0;
        if (session !== boardSession) return;
        var scroll = boardSession.shell.scroll;
        var diff = boardSession.scrollTarget - scroll.scrollTop;
        if (Math.abs(diff) < 0.5) { scroll.scrollTop = boardSession.scrollTarget; return; }
        scroll.scrollTop += diff * 0.32;
        boardSession.scrollFrame = window.requestAnimationFrame(step);
      };
      boardSession.scrollFrame = window.requestAnimationFrame(step);
    }

    /** Ctrl+滚轮：以鼠标下的原图点为锚，缩放前后该点纹丝不动。 */
    function zoomAt(boardSession, factor, clientX, clientY) {
      var next = clamp(boardSession.scale * factor, ZOOM_MIN, ZOOM_MAX);
      if (Math.abs(next - boardSession.scale) < 0.001) return;
      var before = boardSession.shell.pagesEl.getBoundingClientRect();
      var oldScale = boardSession.scale;
      var pointX = (clientX - before.left) / oldScale;
      var pointY = (clientY - before.top) / oldScale;
      boardSession.scale = next;
      applyScale(boardSession);
      var after = boardSession.shell.pagesEl.getBoundingClientRect();
      var scroll = boardSession.shell.scroll;
      scroll.scrollLeft += after.left + pointX * next - clientX;
      scroll.scrollTop += after.top + pointY * next - clientY;
      boardSession.scrollTarget = scroll.scrollTop;
    }

    function onResize() {
      if (!session) return;
      var boardRect = session.shell.board.getBoundingClientRect();
      // 宿主刚把画布铺满、或老师改了窗口大小：没亲手拖过画板就重新居中。
      if (!session.moved) {
        session.shell.board.style.left = Math.max(8, (window.innerWidth - boardRect.width) / 2) + "px";
        session.shell.board.style.top = Math.max(8, (window.innerHeight - boardRect.height) / 2) + "px";
      }
      session.shell.board.style.left = clamp(
        parseFloat(session.shell.board.style.left) || 0, -(boardRect.width - 160),
        Math.max(0, window.innerWidth - 160)) + "px";
      session.shell.board.style.top = clamp(
        parseFloat(session.shell.board.style.top) || 0, 0,
        Math.max(0, window.innerHeight - 60)) + "px";
      session.baseWidth = fitWidth(session);
      applyScale(session);
    }
    // ---------- 键盘 ----------

    function onKey(event) {
      if (!session) return;
      if (event.key === "Tab") {
        var list = Array.prototype.slice.call(session.shell.board.querySelectorAll(
          "button:not([disabled]), [tabindex='0']"
        )).filter(function (node) { return node.offsetParent !== null; });
        if (!list.length) { event.preventDefault(); session.shell.board.focus(); return; }
        var first = list[0];
        var last = list[list.length - 1];
        if (event.shiftKey && (document.activeElement === first
            || document.activeElement === session.shell.board)) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
        return;
      }
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        discard(session);
        return;
      }
      if (event.key === "Enter") {
        event.preventDefault();
        event.stopPropagation();
        save(session);
        return;
      }
      if (event.key === "Delete" || event.key === "Backspace") {
        if (!session.selected) return;
        event.preventDefault();
        event.stopPropagation();
        removeBox(session, session.selected);
      }
    }
    // ---------- 放弃 / 确认 ----------

    function discard(boardSession) {
      if (boardSession.busy || boardSession !== session) return;
      if (boardSession.partial && !boardSession.partialWarned) {
        boardSession.partialWarned = true;
        toast("已有改动写进了中转站；再按一次 Esc 仍可关闭，但建议按【确认切分】收尾。", "error"); return;
      }
      close();
      dock(boardSession.partial
        ? "切题画板已关闭：此前的部分改动已经落库。"
        : "已放弃本次切题改动，原卷一个字节都没动。");
    }

    function close() {
      var boardSession = session;
      if (!boardSession) return;
      session = null;
      hostCall("stage.overlay", { on: false }).catch(function () { /* 宿主没这口子就维持原样 */ });
      if (boardSession.scrollFrame) {
        window.cancelAnimationFrame(boardSession.scrollFrame);
        boardSession.scrollFrame = 0;
      }
      unbindBoard(boardSession);
      document.documentElement.style.overflow = boardSession.prevHtmlOverflow || "";
      document.body.style.overflow = boardSession.prevBodyOverflow || "";
      document.body.style.paddingRight = boardSession.prevBodyPadding || "";
      if (boardSession.prevFocus && boardSession.prevFocus.focus
          && document.contains(boardSession.prevFocus)) {
        try { boardSession.prevFocus.focus(); } catch (error) { /* 焦点回不去不影响收摊 */ }
      }
    }

    function setBusy(boardSession, busy, text) {
      boardSession.busy = busy;
      boardSession.shell.board.classList.toggle("is-busy", busy);
      boardSession.shell.ok.disabled = busy;
      boardSession.shell.cancel.disabled = busy;
      boardSession.shell.close.disabled = busy;
      if (busy && text) boardSession.shell.count.textContent = text;
      if (!busy && !text) refreshState(boardSession);
    }

    /** 最终页图清单：题号按页内自上而下、自左而右重排，坐标收一位小数。 */
    function collectPages(boardSession) {
      var source = Array.isArray(state.pageImages) ? state.pageImages : [];
      var pages = [];
      boardSession.pages.forEach(function (pageRec, index) {
        var original = source[index] || {};
        var live = boardSession.live.filter(function (rec) {
          return rec.pageIndex === index && !rec.deleted;
        });
        live.sort(function (a, b) {
          return a.region.y !== b.region.y ? a.region.y - b.region.y : a.region.x - b.region.x;
        });
        var regions = live.map(function (rec, order) {
          var region = rec.region;
          region.no = order + 1;
          var out = {
            no: region.no,
            x: round1(clamp(region.x, 0, pageRec.width)),
            y: round1(clamp(region.y, 0, pageRec.height)),
            w: round1(clamp(region.w, 0, pageRec.width)),
            h: round1(clamp(region.h, 0, pageRec.height)),
            label: region.label,
            text: region.text
          };
          if (region.pending_id) out.pending_id = region.pending_id;
          return out;
        });
        pages.push({
          name: String(original.name || ""), uri: String(original.uri || ""),
          page: Number(original.page) || pageRec.pageNo,
          width: pageRec.width, height: pageRec.height, regions: regions
        });
      });
      return pages;
    }

    function save(boardSession) {
      if (!boardSession || boardSession !== session || boardSession.busy) return;
      if (!hasChanges(boardSession)) {
        close();
        dock("切题画板没有改动，已关闭。");
        return;
      }
      var added = 0;
      var adjusted = 0;
      boardSession.live.forEach(function (rec) {
        if (rec.isNew) added += 1;
        else if (rec.modified) adjusted += 1;
      });
      var removed = boardSession.removed.length;
      setBusy(boardSession, true, "正在提交…");

      var chain = Promise.resolve();
      // 先补新框：新题一旦建成，后面就算某一步失败，重试也不会重复建题。
      boardSession.live.forEach(function (rec) {
        if (!rec.isNew || rec.region.pending_id) return;
        chain = chain.then(function () {
          return createFromBox(rec);
        });
      });
      // 再按新坐标重切已入池的题图。
      boardSession.live.forEach(function (rec) {
        if (rec.isNew || !rec.modified || rec.updated || !rec.region.pending_id) return;
        var item = itemOf(rec.region.pending_id);
        if (!item) return;
        chain = chain.then(function () {
          return updatePageRegion(item, rec.region, { page: rec.page.pageNo })
            .then(function () {
              rec.updated = true;
              boardSession.partial = true;
            });
        });
      });
      // 最后删题：删除不可逆，放在所有新增/重切之后。
      boardSession.removed.forEach(function (rec) {
        if (rec.deletedOnServer) return;
        var item = itemOf(rec.region.pending_id);
        if (!item || !item.pendingId) return;
        chain = chain.then(function () {
          return hostCall("pending.delete", { pending_id: item.pendingId })
            .then(function () {
              rec.deletedOnServer = true;
              boardSession.partial = true;
              state.items = state.items.filter(function (entry) { return entry !== item; });
            });
        });
      });

      chain.then(function () {
        var pages = collectPages(boardSession);
        for (var index = 0; index < pages.length; index += 1) {
          if (!pages[index].name) throw new Error("原卷页图缺少文件名，坐标写不回去");
        }
        return hostCall("pending.set_pages", {
          batch_id: String(state.batchId || ""),
          page_images: pages
        }).then(function (result) {
          var saved = (result && Array.isArray(result.page_images)) ? result.page_images : [];
          state.pageImages = saved.length ? saved : pages;
          if (state.active >= state.items.length) {
            state.active = Math.max(0, state.items.length - 1);
          }
          close();
          renderAll();
          refreshBatches();
          dock("切题画板已提交：新增 " + added + " 框、删除 " + removed
            + " 框、微调 " + adjusted + " 框。");
        });
      }).catch(function (error) {
        setBusy(boardSession, false);
        dockWarn("切题画板的改动没存住：" + ((error && error.message) || "未知原因"),
          errorDetail(error));
        toast("切题改动没存住，画板还开着，可以再按一次确认。", "error");
      });
    }

    function createFromBox(rec) {
      var page = state.pageImages[rec.pageIndex] || {};
      var pseudo = {
        batchId: String(state.batchId || ""), question: {},
        pageImage: { uri: String(page.uri || ""), page: rec.page.pageNo }
      };
      return splitPageRegion(pseudo, rec.region, { page: rec.page.pageNo })
        .then(function (created) {
          if (!created || !created.pendingId) throw new Error("新框没能生成待审题");
          rec.region.pending_id = created.pendingId;
          session.partial = true;
          return created;
        });
    }

    if (openButton) {
      openButton.addEventListener("click", function (event) {
        event.preventDefault();
        open();
      });
    }

    return {
      open: open,
      close: close,
      isOpen: function () { return Boolean(session); }
    };
  }

  global.JzoEditorSplitBoard = { create: create };
})(window);
