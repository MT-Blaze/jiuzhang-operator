/**
 * 统一的请求报错现场（主公 2026-11-01 抢修）。
 *
 * 一句「Not Found」等于让老师自己猜。任何一次失败请求都必须交代四件事：
 * 请求行（方法 + 完整地址）、HTTP 状态码、响应全文、请求体摘要（密钥脱敏，
 * base64 图片只报类型与长度）。两条路并行保证不丢现场：
 *
 * 1. 拦截器：所有 fetch 的非 2xx 响应都在控制台留一条完整记录——哪怕调用方
 *    忘了判 response.ok，日志里也查得到是谁、去了哪、服务端回了什么；
 * 2. failure()：需要抛给界面的封装（fetchJson / apiCall / postJson）统一造错，
 *    错误的 message 自带「[404 Not Found] POST /api/ingest/files 失败：…」，
 *    detail 字段再铺开请求体与响应全文，供底栏【报错诊断】原样展示。
 */
(function () {
  "use strict";

  var MAX_REASON = 300;
  var MAX_PAYLOAD = 1200;
  var MAX_BODY = 4000;
  var MAX_MESSAGE = 800;
  var SECRET_KEY = /^(password|passwd|token|local_token|x-jzo-token|authorization|api_?key|secret)$/i;

  function clip(text, limit) {
    var value = String(text == null ? "" : text);
    if (value.length <= limit) return value;
    return value.slice(0, limit) + "…（共 " + value.length + " 字符）";
  }

  function dataUrlLabel(text) {
    var match = /^data:([^;,]*)/.exec(String(text));
    return "data:" + (match && match[1] ? match[1] : "未知类型") + ";base64,<" + text.length + " 字符>";
  }

  /** 请求体摘要：密钥脱敏、base64 只留类型与长度，其余按层级截断。 */
  function summarize(value, depth) {
    if (value == null) return value;
    if (typeof value === "string") {
      if (/^data:[^,]*,/.test(value)) return dataUrlLabel(value);
      return clip(value, 160);
    }
    if (typeof value !== "object") return value;
    if (depth >= 3) return Array.isArray(value) ? "[数组 " + value.length + " 项]" : "{…}";
    if (Array.isArray(value)) {
      var items = value.slice(0, 8).map(function (item) { return summarize(item, depth + 1); });
      if (value.length > 8) items.push("…共 " + value.length + " 项");
      return items;
    }
    var out = {};
    Object.keys(value).slice(0, 24).forEach(function (key) {
      out[key] = SECRET_KEY.test(key) ? "<已脱敏>" : summarize(value[key], depth + 1);
    });
    return out;
  }

  function payloadText(body) {
    if (body == null || body === "") return "";
    if (typeof body !== "string") {
      try {
        return clip(JSON.stringify(summarize(body, 0)), MAX_PAYLOAD);
      } catch (error) {
        return clip(String(body), MAX_PAYLOAD);
      }
    }
    try {
      return clip(JSON.stringify(summarize(JSON.parse(body), 0)), MAX_PAYLOAD);
    } catch (error) {
      return clip(body, MAX_PAYLOAD);
    }
  }

  /** 从 FastAPI 的 detail 里取人话；取不到就退回响应正文。 */
  function reasonOf(data, text, status) {
    var detail = data && data.detail;
    if (typeof detail === "string" && detail.trim()) return detail.trim();
    if (detail && typeof detail === "object") {
      var head = typeof detail.message === "string" ? detail.message : "";
      var first = Array.isArray(detail.errors) && typeof detail.errors[0] === "string" ? detail.errors[0] : "";
      if (head && first) return head + "：" + first;
      if (head || first) return head || first;
      try {
        return clip(JSON.stringify(detail), MAX_REASON);
      } catch (error) {
        return "HTTP " + status;
      }
    }
    var raw = String(text == null ? "" : text).trim();
    return raw ? clip(raw, MAX_REASON) : "服务端没有返回正文";
  }

  /** 一行话的请求摘要：「[404 Not Found] POST /api/ingest/files 失败：Not Found」。 */
  function summary(options) {
    var opts = options || {};
    var status = Number(opts.status) || 0;
    var statusText = String(opts.statusText || "");
    var method = String(opts.method || "").toUpperCase();
    var url = String(opts.url || "");
    var reason = opts.reason != null ? String(opts.reason) : reasonOf(opts.data, opts.text, status);
    var head = status ? "[" + status + (statusText ? " " + statusText : "") + "]" : "[请求失败]";
    var target = [method, url].filter(Boolean).join(" ");
    return clip(head + " " + (target ? target + " " : "") + "失败：" + reason, MAX_MESSAGE);
  }

  /** 造一个带完整现场的错误：message 一行可读，detail 铺开全文。 */
  function failure(options) {
    var opts = options || {};
    var status = Number(opts.status) || 0;
    var statusText = String(opts.statusText || "");
    var payload = payloadText(opts.payload);
    var error = new Error(summary(opts));
    error.url = String(opts.url || "");
    error.method = String(opts.method || "").toUpperCase();
    error.status = status;
    error.statusText = statusText;
    error.detail = opts.data && opts.data.detail !== undefined ? opts.data.detail : reasonOf(opts.data, opts.text, status);
    error.body = String(opts.text == null ? "" : opts.text);
    error.payload = payload;
    error.requestLine = [error.method, error.url].filter(Boolean).join(" ");
    return error;
  }

  /** 底栏【报错诊断】的正文：请求行、状态、请求体、响应全文，404 附一句诊断。 */
  function detail(error) {
    if (!error) return "";
    var lines = [];
    var method = String(error.method || "").toUpperCase();
    var url = String(error.url || "");
    if (url) lines.push("请求：" + [method, url].filter(Boolean).join(" "));
    if (error.status) {
      lines.push("状态：HTTP " + error.status + (error.statusText ? " " + error.statusText : ""));
    }
    if (error.payload) lines.push("请求体：" + error.payload);
    if (error.body) lines.push("响应全文：" + clip(error.body, MAX_BODY));
    if (!error.body && error.message) lines.push("原因：" + error.message);
    if (error.status === 404) {
      lines.push("诊断：当前底座进程里没有这个接口。若源码里已经写了该路由，"
        + "说明正在跑的是旧进程——重启一次底座即可（已提交的代码不会自动进内存）。");
    }
    return lines.join("\n").slice(0, 20000);
  }

  /** 读响应全文并尽力解析 JSON（解析失败不算错），交给 fromResponse 统一造错。 */
  function readText(response, handler) {
    return response.text().then(function (text) {
      var data = null;
      try { data = text ? JSON.parse(text) : null; } catch (error) { data = null; }
      return handler(text, data);
    });
  }

  /**
   * 由一次真实的 Response 造错：URL / 方法 / 请求体 / 状态 / 响应全文一次凑齐。
   * 各处的请求封装只负责把「谁、往哪、发了什么」递进来，现场拼装只有这一份。
   */
  function fromResponse(response, text, data, options) {
    var opts = options || {};
    return failure({
      status: response.status,
      statusText: response.statusText || "",
      method: opts.method || "GET",
      url: opts.url || response.url || "",
      text: text,
      data: data,
      payload: opts.payload
    });
  }

  /** 所有 fetch 的兜底记录：非 2xx 一律把完整现场打进控制台。 */
  function installInterceptor() {
    if (!window.fetch || window.__jzoFetchWatched) return;
    window.__jzoFetchWatched = true;
    var nativeFetch = window.fetch.bind(window);
    window.fetch = function (input, init) {
      var url = typeof input === "string" ? input : String((input && input.url) || "");
      var method = String((init && init.method) || (input && input.method) || "GET").toUpperCase();
      var payload = init && init.body ? init.body : "";
      return nativeFetch(input, init).then(function (response) {
        if (response.status >= 400) {
          try {
            response.clone().text().then(function (text) {
              if (!window.console || typeof console.error !== "function") return;
              var data = null;
              try { data = text ? JSON.parse(text) : null; } catch (error) { data = null; }
              var lines = [
                "[JZO 请求失败] " + summary({
                  status: response.status, statusText: response.statusText,
                  method: method, url: url, text: text, data: data
                })
              ];
              var sent = payloadText(payload);
              if (sent) lines.push("请求体：" + sent);
              lines.push("响应全文：" + clip(text, MAX_BODY));
              if (response.status === 404) {
                lines.push("诊断：接口未注册——正在跑的底座进程很可能是旧版本，重启一次再试。");
              }
              console.error(lines.join("\n"));
            }).catch(function () { /* 读副本失败不能影响原响应 */ });
          } catch (error) { /* clone 不支持时静默跳过，界面错误仍由 failure() 交代 */ }
        }
        return response;
      });
    };
  }

  window.JzoHttp = {
    failure: failure,
    fromResponse: fromResponse,
    readText: readText,
    detail: detail,
    summary: summary,
    payloadText: payloadText
  };
  installInterceptor();
})();
