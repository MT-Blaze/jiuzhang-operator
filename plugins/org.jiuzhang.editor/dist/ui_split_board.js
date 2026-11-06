/**
 * ui_split_board.js —— 悬浮切题画板：整条纸带 + 框选编辑 + 确认/放弃。
 *
 * 所有原卷页接成一条纸带，画板本身就是屏幕：框只认纸带坐标，一次可以框穿两页；
 * 落到存储层时才按页界线机械拆块。Ctrl+滚轮缩放比例记在宿主数据舱里，换批次也生效。
 * 整块独立：删掉 index.html 那颗按钮、本脚本与三份 split_board_* 模块即下架。
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
    var splitSpanRegion = deps.splitSpanRegion || function () {
      return Promise.reject(new Error("跨页切题通道没有接上"));
    };
    var updateSpanRegion = deps.updateSpanRegion || function () {
      return Promise.reject(new Error("跨页重切通道没有接上"));
    };
    var closeCrop = deps.closeCrop || function () {};
    var toast = deps.toast;
    var openButton = deps.dom.splitBoardBtnEl;
    var boardDom = window.JzoEditorSplitBoardDom
      ? window.JzoEditorSplitBoardDom.create({ el: el }) : null;
    var geom = window.JzoEditorSplitBoardGeom
      ? window.JzoEditorSplitBoardGeom.create() : null;

    var MIN_BOX_CSS = 6;          // 新框最小屏幕边长：手抖点一下不算框
    var MIN_REGION = 6;           // 纸带坐标里的最小边长
    var ZOOM_MIN = 0.2;
    var ZOOM_MAX = 5;
    var ZOOM_KEY = "split_board_zoom";
    var ZOOM_SAVE_MS = 260;
    var zoomStore = window.JzoEditorSplitBoardZoom
      ? window.JzoEditorSplitBoardZoom.create({
        hostCall: hostCall, key: ZOOM_KEY, min: ZOOM_MIN, max: ZOOM_MAX, delay: ZOOM_SAVE_MS
      }) : null;
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

    function copyRect(rect) {
      return {
        x: Number(rect && rect.x) || 0,
        y: Number(rect && rect.y) || 0,
        w: Number(rect && rect.w) || 0,
        h: Number(rect && rect.h) || 0
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

    function open() {
      if (session) return;
      if (!geom || !boardDom) { toast("切题画板的模块没加载全，画板打不开。", "error"); return; }
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
      var shell = boardDom.buildShell(pages);
      var htmlEl = document.documentElement, bodyEl = document.body;
      var boardSession = {
        shell: shell, pages: boardDom.buildPages(shell, pages),
        rows: [], stripHeight: 0,
        live: [], removed: [], selected: null, drag: null,
        scale: 1, baseWidth: 0, scrollTarget: 0, scrollFrame: 0,
        zoomTouched: false,
        busy: false, partial: false, partialWarned: false,
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
      boardSession.baseWidth = fitWidth(boardSession);
      layoutStrip(boardSession);
      loadRegions(boardSession);
      applyScale(boardSession);
      refreshState(boardSession);
      bindBoard(boardSession);
      shell.board.focus();
      // 缩放比例存在宿主数据舱里：读失败、读回怪值都只退 100%，画板照常能用。
      if (zoomStore) {
        zoomStore.read().then(function (scale) {
          if (session !== boardSession || boardSession.zoomTouched) return;
          if (!isFinite(scale) || !(scale > 0)) return;
          boardSession.scale = clamp(scale, ZOOM_MIN, ZOOM_MAX);
          applyScale(boardSession);
        });
      }
    }

    function fitWidth(boardSession) {
      // 纸带宽度就是滚动区宽度：画板没有边框，题图直接顶到屏幕两侧。
      return Math.max(260, boardSession.shell.scroll.clientWidth);
    }

    function layoutStrip(boardSession) {
      boardSession.rows = geom.layout(boardSession.pages, boardSession.baseWidth);
      boardSession.stripHeight = geom.stripHeight(boardSession.rows);
    }

    function applyScale(boardSession) {
      boardSession.shell.pagesEl.style.width =
        Math.round(boardSession.baseWidth * boardSession.scale) + "px";
      boardSession.shell.zoom.textContent = Math.round(boardSession.scale * 100) + "%";
      repaintAll(boardSession);
      var max = boardSession.shell.scroll.scrollHeight - boardSession.shell.scroll.clientHeight;
      boardSession.scrollTarget = clamp(boardSession.scrollTarget, 0, Math.max(0, max));
    }

    function repaintAll(boardSession) {
      boardSession.live.forEach(function (rec) { paintBox(boardSession, rec); });
    }
    // ---------- 框 ----------

    /** 框按「纸带基准像素 × 当前缩放」落位；跨页框就是一条长矩形，没有页缝。 */
    function paintBox(boardSession, rec) {
      var scale = boardSession.scale;
      rec.el.style.left = (rec.rect.x * scale) + "px";
      rec.el.style.top = (rec.rect.y * scale) + "px";
      rec.el.style.width = (rec.rect.w * scale) + "px";
      rec.el.style.height = (rec.rect.h * scale) + "px";
    }

    function addBox(boardSession, rect, meta, isNew) {
      var pieces = geom.piecesOf(rect, boardSession.pages, boardSession.rows,
        boardSession.baseWidth);
      var rec = {
        rect: copyRect(rect),
        pending_id: String((meta && meta.pending_id) || ""),
        no: Number(meta && meta.no) || 0,
        label: String((meta && meta.label) || ""),
        text: String((meta && meta.text) || ""),
        crossPage: pieces.length > 1,
        isNew: Boolean(isNew), modified: Boolean(isNew), deleted: false, el: null
      };
      rec.el = boardDom.buildBox(boardSession.shell, rec, function (target) {
        removeBox(session, target);
      });
      paintBox(boardSession, rec);
      boardSession.live.push(rec);
      return rec;
    }

    function loadRegions(boardSession) {
      var groups = [], byPending = {};
      boardSession.pages.forEach(function (pageRec, pageIndex) {
        var regions = Array.isArray(pageRec.page.regions) ? pageRec.page.regions : [];
        regions.forEach(function (region) {
          var copy = copyRegion(region);
          if (!(copy.w > 0 && copy.h > 0)) return;
          var rect = geom.rectOfRegion(pageIndex, copy, boardSession.pages,
            boardSession.rows, boardSession.baseWidth);
          if (!rect) return;
          if (!copy.pending_id) {
            addBox(boardSession, rect, {
              no: copy.no, label: copy.label, text: copy.text, pending_id: ""
            }, false);
            return;
          }
          // 同一个待审题被跨页拆成几块时，重开画板要还原成一只整框。
          var group = byPending[copy.pending_id];
          if (!group) {
            group = { pending_id: copy.pending_id, pieces: [], no: copy.no,
              label: copy.label, text: copy.text };
            byPending[copy.pending_id] = group;
            groups.push(group);
          }
          group.pieces.push({ pageIndex: pageIndex, region: copy });
          if (!group.no && copy.no) group.no = copy.no;
          if (!group.label && copy.label) group.label = copy.label;
          if (!group.text && copy.text) group.text = copy.text;
        });
      });
      groups.forEach(function (group) {
        group.pieces.sort(function (a, b) { return a.pageIndex - b.pageIndex; });
        var rect = geom.rectOfPieces(group.pieces, boardSession.pages,
          boardSession.rows, boardSession.baseWidth);
        if (!rect) return;
        addBox(boardSession, rect, {
          no: group.no, label: group.label, text: group.text,
          pending_id: group.pending_id
        }, false);
      });
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

    /** 鼠标位置 → 纸带基准坐标；整条纸带只有一个坐标系，无论落在哪一页。 */
    function pointOf(boardSession, clientX, clientY) {
      var rect = boardSession.shell.pagesEl.getBoundingClientRect();
      return geom.point(rect, boardSession.scale, clientX, clientY,
        boardSession.baseWidth, boardSession.stripHeight);
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
      shell.close.addEventListener("click", function () { discard(boardSession); });
      shell.cancel.addEventListener("click", function () { discard(boardSession); });
      shell.ok.addEventListener("click", function () { save(boardSession); });
      shell.layer.addEventListener("pointerdown", function (event) {
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
      var rec = recOfNode(event.target);
      if (rec) {
        if (event.target.closest(".ed-sb-box-x")) {
          event.preventDefault();
          event.stopPropagation();
          removeBox(boardSession, rec);
          return;
        }
        selectBox(boardSession, rec);
        var point = pointOf(boardSession, event.clientX, event.clientY);
        if (!point) return;
        var handle = event.target.closest(".ed-sb-handle");
        boardSession.drag = {
          kind: handle ? "resize" : "move",
          handle: handle ? String(handle.getAttribute("data-handle") || "") : "",
          rec: rec, start: copyRect(rec.rect), startPoint: point, moved: false
        };
        event.preventDefault();
        return;
      }
      selectBox(boardSession, null);
      var start = pointOf(boardSession, event.clientX, event.clientY);
      if (!start) return;
      var temp = el("div", "ed-sb-box is-new is-drawing");
      boardSession.shell.layer.appendChild(temp);
      boardSession.drag = {
        kind: "create", startPoint: start, el: temp, rect: null
      };
      event.preventDefault();
    }

    function onPointerMove(event) {
      if (!session || !session.drag) return;
      var drag = session.drag;
      var point = pointOf(session, event.clientX, event.clientY);
      if (!point) return;
      if (drag.kind === "create") {
        drag.rect = geom.clampRect(geom.rectBetween(drag.startPoint, point),
          session.baseWidth, session.stripHeight);
        paintRect(session, drag.el, drag.rect);
        event.preventDefault();
        return;
      }
      if (drag.kind === "move") {
        var start = drag.start;
        drag.rec.rect.x = clamp(start.x + point.x - drag.startPoint.x,
          0, Math.max(0, session.baseWidth - start.w));
        drag.rec.rect.y = clamp(start.y + point.y - drag.startPoint.y,
          0, Math.max(0, session.stripHeight - start.h));
      } else {
        resizeRect(drag, point, session);
      }
      drag.moved = true;
      if (!drag.rec.isNew) drag.rec.modified = true;
      paintBox(session, drag.rec);
      refreshState(session);
      event.preventDefault();
    }

    function paintRect(boardSession, node, rect) {
      var scale = boardSession.scale;
      node.style.left = (rect.x * scale) + "px";
      node.style.top = (rect.y * scale) + "px";
      node.style.width = (rect.w * scale) + "px";
      node.style.height = (rect.h * scale) + "px";
    }

    function resizeRect(drag, point, boardSession) {
      var start = drag.start;
      var handle = drag.handle;
      var left = start.x;
      var top = start.y;
      var right = start.x + start.w;
      var bottom = start.y + start.h;
      if (handle.indexOf("w") >= 0) left = clamp(point.x, 0, right - MIN_REGION);
      if (handle.indexOf("e") >= 0) right = clamp(point.x, left + MIN_REGION, boardSession.baseWidth);
      if (handle.indexOf("n") >= 0) top = clamp(point.y, 0, bottom - MIN_REGION);
      if (handle.indexOf("s") >= 0) bottom = clamp(point.y, top + MIN_REGION, boardSession.stripHeight);
      drag.rec.rect = {
        x: left, y: top, w: right - left, h: bottom - top
      };
    }

    function onPointerUp(event) {
      if (!session || !session.drag) return;
      var drag = session.drag;
      session.drag = null;
      if (drag.kind === "create") {
        var box = drag.el.getBoundingClientRect();
        if (drag.el.parentNode) drag.el.parentNode.removeChild(drag.el);
        if (!drag.rect) return;
        if (box.width < MIN_BOX_CSS || box.height < MIN_BOX_CSS) return;
        var created = addBox(session, roundRect(drag.rect), {
          no: 0, label: "", text: "", pending_id: ""
        }, true);
        selectBox(session, created);
        refreshState(session);
        return;
      }
      if (!drag.moved) return;
      // 手一松就把坐标收成一位小数：与底座落库口径一致，也免得浮点尾数乱跳。
      drag.rec.rect = roundRect(drag.rec.rect);
      paintBox(session, drag.rec);
      if (!drag.rec.isNew) drag.rec.modified = true;
      refreshState(session);
      event.preventDefault();
    }

    function roundRect(rect) {
      return {
        x: round1(clamp(rect.x, 0, session.baseWidth)),
        y: round1(clamp(rect.y, 0, session.stripHeight)),
        w: round1(rect.w),
        h: round1(rect.h)
      };
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

    /** Ctrl+滚轮：以鼠标下的纸带点为锚，缩放前后该点纹丝不动。 */
    function zoomAt(boardSession, factor, clientX, clientY) {
      var next = clamp(boardSession.scale * factor, ZOOM_MIN, ZOOM_MAX);
      if (Math.abs(next - boardSession.scale) < 0.001) return;
      var before = boardSession.shell.pagesEl.getBoundingClientRect();
      var oldScale = boardSession.scale;
      var pointX = (clientX - before.left) / oldScale;
      var pointY = (clientY - before.top) / oldScale;
      boardSession.scale = next;
      boardSession.zoomTouched = true;
      applyScale(boardSession);
      var after = boardSession.shell.pagesEl.getBoundingClientRect();
      var scroll = boardSession.shell.scroll;
      scroll.scrollLeft += after.left + pointX * next - clientX;
      scroll.scrollTop += after.top + pointY * next - clientY;
      boardSession.scrollTarget = scroll.scrollTop;
      if (zoomStore) zoomStore.queue(boardSession.scale);
    }

    function onResize() {
      if (!session) return;
      var nextBase = fitWidth(session);
      if (nextBase === session.baseWidth) return;
      var ratio = nextBase / session.baseWidth;
      session.live.forEach(function (rec) {
        rec.rect.x *= ratio;
        rec.rect.y *= ratio;
        rec.rect.w *= ratio;
        rec.rect.h *= ratio;
      });
      session.baseWidth = nextBase;
      layoutStrip(session);
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
      if (boardSession.zoomTouched && zoomStore) zoomStore.flush(boardSession.scale);
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
    // ---------- 落库 ----------

    function pagePieces(boardSession, rec) {
      var out = [];
      geom.piecesOf(rec.rect, boardSession.pages, boardSession.rows,
        boardSession.baseWidth).forEach(function (piece) {
        var pageRec = boardSession.pages[piece.pageIndex];
        var source = state.pageImages[piece.pageIndex] || {};
        out.push({
          pageIndex: piece.pageIndex,
          pageNo: pageRec.pageNo,
          uri: String(source.uri || ""),
          region: {
            no: 0,
            x: round1(piece.region.x),
            y: round1(piece.region.y),
            w: round1(piece.region.w),
            h: round1(piece.region.h),
            label: rec.label,
            text: rec.text
          }
        });
      });
      return out;
    }

    /** 最终页图清单：跨页框按页界线拆块，同一 pending_id 的块仍是同一道题。 */
    function collectPages(boardSession) {
      var source = Array.isArray(state.pageImages) ? state.pageImages : [];
      var buckets = boardSession.pages.map(function () { return []; });
      boardSession.live.forEach(function (rec) {
        if (rec.deleted) return;
        geom.piecesOf(rec.rect, boardSession.pages, boardSession.rows,
          boardSession.baseWidth).forEach(function (piece) {
          var pageRec = boardSession.pages[piece.pageIndex];
          var width = pageRec.width, height = pageRec.height;
          var w = round1(clamp(piece.region.w, 0, width));
          var h = round1(clamp(piece.region.h, 0, height));
          if (w < 4 || h < 4) return;   // 页缝上蹭出来的碎条不值得落库
          var region = {
            no: 0,
            x: round1(clamp(piece.region.x, 0, Math.max(0, width - w))),
            y: round1(clamp(piece.region.y, 0, Math.max(0, height - h))),
            w: w,
            h: h,
            label: rec.label,
            text: rec.text
          };
          if (rec.pending_id) region.pending_id = rec.pending_id;
          buckets[piece.pageIndex].push(region);
        });
      });
      return boardSession.pages.map(function (pageRec, index) {
        var original = source[index] || {};
        var regions = buckets[index];
        regions.sort(function (a, b) {
          return a.y !== b.y ? a.y - b.y : a.x - b.x;
        });
        regions.forEach(function (region, order) { region.no = order + 1; });
        return {
          name: String(original.name || ""), uri: String(original.uri || ""),
          page: Number(original.page) || pageRec.pageNo,
          width: pageRec.width, height: pageRec.height, regions: regions
        };
      });
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
        if (!rec.isNew || rec.pending_id) return;
        chain = chain.then(function () { return createFromBox(boardSession, rec); });
      });
      // 再按新坐标重切已入池的题图。
      boardSession.live.forEach(function (rec) {
        if (rec.isNew || !rec.modified || rec.updated || !rec.pending_id) return;
        chain = chain.then(function () { return updateBox(boardSession, rec); });
      });
      // 最后删题：删除不可逆，放在所有新增/重切之后。
      boardSession.removed.forEach(function (rec) {
        if (rec.deletedOnServer) return;
        var item = itemOf(rec.pending_id);
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

    function createFromBox(boardSession, rec) {
      var pieces = pagePieces(boardSession, rec);
      if (!pieces.length) return Promise.reject(new Error("这个框没有落到任何一页上"));
      var first = pieces[0];
      var page = state.pageImages[first.pageIndex] || {};
      var pseudo = {
        batchId: String(state.batchId || ""), question: {},
        pageImage: { uri: String(page.uri || ""), page: first.pageNo }
      };
      var task = pieces.length > 1
        ? splitSpanRegion(pseudo, pieces)
        : splitPageRegion(pseudo, pieces[0].region, { page: first.pageNo });
      return task.then(function (created) {
        if (!created || !created.pendingId) throw new Error("新框没能生成待审题");
        rec.pending_id = created.pendingId;
        boardSession.partial = true;
        return created;
      });
    }

    function updateBox(boardSession, rec) {
      var item = itemOf(rec.pending_id);
      if (!item) return Promise.resolve();
      var pieces = pagePieces(boardSession, rec);
      if (!pieces.length) return Promise.resolve();
      var task = pieces.length > 1
        ? updateSpanRegion(item, pieces)
        : updatePageRegion(item, pieces[0].region, { page: pieces[0].pageNo });
      return task.then(function () {
        rec.updated = true;
        boardSession.partial = true;
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
