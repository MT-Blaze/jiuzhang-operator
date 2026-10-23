(function () {
  "use strict";

  var PROTOCOL = "jzo-plugin/1";
  var PLUGIN_ID = "org.jiuzhang.classic-card";

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
    // 契约 1.0 的旧值只做兜底，归一由底座写入端负责
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

  function renderOptions(options) {
    if (!Array.isArray(options) || options.length === 0) return "";

    var rows = options.map(function (option) {
      var body = option.content ? escapeHtml(option.content) : "";
      if (Array.isArray(option.image_ids) && option.image_ids.length > 0) {
        body = (body ? body + " " : "") + "〔图 " + escapeHtml(option.image_ids.join("、")) + "〕";
      }
      return [
        '<li class="jzc-option">',
        '<span class="jzc-key">' + escapeHtml(option.key) + "</span>",
        '<span class="jzc-option-body">' + body + "</span>",
        "</li>"
      ].join("");
    });

    return '<ol class="jzc-options">' + rows.join("") + "</ol>";
  }

  function renderTags(tags) {
    if (!Array.isArray(tags) || tags.length === 0) return "";
    var items = tags.slice(0, 12).map(function (tag) {
      return '<span class="jzc-tag">' + escapeHtml(tag) + "</span>";
    });
    return '<div class="jzc-tags">' + items.join("") + "</div>";
  }

  function renderSource(source) {
    if (!source || typeof source !== "object") return "";
    var parts = [];
    if (source.year) parts.push(String(source.year) + "年");
    if (source.region) parts.push(source.region);
    if (source.school) parts.push(source.school);
    if (source.exam_type) parts.push(source.exam_type);
    if (source.question_no) parts.push("第 " + source.question_no + " 题");
    return parts.length > 0 ? parts.map(escapeHtml).join(" · ") : "";
  }

  function render(question) {
    var status = question.meta && question.meta.status ? question.meta.status : "draft";
    var statusLabel = status === "published" ? "已发布" : status === "archived" ? "已归档" : "草稿";
    var source = renderSource(question.source);

    return [
      '<article class="jzc-card" data-jzo-plugin="' + PLUGIN_ID + '">',
      '<header class="jzc-head">',
      '<span class="jzc-badge">' + labelOf(TYPE_LABELS, question.type) + "</span>",
      '<span class="jzc-badge jzc-difficulty" data-level="' + escapeHtml(question.difficulty) + '">' +
        labelOf(DIFFICULTY_LABELS, question.difficulty) + "</span>",
      '<span class="jzc-status" data-status="' + escapeHtml(status) + '">' + statusLabel + "</span>",
      '<span class="jzc-id">' + escapeHtml(question.id) + "</span>",
      "</header>",
      '<p class="jzc-stem">' + escapeHtml(question.stem) + "</p>",
      renderOptions(question.options),
      '<footer class="jzc-foot">',
      renderTags(question.tags),
      source ? '<span class="jzc-source">' + source + "</span>" : "",
      "</footer>",
      "</article>"
    ].join("");
  }

  function reply(target, requestId, result) {
    if (!target) return;
    target.postMessage({
      protocol: PROTOCOL,
      id: requestId,
      kind: "response",
      ok: true,
      result: result
    }, "*");
  }

  function fail(target, requestId, code, message) {
    if (!target) return;
    target.postMessage({
      protocol: PROTOCOL,
      id: requestId,
      kind: "response",
      ok: false,
      error: { code: code, message: message, retryable: false }
    }, "*");
  }

  window.addEventListener("message", function (event) {
    var message = event.data;
    if (!message || message.protocol !== PROTOCOL || message.kind !== "request") return;

    var method = message.method;

    if (method === "plugin.activate") {
      reply(event.source, message.id, { ready: true, plugin_id: PLUGIN_ID, api_version: "1.0" });
      return;
    }

    if (method === "plugin.deactivate") {
      reply(event.source, message.id, { ready: false });
      return;
    }

    if (method === "question.render") {
      var payload = message.payload || {};
      var question = payload.question;
      if (payload.slot !== "question.card") {
        fail(event.source, message.id, "UNSUPPORTED_SLOT", "仅支持 question.card 插槽。");
        return;
      }
      if (!question || typeof question.id !== "string" || typeof question.stem !== "string") {
        fail(event.source, message.id, "INVALID_PAYLOAD", "题目载荷缺少 id 或 stem。");
        return;
      }
      reply(event.source, message.id, { html: render(question), height: 180 });
      return;
    }

    if (method === "theme.changed" || method === "locale.changed" || method === "question.updated") {
      reply(event.source, message.id, { accepted: true });
      return;
    }

    fail(event.source, message.id, "UNSUPPORTED_METHOD", "未实现的方法：" + String(method));
  });
})();
