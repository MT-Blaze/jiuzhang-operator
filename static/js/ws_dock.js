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
    entries: function () { return entriesForView(); },
    view: function () { return wsState.dockView; },
    scrollEl: function () {
      return dockOpen() ? document.getElementById("wsDockBody") : null;
    }
  });

  // 【运行日志】与【系统终端】各记一本账：
  //   系统底座主题（stage./region./layout./plugin./system./workspace./provider.）只进系统终端；
  //   其余业务主题（dict./bank./editor./prefs./agent./basket./host. 等）只进运行日志。
  // 整块下架：恢复成单一账本，删掉本段与 core_log.js 里的 scope 判定即可。
  var SYSTEM_TOPIC_RE = /^(stage|region|layout|plugin|system|workspace|provider)\./i;
  var LEVELS = ["note", "info", "ok", "warn", "error", "system"];

  function isSystemTopic(topic) {
    return SYSTEM_TOPIC_RE.test(String(topic || ""));
  }

  function normalizeLevel(raw) {
    var kind = String(raw == null ? "" : raw).toLowerCase();
    if (kind === "warning") return "warn";
    if (kind === "success") return "ok";
    if (kind === "fatal") return "error";
    return LEVELS.indexOf(kind) >= 0 ? kind : "";
  }

  /** 当前视图该读哪本账：报错诊断把两本账里的 warn/error 合起来按时间排。 */
  function allEntries() {
    return wsState.sysEntries.concat(wsState.runtimeEntries).sort(function (a, b) {
      return a.at - b.at;
    });
  }

  function entriesForView() {
    var view = wsState.dockView;
    if (view === "terminal") return wsState.sysEntries;
    if (view === "error") return allEntries();
    return wsState.runtimeEntries;
  }

  function clearDock() {
    wsState.sysEntries = [];
    wsState.runtimeEntries = [];
    renderDock();
  }

  // 只判级别与语气，不做内容猜谜；落哪本账由 route 决定，不靠 level 兼任。
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

  /**
   * 记一行账。scope 由调用方按「事件从哪来」决定：
   *   system —— 底座/内核生命周期，进【系统终端】；
   *   runtime —— 真实业务操作，进【运行日志】。
   * 不传 scope 时才退回按主题名判，兼容宿主里直接调 dockLine 的老调用点。
   */
  function dockLine(text, topic, level, detail, scope) {
    var full = String(text == null ? "" : text);
    var body = full.slice(0, 400);
    var name = String(topic || "");
    var at = stamp();
    var kind = normalizeLevel(level) || dockLevel(name, full);
    if (!kind) kind = "info";
    var target = scope === "system" || scope === "runtime"
      ? scope
      : (kind === "system" || isSystemTopic(name) ? "system" : "runtime");
    // 完整现场独立存放：运行日志只显示摘要，诊断页才铺原文。
    var detailText = String(detail == null ? "" : detail).slice(0, 20000);
    if (!detailText && (kind === "error" || kind === "warn")) detailText = full.slice(0, 20000);
    // 「记一笔」只留一行灰字：`[15:30] 正文`——不带主题名，不带秒，像随口说的。
    var line = kind === "note"
      ? "[" + at.slice(0, 5) + "] " + body
      : at + (name ? " [" + name + "] " : " ") + body;
    var ledger = target === "system" ? wsState.sysEntries : wsState.runtimeEntries;
    ledger.push({
      time: at,
      at: Date.now(),
      topic: name,
      text: body,
      detail: detailText,
      level: kind,
      scope: target,
      line: line,
    });
    while (ledger.length > DOCK_MAX) ledger.shift();
    renderDock();
  }

  function wireDock() {
    if (!window.JzoBus || typeof window.JzoBus.on !== "function") return;
    // 两条独立订阅、两本账：region.dock 按语义来源分流，layout.changed 只进系统终端。
    window.JzoBus.on("region.dock", function (event) {
      var payload = event.payload || {};
      // tone 是老口径、level 是新口径：两者都收，warn/error 一律进【报错诊断】。
      var tone = normalizeLevel(payload.level || payload.tone);
      var detail = typeof payload.detail === "string" ? payload.detail
        : (typeof payload.detail_text === "string" ? payload.detail_text : "");
      // 插件经宿主桥投来的消息带 pluginId：那是插件业务日志，永远进运行日志。
      var fromPlugin = Boolean(payload.pluginId);
      var semantic = String(payload.topic || "");
      var route = payload.scope === "system" || payload.scope === "runtime"
        ? payload.scope
        : (fromPlugin ? "runtime"
          : (tone === "system" || isSystemTopic(semantic) || (!semantic && isSystemTopic(event.topic)))
            ? "system" : "runtime");
      dockLine(payload.text || "（空消息）", semantic || (fromPlugin ? "" : event.topic),
        tone, detail, route);
    });
    window.JzoBus.on("layout.changed", function (event) {
      var payload = event.payload || {};
      if (payload.by === "restore") return;   // 刷新恢复不必刷屏
      var sizes = payload.sizes || {};
      dockLine("布局已调整（" + (payload.by || "drag") + "）：左 " + sizes.side +
        " / 右 " + sizes.context + " / 下 " + sizes.dock, "layout.changed", "", "", "system");
    });
    if (dockClearBtn) {
      dockClearBtn.addEventListener("click", clearDock);
    }
  }

    // 只读台账快照：探针与诊断一次取全两本账；页面渲染仍按视图各取一本。
    window.JzoDockLedger = function () {
      return allEntries().map(function (entry) {
        return {
          time: entry.time, at: entry.at, topic: entry.topic, text: entry.text,
          level: entry.level, scope: entry.scope, line: entry.line,
        };
      });
    };

    return {
      DOCK_MAX: DOCK_MAX,
      DOCK_VIEWS: DOCK_VIEWS,
      clearDock: clearDock,
      copyPlainText: copyPlainText,
      dockCore: dockCore,
      dockLevel: dockLevel,
      dockLine: dockLine,
      entriesForView: entriesForView,
      entryVisible: entryVisible,
      fallbackCopy: fallbackCopy,
      isSystemTopic: isSystemTopic,
      renderDock: renderDock,
      setDockView: setDockView,
      stamp: stamp,
      wireDock: wireDock,
    };
  }

  global.JzoWsDock = { create: create };
})(window);
