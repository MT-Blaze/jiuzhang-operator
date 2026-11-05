/**
 * Stage：中栏画布的 Tabs 宿主。
 *
 * 职责边界（军令任务 3）：中栏只是「通用舞台」，底座负责挂标签页、挂 iframe、
 * 转发事件；业务画面一律由插件自己画。左、右、下三区仍由底座托管，
 * 插件只能经 HostBus 向指定区域投递数据，拿不到那三区的 DOM。
 *
 * 两类页签：
 *   - 原生页签：「设置与控制台」，带关闭叉。关掉后可从左栏底部入口重新叫回。
 *     画布不设兜底页：所有页签关掉后中栏留白，不塞任何占位文案。
 *     对话不住在中栏——军令 #15 把 AI 助手交还成右栏里的一个普通插件，
 *     底座不再为它保留任何特权入口。
 *   - 重型页签：沙箱 iframe 插件。带 LRU 休眠——同时存活的 iframe 最多 MAX_LIVE_FRAMES 个，
 *     最久未用的发 plugin.deactivate 后摘掉文档，页签保留、状态标「休眠」，再点回来重新挂载。
 *
 * 协议：jzo-plugin/1（PLUGIN_SPEC §2.3.3）。宿主发 request，插件回 response；
 * 另有单向 notification（无 id、不等回复、插件必须幂等）。
 * 沙箱给 allow-scripts + allow-modals：前者让插件跑起来，后者是用户点「打印 / PDF」时
 * window.print() 的必要条件（Chromium 会静默丢弃无 allow-modals 沙箱里的 print 调用）。
 * 依旧不给 allow-same-origin：插件文档处于不透明源，碰不到宿主 DOM 与令牌。
 */
