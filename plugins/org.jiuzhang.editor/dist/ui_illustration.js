/**
 * ui_illustration.js —— 源码栏【添加配图】：原图变画板，框一块，双击确认
 * （终极军令 任务四；独立整块，连同 index.html 那颗按钮一起删即下架）。
 *
 * 与切图台（ui_crop.js）的分工：切图台管「这道题的图从哪来」，
 * 本模块管「题干/解析/选项里怎么长出一张配图」。画布、取图、裁像素复用
 * ui_crop 已经调好的底层（layoutCrop / cropPoint / cropRegionToDataUrl），
 * 不另造一套坐标换算。
 *
 * 插入规则（格式宪法）：
 *   题干/解析 —— \vspace{1ex} + \begin{center} 包住 \includegraphics；
 *   \item 选项 —— 只插 \includegraphics[width=0.2\textwidth]{...}，
 *                绝不补 \\，也绝不补 A./B. 之类的前缀。
 * 光标位置以老师在源码/卡片里最后一次落点为准，点按钮不会把它弄丢。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var clampValue = deps.clampValue;
    var coreState = deps.coreState;
    var cropApi = deps.cropApi;
    var dock = deps.dock;
    var dockWarn = deps.dockWarn;
    var el = deps.el;
    var errorDetail = deps.errorDetail;
    var fieldRanges = deps.fieldRanges;
    var growTextarea = deps.growTextarea;
    var hostCall = deps.hostCall;
    var itemImage = deps.itemImage;
    var onBoxInput = deps.onBoxInput;
    var onSourceInput = deps.onSourceInput;
    var state = coreState.state;
    var imageBodyEl = deps.dom.imageBodyEl;
    var sourceBodyEl = deps.dom.sourceBodyEl;
    var addButton = deps.dom.addIllustrationEl;

    var MIN_SIDE = 6;             // 最小选区边长（CSS 像素）
    var CENTER_WIDTH = "0.6\\textwidth";
    var OPTION_WIDTH = "0.2\\textwidth";
    var board = null;
    var caret = null;

    // ---------- 光标记忆：源码 textarea / 卡片输入框各自带 data-index、data-field ----------

    function nodeField(node) {
      if (!node || !node.getAttribute) return "";
      return node.getAttribute("data-field") == null ? "" : String(node.getAttribute("data-field"));
    }

    function nodeIndexOf(node) {
      if (!node || !node.getAttribute) return -1;
      var raw = node.getAttribute("data-index");
      if (raw == null) return -1;
      var index = Number(raw);
      return isNaN(index) || index < 0 ? -1 : index;
    }

    function rememberCaret(node) {
      var field = nodeField(node);
      var index = nodeIndexOf(node);
      if (!field || index < 0) return;
      if (node.tagName !== "TEXTAREA" && node.tagName !== "INPUT") return;
      var pos = node.getAttribute("data-pos");
      caret = {
        index: index,
        field: field,
        pos: pos == null ? null : Number(pos),
        start: Number(node.selectionStart) || 0,
        end: Number(node.selectionEnd) || 0
      };
    }

    function trackEvents() {
      ["focusin", "click", "keyup", "select", "input"].forEach(function (type) {
        sourceBodyEl.addEventListener(type, function (event) {
          rememberCaret(event.target);
        });
      });
    }

    /** 没落过光标时给一个诚实的默认落点：题干预设段的末尾，绝不插到源码环境外壳上。 */
    function fallbackCaret() {
      var index = Number(state.active) || 0;
      var item = state.items[index];
      if (!item) return null;
      if (state.format === "boxed") {
        var box = sourceBodyEl.querySelector(
          '.ed-box-area[data-index="' + index + '"][data-field="stem"]');
        if (!box) return null;
        var at = String(box.value || "").length;
        return { index: index, field: "stem", pos: null, start: at, end: at };
      }
      var text = String(item.source || "");
      var ranges = fieldRanges(text);
      var offset = ranges.stem ? ranges.stem.end : text.length;
      return { index: index, field: "source", pos: null, start: offset, end: offset };
    }

    function usableCaret() {
      var info = caret;
      if (info && state.items[info.index]) {
        var live = info.field === "source" ? sourceNode(info.index) : boxNode(info);
        if (live) return info;
      }
      return fallbackCaret();
    }

    // ---------- 画板 ----------

    function sourceNode(index) {
      return sourceBodyEl.querySelector('.ed-src-area[data-index="' + index + '"]');
    }

    function boxNode(info) {
      var selector = '.ed-box-area[data-index="' + info.index + '"][data-field="' + info.field + '"]';
      if (info.pos != null) selector += '[data-pos="' + info.pos + '"]';
      return sourceBodyEl.querySelector(selector);
    }

    /** 纯图片卷的左栏是整页阅读器（data-page-index），普通批次则按题号一格。 */
    function findSpot(index, item) {
      var cell = null;
      if (state.scanBatch && item.pageImage) {
        var pages = Array.isArray(state.pageImages) ? state.pageImages : [];
        var pageNo = Number(item.pageImage.page) || 0;
        var pageIndex = -1;
        for (var i = 0; i < pages.length; i += 1) {
          if (Number(pages[i] && pages[i].page) === pageNo) { pageIndex = i; break; }
        }
        if (pageIndex < 0) pageIndex = Math.min(index, Math.max(0, pages.length - 1));
        cell = imageBodyEl.querySelector('.ed-page-cell[data-page-index="' + pageIndex + '"]');
      } else {
        cell = imageBodyEl.querySelector('.ed-img-cell[data-index="' + index + '"]');
      }
      if (!cell) return null;
      var frame = cell.querySelector(".ed-img-frame");
      return frame ? { cell: cell, frame: frame } : null;
    }

    function pointInRect(rect, point) {
      return Boolean(rect && point
        && point.x >= rect.x && point.x <= rect.x + rect.w
        && point.y >= rect.y && point.y <= rect.y + rect.h);
    }

    function draw(session) {
      cropApi.drawCropCanvas(session);
    }

    function unbind(session) {
      window.removeEventListener("pointermove", session.onMove, true);
      window.removeEventListener("mousemove", session.onMove, true);
      window.removeEventListener("pointerup", session.onUp, true);
      window.removeEventListener("mouseup", session.onUp, true);
      window.removeEventListener("pointercancel", session.onCancel, true);
      window.removeEventListener("keydown", session.onKey, true);
      window.removeEventListener("resize", session.onResize);
    }

    function closeBoard() {
      var session = board;
      if (!session) return;
      board = null;
      unbind(session);
      if (session.canvas && session.canvas.parentNode) {
        session.canvas.parentNode.removeChild(session.canvas);
      }
      if (session.hint && session.hint.parentNode) {
        session.hint.parentNode.removeChild(session.hint);
      }
      if (session.img) session.img.hidden = false;
      if (session.box) session.box.hidden = false;
      // 位图来自 ui_crop 的整页缓存，收摊时不关——关了下一题就解不开同一页。
    }

    function isBoard(session) {
      return Boolean(session) && board === session;
    }

    function mount(session, spot, bitmap) {
      session.bitmap = bitmap;
      session.width = bitmap.width;
      session.height = bitmap.height;
      session.img = spot.frame.querySelector("img");
      session.box = spot.frame.querySelector(".ed-img-box");
      if (session.img) session.img.hidden = true;
      if (session.box) session.box.hidden = true;
      var canvas = document.createElement("canvas");
      canvas.className = "ed-illustration-canvas";
      canvas.setAttribute("aria-label", "配图画板：拖拽框选，双击确认，Esc 取消");
      session.canvas = canvas;
      session.ctx = canvas.getContext("2d");
      spot.frame.insertBefore(canvas, spot.frame.firstChild);
      bindCanvas(session);
      cropApi.layoutCrop(session);
      session.hint.textContent = "在图上拖出要插入的一块，双击确认；Esc 取消。";
    }

    function bindCanvas(session) {
      var canvas = session.canvas;
      var startDrag = function (event) {
        if (event.button !== 0 || session.busy) return;
        var point = cropApi.cropPoint(session, event.clientX, event.clientY);
        // 双击确认的前两下会落在框内：这里绝不能再清框，否则框刚画好就没了。
        if (pointInRect(session.rect, point)) return;
        if (event.detail > 1) return;
        event.preventDefault();
        session.dragging = true;
        session.start = point;
        session.rect = null;
        draw(session);
        if (canvas.setPointerCapture && event.pointerId != null) {
          try { canvas.setPointerCapture(event.pointerId); } catch (error) { /* 捕获失败照常拖 */ }
        }
      };
      canvas.addEventListener("pointerdown", startDrag);
      canvas.addEventListener("mousedown", startDrag);
      // 点击不许冒泡：纯图片卷的页格把单击当成「重新开切图台」。
      canvas.addEventListener("click", function (event) {
        event.stopPropagation();
      });
      canvas.addEventListener("dblclick", function (event) {
        event.preventDefault();
        event.stopPropagation();
        confirmSelection(session);
      });

      session.onMove = function (event) {
        if (!isBoard(session) || !session.dragging || !session.bitmap) return;
        var point = cropApi.cropPoint(session, event.clientX, event.clientY);
        session.rect = {
          x: Math.min(session.start.x, point.x),
          y: Math.min(session.start.y, point.y),
          w: Math.abs(point.x - session.start.x),
          h: Math.abs(point.y - session.start.y)
        };
        draw(session);
      };
      session.onUp = function (event) {
        if (!isBoard(session) || !session.dragging) return;
        if (event.button !== 0) return;
        session.dragging = false;
        var rect = session.rect;
        if (!rect || rect.w < MIN_SIDE || rect.h < MIN_SIDE) {
          session.rect = null;
          draw(session);
          session.hint.textContent = "框太小了，再拖一次。";
          return;
        }
        session.hint.textContent = "选中了 " + Math.round(rect.w) + "×" + Math.round(rect.h)
          + " 像素，双击确认；Esc 取消。";
      };
      session.onCancel = function () {
        if (!isBoard(session) || !session.dragging) return;
        session.dragging = false;
        session.rect = null;
        session.hint.textContent = "这次拖拽被打断了，再拖一次。";
        draw(session);
      };
      session.onKey = function (event) {
        if (!isBoard(session) || event.key !== "Escape") return;
        event.preventDefault();
        closeBoard();
        dock("已取消添加配图。");
      };
      session.onResize = function () {
        if (!isBoard(session) || !session.canvas || !session.canvas.parentNode) return;
        cropApi.layoutCrop(session);
      };

      window.addEventListener("pointermove", session.onMove, true);
      window.addEventListener("mousemove", session.onMove, true);
      window.addEventListener("pointerup", session.onUp, true);
      window.addEventListener("mouseup", session.onUp, true);
      window.addEventListener("pointercancel", session.onCancel, true);
      window.addEventListener("keydown", session.onKey, true);
      window.addEventListener("resize", session.onResize);
    }

    // ---------- 确认 → 裁像素 → 上传 → 按光标上下文插入 ----------

    function confirmSelection(session) {
      if (!isBoard(session) || session.busy) return;
      var rect = session.rect;
      var scale = Number(session.scale);
      if (!rect || !(scale > 0) || rect.w < MIN_SIDE || rect.h < MIN_SIDE) {
        session.hint.textContent = "先拖出一个框，再双击确认。";
        return;
      }
      var cropped = cropApi.cropRegionToDataUrl(session.bitmap, {
        x: rect.x / scale,
        y: rect.y / scale,
        w: rect.w / scale,
        h: rect.h / scale
      });
      if (!cropped) {
        session.hint.textContent = "这次框选的坐标没算出来，请再拖一次。";
        return;
      }
      session.busy = true;
      session.hint.textContent = "正在保存配图…";
      hostCall("asset.upload", { data_url: cropped.dataUrl }).then(function (result) {
        if (!isBoard(session)) return;
        var uri = String((result && result.uri) || "");
        if (!uri) {
          session.busy = false;
          session.hint.textContent = "底座没有返回配图地址，再双击试一次。";
          return;
        }
        var target = {
          index: session.index,
          field: session.field,
          pos: session.pos,
          start: session.startOffset,
          end: session.endOffset
        };
        closeBoard();
        insertAsset(target, uri);
      }, function (error) {
        if (!isBoard(session)) return;
        session.busy = false;
        session.hint.textContent = "没存住：" + ((error && error.message) || "未知原因") + "，再双击试一次。";
        dockWarn("配图没存住：" + ((error && error.message) || "未知原因"), errorDetail(error));
      });
    }

    function sourceContext(text, offset) {
      var before = String(text || "").slice(0, Math.max(0, Number(offset) || 0));
      var begin = before.lastIndexOf("\\begin{choices}");
      var end = before.lastIndexOf("\\end{choices}");
      return begin >= 0 && begin > end ? "choice" : "body";
    }

    function centeredSnippet(uri) {
      return "\\vspace{1ex}\n\\begin{center}\n"
        + "\\includegraphics[width=" + CENTER_WIDTH + "]{" + uri + "}\n"
        + "\\end{center}\n";
    }

    /** 选项里只要这一张图：没有 \\\\、没有 A. 前缀，选项字母由 \item 自己长。 */
    function optionSnippet(uri) {
      return "\\includegraphics[width=" + OPTION_WIDTH + "]{" + uri + "}";
    }

    function spliceValue(value, start, end, snippet) {
      var text = String(value == null ? "" : value);
      var from = clampValue(Number(start) || 0, 0, text.length);
      var to = clampValue(Number(end) || from, from, text.length);
      return {
        text: text.slice(0, from) + snippet + text.slice(to),
        at: from + snippet.length
      };
    }

    function insertAsset(info, uri) {
      var item = state.items[info.index];
      if (!item) {
        dockWarn("配图已存好，但第 " + (info.index + 1) + " 题已经不在画布上，没法插入。");
        return;
      }
      var node;
      var value;
      var context;
      if (info.field === "source") {
        node = sourceNode(info.index);
        value = node ? node.value : item.source;
        context = sourceContext(value, info.start);
      } else {
        node = boxNode(info);
        if (!node) {
          dockWarn("光标所在的输入框已经重建，请把光标重新放好再试一次。");
          return;
        }
        value = node.value;
        context = info.field === "choice" ? "choice" : "body";
      }
      var snippet = context === "choice" ? optionSnippet(uri) : centeredSnippet(uri);
      var next = spliceValue(value, info.start, info.end, snippet);
      if (info.field === "source") {
        if (node) {
          node.value = next.text;
          growTextarea(node);
          node.focus();
          try { node.setSelectionRange(next.at, next.at); } catch (error) { /* 光标尽力而为 */ }
        }
        onSourceInput(info.index, next.text);
      } else {
        node.value = next.text;
        node.focus();
        try { node.setSelectionRange(next.at, next.at); } catch (error) { /* input 不一定支持 */ }
        onBoxInput(info.index, info.field, info.pos, next.text);
      }
      dock("配图已插入第 " + (info.index + 1) + " 题的"
        + (context === "choice" ? "选项" : "题干/解析") + "，还没保存。");
    }

    function openBoard() {
      var info = usableCaret();
      if (!info) {
        dockWarn("先把光标放到题干、解析或选项里，再点【添加配图】。");
        return;
      }
      var item = state.items[info.index];
      if (!item) return;
      closeBoard();
      var picture = itemImage(item);
      if (!picture || !picture.uri) {
        dockWarn("第 " + (info.index + 1) + " 题还没有原图：先在左栏框选切题，或在题图里贴一张。");
        return;
      }
      if (/\.svg(?:$|\?)/i.test(String(picture.uri))) {
        dockWarn("文本还原页是矢量图，框不出像素配图。");
        return;
      }
      var spot = findSpot(info.index, item);
      if (!spot) {
        dockWarn("左栏没有第 " + (info.index + 1) + " 题的原图位置。");
        return;
      }
      var hint = el("p", "ed-illustration-hint", "正在取图…");
      spot.cell.appendChild(hint);
      var session = {
        index: info.index,
        field: info.field,
        pos: info.pos == null ? null : Number(info.pos),
        startOffset: Number(info.start) || 0,
        endOffset: Number(info.end) || 0,
        cell: spot.cell,
        frame: spot.frame,
        hint: hint,
        bitmap: null,
        width: 0,
        height: 0,
        scale: 1,
        dpr: 1,
        rect: null,
        start: null,
        dragging: false,
        busy: false,
        canvas: null,
        ctx: null,
        img: null,
        box: null,
      };
      board = session;
      cropApi.loadPageBitmap(picture.uri).then(function (bitmap) {
        if (!isBoard(session)) return;
        mount(session, spot, bitmap);
      }, function (error) {
        if (!isBoard(session)) return;
        hint.textContent = "这张原图取不出来（" + ((error && error.message) || "未知原因") + "）。";
      });
    }

    if (addButton) {
      addButton.addEventListener("click", openBoard);
    }
    if (sourceBodyEl) {
      trackEvents();
    }

    return {
      openBoard: openBoard,
      closeBoard: closeBoard,
      isOpen: function () { return Boolean(board); },
      sourceContext: sourceContext,
      centeredSnippet: centeredSnippet,
      optionSnippet: optionSnippet
    };
  }

  global.JzoEditorIllustration = { create: create };
})(window);
