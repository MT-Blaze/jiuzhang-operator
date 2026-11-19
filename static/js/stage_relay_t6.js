/* T6 转发家族（转码七链路路由与审核重认）：本地 VLM 安装/进度＋审核重认＋整批打回。
 *
 * 与 stage_relay_io.js 同一套 create(deps) 口径，独立成文件是为了整块下架：
 * 删本文件＋workspace.html 的 script 行＋stage.js 里 relayT6 两处点名即可，
 * 不留残余。写口一律宿主代持一次性令牌；插件只递 sanitized 形状。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var fetchJson = deps.fetchJson;
    var intValue = deps.intValue;
    var replyHost = deps.replyHost;
    var textValue = deps.textValue;
    var withWriteToken = deps.withWriteToken;

    /** relay() 的「T6」分支族：VLM 安装只读/点击发起＋审核重认写口。 */
    function relayT6(ctx) {
      var tab = ctx.tab, message = ctx.message, method = ctx.method, payload = ctx.payload;
      var done = ctx.done, fail = ctx.fail;

      if (method === "models.vlm_status") {
        // 只读：engines/vlm 安装进度（state/step/人话），配置页轮询用。
        fetchJson("/api/models/vlm/status").then(done, fail);
        return true;
      }

      if (method === "models.ocr_status") {
        // 只读：RapidOCR·准权重安装进度（2.20.0 卡§6），配置页轮询用。
        fetchJson("/api/models/ocr/status").then(done, fail);
        return true;
      }

      if (method === "models.formula_status") {
        // 只读：PP-FormulaNet·M 权重安装进度（2.22.0 卡§2），配置页轮询用。
        fetchJson("/api/models/formula/status").then(done, fail);
        return true;
      }

      if (method === "pending.reidentify_spans") {
        // 只读：公式块清单（坐标来源 MinerU 公式块/文字层），审核渲染列画块级钮用。
        var readPerms = (tab.plugin && tab.plugin.permissions) || [];
        if (readPerms.indexOf("questions:read") < 0) {
          replyHost(tab, message, false, { code: "FORBIDDEN",
            message: "插件未声明 questions:read 权限，不能读取重认公式块" });
          return true;
        }
        var spanPid = textValue(payload || {}, "pending_id", 80);
        if (!/^p_[A-Za-z0-9_-]{8,64}$/.test(spanPid)) {
          replyHost(tab, message, false, { code: "BAD_REQUEST", message: "中转站编号不合法" });
          return true;
        }
        fetchJson("/api/pending/reidentify/spans?pending_id=" + encodeURIComponent(spanPid))
          .then(done, fail);
        return true;
      }

      if (method === "models.vlm_install") {
        // 写口：安装会出网（老师点击才发起），要写令牌＋questions:write。
        var installPerms = (tab.plugin && tab.plugin.permissions) || [];
        if (installPerms.indexOf("questions:write") < 0) {
          replyHost(tab, message, false, { code: "FORBIDDEN",
            message: "插件未声明 questions:write 权限，不能发起本地 VLM 安装" });
          return true;
        }
        withWriteToken("/api/models/vlm/install", { method: "POST",
          headers: { "Content-Type": "application/json" }, body: "{}" }).then(done, fail);
        return true;
      }

      if (method === "models.ocr_install") {
        // 写口：准档权重下载会出网（老师点击才发起），要写令牌＋questions:write。
        var ocrPerms = (tab.plugin && tab.plugin.permissions) || [];
        if (ocrPerms.indexOf("questions:write") < 0) {
          replyHost(tab, message, false, { code: "FORBIDDEN",
            message: "插件未声明 questions:write 权限，不能发起 RapidOCR 准档安装" });
          return true;
        }
        withWriteToken("/api/models/ocr/install", { method: "POST",
          headers: { "Content-Type": "application/json" }, body: "{}" }).then(done, fail);
        return true;
      }

      if (method === "models.formula_install") {
        // 写口：PP-FormulaNet·M 权重下载会出网（老师点击才发起），要写令牌＋questions:write。
        var formulaPerms = (tab.plugin && tab.plugin.permissions) || [];
        if (formulaPerms.indexOf("questions:write") < 0) {
          replyHost(tab, message, false, { code: "FORBIDDEN",
            message: "插件未声明 questions:write 权限，不能发起 PP-FormulaNet·M 安装" });
          return true;
        }
        withWriteToken("/api/models/formula/install", { method: "POST",
          headers: { "Content-Type": "application/json" }, body: "{}" }).then(done, fail);
        return true;
      }

      if (method === "models.uninstall_vlm" || method === "models.uninstall_mineru" ||
          method === "models.uninstall_ocr" || method === "models.uninstall_formula") {
        // 写口：卸载先停服/丢缓存再删 engines/ 目录（老师点击＋确认发起），要写令牌＋questions:write。
        var uninstallPerms = (tab.plugin && tab.plugin.permissions) || [];
        if (uninstallPerms.indexOf("questions:write") < 0) {
          replyHost(tab, message, false, { code: "FORBIDDEN",
            message: "插件未声明 questions:write 权限，不能卸载本地引擎" });
          return true;
        }
        var uninstallPaths = { "models.uninstall_vlm": "/api/models/vlm/uninstall",
          "models.uninstall_mineru": "/api/models/mineru/uninstall",
          "models.uninstall_ocr": "/api/models/ocr/uninstall",
          "models.uninstall_formula": "/api/models/formula/uninstall" };
        withWriteToken(uninstallPaths[method], { method: "POST",
          headers: { "Content-Type": "application/json" }, body: "{}" }).then(done, fail);
        return true;
      }

      if (method === "pending.reidentify") {
        // 写口：同张题图裁块/整题送选中席，原位替换；失败进批次失败清单。
        var perms = (tab.plugin && tab.plugin.permissions) || [];
        if (perms.indexOf("questions:write") < 0) {
          replyHost(tab, message, false, { code: "FORBIDDEN",
            message: "插件未声明 questions:write 权限，不能发起审核重认" });
          return true;
        }
        var body = {
          pending_id: textValue(payload || {}, "pending_id", 80),
          seat: textValue(payload || {}, "seat", 80),
          target: textValue(payload || {}, "target", 20) || "question",
          span_index: intValue(payload || {}, "span_index", 0, 0, 31)
        };
        // 单题重认最长等 15 分钟（MinerU/VLM 排队属预期）：转发超时放宽到 16 分钟。
        withWriteToken("/api/pending/reidentify", { method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body), timeout: 960000 }).then(done, fail);
        return true;
      }

      if (method === "pending.return_batch") {
        // 写口：整批打回收集框（源文件＋元数据原样），未入库随批作废、已入库留库。
        var returnPerms = (tab.plugin && tab.plugin.permissions) || [];
        if (returnPerms.indexOf("questions:write") < 0) {
          replyHost(tab, message, false, { code: "FORBIDDEN",
            message: "插件未声明 questions:write 权限，不能整批打回重新识别" });
          return true;
        }
        var returnBody = { batch_id: textValue(payload || {}, "batch_id", 40) };
        withWriteToken("/api/pending/return_batch", { method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(returnBody), timeout: 120000 }).then(done, fail);
        return true;
      }

      return false;
    }

    return { relayT6: relayT6 };
  }

  global.JzoStageRelayT6 = { create: create };
})(window);