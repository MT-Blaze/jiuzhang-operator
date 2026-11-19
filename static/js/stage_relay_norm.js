/**
 * stage_relay_norm.js —— 记号标准字典（闭集＋开集）的宿主转发族（2.21.0 卡 §4）。
 *
 * 整机库 data/latex_norm.db 住底座，插件在沙箱里摸不到：读开放、写带一次性令牌。
 * 闭集内容出厂冻结，老师只写选择（choose/reset）；开集只有 pending 可裁决（decide）。
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM（先例 stage_relay_io.js）。
 */
(function (global) {
  "use strict";

  // 开集四态：读侧过滤只认这四个，别的值一律当「没传」，绝不猜一个态。
  var CORRECTION_STATUSES = ["pending", "confirmed", "rejected", "archived"];
  // 人闸裁决只收两个动作；confirmed 必须带目标代码，rejected 进黑名单（后端再校验）。
  var DECISIONS = ["confirmed", "rejected"];

  function create(deps) {
    var fetchJson = deps.fetchJson;
    var withWriteToken = deps.withWriteToken;
    var replyHost = deps.replyHost;
    var textValue = deps.textValue;
    var intValue = deps.intValue;

    /** relay() 的「Norm」分支族：不属本族立刻返回 false，办完返回 true。 */
    function relayNorm(ctx) {
      var tab = ctx.tab, message = ctx.message, method = ctx.method, payload = ctx.payload;
      var done = ctx.done, fail = ctx.fail, failWith = ctx.failWith;

      if (method.indexOf("norm.") !== 0) return false;

      if (method === "norm.list" || method === "norm.corrections") {
        // 字典读：闭集条目＋变体行、开集候选＋四态计数。任何有 questions:read 的插件都能查。
        var readPerms = (tab.plugin && tab.plugin.permissions) || [];
        if (readPerms.indexOf("questions:read") < 0) {
          replyHost(tab, message, false, {
            code: "FORBIDDEN",
            message: "插件未声明 questions:read 权限，不能读记号标准字典"
          });
          return true;
        }
        if (method === "norm.list") {
          fetchJson("/api/norm/entries").then(done, fail);
          return true;
        }
        var status = textValue(payload, "status", 20);
        var query = CORRECTION_STATUSES.indexOf(status) >= 0
          ? "?status=" + encodeURIComponent(status) : "";
        fetchJson("/api/norm/corrections" + query).then(done, fail);
        return true;
      }

      if (method === "norm.choose" || method === "norm.reset" || method === "norm.decide") {
        // 字典写：选默认字形、恢复出厂、开集裁决。令牌照旧只在宿主手里。
        var writePerms = (tab.plugin && tab.plugin.permissions) || [];
        if (writePerms.indexOf("questions:write") < 0) {
          replyHost(tab, message, false, {
            code: "FORBIDDEN",
            message: "插件未声明 questions:write 权限，不能改记号标准字典"
          });
          return true;
        }
        var headers = { "Content-Type": "application/json" };
        if (method === "norm.choose") {
          var entryKey = textValue(payload, "entry_key", 80);
          if (!entryKey) {
            failWith("BAD_REQUEST", "缺少记号条目 entry_key");
            return true;
          }
          var variantId = intValue(payload, "variant_id", 0, 1, 100000000);
          if (!variantId) {
            failWith("BAD_REQUEST", "variant_id 必须是正整数");
            return true;
          }
          withWriteToken("/api/norm/choose", {
            method: "POST",
            headers: headers,
            body: JSON.stringify({ entry_key: entryKey, variant_id: variantId })
          }).then(done, fail);
          return true;
        }
        if (method === "norm.reset") {
          var resetKey = textValue(payload, "entry_key", 80);
          if (!resetKey) {
            failWith("BAD_REQUEST", "缺少记号条目 entry_key");
            return true;
          }
          withWriteToken("/api/norm/reset", {
            method: "POST",
            headers: headers,
            body: JSON.stringify({ entry_key: resetKey })
          }).then(done, fail);
          return true;
        }
        var rawCode = textValue(payload, "raw_code", 80);
        var decision = textValue(payload, "decision", 20);
        if (!rawCode) {
          failWith("BAD_REQUEST", "缺少待裁决的原始代码 raw_code");
          return true;
        }
        if (DECISIONS.indexOf(decision) < 0) {
          failWith("BAD_REQUEST", "裁决只认 confirmed / rejected");
          return true;
        }
        var decideBody = { raw_code: rawCode, decision: decision };
        var targetCode = textValue(payload, "target_code", 80);
        if (targetCode) decideBody.target_code = targetCode;
        withWriteToken("/api/norm/decide", {
          method: "POST",
          headers: headers,
          body: JSON.stringify(decideBody)
        }).then(done, fail);
        return true;
      }

      return false;
    }

    return { relayNorm: relayNorm };
  }

  global.JzoStageRelayNorm = { create: create };
})(window);