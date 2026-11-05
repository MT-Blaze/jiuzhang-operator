/**
 * ws_rail.js —— workspace.js 的「折叠：左栏」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1 同款口径：底座 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var ctxToggle = deps.ctxToggle;
    var dockToggle = deps.dockToggle;
    var sidebarToggle = deps.sidebarToggle;

  // ============ 折叠：左栏 / 右栏（data 属性驱动，桌面收轨道、移动滑抽屉） ============
  // 状态机只有一个事实来源：.ws-page 上的 data-side / data-ctx。
  // 样式按这两枚属性钉轨切轨（见 workspace.css 折叠态一节），脚本只负责翻属性，
  // 绝不再往元素上补 style，避免「属性说收起、内联样式说展开」的两本账。
  var wsPage = document.querySelector(".ws-page");
  var mqMobile = window.matchMedia("(max-width: 768px)");
  var openSidebarBtn = document.getElementById("wsOpenSidebar");
  var openCtxBtn = document.getElementById("wsOpenCtx");

  function sideOpen() {
    return !!wsPage && wsPage.getAttribute("data-side") === "open";
  }

  function setSide(open) {
    if (!wsPage) return;
    wsPage.setAttribute("data-side", open ? "open" : "hidden");
    if (sidebarToggle) {
      sidebarToggle.setAttribute("aria-expanded", String(open));
      sidebarToggle.textContent = open ? "折叠" : "展开";
    }
    if (openSidebarBtn) openSidebarBtn.setAttribute("aria-expanded", String(open));
  }

  function ctxOpen() {
    return !!wsPage && wsPage.getAttribute("data-ctx") === "open";
  }

  function immersiveOn() {
    return !!wsPage && wsPage.getAttribute("data-immersive") === "on";
  }

  /**
   * 左栏开关。沉浸全屏里它不许动 data-side——老师的折叠偏好是另一本账，
   * 退出沉浸后必须原样回来；那一屏只翻 data-immersive-rail 这枚呼入位，
   * 左栏以覆盖层浮在画布上（见 workspace.css 沉浸态一节）。
   */
  function toggleRail() {
    if (!wsPage) return;
    if (immersiveOn()) {
      var shown = wsPage.getAttribute("data-immersive-rail") === "on";
      if (shown) wsPage.removeAttribute("data-immersive-rail");
      else wsPage.setAttribute("data-immersive-rail", "on");
      return;
    }
    setSide(!sideOpen());
  }

  function setCtx(open) {
    if (!wsPage) return;
    wsPage.setAttribute("data-ctx", open ? "open" : "hidden");
    if (ctxToggle) {
      ctxToggle.setAttribute("aria-expanded", String(open));
      ctxToggle.textContent = open ? "折叠" : "展开";
    }
    if (openCtxBtn) openCtxBtn.setAttribute("aria-expanded", String(open));
  }

  // 右栏折叠策略（2026-11-05）：默认收起，只由「当前页签插件声明了 sidebar.right」
  // 自动拉起一次；老师亲手折叠过就再也不自动弹开。自动拉起的也不在住户搬走后留空壳。
  var ctxUserWantsOpen = false;  // 老师手动拨过的偏好
  var ctxTouched = false;        // 手动拨过没有
  var ctxAutoOpened = false;     // 当前这次展开是不是插件自动拉的

  /** 插件占了右栏时调用：只拉起一次，且绝不覆盖老师的手动折叠。 */
  function autoOpenCtx() {
    if (!wsPage || ctxOpen() || mqMobile.matches) return;
    if (ctxTouched && !ctxUserWantsOpen) return;
    ctxAutoOpened = true;
    setCtx(true);
  }

  /** 住户搬走时调用：只有「自动拉起的那次」才收回，老师自己开的保持原样。 */
  function collapseCtxIfAuto() {
    if (!wsPage || !ctxOpen() || !ctxAutoOpened) return;
    ctxAutoOpened = false;
    setCtx(false);
  }

  function dockOpen() {
    return !!wsPage && wsPage.getAttribute("data-dock") === "open";
  }

  function setDock(open) {
    if (!wsPage) return;
    wsPage.setAttribute("data-dock", open ? "open" : "hidden");
    if (dockToggle) {
      dockToggle.setAttribute("aria-expanded", String(open));
      dockToggle.textContent = open ? "折叠" : "展开";
    }
  }

  if (sidebarToggle) {
    sidebarToggle.addEventListener("click", function () {
      toggleRail();
    });
  }

  if (openSidebarBtn) {
    openSidebarBtn.addEventListener("click", function () {
      toggleRail();
    });
  }

  function manualCtx(open) {
    ctxTouched = true;
    ctxUserWantsOpen = open;
    ctxAutoOpened = false;
    setCtx(open);
  }

  if (ctxToggle) {
    ctxToggle.addEventListener("click", function () {
      manualCtx(!ctxOpen());
    });
  }

  if (openCtxBtn) {
    openCtxBtn.addEventListener("click", function () {
      manualCtx(true);
    });
  }

  if (dockToggle) {
    dockToggle.addEventListener("click", function () {
      setDock(!dockOpen());
    });
  }

  // 默认态：左栏与底栏桌面展开；右栏一律先收起（没有插件占用时它就是空的）。
  // 窄屏三者都收起，避免一进来就糊在中栏上。
  setSide(!mqMobile.matches);
  setCtx(false);
  setDock(!mqMobile.matches);

  // 跨断点时必须重算：窄屏收起的抽屉拖宽到桌面会留下「轨道已收起、属性仍写 open」
  // 的错位；反过来桌面展开态拉到窄屏则会让抽屉直接糊住中栏。
  function onBreakpoint(matched) {
    setSide(!matched);
    setDock(!matched);
    // 右栏回桌面只恢复老师亲手动过的「想开」；从没拨过就一直收着。
    setCtx(!matched && ctxTouched && ctxUserWantsOpen);
    if (matched) ctxAutoOpened = false;
  }
  if (typeof mqMobile.addEventListener === "function") {
    mqMobile.addEventListener("change", function (e) { onBreakpoint(e.matches); });
  } else if (typeof mqMobile.addListener === "function") {
    mqMobile.addListener(function (e) { onBreakpoint(e.matches); });
  }

    return {
      autoOpenCtx: autoOpenCtx,
      collapseCtxIfAuto: collapseCtxIfAuto,
      ctxOpen: ctxOpen,
      dockOpen: dockOpen,
      immersiveOn: immersiveOn,
      mqMobile: mqMobile,
      onBreakpoint: onBreakpoint,
      openCtxBtn: openCtxBtn,
      openSidebarBtn: openSidebarBtn,
      setCtx: setCtx,
      setDock: setDock,
      setSide: setSide,
      sideOpen: sideOpen,
      toggleRail: toggleRail,
      wsPage: wsPage,
    };
  }

  global.JzoWsRail = { create: create };
})(window);
