/**
 * ws_dock.js —— workspace.js 的「底栏输出区」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1 同款口径：底座 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var dockClearBtn = deps.dockClearBtn;
    var dockLog = deps.dockLog;
    var dockOpen = deps.dockOpen;
    var dockTabs = deps.dockTabs;
    var wsState = deps.wsState;

  // ============ 底栏输出区：EventBus 的 region.dock 落点 ============
  // 四区里左、右、下都由底座托管。插件想往底栏写字，只能发 region.dock 事件，
  // 底座收到后一律 textContent 落 DOM（AGENTS §5：不可信输入进 DOM 前必须净化）。
  var DOCK_MAX = 120;
  // 三级视图的过滤与渲染已拆到 core_log.js（底座微内核），这里只留账本与事件接线。
  var DOCK_VIEWS = window.JzoCoreLog.DOCK_VIEWS;
  var dockCore = window.JzoCoreLog.create({
    el: dockLog,
    entries: function () { return wsState.dockEntries; },
    view: function () { return wsState.dockView; },
    scrollEl: function () {
      return dockOpen() ? document.getElementById("wsDockBody") : null;
    }
  });

  // 三级分类只按事件主题与关键词判，不做内容猜谜：
  // error 进【报错诊断】，宿主生命周期进【系统终端】，其余留在【运行日志】。
  function dockLevel(topic, text) {
    var name = String(topic || "");
    // 「记一笔」级别：只是流水，不惊动人。显式声明的 note 优先于关键词判定。
    if (/^note[._-]/i.test(name)) return "note";
    if (/(^|[._-])(error|failed|failure|timeout)([._-]|$)/i.test(name) ||
      /失败|错误|异常|超时|冲突/.test(text) ||
      /\b(not found|unauthorized|forbidden|internal server error|bad gateway|gateway timeout)\b/i.test(text)) {
      return "error";
    }
    if (/(^|[._-])(warn|warning)([._-]|$)/i.test(name)) return "warn";
    if (/^(plugin|workspace|system|stage|layout|provider)\./.test(name)) return "system";
    return "info";
  }

  function stamp() {
    var now = new Date();
    return String(now.getHours()).padStart(2, "0") + ":" +
      String(now.getMinutes()).padStart(2, "0") + ":" +
      String(now.getSeconds()).padStart(2, "0");
  }

  // 复制必须「静默」：不弹提示、不抢焦点。成功与否只回布尔，由调用方决定原位反馈。
  function copyPlainText(value) {
    var text = String(value == null ? "" : value);
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      return navigator.clipboard.writeText(text).then(function () {
        return true;
      }, function () {
        return fallbackCopy(text);
      });
    }
    return Promise.resolve(fallbackCopy(text));
  }

  // http 下 navigator.clipboard 不可用（非安全上下文），回落老办法。
  // 隐藏 textarea 的 select() 会把焦点吸走，复制完必须原样还给用户原来所在的元素。
  function fallbackCopy(text) {
    var active = document.activeElement;
    var area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.top = "0";
    area.style.left = "0";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    var ok = false;
    try { ok = document.execCommand("copy"); } catch (error) { ok = false; }
    document.body.removeChild(area);
    if (active && active !== document.body && typeof active.focus === "function") {
      try { active.focus({ preventScroll: true }); } catch (error) { try { active.focus(); } catch (e) { /* 老内核不支持 options，尽力而为 */ } }
    }
    return ok;
  }

  function entryVisible(entry) {
    return dockCore.entryVisible(entry);
  }

  function renderDock() {
    dockCore.renderDock();
  }

  function setDockView(view) {
    wsState.dockView = DOCK_VIEWS[view] ? view : "log";
    if (dockTabs) {
      var buttons = dockTabs.querySelectorAll(".ws-dock-tab");
      for (var i = 0; i < buttons.length; i += 1) {
        buttons[i].setAttribute("aria-selected", String(buttons[i].getAttribute("data-view") === wsState.dockView));
      }
    }
    renderDock();
  }

  // 报错诊断的双击复制：原位闪绿底 + 变字，不弹 Toast、不选中文本、不抢焦点。
  // 第一下 mousedown 就掐掉默认行为：行本身不可聚焦，放任默认只会先把焦点丢给 body、
  // 再把整行文字刷蓝，等 dblclick 到手时已经晚了（隐藏 textarea 也就无从归还焦点）。
  if (dockLog) {
    dockLog.addEventListener("mousedown", function (event) {
      if (wsState.dockView !== "error") return;
      if (event.target && event.target.closest && event.target.closest(".ws-dock-detail")) return;
      var target = event.target && event.target.closest ? event.target.closest(".ws-dock-item") : null;
      if (target) event.preventDefault();
    });
    dockLog.addEventListener("selectstart", function (event) {
      if (wsState.dockView !== "error") return;
      if (event.target && event.target.closest && event.target.closest(".ws-dock-detail")) return;
      var target = event.target && event.target.closest ? event.target.closest(".ws-dock-item") : null;
      if (target) event.preventDefault();
    });
    dockLog.addEventListener("dblclick", function (event) {
      if (wsState.dockView !== "error") return;
      if (event.target && event.target.closest && event.target.closest(".ws-dock-detail")) return;
      var item = event.target && event.target.closest ? event.target.closest(".ws-dock-item") : null;
      if (!item) return;
      event.preventDefault();
      var selection = window.getSelection ? window.getSelection() : null;
      if (selection) selection.removeAllRanges();
      var hint = item.querySelector(".ws-dock-copy");
      var flash = function (label) {
        item.classList.add("is-copied");
        if (hint) hint.textContent = label;
        window.setTimeout(function () {
          item.classList.remove("is-copied");
          if (hint) hint.textContent = "双击复制";
        }, 1200);
      };
      copyPlainText(item.getAttribute("data-copy") || "").then(function (ok) {
        flash(ok ? "已复制" : "复制失败");
      }, function () {
        flash("复制失败");
      });
    });
  }

  if (dockTabs) {
    dockTabs.addEventListener("click", function (event) {
      var button = event.target && event.target.closest ? event.target.closest(".ws-dock-tab") : null;
      if (button) setDockView(button.getAttribute("data-view"));
    });
    dockTabs.addEventListener("keydown", function (event) {
      var keys = { ArrowLeft: -1, ArrowRight: 1 };
      if (!(event.key in keys)) return;
      var buttons = Array.prototype.slice.call(dockTabs.querySelectorAll(".ws-dock-tab"));
      var index = buttons.indexOf(document.activeElement);
      if (index < 0) return;
      event.preventDefault();
      var next = buttons[(index + keys[event.key] + buttons.length) % buttons.length];
      next.focus();
      setDockView(next.getAttribute("data-view"));
    });
  }

  function dockLine(text, topic, level, detail) {
    var full = String(text == null ? "" : text);
    var body = full.slice(0, 400);
    var name = String(topic || "");
    var at = stamp();
    var kind = String(level || "");
    if (kind === "warning") kind = "warn";
    if (["note", "warn", "error", "system", "info"].indexOf(kind) < 0) kind = "";
    if (!kind) kind = dockLevel(name, full);
    // 完整现场独立存放：运行日志只显示摘要，诊断页才铺原文。
    var detailText = String(detail == null ? "" : detail).slice(0, 20000);
    if (!detailText && (kind === "error" || kind === "warn")) detailText = full.slice(0, 20000);
    // 「记一笔」只留一行灰字：`[15:30] 正文`——不带主题名，不带秒，像随口说的。
    var line = kind === "note"
      ? "[" + at.slice(0, 5) + "] " + body
      : at + (name ? " [" + name + "] " : " ") + body;
    wsState.dockEntries.push({
      time: at,
      topic: name,
      text: body,
      detail: detailText,
      level: kind,
      line: line,
    });
    while (wsState.dockEntries.length > DOCK_MAX) wsState.dockEntries.shift();
    renderDock();
  }

  function wireDock() {
    if (!window.JzoBus || typeof window.JzoBus.on !== "function") return;
    window.JzoBus.on("region.dock", function (event) {
      var payload = event.payload || {};
      // tone 是老口径、level 是新口径：两者都收，warn/error 一律进【报错诊断】。
      var tone = String(payload.level || payload.tone || "");
      var detail = typeof payload.detail === "string" ? payload.detail
        : (typeof payload.detail_text === "string" ? payload.detail_text : "");
      dockLine(payload.text || "（空消息）", payload.topic || event.topic, tone, detail);
    });
    window.JzoBus.on("layout.changed", function (event) {
      var payload = event.payload || {};
      if (payload.by === "restore") return;   // 刷新恢复不必刷屏
      var sizes = payload.sizes || {};
      dockLine("布局已调整（" + (payload.by || "drag") + "）：左 " + sizes.side +
        " / 右 " + sizes.context + " / 下 " + sizes.dock, "layout.changed");
    });
    if (dockClearBtn) {
      dockClearBtn.addEventListener("click", function () {
        wsState.dockEntries = [];
        renderDock();
      });
    }
  }

    return {
      DOCK_MAX: DOCK_MAX,
      DOCK_VIEWS: DOCK_VIEWS,
      copyPlainText: copyPlainText,
      dockCore: dockCore,
      dockLevel: dockLevel,
      dockLine: dockLine,
      entryVisible: entryVisible,
      fallbackCopy: fallbackCopy,
      renderDock: renderDock,
      setDockView: setDockView,
      stamp: stamp,
      wireDock: wireDock,
    };
  }

  global.JzoWsDock = { create: create };
})(window);
