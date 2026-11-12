/**
 * 控制台请求客户端：读接口直接 fetch；写接口先取新鲜令牌再发。
 * 令牌一次性轮换（app/core/security.py），所以每次写前都重新 GET /api/settings，
 * 绝不缓存旧令牌。报错统一走 JzoHttp，控制台与【报错诊断】都有完整现场。
 */
(function () {
  "use strict";

  function fetchJson(url, options) {
    var opts = options || {};
    return fetch(url, {
      method: opts.method || "GET",
      headers: opts.headers || {},
      body: opts.body,
      cache: "no-store"
    }).then(function (response) {
      return window.JzoHttp.readText(response, function (text, data) {
        if (!response.ok) {
          throw window.JzoHttp.fromResponse(response, text, data, {
            method: opts.method || "GET", url: url, payload: opts.payload
          });
        }
        return data;
      });
    });
  }

  /** 写请求：当场取令牌 → 带 X-JZO-Token 发出。令牌用后即焚，下次写再取。 */
  function writeJson(url, payload, method) {
    var verb = method || "POST";
    var action = verb === "POST" ? "新增" : (verb === "DELETE" ? "删除" : "修改");
    var table = String(url || "").split("?")[0].split("/").pop();
    return fetchJson("/api/settings").then(function (data) {
      var token = data && data.local_token;
      if (!token) throw new Error("本机未生成就绪令牌：GET /api/settings 没有返回 local_token");
      return fetchJson(url, {
        method: verb,
        headers: { "Content-Type": "application/json", "X-JZO-Token": String(token) },
        body: payload == null ? null : JSON.stringify(payload),
        payload: payload
      });
    }).then(function (result) {
      // 真实业务回执：成功进【运行日志】绿字，不是底座事件。
      if (window.DcOpsLog) window.DcOpsLog.ok("字典" + action + "成功：" + table, "dict." + verb.toLowerCase());
      return result;
    }, function (error) {
      if (window.DcOpsLog) {
        window.DcOpsLog.fail("字典" + action + "失败：" + ((error && error.message) || "未知原因"),
          "dict.error");
      }
      throw error;
    });
  }

  window.DcClient = { fetchJson: fetchJson, writeJson: writeJson };
})();