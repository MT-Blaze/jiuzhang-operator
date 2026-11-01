/*
 * AI 助手插件 · 富卡片（ui_ 前缀 = 只管「数据变成界面」，PLUGIN_SPEC §2.8.1）。
 *
 * 本文件把模型吐出的 ui_json 卡片变成 DOM：题卡、安装建议卡、操作确认卡与智能跳转钮。
 * 它不认识宿主协议，一切对外动作都通过 create(ctx) 交进来的回调做：
 *   ctx.hostCall(method, payload, timeoutMs) → 唯一的数据/写操作通道（令牌在底座手里）
 *   ctx.sendPrompt / ctx.addBubble / ctx.dock / ctx.refreshWorkspace → 回对话与底栏
 * 卡片文案一律 clampText 截断、一律 textContent 落屏，不拼 HTML（铁律 4）。
 */
(function (global) {
  "use strict";

  function create(ctx) {
    var clampText = ctx.clampText;
    var renderMathInto = ctx.renderMathInto;
    var hostCall = ctx.hostCall;
    var addBubble = ctx.addBubble;
    var dock = ctx.dock;
    var refreshWorkspace = ctx.refreshWorkspace;
    var sendPrompt = ctx.sendPrompt;
    var AGENT_TIMEOUT_MS = ctx.AGENT_TIMEOUT_MS;

    // 卡片详情区的 DOM id 序号：只有本模块发卡片，序号就归本模块自己管。
    var cardSeq = 0;

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
            buttonEl.setAttribute("aria-busy", "true");
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
          // 命令确认卡带 silent：确认码是控制信令，不该在对话里留一条技术气泡。
          sendPrompt(command, { origin: "confirm_card", silent: action.silent === true });
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

    return {
      splitUiBlocks: splitUiBlocks,
      buildCard: buildCard,
      buildActionButton: buildActionButton
    };
  }

  global.JzoChatCards = { create: create };
})(window);
