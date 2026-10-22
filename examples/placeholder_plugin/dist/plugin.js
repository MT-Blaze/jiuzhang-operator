(function () {
  "use strict";

  var PROTOCOL = "jzo-plugin/1";
  var PLUGIN_ID = "org.jiuzhang.placeholder";

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
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

  function render(question) {
    return [
      '<article class="jzp-card" data-jzo-plugin="' + PLUGIN_ID + '">',
      '<span class="jzp-badge">占位演示</span>',
      '<p class="jzp-stem">' + escapeHtml(question.stem) + "</p>",
      '<span class="jzp-id">' + escapeHtml(question.id) + "</span>",
      "</article>"
    ].join("");
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
      reply(event.source, message.id, { html: render(question), height: 96 });
      return;
    }

    if (method === "theme.changed" || method === "locale.changed" || method === "question.updated") {
      reply(event.source, message.id, { accepted: true });
      return;
    }

    fail(event.source, message.id, "UNSUPPORTED_METHOD", "未实现的方法：" + String(method));
  });
})();
