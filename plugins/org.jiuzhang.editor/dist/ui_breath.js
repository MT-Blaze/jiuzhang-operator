/**
 * 双侧呼吸灯与批次公共元数据折叠（军令 #29 / #30）。
 *
 * 画布帧：鼠标在某一题上停够 ``delay`` 毫秒，那一行的边缘亮灯；离开就熄。
 * 辅助栏帧：收到画布经宿主转来的悬停题号，亮右侧栏边缘、把批次公共元数据收成一行。
 *
 * 状态全交给 ``JzoReactive``（见 ui_reactive.js）：这里只登记「数据 → DOM」的渲染函数，
 * 事件处理器只改数据，不再自己伸手改 DOM。
 */
(function (global) {
  "use strict";

  var ROW_SELECTOR = ".ed-img-cell[data-index], .ed-src-cell[data-index], .ed-q-block[data-index]";

  function create(ctx) {
    var ui = global.JzoReactive.reactive({
      hover: -1,        // 画布上亮着的那一行题号（-1 表示没亮）
      pending: -1,      // 鼠标停住的候选行：停满 delay 才转成 hover
      panelHover: -1,   // 辅助栏收到的悬停题号
      foldOpen: true,   // 批次公共元数据是否展开
      summary: "—"      // 收起后那一行矮标题上的字
    });
    var lampTimer = 0;
    var scrollSignalAt = 0;

    function paintLamp() {
      var cells = document.querySelectorAll(ROW_SELECTOR);
      Array.prototype.forEach.call(cells, function (cell) {
        if (Number(cell.getAttribute("data-index")) === ui.hover) {
          cell.setAttribute("data-lamp", "on");
        } else {
          cell.removeAttribute("data-lamp");
        }
      });
    }

    function paintPanel() {
      if (!ctx.panelRoot) return;
      if (ui.panelHover >= 0) {
        ctx.panelRoot.setAttribute("data-lamp", "on");
        ctx.panelRoot.setAttribute("data-hover", String(ui.panelHover));
      } else {
        ctx.panelRoot.removeAttribute("data-lamp");
        ctx.panelRoot.removeAttribute("data-hover");
      }
    }

    function paintFold() {
      if (ctx.panelMetaSecEl) {
        if (ui.foldOpen) ctx.panelMetaSecEl.setAttribute("data-fold", "open");
        else ctx.panelMetaSecEl.setAttribute("data-fold", "closed");
      }
      if (ctx.panelMetaFoldEl) {
        ctx.panelMetaFoldEl.setAttribute("aria-expanded", ui.foldOpen ? "true" : "false");
      }
      if (ctx.panelMetaSummaryEl) {
        ctx.panelMetaSummaryEl.textContent = ui.summary;
        ctx.panelMetaSummaryEl.title = ui.summary === "—" ? "" : ui.summary;
      }
    }

    global.JzoReactive.watch(function () {
      paintLamp();
      paintPanel();
      paintFold();
    });

    function lampRowOf(node) {
      if (!node || !node.closest) return null;
      return node.closest(".ed-img-cell, .ed-src-cell, .ed-q-block");
    }

    function movePointer(index) {
      if (index === ui.pending) return;
      ui.pending = index;
      window.clearTimeout(lampTimer);
      lampTimer = window.setTimeout(function () {
        if (ui.pending !== index) return;
        ui.hover = index;
        // 画布与辅助栏是两个沙箱帧：亮灯信号只能经宿主总线转过去。
        if (ctx.publish) ctx.publish("editor.canvas_state", { hover: index });
      }, ctx.delay || 200);
    }

    function extinguishLamp() {
      window.clearTimeout(lampTimer);
      lampTimer = 0;
      ui.pending = -1;
      if (ui.hover < 0) return;
      ui.hover = -1;
      if (ctx.publish) ctx.publish("editor.canvas_state", { hover: -1 });
    }

    function wireLamp() {
      (ctx.rows || []).forEach(function (node) {
        if (!node) return;
        node.addEventListener("mouseover", function (event) {
          var row = lampRowOf(event.target);
          if (!row) { extinguishLamp(); return; }
          var index = Number(row.getAttribute("data-index"));
          if (Number.isFinite(index)) movePointer(index);
        });
        node.addEventListener("mouseleave", extinguishLamp);
      });
    }

    /** 辅助栏收到画布的状态：亮边缘、收批次公共元数据。 */
    function onCanvasState(payload) {
      if (!ctx.panelRoot) return;
      var raw = payload && payload.raw ? payload.raw : payload;
      if (!raw || typeof raw !== "object") return;
      if (raw.hover != null) {
        var hover = Number(raw.hover);
        ui.panelHover = Number.isFinite(hover) ? hover : -1;
      }
      if (raw.scroll) collapseMetaSection();
    }

    /** 画布一滚动就报一声（节流 400ms）：辅助栏据此把公共元数据收起来。 */
    function signalCanvasScroll() {
      var now = Date.now();
      if (scrollSignalAt && now - scrollSignalAt < 400) return;
      scrollSignalAt = now;
      if (ctx.publish) ctx.publish("editor.canvas_state", { scroll: true });
    }

    function collapseMetaSection() {
      ui.foldOpen = false;
    }

    function expandMetaSection() {
      ui.foldOpen = true;
    }

    function renderFoldSummary(text) {
      var value = String(text == null ? "" : text).trim();
      ui.summary = value || "—";
    }

    function isFoldOpen() {
      return ui.foldOpen;
    }

    return {
      state: ui,
      wireLamp: wireLamp,
      onCanvasState: onCanvasState,
      signalCanvasScroll: signalCanvasScroll,
      collapseMetaSection: collapseMetaSection,
      expandMetaSection: expandMetaSection,
      renderFoldSummary: renderFoldSummary,
      isFoldOpen: isFoldOpen
    };
  }

  global.JzoBreath = { create: create };
})(window);
