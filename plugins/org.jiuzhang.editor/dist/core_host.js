/**
 * core_host.js —— plugin.js 的「宿主通信」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var PROTOCOL = coreState.PROTOCOL;
    var REQUEST_TIMEOUT_MS = coreState.REQUEST_TIMEOUT_MS;
    var pending = coreState.pending;
    var state = coreState.state;
    var panelMessageEl = deps.dom.panelMessageEl;
    var toastEl = deps.dom.toastEl;

  var requestSeq = 0;
  var toastTimer = 0;

  // ---------- 宿主通信 ----------
  function hostCall(method, payload, timeoutMs) {
    return new Promise(function (resolve, reject) {
      requestSeq += 1;
      var id = "edv2" + requestSeq + "-" + Date.now().toString(36);
      var limit = Number(timeoutMs) > 0 ? Number(timeoutMs) : REQUEST_TIMEOUT_MS;
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

  /** 宿主错误码必须原样带出来：409 撞号、422 不符合 Schema 与「没权限」是三种话。 */
  function hostError(raw) {
    var error = new Error((raw && raw.message) || "宿主返回失败");
    error.code = String((raw && raw.code) || "HOST_ERROR");
    error.retryable = Boolean(raw && raw.retryable);
    // 查重：底座把主库那道题的 id 与 duplicate 标记一并带回来，弹窗才画得出「返回修改 / 强行覆盖」。
    error.existingId = String((raw && raw.existing_id) || "");
    error.duplicate = Boolean(raw && raw.duplicate);
    // 报错诊断与字典拦截都靠这几个字段：完整现场 + 结构化的冲突信息。
    error.detail = String((raw && raw.detail) || "");
    error.status = Number(raw && raw.status) || 0;
    error.detailCode = String((raw && raw.detail_code) || "");
    error.existingFullName = String((raw && raw.existing_full_name) || "");
    return error;
  }

  function publish(event, payload) {
    try {
      window.parent.postMessage({
        protocol: PROTOCOL, kind: "notification", event: event, payload: payload || {}
      }, "*");
    } catch (error) { /* 通知丢一帧不致命 */ }
  }

  /** 往底部日志写一行。level 由宿主白名单把关：note（灰字流水）、warn（警告）、info。 */
  function dock(text, level, topic, detail) {
    publish("region.dock", {
      text: String(text == null ? "" : text).slice(0, 400),
      level: level || "info",
      topic: topic || "",
      // 报错诊断要完整现场：宿主中继失败时把请求行、状态、Response 全文一并交出去。
      detail: String(detail == null ? "" : detail).slice(0, 20000)
    });
  }

  function errorDetail(error) {
    if (!error) return "";
    if (typeof error.detail === "string" && error.detail) return error.detail;
    var lines = [];
    if (error.status) lines.push("HTTP " + error.status + (error.statusText ? " " + error.statusText : ""));
    if (error.message) lines.push(String(error.message));
    return lines.join("\n");
  }

  /**
   * 警告只进底部日志，绝不在画布上弹红窗——
   * 后台切题时识别错得再离谱也照切不误，老师看到的只是一行提示，不是一块拦路的窗。
   */
  function dockWarn(text, detail) {
    dock("⚠ " + String(text == null ? "" : text).slice(0, 360), "warn", "editor.warn", detail);
  }

  function respond(target, id, ok, result, code, message) {
    var packet = { protocol: PROTOCOL, id: id, kind: "response", ok: ok };
    if (ok) packet.result = result || {};
    else packet.error = { code: code || "ERROR", message: message || "失败", retryable: false };
    try { target.postMessage(packet, "*"); } catch (error) { /* 宿主已走 */ }
  }

  function toast(text, tone) {
    if (!toastEl) return;
    toastEl.textContent = text;
    toastEl.setAttribute("data-tone", tone || "info");
    toastEl.setAttribute("data-show", "true");
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(function () {
      toastEl.setAttribute("data-show", "false");
    }, 2600);
  }

  /** 辅助栏的落地话术：状态区常驻，不用老师盯着画布的一闪而过的提示。 */
  function panelSay(text, tone, state) {
    if (!panelMessageEl) return;
    panelMessageEl.textContent = text;
    panelMessageEl.setAttribute("data-tone", tone || "info");
    panelMessageEl.setAttribute("data-save-state", state || "idle");
  }

  function trunc(value, limit) {
    var text = String(value == null ? "" : value);
    return text.length > limit ? text.slice(0, limit) : text;
  }

  function nowIso() {
    var date = new Date();
    var pad = function (n) { return (n < 10 ? "0" : "") + n; };
    var offset = -date.getTimezoneOffset();
    var sign = offset >= 0 ? "+" : "-";
    var hours = pad(Math.floor(Math.abs(offset) / 60));
    var minutes = pad(Math.abs(offset) % 60);
    return date.getFullYear() + "-" + pad(date.getMonth() + 1) + "-" + pad(date.getDate())
      + "T" + pad(date.getHours()) + ":" + pad(date.getMinutes()) + ":" + pad(date.getSeconds())
      + sign + hours + ":" + minutes;
  }

    return {
      dock: dock,
      dockWarn: dockWarn,
      errorDetail: errorDetail,
      hostCall: hostCall,
      hostError: hostError,
      nowIso: nowIso,
      panelSay: panelSay,
      publish: publish,
      requestSeq: requestSeq,
      respond: respond,
      toast: toast,
      toastTimer: toastTimer,
      trunc: trunc,
    };
  }

  global.JzoEditorHost = { create: create };
})(window);
