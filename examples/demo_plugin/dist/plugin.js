/**
 * 示例题库插件运行时（org.jiuzhang.demo-bank）。
 *
 * 两种运行形态：
 * 1. 沙箱 iframe 中接收宿主 postMessage 请求（jzo-plugin/1 协议）：
 *    激活/停用、question.card 渲染、吐出自带的 5 道种子题。
 * 2. 被直接打开时（无宿主），自渲染一份种子题清单预览。
 *
 * 安全：所有题目文本一律转义后才拼进 HTML；预览模式只用 textContent。
 */
(function () {
  "use strict";

  var PROTOCOL = "jzo-plugin/1";
  var PLUGIN_ID = "org.jiuzhang.demo-bank";

  // 构建脚本会把 seed/questions.json 内联到下面这个占位数组里。
  var SEED_QUESTIONS = /*__SEED_QUESTIONS__*/[];

  var TYPE_LABELS = {
    single_choice: "单选",
    multiple_choice: "多选",
    fill_blank: "填空",
    solution: "解答",
    proof: "证明",
    unknown: "待定"
  };

  var DIFFICULTY_LABELS = {
    L1: "基础",
    L2: "中档",
    L3: "难",
    L4: "压轴",
    // 契约 1.0 的旧值在这里只做兜底显示，归一由底座写入端负责
    basic: "基础",
    medium: "中档",
    hard: "难",
    novel: "压轴"
  };

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function labelOf(map, key) {
    return Object.prototype.hasOwnProperty.call(map, key) ? map[key] : "未知";
  }

  function renderCard(question) {
    var parts = [];
    parts.push('<article class="jdb-card" data-jzo-plugin="' + PLUGIN_ID + '">');
    parts.push('<header class="jdb-head">');
    parts.push('<span class="jdb-badge">' + escapeHtml(labelOf(TYPE_LABELS, question.type)) + "</span>");
    parts.push('<span class="jdb-badge jdb-difficulty" data-level="' + escapeHtml(question.difficulty) + '">' +
      escapeHtml(labelOf(DIFFICULTY_LABELS, question.difficulty)) + "</span>");
    parts.push('<span class="jdb-id">' + escapeHtml(question.id) + "</span>");
    parts.push("</header>");
    parts.push('<p class="jdb-stem">' + escapeHtml(question.stem) + "</p>");
    if (Array.isArray(question.options) && question.options.length > 0) {
      parts.push('<ol class="jdb-options">');
      question.options.forEach(function (option) {
        parts.push('<li><span class="jdb-key">' + escapeHtml(option.key) + "</span>" +
          "<span>" + escapeHtml(option.content) + "</span></li>");
      });
      parts.push("</ol>");
    }
    if (Array.isArray(question.tags) && question.tags.length > 0) {
      parts.push('<div class="jdb-tags">');
      question.tags.slice(0, 8).forEach(function (tag) {
        parts.push('<span class="jdb-tag">' + escapeHtml(tag) + "</span>");
      });
      parts.push("</div>");
    }
    parts.push("</article>");
    return parts.join("");
  }

  // ============ 宿主协议（沙箱 iframe 形态） ============

  function respond(target, requestId, ok, body) {
    if (!target) return;
    var message = { protocol: PROTOCOL, id: requestId, kind: "response", ok: ok };
    if (ok) message.result = body;
    else message.error = { code: body.code, message: body.message, retryable: false };
    target.postMessage(message, "*");
  }

  window.addEventListener("message", function (event) {
    var message = event.data;
    if (!message || message.protocol !== PROTOCOL) return;

    // 单向通知（v0.6.0 新增）：宿主不等回复，插件必须幂等——
    // 同一个参数连发两次，画面只能有一份结果。
    if (message.kind === "notification") {
      if (message.event === "ui.params.changed") {
        var incoming = message.payload || {};
        stageParams = incoming.values || {};
        if (stageMode) renderStageView();
        publishToHost("region.dock", "示例题库收到面板参数：" + describeParams(stageParams));
      }
      return;
    }

    if (message.kind !== "request") return;

    if (message.method === "plugin.activate") {
      var activatePayload = message.payload || {};
      // 宿主把本插件挂进中栏画布时会带上 slot；这时要自己画出界面
      if (activatePayload.slot === "stage.center") {
        stageMode = true;
        renderStageView();
      }
      respond(event.source, message.id, true, {
        ready: true,
        plugin_id: PLUGIN_ID,
        api_version: "1.0",
        seed_count: SEED_QUESTIONS.length
      });
      return;
    }
    if (message.method === "plugin.deactivate") {
      stageMode = false;
      respond(event.source, message.id, true, { ready: false });
      return;
    }
    if (message.method === "seed.questions") {
      respond(event.source, message.id, true, { questions: SEED_QUESTIONS });
      return;
    }
    if (message.method === "question.render") {
      var payload = message.payload || {};
      if (payload.slot !== "question.card") {
        respond(event.source, message.id, false, {
          code: "UNSUPPORTED_SLOT",
          message: "示例题库只支持 question.card 插槽。"
        });
        return;
      }
      var question = payload.question;
      if (!question || typeof question.id !== "string" || typeof question.stem !== "string") {
        respond(event.source, message.id, false, {
          code: "INVALID_PAYLOAD",
          message: "题目载荷缺少 id 或 stem。"
        });
        return;
      }
      respond(event.source, message.id, true, { html: renderCard(question), height: 200 });
      return;
    }
    if (message.method === "theme.changed" || message.method === "locale.changed" ||
        message.method === "question.updated") {
      respond(event.source, message.id, true, { accepted: true });
      return;
    }
    respond(event.source, message.id, false, {
      code: "UNSUPPORTED_METHOD",
      message: "未实现的方法：" + String(message.method)
    });
  });

  // ============ 中栏画布形态（v0.6.0：宿主挂进 stage.center 时自绘） ============

  var stageMode = false;
  var stageParams = {};

  function publishToHost(event, text) {
    if (window.parent === window) return;
    window.parent.postMessage({
      protocol: PROTOCOL,
      kind: "notification",
      event: event,
      payload: { text: text }
    }, "*");
  }

  function describeParams(values) {
    var grade = values && values.grade ? values.grade : "全部";
    var difficulty = values && values.difficulty ? values.difficulty : "全部";
    return "年级 " + grade + " · 难度 " + difficulty;
  }

  function matchesParams(question) {
    var wanted = stageParams && stageParams.difficulty;
    if (!wanted || wanted === "全部") return true;
    return labelOf(DIFFICULTY_LABELS, question.difficulty) === wanted;
  }

  /** 幂等重画：先清空 root，再按当前参数出一份列表。 */
  function renderStageView() {
    var root = document.getElementById("root");
    if (!root) return;
    root.textContent = "";

    var title = document.createElement("h1");
    title.className = "jdb-preview-title";
    title.textContent = "示例题库 · 画布页";
    root.appendChild(title);

    var picked = SEED_QUESTIONS.filter(matchesParams);
    var hint = document.createElement("p");
    hint.className = "jdb-preview-hint";
    hint.textContent = "当前参数：" + describeParams(stageParams) +
      "（右栏改下拉，这行会立刻跟着变）· 命中 " + picked.length + " / " + SEED_QUESTIONS.length + " 题";
    root.appendChild(hint);

    picked.forEach(function (question, index) {
      var card = document.createElement("section");
      card.className = "jdb-preview-card";

      var head = document.createElement("p");
      head.className = "jdb-preview-head";
      head.textContent = "第 " + (index + 1) + " 题 · " +
        labelOf(TYPE_LABELS, question.type) + " · " +
        labelOf(DIFFICULTY_LABELS, question.difficulty);
      card.appendChild(head);

      var stem = document.createElement("p");
      stem.className = "jdb-preview-stem";
      stem.textContent = question.stem;
      card.appendChild(stem);

      root.appendChild(card);
    });

    if (!picked.length) {
      var empty = document.createElement("p");
      empty.className = "jdb-preview-hint";
      empty.textContent = "这个难度下暂时没有示例题，换个参数试试。";
      root.appendChild(empty);
    }

    root.hidden = false;
  }

  // ============ 独立预览（直接打开页面时） ============

  function renderStandalonePreview() {
    var root = document.getElementById("root");
    if (!root || !SEED_QUESTIONS.length) return;

    var title = document.createElement("h1");
    title.className = "jdb-preview-title";
    title.textContent = "示例题库 · 5 道高中数学示例题";
    root.appendChild(title);

    var hint = document.createElement("p");
    hint.className = "jdb-preview-hint";
    hint.textContent = "这些题目随九章算子底座首次启动自动安装。回到工作台，输入「拆分第一题」即可体验。";
    root.appendChild(hint);

    SEED_QUESTIONS.forEach(function (question, index) {
      var card = document.createElement("section");
      card.className = "jdb-preview-card";

      var head = document.createElement("p");
      head.className = "jdb-preview-head";
      head.textContent = "第 " + (index + 1) + " 题 · " +
        labelOf(TYPE_LABELS, question.type) + " · " +
        labelOf(DIFFICULTY_LABELS, question.difficulty);
      card.appendChild(head);

      var stem = document.createElement("p");
      stem.className = "jdb-preview-stem";
      stem.textContent = question.stem;
      card.appendChild(stem);

      root.appendChild(card);
    });

    root.hidden = false;
  }

  if (window.self === window.top) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", renderStandalonePreview);
    } else {
      renderStandalonePreview();
    }
  }
})();
