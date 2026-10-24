/**
 * SplitPane：四区边界的原生拖拽调尺寸（零第三方库）。
 *
 * 事实来源只有一个：`.ws-page` 上的三枚 CSS 变量
 *   --sidebar-width / --context-width / --dock-height
 * 拖拽只改变量，栅格轨道自己跟着走；折叠态也只改变量（见 workspace.css）。
 * 绝不在拖拽里往元素上补 width/height 内联样式——两本账是当年折叠死锁的温床。
 *
 * 暗坑（军令任务 1.4）：拖拽中必须让 iframe 交出指针事件。
 * 鼠标一旦滑进插件文档，事件被 iframe 吞掉、不再冒泡到宿主，mousemove 断流，
 * 手柄就卡死在半路。这里用 `.ws-page[data-resizing] iframe { pointer-events: none }`
 * 一刀切断，拖拽结束再放开。
 *
 * 记忆（军令任务 2）：mouseup 后写 localStorage，刷新时恢复；左下角一键回默认。
 */
(function () {
  "use strict";

  var STORAGE_KEY = "jzo.workspace.layout.v1";
  var KEY_STEP = 8;
  var KEY_STEP_FAST = 32;

  var PANES = {
    side: {
      variable: "--sidebar-width",
      resizer: "side",
      axis: "x",
      // 左栏在栅格最左侧：鼠标右移 = 变宽
      sign: 1,
      min: 180,
      max: 480,
      fallback: 240,
      hiddenAttr: "data-side",
      label: "左栏宽度"
    },
    context: {
      variable: "--context-width",
      resizer: "context",
      axis: "x",
      // 右栏贴在右边界：鼠标左移 = 变宽
      sign: -1,
      min: 220,
      max: 520,
      fallback: 300,
      hiddenAttr: "data-ctx",
      label: "右栏宽度"
    },
    dock: {
      variable: "--dock-height",
      resizer: "dock",
      axis: "y",
      // 底栏贴在下边界：鼠标上移 = 变高
      sign: -1,
      min: 96,
      max: 640,
      fallback: 190,
      hiddenAttr: "data-dock",
      label: "底栏高度"
    }
  };

  var page = document.querySelector(".ws-page");
  if (!page) return;

  var bus = window.JzoBus;
  var drag = null;
  var frameQueued = false;
  var pendingValue = 0;
  var pendingPane = null;

  function emit(topic, payload) {
    if (bus && typeof bus.emit === "function") bus.emit(topic, payload, { source: "splitpane" });
  }

  function isNumber(value) {
    return typeof value === "number" && isFinite(value);
  }

  function clamp(pane, value) {
    var max = pane.max;
    if (pane === PANES.dock) {
      // 底栏不许吃光画布：留出舞台头 + 至少 240px 的对话区
      var available = page.clientHeight - 240;
      if (available > pane.min) max = Math.min(pane.max, available);
    }
    return Math.round(Math.min(Math.max(value, pane.min), max));
  }

  function readSize(pane) {
    var raw = window.getComputedStyle(page).getPropertyValue(pane.variable);
    var value = parseFloat(raw);
    return isNumber(value) && value > 0 ? value : pane.fallback;
  }

  function writeSize(paneKey, value, options) {
    var pane = PANES[paneKey];
    if (!pane) return;
    var size = clamp(pane, value);
    page.style.setProperty(pane.variable, size + "px");
    syncAria(paneKey, size);
    if (options && options.persist) save();
    return size;
  }

  function syncAria(paneKey, size) {
    var pane = PANES[paneKey];
    var handle = document.querySelector('.ws-resizer[data-resize="' + pane.resizer + '"]');
    if (!handle) return;
    handle.setAttribute("aria-valuenow", String(Math.round(size)));
    handle.setAttribute("aria-valuemin", String(pane.min));
    handle.setAttribute("aria-valuemax", String(pane.max));
    handle.setAttribute("aria-valuetext", pane.label + " " + Math.round(size) + " 像素");
  }

  function currentSizes() {
    return {
      side: Math.round(readSize(PANES.side)),
      context: Math.round(readSize(PANES.context)),
      dock: Math.round(readSize(PANES.dock))
    };
  }

  // ---------- 记忆：localStorage ----------
  function save() {
    try {
      var sizes = currentSizes();
      sizes.savedAt = new Date().toISOString();
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(sizes));
    } catch (error) {
      // 隐私模式 / 配额满：布局照样能用，只是不记忆，不许抛到调用点
    }
  }

  function load() {
    try {
      var raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      var data = JSON.parse(raw);
      if (!data || typeof data !== "object") return null;
      var sizes = {};
      Object.keys(PANES).forEach(function (key) {
        var value = parseFloat(data[key]);
        if (isNumber(value) && value > 0) sizes[key] = clamp(PANES[key], value);
      });
      return Object.keys(sizes).length ? sizes : null;
    } catch (error) {
      return null;
    }
  }

  function restore() {
    var sizes = load();
    if (!sizes) return false;
    Object.keys(sizes).forEach(function (key) {
      writeSize(key, sizes[key], {});
    });
    emit("layout.changed", { by: "restore", sizes: currentSizes() });
    return true;
  }

  // ---------- 拖拽：mousedown → mousemove → mouseup ----------
  function beginDrag(paneKey, event) {
    var pane = PANES[paneKey];
    if (!pane) return;
    // 收起态的手柄已被 CSS 摘走；这里再兜一层，别拖一条 0 宽的空轨道
    if (page.getAttribute(pane.hiddenAttr) === "hidden") return;

    drag = {
      pane: paneKey,
      axis: pane.axis,
      sign: pane.sign,
      start: pane.axis === "x" ? event.clientX : event.clientY,
      size: readSize(pane)
    };
    pendingPane = paneKey;
    pendingValue = drag.size;
    // data-resizing 一挂上，CSS 立刻把所有 iframe 的 pointer-events 关掉
    page.setAttribute("data-resizing", paneKey);
    document.documentElement.classList.add("ws-dragging");
    if (pane.axis === "y") document.documentElement.classList.add("ws-drag-y");

    window.addEventListener("mousemove", onDragMove, true);
    window.addEventListener("mouseup", endDrag, true);
    window.addEventListener("blur", cancelDrag, true);
    event.preventDefault();
  }

  function onDragMove(event) {
    if (!drag) return;
    var current = drag.axis === "x" ? event.clientX : event.clientY;
    pendingValue = clamp(PANES[drag.pane], drag.size + (current - drag.start) * drag.sign);
    // 一帧最多写一次变量：mousemove 频率高于刷新率时，多写只会白烧主线程
    if (frameQueued) return;
    frameQueued = true;
    window.requestAnimationFrame(flushFrame);
  }

  function flushFrame() {
    frameQueued = false;
    if (!drag || !pendingPane) return;
    page.style.setProperty(PANES[pendingPane].variable, pendingValue + "px");
  }

  function endDrag() {
    if (!drag) return;
    var paneKey = drag.pane;
    drag = null;
    window.removeEventListener("mousemove", onDragMove, true);
    window.removeEventListener("mouseup", endDrag, true);
    window.removeEventListener("blur", cancelDrag, true);
    page.removeAttribute("data-resizing");
    document.documentElement.classList.remove("ws-dragging");
    document.documentElement.classList.remove("ws-drag-y");

    var size = writeSize(paneKey, pendingValue, { persist: true });
    pendingPane = null;
    emit("layout.changed", { by: "drag", pane: paneKey, value: size, sizes: currentSizes() });
  }

  function cancelDrag() {
    if (!drag) return;
    endDrag();
  }

  // ---------- 键盘：方向键调尺寸，Home 回默认（AGENTS §6 可键盘操作） ----------
  function onHandleKey(paneKey, event) {
    var pane = PANES[paneKey];
    if (!pane) return;
    var key = event.key;
    var horizontal = pane.axis === "x";
    var delta = 0;
    if (key === (horizontal ? "ArrowRight" : "ArrowDown")) delta = 1;
    else if (key === (horizontal ? "ArrowLeft" : "ArrowUp")) delta = -1;
    else if (key === "Home" || key === "Enter") {
      event.preventDefault();
      writeSize(paneKey, pane.fallback, { persist: true });
      emit("layout.changed", { by: "key", pane: paneKey, value: pane.fallback, sizes: currentSizes() });
      return;
    } else {
      return;
    }
    event.preventDefault();
    var step = event.shiftKey ? KEY_STEP_FAST : KEY_STEP;
    var next = writeSize(paneKey, readSize(pane) + delta * step * pane.sign, { persist: true });
    emit("layout.changed", { by: "key", pane: paneKey, value: next, sizes: currentSizes() });
  }

  function bindHandles() {
    var handles = document.querySelectorAll(".ws-resizer[data-resize]");
    for (var i = 0; i < handles.length; i += 1) {
      (function (handle) {
        var paneKey = handle.getAttribute("data-resize");
        handle.addEventListener("mousedown", function (event) {
          if (event.button !== 0) return;
          beginDrag(paneKey, event);
        });
        handle.addEventListener("keydown", function (event) {
          onHandleKey(paneKey, event);
        });
        // 双击分隔条把该区弹回默认：拖错了当场就能改回来，不必再去动偏好设置
        handle.addEventListener("dblclick", function () {
          writeSize(paneKey, PANES[paneKey].fallback, { persist: true });
          emit("layout.changed", { by: "dblclick", pane: paneKey, sizes: currentSizes() });
          emit("region.dock", { text: PANES[paneKey].label + "已恢复默认。" });
        });
        syncAria(paneKey, readSize(PANES[paneKey]));
      })(handles[i]);
    }
  }

  // 视口变小后旧尺寸可能已经越界（例如把窗口拖窄后再拖宽）：重新夹一遍
  window.addEventListener("resize", function () {
    Object.keys(PANES).forEach(function (key) {
      var size = readSize(PANES[key]);
      var bounded = clamp(PANES[key], size);
      if (bounded !== Math.round(size)) writeSize(key, bounded, { persist: true });
    });
  });

  bindHandles();
  restore();

  window.JzoSplitPane = {
    sizes: currentSizes,
    set: function (paneKey, value) { return writeSize(paneKey, value, { persist: true }); }
  };
})();
