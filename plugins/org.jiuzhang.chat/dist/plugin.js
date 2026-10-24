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
 * 渲染安全：模型与插件返回的文本一律 textContent 落 DOM，只有本地 KaTeX
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
  var MAX_HISTORY_ITEMS = 8;

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
  var cardSeq = 0;

  // 底座状态快照（由宿主 workspace.state 供给）：当前舞台、工作模式插件、
  // 面板参数与模型 Provider。插件只读它，不自己去猜。
  var workspace = { current_task: "", stage: "", plugin: null, ui: null, provider: null };
  var transcript = [];
  var editorContext = { id: "", question: null, at: 0 };
  var pendingPatch = null;
  var mounted = false;

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
    var katex = window.katex;
    if (!katex || typeof katex.renderToString !== "function" || source.indexOf("$") === -1) {
      el.textContent = source;
      return;
    }
    var pattern = /(\$\$[\s\S]*?\$\$|\$[^$\n]*?\$)/g;
    var last = 0;
    var match;
    while ((match = pattern.exec(source)) !== null) {
      if (match.index > last) {
        el.appendChild(document.createTextNode(source.slice(last, match.index)));
      }
      var token = match[0];
      var display = token.slice(0, 2) === "$$";
      var node = document.createElement(display ? "div" : "span");
      node.className = display ? "jzochat-math-block" : "jzochat-math";
      try {
        node.innerHTML = katex.renderToString(display ? token.slice(2, -2) : token.slice(1, -1), {
          displayMode: display,
          throwOnError: false,
          trust: false,
          strict: "ignore"
        });
        el.appendChild(node);
      } catch (error) {
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

  // ---------- 富卡片 ----------
  var TYPE_LABELS = {
    single_choice: "单选", multiple_choice: "多选", fill_blank: "填空",
    solution: "解答", proof: "证明", unknown: "待定"
  };
  var DIFFICULTY_LABELS = { L1: "基础", L2: "中档", L3: "难", L4: "压轴" };
  var DIFFICULTY_LEGACY = { basic: "L1", medium: "L2", hard: "L3", novel: "L4" };
  var KIND_LABELS = { renderer: "渲染", importer: "导入", exporter: "导出", tool: "工具" };

  function normalizeQuestionCard(raw) {
    if (!raw || typeof raw !== "object") return null;
    var stem = clampText(raw.stem, 4000);
    if (!stem) return null;
    var type = TYPE_LABELS[raw.type] ? raw.type : "unknown";
    var difficultyRaw = DIFFICULTY_LEGACY[raw.difficulty] || raw.difficulty;
    var difficulty = DIFFICULTY_LABELS[difficultyRaw] ? difficultyRaw : "L1";
    var options = [];
    (Array.isArray(raw.options) ? raw.options : []).slice(0, 10).forEach(function (option) {
      if (!option || typeof option !== "object") return;
      var key = clampText(option.key, 8);
      var content = clampText(option.content, 1000);
      if (key || content) options.push({ key: key, content: content });
    });
    var tags = [];
    (Array.isArray(raw.tags) ? raw.tags : []).slice(0, 8).forEach(function (tag) {
      var text = clampText(tag, 24);
      if (text) tags.push(text);
    });
    return {
      id: clampText(raw.id, 80),
      questionNo: raw.question_no > 0 ? raw.question_no : 0,
      type: type,
      typeLabel: clampText(raw.type_label, 16) || TYPE_LABELS[type],
      difficulty: difficulty,
      difficultyLabel: clampText(raw.difficulty_label, 16) || DIFFICULTY_LABELS[difficulty],
      stem: stem,
      options: options,
      answer: clampText(raw.answer, 1000),
      solution: clampText(raw.solution, 4000),
      tags: tags
    };
  }

  function isKnownCard(block) {
    if (!block || typeof block !== "object") return false;
    if (block.type === "question_card") {
      return Array.isArray(block.questions) && block.questions.some(function (item) {
        return normalizeQuestionCard(item) !== null;
      });
    }
    if (block.type === "install_card") {
      return Boolean(block.plugin && typeof block.plugin === "object" && block.plugin.name);
    }
    if (block.type === "confirm_card") {
      return Array.isArray(block.actions) && block.actions.length > 0;
    }
    return false;
  }

  // 摘出 ```ui_json / ```json 围栏里的卡片；不是卡片的 json 原样留给动作解析。
  function splitUiBlocks(content) {
    var text = String(content == null ? "" : content);
    var cards = [];
    var pattern = /```(ui_json|json)[ \t]*\r?\n([\s\S]*?)```/g;
    text = text.replace(pattern, function (whole, language, body) {
      var parsed;
      try {
        parsed = JSON.parse(body.trim());
      } catch (error) {
        return language === "ui_json" ? "" : whole;
      }
      if (!isKnownCard(parsed)) return language === "ui_json" ? "" : whole;
      if (parsed.type === "question_card") {
        parsed.questions.forEach(function (item) {
          var card = normalizeQuestionCard(item);
          if (card) cards.push({ type: "question", data: card });
        });
      } else if (parsed.type === "install_card") {
        cards.push({ type: "install", data: parsed });
      } else if (parsed.type === "confirm_card") {
        cards.push({ type: "confirm", data: parsed });
      }
      return "";
    });
    return { text: text.trim(), cards: cards.slice(0, 3) };
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function buildQuestionCard(card) {
    var article = el("article", "jzochat-card jzochat-question-card");
    article.setAttribute("data-type", card.type);
    article.setAttribute("data-difficulty", card.difficulty);

    var head = el("header", "jzochat-card-head");
    if (card.questionNo) head.appendChild(el("span", "jzochat-tag", "第 " + card.questionNo + " 题"));
    head.appendChild(el("span", "jzochat-tag jzochat-tag-type", card.typeLabel));
    head.appendChild(el("span", "jzochat-tag jzochat-tag-diff", card.difficultyLabel));
    article.appendChild(head);

    var stem = el("div", "jzochat-card-stem");
    renderMathInto(stem, card.stem);
    article.appendChild(stem);

    if (card.options.length) {
      var options = el("div", "jzochat-card-options");
      card.options.forEach(function (option) {
        var row = el("div", "jzochat-card-option");
        row.appendChild(el("span", "jzochat-option-key", option.key || "·"));
        var body = el("span");
        renderMathInto(body, option.content);
        row.appendChild(body);
        options.appendChild(row);
      });
      article.appendChild(options);
    }
    if (card.tags.length) {
      var tags = el("div", "jzochat-card-head");
      card.tags.forEach(function (text) { tags.appendChild(el("span", "jzochat-tag", text)); });
      article.appendChild(tags);
    }

    var detailId = "jzochatDetail" + (++cardSeq);
    var detail = el("div", "jzochat-card-detail");
    detail.id = detailId;
    detail.hidden = true;
    if (card.answer) {
      var answer = el("p");
      answer.appendChild(el("strong", null, "答案："));
      var answerBody = el("span");
      renderMathInto(answerBody, card.answer);
      answer.appendChild(answerBody);
      detail.appendChild(answer);
    }
    if (card.solution) {
      var solution = el("p");
      solution.appendChild(el("strong", null, "解析："));
      var solutionBody = el("span");
      renderMathInto(solutionBody, card.solution);
      solution.appendChild(solutionBody);
      detail.appendChild(solution);
    }

    var foot = el("footer", "jzochat-card-foot");
    var toggle = el("button", "jzochat-btn", "查看解析");
    toggle.type = "button";
    var hasDetail = Boolean(card.answer || card.solution);
    if (!hasDetail) {
      toggle.disabled = true;
      toggle.title = "本题暂无答案与解析";
    } else {
      toggle.setAttribute("aria-expanded", "false");
      toggle.setAttribute("aria-controls", detailId);
      toggle.addEventListener("click", function () {
        detail.hidden = !detail.hidden;
        toggle.setAttribute("aria-expanded", String(!detail.hidden));
        toggle.textContent = detail.hidden ? "查看解析" : "收起解析";
      });
    }
    foot.appendChild(toggle);
    if (card.id) {
      var jump = el("button", "jzochat-btn", "去编辑这道题");
      jump.type = "button";
      jump.addEventListener("click", function () {
        runJump({ type: "open_editor", label: "去编辑", question_id: card.id });
        jump.disabled = true;
        jump.textContent = "已交给底座";
      });
      foot.appendChild(jump);
    }
    article.appendChild(foot);
    article.appendChild(detail);
    return article;
  }

  function safeHttpUrl(value) {
    try {
      var parsed = new URL(String(value || ""));
      return parsed.protocol === "http:" || parsed.protocol === "https:" ? parsed.href : "";
    } catch (error) {
      return "";
    }
  }

  function hostOf(url) {
    try {
      return new URL(String(url)).host;
    } catch (error) {
      return "未知来源";
    }
  }

  function buildInstallCard(block) {
    var plugin = block.plugin || {};
    var name = clampText(plugin.name, 64);
    var version = clampText(plugin.version, 32);
    var zipUrl = safeHttpUrl(plugin.zip_url);
    if (!name || !zipUrl) return null;

    var article = el("article", "jzochat-card jzochat-install-card");
    article.setAttribute("data-state", "suggested");
    var head = el("header", "jzochat-card-head");
    head.appendChild(el("span", "jzochat-tag jzochat-tag-type", "安装建议"));
    head.appendChild(el("span", "jzochat-tag", KIND_LABELS[plugin.kind] || "插件"));
    article.appendChild(head);
    article.appendChild(el("h4", "jzochat-card-title", name + (version ? " v" + version : "")));
    if (plugin.description) {
      article.appendChild(el("p", "jzochat-card-desc", clampText(plugin.description, 200)));
    }
    if (block.reason) article.appendChild(el("p", "jzochat-card-reason", "推荐理由：" + clampText(block.reason, 200)));
    article.appendChild(el("p", "jzochat-card-note",
      "来源 " + hostOf(zipUrl) + " · 只有你点【确认安装】，底座才会下载这一个 zip 并走完整校验。"));

    var status = el("p", "jzochat-card-status", "等待你的确认。");
    status.setAttribute("role", "status");
    article.appendChild(status);

    var mirrors = (Array.isArray(plugin.mirrors) ? plugin.mirrors : [])
      .map(function (item) { return clampText(item, 800); }).filter(Boolean);

    var foot = el("footer", "jzochat-card-foot");
    var installBtn = el("button", "jzochat-btn jzochat-btn-primary", "确认安装");
    installBtn.type = "button";
    var cancelBtn = el("button", "jzochat-btn", "暂不安装");
    cancelBtn.type = "button";
    cancelBtn.addEventListener("click", function () {
      article.setAttribute("data-state", "cancelled");
      installBtn.disabled = true;
      cancelBtn.disabled = true;
      status.textContent = "已取消，未下载任何内容。";
    });
    installBtn.addEventListener("click", function () {
      installBtn.disabled = true;
      installBtn.setAttribute("aria-busy", "true");
      installBtn.textContent = "安装中…";
      status.textContent = "正在下载并校验 " + name + " …";
      requestInstall({ url: zipUrl, mirrors: mirrors, name: name }, status, installBtn, article);
    });
    foot.appendChild(installBtn);
    foot.appendChild(cancelBtn);
    article.appendChild(foot);
    return article;
  }

  /** 安装只发一次 Host API 请求：写令牌、下载与校验全在底座侧，插件看不到令牌。 */
  function requestInstall(target, statusEl, buttonEl, cardEl, replace) {
    return hostCall("plugin.install_url", {
      url: target.url,
      mirrors: target.mirrors,
      replace: Boolean(replace)
    }, AGENT_TIMEOUT_MS).then(function (result) {
      var plugin = (result && result.plugin) || {};
      cardEl.setAttribute("data-state", "installed");
      buttonEl.removeAttribute("aria-busy");
      buttonEl.disabled = true;
      buttonEl.textContent = "已安装";
      statusEl.textContent = "安装成功：" + (plugin.name || target.name) +
        (result && result.source_host ? "（来源 " + result.source_host + "）" : "");
      addBubble("sys", "插件已安装：" + (plugin.name || plugin.id || target.name) + " v" + (plugin.version || "?"));
      dock("AI 助手经宿主安装了插件「" + (plugin.name || target.name) + "」");
      refreshWorkspace();
      return true;
    }, function (error) {
      var message = error && error.message ? error.message : String(error);
      if (error && error.code === "PLUGIN_EXISTS" && !replace) {
        statusEl.textContent = message + " 覆盖安装会先删除旧目录，请再点一次【覆盖安装】。";
        buttonEl.removeAttribute("aria-busy");
        buttonEl.disabled = false;
        buttonEl.textContent = "覆盖安装";
        buttonEl.addEventListener("click", function () {
          buttonEl.disabled = true;
          buttonEl.textContent = "安装中…";
          requestInstall(target, statusEl, buttonEl, cardEl, true);
        }, { once: true });
        return false;
      }
      cardEl.setAttribute("data-state", "failed");
      buttonEl.removeAttribute("aria-busy");
      buttonEl.disabled = false;
      buttonEl.textContent = "重试安装";
      statusEl.textContent = "安装失败：" + message;
      return false;
    });
  }

  function buildConfirmCard(block) {
    var actions = (Array.isArray(block.actions) ? block.actions : []).slice(0, 4);
    if (!actions.length) return null;
    var article = el("article", "jzochat-card jzochat-confirm-card");
    var head = el("header", "jzochat-card-head");
    head.appendChild(el("span", "jzochat-tag jzochat-tag-type", "操作确认"));
    article.appendChild(head);
    article.appendChild(el("h4", "jzochat-card-title", clampText(block.title, 60) || "操作确认"));
    if (block.description) article.appendChild(el("p", "jzochat-card-desc", clampText(block.description, 400)));
    var foot = el("footer", "jzochat-card-foot");
    actions.forEach(function (action, index) {
      var label = clampText(action && action.label, 20);
      var command = clampText(action && action.command, 200);
      if (!label || !command) return;
      var button = el("button", "jzochat-btn" + (index === 0 ? " jzochat-btn-primary" : ""), label);
      button.type = "button";
      button.addEventListener("click", function () {
        if (article.getAttribute("data-state") === "sent") return;
        article.setAttribute("data-state", "sent");
        foot.querySelectorAll("button").forEach(function (item) { item.disabled = true; });
        // 卡片按钮是「人点的」：把指令作为新一轮人类指令交回对话，而不是 AI 自作主张。
        sendPrompt(command, { origin: "confirm_card" });
      });
      foot.appendChild(button);
    });
    article.appendChild(foot);
    return article;
  }

  function buildCard(raw) {
    if (!raw || typeof raw !== "object") return null;
    if (raw.type === "question") return buildQuestionCard(raw.data);
    if (raw.type === "install") return buildInstallCard(raw.data);
    if (raw.type === "confirm") return buildConfirmCard(raw.data);
    return null;
  }

  /**
   * 智能跳转按钮（军令 #15 任务 3）：AI 只说出「去哪、带什么参数」，
   * 真正打开插件与注入搜索词由底座执行；本插件不写 URL、不碰别的区。
   */
  function buildActionButton(action) {
    var button = el("button", "jzochat-action", action.label || "前往");
    button.type = "button";
    button.addEventListener("click", function () {
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      runJump(action, button);
    });
    return button;
  }

  function runJump(action, buttonEl) {
    var method = action.type === "open_editor" ? "stage.open_editor" : "stage.open_bank";
    return hostCall(method, {
      query: clampText(action.query, 100),
      plugin_id: clampText(action.plugin_id, 100),
      question_id: clampText(action.question_id, 80)
    }).then(function () {
      if (buttonEl) {
        buttonEl.removeAttribute("aria-busy");
        buttonEl.textContent = action.label || "已跳转";
      }
      addBubble("sys", "底座已执行跳转：" + (action.label || action.type) +
        (action.query ? "（关键词「" + action.query + "」）" : "") + "。");
    }, function (error) {
      if (buttonEl) {
        buttonEl.removeAttribute("aria-busy");
        buttonEl.disabled = false;
        buttonEl.textContent = action.label || "前往";
      }
      addBubble("sys", "跳转没做成：" + error.message, { tone: "warn" });
    });
  }

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
    if (typeof parsed === "string") return parsed;
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
    var source = describeSource(envelope, pluginCalls);
    if (!content) {
      return { text: "模型没有返回内容，请检查 Provider 配置。", tone: "warn", source: source, cards: [], actions: [] };
    }
    var split = splitUiBlocks(content);
    var body = stripFences(split.text);
    var cards = split.cards;

    if (pluginCalls.length) {
      return {
        text: body, source: source, cards: cards,
        pluginCalls: pluginCalls, route: envelope && envelope.route, actions: actions
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

  function sendPrompt(prompt, options) {
    options = options || {};
    var text = String(prompt == null ? "" : prompt).trim();
    if (!text) return Promise.resolve();
    addBubble("user", text, originNote(options) ? { source: originNote(options) } : undefined);
    // 历史在推进去之前取：只带「本轮之前」的轮次，本轮指令由后端当 user 消息。
    var history = transcript.slice(-TRANSCRIPT_SEND);
    pushTurn("user", text);
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
      if (res.control && res.control.action === "update_params") return applyParamsByHost(res.control.params);
      return null;
    }, function (error) {
      if (typing) typing.remove();
      addBubble("bot", "指令执行失败：" + error.message, { tone: "warn", source: "底座未响应或 Provider 不可用" });
      pushTurn("assistant", "指令执行失败：" + error.message);
    }).then(function () {
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
    if (copilotAsk) copilotAsk.disabled = !editorContext.question;
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
    }).then(function () {
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
      mounted = true;
      root.hidden = false;
      if (promptInput) promptInput.focus();
      bootstrap();
      restoreTranscript();
      return respond(event.source, message.id, true, { ready: true, plugin_id: PLUGIN_ID });
    }
    if (message.method === "plugin.deactivate") {
      // 交还右栏主权前先把对话记忆存回宿主，切回来才接得上
      saveTranscript();
      mounted = false;
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

  function focusComposer() {
    if (!promptInput) return;
    promptInput.focus();
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
