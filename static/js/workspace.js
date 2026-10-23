/**
 * 工作台：三栏「智能体」空壳原型 —— 对话流驱动。
 *
 * 设计取向（先见形，后调逻辑）：中栏是对话流主区，兼当前任务舞台；
 * 发送指令 → 用户气泡 → 调 /api/agent/chat → 助手气泡回显识别到的意图。
 * 左栏只放「自由对话」与动态渲染的已装插件；索引、手动安装与底座信息
 * 收纳到栏底齿轮进入的 /settings，不在工作台堆低频控件。
 *
 * 安全：所有气泡文本（含模型返回、插件反馈）一律用 textContent 落 DOM，
 * 不走 innerHTML，杜绝 XSS（AGENTS §5：不可信输入进 DOM 前必须净化）。
 */
(function () {
  "use strict";

  // --- State ---
  var providerList = [];
  var installedPlugins = [];
  var writeToken = null;
  var currentTask = "";
  var activePlugin = null;
  // 右侧面板状态：values 是当前参数，revisions 记录人类
  // 手改次数。发请求时拍快照，AI 回来要改参数时只改「人没同时动过」的字段——
  // 人类的主动点击永远覆盖 AI 的自动设定。
  var uiState = { pluginId: null, values: {}, revisions: {} };
  var uiPanelControls = [];
  // 对话轮次记忆：注入下一轮请求，让模型延续前文而非孤立理解（10.24 军令 P0-2）。
  var transcript = [];
  var TRANSCRIPT_MAX = 24;   // 内存里最多留多少轮
  var TRANSCRIPT_SEND = 8;   // 每轮最多回传多少轮给模型

  // --- DOM refs ---
  var sidebarToggle = document.getElementById("wsToggleSidebar");
  var thread = document.getElementById("wsThread");
  var chatForm = document.getElementById("wsChatForm");
  var promptInput = document.getElementById("wsPrompt");
  var sendBtn = document.getElementById("wsSendBtn");
  var stageTitle = document.getElementById("wsStageTitle");
  var ctxTask = document.getElementById("ctxTask");
  var ctxModel = document.getElementById("ctxModel");
  var ctxHistory = document.getElementById("ctxHistory");
  var chatEntry = document.getElementById("wsChatEntry");
  var pluginListEl = document.getElementById("wsPluginList");
  var pluginCountEl = document.getElementById("wsPluginCount");
  var pluginPanel = document.getElementById("wsPluginPanel");
  var pluginPanelTitle = document.getElementById("wsPluginPanelTitle");
  var pluginPanelDesc = document.getElementById("wsPluginPanelDesc");
  var pluginControlsEl = document.getElementById("wsPluginControls");
  var pluginPanelHint = document.getElementById("wsPluginPanelHint");
  var uiStateSummary = document.getElementById("wsUiStateSummary");
  var dockToggle = document.getElementById("wsToggleDock");
  var dockClearBtn = document.getElementById("wsDockClear");
  var dockLog = document.getElementById("wsDockLog");
  var dockTabs = document.getElementById("wsDockTabs");

  // 右侧 AI 副驾：感知录题工作台当前题，改写一个字段后回填到表单。
  var cpCtx = document.getElementById("cpCtx");
  var cpField = document.getElementById("cpField");
  var cpInput = document.getElementById("cpInput");
  var cpAsk = document.getElementById("cpAsk");
  var cpBackfill = document.getElementById("cpBackfill");
  var cpOut = document.getElementById("cpOut");
  var editorContext = { id: "", question: null, at: 0 };
  var pendingPatch = null;

  // ============ 对话流：气泡工厂 ============
  var CARD_SEQ = 0;

  function clampText(value, limit) {
    return String(value == null ? "" : value).trim().slice(0, limit);
  }

  // Markdown + LaTeX 的最小渲染：普通文本走 textContent，公式交给本地 KaTeX。
  // 只把 KaTeX 自己生成的 HTML 写进节点（trust:false），不执行任何远端资源。
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
      var body = display ? token.slice(2, -2) : token.slice(1, -1);
      var node = document.createElement(display ? "div" : "span");
      node.className = display ? "ws-math-block" : "ws-math";
      try {
        node.innerHTML = katex.renderToString(body, {
          displayMode: display,
          throwOnError: false,
          trust: false,
          strict: "ignore",
        });
        el.appendChild(node);
      } catch (error) {
        el.appendChild(document.createTextNode(token));
      }
      last = pattern.lastIndex;
    }
    if (last < source.length) {
      el.appendChild(document.createTextNode(source.slice(last)));
    }
  }

  function addBubble(role, text, opts) {
    if (!thread) return null;
    opts = opts || {};
    var wrap = document.createElement("div");
    wrap.className = "ws-msg ws-msg-" + role;

    var hasText = !!(String(text == null ? "" : text).trim());
    if (hasText || opts.pluginCalls || opts.source) {
      var bubble = document.createElement("div");
      bubble.className = "ws-bubble";
      if (opts.tone) bubble.setAttribute("data-tone", opts.tone);
      if (hasText) {
        if (opts.richText && role === "bot") {
          renderMathInto(bubble, text);
        } else {
          bubble.textContent = text; // 不可信内容只当纯文本，天然免 XSS
        }
      }

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
    }

    (opts.cards || []).forEach(function (card) {
      var node = buildCard(card);
      if (node) wrap.appendChild(node);
    });

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

  // ============ 富卡片：ui_json 拦截与渲染 ============
  var CARD_TYPE_LABELS = {
    single_choice: "单选",
    multiple_choice: "多选",
    fill_blank: "填空",
    solution: "解答",
    proof: "证明",
    unknown: "待定",
  };
  var CARD_DIFFICULTY_LABELS = {
    L1: "基础",
    L2: "中档",
    L3: "难",
    L4: "压轴",
  };
  // 契约 1.0 的题卡仍可能带旧难度值，渲染前归一到 L 码（novel 已废弃，并入 L4）
  var CARD_DIFFICULTY_LEGACY = { basic: "L1", medium: "L2", hard: "L3", novel: "L4" };

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

  function normalizeQuestionCard(raw) {
    if (!raw || typeof raw !== "object") return null;
    var stem = clampText(raw.stem, 4000);
    if (!stem) return null;
    var type = CARD_TYPE_LABELS[raw.type] ? raw.type : "unknown";
    var difficultyRaw = CARD_DIFFICULTY_LEGACY[raw.difficulty] || raw.difficulty;
    var difficulty = CARD_DIFFICULTY_LABELS[difficultyRaw] ? difficultyRaw : "L1";
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
      typeLabel: clampText(raw.type_label, 16) || CARD_TYPE_LABELS[type],
      difficulty: difficulty,
      difficultyLabel: clampText(raw.difficulty_label, 16) || CARD_DIFFICULTY_LABELS[difficulty],
      stem: stem,
      options: options,
      answer: clampText(raw.answer, 1000),
      solution: clampText(raw.solution, 4000),
      tags: tags,
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

  // 拦截 ```ui_json 围栏（也容忍模型把卡片塞进 ```json）。不是卡片的 json
  // 围栏原样保留，继续走动作 JSON 解析，不误伤既有控制协议。
  function splitUiBlocks(content) {
    var text = String(content == null ? "" : content);
    var cards = [];
    var sawCard = false;
    var pattern = /```(ui_json|json)[ \t]*\r?\n([\s\S]*?)```/g;
    text = text.replace(pattern, function (whole, language, body) {
      var parsed;
      try {
        parsed = JSON.parse(body.trim());
      } catch (error) {
        return language === "ui_json" ? "" : whole;
      }
      if (!isKnownCard(parsed)) {
        return language === "ui_json" ? "" : whole;
      }
      sawCard = true;
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
    return { text: text.trim(), cards: cards.slice(0, 3), sawCard: sawCard };
  }

  function buildQuestionCard(card) {
    var article = document.createElement("article");
    article.className = "ws-card ws-question-card";
    article.setAttribute("data-type", card.type);
    article.setAttribute("data-difficulty", card.difficulty);

    var head = document.createElement("header");
    head.className = "ws-card-head";
    if (card.questionNo) {
      var number = document.createElement("span");
      number.className = "ws-card-no";
      number.textContent = "第 " + card.questionNo + " 题";
      head.appendChild(number);
    }
    var typeTag = document.createElement("span");
    typeTag.className = "ws-tag ws-tag-type";
    typeTag.textContent = card.typeLabel;
    head.appendChild(typeTag);
    var diffTag = document.createElement("span");
    diffTag.className = "ws-tag ws-tag-diff";
    diffTag.textContent = card.difficultyLabel;
    head.appendChild(diffTag);
    article.appendChild(head);

    var stem = document.createElement("div");
    stem.className = "ws-card-stem";
    renderMathInto(stem, card.stem);
    article.appendChild(stem);

    if (card.options.length) {
      var options = document.createElement("div");
      options.className = "ws-card-options";
      card.options.forEach(function (option) {
        var row = document.createElement("div");
        row.className = "ws-card-option";
        var key = document.createElement("span");
        key.className = "ws-option-key";
        key.textContent = option.key || "·";
        var body = document.createElement("span");
        body.className = "ws-option-body";
        renderMathInto(body, option.content);
        row.appendChild(key);
        row.appendChild(body);
        options.appendChild(row);
      });
      article.appendChild(options);
    }

    if (card.tags.length) {
      var tags = document.createElement("div");
      tags.className = "ws-card-tags";
      card.tags.forEach(function (text) {
        var tag = document.createElement("span");
        tag.className = "ws-tag ws-tag-topic";
        tag.textContent = text;
        tags.appendChild(tag);
      });
      article.appendChild(tags);
    }

    var detailId = "wsCardDetail" + (++CARD_SEQ);
    var detail = document.createElement("div");
    detail.className = "ws-card-detail";
    detail.id = detailId;
    detail.hidden = true;
    if (card.answer) {
      var answer = document.createElement("p");
      var answerLabel = document.createElement("strong");
      answerLabel.textContent = "答案：";
      answer.appendChild(answerLabel);
      var answerBody = document.createElement("span");
      renderMathInto(answerBody, card.answer);
      answer.appendChild(answerBody);
      detail.appendChild(answer);
    }
    if (card.solution) {
      var solution = document.createElement("p");
      var solutionLabel = document.createElement("strong");
      solutionLabel.textContent = "解析：";
      solution.appendChild(solutionLabel);
      var solutionBody = document.createElement("span");
      renderMathInto(solutionBody, card.solution);
      solution.appendChild(solutionBody);
      detail.appendChild(solution);
    }

    var foot = document.createElement("footer");
    foot.className = "ws-card-foot";
    var toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "ws-btn ws-btn-sm ws-card-toggle";
    toggle.textContent = "查看解析";
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-controls", detailId);
    var hasDetail = Boolean(card.answer || card.solution);
    if (!hasDetail) {
      toggle.disabled = true;
      toggle.title = "本题暂无答案与解析";
    } else {
      toggle.addEventListener("click", function () {
        detail.hidden = !detail.hidden;
        toggle.setAttribute("aria-expanded", String(!detail.hidden));
        toggle.textContent = detail.hidden ? "查看解析" : "收起解析";
      });
    }
    foot.appendChild(toggle);
    article.appendChild(foot);
    article.appendChild(detail);
    return article;
  }

  function buildInstallCard(block) {
    var plugin = block.plugin || {};
    var name = clampText(plugin.name, 64);
    var version = clampText(plugin.version, 32);
    var zipUrl = safeHttpUrl(plugin.zip_url);
    if (!name || !zipUrl) return null;

    var installed = installedPlugins.some(function (item) { return item.id === plugin.id; });
    var article = document.createElement("article");
    article.className = "ws-card ws-install-card";
    article.setAttribute("data-state", installed ? "installed" : "suggested");

    var head = document.createElement("header");
    head.className = "ws-card-head";
    var kicker = document.createElement("span");
    kicker.className = "ws-tag ws-install-kicker";
    kicker.textContent = "安装建议";
    head.appendChild(kicker);
    var kind = document.createElement("span");
    kind.className = "ws-tag ws-tag-topic";
    kind.textContent = KIND_LABELS[plugin.kind] || "插件";
    head.appendChild(kind);
    article.appendChild(head);

    var title = document.createElement("h4");
    title.className = "ws-card-title";
    title.textContent = name + (version ? " v" + version : "");
    article.appendChild(title);

    if (plugin.description) {
      var desc = document.createElement("p");
      desc.className = "ws-card-desc";
      desc.textContent = clampText(plugin.description, 200);
      article.appendChild(desc);
    }
    if (block.reason) {
      var reason = document.createElement("p");
      reason.className = "ws-card-reason";
      reason.textContent = "推荐理由：" + clampText(block.reason, 200);
      article.appendChild(reason);
    }

    var note = document.createElement("p");
    note.className = "ws-card-note";
    note.textContent = "来源 " + hostOf(zipUrl) + " · 只有你点【确认安装】，底座才会下载这一个 zip 并走完整校验。";
    article.appendChild(note);

    var status = document.createElement("p");
    status.className = "ws-card-status";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    article.appendChild(status);

    var foot = document.createElement("footer");
    foot.className = "ws-card-foot";
    var installBtn = document.createElement("button");
    installBtn.type = "button";
    installBtn.className = "ws-btn ws-btn-primary ws-btn-sm ws-install-confirm";
    installBtn.textContent = installed ? "已安装" : "确认安装";
    installBtn.disabled = installed;
    var cancelBtn = document.createElement("button");
    cancelBtn.type = "button";
    cancelBtn.className = "ws-btn ws-btn-sm";
    cancelBtn.textContent = "暂不安装";
    if (installed) {
      status.textContent = "本机已安装该插件，无需重复安装。";
      cancelBtn.hidden = true;
    } else {
      cancelBtn.addEventListener("click", function () {
        article.setAttribute("data-state", "cancelled");
        installBtn.disabled = true;
        cancelBtn.disabled = true;
        status.textContent = "已取消，未下载任何内容。";
      });
      installBtn.addEventListener("click", function () {
        installSuggestedPlugin(article, status, installBtn, {
          url: zipUrl,
          mirrors: (plugin.mirrors || []).map(function (item) { return clampText(item, 800); }).filter(Boolean),
          name: name,
        });
      });
    }
    foot.appendChild(installBtn);
    foot.appendChild(cancelBtn);
    article.appendChild(foot);
    return article;
  }

  function installSuggestedPlugin(cardEl, statusEl, buttonEl, target) {
    var replace = false;
    cardEl.setAttribute("data-state", "installing");
    buttonEl.disabled = true;
    buttonEl.setAttribute("aria-busy", "true");
    buttonEl.textContent = "安装中…";
    statusEl.textContent = "正在下载并校验 " + target.name + " …";

    function attempt(allowReplace) {
      return fetchWriteToken()
        .then(function (token) {
          return fetch("/api/plugins/install-url", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-JZO-Token": token },
            body: JSON.stringify({
              url: target.url,
              mirrors: target.mirrors,
              replace: allowReplace,
            }),
          });
        })
        .then(function (response) {
          return response.json().catch(function () { return null; }).then(function (body) {
            if (response.status === 409 && !allowReplace) {
              var question = readErrorDetail(response, body) + " 覆盖安装会先删除旧目录，继续吗？";
              if (window.confirm(question)) return attempt(true);
              return { cancelled: true };
            }
            if (!response.ok) throw new Error(readErrorDetail(response, body));
            return body || {};
          });
        })
        .finally(function () {
          writeToken = null;
        });
    }

    attempt(false)
      .then(function (result) {
        if (result && result.cancelled) {
          cardEl.setAttribute("data-state", "suggested");
          buttonEl.disabled = false;
          buttonEl.removeAttribute("aria-busy");
          buttonEl.textContent = "确认安装";
          statusEl.textContent = "已取消覆盖安装。";
          return null;
        }
        var plugin = (result && result.plugin) || {};
        cardEl.setAttribute("data-state", "installed");
        buttonEl.removeAttribute("aria-busy");
        buttonEl.textContent = "已安装";
        statusEl.textContent = "安装成功：" + (plugin.name || target.name) +
          (result && result.source_host ? "（来源 " + result.source_host + "）" : "");
        addBubble("sys", "插件已安装：" + (plugin.name || plugin.id || target.name) +
          " v" + (plugin.version || "?"));
        logHistory("安装插件 " + (plugin.name || target.name));
        return loadPlugins().catch(function () { return null; });
      })
      .catch(function (error) {
        cardEl.setAttribute("data-state", "failed");
        buttonEl.disabled = false;
        buttonEl.removeAttribute("aria-busy");
        buttonEl.textContent = "重试安装";
        statusEl.textContent = "安装失败：" + error.message;
      });
  }

  function buildConfirmCard(block) {
    var title = clampText(block.title, 60) || "操作确认";
    var actions = (Array.isArray(block.actions) ? block.actions : []).slice(0, 4);
    if (!actions.length) return null;
    var article = document.createElement("article");
    article.className = "ws-card ws-confirm-card";

    var head = document.createElement("header");
    head.className = "ws-card-head";
    var kicker = document.createElement("span");
    kicker.className = "ws-tag ws-confirm-kicker";
    kicker.textContent = "操作确认";
    head.appendChild(kicker);
    article.appendChild(head);

    var heading = document.createElement("h4");
    heading.className = "ws-card-title";
    heading.textContent = title;
    article.appendChild(heading);

    if (block.description) {
      var desc = document.createElement("p");
      desc.className = "ws-card-desc";
      desc.textContent = clampText(block.description, 400);
      article.appendChild(desc);
    }

    var foot = document.createElement("footer");
    foot.className = "ws-card-foot";
    actions.forEach(function (action, index) {
      var label = clampText(action && action.label, 20);
      var command = clampText(action && action.command, 200);
      if (!label || !command) return;
      var button = document.createElement("button");
      button.type = "button";
      button.className = "ws-btn ws-btn-sm" + (index === 0 ? " ws-btn-primary" : "");
      button.textContent = label;
      button.addEventListener("click", function () {
        if (article.getAttribute("data-state") === "sent") return;
        article.setAttribute("data-state", "sent");
        foot.querySelectorAll("button").forEach(function (item) { item.disabled = true; });
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
    var items = document.querySelectorAll(".ws-plugin-item");
    for (var i = 0; i < items.length; i += 1) {
      items[i].setAttribute("aria-current", String(items[i] === activeEl));
    }
  }

  function enterChatMode() {
    activePlugin = null;
    markActiveEntry(chatEntry);
    setStage("自由对话");
    clearPluginPanel();
    if (window.JzoStage && typeof window.JzoStage.activate === "function") {
      window.JzoStage.activate("chat");
    }
    addBubble("sys", "已进入「自由对话」模式。");
    logHistory("进入自由对话");
    if (promptInput) promptInput.focus();
  }

  function enterPluginMode(plugin, item) {
    activePlugin = plugin;
    markActiveEntry(item);
    var name = plugin.name || plugin.id || "插件";
    setStage(name);
    initUiState(plugin);
    renderPluginPanel(plugin);
    // 中栏是通用舞台：只有清单里声明了 stage（slots 带 stage.center）的插件才开画布页。
    // 没声明的插件照旧只切工作模式 + 右栏面板，不给它一块它没要过的地方。
    if (plugin.stage && window.JzoStage && typeof window.JzoStage.openPlugin === "function") {
      window.JzoStage.openPlugin(plugin);
    }
    addBubble("sys", "现在处于插件「" + name + "」的工作模式下。" +
      (plugin.description ? " " + plugin.description : ""));
    var capabilities = (plugin.capabilities || []).slice(0, 4).join("、");
    var actions = uiPanelControls.filter(function (control) {
      return control.type === "button";
    }).slice(0, 3).map(function (control) { return "【" + control.label + "】"; });
    var intro = "「" + name + "」支持：" + (capabilities || "见插件说明") + "。";
    if (actions.length) {
      intro += "右侧「" + ((plugin.ui && plugin.ui.title) || (name + "快捷操作")) +
        "」面板可以直接点 " + actions.join(" ") + "，点一下就等于在对话区发送对应指令；" +
        "年级、难度等下拉选择会实时同步给我。你也可以直接说话，比如「随机出一道高一基础题」。";
    } else {
      intro += "你也可以直接说话，我会优先调用这个插件的能力。";
    }
    addBubble("bot", intro);
    logHistory("进入插件「" + name + "」");
    if (promptInput) promptInput.focus();
  }

  if (chatEntry) chatEntry.addEventListener("click", enterChatMode);

  /**
   * 启动行为（军令 #11 阶段三）：老师选了「打开软件默认进入某插件」，这里执行它。
   * 失效判定不在前端重做一遍——后端 /api/startup 已经把卸载/停用的目标回落成
   * chat 并给了 fallback_reason，前端只负责照办与如实播报（底栏 + 对话区都记一笔）。
   * 读不到配置就停在默认欢迎页，任何异常都不许挡住启动。
   */
  function applyStartupBehavior(plugins) {
    return fetch("/api/startup", { cache: "no-store" })
      .then(function (response) { return response.ok ? response.json() : null; })
      .then(function (body) {
        if (!body) return;
        if (body.fallback_reason) {
          addBubble("sys", String(body.fallback_reason), { tone: "warn" });
          logHistory("启动行为回退：" + body.fallback_reason);
        }
        var effective = String(body.effective || "chat");
        if (effective.indexOf("plugin:") !== 0) return;
        var wantedId = effective.slice("plugin:".length);
        var target = null;
        (plugins || []).forEach(function (plugin) {
          if (!target && plugin.id === wantedId && plugin.enabled !== false) target = plugin;
        });
        if (!target) {
          logHistory("启动插件不在场，停在自由对话：" + wantedId);
          return;
        }
        var item = null;
        var buttons = pluginListEl ? pluginListEl.querySelectorAll(".ws-plugin-item") : [];
        for (var i = 0; i < buttons.length; i += 1) {
          if (buttons[i].getAttribute("data-plugin-id") === wantedId) { item = buttons[i]; break; }
        }
        enterPluginMode(target, item);
      })
      .catch(function () { /* 配置读不到就当没配过，默认欢迎页照旧 */ });
  }

  // ============ 右侧插件面板（双向操控） ============
  // 控件由 plugin.json 的 ui 字段（或底座按能力生成的默认面板）下发。
  // 人类改下拉 → revisions[key] 加一；AI 改参数时用发送时的快照比对，
  // 只要人类在请求飞行期间动过同一字段，AI 的设定就让位。
  function panelControls(plugin) {
    var ui = plugin && plugin.ui;
    return ui && Array.isArray(ui.controls) ? ui.controls : [];
  }

  function initUiState(plugin) {
    var controls = panelControls(plugin);
    var values = {};
    controls.forEach(function (control) {
      if (control.type !== "select") return;
      var options = Array.isArray(control.options) ? control.options : [];
      var fallback = options.length ? options[0].value : "";
      values[control.key] = control.default || fallback;
    });
    uiPanelControls = controls;
    uiState = { pluginId: plugin ? plugin.id : null, values: values, revisions: {} };
    updateUiStateSummary();
  }

  function syncUiState(plugin) {
    var controls = panelControls(plugin);
    var next = {};
    controls.forEach(function (control) {
      if (control.type !== "select") return;
      var options = Array.isArray(control.options) ? control.options : [];
      var fallback = options.length ? options[0].value : "";
      var previous = uiState.values[control.key];
      var valid = options.some(function (option) { return option.value === previous; });
      next[control.key] = valid ? previous : (control.default || fallback);
    });
    uiPanelControls = controls;
    uiState.pluginId = plugin ? plugin.id : null;
    uiState.values = next;
  }

  function clearPluginPanel() {
    uiPanelControls = [];
    uiState = { pluginId: null, values: {}, revisions: {} };
    if (pluginPanel) pluginPanel.hidden = true;
    if (pluginControlsEl) pluginControlsEl.textContent = "";
    if (uiStateSummary) uiStateSummary.textContent = "";
  }

  function renderPluginPanel(plugin) {
    if (!pluginPanel || !pluginControlsEl) return;
    var controls = panelControls(plugin);
    if (!controls.length) {
      clearPluginPanel();
      return;
    }
    var ui = plugin.ui || {};
    if (pluginPanelTitle) pluginPanelTitle.textContent = ui.title || ((plugin.name || "插件") + "快捷操作");
    if (pluginPanelDesc) {
      pluginPanelDesc.textContent = plugin.description || "该插件未提供说明。";
    }
    if (pluginPanelHint) {
      pluginPanelHint.textContent = ui.hint || "点按钮等于发送对应指令；你手动改过的参数优先于 AI 的自动设定。";
    }
    pluginControlsEl.textContent = "";

    controls.forEach(function (control) {
      if (control.type === "select") {
        var field = document.createElement("label");
        field.className = "ws-ui-field";
        var label = document.createElement("span");
        label.className = "ws-ui-field-label";
        label.textContent = control.label || control.key;
        var select = document.createElement("select");
        select.className = "ws-ui-select";
        select.setAttribute("data-ui-key", control.key);
        (control.options || []).forEach(function (option) {
          var item = document.createElement("option");
          item.value = option.value;
          item.textContent = option.label || option.value;
          if (uiState.values[control.key] === option.value) item.selected = true;
          select.appendChild(item);
        });
        select.addEventListener("change", function () {
          uiState.values[control.key] = select.value;
          uiState.revisions[control.key] = (uiState.revisions[control.key] || 0) + 1;
          updateUiStateSummary();
          logHistory("面板调整：" + (control.label || control.key) + " = " + select.value);
          publishUiParams("human", control.key);
        });
        field.appendChild(label);
        field.appendChild(select);
        pluginControlsEl.appendChild(field);
        return;
      }
      if (control.type === "button") {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "ws-btn ws-btn-sm ws-ui-action";
        btn.setAttribute("data-ui-button", control.id);
        btn.textContent = control.label || "执行";
        btn.addEventListener("click", function () {
          sendPrompt(expandCommand(control.command), {
            origin: "ui_button",
            buttonId: control.id,
            label: control.label || "面板按钮",
          });
        });
        pluginControlsEl.appendChild(btn);
      }
    });

    pluginPanel.hidden = false;
    updateUiStateSummary();
  }

  function updateUiStateSummary() {
    if (!uiStateSummary) return;
    var parts = [];
    uiPanelControls.forEach(function (control) {
      if (control.type !== "select") return;
      var value = uiState.values[control.key];
      if (value == null || value === "") return;
      var edited = uiState.revisions[control.key] ? "（你已改）" : "";
      parts.push((control.label || control.key) + "：" + value + edited);
    });
    uiStateSummary.textContent = parts.length
      ? "当前参数 " + parts.join(" · ")
      : "面板操作会实时同步给 AI。";
  }

  function currentUiValues() {
    var values = {};
    Object.keys(uiState.values).forEach(function (key) {
      values[key] = uiState.values[key];
    });
    return values;
  }

  function compactControls() {
    return uiPanelControls.map(function (control) {
      if (control.type === "select") {
        return {
          id: control.id,
          type: "select",
          key: control.key,
          label: control.label,
          options: (control.options || []).map(function (option) {
            return { value: option.value, label: option.label };
          }),
          default: control.default,
        };
      }
      return { id: control.id, type: "button", label: control.label };
    });
  }

  function expandCommand(template) {
    return String(template || "").replace(/\{([a-z][a-z0-9_]{0,15})\}/g, function (whole, key) {
      var value = uiState.values[key];
      return value == null ? whole : String(value);
    });
  }

  function findUiControl(id, type) {
    for (var i = 0; i < uiPanelControls.length; i += 1) {
      var control = uiPanelControls[i];
      if (control.id === id && control.type === type) return control;
    }
    return null;
  }

  function snapshotRevisions() {
    var snapshot = {};
    Object.keys(uiState.revisions).forEach(function (key) {
      snapshot[key] = uiState.revisions[key];
    });
    return snapshot;
  }

  // 应用 AI 的 update_params：只改「人没在本轮同时动过」且值合法的字段。
  function applyUiParams(params, snapshot) {
    var applied = [];
    var skipped = [];
    if (!params || typeof params !== "object") return { applied: applied, skipped: skipped };
    Object.keys(params).forEach(function (key) {
      var control = findUiControl(key, "select");
      if (!control) return;
      var incoming = params[key];
      var valid = (control.options || []).some(function (option) { return option.value === incoming; });
      if (!valid) {
        skipped.push({ label: control.label, value: incoming, reason: "不是可选值" });
        return;
      }
      if (snapshot && snapshot[key] !== uiState.revisions[key]) {
        skipped.push({ label: control.label, value: incoming, reason: "你刚手动改过" });
        return;
      }
      uiState.values[key] = incoming;
      var select = pluginControlsEl
        ? pluginControlsEl.querySelector('[data-ui-key="' + key + '"]')
        : null;
      if (select) select.value = incoming;
      applied.push({ label: control.label, value: incoming });
    });
    if (applied.length) {
      updateUiStateSummary();
      // AI 代人改参数同样要广播：中栏插件看到的参数必须和右栏一致
      publishUiParams("ai", null);
    }
    return { applied: applied, skipped: skipped };
  }

  function triggerUiButton(id) {
    var control = findUiControl(String(id || ""), "button");
    if (!control) {
      addBubble("sys", "AI 想触发面板按钮「" + id + "」，但当前面板没有这个按钮。", { tone: "warn" });
      return;
    }
    sendPrompt(expandCommand(control.command), {
      origin: "ai_button",
      buttonId: control.id,
      label: control.label,
    });
  }

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
  }

  function dockOpen() {
    return !!wsPage && wsPage.getAttribute("data-dock") === "open";
  }

  function setDock(open) {
    if (!wsPage) return;
    wsPage.setAttribute("data-dock", open ? "open" : "hidden");
    if (dockToggle) {
      dockToggle.setAttribute("aria-expanded", String(open));
      dockToggle.textContent = open ? "折叠" : "展开";
    }
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

  if (dockToggle) {
    dockToggle.addEventListener("click", function () {
      setDock(!dockOpen());
    });
  }

  // 默认态：桌面两栏展开、底栏展开；窄屏抽屉与底栏都收起，避免一进来就糊在中栏上。
  setSide(!mqMobile.matches);
  setCtx(!mqMobile.matches);
  setDock(!mqMobile.matches);

  // 跨断点时必须重算：窄屏收起的抽屉拖宽到桌面会留下「轨道已收起、属性仍写 open」
  // 的错位；反过来桌面展开态拉到窄屏则会让抽屉直接糊住对话流。
  function onBreakpoint(matched) {
    setSide(!matched);
    setCtx(!matched);
    setDock(!matched);
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

  // ============ 底栏输出区：EventBus 的 region.dock 落点 ============
  // 四区里左、右、下都由底座托管。插件想往底栏写字，只能发 region.dock 事件，
  // 底座收到后一律 textContent 落 DOM（AGENTS §5：不可信输入进 DOM 前必须净化）。
  var DOCK_MAX = 120;
  var dockEntries = [];
  var dockView = "log";
  var DOCK_VIEWS = { log: true, error: true, terminal: true };
  var DOCK_EMPTY = {
    log: "暂无输出。插件与面板事件会出现在这里。",
    error: "没有报错。插件与底座的事件流一切正常。",
    terminal: "暂无系统事件。",
  };

  // 三级分类只按事件主题与关键词判，不做内容猜谜：
  // error 进【报错诊断】，宿主生命周期进【系统终端】，其余留在【运行日志】。
  function dockLevel(topic, text) {
    var name = String(topic || "");
    if (/(^|[._-])(error|failed|failure|timeout)([._-]|$)/i.test(name) ||
      /失败|错误|异常|超时/.test(text)) {
      return "error";
    }
    if (/^(plugin|workspace|system|stage|layout|provider)\./.test(name)) return "system";
    return "info";
  }

  function stamp() {
    var now = new Date();
    return String(now.getHours()).padStart(2, "0") + ":" +
      String(now.getMinutes()).padStart(2, "0") + ":" +
      String(now.getSeconds()).padStart(2, "0");
  }

  function copyPlainText(value) {
    var text = String(value == null ? "" : value);
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      return navigator.clipboard.writeText(text).catch(function () { fallbackCopy(text); });
    }
    fallbackCopy(text);
    return Promise.resolve();
  }

  // http 下 navigator.clipboard 不可用（非安全上下文），回落老办法。
  function fallbackCopy(text) {
    var area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    try { document.execCommand("copy"); } catch (error) { /* 浏览器连老办法也不给，保持静默 */ }
    document.body.removeChild(area);
  }

  function entryVisible(entry) {
    if (dockView === "error") return entry.level === "error";
    if (dockView === "terminal") return entry.level === "system";
    return true;
  }

  function renderDock() {
    if (!dockLog) return;
    dockLog.setAttribute("data-view", dockView);
    dockLog.textContent = "";
    var shown = dockEntries.filter(entryVisible);
    if (!shown.length) {
      var empty = document.createElement("li");
      empty.className = "ws-dock-empty";
      empty.textContent = DOCK_EMPTY[dockView] || DOCK_EMPTY.log;
      dockLog.appendChild(empty);
      return;
    }
    shown.forEach(function (entry) {
      var item = document.createElement("li");
      item.className = "ws-dock-item";
      item.setAttribute("data-level", entry.level);
      item.setAttribute("data-copy", entry.line);
      var time = document.createElement("span");
      time.className = "ws-dock-time";
      time.textContent = entry.time;
      item.appendChild(time);
      if (entry.topic) {
        var tag = document.createElement("span");
        tag.className = "ws-dock-topic";
        tag.textContent = entry.topic;
        item.appendChild(tag);
      }
      var body = document.createElement("span");
      body.className = "ws-dock-text";
      body.textContent = entry.text;
      item.appendChild(body);
      if (dockView === "error") {
        var hint = document.createElement("span");
        hint.className = "ws-dock-copy";
        hint.setAttribute("aria-hidden", "true");
        hint.textContent = "双击复制";
        item.appendChild(hint);
      }
      dockLog.appendChild(item);
    });
    if (dockOpen()) {
      var dockBody = document.getElementById("wsDockBody");
      if (dockBody) dockBody.scrollTop = dockBody.scrollHeight;
    }
  }

  function setDockView(view) {
    dockView = DOCK_VIEWS[view] ? view : "log";
    if (dockTabs) {
      var buttons = dockTabs.querySelectorAll(".ws-dock-tab");
      for (var i = 0; i < buttons.length; i += 1) {
        buttons[i].setAttribute("aria-selected", String(buttons[i].getAttribute("data-view") === dockView));
      }
    }
    renderDock();
  }

  // 报错诊断的双击复制：原位闪绿底 + 变字，不弹 Toast、不选中文本、不抢焦点。
  if (dockLog) {
    dockLog.addEventListener("dblclick", function (event) {
      if (dockView !== "error") return;
      var item = event.target && event.target.closest ? event.target.closest(".ws-dock-item") : null;
      if (!item) return;
      event.preventDefault();
      var selection = window.getSelection ? window.getSelection() : null;
      if (selection) selection.removeAllRanges();
      var hint = item.querySelector(".ws-dock-copy");
      copyPlainText(item.getAttribute("data-copy") || "").then(function () {
        item.classList.add("is-copied");
        if (hint) hint.textContent = "已复制";
        window.setTimeout(function () {
          item.classList.remove("is-copied");
          if (hint) hint.textContent = "双击复制";
        }, 1200);
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

  function dockLine(text, topic, level) {
    var body = String(text == null ? "" : text).slice(0, 400);
    var name = String(topic || "");
    var at = stamp();
    dockEntries.push({
      time: at,
      topic: name,
      text: body,
      level: level || dockLevel(name, body),
      line: at + (name ? " [" + name + "] " : " ") + body,
    });
    while (dockEntries.length > DOCK_MAX) dockEntries.shift();
    renderDock();
  }

  // ============ 右侧 AI 副驾：感知录题当前题 → 改写字段 → 回填表单 ============
  function cpStatus(text) { if (cpCtx) cpCtx.textContent = text; }

  function cpRefresh() {
    var hasQ = Boolean(editorContext.question);
    if (cpAsk) cpAsk.disabled = !hasQ;
    if (cpBackfill) cpBackfill.disabled = !(hasQ && pendingPatch);
  }

  function cpAskNow() {
    if (!editorContext.question) { cpStatus("先在中栏打开或编辑一道题"); return; }
    var instruction = clampText(cpInput && cpInput.value, 400);
    if (!instruction) { cpStatus("请先写一句改写指令"); return; }
    var field = cpField && cpField.value === "solution" ? "solution" : "stem";
    var targetId = editorContext.id;
    if (cpAsk) { cpAsk.disabled = true; cpAsk.setAttribute("aria-busy", "true"); cpAsk.textContent = "改写中…"; }
    cpStatus("AI 副驾改写中…");
    pendingPatch = null; cpRefresh();
    fetch("/api/agent/refine", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: editorContext.question, instruction: instruction,
        field: field, task_id: "cp_" + Date.now()
      })
    })
      .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then(function (response) {
        var env = response && response.data ? response.data : (response && response.fallback);
        var value = env && env.value;
        var note = env && env.note;
        if (typeof value !== "string" || !value.trim()) {
          cpStatus("AI 没有给出可用的改写内容");
          return;
        }
        pendingPatch = { id: targetId, field: field, value: value };
        if (cpOut) cpOut.textContent = (note ? note + "\n\n" : "") + value;
        cpStatus((field === "solution" ? "解析" : "题干") + "改写完成，点「回填到表单」");
      })
      .catch(function (err) { cpStatus("副驾调用失败：" + err.message); })
      .then(function () {
        if (cpAsk) { cpAsk.disabled = false; cpAsk.removeAttribute("aria-busy"); cpAsk.textContent = "让 AI 改写"; }
        cpRefresh();
      });
  }

  function cpBackfillNow() {
    if (!pendingPatch) return;
    if (window.JzoStage && typeof window.JzoStage.broadcast === "function") {
      window.JzoStage.broadcast("editor.apply_patch", {
        id: pendingPatch.id, field: pendingPatch.field, value: pendingPatch.value
      });
      cpStatus("已回填到录题表单，请核对后保存");
      dockLine("AI 副驾把改写的" + (pendingPatch.field === "solution" ? "解析" : "题干") +
        "回填到了录题工作台", "copilot.apply");
    } else {
      cpStatus("当前没有可回填的录题页签");
    }
    cpRefresh();
  }

  function cpResetContext() {
    editorContext = { id: "", question: null, at: 0 };
    pendingPatch = null;
    cpStatus("尚未打开题目");
    if (cpOut) cpOut.textContent = "";
    cpRefresh();
  }

  function wireCopilot() {
    if (!cpAsk) return;
    cpRefresh();
    if (window.JzoBus && typeof window.JzoBus.on === "function") {
      // 录题工作台每次重绘都会经 stage.selection 上抛当前题目；副驾只认录题插件的选区。
      window.JzoBus.on("stage.selection", function (event) {
        var p = (event.payload && event.payload.raw) || {};
        if (p.pluginId !== "org.jiuzhang.editor") return;
        editorContext.question = p.question || null;
        editorContext.id = typeof p.editingId === "string" ? p.editingId : "";
        editorContext.at = Date.now();
        pendingPatch = null;
        cpStatus(editorContext.question
          ? (editorContext.id ? "正在编辑 " + editorContext.id : "正在录入新题")
          : "尚未打开题目");
        if (cpOut) cpOut.textContent = "";
        cpRefresh();
      });
      // 录题页签关闭后，副驾回到「未打开」，不把旧题当上下文继续改写。
      window.JzoBus.on("stage.tab.closed", function (event) {
        var key = (event.payload && event.payload.key) || "";
        if (key.indexOf("org.jiuzhang.editor") >= 0) cpResetContext();
      });
    }
    cpAsk.addEventListener("click", cpAskNow);
    if (cpBackfill) cpBackfill.addEventListener("click", cpBackfillNow);
  }

  function wireDock() {
    if (!window.JzoBus || typeof window.JzoBus.on !== "function") return;
    window.JzoBus.on("region.dock", function (event) {
      var payload = event.payload || {};
      dockLine(payload.text || "（空消息）", payload.topic || event.topic);
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
        dockEntries = [];
        renderDock();
      });
    }
  }

  // ============ 面板参数 → EventBus（右栏改一个值，中栏插件立刻知道） ============
  function uiValuesCopy() {
    var copy = {};
    Object.keys(uiState.values).forEach(function (key) { copy[key] = uiState.values[key]; });
    return copy;
  }

  function publishUiParams(source, changedKey) {
    if (!window.JzoBus || typeof window.JzoBus.emit !== "function") return;
    window.JzoBus.emit("ui.params.changed", {
      pluginId: uiState.pluginId,
      key: changedKey || null,
      values: uiValuesCopy(),
      revisions: JSON.parse(JSON.stringify(uiState.revisions)),
      by: source
    }, { source: "workspace" });
  }

  // 舞台挂载/唤醒插件时要补发一次当前参数，插件不必等下一次改动才对齐
  window.JzoUiState = { snapshot: function () {
    return { pluginId: uiState.pluginId, values: uiValuesCopy(), by: "snapshot" };
  } };

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
      if (uiPanelControls.length) {
        context.ui = {
          plugin_id: activePlugin.id,
          values: currentUiValues(),
          controls: compactControls(),
        };
      }
    }
    return context;
  }

  function summarizeUiControl(parsed) {
    var message = typeof parsed.message === "string" ? parsed.message.trim() : "";
    if (message && !looksLikeRawJson(message)) return message;
    if (parsed.action === "update_params") {
      var params = parsed.params && typeof parsed.params === "object" ? parsed.params : {};
      var pairs = Object.keys(params).map(function (key) { return key + "=" + params[key]; });
      return pairs.length
        ? "好，我把右侧面板调成：" + pairs.join("、") + "。"
        : "好，我来调整右侧面板。";
    }
    return "好，我替你点一下右侧面板的「" + clampText(parsed.button, 32) + "」。";
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
          return { text: "模型没有返回内容，请检查 Provider 配置。", source: source, tone: "warn", cards: [] };
        }

        // 先摘掉 ui_json 卡片围栏：卡片由前端渲染，正文才是给人看的话。
        var split = splitUiBlocks(content);
        var body = stripFences(split.text);
        var cards = split.cards;

        // 插件结果已经是后端整理好的自然语言，直接展示，不再当控制 JSON 解析。
        if (pluginCalls.length) {
          return {
            text: body,
            source: source,
            tone: null,
            pluginCalls: pluginCalls,
            route: response && response.route,
            cards: cards,
          };
        }

        if (!body && cards.length) {
          return { text: "", source: source, tone: null, cards: cards };
        }

        // 拦截：先把内容当控制 JSON 解析。命中 action 就翻译成人话，
        // 命中无 action 的普通 JSON 给通用回执，都不把原始 JSON 露给用户。
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
              text: summarizeUiControl(parsed),
              source: source,
              cards: cards,
              control: { action: "update_params", params: params },
            };
          }
          if (action === "trigger_button") {
            return {
              text: summarizeUiControl(parsed),
              source: source,
              cards: cards,
              control: { action: "trigger_button", button: typeof parsed.button === "string" ? parsed.button : "" },
            };
          }
          if (action) {
            return { text: summarizeAction(parsed, source), source: source, tone: null, cards: cards };
          }
          return {
            text: cards.length ? "" : "已收到模型的结构化回执（系统内部数据，已折叠）。",
            source: source,
            tone: null,
            cards: cards,
          };
        }
        // 不是 JSON：若是裸围栏/括号开头，判定为控制信令漏网，绝不直接显示。
        if (body && looksLikeRawJson(body)) {
          return {
            text: "模型返回了未识别的系统信令，已拦截未显示。请换种说法再试一次。",
            source: source,
            tone: "warn",
            cards: cards,
          };
        }
        // 真正的自然语言散文，可以直接给用户看（$...$ 交本地 KaTeX 渲染）。
        return { text: body, source: source, tone: null, cards: cards, richText: true };
      });
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
    if (options.origin === "ui_button") return "右侧面板 · 你点了「" + (options.label || "按钮") + "」";
    if (options.origin === "ai_button") return "AI 操控面板 · 触发「" + (options.label || "按钮") + "」";
    if (options.origin === "confirm_card") return "卡片按钮";
    return "";
  }

  // 处理模型下发的界面动作。返回需要在本次请求收尾后追加发送的指令。
  function handleControl(control, snapshot, allowUi) {
    if (!control) return null;
    if (control.action === "update_params") {
      if (!uiPanelControls.length) {
        addBubble("sys", "AI 想调整右侧面板，但当前没有可调参数，已忽略。", { tone: "warn" });
        return null;
      }
      var result = applyUiParams(control.params, snapshot);
      if (result.applied.length) {
        var appliedText = result.applied.map(function (item) {
          return item.label + " 设为「" + item.value + "」";
        }).join("，");
        addBubble("sys", "右侧面板已更新：" + appliedText + "。");
        logHistory("AI 调整面板：" + appliedText);
      }
      if (result.skipped.length) {
        var skippedText = result.skipped.map(function (item) {
          return item.label + "（" + item.reason + "，保留当前值）";
        }).join("，");
        addBubble("sys", "AI 想改的以下参数没有覆盖你的操作：" + skippedText + "。", { tone: "warn" });
      }
      return null;
    }
    if (control.action === "trigger_button") {
      if (!allowUi) {
        addBubble("sys", "本轮指令已由面板按钮触发，AI 再次触发按钮被忽略，避免循环。", { tone: "warn" });
        return null;
      }
      var button = findUiControl(control.button, "button");
      if (!button) {
        addBubble("sys", "AI 想触发面板按钮「" + control.button + "」，但当前面板没有这个按钮。", { tone: "warn" });
        return null;
      }
      addBubble("sys", "AI 正在替你执行面板按钮「" + button.label + "」…");
      logHistory("AI 触发面板按钮：" + button.label);
      return {
        prompt: expandCommand(button.command),
        options: { origin: "ai_button", buttonId: button.id, label: button.label },
      };
    }
    return null;
  }

  // 统一发送入口：人类输入、右侧面板按钮、AI 触发、确认卡片都走这里。
  function sendPrompt(prompt, options) {
    options = options || {};
    var text = String(prompt == null ? "" : prompt).trim();
    if (!text) return Promise.resolve();
    var origin = options.origin || "human";
    // AI 触发的按钮只允许再走一层：该轮若又拿到 trigger_button 就忽略。
    var allowUi = origin === "human" || origin === "confirm_card";

    addBubble("user", text, originNote(options) ? { source: originNote(options) } : undefined);
    logHistory("发送指令：" + (text.length > 24 ? text.slice(0, 24) + "…" : text));
    pushTurn("user", text);
    if (promptInput) {
      promptInput.value = "";
      autoGrow();
    }

    setSending(true);
    var typing = addTyping();
    var snapshot = snapshotRevisions();
    var followUp = null;

    return callAgent(text)
      .then(function (res) {
        if (typing) typing.remove();
        addBubble("bot", res.text, {
          source: res.source,
          tone: res.tone,
          pluginCalls: res.pluginCalls,
          route: res.route,
          cards: res.cards,
          richText: res.richText,
        });
        if (res.pluginCalls && res.pluginCalls.length) {
          logHistory("调用插件：" + pluginCallNames(res.pluginCalls));
        }
        pushTurn("assistant", res.text || (res.cards && res.cards.length ? "[已展示可视化卡片]" : ""));
        followUp = handleControl(res.control, snapshot, allowUi);
      })
      .catch(function (err) {
        if (typing) typing.remove();
        addBubble("bot", "指令执行失败：" + err.message, { tone: "warn", source: "底座未响应或 Provider 不可用" });
        pushTurn("assistant", "指令执行失败：" + err.message);
      })
      .finally(function () {
        setSending(false);
        if (promptInput) promptInput.focus();
        if (followUp) sendPrompt(followUp.prompt, followUp.options);
      });
  }

  if (chatForm) {
    chatForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var prompt = promptInput ? promptInput.value.trim() : "";
      if (!prompt) return;
      sendPrompt(prompt, { origin: "human" });
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

  // 顶栏模型胶囊已随舞台头一起退役：模型状态只在右栏「模型」一节如实显示。
  function renderModelChip() {
    var active = findActiveProvider();
    if (!ctxModel) return;
    if (!active) {
      ctxModel.textContent = "未就绪";
      return;
    }
    if (!active.configured || active.mock) {
      ctxModel.textContent = active.label + " · Mock 降级（未配置密钥）";
      return;
    }
    ctxModel.textContent = active.label + " · " + (active.model || "已配置");
  }

  function loadProviders() {
    return fetch("/api/providers", { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        providerList = data.providers || [];
        renderModelChip();
        return data;
      });
  }

  // --- 控制台页签：全仓唯一的「配置现场」 ---
  // 底座被改坏时仍可直连 /settings 强制进同一套面板（防变砖兜底，见军令例外条款）。
  var consoleFrameLoaded = false;
  var consolePanelPending = null;

  function postConsolePanel(frame, panel) {
    try {
      frame.contentWindow.postMessage({ jzo: "console.panel", panel: panel }, window.location.origin);
    } catch (error) {
      /* 内嵌面板还没起来：等 load 事件补发，不拿异常打死点击 */
    }
  }

  function openConsoleTab(panel) {
    var frame = document.getElementById("wsConsoleFrame");
    if (frame) {
      if (!consoleFrameLoaded) {
        frame.addEventListener("load", function () {
          consoleFrameLoaded = true;
          if (consolePanelPending) {
            postConsolePanel(frame, consolePanelPending);
            consolePanelPending = null;
          }
        }, { once: true });
        // 首次水合：直接把目标面板写进地址，省一次「先开默认页再跳面板」的闪动。
        var src = frame.getAttribute("src") || "about:blank";
        if (src === "about:blank" && panel) {
          frame.setAttribute("src", "/settings?embedded=1&panel=" + encodeURIComponent(panel));
          consolePanelPending = panel;
        } else if (panel) {
          consolePanelPending = panel;
        }
      } else if (panel) {
        postConsolePanel(frame, panel);
      }
    }
    if (window.JzoStage && typeof window.JzoStage.activate === "function") {
      window.JzoStage.activate("console");
    }
  }

  // 定调令：工作台不许再有弹窗。左栏图标与顶栏模型胶囊都只是「走到页签里」，
  // 模型配置表单在控制台里只有那一份。
  (function wireConsoleEntry() {
    var btn = document.getElementById("wsConsoleBtn");
    if (btn) {
      btn.addEventListener("click", function () { openConsoleTab(); });
    }
    // 控制台里改了模型配置 → 顶栏胶囊立即重拉状态，不让老师对着旧标签发愣。
    window.addEventListener("message", function (event) {
      if (event.origin !== window.location.origin) return;
      if (event.data && event.data.jzo === "providers.changed") loadProviders().catch(function () {});
    });
    // 控制台里热更了插件（PLUGIN_SPEC §1.7）→ 左栏、页签与画布立刻接上新代码，
    // 全程不刷新浏览器、不重启底座。宿主自己在总线上广播 plugin.updated。
    window.addEventListener("message", function (event) {
      if (event.origin !== window.location.origin) return;
      var data = event.data;
      if (!data || data.jzo !== "plugins.updated") return;
      var updated = Array.isArray(data.updated) ? data.updated : [];
      loadPlugins({ announce: false }).then(function () {
        updated.forEach(function (row) {
          var id = row && row.id;
          if (!id) return;
          if (window.JzoBus && typeof window.JzoBus.emit === "function") {
            window.JzoBus.emit("plugin.updated", {
              id: id, from: String(row.from || ""), to: String(row.to || "")
            });
          }
          if (window.JzoStage && typeof window.JzoStage.rehydratePlugin === "function") {
            window.JzoStage.rehydratePlugin(id);
          }
          logHistory("插件热更新：" + id + " " + (row.from || "?") + " → " + (row.to || "?"));
        });
      }).catch(function () {});
    });
  })();

  // ============ 已安装插件：动态渲染左栏插件区 ============
  var KIND_LABELS = { renderer: "渲染", importer: "导入", exporter: "导出", tool: "工具" };

  function pluginPriority(plugin) {
    var stage = plugin && plugin.stage;
    var value = stage && typeof stage.priority === "number" ? stage.priority : 0;
    return Math.max(-100, Math.min(100, value));
  }

  // 左栏插件的直白功能副标题：优先用 curated 文案，
  // 其次回落插件 description，最后才是类型标签——老师一眼看懂这插件干什么，而不是版本加点类型。
  var PLUGIN_TAGLINES = {
    "org.jiuzhang.core-bank": "内置大纲与题库引擎",
    "org.jiuzhang.editor": "录题、改题、删题工作台",
    "org.jiuzhang.paper-gen": "题篮排成 A4 练习卷",
    "org.jiuzhang.handout": "Markdown 讲义实时排 A4"
  };

  function pluginSidebarSubtitle(plugin) {
    var tagline = PLUGIN_TAGLINES[plugin.id];
    if (tagline) return tagline;
    var desc = String(plugin.description || "").trim();
    if (desc) return desc.split(/[：:。\n]/)[0].slice(0, 24);
    return KIND_LABELS[plugin.kind] || "插件";
  }

  // 拖拽排序的落盘键：只存条目 key 的顺序，不存任何业务数据。
  var PLUGIN_ORDER_KEY = "jzo.sidebar.order";

  function readPluginOrder() {
    try {
      var parsed = JSON.parse(window.localStorage.getItem(PLUGIN_ORDER_KEY) || "[]");
      return Array.isArray(parsed) ? parsed.filter(function (key) {
        return typeof key === "string";
      }) : [];
    } catch (error) {
      return [];   // 隐私模式或脏数据：按默认顺序渲染，绝不抛到调用点
    }
  }

  function savePluginOrder(keys) {
    try {
      window.localStorage.setItem(PLUGIN_ORDER_KEY, JSON.stringify(keys));
    } catch (error) {
      /* 写不进去只影响“记住顺序”，不影响本次拖拽结果 */
    }
  }

  function buildPluginRow(plugin) {
    var li = document.createElement("li");
    li.className = "ws-plugin-row";
    li.setAttribute("data-key", "plugin:" + String(plugin.id || ""));
    li.setAttribute("draggable", "true");
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "ws-plugin-item";
    btn.setAttribute("data-plugin-id", String(plugin.id || ""));
    btn.setAttribute("aria-current", String(Boolean(activePlugin && activePlugin.id === plugin.id)));
    var name = document.createElement("span");
    name.className = "ws-plugin-item-name";
    name.textContent = plugin.name || plugin.id || "未命名插件";
    var meta = document.createElement("span");
    meta.className = "ws-plugin-item-meta";
    meta.textContent = pluginSidebarSubtitle(plugin);
    btn.title = "v" + (plugin.version || "?");
    btn.appendChild(name);
    btn.appendChild(meta);
    btn.addEventListener("click", function () { enterPluginMode(plugin, btn); });
    li.appendChild(btn);
    return li;
  }

  function clearDropMarks() {
    if (!pluginListEl) return;
    var rows = pluginListEl.querySelectorAll(".ws-plugin-row[data-drop]");
    for (var i = 0; i < rows.length; i += 1) rows[i].removeAttribute("data-drop");
  }

  // 原生 HTML5 拖拽：拖起一行，落在目标行的上半/下半决定插前还是插后，
  // 顺序只写 localStorage（宿主自有），插件代码一律碰不到浏览器存储。
  function wirePluginDrag() {
    if (!pluginListEl) return;
    var draggingKey = "";
    pluginListEl.addEventListener("dragstart", function (event) {
      var row = event.target && event.target.closest ? event.target.closest(".ws-plugin-row") : null;
      if (!row) return;
      draggingKey = row.getAttribute("data-key") || "";
      row.classList.add("is-dragging");
      if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = "move";
        try { event.dataTransfer.setData("text/plain", draggingKey); } catch (error) { /* 旧浏览器忽略 */ }
      }
    });
    pluginListEl.addEventListener("dragover", function (event) {
      if (!draggingKey) return;
      var row = event.target && event.target.closest ? event.target.closest(".ws-plugin-row") : null;
      clearDropMarks();
      if (!row || row.getAttribute("data-key") === draggingKey) return;
      event.preventDefault();
      if (event.dataTransfer) event.dataTransfer.dropEffect = "move";
      var rect = row.getBoundingClientRect();
      row.setAttribute("data-drop", event.clientY < rect.top + rect.height / 2 ? "before" : "after");
    });
    pluginListEl.addEventListener("drop", function (event) {
      if (!draggingKey) return;
      var row = event.target && event.target.closest ? event.target.closest(".ws-plugin-row") : null;
      if (!row || row.getAttribute("data-key") === draggingKey) { draggingKey = ""; clearDropMarks(); return; }
      event.preventDefault();
      var targetKey = row.getAttribute("data-key") || "";
      var position = row.getAttribute("data-drop") || "before";
      var keys = [];
      var rows = pluginListEl.querySelectorAll(".ws-plugin-row");
      for (var i = 0; i < rows.length; i += 1) {
        var key = rows[i].getAttribute("data-key") || "";
        if (key && key !== draggingKey) keys.push(key);
      }
      var at = keys.indexOf(targetKey);
      if (at < 0) at = keys.length;
      if (position === "after") at += 1;
      keys.splice(at, 0, draggingKey);
      savePluginOrder(keys);
      draggingKey = "";
      clearDropMarks();
      renderPlugins(installedPlugins);
    });
    pluginListEl.addEventListener("dragend", function () {
      draggingKey = "";
      clearDropMarks();
      var dragging = pluginListEl.querySelectorAll(".ws-plugin-row.is-dragging");
      for (var i = 0; i < dragging.length; i += 1) dragging[i].classList.remove("is-dragging");
    });
  }

  function renderPlugins(plugins) {
    if (!pluginListEl) return;
    // 三态管理落到导航：停用的（enabled=false）与不占位的（show_in_sidebar=false）都不进左栏。
    var list = (plugins || []).filter(function (plugin) {
      return plugin.enabled !== false && plugin.show_in_sidebar !== false;
    });
    // 默认顺序：stage.priority 高者在前，同优先级按名称稳定排序；
    // 老师拖过之后，以 localStorage 里的顺序为唯一事实来源。
    list.sort(function (a, b) {
      var delta = pluginPriority(b) - pluginPriority(a);
      if (delta !== 0) return delta;
      return String(a.name || a.id || "").localeCompare(String(b.name || b.id || ""), "zh-CN");
    });
    var saved = readPluginOrder();
    function rank(key) {
      var index = saved.indexOf(key);
      return index < 0 ? Number.MAX_SAFE_INTEGER : index;
    }
    var chatRow = pluginListEl.querySelector('.ws-plugin-row[data-key="chat"]');
    var rows = [];
    if (chatRow) {
      var chatButton = chatRow.querySelector(".ws-plugin-item");
      if (chatButton) chatButton.setAttribute("aria-current", String(!activePlugin));
      rows.push(chatRow);
    }
    list.forEach(function (plugin) { rows.push(buildPluginRow(plugin)); });
    rows.sort(function (a, b) {
      return rank(a.getAttribute("data-key")) - rank(b.getAttribute("data-key"));
    });
    pluginListEl.textContent = "";
    rows.forEach(function (row) { pluginListEl.appendChild(row); });
    if (!list.length) {
      var empty = document.createElement("li");
      empty.className = "ws-plugin-empty";
      empty.textContent = "暂无插件";
      pluginListEl.appendChild(empty);
    }
    if (pluginCountEl) {
      pluginCountEl.hidden = false;
      pluginCountEl.textContent = String(list.length);
    }
  }

  var pluginSignature = null;
  var knownPluginIds = {};

  function pluginSignatureOf(data, plugins) {
    if (data && typeof data.signature === "string" && data.signature) return data.signature;
    return plugins.map(function (p) { return p.id + "@" + p.version; }).join("|");
  }

  /**
   * 热插拔：/api/plugins 每次请求都重新扫描 plugins/，后端另回一份清单签名。
   * 页面只需定时比对签名，用户往 plugins/ 里解压一个新目录（或拖装成功）后，
   * 左栏与画布无需重启即可看到变化。运行中的 iframe 代码不热替换——规范 §4
   * 明确要求刷新页面才加载新代码，这里只负责“发现与接入”。
   */
  function loadPlugins(options) {
    var opts = options || {};
    return fetch("/api/plugins", { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        var plugins = (data && data.plugins) || [];
        var signature = pluginSignatureOf(data, plugins);
        var changed = pluginSignature !== null && signature !== pluginSignature;
        var added = [];
        plugins.forEach(function (plugin) {
          if (!knownPluginIds[plugin.id]) added.push(plugin);
        });

        installedPlugins = plugins;
        if (activePlugin) {
          var still = null;
          for (var i = 0; i < plugins.length; i += 1) {
            if (plugins[i].id === activePlugin.id) { still = plugins[i]; break; }
          }
          if (still) {
            activePlugin = still;
            syncUiState(still);
            renderPluginPanel(still);
          } else {
            activePlugin = null;
            clearPluginPanel();
            setStage("自由对话");
            markActiveEntry(chatEntry);
          }
        }
        renderPlugins(plugins);
        if (window.JzoStage && typeof window.JzoStage.updatePlugin === "function") {
          plugins.forEach(function (plugin) { window.JzoStage.updatePlugin(plugin); });
        }

        if (opts.announce !== false && changed) {
          if (added.length) {
            addBubble("sys", "检测到新插件 " + added.map(function (p) {
              return "「" + (p.name || p.id) + "」";
            }).join("、") + "，已热接入左栏，无需重启。");
          } else {
            addBubble("sys", "插件清单已更新（覆盖安装或卸载）。左栏与页签已刷新。");
          }
          logHistory("插件热刷新：" + (added.length ? added.map(function (p) { return p.id; }).join(",") : signature));
        }

        pluginSignature = signature;
        knownPluginIds = {};
        plugins.forEach(function (plugin) { knownPluginIds[plugin.id] = true; });
        return plugins;
      });
  }

  function pollPlugins() {
    if (document.hidden) return;
    loadPlugins({ announce: true }).catch(function () { /* 轮询失败保持现状，下次再试 */ });
  }
  window.setInterval(pollPlugins, 5000);
  window.addEventListener("focus", pollPlugins);
  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) pollPlugins();
  });

  // ============ 插件拖拽装：工作台全局兜底（选文件与索引入口在 /settings） ============
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

  // ============ 初始化 ============
  // 默认入口只有「自由对话」；插件区完全由 /api/plugins 的发现结果渲染。
  wireDock();
  wireCopilot();
  wirePluginDrag();
  setStage("自由对话");
  markActiveEntry(chatEntry);
  addBubble("sys", "九章算子工作台已就绪 · 已装插件会自动接入对话工具（tool_calls），结果以「已调用插件」标识回显");
  addBubble("bot", "你好，我是九章算子工作台助手。从左侧选择「自由对话」或某个已安装插件，也可以直接在下方输入指令。进入插件工作模式后，我会优先调用该插件的能力。安装插件、切换题库或配置模型，点左下角【设置与控制台】。");

  // 种子题库插件在场时才提示示例题（10.24 军令任务 2）：插件被删就不许说谎。
  loadPlugins()
    .then(function (plugins) {
      // 启动行为在插件清单渲染完之后执行：左栏条目已就位，进去才能高亮对应项
      return applyStartupBehavior(plugins).then(function () {
        var hasDemo = plugins.some(function (p) { return p.id === "org.jiuzhang.demo-bank"; });
        if (hasDemo && !activePlugin) {
          addBubble("bot", "系统已为您预置了 5 道示例数学题，您可以直接输入「拆分第一题」进行体验。");
        }
      });
    })
    .catch(function () { /* 探测失败保留「暂无插件」空态，不打扰用户 */ });

  loadProviders().catch(function () {
    renderModelChip();
  });
})();
