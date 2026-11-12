/**
 * stage_inbound.js —— stage.js 的「消息入口 + 三端分离 + 看板跳转」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：底座 JS 单文件不超 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var AI_INVOKE_PERMISSION = deps.AI_INVOKE_PERMISSION;
    var EDITOR_PLUGIN_ID = deps.EDITOR_PLUGIN_ID;
    var ID_RE = deps.ID_RE;
    var OPEN_BANK_QUERY_MAX = deps.OPEN_BANK_QUERY_MAX;
    var PROTOCOL = deps.PROTOCOL;
    var activate = deps.activate;
    var busCore = deps.busCore;
    var dock = deps.dock;
    var emit = deps.emit;
    var fetchJson = deps.fetchJson;
    var hasCapability = deps.hasCapability;
    var loadBankView = deps.loadBankView;
    var notify = deps.notify;
    var openPlugin = deps.openPlugin;
    var relay = deps.relay;
    var replyHost = deps.replyHost;
    var stageState = deps.stageState;

  // ---------- 消息入口：响应归位 + 插件事件上桥 ----------
  window.addEventListener("message", function (event) {
    var message = event.data;
    if (!message || message.protocol !== PROTOCOL) return;
    var tab = null;
    for (var i = 0; i < stageState.tabs.length; i += 1) {
      if (stageState.tabs[i].frame && stageState.tabs[i].frame.contentWindow === event.source) {
        tab = stageState.tabs[i];
        break;
      }
    }
    if (!tab) {
      for (var p = 0; p < stageState.panels.length; p += 1) {
        if (stageState.panels[p].frame && stageState.panels[p].frame.contentWindow === event.source) {
          tab = stageState.panels[p];
          break;
        }
      }
    }
    if (!tab) return;   // 不认识的发信人一律丢弃

    // 插件主动申请宿主数据（jzo-plugin/1 的 request 方向，题库通道新增）。
    // 只认白名单方法，id 必须是短标识；回复严格回到发信 iframe。
    if (message.kind === "request") {
      if (typeof message.id !== "string" || !ID_RE.test(message.id)) {
        // 显式降级，不静默吞掉（2026-10-23 军令 #07 批复 2）：把 id 原样回包，插件的 pending
        // 表能命中自己那条、立刻拿到可读原因；同时在底栏记一笔，开发者不再抓瞎。
        var badName = (tab.plugin && tab.plugin.name) || tab.plugin.id || "未命名插件";
        replyHost(tab, { id: message.id }, false, {
          code: "BAD_REQUEST_ID",
          message: "请求 id 不合法：宿主要求匹配 ^[A-Za-z0-9_-]{1,80}$（带点号会被拒），本次请求未转发"
        });
        dock("插件「" + badName + "」的请求 id 不合法，宿主已拒发（未转发到数据通道）——"
          + "id 须匹配 ^[A-Za-z0-9_-]{1,80}$，不要用带点号的插件 id 拼", "plugin.error");
        return;
      }
      relay(tab, message);
      return;
    }

    if (message.kind === "response" && tab.pending) {
      var waiter = tab.pending.get(message.id);
      if (!waiter) return;
      tab.pending.delete(message.id);
      if (message.ok) {
        waiter.resolve(message.result || {});
      } else {
        var error = message.error || {};
        waiter.reject(new Error(error.message || error.code || "插件返回失败"));
      }
      return;
    }

    if (message.kind === "notification") {
      var topic = String(message.event || "").toLowerCase();
      if (busCore.denies(topic)) {
        dock("插件「" + (tab.plugin.name || tab.plugin.id) + "」想发未授权事件 " + topic + "，已丢弃。", "bus.denied");
        return;
      }
      var text = message.payload && typeof message.payload.text === "string"
        ? message.payload.text.slice(0, 400)
        : JSON.stringify(message.payload || {}).slice(0, 400);
      // 日志级别由插件自报，但只在白名单里认：底座不许被插件改成「一切正常」的样子。
      // warn 是「出了岔子但没挡住老师」——后台切题识别有出入就走这一档，不许弹红窗。
      var level = String(message.payload && message.payload.level || "");
      if (!level && message.payload && message.payload.tone) {
        // 兼容 tone 口径：warn/error 一律进【报错诊断】，不许只躺在运行日志里。
        var tone = String(message.payload.tone).toLowerCase();
        if (tone === "warn" || tone === "warning") level = "warn";
        else if (tone === "error" || tone === "fatal") level = "error";
        else if (tone === "note") level = "note";
        else if (tone === "ok" || tone === "success") level = "ok";
      }
      if (["note", "ok", "error", "info", "system", "warn"].indexOf(level) < 0) level = "";
      // 插件自报的主题名只作归类用：长度卡死，防止插件拿它夹带长文本。
      var dockTopic = String(message.payload && message.payload.topic || "").slice(0, 60);
      // 错误现场（Response 全文 / 堆栈）单独放行：报错诊断要打完整，不许只剩一句干话。
      var dockDetail = message.payload && typeof message.payload.detail === "string"
        ? message.payload.detail.slice(0, 20000)
        : "";
      emit(topic, {
        text: text, pluginId: tab.plugin.id, level: level,
        topic: dockTopic, detail: dockDetail, raw: message.payload || null
      });
    }
  });

  // ---------- 三端分离：编辑跳转（存储端/输出端 → 输入端） ----------
  // 题库与组卷/讲义一律只读；老师点「去编辑」时插件只发一个 system.open_editor，
  // 由宿主负责开录题插件的页签并把题号注进去——插件之间不直连（AGENTS §2）。
  var pendingEditorIntent = null;
  var pendingBankQuery = null;

  function findPluginTab(pluginId) {
    for (var i = 0; i < stageState.tabs.length; i += 1) {
      if (stageState.tabs[i].kind === "plugin" && stageState.tabs[i].plugin && stageState.tabs[i].plugin.id === pluginId) return stageState.tabs[i];
    }
    return null;
  }

  function deliverEditorIntent(tab) {
    if (!pendingEditorIntent || !tab || tab.state !== "live") return;
    var intent = pendingEditorIntent;
    pendingEditorIntent = null;
    notify(tab, "system.open_editor", { question_id: intent.question_id, from: intent.from });
  }

  /** 挂载/唤醒完成后补发检索意图：iframe 文档没就绪就 postMessage，通知会丢。 */
  function deliverBankQuery(tab) {
    if (!pendingBankQuery || !tab || tab.state !== "live") return;
    var intent = pendingBankQuery;
    pendingBankQuery = null;
    notify(tab, "system.bank_query", { query: intent.query, question_id: intent.question_id });
  }

  function openEditor(payload) {
    var raw = (payload && payload.raw) || {};
    var questionId = typeof raw.question_id === "string" ? raw.question_id.slice(0, 80) : "";
    if (questionId && !ID_RE.test(questionId)) {
      dock("编辑跳转带来的题目 id 不合法，已拒绝。", "bus.denied");
      return;
    }
    pendingEditorIntent = { question_id: questionId, from: (payload && payload.pluginId) || "" };
    var tab = findPluginTab(EDITOR_PLUGIN_ID);
    if (tab) {
      activate(tab.key);
      deliverEditorIntent(tab);
      return;
    }
    fetchJson("/api/plugins").then(function (data) {
      var plugin = ((data && data.plugins) || []).filter(function (item) {
        return item.id === EDITOR_PLUGIN_ID;
      })[0];
      if (!plugin) {
        pendingEditorIntent = null;
        dock("没找到录题工作台插件，编辑跳转未完成。", "stage.editor.missing");
        return;
      }
      openPlugin(plugin);   // 挂载就绪后由 mountFrame 补发注入
      dock("正在唤醒录题工作台…", "stage.editor.wake");
    }, function (error) {
      pendingEditorIntent = null;
      dock("读插件清单失败，编辑跳转未完成：" + error.message, "stage.editor.missing");
    });
  }

  /** 清单声明才算数：插件 payload 里自报的权限一律不认（与 bank 串库同规则）。 */
  function hasAiGrant(tab) {
    var list = tab.plugin && tab.plugin.permissions;
    return Array.isArray(list) && list.indexOf(AI_INVOKE_PERMISSION) >= 0;
  }

  // ---------- 看板跳转：打开题库视图页签（system.open_bank） ----------
  // 与 openEditor 同构：插件只发意图，跳转由宿主完成。军令 #20 后「数据引擎」
  // 与「界面」分家：跳转目标是声明 bank.view 的视图插件，provider 不再开页签。
  function findBankViewTab() {
    for (var i = 0; i < stageState.tabs.length; i += 1) {
      if (stageState.tabs[i].kind === "plugin" && hasCapability(stageState.tabs[i], "bank.view")) return stageState.tabs[i];
    }
    return null;
  }

  function openBank(payload) {
    var raw = (payload && payload.raw) || {};
    var questionId = typeof raw.question_id === "string" ? raw.question_id.slice(0, 80) : "";
    if (questionId && !ID_RE.test(questionId)) {
      dock("题库跳转带来的题目 id 不合法，已拒绝。", "bus.denied");
      return;
    }
    // 军令 #15：AI 回复里的「前往题库并搜索」把检索词一并交进来，
    // 由宿主写进目标插件（system.bank_query），插件不必自己猜要不要重开页签。
    var query = typeof raw.query === "string" ? raw.query.trim().slice(0, OPEN_BANK_QUERY_MAX) : "";
    if (query || questionId) {
      pendingBankQuery = { query: query, question_id: questionId };
    }
    var tab = findBankViewTab();
    if (tab) {
      activate(tab.key);
      if (tab.ready) deliverBankQuery(tab);   // 刚唤醒的交给 mountFrame 补发
      dock("已跳转到题库"
        + (query ? "，检索「" + query + "」" : "")
        + (questionId ? "（题目 " + questionId + "）" : "") + "。", "stage.bank.opened");
      return;
    }
    loadBankView().then(function (plugin) {
      if (!plugin) {
        pendingBankQuery = null;
        dock("没找到题库视图插件（bank.view），跳转未完成。", "stage.bank.missing");
        return;
      }
      openPlugin(plugin);
      dock("正在打开题库"
        + (query ? "，检索「" + query + "」" : "")
        + (questionId ? "（题目 " + questionId + "）" : "") + "…", "stage.bank.opened");
    }, function (error) {
      pendingBankQuery = null;
      dock("读插件清单失败，题库跳转未完成：" + error.message, "stage.bank.missing");
    });
  }

    return {
      deliverBankQuery: deliverBankQuery,
      deliverEditorIntent: deliverEditorIntent,
      findBankViewTab: findBankViewTab,
      findPluginTab: findPluginTab,
      hasAiGrant: hasAiGrant,
      openBank: openBank,
      openEditor: openEditor,
      pendingBankQuery: pendingBankQuery,
      pendingEditorIntent: pendingEditorIntent,
    };
  }

  global.JzoStageInbound = { create: create };
})(window);
