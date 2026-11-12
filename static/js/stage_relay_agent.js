/**
 * stage_relay_agent.js —— stage.js 的「智能体接口」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：底座 JS 单文件不超 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var AGENT_TIMEOUT_MS = deps.AGENT_TIMEOUT_MS;
    var ID_RE = deps.ID_RE;
    var OPEN_BANK_QUERY_MAX = deps.OPEN_BANK_QUERY_MAX;
    var broadcast = deps.broadcast;
    var dock = deps.dock;
    var fetchJson = deps.fetchJson;
    var openBank = deps.openBank;
    var openEditor = deps.openEditor;
    var plainObject = deps.plainObject;
    var textValue = deps.textValue;
    var urlValue = deps.urlValue;
    var withWriteToken = deps.withWriteToken;

  // 四个任务键与底座 ai_center.TASKS 同名单；账号 id 形状与底座 ACCOUNT_ID_RE 一致。
  var AI_TASKS = ["ocr", "solve", "meta", "tikz", "mineru"];
  var ACCOUNT_ID_RE = /^acc_[0-9a-f]{10}$/;
  var AI_RECOGNIZE_TIMEOUT_MS = 125000;

  /**
   * 智能体接口（2026-11-05 起只保留 AI 帮改与配置中心）。插件不能读库、不能碰宿主 DOM、
   * 更没有鼠标键盘——所有「改写 / 装插件 / 开页签 / 改面板」都只能到这里，
   * 由宿主用它自己的身份去做，做完把结果摘要回给插件。
   */
  function relayAgent(method, payload, done, fail, failWith) {
    var jsonHeaders = { "Content-Type": "application/json" };

    if (method === "agent.refine") {
      var instruction = textValue(payload, "instruction", 400);
      if (!instruction) { failWith("BAD_REQUEST", "instruction 不能为空"); return; }
      fetchJson("/api/agent/refine", {
        method: "POST",
        headers: jsonHeaders,
        timeout: AGENT_TIMEOUT_MS,
        body: JSON.stringify({
          question: plainObject(payload.question),
          instruction: instruction,
          field: textValue(payload, "field", 20) === "solution" ? "solution" : "stem",
          task_id: textValue(payload, "task_id", 60) || "refine_" + Date.now()
        })
      }).then(function (response) {
        // 后端把正文埋在 data / fallback 里：摊平成 {value, note, field}，插件不必猜信封
        var data = plainObject(response && response.data);
        var envelope = data.value === undefined ? plainObject(response && response.fallback) : data;
        done({
          ok: !(response && response.type === "error"),
          field: textValue(envelope, "field", 20) || "stem",
          value: textValue(envelope, "value", 20000),
          note: textValue(envelope, "note", 300)
        });
      }, fail);
      return;
    }

    if (method === "plugins.list") {
      fetchJson("/api/plugins").then(function (data) {
        done({
          plugins: ((data && data.plugins) || []).map(function (item) {
            return {
              id: item.id,
              name: item.name,
              version: item.version,
              kind: item.kind,
              description: textValue(item, "description", 200),
              capabilities: item.capabilities || [],
              slots: item.slots || [],
              enabled: item.enabled !== false
            };
          })
        });
      }, fail);
      return;
    }

    if (method === "workspace.state") {
      var snapshot = window.JzoWorkspace && typeof window.JzoWorkspace.stateSnapshot === "function"
        ? window.JzoWorkspace.stateSnapshot() : null;
      if (!snapshot) { failWith("NOT_READY", "宿主工作区快照尚未就绪"); return; }
      done(snapshot);
      return;
    }

    if (method === "plugin.install_url") {
      // 与索引页【在线安装】完全同款的落地校验；令牌仍由宿主代取，插件不可见。
      var zipUrl = urlValue(payload.url, 500);
      if (!zipUrl) { failWith("BAD_URL", "只允许 http(s) 直链"); return; }
      var mirrors = (Array.isArray(payload.mirrors) ? payload.mirrors : [])
        .map(function (item) { return urlValue(item, 500); })
        .filter(Boolean).slice(0, 6);
      withWriteToken("/api/plugins/install-url", {
        method: "POST",
        headers: jsonHeaders,
        timeout: AGENT_TIMEOUT_MS,
        body: JSON.stringify({
          url: zipUrl, mirrors: mirrors, replace: payload.replace === true
        })
      }).then(function (result) {
        if (window.JzoWorkspace && typeof window.JzoWorkspace.refreshPlugins === "function") {
          window.JzoWorkspace.refreshPlugins();
        }
        done(result);
      }, function (error) {
        if (error && error.status === 409) {
          failWith("PLUGIN_EXISTS",
            String((error.detail && error.detail.message) || error.message || "插件已安装"), false);
          return;
        }
        fail(error);
      });
      return;
    }

    if (method === "ui.params.set") {
      if (!window.JzoWorkspace || typeof window.JzoWorkspace.applyAiParams !== "function") {
        failWith("NOT_READY", "宿主面板仲裁器未就绪");
        return;
      }
      var outcome = window.JzoWorkspace.applyAiParams(
        payload.params, payload.snapshot, textValue(payload, "plugin_id", 80));
      if (outcome && outcome.error) {
        failWith(outcome.error.code || "PARAM_REJECTED", outcome.error.message);
        return;
      }
      done(outcome);
      return;
    }

    if (method === "editor.apply_patch") {
      var patchValue = textValue(payload, "value", 20000);
      if (!patchValue) { failWith("BAD_REQUEST", "回填内容为空"); return; }
      var patchField = textValue(payload, "field", 20);
      if (patchField !== "solution" && patchField !== "answer") patchField = "stem";
      var patch = {
        id: textValue(payload, "id", 80),
        field: patchField,
        value: patchValue
      };
      broadcast("editor.apply_patch", patch);
      var patchLabel = patch.field === "solution" ? "解析" : patch.field === "answer" ? "答案" : "题干";
      dock("辅助栏请求把改写的" + patchLabel + "回填到录题表单。", "agent.patch");
      done({ ok: true, field: patch.field, id: patch.id });
      return;
    }

    if (method === "stage.open_bank") {
      var bankQuery = textValue(payload, "query", OPEN_BANK_QUERY_MAX);
      var bankQuestionId = textValue(payload, "question_id", 80);
      if (!ID_RE.test(bankQuestionId)) bankQuestionId = "";
      openBank({
        pluginId: "agent",
        raw: { query: bankQuery, question_id: bankQuestionId }
      });
      done({ ok: true, query: bankQuery, question_id: bankQuestionId });
      return;
    }

    if (method === "stage.open_editor") {
      var editorQuestionId = textValue(payload, "question_id", 80);
      if (!editorQuestionId) { failWith("BAD_REQUEST", "question_id 不能为空"); return; }
      openEditor({ pluginId: "agent", raw: { question_id: editorQuestionId } });
      done({ ok: true, question_id: editorQuestionId });
      return;
    }

    // ---------- AI 配置中心 ----------
    // 密钥池只回掩码；Key 原文只从插件表单进来、由宿主直送底座落 .env，
    // 既不回填到插件，也不进任何日志。改账号时 api_key 留空＝保留旧 Key。
    if (method === "ai.center") {
      fetchJson("/api/ai-center").then(done, fail);
      return;
    }

    if (method === "ai.account_save") {
      var accountName = textValue(payload, "name", 40);
      var accountBase = urlValue(payload.base_url, 512);
      var accountId = textValue(payload, "id", 64);
      if (!accountName) { failWith("BAD_REQUEST", "账号名称不能为空"); return; }
      if (!accountBase) { failWith("BAD_URL", "Base URL 必须是 http(s) 直链"); return; }
      if (accountId && !ACCOUNT_ID_RE.test(accountId)) {
        failWith("BAD_REQUEST", "账号 id 形状不对");
        return;
      }
      var accountBody = { name: accountName, base_url: accountBase };
      if (accountId) accountBody.id = accountId;
      // 没填 Key 就不发这个字段：后端按「保留旧 Key」处理，绝不用空串覆盖。
      if (typeof payload.api_key === "string") {
        accountBody.api_key = payload.api_key.trim().slice(0, 512);
      }
      withWriteToken("/api/ai-center/accounts", {
        method: "POST",
        headers: jsonHeaders,
        timeout: AGENT_TIMEOUT_MS,
        body: JSON.stringify(accountBody)
      }).then(done, fail);
      return;
    }

    if (method === "ai.account_delete") {
      var deleteId = textValue(payload, "account_id", 64);
      if (!ACCOUNT_ID_RE.test(deleteId)) { failWith("BAD_REQUEST", "账号 id 形状不对"); return; }
      withWriteToken("/api/ai-center/accounts/" + encodeURIComponent(deleteId), {
        method: "DELETE",
        headers: jsonHeaders,
        timeout: AGENT_TIMEOUT_MS
      }).then(done, fail);
      return;
    }

    if (method === "ai.assign") {
      var assignTaskKey = textValue(payload, "task", 16);
      var assignAccount = textValue(payload, "account_id", 64);
      var assignModel = textValue(payload, "model", 128);
      if (AI_TASKS.indexOf(assignTaskKey) < 0) { failWith("BAD_REQUEST", "未知任务"); return; }
      if (!ACCOUNT_ID_RE.test(assignAccount)) { failWith("BAD_REQUEST", "账号 id 形状不对"); return; }
      if (!assignModel) { failWith("BAD_REQUEST", "模型名不能为空；下拉里没有就手动输入"); return; }
      withWriteToken("/api/ai-center/assign", {
        method: "POST",
        headers: jsonHeaders,
        timeout: AGENT_TIMEOUT_MS,
        body: JSON.stringify({ task: assignTaskKey, account_id: assignAccount, model: assignModel })
      }).then(done, fail);
      return;
    }

    if (method === "ai.models") {
      var modelAccount = textValue(payload, "account_id", 64);
      if (modelAccount && !ACCOUNT_ID_RE.test(modelAccount)) {
        failWith("BAD_REQUEST", "账号 id 形状不对");
        return;
      }
      var modelBase = urlValue(payload.base_url, 512);
      if (!modelAccount && !modelBase) {
        failWith("BAD_REQUEST", "先保存账号，或填 Base URL 与 Key 再拉模型");
        return;
      }
      withWriteToken("/api/ai-center/models", {
        method: "POST",
        headers: jsonHeaders,
        timeout: AGENT_TIMEOUT_MS,
        body: JSON.stringify({
          account_id: modelAccount,
          base_url: modelAccount ? "" : modelBase,
          api_key: typeof payload.api_key === "string" ? payload.api_key.trim().slice(0, 512) : ""
        })
      }).then(done, fail);
      return;
    }

    // 单题识别：只回结构化正文与底座套好的 exam-zh 源码，插件不碰 \begin 环境拼装。
    // 模型一轮可能要几十秒，超时放宽到与后端 120 秒同一量级。
    if (method === "ai.recognize") {
      var rawImages = Array.isArray(payload.images) ? payload.images : [];
      var images = [];
      for (var index = 0; index < rawImages.length && images.length < 3; index += 1) {
        var uri = textValue({ v: rawImages[index] }, "v", 20000);
        if (uri) images.push(uri);
      }
      // ocr 必须带题图；solve 只补答案与解析，题干走 context，不强制题图。
      var aiTask = textValue(payload, "task", 16) === "solve" ? "solve" : "ocr";
      if (aiTask === "ocr" && !images.length) {
        failWith("BAD_REQUEST", "这道题没有可识别的题图");
        return;
      }
      withWriteToken("/api/ai-center/recognize", {
        method: "POST",
        headers: jsonHeaders,
        timeout: AI_RECOGNIZE_TIMEOUT_MS,
        body: JSON.stringify({
          images: images,
          context: plainObject(payload.context),
          task: aiTask
        })
      }).then(done, fail);
      return;
    }

    failWith("UNSUPPORTED_METHOD", "宿主未开放方法：" + String(method).slice(0, 60));
  }

    return {
      relayAgent: relayAgent,
    };
  }

  global.JzoStageRelayAgent = { create: create };
})(window);
