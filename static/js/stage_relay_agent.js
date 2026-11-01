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
    var CHAT_HISTORY_MAX = deps.CHAT_HISTORY_MAX;
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

  /** 历史轮次只留 role/content 两个字符串字段，长度设限——模型不必看见插件的内部态。 */
  function cleanHistory(value) {
    if (!Array.isArray(value)) return [];
    return value.slice(-CHAT_HISTORY_MAX)
      .map(function (turn) {
        var item = plainObject(turn);
        var role = textValue(item, "role", 10);
        if (role !== "assistant" && role !== "sys") role = "user";
        return { role: role, content: textValue(item, "content", 2000) };
      })
      .filter(function (turn) { return turn.content; });
  }

  /**
   * 智能体接口（军令 #15）。AI 助手是一个普通插件：它不能读库、不能碰宿主 DOM、
   * 更没有鼠标键盘——所有「查题库 / 开页签 / 改面板 / 装插件」都只能到这里，
   * 由宿主用它自己的身份去做，做完把结果摘要回给插件。
   */
  function relayAgent(method, payload, done, fail, failWith) {
    var jsonHeaders = { "Content-Type": "application/json" };

    if (method === "agent.chat") {
      var userInput = textValue(payload, "user_input", 4000);
      if (!userInput) { failWith("BAD_REQUEST", "user_input 不能为空"); return; }
      fetchJson("/api/agent/chat", {
        method: "POST",
        headers: jsonHeaders,
        timeout: AGENT_TIMEOUT_MS,
        body: JSON.stringify({
          user_input: userInput,
          task_id: textValue(payload, "task_id", 60) || "chat_" + Date.now(),
          context: plainObject(payload.context),
          history: cleanHistory(payload.history)
        })
      }).then(done, fail);
      return;
    }

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
      var patch = {
        id: textValue(payload, "id", 80),
        field: textValue(payload, "field", 20) === "solution" ? "solution" : "stem",
        value: patchValue
      };
      broadcast("editor.apply_patch", patch);
      dock("AI 助手请求把改写的" + (patch.field === "solution" ? "解析" : "题干") + "回填到录题表单。",
        "agent.patch");
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

    failWith("UNSUPPORTED_METHOD", "宿主未开放方法：" + String(method).slice(0, 60));
  }

    return {
      cleanHistory: cleanHistory,
      relayAgent: relayAgent,
    };
  }

  global.JzoStageRelayAgent = { create: create };
})(window);
