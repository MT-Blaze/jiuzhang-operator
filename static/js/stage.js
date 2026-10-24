/**
 * Stage：中栏画布的 Tabs 宿主。
 *
 * 职责边界（军令任务 3）：中栏只是「通用舞台」，底座负责挂标签页、挂 iframe、
 * 转发事件；业务画面一律由插件自己画。左、右、下三区仍由底座托管，
 * 插件只能经 HostBus 向指定区域投递数据，拿不到那三区的 DOM。
 *
 * 两类页签：
 *   - 原生页签：引导页与「设置与控制台」。引导页是舞台的永久兜底页，不可关闭
 *     （插件全崩也还有地方落脚）。对话不再住在中栏——军令 #15 把 AI 助手交还成
 *     右栏里的一个普通插件，底座不再为它保留任何特权入口。
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
  var DOCK_LOG_MAX = 120;
  var TAB_OVERFLOW = 10;            // 军令 #16 模块三：超过 10 个页签固定 120px + 横滚 + 分组合并
  var TAB_GROUP_MIN = 2;            // 组内凑满两页才收成下拉，单页收成下拉只是添堵
  var UNGROUPED_KEY = "ungrouped";  // 没进任何文件夹的插件，共用这一个集合分组

  // 插件能主动发的事件主题白名单：只许投给底座托管的三区与舞台选区，
  // 不许发 layout.* / ui.params.*（那是底座与人的地盘，防插件反向操控面板）。
  // system.open_editor 是三端分离架构的唯一跨端跳转口：存储端/输出端只读，
  // 改题目一律交给录题插件，由宿主负责开页签与注入题号。
  var PUBLISH_ALLOW = [
    "region.dock", "region.left", "region.right", "stage.selection",
    "system.open_editor", "system.return_from_editor", "system.editor_close",
    "system.open_bank"
  ];
  var EDITOR_PLUGIN_ID = "org.jiuzhang.editor";

  var tabsEl = document.getElementById("wsTabs");
  var bodyEl = document.getElementById("wsCanvasBody");
  var bus = window.JzoBus;
  var tabs = [];
  // 右栏辅助面板（sidebar.right）不占画布页签，但同样要能走 Host API：
  // 单独一张登记表，消息入口按 frame.contentWindow 反查它的插件身份。
  var panels = [];
  var activeKey = null;
  var requestSeq = 0;
  var openSeq = 0;
  var groupTree = [];        // 左栏那棵树的镜像：分组页签只显示文件夹名，名字从这里取
  var holders = {};          // 分组 key -> {chip, btn, list, count}
  var expandedKey = "";      // 同一时刻只许一个分组下拉摊开
  var scrollBtns = null;     // 页签栏溢出时的左右小箭头
  var immersiveKey = "";     // 沉浸全屏中的页签 key，空串表示没沉浸

  function priorityOf(tab) {
    var stage = tab.plugin && tab.plugin.stage;
    var value = stage && typeof stage.priority === "number" ? stage.priority : 0;
    return Math.max(-100, Math.min(100, value));
  }

  /**
   * 舞台优先级（stage.priority）的真实消费点：同排插件页签按优先级从高到低排，
   * 同优先级按打开先后。原生页签（引导）永远排第一，不参与抢位。
   * 排完交给 renderTabBar：页签挤爆时才把同组收成下拉、并上横滚（军令 #16 模块三）。
   */
  function orderPluginTabs() {
    if (!tabsEl) return;
    var pluginTabs = tabs.filter(function (tab) { return tab.kind === "plugin"; });
    pluginTabs.sort(function (a, b) {
      var delta = priorityOf(b) - priorityOf(a);
      return delta !== 0 ? delta : a.order - b.order;
    });
    // 判据只数插件页签，不数收成下拉后的条目：收完变少也不会反过来又摊开（来回抖动）
    var many = pluginTabs.length > TAB_OVERFLOW;
    renderTabBar(pluginTabs, many);
    paintOverflowBar(many);
  }

  function emit(topic, payload) {
    if (bus && typeof bus.emit === "function") bus.emit(topic, payload, { source: "stage" });
  }

  function dock(text, topic) {
    emit("region.dock", { text: text, topic: topic || "" });
  }

  function findTab(key) {
    for (var i = 0; i < tabs.length; i += 1) {
      if (tabs[i].key === key) return tabs[i];
    }
    return null;
  }

  function liveFrames() {
    return tabs.filter(function (tab) { return tab.kind === "plugin" && tab.state === "live"; });
  }

  function touch(tab) {
    tab.lastUsed = Date.now();
  }

  // ---------- 页签按钮 ----------
  function buildTabButton(tab) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "ws-tab";
    button.id = "wsTab_" + tab.key.replace(/[^a-zA-Z0-9_-]/g, "_");
    button.setAttribute("role", "tab");
    button.setAttribute("aria-selected", "false");
    button.setAttribute("aria-controls", tab.panel.id);
    button.setAttribute("data-tab", tab.key);

    var label = document.createElement("span");
    label.className = "ws-tab-label";
    label.textContent = tab.title;   // 插件名是不可信清单内容，只能 textContent
    button.appendChild(label);

    var state = document.createElement("span");
    state.className = "ws-tab-state";
    state.setAttribute("aria-hidden", "true");
    button.appendChild(state);
    tab.stateEl = state;

    if (tab.closable) {
      var close = document.createElement("span");
      close.className = "ws-tab-close";
      close.setAttribute("role", "button");
      close.setAttribute("tabindex", "0");
      close.setAttribute("aria-label", "关闭" + tab.title);
      close.textContent = "\u00d7";
      close.addEventListener("click", function (event) {
        event.stopPropagation();
        closeTab(tab.key);
      });
      close.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          event.stopPropagation();
          closeTab(tab.key);
        }
      });
      button.appendChild(close);
      tab.closeEl = close;
    }

    button.addEventListener("click", function () { activate(tab.key); });
    // 双击页签=沉浸全屏（军令 #16 模块三第 1 条）。单击仍照常切页，两次手势互不牺牲。
    button.addEventListener("dblclick", function (event) {
      if (event.target && event.target.closest && event.target.closest(".ws-tab-close")) return;
      event.preventDefault();
      toggleImmersive(tab.key);
    });
    tab.button = button;
    return button;
  }

  function paintTabState(tab) {
    if (!tab.stateEl) return;
    if (tab.kind !== "plugin") {
      tab.stateEl.textContent = "";
      return;
    }
    tab.stateEl.textContent = tab.state === "live" ? "" : "休眠";
    tab.button.setAttribute("data-state", tab.state);
    tab.button.setAttribute("title", tab.state === "live" ? tab.title : tab.title + "（已休眠，点击唤醒）");
  }

  // ---------- iframe 挂载与协议 ----------
  function mountFrame(tab) {
    if (tab.state === "live") return Promise.resolve(tab);
    var panel = tab.panel;
    panel.textContent = "";

    var frame = document.createElement("iframe");
    frame.className = "ws-plugin-frame";
    frame.setAttribute("sandbox", SANDBOX);
    frame.setAttribute("title", (tab.plugin.name || tab.plugin.id) + " 画布");
    frame.setAttribute("loading", "lazy");
    frame.src = tab.plugin.entry_url;
    tab.frame = frame;
    tab.pending = new Map();
    panel.appendChild(frame);

    tab.state = "live";
    paintTabState(tab);

    return new Promise(function (resolve) {
      var settled = false;
      var timer = window.setTimeout(function () {
        if (settled) return;
        settled = true;
        dock("插件「" + (tab.plugin.name || tab.plugin.id) + "」激活超时（30s），已保留页签但不再等待。", "plugin.timeout");
        resolve(tab);
      }, REQUEST_TIMEOUT_MS);

      frame.addEventListener("load", function () {
        request(tab, "plugin.activate", { slot: "stage.center" })
          .then(function (result) {
            if (settled) return;
            settled = true;
            window.clearTimeout(timer);
            tab.ready = Boolean(result && result.ready);
            dock("插件「" + (tab.plugin.name || tab.plugin.id) + "」已挂载" + (tab.ready ? "并就绪。" : "，但未回 ready。"), "plugin.mounted");
            pushParams(tab);
            deliverEditorIntent(tab);
            deliverBankQuery(tab);
            resolve(tab);
          })
          .catch(function (error) {
            if (settled) return;
            settled = true;
            window.clearTimeout(timer);
            tab.ready = false;
            dock("插件「" + (tab.plugin.name || tab.plugin.id) + "」激活失败：" + error.message, "plugin.error");
            resolve(tab);
          });
      });

      frame.addEventListener("error", function () {
        if (settled) return;
        settled = true;
        window.clearTimeout(timer);
        showFrameError(tab, "插件入口加载失败：" + String(tab.plugin.entry_url || ""));
        resolve(tab);
      });
    });
  }

  function showFrameError(tab, message) {
    tab.state = "error";
    tab.frame = null;
    tab.panel.textContent = "";
    var box = document.createElement("div");
    box.className = "ws-frame-error";
    box.setAttribute("role", "alert");
    box.textContent = message + "（底座仍可继续使用引导页）";
    tab.panel.appendChild(box);
    paintTabState(tab);
  }

  function hibernate(tab, reason) {
    if (tab.kind !== "plugin" || tab.state !== "live") return;
    // 尽力通知，不等回复：休眠不能被一个装死的插件拖住
    notify(tab, "plugin.deactivate", { reason: reason || "lru" });
    if (tab.frame && tab.frame.parentNode) tab.frame.parentNode.removeChild(tab.frame);
    tab.frame = null;
    tab.state = "sleep";
    tab.ready = false;
    if (tab.pending) tab.pending.clear();
    tab.panel.textContent = "";
    var note = document.createElement("p");
    note.className = "ws-frame-note";
    note.textContent = "此页签已休眠（同时存活的插件页最多 " + MAX_LIVE_FRAMES + " 个）。点页签即唤醒。";
    tab.panel.appendChild(note);
    paintTabState(tab);
    dock("插件「" + (tab.plugin.name || tab.plugin.id) + "」已休眠" + (reason ? "（" + reason + "）" : "") + "。", "stage.tab.sleep");
    emit("stage.tab.sleep", { key: tab.key, pluginId: tab.plugin.id });
  }

  /** 深休眠名额只数重型页签：light 插件后台只是浅休眠，不挤这 3 个常驻位。 */
  function enforceLru() {
    var live = heavyLiveFrames();
    while (live.length > MAX_LIVE_FRAMES) {
      var oldest = null;
      live.forEach(function (tab) {
        if (tab.key === activeKey) return;
        if (!oldest || tab.lastUsed < oldest.lastUsed) oldest = tab;
      });
      if (!oldest) break;   // 全是活动页：不硬摘，宁可多留一个也不打断用户
      hibernate(oldest, "LRU");
      live = heavyLiveFrames();
    }
  }

  function request(tab, method, payload) {
    return new Promise(function (resolve, reject) {
      if (!tab.frame || !tab.frame.contentWindow) {
        reject(new Error("插件页未在运行"));
        return;
      }
      requestSeq += 1;
      var id = "r" + requestSeq + "_" + Date.now().toString(36);
      var timer = window.setTimeout(function () {
        if (!tab.pending || !tab.pending.has(id)) return;
        tab.pending.delete(id);
        reject(new Error("插件响应超时（" + Math.round(REQUEST_TIMEOUT_MS / 1000) + "s）"));
      }, REQUEST_TIMEOUT_MS);

      tab.pending.set(id, {
        resolve: function (result) { window.clearTimeout(timer); resolve(result); },
        reject: function (error) { window.clearTimeout(timer); reject(error); }
      });

      try {
        tab.frame.contentWindow.postMessage({
          protocol: PROTOCOL,
          id: id,
          kind: "request",
          method: method,
          payload: payload || {}
        }, "*");
      } catch (error) {
        tab.pending.delete(id);
        window.clearTimeout(timer);
        reject(error);
      }
    });
  }

  function notify(tab, event, payload) {
    if (!tab.frame || !tab.frame.contentWindow) return;
    try {
      tab.frame.contentWindow.postMessage({
        protocol: PROTOCOL,
        kind: "notification",
        event: event,
        payload: payload || null
      }, "*");
    } catch (error) {
      // 通知丢了不致命，记一笔就够
      dock("向插件「" + (tab.plugin.name || tab.plugin.id) + "」发通知失败：" + error.message, "plugin.error");
    }
  }

  /** 广播覆盖中栏活页签与右栏面板：AI 助手住在右栏，选区、回流与参数变化都得收到。 */
  function broadcast(event, payload) {
    var targets = liveFrames().concat(panels.filter(function (panel) { return panel.frame; }));
    targets.forEach(function (tab) { notify(tab, event, payload); });
  }

  // ---------- 右栏辅助面板（sidebar.right） ----------
  // 面板与画布页签共用同一套 jzo-plugin/1 协议和 Host API：插件只交出一个 iframe，
  // 身份由宿主按清单绑定，bank.* / basket.* / draft.* 的写令牌仍留在宿主侧。
  function attachPanel(frame, plugin) {
    var handle = {
      kind: "panel",
      key: "panel:" + ((plugin && plugin.id) || "unknown"),
      plugin: plugin,
      frame: frame,
      pending: new Map(),
      relayWindow: 0,
      relayCount: 0
    };
    panels.push(handle);
    return {
      request: function (method, payload) { return request(handle, method, payload); },
      notify: function (event, payload) { return notify(handle, event, payload); },
      detach: function () {
        var index = panels.indexOf(handle);
        if (index >= 0) panels.splice(index, 1);
        if (handle.pending) handle.pending.clear();
      }
    };
  }

  // ---------- 插件数据通道（Host API 转发） ----------
  // 插件不直连数据库、也不联网；它只能申请下列方法，由宿主按「当前页签自己的
  // plugin.id」去查接口。插件在 payload 里自报 plugin_id 一律不认，防止串库。
  // 读接口开放；题篮写操作由宿主代取一次性令牌（插件永远看不到令牌）。
  var RELAY_METHODS = [
    "bank.list", "bank.stats", "bank.get", "bank.random", "bank.create",
    "bank.active_list", "bank.active_stats",
    "bank.topics", "bank.topic_notes", "bank.review", "bank.update", "bank.delete",
    "bank.dashboard_stats", "bank.dashboard_heatmap",
    "basket.list", "basket.add", "basket.active_add", "basket.remove", "basket.clear",
    "asset.upload",
    "draft.save", "draft.load",
    // 军令 #15：AI 助手降级成一个普通插件后，它能用的口子只有这一排。
    // 对话、改写、读清单、读工作区快照、装插件、设面板参数、开页签全部由宿主代办；
    // 数据库、写令牌与宿主 DOM 一道门都没开。
    "agent.chat", "agent.refine", "plugins.list", "workspace.state",
    "plugin.install_url", "ui.params.set", "editor.apply_patch",
    "stage.open_bank", "stage.open_editor"
  ];
  // 智能体接口只对清单里声明了 ai:invoke 的插件开放：
  // 别的插件即使猜对方法名，也只会拿到 PERMISSION_DENIED。
  var AI_ONLY_METHODS = [
    "agent.chat", "agent.refine", "plugin.install_url",
    "ui.params.set", "editor.apply_patch", "stage.open_bank", "stage.open_editor"
  ];
  var AI_INVOKE_PERMISSION = "ai:invoke";
  // 助手要读的两种清单：实现写在 relayAgent 里，分发就必须走到 relayAgent。
  // 它们不在 AI_ONLY_METHODS 里（任何插件都可以读清单），所以得单独点名——
  // 漏点一次，请求就会一路掉到 relay 末尾的分支上（真机曾因此把题篮清空）。
  var AGENT_READ_METHODS = ["plugins.list", "workspace.state"];
  var CHAT_HISTORY_MAX = 12;
  var AGENT_TIMEOUT_MS = 60000;      // 模型一轮回答可以慢，但不能无限等
  var OPEN_BANK_QUERY_MAX = 40;

  // 录题插件的写入目标不再写死：跨页签共享的题库通道走「活跃 provider」，
  // 由底座按 data/bank_provider.json 解析（PLUGIN_SPEC §2.6.1）。官方 core-bank
  // 只是默认值——取不到 provider 时仍用它，不能让「读不到配置」打死整条数据通道。
  var BANK_PROVIDER_DEFAULT = "org.jiuzhang.core-bank";
  var bankProviderId = BANK_PROVIDER_DEFAULT;
  var bankProviderCall = null;

  function bankProviderBase() {
    return "/api/bank/plugins/" + encodeURIComponent(bankProviderId);
  }

  function loadBankProvider() {
    if (!bankProviderCall) {
      bankProviderCall = fetchJson("/api/bank/provider").then(function (info) {
        var id = info && info.plugin_id;
        if (typeof id === "string" && id) bankProviderId = id;
        return info;
      }, function () { return null; });
    }
    return bankProviderCall;
  }
  loadBankProvider();   // 启动即取；插件要等用户点击才激活，届时已解析完
  var RELAY_TIMEOUT_MS = 20000;
  var RELAY_WINDOW_MS = 10000;
  var RELAY_MAX_PER_WINDOW = 80;
  var ID_RE = /^[A-Za-z0-9_-]{1,80}$/;
  // 大纲节点 ID：tp_ + 层别码（bo/ch/se/kx）+ 8 位十六进制，定长 13（bank/schema.sql）
  var TOPIC_ID_RE = /^tp_(bo|ch|se|kx)[0-9a-f]{8}$/;

  function replyHost(tab, message, ok, value) {
    if (!tab.frame || !tab.frame.contentWindow) return;
    var packet = { protocol: PROTOCOL, id: message.id, kind: "response", ok: ok };
    if (ok) {
      packet.result = value === undefined ? {} : value;
    } else {
      packet.error = {
        code: (value && value.code) || "HOST_ERROR",
        message: (value && value.message) || "宿主拒绝了请求",
        retryable: Boolean(value && value.retryable)
      };
    }
    try {
      tab.frame.contentWindow.postMessage(packet, "*");
    } catch (error) {
      // 帧已经被摘掉：回复无处可去，忽略
    }
  }

  /** 每页签限流，挡住插件里失控的循环把本机 SQLite 打满。 */
  function relayBudget(tab) {
    var now = Date.now();
    if (!tab.relayWindow || now - tab.relayWindow > RELAY_WINDOW_MS) {
      tab.relayWindow = now;
      tab.relayCount = 0;
    }
    tab.relayCount += 1;
    return tab.relayCount <= RELAY_MAX_PER_WINDOW;
  }

  // ---------- 草稿托管（宿主代持 localStorage，按工作区分箱） ----------
  // 沙箱 iframe 是不透明源（只给 allow-scripts，不同源），插件里访问
  // localStorage 会直接抛 SecurityError——「关 Tab 不丢草稿」这件事只能由同源的宿主来做。
  // 插件通过 draft.save / draft.load 两个 RPC 把表单态交给宿主，宿主按「工作区 + plugin.id」分箱：
  // 切库重启后各区只看自己那箱，A 区没录完的题不会串进 B 区，切回来时还在。
  // 这里绝不碰后端题库：草稿是浏览器本地易失态，不进库、不出网。
  var DRAFT_NS = "jzo.draft.";
  var DRAFT_KEY_RE = /^[A-Za-z0-9_.:-]{1,80}$/;
  var DRAFT_MAX_CHARS = 200000;
  var DRAFT_TTL_MS = 14 * 24 * 60 * 60 * 1000;   // 两周没来取的草稿算陈旧，随写随清
  var DRAFT_BOX_MAX = 60;                        // 每箱最多 60 槽，超了丢最旧的
  var DRAFT_WS_RE = /^[A-Za-z0-9_-]{1,40}$/;
  // 分箱槽位的工作区段只有两种来源：default 与底座生成、一律带 ws_ 前缀的 id（app/api/workspaces.py）；
  // 插件 id 是反向域名，首段恒为 org/com/net 之类，永不会长这样。判「是否已分箱」必须用这个形状——
  // 只看「有没有点」会在 B 区开机时把 A 区已分箱的草稿当旧槽搬走。
  var DRAFT_BOXED_HEAD_RE = /^(default|ws_[A-Za-z0-9_-]{4,})\./;
  var draftWorkspace = "";                       // 当前工作区 id；没拿到之前一槽都不碰
  var draftBoxReady = null;

  function draftPrefix(workspaceId) {
    return DRAFT_NS + workspaceId + ".";
  }

  function draftSlot(pluginId, key) {
    return draftPrefix(draftWorkspace) + pluginId + "." + key;
  }

  function draftBoxUnknown() {
    return { ok: false, reason: "工作区身份未就绪，草稿箱未开放" };
  }

  function draftEachSlot(workspaceId, visit) {
    var prefix = draftPrefix(workspaceId);
    var slots = [];
    for (var i = 0; i < window.localStorage.length; i += 1) {
      var slot = window.localStorage.key(i);
      if (slot && slot.indexOf(prefix) === 0) slots.push(slot);
    }
    slots.forEach(visit);
    return slots.length;
  }

  /** 槽位信封 {saved_at, value}；分箱之前的裸值按「无时间戳」收编，下次写入自动补信封。 */
  function draftUnwrap(text) {
    var parsed = JSON.parse(text);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)
      && typeof parsed.saved_at === "number" && "value" in parsed) return parsed;
    return { saved_at: 0, value: parsed };
  }

  /** 清掉本箱里过期与超量的槽位；返回删除数。saved_at 为 0 的旧槽排在最先丢。 */
  function sweepDraftBox() {
    if (!draftWorkspace) return 0;
    var now = Date.now();
    var alive = [];
    var removed = 0;
    draftEachSlot(draftWorkspace, function (slot) {
      var stamp = 0;
      try {
        var text = window.localStorage.getItem(slot);
        if (!text) return;
        stamp = draftUnwrap(text).saved_at;
      } catch (error) {
        window.localStorage.removeItem(slot);
        removed += 1;
        return;
      }
      if (stamp && now - stamp > DRAFT_TTL_MS) {
        window.localStorage.removeItem(slot);
        removed += 1;
        return;
      }
      alive.push({ slot: slot, saved_at: stamp });
    });
    if (alive.length <= DRAFT_BOX_MAX) return removed;
    alive.sort(function (a, b) { return a.saved_at - b.saved_at; });
    var drop = alive.length - DRAFT_BOX_MAX;
    for (var i = 0; i < drop; i += 1) {
      window.localStorage.removeItem(alive[i].slot);
      removed += 1;
    }
    return removed;
  }

  /** 老命名空间 jzo.draft.<插件 id>.<键> 里没有工作区段；带工作区段的槽位一律不碰，别区的不许搬进本区。 */
  function migrateLegacyDrafts(workspaceId) {
    var target = draftPrefix(workspaceId);
    var slots = [];
    for (var i = 0; i < window.localStorage.length; i += 1) {
      var slot = window.localStorage.key(i);
      if (!slot || slot.indexOf(DRAFT_NS) !== 0 || slot.indexOf(target) === 0) continue;
      if (DRAFT_BOXED_HEAD_RE.test(slot.slice(DRAFT_NS.length))) continue;
      if (slot.slice(DRAFT_NS.length).indexOf(".") < 0) continue;
      slots.push(slot);
    }
    slots.forEach(function (slot) {
      var next = target + slot.slice(DRAFT_NS.length);
      var text = window.localStorage.getItem(slot);
      if (text && !window.localStorage.getItem(next)) window.localStorage.setItem(next, text);
      window.localStorage.removeItem(slot);
    });
    return slots.length;
  }

  /** 向底座问一次「我现在住在哪个工作区」；问不到就宁可不开箱，也绝不把草稿挂到别的区上。 */
  function resolveDraftBox() {
    if (draftBoxReady) return draftBoxReady;
    draftBoxReady = fetch("/api/settings", { cache: "no-store" })
      .then(function (response) { return response.ok ? response.json() : null; })
      .then(function (data) {
        var id = data && typeof data.workspace_id === "string" ? data.workspace_id : "";
        if (!DRAFT_WS_RE.test(id)) return "";
        draftWorkspace = id;
        try {
          migrateLegacyDrafts(id);
          sweepDraftBox();
        } catch (error) {
          // 搬家/清扫失败只影响陈旧槽位回收，不拦老师当场存草稿。
        }
        return id;
      })
      .catch(function () { return ""; });
    return draftBoxReady;
  }

  resolveDraftBox();   // 页签挂载前先把箱子落到哪个区问清楚，插件第一次 draft.load 就不用等

  /** 宿主代存草稿：value 为 null 即清除。返回是否成功（配额满/非法键/未分箱都如实报失败）。 */
  function saveDraft(pluginId, key, value) {
    if (!DRAFT_KEY_RE.test(key)) return { ok: false, reason: "草稿键不合法" };
    if (!draftWorkspace) return draftBoxUnknown();
    var slot = draftSlot(pluginId, key);
    try {
      if (value === null || value === undefined) {
        window.localStorage.removeItem(slot);
        return { ok: true, cleared: true };
      }
      var envelope = { saved_at: Date.now(), value: value };
      var text = JSON.stringify(envelope);
      if (text.length > DRAFT_MAX_CHARS) return { ok: false, reason: "草稿过大，未保存" };
      window.localStorage.setItem(slot, text);
      sweepDraftBox();
      return { ok: true, saved_at: envelope.saved_at };
    } catch (error) {
      return { ok: false, reason: String(error && error.name || "存储失败") };
    }
  }

  function loadDraft(pluginId, key) {
    if (!DRAFT_KEY_RE.test(key)) return { ok: false, reason: "草稿键不合法" };
    if (!draftWorkspace) return draftBoxUnknown();
    try {
      var text = window.localStorage.getItem(draftSlot(pluginId, key));
      return { ok: true, value: text ? draftUnwrap(text).value : null };
    } catch (error) {
      return { ok: false, reason: String(error && error.name || "读取失败") };
    }
  }

  function textValue(payload, key, max) {
    var value = payload[key];
    if (typeof value !== "string") return "";
    return value.trim().slice(0, max);
  }

  /** 「全部 / all」是面板的展示值，到了查询层必须变成「不过滤」。 */
  function filterValue(payload, key, max) {
    var value = textValue(payload, key, max);
    if (value === "全部" || value.toLowerCase() === "all") return "";
    return value;
  }

  function intValue(payload, key, fallback, min, max) {
    var value = Number(payload[key]);
    if (!Number.isFinite(value)) return fallback;
    value = Math.floor(value);
    if (value < min) return fallback;
    return Math.min(value, max);
  }

  function fetchJson(url, options) {
    var settings = options || {};
    settings.headers = Object.assign({ Accept: "application/json" }, settings.headers || {});
    var controller = typeof AbortController === "function" ? new AbortController() : null;
    var timer = 0;
    // 默认 20s 够用，智能体接口要等模型：整条转发链路的上限由调用方给。
    var timeoutMs = Number(settings.timeout);
    delete settings.timeout;
    if (!(timeoutMs >= 1000)) timeoutMs = RELAY_TIMEOUT_MS;
    if (controller) {
      settings.signal = controller.signal;
      timer = window.setTimeout(function () { controller.abort(); }, timeoutMs);
    }
    return fetch(url, settings)
      .then(function (response) {
        return response.text().then(function (text) {
          var data = null;
          try {
            data = text ? JSON.parse(text) : {};
          } catch (error) {
            data = null;
          }
          if (!response.ok) {
            var detail = data && data.detail;
            var message = "";
            if (typeof detail === "string") {
              message = detail;
            } else if (detail && typeof detail === "object") {
              // 校验失败是 {message, errors[]}：把首条具体错误带出去，插件才能告诉老师哪里错了
              var head = typeof detail.message === "string" ? detail.message : "";
              var first = Array.isArray(detail.errors) && typeof detail.errors[0] === "string" ? detail.errors[0] : "";
              message = head && first ? head + "：" + first : head || first;
            }
            var failure = new Error(message || "宿主接口返回 HTTP " + response.status);
            failure.status = response.status;
            failure.detail = detail;
            throw failure;
          }
          if (data === null) throw new Error("宿主接口返回了非 JSON 内容");
          return data;
        });
      })
      .then(function (data) {
        if (timer) window.clearTimeout(timer);
        return data;
      }, function (error) {
        if (timer) window.clearTimeout(timer);
        if (error && error.name === "AbortError") {
          throw new Error("宿主接口超时（" + Math.round(timeoutMs / 1000) + "s）");
        }
        throw error;
      });
  }

  /** 写操作：先取一次性令牌（用后即焚），再把令牌放进请求头，插件全程不可见。 */
  function withWriteToken(url, options) {
    return fetchJson("/api/settings").then(function (data) {
      var token = data && data.local_token;
      if (!token) throw new Error("拿不到本地写操作令牌");
      options.headers = Object.assign({}, options.headers || {}, { "X-JZO-Token": token });
      return fetchJson(url, options);
    });
  }

  function plainObject(value) {
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  }

  function urlValue(value, max) {
    var text = String(value == null ? "" : value).trim().slice(0, max || 500);
    return /^https?:\/\//i.test(text) ? text : "";
  }

  /** 历史轮次只留 role/content 两个字符串字段，长度设限——模型不必看见插件的内部态。 */
  function cleanHistory(value) {
    if (!Array.isArray(value)) return [];
    return value.slice(-CHAT_HISTORY_MAX)
      .map(function (turn) {
        var item = plainObject(turn);
        var role = textValue(item, "role", 10);
        if (role !== "assistant" && role !== "sys") role = "user";
        return { role: role, content: textValue(item, "content", 2000) };
      })
      .filter(function (turn) { return turn.content; });
  }

  /**
   * 智能体接口（军令 #15）。AI 助手是一个普通插件：它不能读库、不能碰宿主 DOM、
   * 更没有鼠标键盘——所有「查题库 / 开页签 / 改面板 / 装插件」都只能到这里，
   * 由宿主用它自己的身份去做，做完把结果摘要回给插件。
   */
  function relayAgent(method, payload, done, fail, failWith) {
    var jsonHeaders = { "Content-Type": "application/json" };

    if (method === "agent.chat") {
      var userInput = textValue(payload, "user_input", 4000);
      if (!userInput) { failWith("BAD_REQUEST", "user_input 不能为空"); return; }
      fetchJson("/api/agent/chat", {
        method: "POST",
        headers: jsonHeaders,
        timeout: AGENT_TIMEOUT_MS,
        body: JSON.stringify({
          user_input: userInput,
          task_id: textValue(payload, "task_id", 60) || "chat_" + Date.now(),
          context: plainObject(payload.context),
          history: cleanHistory(payload.history)
        })
      }).then(done, fail);
      return;
    }

    if (method === "agent.refine") {
      var instruction = textValue(payload, "instruction", 400);
      if (!instruction) { failWith("BAD_REQUEST", "instruction 不能为空"); return; }
      fetchJson("/api/agent/refine", {
        method: "POST",
        headers: jsonHeaders,
        timeout: AGENT_TIMEOUT_MS,
        body: JSON.stringify({
          question: plainObject(payload.question),
          instruction: instruction,
          field: textValue(payload, "field", 20) === "solution" ? "solution" : "stem",
          task_id: textValue(payload, "task_id", 60) || "refine_" + Date.now()
        })
      }).then(function (response) {
        // 后端把正文埋在 data / fallback 里：摊平成 {value, note, field}，插件不必猜信封
        var data = plainObject(response && response.data);
        var envelope = data.value === undefined ? plainObject(response && response.fallback) : data;
        done({
          ok: !(response && response.type === "error"),
          field: textValue(envelope, "field", 20) || "stem",
          value: textValue(envelope, "value", 20000),
          note: textValue(envelope, "note", 300)
        });
      }, fail);
      return;
    }

    if (method === "plugins.list") {
      fetchJson("/api/plugins").then(function (data) {
        done({
          plugins: ((data && data.plugins) || []).map(function (item) {
            return {
              id: item.id,
              name: item.name,
              version: item.version,
              kind: item.kind,
              description: textValue(item, "description", 200),
              capabilities: item.capabilities || [],
              slots: item.slots || [],
              enabled: item.enabled !== false
            };
          })
        });
      }, fail);
      return;
    }

    if (method === "workspace.state") {
      var snapshot = window.JzoWorkspace && typeof window.JzoWorkspace.stateSnapshot === "function"
        ? window.JzoWorkspace.stateSnapshot() : null;
      if (!snapshot) { failWith("NOT_READY", "宿主工作区快照尚未就绪"); return; }
      done(snapshot);
      return;
    }

    if (method === "plugin.install_url") {
      // 与索引页【在线安装】完全同款的落地校验；令牌仍由宿主代取，插件不可见。
      var zipUrl = urlValue(payload.url, 500);
      if (!zipUrl) { failWith("BAD_URL", "只允许 http(s) 直链"); return; }
      var mirrors = (Array.isArray(payload.mirrors) ? payload.mirrors : [])
        .map(function (item) { return urlValue(item, 500); })
        .filter(Boolean).slice(0, 6);
      withWriteToken("/api/plugins/install-url", {
        method: "POST",
        headers: jsonHeaders,
        timeout: AGENT_TIMEOUT_MS,
        body: JSON.stringify({
          url: zipUrl, mirrors: mirrors, replace: payload.replace === true
        })
      }).then(function (result) {
        if (window.JzoWorkspace && typeof window.JzoWorkspace.refreshPlugins === "function") {
          window.JzoWorkspace.refreshPlugins();
        }
        done(result);
      }, function (error) {
        if (error && error.status === 409) {
          failWith("PLUGIN_EXISTS",
            String((error.detail && error.detail.message) || error.message || "插件已安装"), false);
          return;
        }
        fail(error);
      });
      return;
    }

    if (method === "ui.params.set") {
      if (!window.JzoWorkspace || typeof window.JzoWorkspace.applyAiParams !== "function") {
        failWith("NOT_READY", "宿主面板仲裁器未就绪");
        return;
      }
      var outcome = window.JzoWorkspace.applyAiParams(
        payload.params, payload.snapshot, textValue(payload, "plugin_id", 80));
      if (outcome && outcome.error) {
        failWith(outcome.error.code || "PARAM_REJECTED", outcome.error.message);
        return;
      }
      done(outcome);
      return;
    }

    if (method === "editor.apply_patch") {
      var patchValue = textValue(payload, "value", 20000);
      if (!patchValue) { failWith("BAD_REQUEST", "回填内容为空"); return; }
      var patch = {
        id: textValue(payload, "id", 80),
        field: textValue(payload, "field", 20) === "solution" ? "solution" : "stem",
        value: patchValue
      };
      broadcast("editor.apply_patch", patch);
      dock("AI 助手请求把改写的" + (patch.field === "solution" ? "解析" : "题干") + "回填到录题表单。",
        "agent.patch");
      done({ ok: true, field: patch.field, id: patch.id });
      return;
    }

    if (method === "stage.open_bank") {
      var bankQuery = textValue(payload, "query", OPEN_BANK_QUERY_MAX);
      var bankQuestionId = textValue(payload, "question_id", 80);
      if (!ID_RE.test(bankQuestionId)) bankQuestionId = "";
      openBank({
        pluginId: "agent",
        raw: { query: bankQuery, question_id: bankQuestionId }
      });
      done({ ok: true, query: bankQuery, question_id: bankQuestionId });
      return;
    }

    if (method === "stage.open_editor") {
      var editorQuestionId = textValue(payload, "question_id", 80);
      if (!editorQuestionId) { failWith("BAD_REQUEST", "question_id 不能为空"); return; }
      openEditor({ pluginId: "agent", raw: { question_id: editorQuestionId } });
      done({ ok: true, question_id: editorQuestionId });
      return;
    }

    failWith("UNSUPPORTED_METHOD", "宿主未开放方法：" + String(method).slice(0, 60));
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
      replyHost(tab, message, false, {
        code: "HOST_" + (error.status || 0),
        message: String((error && error.message) || "宿主请求失败").slice(0, 200),
        retryable: Boolean(error && error.status >= 500)
      });
    }

    function failWith(code, text, retryable) {
      replyHost(tab, message, false, {
        code: code,
        message: String(text || "宿主请求失败").slice(0, 200),
        retryable: Boolean(retryable)
      });
    }

    // 智能体通道：AI 助手插件的申请一律在这里由宿主代执行（军令 #15）。
    if (AI_ONLY_METHODS.indexOf(method) >= 0 || AGENT_READ_METHODS.indexOf(method) >= 0) {
      relayAgent(method, payload, done, fail, failWith);
      return;
    }

    if (method === "asset.upload") {
      // 框选切图只交 data URL，落盘位置与文件名全由底座决定；插件仍然看不到令牌。
      var assetPermissions = (tab.plugin && tab.plugin.permissions) || [];
      if (assetPermissions.indexOf("assets:write") < 0) {
        replyHost(tab, message, false, {
          code: "FORBIDDEN",
          message: "插件未声明 assets:write 权限，不能上传配图"
        });
        return;
      }
      var dataUrl = typeof payload.data_url === "string" ? payload.data_url : "";
      if (!dataUrl) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "缺少待上传的 data_url" });
        return;
      }
      if (dataUrl.length > 12 * 1024 * 1024) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "图片过大（解码后上限 8 MiB）" });
        return;
      }
      withWriteToken("/api/assets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data_url: dataUrl })
      }).then(done, fail);
      return;
    }

    if (method === "bank.create") {
      var permissions = (tab.plugin && tab.plugin.permissions) || [];
      if (permissions.indexOf("questions:write") < 0) {
        replyHost(tab, message, false, {
          code: "FORBIDDEN",
          message: "插件未声明 questions:write 权限，不能写入题库"
        });
        return;
      }
      var question = payload.question;
      if (!question || typeof question !== "object" || Array.isArray(question)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "缺少待写入的 question 对象" });
        return;
      }
      withWriteToken(
        bankProviderBase() + "/questions",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: question })
        }
      ).then(function (result) {
        emit("system.question_updated", {
          action: "create",
          id: result && result.id,
          pluginId: tab.plugin.id
        });
        done(result);
      }, fail);
      return;
    }

    if (method === "bank.update") {
      // 人工审核页的一键修复：与新增同权——必须先声明 questions:write，令牌仍留在宿主侧
      var writePermissions = (tab.plugin && tab.plugin.permissions) || [];
      if (writePermissions.indexOf("questions:write") < 0) {
        replyHost(tab, message, false, {
          code: "FORBIDDEN",
          message: "插件未声明 questions:write 权限，不能修改题库"
        });
        return;
      }
      var targetId = textValue(payload, "id", 80);
      if (!ID_RE.test(targetId)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "待修改的题目 id 不合法" });
        return;
      }
      var patch = payload.question;
      if (!patch || typeof patch !== "object" || Array.isArray(patch)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "缺少待写入的 question 对象" });
        return;
      }
      withWriteToken(
        bankProviderBase() + "/questions/"
          + encodeURIComponent(targetId),
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: patch })
        }
      ).then(function (result) {
        emit("system.question_updated", {
          action: "update",
          id: result && result.id,
          pluginId: tab.plugin.id
        });
        done(result);
      }, fail);
      return;
    }

    if (method === "bank.delete") {
      // 删题与新增同权：必须先声明 questions:write，令牌仍留在宿主侧，插件不碰。
      var deletePermissions = (tab.plugin && tab.plugin.permissions) || [];
      if (deletePermissions.indexOf("questions:write") < 0) {
        replyHost(tab, message, false, {
          code: "FORBIDDEN",
          message: "插件未声明 questions:write 权限，不能删除题库题目"
        });
        return;
      }
      var deleteId = textValue(payload, "id", 80);
      if (!ID_RE.test(deleteId)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "待删除的题目 id 不合法" });
        return;
      }
      withWriteToken(
        bankProviderBase() + "/questions/"
          + encodeURIComponent(deleteId),
        { method: "DELETE" }
      ).then(function (result) {
        emit("system.question_updated", {
          action: "delete",
          id: (result && result.id) || deleteId,
          pluginId: tab.plugin.id
        });
        done(result);
      }, fail);
      return;
    }

    if (method === "bank.review") {
      var reviewParams = new URLSearchParams();
      var flag = filterValue(payload, "flag", 32);
      if (flag && flag !== "全部") reviewParams.set("flag", flag);
      reviewParams.set("page", String(intValue(payload, "page", 1, 1, 10000)));
      reviewParams.set("page_size", String(intValue(payload, "page_size", 20, 1, 100)));
      fetchJson(sharedBase + "/review?" + reviewParams.toString()).then(done, fail);
      return;
    }

    if (method === "bank.stats" || method === "bank.active_stats") {
      // 浏览型插件没有自己的题库：显式要「活跃题库」的计数，不拿页签 id 去猜库
      fetchJson((method === "bank.active_stats" ? sharedBase : base) + "/stats").then(done, fail);
      return;
    }

    // 数据看板两条只读通道：全局端点，跟页签自己的库无关，永远读活跃题库
    if (method === "bank.dashboard_stats") {
      fetchJson("/api/bank/dashboard/stats").then(done, fail);
      return;
    }

    if (method === "bank.dashboard_heatmap") {
      fetchJson("/api/bank/dashboard/heatmap").then(done, fail);
      return;
    }

    if (method === "bank.list" || method === "bank.active_list") {
      var params = new URLSearchParams();
      params.set("grade", filterValue(payload, "grade", 32));
      params.set("difficulty", filterValue(payload, "difficulty", 32));
      params.set("type", filterValue(payload, "type", 32));
      params.set("chapter", filterValue(payload, "chapter", 64));
      params.set("textbook", filterValue(payload, "textbook", 64));
      var topic = textValue(payload, "topic", 20);
      if (topic && !TOPIC_ID_RE.test(topic)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "考向节点 id 不合法" });
        return;
      }
      if (topic) params.set("topic", topic);
      var search = textValue(payload, "q", 100);
      if (search) params.set("q", search);
      params.set("page", String(intValue(payload, "page", 1, 1, 10000)));
      params.set("page_size", String(intValue(payload, "page_size", 20, 1, 100)));
      // active_list 与 bank.get / bank.topics 同源：浏览端永远看当前活跃题库
      var listBase = method === "bank.active_list" ? sharedBase : base;
      fetchJson(listBase + "/questions?" + params.toString()).then(done, fail);
      return;
    }

    if (method === "bank.get") {
      var questionId = textValue(payload, "id", 80);
      if (!ID_RE.test(questionId)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "题目 id 不合法" });
        return;
      }
      fetchJson(sharedBase + "/questions/" + encodeURIComponent(questionId)).then(done, fail);
      return;
    }

    if (method === "bank.random") {
      var randomParams = new URLSearchParams();
      randomParams.set("grade", filterValue(payload, "grade", 32));
      randomParams.set("difficulty", filterValue(payload, "difficulty", 32));
      randomParams.set("type", filterValue(payload, "type", 32));
      var randomSearch = textValue(payload, "q", 100);
      if (randomSearch) randomParams.set("q", randomSearch);
      var randomTopic = textValue(payload, "topic", 20);
      if (randomTopic) {
        if (!TOPIC_ID_RE.test(randomTopic)) {
          replyHost(tab, message, false, { code: "BAD_REQUEST", message: "考向节点 id 不合法" });
          return;
        }
        randomParams.set("topic", randomTopic);
      }
      fetchJson(base + "/random?" + randomParams.toString()).then(done, fail);
      return;
    }

    if (method === "bank.topics") {
      var topicParams = new URLSearchParams();
      var parentId = textValue(payload, "parent_id", 20);
      if (parentId && !TOPIC_ID_RE.test(parentId)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "大纲节点 parent_id 不合法" });
        return;
      }
      if (parentId) topicParams.set("parent_id", parentId);
      var topicSearch = textValue(payload, "q", 100);
      if (topicSearch) topicParams.set("q", topicSearch);
      fetchJson(sharedBase + "/topics?" + topicParams.toString()).then(done, fail);
      return;
    }

    if (method === "bank.topic_notes") {
      var noteTopic = textValue(payload, "topic_id", 20);
      if (!TOPIC_ID_RE.test(noteTopic)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "考向节点 topic_id 不合法" });
        return;
      }
      fetchJson(sharedBase + "/topics/" + encodeURIComponent(noteTopic) + "/notes").then(done, fail);
      return;
    }

    if (method === "basket.list") {
      fetchJson("/api/basket?expand=" + (payload.expand === true ? "true" : "false")).then(done, fail);
      return;
    }

    if (method === "basket.add" || method === "basket.active_add") {
      var ids = payload.ids;
      if (typeof payload.id === "string") ids = [payload.id];
      if (!Array.isArray(ids) || !ids.length) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "ids 必须是非空数组" });
        return;
      }
      if (ids.length > 200) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "一次最多加 200 题" });
        return;
      }
      var cleanIds = [];
      for (var i = 0; i < ids.length; i += 1) {
        var id = typeof ids[i] === "string" ? ids[i] : "";
        if (!ID_RE.test(id)) {
          replyHost(tab, message, false, { code: "BAD_REQUEST", message: "题目 id 不合法" });
          return;
        }
        cleanIds.push(id);
      }
      // 题篮条目按「题库归属」记账：浏览型插件自己没有库，就要把题目记在当前
      // 活跃 provider 名下，否则读题篮时找不到全文（与 bank.active_list 同源）。
      var basketOwner = pluginId;
      if (method === "basket.active_add") basketOwner = bankProviderId;
      var addToBasket = function () {
        withWriteToken("/api/basket", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ plugin_id: basketOwner, ids: cleanIds })
        }).then(function (result) {
          done(result);
          noteBasketChange(tab, "add", result, cleanIds.length);
        }, fail);
      };
      if (method === "basket.active_add") {
        loadBankProvider().then(addToBasket, addToBasket);
      } else {
        addToBasket();
      }
      return;
    }

    if (method === "basket.remove") {
      var removeId = textValue(payload, "question_id", 80) || textValue(payload, "id", 80);
      if (!ID_RE.test(removeId)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "题目 id 不合法" });
        return;
      }
      withWriteToken("/api/basket/" + encodeURIComponent(removeId), { method: "DELETE" })
        .then(function (result) {
          done(result);
          noteBasketChange(tab, "remove", result, 1);
        }, fail);
      return;
    }

    if (method === "basket.clear") {
      withWriteToken("/api/basket", { method: "DELETE" }).then(function (result) {
        done(result);
        noteBasketChange(tab, "clear", result, 0);
      }, fail);
      return;
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

  // ---------- 消息入口：响应归位 + 插件事件上桥 ----------
  window.addEventListener("message", function (event) {
    var message = event.data;
    if (!message || message.protocol !== PROTOCOL) return;
    var tab = null;
    for (var i = 0; i < tabs.length; i += 1) {
      if (tabs[i].frame && tabs[i].frame.contentWindow === event.source) {
        tab = tabs[i];
        break;
      }
    }
    if (!tab) {
      for (var p = 0; p < panels.length; p += 1) {
        if (panels[p].frame && panels[p].frame.contentWindow === event.source) {
          tab = panels[p];
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
      if (PUBLISH_ALLOW.indexOf(topic) < 0) {
        dock("插件「" + (tab.plugin.name || tab.plugin.id) + "」想发未授权事件 " + topic + "，已丢弃。", "bus.denied");
        return;
      }
      var text = message.payload && typeof message.payload.text === "string"
        ? message.payload.text.slice(0, 200)
        : JSON.stringify(message.payload || {}).slice(0, 200);
      emit(topic, { text: text, pluginId: tab.plugin.id, raw: message.payload || null });
    }
  });

  // ---------- 三端分离：编辑跳转（存储端/输出端 → 输入端） ----------
  // 题库与组卷/讲义一律只读；老师点「去编辑」时插件只发一个 system.open_editor，
  // 由宿主负责开录题插件的页签并把题号注进去——插件之间不直连（AGENTS §2）。
  var pendingEditorIntent = null;
  var pendingBankQuery = null;

  function findPluginTab(pluginId) {
    for (var i = 0; i < tabs.length; i += 1) {
      if (tabs[i].kind === "plugin" && tabs[i].plugin && tabs[i].plugin.id === pluginId) return tabs[i];
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

  // ---------- 看板跳转：打开活跃题库页签（system.open_bank） ----------
  // 与 openEditor 同构：插件只发意图，跳转由宿主完成，目标不写死——
  // 永远打开「当前活跃 provider」的页签（bankProviderId 启动时已从 /api/bank/provider 解析）。
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
    var tab = findPluginTab(bankProviderId);
    if (tab) {
      activate(tab.key);
      if (tab.ready) deliverBankQuery(tab);   // 刚唤醒的交给 mountFrame 补发
      dock("已跳转到题库"
        + (query ? "，检索「" + query + "」" : "")
        + (questionId ? "（题目 " + questionId + "）" : "") + "。", "stage.bank.opened");
      return;
    }
    fetchJson("/api/plugins").then(function (data) {
      var plugin = ((data && data.plugins) || []).filter(function (item) {
        return item.id === bankProviderId;
      })[0];
      if (!plugin) {
        pendingBankQuery = null;
        dock("没找到当前题库插件 " + bankProviderId + "，跳转未完成。", "stage.bank.missing");
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

  // ---------- 页签生命周期 ----------
  function addTab(tab) {
    tab.order = tab.order == null ? ++openSeq : tab.order;
    tabs.push(tab);
    if (tabsEl) tabsEl.appendChild(buildTabButton(tab));
    if (bodyEl) bodyEl.appendChild(tab.panel);
    tab.panel.hidden = true;
    orderPluginTabs();
    return tab;
  }

  function activate(key) {
    var tab = findTab(key);
    if (!tab) return;
    tabs.forEach(function (item) {
      var on = item.key === key;
      item.panel.hidden = !on;
      item.button.setAttribute("aria-selected", String(on));
      item.button.setAttribute("tabindex", on ? "0" : "-1");
    });
    activeKey = key;
    touch(tab);
    dismissGroup(tab);
    paintGroupStates();
    hydrateConsole(key);
    applyFullscreen(tab);
    if (tab.kind === "plugin" && tab.state !== "live") {
      dock("唤醒插件「" + (tab.plugin.name || tab.plugin.id) + "」…", "stage.tab.wake");
      mountFrame(tab).then(function () {
        enforceLru();
        applySleepPolicy();
        deliverEditorIntent(tab);
      });
    } else {
      enforceLru();
      applySleepPolicy();
      deliverEditorIntent(tab);
    }
    emit("stage.tab.activated", { key: key, pluginId: tab.plugin ? tab.plugin.id : null });
  }

  /**
   * fullscreen 模式：收掉左、右、下三区，让插件独占视口。
   * 只翻 data-fullscreen 属性，绝不动 data-side/data-ctx——用户的折叠偏好
   * 是另一本账，退出全屏时必须原样还在。
   */
  function applyFullscreen(tab) {
    var page = document.querySelector(".ws-page");
    if (!page) return;
    var want = Boolean(tab.plugin && tab.plugin.stage && tab.plugin.stage.mode === "fullscreen");
    if (want) page.setAttribute("data-fullscreen", "on");
    else page.removeAttribute("data-fullscreen");
  }

  function closeTab(key) {
    var index = -1;
    for (var i = 0; i < tabs.length; i += 1) {
      if (tabs[i].key === key) { index = i; break; }
    }
    if (index < 0) return;
    var tab = tabs[index];
    if (!tab.closable) return;   // 引导页是兜底，不许关
    if (immersiveKey === key) setImmersive(false, "");   // 沉浸的那页被关，全屏也一起退
    if (tab.kind === "plugin" && tab.state === "live") hibernate(tab, "close");
    if (tab.button.parentNode) tab.button.parentNode.removeChild(tab.button);
    if (tab.panel.parentNode) tab.panel.parentNode.removeChild(tab.panel);
    tabs.splice(index, 1);
    orderPluginTabs();   // 组里少了一页，下拉与计数必须当场跟上
    dock("已关闭插件页「" + (tab.title || key) + "」。", "stage.tab.closed");
    emit("stage.tab.closed", { key: key });
    if (activeKey === key) {
      var next = tabs[index] || tabs[index - 1] || tabs[0];
      if (next) activate(next.key);
    }
  }

  function registerNative(options) {
    var panel = document.getElementById(options.panelId);
    if (!panel) return null;
    var tab = {
      key: options.key,
      kind: "native",
      title: options.title,
      closable: false,
      panel: panel,
      state: "live",
      lastUsed: Date.now()
    };
    addTab(tab);
    return tab;
  }

  /** 打开（或唤醒）一个插件页签；singleton=false 时允许同一插件开多个页签。 */
  function openPlugin(plugin) {
    if (!plugin || !plugin.entry_url) return null;
    var singleton = !(plugin.stage && plugin.stage.singleton === false);
    var baseKey = "plugin:" + plugin.id;
    var key = baseKey;
    var existing = findTab(key);
    if (singleton && existing) {
      existing.plugin = plugin;   // 覆盖安装后清单可能变了
      existing.button.querySelector(".ws-tab-label").textContent = plugin.name || plugin.id;
      activate(key);
      return existing;
    }

    var serial = 1;
    if (!singleton) {
      while (findTab(key)) {
        serial += 1;
        key = baseKey + "#" + serial;
      }
    }
    var title = plugin.name || plugin.id;
    if (!singleton && serial > 1) title += " #" + serial;

    var panel = document.createElement("section");
    panel.className = "ws-tab-panel";
    panel.id = "wsPanel_" + key.replace(/[^a-zA-Z0-9_-]/g, "_");
    panel.setAttribute("role", "tabpanel");
    panel.setAttribute("aria-label", title + " 画布");
    panel.setAttribute("data-tab", key);

    var tab = {
      key: key,
      kind: "plugin",
      title: title,
      closable: true,
      panel: panel,
      plugin: plugin,
      state: "sleep",
      ready: false,
      pending: new Map(),
      lastUsed: Date.now(),
      priority: priorityOf({ plugin: plugin })
    };
    addTab(tab);
    activate(key);
    dock("已为插件「" + title + "」开一个画布页。", "stage.tab.opened");
    emit("stage.tab.opened", { key: key, pluginId: plugin.id });
    return tab;
  }

  /**
   * 覆盖安装 / 热插拔后刷新已打开页签的清单数据。
   * 运行中的 iframe 不主动重载（规范 §4：新代码要刷新页面才加载），只更新标题与
   * 优先级；页签位置随之重排，避免“装完还挂在旧坑位”的错觉。
   */
  function updatePlugin(plugin) {
    if (!plugin || !plugin.id) return;
    tabs.forEach(function (tab) {
      if (tab.kind !== "plugin" || !tab.plugin || tab.plugin.id !== plugin.id) return;
      tab.plugin = plugin;
      var suffix = tab.key.indexOf("#") >= 0 ? tab.key.slice(tab.key.indexOf("#")) : "";
      tab.title = (plugin.name || plugin.id) + suffix;
      var label = tab.button && tab.button.querySelector(".ws-tab-label");
      if (label) label.textContent = tab.title;
      tab.priority = priorityOf(tab);
    });
    orderPluginTabs();
  }

  /**
   * 插件热更新后重新水合（PLUGIN_SPEC §1.7）——这是「运行中的 iframe 不主动重载」
   * 那条默认规则的唯一例外：代码目录已被新版本覆盖，旧脚本必须退场。
   * 正占据中央画布的那个：休眠 → 立刻重挂，加载新代码；其余页签只摘掉旧 iframe，
   * 下次点开自然加载新代码。全程无需刷新浏览器、无需重启底座。
   */
  function rehydratePlugin(pluginId) {
    if (!pluginId) return false;
    var touched = false;
    tabs.forEach(function (tab) {
      if (tab.kind !== "plugin" || !tab.plugin || tab.plugin.id !== pluginId) return;
      touched = true;
      if (tab.state === "live" || tab.state === "error") hibernate(tab, "plugin.updated");
      if (tab.key === activeKey) {
        mountFrame(tab).then(function () {
          dock("插件「" + (tab.plugin.name || tab.plugin.id) + "」已按新版本重新水合。",
            "plugin.updated");
        });
      }
    });
    if (touched) orderPluginTabs();
    return touched;
  }

  // ---------- 页签栏：分组合并、溢出横滚、沉浸全屏与浅休眠（军令 #16 模块三） ----------

  /** 分组归属只认清单里的 folder_id（后端从偏好树反查）；没进组的共用「未分组」。 */
  function groupKeyOf(tab) {
    var folder = String((tab.plugin && tab.plugin.folder_id) || "");
    return folder || UNGROUPED_KEY;
  }

  function groupTitle(key) {
    if (key === UNGROUPED_KEY) return "未分组";
    for (var i = 0; i < groupTree.length; i += 1) {
      var node = groupTree[i];
      if (node && node.kind === "folder" && node.id === key) {
        return String(node.name || "未命名文件夹");
      }
    }
    return "分组";
  }

  /** 左栏那棵树是分组名的唯一来源：workspace 每拉到一次清单、每改一次树都同步过来。 */
  function setSidebarTree(tree) {
    groupTree = Array.isArray(tree) ? tree : [];
    Object.keys(holders).forEach(function (key) {
      var label = holders[key].btn.querySelector(".ws-tab-label");
      if (label) label.textContent = groupTitle(key);
    });
    orderPluginTabs();
  }

  function groupHolder(key) {
    var holder = holders[key];
    if (holder) return holder;
    var chip = document.createElement("div");
    chip.className = "ws-tab-group";
    chip.setAttribute("data-group", key);
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "ws-tab ws-tab-group-chip";
    btn.setAttribute("aria-expanded", "false");
    var label = document.createElement("span");
    label.className = "ws-tab-label";
    label.textContent = groupTitle(key);
    var count = document.createElement("span");
    count.className = "ws-tab-count";
    count.setAttribute("aria-hidden", "true");
    var caret = document.createElement("span");
    caret.className = "ws-tab-caret";
    caret.setAttribute("aria-hidden", "true");
    caret.textContent = "\u25be";
    btn.appendChild(label);
    btn.appendChild(count);
    btn.appendChild(caret);
    var list = document.createElement("div");
    list.className = "ws-tab-group-list";
    list.setAttribute("role", "group");
    // 下拉里点开一页时要凭这张列表反查它属于哪一组，所以组 key 也得落在列表上
    list.setAttribute("data-group", key);
    list.hidden = true;
    btn.addEventListener("click", function () { toggleGroup(key); });
    chip.appendChild(btn);
    chip.appendChild(list);
    holder = { chip: chip, btn: btn, list: list, count: count, label: label };
    holders[key] = holder;
    return holder;
  }

  function collapse(key) {
    var holder = holders[key];
    if (!holder) return;
    holder.list.hidden = true;
    holder.btn.setAttribute("aria-expanded", "false");
    holder.btn.setAttribute("aria-haspopup", "false");
    if (expandedKey === key) expandedKey = "";
  }

  /** 军令逐字「单击下拉展开子 Tab」：点组名就摊开，同一时刻只摊开一个。 */
  function toggleGroup(key) {
    var holder = holders[key];
    if (!holder) return;
    if (expandedKey === key) {
      collapse(key);
      return;
    }
    Object.keys(holders).forEach(function (other) { collapse(other); });
    expandedKey = key;
    placeGroupList(holder);
    holder.list.hidden = false;
    holder.btn.setAttribute("aria-expanded", "true");
    holder.btn.setAttribute("aria-haspopup", "true");
    var first = holder.list.querySelector(".ws-tab");
    if (first && typeof first.focus === "function") first.focus();
  }

  /**
   * 下拉用 fixed 定位挂在页签栏外面：`#wsTabs` 为了横滚必须裁剪溢出，
   * 子页签列表跟着被裁掉就等于「点开看不见」；fixed 相对视口，不受那层裁剪管。
   */
  function placeGroupList(holder) {
    var rect = holder.btn.getBoundingClientRect();
    var width = Math.max(180, Math.min(280, rect.width + 60));
    var left = Math.max(8, Math.min(rect.left, window.innerWidth - width - 8));
    holder.list.style.left = Math.round(left) + "px";
    holder.list.style.top = Math.round(rect.bottom + 4) + "px";
    holder.list.style.width = Math.round(width) + "px";
    holder.list.style.maxHeight = Math.max(120, window.innerHeight - rect.bottom - 16) + "px";
  }

  // 摊开的下拉是「临时态」：点别处就收，不许一直盖着页签栏
  document.addEventListener("click", function (event) {
    if (!expandedKey) return;
    var holder = holders[expandedKey];
    if (holder && event.target && holder.chip.contains(event.target)) return;
    collapse(expandedKey);
  });

  /** 从下拉里点开一页就收摊：菜单一直盖着页签栏，后面的页签一个都点不到。 */
  function dismissGroup(tab) {
    var parent = tab && tab.button ? tab.button.parentNode : null;
    if (!parent || !parent.classList || !parent.classList.contains("ws-tab-group-list")) return;
    collapse(parent.getAttribute("data-group") || "");
  }

  function barItems() {
    if (!tabsEl) return 0;
    return tabsEl.querySelectorAll(":scope > .ws-tab, :scope > .ws-tab-group").length;
  }

  function slideTabs(step) {
    if (!tabsEl) return;
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (typeof tabsEl.scrollBy === "function") {
      tabsEl.scrollBy({ left: step * 140, behavior: reduce ? "auto" : "smooth" });
    } else {
      tabsEl.scrollLeft += step * 140;
    }
  }

  function ensureScrollButtons() {
    if (scrollBtns || !tabsEl || !tabsEl.parentNode) return;
    var wrap = tabsEl.parentNode;

    function make(dir, text, aria) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "ws-tab-scroll-btn";
      button.textContent = text;
      button.setAttribute("aria-label", aria);
      button.addEventListener("click", function () { slideTabs(dir); });
      return button;
    }

    var left = make(-1, "\u2039", "页签栏向左滚");
    var right = make(1, "\u203a", "页签栏向右滚");
    wrap.insertBefore(left, tabsEl);
    wrap.appendChild(right);
    tabsEl.addEventListener("wheel", function (event) {
      // 只在真的横滚得动时接管滚轮，否则不许抢纵向滚动的地盘
      if (!scrollBtns || scrollBtns.right.hidden) return;
      var delta = Math.abs(event.deltaY) > Math.abs(event.deltaX) ? event.deltaY : event.deltaX;
      if (!delta) return;
      event.preventDefault();
      tabsEl.scrollLeft += delta;
    }, { passive: false });
    tabsEl.addEventListener("scroll", function () { paintOverflowBar(); });
    window.addEventListener("resize", function () { paintOverflowBar(); });
    scrollBtns = { left: left, right: right };
  }

  /** 溢出（军令逐字「超过 10 个 Tab」）：固定 120px + 滚轮 + 左右小箭头，三样一起上。 */
  function paintOverflowBar(many) {
    var page = document.querySelector(".ws-page");
    if (!page || !tabsEl) return;
    // scroll/resize 那两条回调是不带参数进来的：这里必须自己把页签数回来。
    // 照原样读 undefined 会把「挤爆态」的类一滚就摘掉，箭头跟着消失，
    // 结果是滚到一半再也滚不动——正是老师最烦的半截子交互。
    var isMany = typeof many === "boolean"
      ? many
      : tabs.filter(function (tab) { return tab.kind === "plugin"; }).length > TAB_OVERFLOW;
    if (isMany) page.classList.add("ws-tabs-many");
    else page.classList.remove("ws-tabs-many");
    ensureScrollButtons();
    if (!scrollBtns) return;
    var needs = isMany && tabsEl.scrollWidth > tabsEl.clientWidth + 1;
    scrollBtns.left.hidden = !needs;
    scrollBtns.right.hidden = !needs;
  }

  /**
   * 重排页签栏。没挤爆时逐个平铺（老师习惯了一插件一页）；挤爆了才合并：
   * 同组（同一文件夹，或都没进组）凑满 TAB_GROUP_MIN 页收成「分组名页签」，单击摊开子页签。
   */
  function renderTabBar(orderedPluginTabs, many) {
    if (!tabsEl) return;
    var buckets = [];
    var byKey = {};
    orderedPluginTabs.forEach(function (tab) {
      if (!tab.button) return;
      var key = many ? groupKeyOf(tab) : "";
      if (!byKey[key]) {
        byKey[key] = { key: key, members: [] };
        buckets.push(byKey[key]);
      }
      byKey[key].members.push(tab);
    });
    tabs.forEach(function (tab) {
      if (tab.kind === "plugin" || !tab.button) return;
      if (tab.button.parentNode !== tabsEl) tabsEl.appendChild(tab.button);
    });
    var alive = {};
    buckets.forEach(function (bucket) {
      if (!many || bucket.members.length < TAB_GROUP_MIN) {
        bucket.members.forEach(function (tab) {
          if (tab.button.parentNode !== tabsEl) tabsEl.appendChild(tab.button);
          tab.button.classList.remove("ws-tab-in-group");
        });
        return;
      }
      var holder = groupHolder(bucket.key);
      alive[bucket.key] = true;
      holder.count.textContent = String(bucket.members.length);
      if (holder.chip.parentNode !== tabsEl) tabsEl.appendChild(holder.chip);
      bucket.members.forEach(function (tab) {
        if (tab.button.parentNode !== holder.list) holder.list.appendChild(tab.button);
        tab.button.classList.add("ws-tab-in-group");
      });
    });
    Object.keys(holders).forEach(function (key) {
      if (alive[key]) return;
      var holder = holders[key];
      if (holder.chip.parentNode) holder.chip.parentNode.removeChild(holder.chip);
      delete holders[key];
    });
    Object.keys(holders).forEach(function (key) {
      if (key !== expandedKey) collapse(key);
    });
    paintGroupStates();
  }

  /** 切页后只补涂组页签的「当前在这一组」标记，不重排 DOM（重排会打断焦点）。 */
  function paintGroupStates() {
    Object.keys(holders).forEach(function (key) {
      var holder = holders[key];
      var members = tabs.filter(function (tab) {
        return tab.kind === "plugin" && groupKeyOf(tab) === key;
      });
      var current = members.filter(function (tab) { return tab.key === activeKey; })[0];
      holder.btn.classList.toggle("is-active", Boolean(current));
      holder.btn.title = current
        ? "组：" + groupTitle(key) + "（当前页：" + current.title + "）"
        : "组：" + groupTitle(key);
    });
  }

  /**
   * 双击任意页签 = 沉浸全屏：真全屏让浏览器地址栏退场，左栏随之收起，
   * 右栏与输出日志照旧在场（老师要的是「这一页独占」，不是「只剩这一页」）。
   * 退出走同一次双击或浏览器原生的 Esc。
   */
  function toggleImmersive(key) {
    if (immersiveKey === key) {
      setImmersive(false, "");
      return;
    }
    setImmersive(true, key);
    dock("沉浸全屏：左栏已收起、浏览器地址栏退场；右栏与输出日志照旧。"
      + "再双击该页签或按 Esc 退出。", "stage.immersive");
  }

  function setImmersive(on, key) {
    immersiveKey = on ? key : "";
    var page = document.querySelector(".ws-page");
    if (page) {
      // 覆盖层呼入位每次进沉浸都擦干净：上一回按 Ctrl+B 唤出来的浮层，
      // 不该在下一张卷子独占屏幕时自己冒回来。
      page.removeAttribute("data-immersive-rail");
      if (on) page.setAttribute("data-immersive", "on");
      else page.removeAttribute("data-immersive");
    }
    var root = document.documentElement;
    if (on && !document.fullscreenElement && typeof root.requestFullscreen === "function") {
      try {
        var asking = root.requestFullscreen();
        if (asking && typeof asking.catch === "function") asking.catch(function () {});
      } catch (error) {
        // 浏览器不给真全屏（无手势、被策略拦）时，CSS 沉浸照旧生效，不为此打断操作
      }
    } else if (!on && document.fullscreenElement && typeof document.exitFullscreen === "function") {
      try {
        var leaving = document.exitFullscreen();
        if (leaving && typeof leaving.catch === "function") leaving.catch(function () {});
      } catch (error) {
        /* 已经退了：属性已摘，不必再管 */
      }
    }
  }

  /** 退沉浸只走这一张嘴：谁先落地谁记话，后到的那条通道自动哑火。 */
  function exitImmersive(via) {
    if (!immersiveKey) return;
    setImmersive(false, "");
    dock("已退出沉浸全屏（" + via + "）。", "stage.immersive");
  }

  document.addEventListener("fullscreenchange", function () {
    if (document.fullscreenElement) return;
    // 浏览器原生 Esc 退全屏时顺手把 data-immersive 一起摘掉，不留半吊子状态
    exitImmersive("Esc");
  });

  document.addEventListener("keydown", function (event) {
    if (!immersiveKey || event.key !== "Escape" || event.ctrlKey
      || event.metaKey || event.altKey || event.shiftKey) return;
    if (document.querySelector(".ws-dialog-backdrop")) return;   // 弹窗还要用 Esc 关掉，别抢
    // 有的浏览器（含自动化环境）把 Esc 留给页面自己处理，这条是原生退全屏的兜底
    exitImmersive("Esc");
  });

  function weightOf(tab) {
    var stage = tab.plugin && tab.plugin.stage;
    return stage && stage.weight === "light" ? "light" : "heavy";
  }

  function heavyLiveFrames() {
    return liveFrames().filter(function (tab) { return weightOf(tab) === "heavy"; });
  }

  /**
   * 浅休眠：light 插件切后台不摘文档，只发 plugin.suspend 让它自己收定时器，
   * 回到前台补发 plugin.resume。深休眠（摘掉 iframe）仍只数 heavy 的 LRU 账。
   */
  function applySleepPolicy() {
    tabs.forEach(function (tab) {
      if (tab.kind !== "plugin" || tab.state !== "live" || weightOf(tab) !== "light") return;
      var background = tab.key !== activeKey;
      if (background && !tab.suspended) {
        tab.suspended = true;
        notify(tab, "plugin.suspend", { reason: "background" });
      } else if (!background && tab.suspended) {
        tab.suspended = false;
        notify(tab, "plugin.resume", { reason: "foreground" });
      }
    });
  }

  function pushParams(tab) {
    // 挂载/唤醒后补发一次当前面板参数，插件不必等下一次改动才对齐
    var snapshot = window.JzoUiState && typeof window.JzoUiState.snapshot === "function"
      ? window.JzoUiState.snapshot()
      : null;
    if (snapshot) notify(tab, "ui.params.changed", snapshot);
  }

  /**
   * 「设置与控制台」是宿主自有的画布页签（不是沙箱插件）：
   * 系统管理面板必须能读工作区、装卸插件、切题库——这些能力一旦放进不透明源的
   * iframe，就得为它单开一组宿主转发方法，等于给沙箱多开一个攻击面；
   * 而且插件可卸载，控制台被卸掉就把底座变砖了。同源自检 + /settings 强制兜底
   * 才是「防变砖」的正解（军令的例外兜底条款）。
   */
  function hydrateConsole(key) {
    if (key !== "console") return;
    var frame = document.getElementById("wsConsoleFrame");
    // 哨兵值是 HTML 里写死的 about:blank（不是「没设过 src」），必须按值比，
    // 用 !getAttribute('src') 判空会永远为假、页签里就只剩一张白纸。
    if (frame && (!frame.getAttribute("src") || frame.getAttribute("src") === "about:blank")) {
      frame.setAttribute("src", "/settings?embedded=1");
    }
  }

  function init() {
    if (!tabsEl || !bodyEl) return;
    registerNative({ key: "home", title: "引导", panelId: "wsPanelHome" });
    registerNative({ key: "console", title: "设置与控制台", panelId: "wsPanelConsole" });
    activate("home");

    if (bus && typeof bus.on === "function") {
      // 右栏改参数 → 直达中栏所有活着的插件（军令任务 3.3）
      bus.on("ui.params.changed", function (event) { broadcast("ui.params.changed", event.payload); });
      // 录题插件的当前题只喂给右栏面板（AI 助手插件的副驾），不广播给中栏——
      // 中栏插件自己就是选区的来源，回灌只会形成回声。
      bus.on("stage.selection", function (event) {
        panels.forEach(function (panel) { notify(panel, "stage.selection", event.payload); });
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
      // 插件被热更新（PLUGIN_SPEC §1.7）：转给订阅了它的插件，画布水合由宿主自己处理
      bus.on("plugin.updated", function (event) { broadcast("plugin.updated", event.payload); });
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
    activate: activate,
    close: closeTab,
    attachPanel: attachPanel,
    tabs: function () {
      return tabs.map(function (tab) {
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
      panels.forEach(function (panel) {
        if (panel.plugin && panel.plugin.id === pluginId && panel.frame) {
          notify(panel, event, payload);
          reached = true;
        }
      });
      return reached;
    },
    broadcast: broadcast,
    maxLiveFrames: MAX_LIVE_FRAMES,
    dockLogMax: DOCK_LOG_MAX
  };
})();
