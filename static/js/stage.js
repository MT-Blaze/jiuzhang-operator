/**
 * Stage：中栏画布的 Tabs 宿主。
 *
 * 职责边界（军令任务 3）：中栏只是「通用舞台」，底座负责挂标签页、挂 iframe、
 * 转发事件；业务画面一律由插件自己画。左、右、下三区仍由底座托管，
 * 插件只能经 HostBus 向指定区域投递数据，拿不到那三区的 DOM。
 *
 * 两类页签：
 *   - 原生页签：对话流。它是舞台的永久兜底页，不可关闭（插件全崩也还有地方说话）。
 *   - 重型页签：沙箱 iframe 插件。带 LRU 休眠——同时存活的 iframe 最多 MAX_LIVE_FRAMES 个，
 *     最久未用的发 plugin.deactivate 后摘掉文档，页签保留、状态标「休眠」，再点回来重新挂载。
 *
 * 协议：jzo-plugin/1（PLUGIN_SPEC §2.3.3）。宿主发 request，插件回 response；
 * 另有单向 notification（无 id、不等回复、插件必须幂等）。
 * 沙箱只给 allow-scripts：插件文档处于不透明源，碰不到宿主 DOM 与令牌。
 */
(function () {
  "use strict";

  var PROTOCOL = "jzo-plugin/1";
  var SANDBOX = "allow-scripts";
  var MAX_LIVE_FRAMES = 3;
  var REQUEST_TIMEOUT_MS = 30000;   // PLUGIN_SPEC §5.1：宿主对插件请求 30 秒超时
  var DOCK_LOG_MAX = 120;

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

  function priorityOf(tab) {
    var stage = tab.plugin && tab.plugin.stage;
    var value = stage && typeof stage.priority === "number" ? stage.priority : 0;
    return Math.max(-100, Math.min(100, value));
  }

  /**
   * 舞台优先级（stage.priority）的真实消费点：同排插件页签按优先级从高到低排，
   * 同优先级按打开先后。原生页签（对话）永远排第一，不参与抢位。
   */
  function orderPluginTabs() {
    if (!tabsEl) return;
    var pluginTabs = tabs.filter(function (tab) { return tab.kind === "plugin"; });
    pluginTabs.sort(function (a, b) {
      var delta = priorityOf(b) - priorityOf(a);
      return delta !== 0 ? delta : a.order - b.order;
    });
    pluginTabs.forEach(function (tab) {
      if (tab.button && tab.button.parentNode === tabsEl) tabsEl.appendChild(tab.button);
    });
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
    box.textContent = message + "（底座仍可继续使用对话页）";
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

  function enforceLru() {
    var live = liveFrames();
    while (live.length > MAX_LIVE_FRAMES) {
      var oldest = null;
      live.forEach(function (tab) {
        if (tab.key === activeKey) return;
        if (!oldest || tab.lastUsed < oldest.lastUsed) oldest = tab;
      });
      if (!oldest) break;   // 全是活动页：不硬摘，宁可多留一个也不打断用户
      hibernate(oldest, "LRU");
      live = liveFrames();
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

  function broadcast(event, payload) {
    liveFrames().forEach(function (tab) { notify(tab, event, payload); });
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
    "draft.save", "draft.load"
  ];
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

  // ---------- 草稿托管（宿主代持 localStorage） ----------
  // 沙箱 iframe 是不透明源（只给 allow-scripts，不同源），插件里访问
  // localStorage 会直接抛 SecurityError——「关 Tab 不丢草稿」这件事只能由同源的宿主来做。
  // 插件通过 draft.save / draft.load 两个 RPC 把表单态交给宿主，宿主按 plugin.id 分命名空间，
  // A 插件读不到 B 插件的草稿。这里绝不碰后端：草稿是本地易失态，不进库、不出网。
  var DRAFT_NS = "jzo.draft.";
  var DRAFT_KEY_RE = /^[A-Za-z0-9_.:-]{1,80}$/;
  var DRAFT_MAX_CHARS = 200000;

  function draftSlot(pluginId, key) {
    return DRAFT_NS + pluginId + "." + key;
  }

  /** 宿主代存草稿：value 为 null 即清除。返回是否成功（配额满/非法键都如实报失败）。 */
  function saveDraft(pluginId, key, value) {
    if (!DRAFT_KEY_RE.test(key)) return { ok: false, reason: "草稿键不合法" };
    var slot = draftSlot(pluginId, key);
    try {
      if (value === null || value === undefined) {
        window.localStorage.removeItem(slot);
        return { ok: true, cleared: true };
      }
      var text = JSON.stringify(value);
      if (text.length > DRAFT_MAX_CHARS) return { ok: false, reason: "草稿过大，未保存" };
      window.localStorage.setItem(slot, text);
      return { ok: true, saved_at: Date.now() };
    } catch (error) {
      return { ok: false, reason: String(error && error.name || "存储失败") };
    }
  }

  function loadDraft(pluginId, key) {
    if (!DRAFT_KEY_RE.test(key)) return { ok: false, reason: "草稿键不合法" };
    try {
      var text = window.localStorage.getItem(draftSlot(pluginId, key));
      return { ok: true, value: text ? JSON.parse(text) : null };
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
    if (controller) {
      settings.signal = controller.signal;
      timer = window.setTimeout(function () { controller.abort(); }, RELAY_TIMEOUT_MS);
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

  function relay(tab, message) {
    var method = String(message.method || "");
    if (RELAY_METHODS.indexOf(method) < 0) {
      replyHost(tab, message, false, {
        code: "UNSUPPORTED_METHOD",
        message: "宿主未开放方法：" + method.slice(0, 80)
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

    // 草稿走本地托管，不出网、不进库：先于任何 HTTP 分支就地答复。
    if (method === "draft.save" || method === "draft.load") {
      var draftKey = textValue(payload, "key", 80);
      if (method === "draft.save") {
        done(saveDraft(pluginId, draftKey, payload.value === undefined ? null : payload.value));
      } else {
        done(loadDraft(pluginId, draftKey));
      }
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

    // basket.clear
    withWriteToken("/api/basket", { method: "DELETE" }).then(function (result) {
      done(result);
      noteBasketChange(tab, "clear", result, 0);
    }, fail);
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
    var tab = findPluginTab(bankProviderId);
    if (tab) {
      activate(tab.key);
      dock("已跳转到题库" + (questionId ? "（题目 " + questionId + "）" : "") + "。", "stage.bank.opened");
      return;
    }
    fetchJson("/api/plugins").then(function (data) {
      var plugin = ((data && data.plugins) || []).filter(function (item) {
        return item.id === bankProviderId;
      })[0];
      if (!plugin) {
        dock("没找到当前题库插件 " + bankProviderId + "，跳转未完成。", "stage.bank.missing");
        return;
      }
      openPlugin(plugin);
      dock("正在打开题库" + (questionId ? "（题目 " + questionId + "）" : "") + "…", "stage.bank.opened");
    }, function (error) {
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
    hydrateConsole(key);
    applyFullscreen(tab);
    if (tab.kind === "plugin" && tab.state !== "live") {
      dock("唤醒插件「" + (tab.plugin.name || tab.plugin.id) + "」…", "stage.tab.wake");
      mountFrame(tab).then(function () {
        enforceLru();
        deliverEditorIntent(tab);
      });
    } else {
      enforceLru();
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
    if (!tab.closable) return;   // 对话页是兜底，不许关
    if (tab.kind === "plugin" && tab.state === "live") hibernate(tab, "close");
    if (tab.button.parentNode) tab.button.parentNode.removeChild(tab.button);
    if (tab.panel.parentNode) tab.panel.parentNode.removeChild(tab.panel);
    tabs.splice(index, 1);
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
    registerNative({ key: "chat", title: "对话", panelId: "wsPanelChat" });
    registerNative({ key: "console", title: "设置与控制台", panelId: "wsPanelConsole" });
    activate("chat");

    if (bus && typeof bus.on === "function") {
      // 右栏改参数 → 直达中栏所有活着的插件（军令任务 3.3）
      bus.on("ui.params.changed", function (event) { broadcast("ui.params.changed", event.payload); });
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
    broadcast: broadcast,
    maxLiveFrames: MAX_LIVE_FRAMES,
    dockLogMax: DOCK_LOG_MAX
  };
})();