(function () {
  "use strict";

  var PROTOCOL = "jzo-plugin/1";
  var SANDBOX = "allow-scripts allow-modals";
  var MAX_LIVE_FRAMES = 3;
  var REQUEST_TIMEOUT_MS = 30000;   // PLUGIN_SPEC §5.1：宿主对插件请求 30 秒超时
  var TAB_OVERFLOW = 10;            // 军令 #16 模块三：超过 10 个页签固定 120px + 横滚 + 分组合并
  var TAB_GROUP_MIN = 2;            // 组内凑满两页才收成下拉，单页收成下拉只是添堵
  var UNGROUPED_KEY = "ungrouped";  // 没进任何文件夹的插件，共用这一个集合分组

  // 录题插件的写入目标不再写死：跨页签共享的题库通道走「活跃 provider」，
  // 由底座按 data/bank_provider.json 解析（PLUGIN_SPEC §2.6.1）。军令 #20 之后
  // provider 只认无界面的题库引擎；取不到 provider 时仍用它，不能让「读不到配置」
  // 打死整条数据通道。界面与引擎分家：跳转题库要打开「声明 bank.view 的视图插件」。
  var BANK_PROVIDER_DEFAULT = "org.jiuzhang.bank-engine";
  var BANK_VIEW_DEFAULT = "org.jiuzhang.bank-ui";
  // 宿主替插件出网的时间闸：草稿箱、题篮、任何 relay 里的 fetch 共用这一个口径，
  // 所以它必须留在组合根最上面——拆出去的模块只能按值领它。
  var RELAY_TIMEOUT_MS = 20000;
  // AI 专用方法的门槛同上：白名单与权限名都由组合根持有，模块只管比对。
  var AI_INVOKE_PERMISSION = "ai:invoke";
  // id 的通行证同理：转发表、消息入口、编辑跳转三条通道都比的是这一个正则，
  // 谁都不能在自己那块里另写一份——口径分叉过一次，插件就会出现「这边认那边不认」。
  var ID_RE = /^[A-Za-z0-9_-]{1,80}$/;
  // 检索词的长度闸也留在组合根：跳转意图由消息入口校验，转发的却是别的模块。
  var OPEN_BANK_QUERY_MAX = 40;

  // 插件能主动发的事件主题白名单已经搬进 core_bus.js：舞台只消费这一份账本。
  var EDITOR_PLUGIN_ID = "org.jiuzhang.editor";

  var tabsEl = document.getElementById("wsTabs");
  var bodyEl = document.getElementById("wsCanvasBody");
  var bus = window.JzoBus;
  var busCore = window.JzoCoreBus.create({ bus: bus });

  // 跨模块共享的可变态：拆文件后依赖按值传，只有挂在同一个对象上才写得到同一份账。
  var stageState = {
    tabs: [],
    // 右栏辅助面板（sidebar.right）不占画布页签，但同样要能走 Host API：
    // 单独一张登记表，消息入口按 frame.contentWindow 反查它的插件身份。
    panels: [],
    activeKey: null,
    requestSeq: 0,
    openSeq: 0,
    groupTree: [],        // 左栏那棵树的镜像：分组页签只显示文件夹名，名字从这里取
    holders: {},          // 分组 key -> {chip, btn, list, count}
    expandedKey: "",      // 同一时刻只许一个分组下拉摊开
    scrollBtns: null,     // 页签栏溢出时的左右小箭头
    immersiveKey: "",     // 沉浸全屏中的页签 key，空串表示没沉浸
    nativeDefs: {},       // 原生页签登记表：关掉后能按原样重建（控制台可从左栏再打开）
    bankProviderId: BANK_PROVIDER_DEFAULT,
    bankViewCall: null,
  };

  // 页签账本（优先级、排位、LRU）在 core_tabs.js：舞台只管画与摘。
  var tabsCore = window.JzoCoreTabs;

  // ---------- 拆出去的模块（PLUGIN_SPEC §2.8.1：单文件不超 800 行） ----------
  var stageTabbar = window.JzoStageTabbar.create({
    TAB_GROUP_MIN: TAB_GROUP_MIN,
    TAB_OVERFLOW: TAB_OVERFLOW,
    UNGROUPED_KEY: UNGROUPED_KEY,
    dock: dock,
    liveFrames: liveFrames,
    // 循环引用：notify 归更下面的 stageFrame，本块排得靠前，只能等它就位后再取。
    notify: function () { return stageFrame.notify.apply(stageFrame, arguments); },
    orderPluginTabs: orderPluginTabs,
    stageState: stageState,
    tabsEl: tabsEl,
  });
  var applySleepPolicy = stageTabbar.applySleepPolicy;
  var dismissGroup = stageTabbar.dismissGroup;
  var groupKeyOf = stageTabbar.groupKeyOf;
  var heavyLiveFrames = stageTabbar.heavyLiveFrames;
  var hydrateConsole = stageTabbar.hydrateConsole;
  var paintGroupStates = stageTabbar.paintGroupStates;
  var paintOverflowBar = stageTabbar.paintOverflowBar;
  var pushParams = stageTabbar.pushParams;
  var renderTabBar = stageTabbar.renderTabBar;
  var setImmersive = stageTabbar.setImmersive;
  var setSidebarTree = stageTabbar.setSidebarTree;
  var toggleImmersive = stageTabbar.toggleImmersive;
  var weightOf = stageTabbar.weightOf;
  var stageInbound = window.JzoStageInbound.create({
    AI_INVOKE_PERMISSION: AI_INVOKE_PERMISSION,
    EDITOR_PLUGIN_ID: EDITOR_PLUGIN_ID,
    ID_RE: ID_RE,
    OPEN_BANK_QUERY_MAX: OPEN_BANK_QUERY_MAX,
    PROTOCOL: PROTOCOL,
    // 循环引用：activate 归更下面的 stageFrame，本块排得靠前，只能等它就位后再取。
    activate: function () { return stageFrame.activate.apply(stageFrame, arguments); },
    busCore: busCore,
    dock: dock,
    emit: emit,
    // 循环引用：fetchJson 归更下面的 stageHttp，本块排得靠前，只能等它就位后再取。
    fetchJson: function () { return stageHttp.fetchJson.apply(stageHttp, arguments); },
    // 循环引用：hasCapability 归更下面的 stageCommand，本块排得靠前，只能等它就位后再取。
    hasCapability: function () { return stageCommand.hasCapability.apply(stageCommand, arguments); },
    // 循环引用：loadBankView 归更下面的 stageCommand，本块排得靠前，只能等它就位后再取。
    loadBankView: function () { return stageCommand.loadBankView.apply(stageCommand, arguments); },
    // 循环引用：notify 归更下面的 stageFrame，本块排得靠前，只能等它就位后再取。
    notify: function () { return stageFrame.notify.apply(stageFrame, arguments); },
    // 循环引用：openPlugin 归更下面的 stageFrame，本块排得靠前，只能等它就位后再取。
    openPlugin: function () { return stageFrame.openPlugin.apply(stageFrame, arguments); },
    relay: relay,
    // 循环引用：replyHost 归更下面的 stageCommand，本块排得靠前，只能等它就位后再取。
    replyHost: function () { return stageCommand.replyHost.apply(stageCommand, arguments); },
    stageState: stageState,
  });
  var deliverBankQuery = stageInbound.deliverBankQuery;
  var deliverEditorIntent = stageInbound.deliverEditorIntent;
  var findPluginTab = stageInbound.findPluginTab;
  var hasAiGrant = stageInbound.hasAiGrant;
  var openBank = stageInbound.openBank;
  var openEditor = stageInbound.openEditor;


  var stageFrame = window.JzoStageFrame.create({
    MAX_LIVE_FRAMES: MAX_LIVE_FRAMES,
    PROTOCOL: PROTOCOL,
    REQUEST_TIMEOUT_MS: REQUEST_TIMEOUT_MS,
    SANDBOX: SANDBOX,
    deliverBankQuery: deliverBankQuery,
    deliverEditorIntent: deliverEditorIntent,
    dock: dock,
    emit: emit,
    heavyLiveFrames: heavyLiveFrames,
    liveFrames: liveFrames,
    pushParams: pushParams,
    stageState: stageState,
    tabsCore: tabsCore,
    toggleImmersive: toggleImmersive,
    applySleepPolicy: applySleepPolicy,
    bodyEl: bodyEl,
    dismissGroup: dismissGroup,
    findTab: findTab,
    hydrateConsole: hydrateConsole,
    orderPluginTabs: orderPluginTabs,
    paintGroupStates: paintGroupStates,
    priorityOf: priorityOf,
    setImmersive: setImmersive,
    tabsEl: tabsEl,
    touch: touch,
  });
  var attachPanel = stageFrame.attachPanel;
  var broadcast = stageFrame.broadcast;
  var notify = stageFrame.notify;
  var request = stageFrame.request;
  var activate = stageFrame.activate;
  var closeTab = stageFrame.closeTab;
  var openPlugin = stageFrame.openPlugin;
  var registerNative = stageFrame.registerNative;
  var rehydratePlugin = stageFrame.rehydratePlugin;
  var updatePlugin = stageFrame.updatePlugin;
  var stageHttp = window.JzoStageHttp.create({
    RELAY_TIMEOUT_MS: RELAY_TIMEOUT_MS,
  });
  var fetchBinary = stageHttp.fetchBinary;
  var fetchJson = stageHttp.fetchJson;
  var filterValue = stageHttp.filterValue;
  var intValue = stageHttp.intValue;
  var plainObject = stageHttp.plainObject;
  var sourceList = stageHttp.sourceList;
  var textValue = stageHttp.textValue;
  var urlValue = stageHttp.urlValue;
  var withWriteToken = stageHttp.withWriteToken;

  var stageCommand = window.JzoStageCommand.create({
    BANK_VIEW_DEFAULT: BANK_VIEW_DEFAULT,
    PROTOCOL: PROTOCOL,
    RELAY_TIMEOUT_MS: RELAY_TIMEOUT_MS,
    activate: activate,
    dock: dock,
    fetchJson: fetchJson,
    findPluginTab: findPluginTab,
    notify: notify,
    openPlugin: openPlugin,
    plainObject: plainObject,
    request: request,
    stageState: stageState,
    textValue: textValue,
  });
  var AGENT_READ_METHODS = stageCommand.AGENT_READ_METHODS;
  var AGENT_TIMEOUT_MS = stageCommand.AGENT_TIMEOUT_MS;
  var AI_ONLY_METHODS = stageCommand.AI_ONLY_METHODS;
  var CHAT_HISTORY_MAX = stageCommand.CHAT_HISTORY_MAX;
  var CLEAN_TEXT_MAX = stageCommand.CLEAN_TEXT_MAX;
  var RELAY_MAX_PER_WINDOW = stageCommand.RELAY_MAX_PER_WINDOW;
  var RELAY_METHODS = stageCommand.RELAY_METHODS;
  var TOPIC_ID_RE = stageCommand.TOPIC_ID_RE;
  var bankProviderBase = stageCommand.bankProviderBase;
  var executeCommand = stageCommand.executeCommand;
  var hasCapability = stageCommand.hasCapability;
  var listCommands = stageCommand.listCommands;
  var loadBankProvider = stageCommand.loadBankProvider;
  var relayBudget = stageCommand.relayBudget;
  var replyHost = stageCommand.replyHost;
  var setPluginCatalog = stageCommand.setPluginCatalog;
  var stageDraft = window.JzoStageDraft.create({
  });
  var loadDraft = stageDraft.loadDraft;
  var resolveDraftBox = stageDraft.resolveDraftBox;
  var saveDraft = stageDraft.saveDraft;
  var stageRelayIo = window.JzoStageRelayIo.create({
    AGENT_TIMEOUT_MS: AGENT_TIMEOUT_MS,
    CLEAN_TEXT_MAX: CLEAN_TEXT_MAX,
    emit: emit,
    fetchBinary: fetchBinary,
    fetchJson: fetchJson,
    intValue: intValue,
    plainObject: plainObject,
    replyHost: replyHost,
    textValue: textValue,
    withWriteToken: withWriteToken,
  });
  var relayMeta = stageRelayIo.relayMeta;
  var relayPending = stageRelayIo.relayPending;
  var relayText = stageRelayIo.relayText;
  var stageRelayBank = window.JzoStageRelayBank.create({
    ID_RE: ID_RE,
    TOPIC_ID_RE: TOPIC_ID_RE,
    bankProviderBase: bankProviderBase,
    emit: emit,
    fetchJson: fetchJson,
    filterValue: filterValue,
    hasCapability: hasCapability,
    intValue: intValue,
    loadBankProvider: loadBankProvider,
    noteBasketChange: noteBasketChange,
    plainObject: plainObject,
    replyHost: replyHost,
    sourceList: sourceList,
    stageState: stageState,
    textValue: textValue,
    withWriteToken: withWriteToken,
  });
  var relayBank = stageRelayBank.relayBank;
  var relayBasket = stageRelayBank.relayBasket;
  var relayIngest = stageRelayBank.relayIngest;
  var stageRelayAgent = window.JzoStageRelayAgent.create({
    AGENT_TIMEOUT_MS: AGENT_TIMEOUT_MS,
    CHAT_HISTORY_MAX: CHAT_HISTORY_MAX,
    ID_RE: ID_RE,
    OPEN_BANK_QUERY_MAX: OPEN_BANK_QUERY_MAX,
    broadcast: broadcast,
    dock: dock,
    fetchJson: fetchJson,
    openBank: openBank,
    openEditor: openEditor,
    plainObject: plainObject,
    textValue: textValue,
    urlValue: urlValue,
    withWriteToken: withWriteToken,
  });
  var relayAgent = stageRelayAgent.relayAgent;






  // ---------- 拆出去的模块：以上每块都只经 deps 拿依赖 ----------

  function priorityOf(tab) {
    return tabsCore.priorityOf(tab);
  }

  /**
   * 舞台优先级（stage.priority）的真实消费点：同排插件页签按优先级从高到低排，
   * 同优先级按打开先后。原生页签永远排第一，不参与抢位。
   * 排完交给 renderTabBar：页签挤爆时才把同组收成下拉、并上横滚（军令 #16 模块三）。
   */
  function orderPluginTabs() {
    if (!tabsEl) return;
    var pluginTabs = stageState.tabs.filter(function (tab) { return tab.kind === "plugin"; });
    pluginTabs = tabsCore.sortPluginTabs(pluginTabs);
    // 判据只数插件页签，不数收成下拉后的条目：收完变少也不会反过来又摊开（来回抖动）
    var many = pluginTabs.length > TAB_OVERFLOW;
    renderTabBar(pluginTabs, many);
    paintOverflowBar(many);
  }

  function emit(topic, payload) {
    busCore.emit(topic, payload);
  }

  function dock(text, topic) {
    busCore.dock(text, topic);
  }

  function findTab(key) {
    return tabsCore.find(stageState.tabs, key);
  }

  function liveFrames() {
    return tabsCore.liveFrames(stageState.tabs);
  }

  function touch(tab) {
    tabsCore.touch(tab);
  }






  function relay(tab, message) {
    var method = String(message.method || "");
    if (RELAY_METHODS.indexOf(method) < 0) {
      replyHost(tab, message, false, {
        code: "UNSUPPORTED_METHOD",
        message: "宿主未开放方法：" + method.slice(0, 80)
      });
      return;
    }
    if (AI_ONLY_METHODS.indexOf(method) >= 0 && !hasAiGrant(tab)) {
      replyHost(tab, message, false, {
        code: "PERMISSION_DENIED",
        message: "方法 " + method.slice(0, 60) + " 需要清单 permissions 声明 " + AI_INVOKE_PERMISSION
      });
      return;
    }
    if (!relayBudget(tab)) {
      replyHost(tab, message, false, {
        code: "RATE_LIMITED",
        message: "请求过于频繁（每 10 秒最多 " + RELAY_MAX_PER_WINDOW + " 次），请稍后再试"
      });
      return;
    }
    var pluginId = tab.plugin && tab.plugin.id;
    if (!pluginId) {
      replyHost(tab, message, false, { code: "NO_PLUGIN", message: "页签没有绑定插件" });
      return;
    }
    var payload = message.payload;
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) payload = {};

    // 能力字典是宿主内存里的表：查询与调度都不出网、不碰库，先于任何 HTTP 分支答复。
    if (method === "command.list") {
      replyHost(tab, message, true, { commands: listCommands() });
      return;
    }
    if (method === "command.execute") {
      executeCommand(tab, payload, function (result) {
        replyHost(tab, message, true, result);
      }, function (code, text, retryable) {
        replyHost(tab, message, false, { code: code, message: text, retryable: Boolean(retryable) });
      });
      return;
    }

    // 草稿走本地托管，不出网、不进库：先于任何 HTTP 分支答复，但必须等分箱完成——
    // 不知道自己在哪个工作区就存取，草稿会串到别的老师的库上。
    if (method === "draft.save" || method === "draft.load") {
      var draftKey = textValue(payload, "key", 80);
      var draftValue = payload.value === undefined ? null : payload.value;
      resolveDraftBox().then(function () {
        done(method === "draft.save"
          ? saveDraft(pluginId, draftKey, draftValue)
          : loadDraft(pluginId, draftKey));
      });
      return;
    }

    var base = "/api/bank/plugins/" + encodeURIComponent(pluginId);
    // 活跃题库的统一入口：读单题正文、大纲树、教研笔记与待审队列一律走它。
    // 录题插件要改真题，不能因为它自己的页签 id 就被引到别的库上（与 bank.create 同规则）。
    var sharedBase = bankProviderBase();

    function done(result) {
      replyHost(tab, message, true, result);
    }

    function fail(error) {
      var detail = error && error.detail;
      var method = String((error && error.method) || "GET");
      var target = String((error && error.url) || "");
      var payload = {
        code: "HOST_" + (error.status || 0),
        message: String((error && error.message) || "宿主请求失败").slice(0, 400),
        retryable: Boolean(error && error.status >= 500),
        status: Number(error && error.status) || 0,
        url: target,
        method: method
      };
      // 报错诊断要的是完整现场：http.js 统一铺开请求行、状态、请求体摘要与响应全文；
      // 只有拿不到 JzoHttp 时才退回旧的三行拼装。
      var full = window.JzoHttp && typeof window.JzoHttp.detail === "function"
        ? window.JzoHttp.detail(error) : "";
      var lines = full ? [full] : [];
      if (!full) {
        if (target) lines.push(method + " " + target);
        if (error && error.status) {
          lines.push("HTTP " + error.status + (error.statusText ? " " + error.statusText : ""));
        }
        if (error && error.message) lines.push(String(error.message));
      }
      if (detail && typeof detail === "object") {
        lines.push("detail: " + JSON.stringify(detail));
      }
      payload.detail = lines.join("\n").slice(0, 20000);
      // 409 查重：detail 里带着主库那道题的 id 与 duplicate 标记，原样带给插件，
      // 插件才弹得出「返回修改 / 强行覆盖」两颗钮。
      if (detail && typeof detail === "object") {
        if (detail.existing_id) payload.existing_id = String(detail.existing_id);
        if (detail.duplicate === true) payload.duplicate = true;
        if (detail.code) payload.detail_code = String(detail.code);
        if (detail.existing_full_name) payload.existing_full_name = String(detail.existing_full_name);
      }
      replyHost(tab, message, false, payload);
    }

    function failWith(code, text, retryable) {
      replyHost(tab, message, false, {
        code: code,
        message: String(text || "宿主请求失败").slice(0, 200),
        retryable: Boolean(retryable)
      });
    }

    // 中转站改动后由宿主广播：插件据此撤掉已入库/已删除的题，不必整批重载，
    // 免得老师正在改的另一道题被顺手刷掉。
    function emitPendingUpdated(action, pendingIds, result) {
      var batch = (result && result.batch) || null;
      emit("system.pending_updated", {
        action: action,
        pending_ids: (pendingIds || []).map(function (id) { return String(id); }),
        batch_id: String((batch && batch.batch_id) || (result && result.batch_id) || ""),
        pluginId: pluginId
      });
    }

    // 智能体通道：AI 助手插件的申请一律在这里由宿主代执行（军令 #15）。
    if (AI_ONLY_METHODS.indexOf(method) >= 0 || AGENT_READ_METHODS.indexOf(method) >= 0) {
      relayAgent(method, payload, done, fail, failWith);
      return;
    }

    // 现场打包交给各家族：done/fail/failWith 是同一对回执口径，家族只管方法前缀。
    var ctx = {
      tab: tab, message: message, method: method, payload: payload, pluginId: pluginId,
      base: base, sharedBase: sharedBase,
      done: done, fail: fail, failWith: failWith, emitPendingUpdated: emitPendingUpdated,
    };
    var families = [relayText, relayPending, relayMeta, relayIngest, relayBank, relayBasket];
    for (var f = 0; f < families.length; f += 1) {
      if (families[f](ctx)) return;
    }

    // 白名单里挂着、但这一层没有分支的方法：明确拒回，绝不落到上面任何一条分支的兜底上。
    // （曾经 basket.clear 是函数末尾的默认动作，任何漏分发的方法都会顺手清空老师的题篮。）
    failWith("UNSUPPORTED_METHOD", "宿主转发表未实现方法：" + method.slice(0, 60));
  }


  /** 题篮变动记一笔，让底栏与其它插件（如组卷）能跟上；插件名不进 DOM 以外的地方。 */
  function noteBasketChange(tab, action, result, count) {
    var total = result && typeof result.total === "number" ? result.total : null;
    dock("插件「" + (tab.plugin.name || tab.plugin.id) + "」" + (
      action === "add" ? "向题篮加入 " + count + " 题" :
      action === "remove" ? "从题篮移除 1 题" : "清空了题篮"
    ) + (total == null ? "。" : "，现共 " + total + " 题。"), "basket.changed");
    emit("basket.changed", { action: action, total: total, pluginId: tab.plugin.id });
  }




  /** 录题两帧之间的双向指令：谁发的就投给另一方，绝不投回发送者自己。
   *  from === "panel" → 画布页签；from === "canvas" → 右栏辅助栏；
   *  认不出的 from 一律不投（宁可让界面不动，也不制造回声）。 */
  /**
   * editor 那两帧之间的双向指令（军令 #32 · 第五步）。
   *
   * payload 已被 stage_inbound 重包成 `{ text, pluginId, level, raw }`，业务数据在 `raw` 里；
   * 谁发的就投给另一方——`from: "panel"` 进画布，`from: "canvas"` 回辅助栏。
   * 主题名一律写在 `notify` 的调用处（逐字面量）：总线是白名单制的，
   * tests.test_plugin_bus_parity 要能在源码里扫到投递点，抽成变量传参就扫不出来
   * （#18-结 的 `stage.tab.*` 正是这样断掉的）。
   */
  function editorPairPayload(event) {
    var payload = (event && event.payload) || {};
    if (payload.pluginId !== EDITOR_PLUGIN_ID) return null;
    var raw = (payload.raw && typeof payload.raw === "object") ? payload.raw : payload;
    return { payload: payload, from: String(raw.from || "") };
  }

  function eachEditorCanvas(node) {
    var canvasTab = findPluginTab(EDITOR_PLUGIN_ID);
    if (canvasTab && canvasTab.frame && canvasTab.state === "live") node(canvasTab);
  }

  function eachEditorPanel(node) {
    stageState.panels.forEach(function (panel) {
      if (panel.plugin && panel.plugin.id === EDITOR_PLUGIN_ID && panel.frame) node(panel);
    });
  }



  function init() {
    if (!tabsEl || !bodyEl) return;
    // 启动不预开任何页签（含兜底页与设置控制台）：中栏留白，等用户从左右栏开页。
    // 控制台只登记定义、不建页签——它绝不许在启动时自己冒出来抢画布。
    registerNative({
      key: "console", title: "设置与控制台", panelId: "wsPanelConsole", lazy: true
    });

    if (bus && typeof bus.on === "function") {
      // 右栏改参数 → 直达中栏所有活着的插件（军令任务 3.3）
      bus.on("ui.params.changed", function (event) { broadcast("ui.params.changed", event.payload); });
      // PLUGIN_SPEC §2.5 把这两条列为合法入站主题，但它们过去只 emit 给宿主自己的总线，
      // 插件 iframe 一条也没收到过——右栏助手清不掉已关闭的录题页快照。这里补上投递。
      bus.on("stage.tab.activated", function (event) { broadcast("stage.tab.activated", event.payload); });
      bus.on("stage.tab.closed", function (event) { broadcast("stage.tab.closed", event.payload); });
      // 录题插件的当前题只喂给右栏面板（AI 助手插件的副驾），不广播给中栏——
      // 中栏插件自己就是选区的来源，回灌只会形成回声。
      bus.on("stage.selection", function (event) {
        stageState.panels.forEach(function (panel) { notify(panel, "stage.selection", event.payload); });
      });
      // 军令 #29：画布报「鼠标停在哪一题」「画布在滚动」，只投给右栏辅助栏——
      // 呼吸灯与批次折叠是辅助栏的事，画布自己不需要这份回执。
      bus.on("editor.canvas_state", function (event) {
        stageState.panels.forEach(function (panel) { notify(panel, "editor.canvas_state", event.payload); });
      });
      // 军令 #31：查重命中的对比浮层只能画在画布那帧（渲染能力在那里），
      // 而发起点在辅助栏（它手上有待审号）。宿主这一跳把报告原样转过去。
      // payload 已被宿主重包成 { text, pluginId, level, raw }，用户数据在 raw 里。
      bus.on("editor.dup_review", function (event) {
        var payload = (event && event.payload) || {};
        if (payload.pluginId !== EDITOR_PLUGIN_ID) return;
        var dupTab = findPluginTab(EDITOR_PLUGIN_ID);
        if (dupTab && dupTab.frame && dupTab.state === "live") {
          notify(dupTab, "editor.dup_review", payload);
        }
      });
      // 军令 #32 · 第五步：重题池的左右渲染对比与整批扫灯都只能由画布那帧执行
      // （MathJax 与滚动条都在那里），发起点仍在辅助栏（按钮与档位都在那里）。
      // 与 dup_review 同一条路，但这两条是**双向**的：谁发的就投给另一方——
      // 辅助栏发的开窗/换档/全部入库进画布，画布发的收窗（Esc）与扫灯结果回辅助栏。
      bus.on("editor.pool_review", function (event) {
        var pair = editorPairPayload(event);
        if (!pair) return;
        if (pair.from === "panel") {
          eachEditorCanvas(function (tab) { notify(tab, "editor.pool_review", pair.payload); });
        } else if (pair.from === "canvas") {
          eachEditorPanel(function (panel) { notify(panel, "editor.pool_review", pair.payload); });
        }
      });
      bus.on("editor.batch_review", function (event) {
        var pair = editorPairPayload(event);
        if (!pair) return;
        if (pair.from === "panel") {
          eachEditorCanvas(function (tab) { notify(tab, "editor.batch_review", pair.payload); });
        } else if (pair.from === "canvas") {
          eachEditorPanel(function (panel) { notify(panel, "editor.batch_review", pair.payload); });
        }
      });
      // 4.3：LaTeX 清洗预览。正文对照只进画布帧；画布不在就回投 tab_not_live，
      // 让辅助栏立刻降级为纯摘要——绝不让老师按到必然落空的【采用】。
      bus.on("editor.clean_review", function (event) {
        var payload = (event && event.payload) || {};
        if (payload.pluginId !== EDITOR_PLUGIN_ID) return;
        var cleanRaw = (payload.raw && typeof payload.raw === "object") ? payload.raw : {};
        var cleanTab = findPluginTab(EDITOR_PLUGIN_ID);
        if (cleanTab && cleanTab.frame && cleanTab.state === "live") {
          notify(cleanTab, "editor.clean_review", payload);
          return;
        }
        stageState.panels.forEach(function (panel) {
          if (panel.plugin && panel.plugin.id === EDITOR_PLUGIN_ID && panel.frame) {
            notify(panel, "editor.clean_review_state", {
              key: String(cleanRaw.key || ""), phase: "tab_not_live", reason: "canvas_not_live"
            });
          }
        });
      });
      // 画布的回执（opened / closed）只投辅助栏，画布自己不需要这份回声。
      bus.on("editor.clean_review_state", function (event) {
        var payload = (event && event.payload) || {};
        if (payload.pluginId !== EDITOR_PLUGIN_ID) return;
        stageState.panels.forEach(function (panel) {
          if (panel.plugin && panel.plugin.id === EDITOR_PLUGIN_ID && panel.frame) {
            notify(panel, "editor.clean_review_state", payload);
          }
        });
      });
      // 题篮变了，组卷/讲义画布要跟上；不广播的话它们只能等用户再点一次刷新
      bus.on("basket.changed", function (event) { broadcast("basket.changed", event.payload); });
      // 录题插件写库成功 → 题库画布刷新列表（宿主统一生成事件，插件之间不直连）
      // 录题插件写库成功 → 各端回流刷新（统一口径 system.question_updated）。
      // 老插件仍只认 question.updated，两个名字都广播一次，谁订谁生效，不会刷两遍。
      bus.on("system.question_updated", function (event) {
        broadcast("system.question_updated", event.payload);
        broadcast("question.updated", event.payload);
      });
      bus.on("question.updated", function (event) { broadcast("question.updated", event.payload); });
      // 中转站改动（暂存/删除/入库）→ 录题插件据此撤掉已走的题，不整批重载。
      bus.on("system.pending_updated", function (event) {
        broadcast("system.pending_updated", event.payload);
      });
      // 插件被热更新（PLUGIN_SPEC §1.7）：转给订阅了它的插件，画布水合由宿主自己处理
      bus.on("plugin.updated", function (event) { broadcast("plugin.updated", event.payload); });
      // 军令 #27：辅助栏那边接到的文件，宿主送进画布的收集筐。
      // 只有录题插件自己发的才算数——别的插件想往筐里塞东西，门都不给。
      bus.on("editor.collect_files", function (event) {
        var payload = (event && event.payload) || {};
        if (payload.pluginId !== EDITOR_PLUGIN_ID) return;
        var files = (payload.raw && payload.raw.files) || [];
        if (!Array.isArray(files) || !files.length) return;
        var editorTab = findPluginTab(EDITOR_PLUGIN_ID);
        if (editorTab && editorTab.frame && editorTab.state === "live") {
          notify(editorTab, "editor.collect_files", { files: files });
          return;
        }
        // 画布页签没开或已休眠：文件不许凭空消失，退回宿主自己入库（旧口径）。
        if (window.JzoIntake && typeof window.JzoIntake.ingestFiles === "function") {
          window.JzoIntake.ingestFiles(files, { source: "panel" });
        }
      });
      // 存储端/输出端的「去编辑」→ 宿主开录题页签并注入题号
      bus.on("system.open_editor", function (event) { openEditor(event.payload); });
      // 看板等只读端的「去题库」→ 宿主开活跃题库页签
      bus.on("system.open_bank", function (event) { openBank(event.payload); });
      // 录题端「保存并返回」→ 回到发起跳转的那个页签，老师不必自己找
      bus.on("system.return_from_editor", function (event) {
        var raw = (event.payload && event.payload.raw) || {};
        var origin = typeof raw.plugin_id === "string" ? raw.plugin_id : "";
        var tab = origin && origin !== EDITOR_PLUGIN_ID ? findPluginTab(origin) : null;
        if (tab) {
          activate(tab.key);
          dock("已回到「" + tab.title + "」。", "stage.editor.returned");
        } else {
          dock("没有可返回的来源页签，留在录题工作台。", "stage.editor.returned");
        }
      });
      // 录题端「保存成功 1 秒后自动收页」：关掉编辑器页签，切回发起端。
      // 列表的静默回流刷新由前面 system.question_updated 的广播负责，这里只管收尾。
      bus.on("system.editor_close", function (event) {
        var raw = (event.payload && event.payload.raw) || {};
        var origin = typeof raw.plugin_id === "string" ? raw.plugin_id : "";
        var editor = findPluginTab(EDITOR_PLUGIN_ID);
        var target = origin && origin !== EDITOR_PLUGIN_ID ? findPluginTab(origin) : null;
        if (editor) closeTab(editor.key);
        if (target) {
          activate(target.key);
          dock("已保存，录题页自动收起，回到「" + target.title + "」。", "stage.editor.closed");
        } else {
          dock("已保存，录题页自动收起。", "stage.editor.closed");
        }
      });
      bus.on("stage.broadcast", function (event) {
        var payload = event.payload || {};
        if (typeof payload.event === "string") broadcast(payload.event, payload.payload);
      });
    }
  }

  init();

  window.JzoStage = {
    openPlugin: openPlugin,
    updatePlugin: updatePlugin,
    rehydratePlugin: rehydratePlugin,
    setSidebarTree: setSidebarTree,
    setPluginCatalog: setPluginCatalog,
    commands: listCommands,
    activate: activate,
    close: closeTab,
    attachPanel: attachPanel,
    tabs: function () {
      return stageState.tabs.map(function (tab) {
        return {
          key: tab.key,
          title: tab.title,
          state: tab.state,
          kind: tab.kind,
          priority: tab.kind === "plugin" ? priorityOf(tab) : null,
          group: tab.kind === "plugin" ? groupKeyOf(tab) : "",
          weight: tab.kind === "plugin" ? weightOf(tab) : "native",
          suspended: tab.kind === "plugin" ? tab.suspended === true : false,
          singleton: tab.kind === "plugin" && tab.plugin && tab.plugin.stage
            ? tab.plugin.stage.singleton !== false
            : null
        };
      });
    },
    request: function (key, method, payload) {
      var tab = findTab(key);
      return tab ? request(tab, method, payload) : Promise.reject(new Error("页签不存在"));
    },
    /**
     * 定向投递（军令 #16 快捷键）：同一个插件可能既开着画布页签又住在右栏，
     * 两边都送到才算送达；休眠中的页签没有帧，如实回 false。
     */
    notifyPlugin: function (pluginId, event, payload) {
      var reached = false;
      var tab = findPluginTab(pluginId);
      if (tab && tab.frame && tab.state === "live") {
        notify(tab, event, payload);
        reached = true;
      }
      stageState.panels.forEach(function (panel) {
        if (panel.plugin && panel.plugin.id === pluginId && panel.frame) {
          notify(panel, event, payload);
          reached = true;
        }
      });
      return reached;
    },
    /**
     * 只投递给画布页签（军令 #27）：文件收集筐只住在画布里，
     * 辅助栏那张 iframe 收到同样的通知只会多收一份。
     */
    notifyCanvas: function (pluginId, event, payload) {
      var tab = findPluginTab(pluginId);
      if (!tab || !tab.frame || tab.state !== "live") return false;
      notify(tab, event, payload);
      return true;
    },
    broadcast: broadcast
  };
})();
