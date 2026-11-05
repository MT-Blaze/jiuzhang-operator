/**
 * AI 助手插件（org.jiuzhang.chat）——右栏 sidebar.right 的默认主人。
 *
 * 军令 #15 的定调：AI 是**普通插件**，不是底座的特权成员。
 * - 不直连数据库、不联网、不读宿主 DOM、不碰浏览器存储：所有读写都以
 *   ``jzo-plugin/1`` 的 request 交给宿主，由底座按白名单代为执行；
 * - 没有「替用户点击」的能力：底座已删除按钮模拟通道，本插件也不提供
 *   任何 dispatchEvent / 键盘模拟；参数变更只能发 ui.params.set 请求，
 *   由宿主仲裁（人类手改过的字段优先）后再广播给目标插件；
 * - 智能跳转只交意图：回复里的动作按钮点下去后发 stage.open_bank /
 *   stage.open_editor 请求，打开页签与注入搜索词都由宿主完成。
 *
 * 渲染安全：模型与插件返回的文本一律 textContent 落 DOM，只有本地 MathJax
 * 自己生成的 HTML 才进 innerHTML（trust:false）。
 */
(function () {
  "use strict";

  var PROTOCOL = "jzo-plugin/1";
  var PLUGIN_ID = "org.jiuzhang.chat";
  var FAST_TIMEOUT_MS = 12000;
  var AGENT_TIMEOUT_MS = 32000;
  var TRANSCRIPT_MAX = 24;
  var TRANSCRIPT_SEND = 8;

  var root = document.getElementById("chatRoot");
  var thread = document.getElementById("chatThread");
  var promptInput = document.getElementById("chatPrompt");
  var sendBtn = document.getElementById("chatSend");
  var modeChip = document.getElementById("chatModeChip");
  var modelChip = document.getElementById("chatModelChip");
  var copilot = document.getElementById("chatCopilot");
  var copilotCtx = document.getElementById("copilotCtx");
  var copilotField = document.getElementById("copilotField");
  var copilotInput = document.getElementById("copilotInput");
  var copilotAsk = document.getElementById("copilotAsk");
  var copilotApply = document.getElementById("copilotApply");
  var copilotOut = document.getElementById("copilotOut");

  var pending = new Map();
  var requestSeq = 0;

  // 底座状态快照（由宿主 workspace.state 供给）：当前舞台、工作模式插件、
  // 面板参数与模型 Provider。插件只读它，不自己去猜。
  var workspace = { current_task: "", stage: "", plugin: null, ui: null, provider: null };
  var transcript = [];
  var editorContext = { id: "", question: null, at: 0 };
  var pendingPatch = null;
  // AI 改写是否在飞行中：期间的通知重渲染不许把【让 AI 改写】按钮重新点亮，
  // 否则一次点击能发两遍 agent.refine。
  var refineBusy = false;

  // ---------- 宿主通信 ----------
  function hostCall(method, payload, timeoutMs) {
    return new Promise(function (resolve, reject) {
      requestSeq += 1;
      var id = "c" + requestSeq + "_" + Date.now().toString(36);
      var limit = timeoutMs || FAST_TIMEOUT_MS;
      var timer = window.setTimeout(function () {
        pending.delete(id);
        reject(new Error("宿主响应超时（" + Math.round(limit / 1000) + "s）"));
      }, limit);
      pending.set(id, {
        resolve: function (result) { window.clearTimeout(timer); resolve(result); },
        reject: function (error) { window.clearTimeout(timer); reject(error); }
      });
      try {
        window.parent.postMessage({
          protocol: PROTOCOL, id: id, kind: "request", method: method, payload: payload || {}
        }, "*");
      } catch (error) {
        pending.delete(id);
        window.clearTimeout(timer);
        reject(error);
      }
    });
  }

  function publish(event, payload) {
    try {
      window.parent.postMessage({
        protocol: PROTOCOL, kind: "notification", event: event, payload: payload || {}
      }, "*");
    } catch (error) { /* 通知丢一帧不致命 */ }
  }

  function dock(text) {
    publish("region.dock", { text: String(text || "").slice(0, 200) });
  }

  function respond(source, id, ok, result, code, message) {
    var packet = { protocol: PROTOCOL, id: id, kind: "response", ok: ok };
    if (ok) packet.result = result || {};
    else packet.error = { code: code || "ERROR", message: message || "失败", retryable: false };
    try { source.postMessage(packet, "*"); } catch (error) { /* 宿主已走 */ }
  }

  // ---------- 文本与公式 ----------
  function clampText(value, limit) {
    return String(value == null ? "" : value).trim().slice(0, limit);
  }

  function renderMathInto(el, text) {
    var source = String(text == null ? "" : text);
    if (!source) return;
    var pattern = /(\$\$[\s\S]*?\$\$|\$[^$\n]*?\$|\\paren\*?(?:\[[^\]]*\])?)/g;
    var last = 0;
    var match;
    while ((match = pattern.exec(source)) !== null) {
      if (match.index > last) {
        el.appendChild(document.createTextNode(source.slice(last, match.index)));
      }
      var token = match[0];
      var paren = token.slice(0, 6) === "\\paren";
      var display = !paren && token.slice(0, 2) === "$$";
      var body = paren ? token : (display ? token.slice(2, -2) : token.slice(1, -1));
      var html = window.JzoMath ? window.JzoMath.render(body, display) : "";
      if (html) {
        var node = document.createElement(display ? "div" : "span");
        node.className = display ? "jzochat-math-block" : "jzochat-math";
        node.innerHTML = html;
        el.appendChild(node);
      } else {
        el.appendChild(document.createTextNode(token));
      }
      last = pattern.lastIndex;
    }
    if (last < source.length) el.appendChild(document.createTextNode(source.slice(last)));
  }

  function scrollToEnd() {
    if (thread) thread.scrollTop = thread.scrollHeight;
  }

  function callNames(calls) {
    var names = [];
    (calls || []).forEach(function (call) {
      var name = call && call.plugin && call.plugin.name ? call.plugin.name : (call && call.tool) || "底座";
      if (names.indexOf(name) === -1) names.push(name);
    });
    return names.join("、");
  }

  function buildBubble(role, text, opts) {
    opts = opts || {};
    var wrap = document.createElement("div");
    wrap.className = "jzochat-msg jzochat-msg-" + role;
    var hasText = !!(String(text == null ? "" : text).trim());
    if (hasText || opts.pluginCalls || opts.source) {
      var bubble = document.createElement("div");
      bubble.className = "jzochat-bubble";
      if (opts.tone) bubble.setAttribute("data-tone", opts.tone);
      if (hasText) {
        if (opts.richText && role === "bot") renderMathInto(bubble, text);
        else bubble.textContent = text;
      }
      if (opts.pluginCalls && opts.pluginCalls.length) {
        var badge = document.createElement("span");
        badge.className = "jzochat-badge";
        badge.textContent = "[已调用] " + callNames(opts.pluginCalls);
        badge.title = opts.route === "host"
          ? "模型未发起工具调用，由底座按明确意图代为执行"
          : "由模型发起 tool_calls，底座执行并回传结果";
        bubble.insertBefore(badge, bubble.firstChild);
      }
      if (opts.source) {
        var src = document.createElement("span");
        src.className = "jzochat-source";
        src.textContent = opts.source;
        bubble.appendChild(src);
      }
      wrap.appendChild(bubble);
    }
    (opts.cards || []).forEach(function (card) {
      var node = buildCard(card);
      if (node) wrap.appendChild(node);
    });
    (opts.actions || []).forEach(function (action) {
      wrap.appendChild(buildActionButton(action));
    });
    return wrap;
  }

  function addBubble(role, text, opts) {
    if (!thread) return null;
    var wrap = buildBubble(role, text, opts);
    thread.appendChild(wrap);
    scrollToEnd();
    return wrap;
  }

  function addTyping() {
    if (!thread) return null;
    var wrap = document.createElement("div");
    wrap.className = "jzochat-msg jzochat-msg-bot";
    var bubble = document.createElement("div");
    bubble.className = "jzochat-bubble";
    var typing = document.createElement("span");
    typing.className = "jzochat-typing";
    for (var i = 0; i < 3; i += 1) typing.appendChild(document.createElement("i"));
    bubble.appendChild(typing);
    wrap.appendChild(bubble);
    thread.appendChild(wrap);
    scrollToEnd();
    return wrap;
  }

  // ---------- 富卡片：题卡 / 安装建议 / 操作确认 / 智能跳转，已拆到 ui_cards.js（§2.8.1） ----------
  var cards = window.JzoChatCards.create({
    clampText: clampText,
    renderMathInto: renderMathInto,
    hostCall: hostCall,
    addBubble: addBubble,
    dock: dock,
    refreshWorkspace: refreshWorkspace,
    sendPrompt: sendPrompt,
    AGENT_TIMEOUT_MS: AGENT_TIMEOUT_MS
  });
  var splitUiBlocks = cards.splitUiBlocks;
  var buildCard = cards.buildCard;
  var buildActionButton = cards.buildActionButton;

  // ---------- 动作 JSON 拦截 ----------
  function stripFences(text) {
    if (typeof text !== "string") return "";
    var trimmed = text.trim();
    var fence = trimmed.match(/^```[a-zA-Z0-9_-]*[ \t]*\r?\n?([\s\S]*?)\r?\n?```[ \t]*$/);
    return fence ? fence[1].trim() : trimmed;
  }

  function extractControlJson(content) {
    var body = stripFences(content);
    if (!body) return null;
    try {
      var direct = JSON.parse(body);
      if (direct && typeof direct === "object") return direct;
    } catch (error) { /* 落到抠取 */ }
    var brace = body.match(/\{[\s\S]*\}/);
    if (brace) {
      try {
        var extracted = JSON.parse(brace[0]);
        if (extracted && typeof extracted === "object") return extracted;
      } catch (error) { /* 不是对象就当散文 */ }
    }
    return null;
  }

  function looksLikeRawJson(text) {
    return /^\s*(```|[\[{])/.test(text || "");
  }

  function summarizeAction(parsed) {
    var action = parsed && parsed.action;
    var p = (parsed && parsed.params) ? parsed.params : (parsed || {});
    if (action === "split_paper") {
      var range = Array.isArray(p.page_range) ? p.page_range : [];
      var pageText = range.length === 2 ? "第 " + range[0] + "–" + range[1] + " 页" : "全卷";
      return "已识别【拆题】指令：" + pageText + "。";
    }
    if (action === "tag_question") return "已识别【标记题目】指令：" + (p.question_id || "未指明题目") + "。";
    if (action === "export_paper") return "已识别【导出】指令：格式 " + (p.format || "未指明") + "。";
    if (action === "clarify") {
      var question = p.question || (parsed && parsed.question) || "";
      if (question && !looksLikeRawJson(question)) return question;
      return "我还不能确定你的意图，能否说得再具体些？比如「拆分第 1–2 页」或「导出为 PDF」。";
    }
    if (action === "update_params") {
      var params = parsed.params && typeof parsed.params === "object" ? parsed.params : {};
      var pairs = Object.keys(params).map(function (key) { return key + "=" + params[key]; });
      return pairs.length ? "好，我请求底座把面板调成：" + pairs.join("、") + "。" : "好，我来请求调整面板参数。";
    }
    return "已收到指令，但暂未识别为具体操作。";
  }

  // ---------- 上下文与状态 ----------
  function refreshWorkspace() {
    return hostCall("workspace.state").then(function (state) {
      workspace = state || workspace;
      renderChips();
      renderCopilotVisibility();
      return workspace;
    }, function () { /* 读不到状态就保持上一次快照，不打扰用户 */ });
  }

  function renderChips() {
    var plugin = workspace.plugin;
    if (modeChip) {
      modeChip.textContent = plugin && plugin.name ? "插件「" + plugin.name + "」工作模式"
        : (workspace.current_task || "自由对话");
    }
    if (!modelChip) return;
    var provider = workspace.provider || {};
    if (provider.mock || provider.configured === false) {
      modelChip.textContent = "Mock 降级（Provider 未配置密钥）";
      return;
    }
    modelChip.textContent = "模型 " + (provider.model || provider.label || "未知");
  }

  function gatherContext() {
    var context = {
      current_task: workspace.current_task || "未选择",
      stage: workspace.stage || workspace.current_task || "新会话",
      model: (workspace.provider && (workspace.provider.model || workspace.provider.label)) || "未就绪",
      mock: workspace.provider ? Boolean(workspace.provider.mock || workspace.provider.configured === false) : true
    };
    if (workspace.plugin) {
      context.working_mode = "插件「" + (workspace.plugin.name || workspace.plugin.id) + "」工作模式";
      context.plugin = {
        id: workspace.plugin.id,
        name: workspace.plugin.name,
        version: workspace.plugin.version,
        kind: workspace.plugin.kind,
        capabilities: workspace.plugin.capabilities || []
      };
    }
    if (workspace.ui && workspace.ui.controls && workspace.ui.controls.length) {
      context.ui = workspace.ui;
    }
    if (editorContext.question) {
      context.editing = { id: editorContext.id, stem: clampText(editorContext.question.stem, 240) };
    }
    return context;
  }

  function describeSource(envelope, pluginCalls) {
    if (envelope && envelope.route === "host") return "底座按意图代为执行（模型未参与）";
    if (envelope && envelope.mock) return pluginCalls.length ? "Mock 模型发起 · 底座真实执行" : "Mock 降级";
    var data = (envelope && envelope.data) || {};
    var model = data.model || "未知";
    return pluginCalls.length ? "模型 " + model + " 发起 · 底座真实执行" : "模型 " + model + " 产出";
  }

  /** 把底座回的信封翻译成气泡内容；控制 JSON 绝不当散文显示。 */
  function interpret(envelope) {
    var data = envelope && envelope.data ? envelope.data : (envelope && envelope.fallback) || {};
    var content = data.content;
    var pluginCalls = Array.isArray(data.plugin_calls) ? data.plugin_calls : [];
    var actions = Array.isArray(data.actions) ? data.actions : [];
    var commandRequests = [];
    pluginCalls.forEach(function (call) {
      if (call && call.command_request && call.command_request.command_id) {
        commandRequests.push(call.command_request);
      }
    });
    var source = describeSource(envelope, pluginCalls);
    if (!content) {
      return {
        text: "模型没有返回内容，请检查 Provider 配置。", tone: "warn", source: source,
        cards: [], actions: [], commandRequests: commandRequests
      };
    }
    var split = splitUiBlocks(content);
    var body = stripFences(split.text);
    var cards = split.cards;

    if (pluginCalls.length) {
      return {
        text: body, source: source, cards: cards,
        pluginCalls: pluginCalls, route: envelope && envelope.route, actions: actions,
        commandRequests: commandRequests
      };
    }
    if (!body && cards.length) return { text: "", source: source, cards: cards, actions: actions };

    var parsed = body ? extractControlJson(body) : null;
    if (parsed) {
      var action = typeof parsed.action === "string" ? parsed.action : "";
      if (action === "update_params") {
        var params = parsed.params && typeof parsed.params === "object" ? parsed.params : {};
        if (!Object.keys(params).length) {
          Object.keys(parsed).forEach(function (key) {
            if (key !== "action" && key !== "message") params[key] = parsed[key];
          });
        }
        return {
          text: summarizeAction(parsed), source: source, cards: cards,
          control: { action: "update_params", params: params }
        };
      }
      if (action) return { text: summarizeAction(parsed), source: source, cards: cards };
      return {
        text: cards.length ? "" : "已收到模型的结构化回执（系统内部数据，已折叠）。",
        source: source, cards: cards
      };
    }
    if (body && looksLikeRawJson(body)) {
      return {
        text: "模型返回了未识别的系统信令，已拦截未显示。请换种说法再试一次。",
        tone: "warn", source: source, cards: cards
      };
    }
    return { text: body, source: source, cards: cards, richText: true, actions: actions };
  }

  // ---------- 对话记忆的托管（浏览器存储由宿主代持） ----------
  // 沙箱 iframe 是不透明源，插件自己读写浏览器存储会直接抛 SecurityError；
  // 而右栏主权交替时本插件的 iframe 会被底座摘掉。所以对话记录经 draft.* 交给宿主，
  // 切回来还能接着聊——这也是「AI 没有底层特权」的对价：记忆不由它自己藏。
  var DRAFT_KEY = "transcript";
  var draftTimer = 0;

  function saveTranscript() {
    return hostCall("draft.save", { key: DRAFT_KEY, value: transcript.slice(-TRANSCRIPT_MAX) }, 8000)
      .then(function () { return true; }, function () { return false; });
  }

  function scheduleDraftSave() {
    if (draftTimer) window.clearTimeout(draftTimer);
    draftTimer = window.setTimeout(function () {
      draftTimer = 0;
      saveTranscript();
    }, 600);
  }

  function restoreTranscript() {
    return hostCall("draft.load", { key: DRAFT_KEY }, 8000).then(function (result) {
      var saved = result && Array.isArray(result.value) ? result.value : [];
      if (!saved.length || transcript.length) return;
      transcript = saved.slice(-TRANSCRIPT_MAX);
      transcript.forEach(function (turn) {
        if (!turn || !turn.content) return;
        addBubble(turn.role === "user" ? "user" : "bot", turn.content);
      });
      addBubble("sys", "已接上此前的对话（" + transcript.length + " 条）。");
    }, function () { /* 没有存档也正常：新会话照聊 */ });
  }

  function pushTurn(role, content) {
    if (!content) return;
    transcript.push({ role: role, content: String(content) });
    while (transcript.length > TRANSCRIPT_MAX) transcript.shift();
    scheduleDraftSave();
  }

  function setSending(active) {
    if (!sendBtn) return;
    sendBtn.disabled = active;
    if (active) {
      sendBtn.setAttribute("aria-busy", "true");
      sendBtn.textContent = "发送中…";
    } else {
      sendBtn.removeAttribute("aria-busy");
      sendBtn.textContent = "发送";
    }
  }

  function originNote(options) {
    if (!options) return "";
    if (options.origin === "panel_button") return "面板按钮 · 你点了「" + (options.label || "按钮") + "」";
    if (options.origin === "confirm_card") return "卡片按钮";
    return "";
  }

  /**
   * AI 建议的参数交给宿主仲裁（军令 #15 任务 2.1）：
   * 插件带上「我发请求时看到的 revisions 快照」，人在这期间动过的字段一律不覆盖。
   */
  function applyParamsByHost(params) {
    var snapshot = (workspace.ui && workspace.ui.revisions) || {};
    var pluginId = (workspace.ui && workspace.ui.plugin_id) || (workspace.plugin && workspace.plugin.id) || "";
    return hostCall("ui.params.set", {
      plugin_id: pluginId,
      params: params,
      snapshot: snapshot
    }).then(function (result) {
      var applied = (result && result.applied) || [];
      var skipped = (result && result.skipped) || [];
      if (applied.length) {
        addBubble("sys", "面板已更新：" + applied.map(function (item) {
          return item.label + " 设为「" + item.value + "」";
        }).join("，") + "。");
      }
      if (skipped.length) {
        addBubble("sys", "以下参数保留了你手动设定的值：" + skipped.map(function (item) {
          return item.label + "（" + item.reason + "）";
        }).join("，") + "。", { tone: "warn" });
      }
      if (!applied.length && !skipped.length) {
        addBubble("sys", "当前没有可由 AI 设定的参数（面板没有下拉项），已忽略这次调整。", { tone: "warn" });
      }
      return refreshWorkspace();
    }, function (error) {
      addBubble("sys", "请求底座设置参数失败：" + error.message, { tone: "warn" });
    });
  }

  /**
   * 底座把「有界面插件的命令」回成 command_request，由宿主转发给目标插件。
   * 目标页签自动打开、串行与 requires_user 确认仍由宿主 stage.js 负责；
   * 本插件只交命令 id 与已经底座校验过的 context，不自己拼路由。
   */
  function runCommandRequest(request) {
    var title = clampText(request.title, 40) || clampText(request.command_id, 60);
    return hostCall("command.execute", {
      command_id: request.command_id,
      context: request.context && typeof request.context === "object" ? request.context : {}
    }, 30000).then(function (result) {
      addBubble("sys", "命令「" + title + "」已由「"
        + (clampText(request.plugin_name, 24) || "目标插件") + "」执行。");
      return result;
    }, function (error) {
      var message = error && error.code === "COMMAND_DENIED"
        ? "你在宿主确认框里拒绝了这条命令，未执行。"
        : "命令未执行：" + ((error && error.message) || "未知原因");
      addBubble("sys", "「" + title + "」" + message, { tone: "warn" });
    });
  }

  function runCommandRequests(requests) {
    return requests.reduce(function (chain, request) {
      return chain.then(function () { return runCommandRequest(request); });
    }, Promise.resolve());
  }

  function sendPrompt(prompt, options) {
    options = options || {};
    var text = String(prompt == null ? "" : prompt).trim();
    if (!text) return Promise.resolve();
    // 确认码是卡片的控制信令：只发请求不留气泡，避免把内部令牌印进对话。
    if (!options.silent) {
      addBubble("user", text, originNote(options) ? { source: originNote(options) } : undefined);
    }
    // 历史在推进去之前取：只带「本轮之前」的轮次，本轮指令由后端当 user 消息。
    var history = transcript.slice(-TRANSCRIPT_SEND);
    if (!options.silent) pushTurn("user", text);
    if (promptInput) {
      promptInput.value = "";
      autoGrow();
    }
    setSending(true);
    var typing = addTyping();
    return hostCall("agent.chat", {
      user_input: text,
      context: gatherContext(),
      history: history,
      task_id: "chat_" + Date.now()
    }, AGENT_TIMEOUT_MS).then(function (envelope) {
      if (typing) typing.remove();
      var res = interpret(envelope || {});
      addBubble("bot", res.text, {
        source: res.source,
        tone: res.tone,
        cards: res.cards,
        pluginCalls: res.pluginCalls,
        route: res.route,
        actions: res.actions,
        richText: res.richText
      });
      pushTurn("assistant", res.text || (res.cards && res.cards.length ? "[已展示可视化卡片]" : ""));
      if (res.pluginCalls && res.pluginCalls.length) {
        dock("AI 助手经宿主调用：" + callNames(res.pluginCalls));
      }
      var follow = null;
      if (res.commandRequests && res.commandRequests.length) {
        follow = runCommandRequests(res.commandRequests);
      }
      if (res.control && res.control.action === "update_params") {
        follow = follow
          ? follow.then(function () { return applyParamsByHost(res.control.params); })
          : applyParamsByHost(res.control.params);
      }
      return follow;
    }, function (error) {
      if (typing) typing.remove();
      addBubble("bot", "指令执行失败：" + error.message, { tone: "warn", source: "底座未响应或 Provider 不可用" });
      pushTurn("assistant", "指令执行失败：" + error.message);
    }).finally(function () {
      setSending(false);
      if (promptInput) promptInput.focus();
    });
  }

  function autoGrow() {
    if (!promptInput) return;
    promptInput.style.height = "auto";
    promptInput.style.height = Math.min(promptInput.scrollHeight, 120) + "px";
  }

  // ---------- AI 副驾：改写当前题并回填 ----------
  function renderCopilotVisibility() {
    if (!copilot) return;
    copilot.hidden = !editorContext.question;
    if (copilotAsk) copilotAsk.disabled = !editorContext.question || refineBusy;
    if (copilotApply) copilotApply.disabled = !(editorContext.question && pendingPatch);
    if (copilotCtx) {
      copilotCtx.textContent = editorContext.question
        ? (editorContext.id ? "正在编辑 " + editorContext.id : "正在录入新题")
        : "尚未打开题目";
    }
  }

  function askRefine() {
    if (!editorContext.question) return;
    var instruction = clampText(copilotInput && copilotInput.value, 400);
    if (!instruction) {
      if (copilotCtx) copilotCtx.textContent = "请先写一句改写指令";
      return;
    }
    var field = copilotField && copilotField.value === "solution" ? "solution" : "stem";
    var targetId = editorContext.id;
    refineBusy = true;
    copilotAsk.disabled = true;
    copilotAsk.setAttribute("aria-busy", "true");
    copilotAsk.textContent = "改写中…";
    if (copilotCtx) copilotCtx.textContent = "AI 改写中…";
    pendingPatch = null;
    hostCall("agent.refine", {
      question: editorContext.question,
      instruction: instruction,
      field: field,
      task_id: "cp_" + Date.now()
    }, AGENT_TIMEOUT_MS).then(function (result) {
      var value = result && result.value;
      var note = result && result.note;
      if (typeof value !== "string" || !value.trim()) {
        if (copilotCtx) copilotCtx.textContent = "AI 没有给出可用的改写内容";
        return;
      }
      pendingPatch = { id: targetId, field: field, value: value };
      if (copilotOut) copilotOut.textContent = (note ? note + "\n\n" : "") + value;
      if (copilotCtx) copilotCtx.textContent = (field === "solution" ? "解析" : "题干") + "改写完成，点「回填到表单」";
    }, function (error) {
      if (copilotCtx) copilotCtx.textContent = "改写失败：" + error.message;
    }).finally(function () {
      refineBusy = false;
      copilotAsk.disabled = false;
      copilotAsk.removeAttribute("aria-busy");
      copilotAsk.textContent = "让 AI 改写";
      renderCopilotVisibility();
    });
  }

  function applyRefinePatch() {
    if (!pendingPatch) return;
    hostCall("editor.apply_patch", {
      id: pendingPatch.id, field: pendingPatch.field, value: pendingPatch.value
    }).then(function () {
      if (copilotCtx) copilotCtx.textContent = "已回填到录题表单，请核对后保存";
      dock("AI 助手把改写的" + (pendingPatch.field === "solution" ? "解析" : "题干") + "回填到了录题工作台");
      pendingPatch = null;
      renderCopilotVisibility();
    }, function (error) {
      if (copilotCtx) copilotCtx.textContent = "回填失败：" + error.message;
    });
  }

  // ---------- 协议入口 ----------
  window.addEventListener("message", function (event) {
    var message = event.data;
    if (!message || message.protocol !== PROTOCOL) return;

    if (message.kind === "response" && pending.has(message.id)) {
      var waiter = pending.get(message.id);
      pending.delete(message.id);
      if (message.ok) waiter.resolve(message.result || {});
      else {
        var err = new Error((message.error && message.error.message) || "宿主返回失败");
        err.code = (message.error && message.error.code) || "";
        waiter.reject(err);
      }
      return;
    }

    if (message.kind === "notification") {
      var payload = message.payload || {};
      if (message.event === "stage.selection") {
        var raw = payload.raw || {};
        if (raw.pluginId === "org.jiuzhang.editor") {
          editorContext.question = raw.question || null;
          editorContext.id = typeof raw.editingId === "string" ? raw.editingId : "";
          editorContext.at = Date.now();
          pendingPatch = null;
          renderCopilotVisibility();
        }
        return;
      }
      if (message.event === "stage.tab.closed") {
        if (String(payload.key || "").indexOf("org.jiuzhang.editor") >= 0) {
          editorContext = { id: "", question: null, at: 0 };
          pendingPatch = null;
          if (copilotOut) copilotOut.textContent = "";
          renderCopilotVisibility();
        }
        return;
      }
      if (message.event === "stage.tab.activated" || message.event === "plugin.updated"
        || message.event === "question.updated") {
        refreshWorkspace();
        return;
      }
      // 人点了右栏「插件快捷操作」里的按钮：底座把展开好的指令交给我，由我这一轮说出去。
      // 我仍然是唯一的对话入口——按钮不直接调 Agent，也不允许我替人去点任何控件。
      if (message.event === "panel.button.click") {
        var command = typeof payload.command === "string" ? payload.command.trim() : "";
        if (!command || !sendBtn || sendBtn.disabled) return;
        sendPrompt(command, {
          origin: "panel_button",
          label: typeof payload.label === "string" ? payload.label : ""
        });
        return;
      }
      return;
    }

    if (message.kind !== "request") return;
    if (message.method === "plugin.activate") {
      root.hidden = false;
      if (promptInput) promptInput.focus();
      bootstrap();
      restoreTranscript();
      return respond(event.source, message.id, true, { ready: true, plugin_id: PLUGIN_ID });
    }
    if (message.method === "plugin.deactivate") {
      // 交还右栏主权前先把对话记忆存回宿主，切回来才接得上
      saveTranscript();
      root.hidden = true;
      return respond(event.source, message.id, true, { ready: false });
    }
    respond(event.source, message.id, false, null, "UNSUPPORTED_METHOD", "未实现的方法：" + message.method);
  });

  // ---------- 启动 ----------
  var greeted = false;

  function bootstrap() {
    refreshWorkspace();
    if (greeted) return;
    greeted = true;
    addBubble("sys", "AI 助手已作为普通插件挂载在右栏：我只能通过底座接口干活，读不到你的数据库，也点不了任何按钮。");
    addBubble("bot", "你好，我是九章算子助手。可以直接说话，比如「查一下题库里有多少道导数题」「拆分第一题」「找个能导出 PDF 的插件」。");
    announceSeedBank();
  }

  /**
   * 种子题库在场才提示例题（10.24 军令任务 2 的口径）：插件被删就不许说谎，
   * 所以现场向底座要清单，而不是把「已预置 5 道题」写死在宿主壳里。
   */
  function announceSeedBank() {
    hostCall("plugins.list", {}).then(function (result) {
      var hasDemo = ((result && result.plugins) || []).some(function (item) {
        return item && item.id === "org.jiuzhang.demo-bank" && item.enabled !== false;
      });
      if (hasDemo) {
        addBubble("bot", "系统已为您预置了 5 道示例数学题，您可以直接输入「拆分第一题」进行体验。");
      }
    }, function () { /* 读不到清单就不提示：宁缺毋谎 */ });
  }

  // 沙箱 iframe 没开 allow-forms，浏览器会在提交前直接掐掉表单原生提交（连 submit 事件都不发）。
  // 所以发送只有「点按钮」和「输入框 Enter」两条显式路径，共用同一个出口，不依赖任何表单原生行为。
  function submitFromComposer() {
    var prompt = promptInput ? promptInput.value.trim() : "";
    if (!prompt) {
      // 空内容按 Enter：不发、不提示，只把焦点留在输入框。
      if (promptInput) promptInput.focus();
      return;
    }
    sendPrompt(prompt, { origin: "human" });
  }

  if (sendBtn) sendBtn.addEventListener("click", submitFromComposer);
  if (promptInput) {
    promptInput.addEventListener("input", autoGrow);
    // 输入铁律（军令 #16-R 第一步）：Enter 发送、Shift+Enter 换行。
    // 中文输入法组合态里的 Enter 只负责上屏选词，绝不能顺手把半截句子发出去；
    // 空内容按 Enter 也不发、不提示，焦点留在输入框。
    var composing = false;
    promptInput.addEventListener("compositionstart", function () {
      composing = true;
    });
    promptInput.addEventListener("compositionend", function () {
      composing = false;
    });
    promptInput.addEventListener("keydown", function (event) {
      if (event.key !== "Enter") return;
      if (event.isComposing || composing || event.keyCode === 229) return;
      if (event.shiftKey) return;
      event.preventDefault();
      submitFromComposer();
    });
  }

  if (copilotAsk) copilotAsk.addEventListener("click", askRefine);
  if (copilotApply) copilotApply.addEventListener("click", applyRefinePatch);
})();
