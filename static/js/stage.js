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
  // 不许发 layout.* / ui.params.*（那是底座与人的地盘，防插件反向操控面板）
  var PUBLISH_ALLOW = ["region.dock", "region.left", "region.right", "stage.selection"];

  var tabsEl = document.getElementById("wsTabs");
  var bodyEl = document.getElementById("wsCanvasBody");
  var bus = window.JzoBus;
  var tabs = [];
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

    var note = document.createElement("p");
    note.className = "ws-frame-note";
    note.textContent = "沙箱运行中：插件只能经 postMessage 与底座说话，碰不到密钥、数据库与文件系统。";
    panel.appendChild(note);

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

  // ---------- 插件数据通道（Host API 转发） ----------
  // 插件不直连数据库、也不联网；它只能申请下列方法，由宿主按「当前页签自己的
  // plugin.id」去查接口。插件在 payload 里自报 plugin_id 一律不认，防止串库。
  // 读接口开放；题篮写操作由宿主代取一次性令牌（插件永远看不到令牌）。
  var RELAY_METHODS = [
    "bank.list", "bank.stats", "bank.get", "bank.random", "bank.create",
    "basket.list", "basket.add", "basket.remove", "basket.clear"
  ];
  // 录题插件的写入目标：底座唯一的公共题库。插件自报 plugin_id 一律不认，
  // 防止 A 插件把题塞进 B 插件私有库。
  var CANONICAL_BANK_ID = "org.jiuzhang.core-bank";
  var RELAY_TIMEOUT_MS = 20000;
  var RELAY_WINDOW_MS = 10000;
  var RELAY_MAX_PER_WINDOW = 80;
  var ID_RE = /^[A-Za-z0-9_-]{1,80}$/;

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
            var failure = new Error(typeof detail === "string" ? detail : "宿主接口返回 HTTP " + response.status);
            failure.status = response.status;
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

    var base = "/api/bank/plugins/" + encodeURIComponent(pluginId);

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
        "/api/bank/plugins/" + encodeURIComponent(CANONICAL_BANK_ID) + "/questions",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: question })
        }
      ).then(function (result) {
        emit("question.updated", {
          action: "create",
          id: result && result.id,
          pluginId: tab.plugin.id
        });
        done(result);
      }, fail);
      return;
    }

    if (method === "bank.stats") {
      fetchJson(base + "/stats").then(done, fail);
      return;
    }

    if (method === "bank.list") {
      var params = new URLSearchParams();
      params.set("grade", filterValue(payload, "grade", 32));
      params.set("difficulty", filterValue(payload, "difficulty", 32));
      params.set("type", filterValue(payload, "type", 32));
      params.set("chapter", filterValue(payload, "chapter", 64));
      params.set("textbook", filterValue(payload, "textbook", 64));
      var search = textValue(payload, "q", 100);
      if (search) params.set("q", search);
      params.set("page", String(intValue(payload, "page", 1, 1, 10000)));
      params.set("page_size", String(intValue(payload, "page_size", 20, 1, 100)));
      fetchJson(base + "/questions?" + params.toString()).then(done, fail);
      return;
    }

    if (method === "bank.get") {
      var questionId = textValue(payload, "id", 80);
      if (!ID_RE.test(questionId)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "题目 id 不合法" });
        return;
      }
      fetchJson(base + "/questions/" + encodeURIComponent(questionId)).then(done, fail);
      return;
    }

    if (method === "bank.random") {
      var randomParams = new URLSearchParams();
      randomParams.set("grade", filterValue(payload, "grade", 32));
      randomParams.set("difficulty", filterValue(payload, "difficulty", 32));
      randomParams.set("type", filterValue(payload, "type", 32));
      var randomSearch = textValue(payload, "q", 100);
      if (randomSearch) randomParams.set("q", randomSearch);
      fetchJson(base + "/random?" + randomParams.toString()).then(done, fail);
      return;
    }

    if (method === "basket.list") {
      fetchJson("/api/basket?expand=" + (payload.expand === true ? "true" : "false")).then(done, fail);
      return;
    }

    if (method === "basket.add") {
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
      withWriteToken("/api/basket", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plugin_id: pluginId, ids: cleanIds })
      }).then(function (result) {
        done(result);
        noteBasketChange(tab, "add", result, cleanIds.length);
      }, fail);
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
    if (!tab) return;   // 不认识的发信人一律丢弃

    // 插件主动申请宿主数据（jzo-plugin/1 的 request 方向，题库通道新增）。
    // 只认白名单方法，id 必须是短标识；回复严格回到发信 iframe。
    if (message.kind === "request") {
      if (typeof message.id !== "string" || !ID_RE.test(message.id)) return;
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
    applyFullscreen(tab);
    if (tab.kind === "plugin" && tab.state !== "live") {
      dock("唤醒插件「" + (tab.plugin.name || tab.plugin.id) + "」…", "stage.tab.wake");
      mountFrame(tab).then(enforceLru);
    } else {
      enforceLru();
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

  function pushParams(tab) {
    // 挂载/唤醒后补发一次当前面板参数，插件不必等下一次改动才对齐
    var snapshot = window.JzoUiState && typeof window.JzoUiState.snapshot === "function"
      ? window.JzoUiState.snapshot()
      : null;
    if (snapshot) notify(tab, "ui.params.changed", snapshot);
  }

  function init() {
    if (!tabsEl || !bodyEl) return;
    registerNative({ key: "chat", title: "对话", panelId: "wsPanelChat" });
    activate("chat");

    if (bus && typeof bus.on === "function") {
      // 右栏改参数 → 直达中栏所有活着的插件（军令任务 3.3）
      bus.on("ui.params.changed", function (event) { broadcast("ui.params.changed", event.payload); });
      // 题篮变了，组卷/讲义画布要跟上；不广播的话它们只能等用户再点一次刷新
      bus.on("basket.changed", function (event) { broadcast("basket.changed", event.payload); });
      // 录题插件写库成功 → 题库画布刷新列表（宿主统一生成事件，插件之间不直连）
      bus.on("question.updated", function (event) { broadcast("question.updated", event.payload); });
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
    activate: activate,
    close: closeTab,
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
