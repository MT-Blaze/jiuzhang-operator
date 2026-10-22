/**
 * 工作台：三栏「智能体」空壳原型 —— 对话流驱动。
 *
 * 设计取向（先见形，后调逻辑）：中栏是对话流主区，兼当前任务舞台；
 * 发送指令 → 用户气泡 → 调 /api/agent/chat → 助手气泡回显识别到的意图。
 * 左栏只放任务/插件简单入口，不做状态面板；右栏是上下文。
 *
 * 安全：所有气泡文本（含模型返回、插件反馈）一律用 textContent 落 DOM，
 * 不走 innerHTML，杜绝 XSS（AGENTS §5：不可信输入进 DOM 前必须净化）。
 */
(function () {
  "use strict";

  // --- State ---
  var providerList = [];
  var writeToken = null;
  var currentTask = "";
  var activePlugin = null;
  // 对话轮次记忆：注入下一轮请求，让模型延续前文而非孤立理解（10.24 军令 P0-2）。
  var transcript = [];
  var TRANSCRIPT_MAX = 24;   // 内存里最多留多少轮
  var TRANSCRIPT_SEND = 8;   // 每轮最多回传多少轮给模型

  // --- DOM refs ---
  var sidebarToggle = document.getElementById("wsToggleSidebar");
  var contextToggle = document.getElementById("wsToggleContext");
  var thread = document.getElementById("wsThread");
  var chatForm = document.getElementById("wsChatForm");
  var promptInput = document.getElementById("wsPrompt");
  var sendBtn = document.getElementById("wsSendBtn");
  var stageTitle = document.getElementById("wsStageTitle");
  var ctxTask = document.getElementById("ctxTask");
  var ctxModel = document.getElementById("ctxModel");
  var ctxHistory = document.getElementById("ctxHistory");
  var modelBtn = document.getElementById("wsModelBtn");
  var modelLabel = document.getElementById("wsModelLabel");
  var providerSelect = document.getElementById("wsProviderSelect");
  var chatEntry = document.getElementById("wsChatEntry");
  var pluginListEl = document.getElementById("wsPluginList");
  var pluginCountEl = document.getElementById("wsPluginCount");

  // ============ 对话流：气泡工厂 ============
  function addBubble(role, text, opts) {
    if (!thread) return null;
    opts = opts || {};
    var wrap = document.createElement("div");
    wrap.className = "ws-msg ws-msg-" + role;

    var bubble = document.createElement("div");
    bubble.className = "ws-bubble";
    if (opts.tone) bubble.setAttribute("data-tone", opts.tone);
    bubble.textContent = text; // 不可信内容也只当纯文本，天然免 XSS

    // 插件调用标识：让用户一眼看见「AI 真的调用了插件」，而不是只说不练。
    if (opts.pluginCalls && opts.pluginCalls.length) {
      var badge = document.createElement("span");
      badge.className = "ws-bubble-plugin";
      badge.textContent = "[已调用插件] " + pluginCallNames(opts.pluginCalls);
      if (opts.route === "host") {
        badge.title = "模型未发起工具调用，由底座按明确意图直接调用插件";
      } else {
        badge.title = "由模型发起 tool_calls，底座执行插件并回传结果";
      }
      bubble.insertBefore(badge, bubble.firstChild);
    }

    if (opts.source) {
      var src = document.createElement("span");
      src.className = "ws-bubble-source";
      src.textContent = opts.source;
      bubble.appendChild(src);
    }

    wrap.appendChild(bubble);
    thread.appendChild(wrap);
    scrollThreadToBottom();
    return wrap;
  }

  function pluginCallNames(calls) {
    var names = [];
    (calls || []).forEach(function (call) {
      var name = call && call.plugin && call.plugin.name ? call.plugin.name : (call && call.tool) || "插件";
      if (names.indexOf(name) === -1) names.push(name);
    });
    return names.join("、");
  }

  function addTyping() {
    if (!thread) return null;
    var wrap = document.createElement("div");
    wrap.className = "ws-msg ws-msg-bot";
    var bubble = document.createElement("div");
    bubble.className = "ws-bubble";
    var typing = document.createElement("span");
    typing.className = "ws-typing";
    for (var i = 0; i < 3; i += 1) typing.appendChild(document.createElement("span"));
    bubble.appendChild(typing);
    wrap.appendChild(bubble);
    thread.appendChild(wrap);
    scrollThreadToBottom();
    return wrap;
  }

  function scrollThreadToBottom() {
    if (thread) thread.scrollTop = thread.scrollHeight;
  }

  function logHistory(text) {
    if (!ctxHistory) return;
    var placeholder = ctxHistory.querySelector(".ws-placeholder");
    if (placeholder) placeholder.remove();
    var li = document.createElement("li");
    var time = new Date();
    var hh = String(time.getHours()).padStart(2, "0");
    var mm = String(time.getMinutes()).padStart(2, "0");
    li.textContent = hh + ":" + mm + " · " + text;
    ctxHistory.insertBefore(li, ctxHistory.firstChild);
    // 只留最近 8 条，避免无限增长
    while (ctxHistory.children.length > 8) {
      ctxHistory.removeChild(ctxHistory.lastChild);
    }
  }

  // 记录一轮对话进内存 transcript，超过上限丢最旧的，供下一轮注入模型。
  function pushTurn(role, content) {
    if (!content) return;
    transcript.push({ role: role, content: String(content) });
    while (transcript.length > TRANSCRIPT_MAX) transcript.shift();
  }

  // ============ 当前任务舞台 ============
  function setStage(taskName) {
    currentTask = taskName || "";
    if (stageTitle) stageTitle.textContent = currentTask || "新会话";
    if (ctxTask) ctxTask.textContent = currentTask || "未选择";
  }

  // ============ 入口切换：自由对话 / 插件工作模式 ============
  // 左栏不再写死业务任务；插件条目由 /api/plugins 动态渲染。点插件只切换
  // 工作模式与上下文，不做任何页面跳转（军令 2.3）。
  function markActiveEntry(activeEl) {
    var items = document.querySelectorAll(".ws-entry-item, .ws-plugin-item");
    for (var i = 0; i < items.length; i += 1) {
      items[i].setAttribute("aria-current", String(items[i] === activeEl));
    }
  }

  function enterChatMode() {
    activePlugin = null;
    markActiveEntry(chatEntry);
    setStage("自由对话");
    addBubble("sys", "已进入「自由对话」模式。");
    logHistory("进入自由对话");
    if (promptInput) promptInput.focus();
  }

  function enterPluginMode(plugin, item) {
    activePlugin = plugin;
    markActiveEntry(item);
    var name = plugin.name || plugin.id || "插件";
    setStage(name);
    addBubble("sys", "现在处于插件「" + name + "」的工作模式下。" +
      (plugin.description ? " " + plugin.description : ""));
    logHistory("进入插件「" + name + "」");
    if (promptInput) promptInput.focus();
  }

  if (chatEntry) chatEntry.addEventListener("click", enterChatMode);

  // ============ 折叠：左栏 / 右栏（data 属性驱动，桌面收轨道、移动滑抽屉） ============
  // 状态机只有一个事实来源：.ws-page 上的 data-side / data-ctx。
  // 样式按这两枚属性钉轨切轨（见 workspace.css 折叠态一节），脚本只负责翻属性，
  // 绝不再往元素上补 style，避免「属性说收起、内联样式说展开」的两本账。
  var wsPage = document.querySelector(".ws-page");
  var mqMobile = window.matchMedia("(max-width: 768px)");
  var openSidebarBtn = document.getElementById("wsOpenSidebar");

  function sideOpen() {
    return !!wsPage && wsPage.getAttribute("data-side") === "open";
  }

  function ctxOpen() {
    return !!wsPage && wsPage.getAttribute("data-ctx") === "open";
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

  function setCtx(open) {
    if (!wsPage) return;
    wsPage.setAttribute("data-ctx", open ? "open" : "hidden");
    if (contextToggle) contextToggle.setAttribute("aria-expanded", String(open));
  }

  if (sidebarToggle) {
    sidebarToggle.addEventListener("click", function () {
      setSide(!sideOpen());
    });
  }

  if (openSidebarBtn) {
    openSidebarBtn.addEventListener("click", function () {
      setSide(!sideOpen());
    });
  }

  if (contextToggle) {
    contextToggle.addEventListener("click", function () {
      setCtx(!ctxOpen());
    });
  }

  // 默认态：桌面两栏展开；窄屏抽屉收起，避免一进来就糊在中栏上。
  setSide(!mqMobile.matches);
  setCtx(!mqMobile.matches);

  // 跨断点时必须重算：窄屏收起的抽屉拖宽到桌面会留下「轨道已收起、属性仍写 open」
  // 的错位；反过来桌面展开态拉到窄屏则会让抽屉直接糊住对话流。
  function onBreakpoint(matched) {
    setSide(!matched);
    setCtx(!matched);
  }
  if (typeof mqMobile.addEventListener === "function") {
    mqMobile.addEventListener("change", function (e) { onBreakpoint(e.matches); });
  } else if (typeof mqMobile.addListener === "function") {
    mqMobile.addListener(function (e) { onBreakpoint(e.matches); });
  }

  // ============ 输入器：Enter 发送 / Shift+Enter 换行 / 自适应高度 ============
  function autoGrow() {
    if (!promptInput) return;
    promptInput.style.height = "auto";
    var next = Math.min(promptInput.scrollHeight, 180);
    promptInput.style.height = next + "px";
  }

  if (promptInput) {
    promptInput.addEventListener("input", autoGrow);
    promptInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (chatForm) chatForm.requestSubmit();
      }
    });
  }

  // ============ 发送指令 → 对话 Agent → 助手气泡 ============
  function describeSource(response) {
    if (response && response.route === "host") {
      return "底座按意图直接调用插件（模型未参与）";
    }
    if (response && response.mock) return "Mock 降级（当前 Provider 未配置密钥）";
    var data = (response && response.data) || {};
    return "模型 " + (data.model || "未知") + " 产出";
  }

  function describePluginSource(response, pluginCalls) {
    if (response && response.route === "host") {
      return "底座按意图直接调用插件（模型未参与）";
    }
    if (response && response.mock) {
      return "Mock 模型发起 · 插件真实执行";
    }
    var data = (response && response.data) || {};
    return "模型 " + (data.model || "未知") + " 发起 · 插件真实执行";
  }

  // --- 解析拦截（10.24 军令 P0-1）：系统控制 JSON 绝不进对话气泡 ---
  // 后端已剥一层代码围栏，前端再兜一层，双保险。
  function stripFences(text) {
    if (typeof text !== "string") return "";
    var trimmed = text.trim();
    var fence = trimmed.match(/^```[a-zA-Z0-9_-]*[ \t]*\r?\n?([\s\S]*?)\r?\n?```[ \t]*$/);
    return fence ? fence[1].trim() : trimmed;
  }

  // 尝试把内容解析成一个「控制对象」：先剥围栏再 JSON.parse，
  // 失败则从文本里抠出第一个 {...} 再试。解析不出对象一律返回 null。
  function extractControlJson(content) {
    var body = stripFences(content);
    if (!body) return null;
    try {
      var direct = JSON.parse(body);
      if (direct && typeof direct === "object") return direct;
    } catch (e) {
      /* 落到下面的兜底抠取 */
    }
    var braceMatch = body.match(/\{[\s\S]*\}/);
    if (braceMatch) {
      try {
        var extracted = JSON.parse(braceMatch[0]);
        if (extracted && typeof extracted === "object") return extracted;
      } catch (e2) {
        /* 仍不是合法 JSON，当作普通文本处理 */
      }
    }
    return null;
  }

  // 判断一段文本是否「看起来就是裸 JSON / 代码围栏」——这种东西不许直接给用户看。
  function looksLikeRawJson(text) {
    return /^\s*(```|[\[{])/.test(text || "");
  }

  function summarizeAction(parsed, source) {
    // 空壳原型：把 Agent 识别到的意图如实回显，具体执行待后续接入。
    var action = parsed && parsed.action;
    // 真实模型常把参数嵌在 params 下，Mock 则平铺在顶层；两处都认。
    var p = (parsed && parsed.params) ? parsed.params : (parsed || {});
    if (action === "split_paper") {
      var range = Array.isArray(p.page_range) ? p.page_range : [];
      var pageText = range.length === 2 ? "第 " + range[0] + "–" + range[1] + " 页" : "全卷";
      return "已识别【拆题】指令：" + pageText + "。（空壳原型：拆题结果将在接入拆题 Agent 后于此展开）";
    }
    if (action === "tag_question") {
      return "已识别【标记题目】指令：" + (p.question_id || "未指明题目") + "。";
    }
    if (action === "export_paper") {
      return "已识别【导出】指令：格式 " + (p.format || "未指明") + "。";
    }
    if (action === "clarify") {
      var question = p.question || (parsed && parsed.question) || "";
      // clarify 的问句本身若又是裸 JSON，说明模型没守规矩，拦下来给友好兜底。
      if (question && !looksLikeRawJson(question)) return question;
      return "我还不能确定你的意图，能否说得再具体些？比如「拆分第 1–2 页」或「导出为 PDF」。";
    }
    if (typeof parsed === "string") return parsed;
    return "已收到指令，但暂未识别为具体操作。（空壳原型：先见形，后调逻辑）";
  }

  // 右栏结构化上下文 → 注入 System 尾部，让模型结合前文干活而非反问。
  function gatherContext() {
    var active = findActiveProvider();
    var context = {
      current_task: currentTask || "未选择",
      stage: (stageTitle && stageTitle.textContent) || currentTask || "新会话",
      textbook: "未选择",
      model: active ? (active.model || active.label || "未知") : "未就绪",
      mock: active ? Boolean(active.mock || !active.configured) : true,
    };
    // 插件模式下把插件身份与能力一并注入 System 尾部；模型据此知道
    // 「现在处于该插件的工作模式下」，优先调用对应工具而不是空谈。
    if (activePlugin) {
      context.working_mode = "插件「" + (activePlugin.name || activePlugin.id) + "」工作模式";
      context.plugin = {
        id: activePlugin.id,
        name: activePlugin.name,
        version: activePlugin.version,
        kind: activePlugin.kind,
        description: activePlugin.description,
        capabilities: activePlugin.capabilities || [],
      };
    }
    return context;
  }

  function callAgent(prompt) {
    var payload = {
      user_input: prompt,
      task_id: "ws_" + Date.now(),
      context: gatherContext(),
      history: transcript.slice(-TRANSCRIPT_SEND),
    };
    return fetch("/api/agent/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (response) {
        // 正常信封读 data.content；模型异常时后端回 fallback.content（仍可用）
        var envelope = response && response.data ? response.data : response && response.fallback;
        var content = envelope && envelope.content;
        var pluginCalls = envelope && Array.isArray(envelope.plugin_calls) ? envelope.plugin_calls : [];
        var source = pluginCalls.length
          ? describePluginSource(response, pluginCalls)
          : describeSource(response);
        if (!content) {
          return { text: "模型没有返回内容，请检查 Provider 配置。", source: source, tone: "warn" };
        }
        // 插件结果已经是后端整理好的自然语言，直接展示，不再当控制 JSON 解析。
        if (pluginCalls.length) {
          return {
            text: stripFences(content),
            source: source,
            tone: null,
            pluginCalls: pluginCalls,
            route: response && response.route,
          };
        }
        // 拦截：先把内容当控制 JSON 解析。命中 action 就翻译成人话，
        // 命中无 action 的普通 JSON 给通用回执，都不把原始 JSON 露给用户。
        var parsed = extractControlJson(content);
        if (parsed) {
          if (typeof parsed.action === "string") {
            return { text: summarizeAction(parsed, source), source: source, tone: null };
          }
          return { text: "已收到模型的结构化回执（系统内部数据，已折叠）。", source: source, tone: null };
        }
        // 不是 JSON：若是裸围栏/括号开头，判定为控制信令漏网，绝不直接显示。
        if (looksLikeRawJson(content)) {
          return { text: "模型返回了未识别的系统信令，已拦截未显示。请换种说法再试一次。", source: source, tone: "warn" };
        }
        // 真正的自然语言散文，可以直接给用户看。
        return { text: stripFences(content), source: source, tone: null };
      });
  }

  if (chatForm) {
    chatForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var prompt = promptInput ? promptInput.value.trim() : "";
      if (!prompt) return;

      addBubble("user", prompt);
      logHistory("发送指令：" + (prompt.length > 24 ? prompt.slice(0, 24) + "…" : prompt));
      pushTurn("user", prompt);
      promptInput.value = "";
      autoGrow();

      if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.setAttribute("aria-busy", "true");
        sendBtn.textContent = "发送中…";
      }
      var typing = addTyping();

      callAgent(prompt)
        .then(function (res) {
          if (typing) typing.remove();
          addBubble("bot", res.text, {
            source: res.source,
            tone: res.tone,
            pluginCalls: res.pluginCalls,
            route: res.route,
          });
          if (res.pluginCalls && res.pluginCalls.length) {
            logHistory("调用插件：" + pluginCallNames(res.pluginCalls));
          }
          pushTurn("assistant", res.text);
        })
        .catch(function (err) {
          if (typing) typing.remove();
          addBubble("bot", "指令执行失败：" + err.message, { tone: "warn", source: "底座未响应或 Provider 不可用" });
          pushTurn("assistant", "指令执行失败：" + err.message);
        })
        .finally(function () {
          if (sendBtn) {
            sendBtn.disabled = false;
            sendBtn.removeAttribute("aria-busy");
            sendBtn.textContent = "发送";
          }
          if (promptInput) promptInput.focus();
        });
    });
  }

  // ============ 写令牌（一次性，用后即焚） ============
  function fetchWriteToken() {
    return fetch("/api/settings", { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("读取本机令牌失败（HTTP " + r.status + "）");
        return r.json();
      })
      .then(function (data) {
        var token = data && data.local_token ? String(data.local_token) : "";
        if (!token) throw new Error("本机未生成就绪令牌，请先启动服务后再试");
        writeToken = token;
        return token;
      });
  }

  function readErrorDetail(response, body) {
    var detail = body && body.detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail.message === "string") return detail.message;
    return "HTTP " + response.status;
  }

  // ============ 模型 Provider：加载 / 切换 / 配置 ============
  function findActiveProvider() {
    for (var i = 0; i < providerList.length; i += 1) {
      if (providerList[i].active) return providerList[i];
    }
    return null;
  }

  function renderModelChip() {
    var active = findActiveProvider();
    if (!modelLabel || !modelBtn) return;
    if (!active) {
      modelLabel.textContent = "模型 · 未就绪";
      modelBtn.setAttribute("data-state", "mock");
      if (ctxModel) ctxModel.textContent = "未就绪";
      return;
    }
    if (!active.configured || active.mock) {
      modelLabel.textContent = "模型 · " + active.label + "（Mock）";
      modelBtn.setAttribute("data-state", "mock");
      if (ctxModel) ctxModel.textContent = active.label + " · Mock 降级（未配置密钥）";
      return;
    }
    modelLabel.textContent = "模型 · " + (active.model || active.label);
    modelBtn.setAttribute("data-state", "live");
    if (ctxModel) ctxModel.textContent = active.label + " · " + (active.model || "已配置");
  }

  function loadProviders() {
    return fetch("/api/providers", { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        providerList = data.providers || [];
        if (providerSelect) {
          providerSelect.innerHTML = "";
          providerList.forEach(function (p) {
            var option = document.createElement("option");
            option.value = p.name;
            option.textContent = p.label + (p.configured ? "" : "（未配置）");
            if (p.active) option.selected = true;
            providerSelect.appendChild(option);
          });
        }
        renderModelChip();
        return data;
      });
  }

  function switchProvider(name) {
    return fetchWriteToken()
      .then(function (token) {
        return fetch("/api/providers/active", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-JZO-Token": token },
          body: JSON.stringify({ name: name }),
        });
      })
      .then(function (r) {
        if (!r.ok) {
          return r.json().catch(function () { return null; }).then(function (body) {
            throw new Error(readErrorDetail(r, body));
          });
        }
        return r.json();
      })
      .then(function (data) {
        addBubble("sys", data.mock
          ? "已切到「" + data.active + "」：未配置密钥，走 Mock"
          : "已切到「" + data.active + "」：真实模型 " + data.model);
        logHistory("切换 Provider：" + data.active);
        return loadProviders();
      })
      .finally(function () { writeToken = null; });
  }

  if (providerSelect) {
    providerSelect.addEventListener("change", function () {
      var name = providerSelect.value;
      if (!name) return;
      switchProvider(name).catch(function (err) {
        addBubble("sys", "切换 Provider 失败：" + err.message, { tone: "warn" });
        loadProviders().catch(function () {});
      });
    });
  }

  // --- Provider 配置弹窗 ---
  var providerModal = document.getElementById("wsProviderModal");
  var providerModalTarget = document.getElementById("wsProviderModalTarget");
  var providerBaseUrlInput = document.getElementById("wsProviderBaseUrl");
  var providerApiKeyInput = document.getElementById("wsProviderApiKey");
  var providerModelInput = document.getElementById("wsProviderModel");
  var providerTestBtn = document.getElementById("wsProviderTestBtn");
  var providerSaveBtn = document.getElementById("wsProviderSaveBtn");
  var providerTestResult = document.getElementById("wsProviderTestResult");
  var providerModalFocusBefore = null;

  function currentProviderName() {
    return providerSelect && providerSelect.value ? providerSelect.value : "";
  }

  function findProvider(name) {
    for (var i = 0; i < providerList.length; i += 1) {
      if (providerList[i].name === name) return providerList[i];
    }
    return null;
  }

  function renderProviderModalTarget() {
    if (!providerModalTarget) return;
    var profile = findProvider(currentProviderName());
    if (!profile) {
      providerModalTarget.textContent = "未选择 Provider";
      return;
    }
    providerModalTarget.textContent =
      profile.label + " · " + (profile.configured ? "已配置" : "未配置") +
      (profile.host ? " · " + profile.host : "") +
      (profile.model ? " · " + profile.model : "");
    if (providerBaseUrlInput) {
      providerBaseUrlInput.placeholder = profile.host
        ? "当前接口主机：" + profile.host + "（留空则不改）"
        : "https://api.example.com/v1";
    }
  }

  function setTestResult(text, tone) {
    if (!providerTestResult) return;
    providerTestResult.textContent = text || "";
    providerTestResult.setAttribute("data-tone", tone || "info");
    providerTestResult.hidden = !text;
  }

  function openProviderModal() {
    if (!providerModal) return;
    if (!providerList.length) {
      addBubble("sys", "Provider 注册表还没加载出来，稍候再试。", { tone: "warn" });
      return;
    }
    providerModalFocusBefore = document.activeElement;
    renderProviderModalTarget();
    if (providerBaseUrlInput) providerBaseUrlInput.value = "";
    if (providerApiKeyInput) providerApiKeyInput.value = "";
    var profile = findProvider(currentProviderName());
    if (providerModelInput) providerModelInput.value = profile ? profile.model || "" : "";
    setTestResult("", "info");
    providerModal.hidden = false;
    if (providerSelect) providerSelect.focus();
  }

  function closeProviderModal() {
    if (!providerModal) return;
    providerModal.hidden = true;
    if (providerModalFocusBefore && typeof providerModalFocusBefore.focus === "function") {
      providerModalFocusBefore.focus();
    }
    providerModalFocusBefore = null;
  }

  if (modelBtn) modelBtn.addEventListener("click", openProviderModal);

  document.querySelectorAll("[data-provider-modal-close]").forEach(function (btn) {
    btn.addEventListener("click", closeProviderModal);
  });

  document.addEventListener("keydown", function (event) {
    if (!providerModal || providerModal.hidden) return;
    if (event.key === "Escape") {
      event.preventDefault();
      closeProviderModal();
      return;
    }
    if (event.key === "Tab") {
      var focusables = providerModal.querySelectorAll(
        'button, input, select, textarea, a[href], [tabindex]:not([tabindex="-1"])'
      );
      if (!focusables.length) return;
      var first = focusables[0];
      var last = focusables[focusables.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });

  function collectProviderForm() {
    var payload = { name: currentProviderName() };
    var dirty = false;
    if (providerBaseUrlInput && providerBaseUrlInput.value.trim()) {
      payload.base_url = providerBaseUrlInput.value.trim();
      dirty = true;
    }
    if (providerApiKeyInput && providerApiKeyInput.value.trim()) {
      payload.api_key = providerApiKeyInput.value.trim();
      dirty = true;
    }
    if (providerModelInput && providerModelInput.value.trim()) {
      payload.model = providerModelInput.value.trim();
      dirty = true;
    }
    return { payload: payload, dirty: dirty };
  }

  function saveProviderConfig() {
    var form = collectProviderForm();
    if (!form.dirty) return Promise.resolve(false);
    providerSaveBtn.disabled = true;
    providerSaveBtn.setAttribute("aria-busy", "true");
    return fetchWriteToken()
      .then(function (token) {
        return fetch("/api/providers/config", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-JZO-Token": token },
          body: JSON.stringify(form.payload),
        });
      })
      .then(function (r) {
        return r.json().catch(function () { return null; }).then(function (body) {
          if (!r.ok) throw new Error(readErrorDetail(r, body));
          return true;
        });
      })
      .finally(function () {
        writeToken = null;
        providerSaveBtn.disabled = false;
        providerSaveBtn.setAttribute("aria-busy", "false");
      });
  }

  if (providerSaveBtn) {
    providerSaveBtn.addEventListener("click", function () {
      saveProviderConfig()
        .then(function (saved) {
          if (saved) {
            addBubble("sys", "配置已保存并热生效（密钥只落在本机 .env）");
            logHistory("保存 Provider 配置");
            if (providerApiKeyInput) providerApiKeyInput.value = "";
            if (providerBaseUrlInput) providerBaseUrlInput.value = "";
          }
          return loadProviders().then(renderProviderModalTarget);
        })
        .catch(function (err) {
          setTestResult("保存失败：" + err.message, "down");
        });
    });
  }

  if (providerTestBtn) {
    providerTestBtn.addEventListener("click", function () {
      providerTestBtn.disabled = true;
      providerTestBtn.setAttribute("aria-busy", "true");
      setTestResult("先把面板里未保存的改动存下来…", "info");
      var saved;
      saveProviderConfig()
        .then(function (didSave) {
          saved = didSave;
          setTestResult("正在向接口发一次只读 GET /models …", "info");
          return fetchWriteToken();
        })
        .then(function (token) {
          return fetch("/api/providers/test", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-JZO-Token": token },
            body: JSON.stringify({ name: currentProviderName() }),
          });
        })
        .then(function (r) {
          return r.json().catch(function () { return null; }).then(function (body) {
            if (!r.ok) throw new Error(readErrorDetail(r, body));
            setTestResult((body.ok ? "连通正常 ✓ " : "不通 ✗ ") + body.detail, body.ok ? "ok" : "down");
            writeToken = null;
            if (saved) return loadProviders().then(renderProviderModalTarget);
            return null;
          });
        })
        .catch(function (err) {
          writeToken = null;
          setTestResult("测试失败：" + err.message, "down");
        })
        .finally(function () {
          providerTestBtn.disabled = false;
          providerTestBtn.setAttribute("aria-busy", "false");
        });
    });
  }

  // ============ 已安装插件：动态渲染左栏插件区 ============
  var KIND_LABELS = { renderer: "渲染", importer: "导入", exporter: "导出", tool: "工具" };

  function renderPlugins(plugins) {
    var list = plugins || [];
    if (!pluginListEl) return;
    pluginListEl.textContent = "";
    if (!list.length) {
      var empty = document.createElement("li");
      empty.className = "ws-plugin-empty";
      empty.textContent = "暂无插件";
      pluginListEl.appendChild(empty);
      if (pluginCountEl) pluginCountEl.hidden = true;
      return;
    }
    list.forEach(function (plugin) {
      var li = document.createElement("li");
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "ws-plugin-item";
      btn.setAttribute("aria-current", String(Boolean(activePlugin && activePlugin.id === plugin.id)));
      var name = document.createElement("span");
      name.className = "ws-plugin-item-name";
      name.textContent = plugin.name || plugin.id || "未命名插件";
      var meta = document.createElement("span");
      meta.className = "ws-plugin-item-meta";
      meta.textContent = "v" + (plugin.version || "?") + " · " + (KIND_LABELS[plugin.kind] || "插件");
      btn.appendChild(name);
      btn.appendChild(meta);
      btn.addEventListener("click", function () { enterPluginMode(plugin, btn); });
      li.appendChild(btn);
      pluginListEl.appendChild(li);
    });
    if (pluginCountEl) {
      pluginCountEl.hidden = false;
      pluginCountEl.textContent = String(list.length);
    }
  }

  function loadPlugins() {
    return fetch("/api/plugins", { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        var plugins = (data && data.plugins) || [];
        if (activePlugin) {
          var still = null;
          for (var i = 0; i < plugins.length; i += 1) {
            if (plugins[i].id === activePlugin.id) { still = plugins[i]; break; }
          }
          if (still) {
            activePlugin = still;
          } else {
            activePlugin = null;
            setStage("自由对话");
            markActiveEntry(chatEntry);
          }
        }
        renderPlugins(plugins);
        return plugins;
      });
  }

  // ============ 插件一键装：拖拽 zip + 选文件（简单入口，反馈进对话流） ============
  var pluginInstallBtn = document.getElementById("wsPluginInstallBtn");
  var pluginFileInput = document.getElementById("wsPluginFile");
  var dropOverlay = document.getElementById("wsDropOverlay");
  var dragDepth = 0;

  function installPluginZip(file, replace) {
    if (!file) return Promise.resolve();
    if (!/\.zip$/i.test(file.name || "")) {
      addBubble("sys", "只接受 .zip 插件包（标准 zip，解压即用）。", { tone: "warn" });
      return Promise.resolve();
    }
    if (file.size > 50 * 1024 * 1024) {
      addBubble("sys", "zip 包超过 50 MB 上限。", { tone: "warn" });
      return Promise.resolve();
    }
    addBubble("sys", "正在安装 " + file.name + " …");
    if (pluginInstallBtn) {
      pluginInstallBtn.disabled = true;
      pluginInstallBtn.setAttribute("aria-busy", "true");
    }
    return fetchWriteToken()
      .then(function (token) {
        return fetch("/api/plugins/install" + (replace ? "?replace=true" : ""), {
          method: "POST",
          headers: { "Content-Type": "application/zip", "X-JZO-Token": token },
          body: file,
        });
      })
      .then(function (r) {
        return r.json().catch(function () { return null; }).then(function (body) {
          if (r.status === 409 && !replace) {
            var question = readErrorDetail(r, body) + " 覆盖升级会先删除旧目录，继续吗？";
            if (window.confirm(question)) return installPluginZip(file, true);
            return null;
          }
          if (!r.ok) throw new Error(readErrorDetail(r, body));
          var plugin = body && body.plugin ? body.plugin : {};
          addBubble("sys", "插件已安装：" + (plugin.name || plugin.id) + " v" + (plugin.version || "?"));
          logHistory("安装插件 " + (plugin.name || plugin.id));
          // 装完立即刷新插件区；刷新失败不回滚安装结果，也不谎报安装失败。
          return loadPlugins().catch(function () { return null; });
        });
      })
      .catch(function (err) {
        addBubble("sys", "插件安装失败：" + err.message, { tone: "warn" });
      })
      .finally(function () {
        writeToken = null;
        if (pluginInstallBtn) {
          pluginInstallBtn.disabled = false;
          pluginInstallBtn.setAttribute("aria-busy", "false");
        }
      });
  }

  function pickFirstZip(fileList) {
    for (var i = 0; i < (fileList || []).length; i += 1) {
      if (/\.zip$/i.test(fileList[i].name || "")) return fileList[i];
    }
    return null;
  }

  function hasFiles(event) {
    var types = (event.dataTransfer && event.dataTransfer.types) || [];
    return Array.prototype.indexOf.call(types, "Files") !== -1;
  }

  function showDropOverlay(show) {
    if (!dropOverlay) return;
    dropOverlay.hidden = !show;
  }

  window.addEventListener("dragenter", function (event) {
    if (!hasFiles(event)) return;
    event.preventDefault();
    dragDepth += 1;
    showDropOverlay(true);
  });
  window.addEventListener("dragover", function (event) {
    if (!hasFiles(event)) return;
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
  });
  window.addEventListener("dragleave", function (event) {
    if (!hasFiles(event)) return;
    dragDepth -= 1;
    if (dragDepth <= 0) {
      dragDepth = 0;
      showDropOverlay(false);
    }
  });
  window.addEventListener("drop", function (event) {
    if (!hasFiles(event)) return;
    event.preventDefault();
    dragDepth = 0;
    showDropOverlay(false);
    var file = pickFirstZip(event.dataTransfer && event.dataTransfer.files);
    if (!file) {
      addBubble("sys", "没看到 .zip 文件：插件包必须是标准 zip。", { tone: "warn" });
      return;
    }
    installPluginZip(file, false);
  });

  if (pluginInstallBtn && pluginFileInput) {
    pluginInstallBtn.addEventListener("click", function () {
      pluginFileInput.click();
    });
    pluginFileInput.addEventListener("change", function () {
      var file = pluginFileInput.files && pluginFileInput.files[0];
      pluginFileInput.value = "";
      if (file) installPluginZip(file, false);
    });
  }

  // ============ 初始化 ============
  // 默认入口只有「自由对话」；插件区完全由 /api/plugins 的发现结果渲染。
  setStage("自由对话");
  markActiveEntry(chatEntry);
  addBubble("sys", "九章算子工作台已就绪 · 已装插件会自动接入对话工具（tool_calls），结果以「已调用插件」标识回显");
  addBubble("bot", "你好，我是九章算子工作台助手。从左侧选择「自由对话」或某个已安装插件，也可以直接在下方输入指令。进入插件工作模式后，我会优先调用该插件的能力。");

  // 种子题库插件在场时才提示示例题（10.24 军令任务 2）：插件被删就不许说谎。
  loadPlugins()
    .then(function (plugins) {
      var hasDemo = plugins.some(function (p) { return p.id === "org.jiuzhang.demo-bank"; });
      if (hasDemo) {
        addBubble("bot", "系统已为您预置了 5 道示例数学题，您可以直接输入「拆分第一题」进行体验。");
      }
    })
    .catch(function () { /* 探测失败保留「暂无插件」空态，不打扰用户 */ });

  loadProviders().catch(function () {
    renderModelChip();
  });
})();
