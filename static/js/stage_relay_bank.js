/**
 * stage_relay_bank.js —— stage.js 的「541」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：底座 JS 单文件不超 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var ID_RE = deps.ID_RE;
    var TOPIC_ID_RE = deps.TOPIC_ID_RE;
    var bankProviderBase = deps.bankProviderBase;
    var emit = deps.emit;
    var fetchJson = deps.fetchJson;
    var filterValue = deps.filterValue;
    var intValue = deps.intValue;
    var loadBankProvider = deps.loadBankProvider;
    var noteBasketChange = deps.noteBasketChange;
    var plainObject = deps.plainObject;
    var replyHost = deps.replyHost;
    var sourceList = deps.sourceList;
    var stageState = deps.stageState;
    var textValue = deps.textValue;
    var withWriteToken = deps.withWriteToken;

  /** relay() 的「Ingest」分支族：不属本族立刻返回 false，办完返回 true。 */
  function relayIngest(ctx) {
    var tab = ctx.tab, message = ctx.message, method = ctx.method, payload = ctx.payload;
    var pluginId = ctx.pluginId, base = ctx.base, sharedBase = ctx.sharedBase;
    var done = ctx.done, fail = ctx.fail, failWith = ctx.failWith;
    var emitPendingUpdated = ctx.emitPendingUpdated;

    if (method !== "ingest.files") return false;

    if (method === "ingest.files") {
      // 拖入/粘贴进来的文件：插件把字节交给宿主，宿主代发（写令牌不出宿主）。
      var ingestPermissions = (tab.plugin && tab.plugin.permissions) || [];
      if (ingestPermissions.indexOf("questions:write") < 0) {
        replyHost(tab, message, false, {
          code: "FORBIDDEN",
          message: "插件未声明 questions:write 权限，不能往中转站塞文件"
        });
        return true;
      }
      var incoming = payload.files;
      if (!Array.isArray(incoming) || !incoming.length) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "缺少待解析的文件数组" });
        return true;
      }
      var prepared = [];
      for (var i = 0; i < incoming.length && prepared.length < 20; i += 1) {
        var entry = plainObject(incoming[i]);
        var fileName = textValue(entry, "name", 120);
        var fileUrl = typeof entry.data_url === "string" ? entry.data_url : "";
        if (!fileName || !fileUrl) continue;
        if (fileUrl.length > 48 * 1024 * 1024) continue;
        prepared.push({ name: fileName, data_url: fileUrl });
      }
      if (!prepared.length) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "没有可解析的文件" });
        return true;
      }
      var intake = window.JzoIntake;
      if (!intake || typeof intake.ingestEntries !== "function") {
        replyHost(tab, message, false, { code: "HOST_MISSING", message: "宿主没有录入通道" });
        return true;
      }
      var layoutEngine = textValue(payload, "layout_engine", 16) || "auto";
      if (["auto", "yolo", "cloud"].indexOf(layoutEngine) < 0) layoutEngine = "auto";
      var recognizeEngine = textValue(payload, "recognize_engine", 16)
        || textValue(payload, "channel", 16) || "auto";
      // 老调用方仍发 local_ai：归到自动识别，不再单独占一种模式。
      if (["auto", "full_ocr", "mineru"].indexOf(recognizeEngine) < 0) {
        recognizeEngine = "auto";
      }
      intake.ingestEntries(prepared, {
        silent: true,
        layout_engine: layoutEngine,
        recognize_engine: recognizeEngine
      }).then(function (result) {
        emitPendingUpdated("ingest", (result && result.saved_ids) || [], result);
        done(result);
      }, fail);
      return true;
    }

    return false;
  }

  /** relay() 的「Bank」分支族：不属本族立刻返回 false，办完返回 true。 */
  function relayBank(ctx) {
    var tab = ctx.tab, message = ctx.message, method = ctx.method, payload = ctx.payload;
    var pluginId = ctx.pluginId, base = ctx.base, sharedBase = ctx.sharedBase;
    var done = ctx.done, fail = ctx.fail, failWith = ctx.failWith;
    var emitPendingUpdated = ctx.emitPendingUpdated;

    if (method.indexOf("bank.") !== 0) return false;

    if (method === "bank.create") {
      var permissions = (tab.plugin && tab.plugin.permissions) || [];
      if (permissions.indexOf("questions:write") < 0) {
        replyHost(tab, message, false, {
          code: "FORBIDDEN",
          message: "插件未声明 questions:write 权限，不能写入题库"
        });
        return true;
      }
      var question = payload.question;
      if (!question || typeof question !== "object" || Array.isArray(question)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "缺少待写入的 question 对象" });
        return true;
      }
      var createSources = sourceList(payload);
      if (!createSources.ok) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: createSources.message });
        return true;
      }
      var createBody = { question: question };
      if (createSources.items !== undefined) createBody.sources = createSources.items;
      withWriteToken(
        bankProviderBase() + "/questions",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(createBody)
        }
      ).then(function (result) {
        emit("system.question_updated", {
          action: "create",
          id: result && result.id,
          pluginId: tab.plugin.id
        });
        done(result);
      }, fail);
      return true;
    }

    if (method === "bank.update") {
      // 人工审核页的一键修复：与新增同权——必须先声明 questions:write，令牌仍留在宿主侧
      var writePermissions = (tab.plugin && tab.plugin.permissions) || [];
      if (writePermissions.indexOf("questions:write") < 0) {
        replyHost(tab, message, false, {
          code: "FORBIDDEN",
          message: "插件未声明 questions:write 权限，不能修改题库"
        });
        return true;
      }
      var targetId = textValue(payload, "id", 80);
      if (!ID_RE.test(targetId)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "待修改的题目 id 不合法" });
        return true;
      }
      var patch = payload.question;
      if (!patch || typeof patch !== "object" || Array.isArray(patch)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "缺少待写入的 question 对象" });
        return true;
      }
      var updateSources = sourceList(payload);
      if (!updateSources.ok) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: updateSources.message });
        return true;
      }
      var updateBody = { question: patch };
      if (updateSources.items !== undefined) updateBody.sources = updateSources.items;
      withWriteToken(
        bankProviderBase() + "/questions/"
          + encodeURIComponent(targetId),
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(updateBody)
        }
      ).then(function (result) {
        emit("system.question_updated", {
          action: "update",
          id: result && result.id,
          pluginId: tab.plugin.id
        });
        done(result);
      }, fail);
      return true;
    }

    if (method === "bank.delete") {
      // 删题与新增同权：必须先声明 questions:write，令牌仍留在宿主侧，插件不碰。
      var deletePermissions = (tab.plugin && tab.plugin.permissions) || [];
      if (deletePermissions.indexOf("questions:write") < 0) {
        replyHost(tab, message, false, {
          code: "FORBIDDEN",
          message: "插件未声明 questions:write 权限，不能删除题库题目"
        });
        return true;
      }
      var deleteId = textValue(payload, "id", 80);
      if (!ID_RE.test(deleteId)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "待删除的题目 id 不合法" });
        return true;
      }
      withWriteToken(
        bankProviderBase() + "/questions/"
          + encodeURIComponent(deleteId),
        { method: "DELETE" }
      ).then(function (result) {
        emit("system.question_updated", {
          action: "delete",
          id: (result && result.id) || deleteId,
          pluginId: tab.plugin.id
        });
        done(result);
      }, fail);
      return true;
    }

    if (method === "bank.review") {
      var reviewParams = new URLSearchParams();
      var flag = filterValue(payload, "flag", 32);
      if (flag && flag !== "全部") reviewParams.set("flag", flag);
      reviewParams.set("page", String(intValue(payload, "page", 1, 1, 10000)));
      reviewParams.set("page_size", String(intValue(payload, "page_size", 20, 1, 100)));
      fetchJson(sharedBase + "/review?" + reviewParams.toString()).then(done, fail);
      return true;
    }

    if (method === "bank.stats" || method === "bank.active_stats") {
      // 浏览型插件没有自己的题库：显式要「活跃题库」的计数，不拿页签 id 去猜库
      fetchJson((method === "bank.active_stats" ? sharedBase : base) + "/stats").then(done, fail);
      return true;
    }

    // 数据看板两条只读通道：全局端点，跟页签自己的库无关，永远读活跃题库
    if (method === "bank.dashboard_stats") {
      fetchJson("/api/bank/dashboard/stats").then(done, fail);
      return true;
    }

    if (method === "bank.dashboard_heatmap") {
      fetchJson("/api/bank/dashboard/heatmap").then(done, fail);
      return true;
    }

    if (method === "bank.list" || method === "bank.active_list") {
      var params = new URLSearchParams();
      params.set("grade", filterValue(payload, "grade", 32));
      params.set("difficulty", filterValue(payload, "difficulty", 32));
      params.set("type", filterValue(payload, "type", 32));
      params.set("chapter", filterValue(payload, "chapter", 64));
      params.set("textbook", filterValue(payload, "textbook", 64));
      var topic = textValue(payload, "topic", 20);
      if (topic && !TOPIC_ID_RE.test(topic)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "考向节点 id 不合法" });
        return true;
      }
      if (topic) params.set("topic", topic);
      var search = textValue(payload, "q", 100);
      if (search) params.set("q", search);
      params.set("page", String(intValue(payload, "page", 1, 1, 10000)));
      params.set("page_size", String(intValue(payload, "page_size", 20, 1, 100)));
      // active_list 与 bank.get / bank.topics 同源：浏览端永远看当前活跃题库
      var listBase = method === "bank.active_list" ? sharedBase : base;
      fetchJson(listBase + "/questions?" + params.toString()).then(done, fail);
      return true;
    }

    if (method === "bank.get") {
      var questionId = textValue(payload, "id", 80);
      if (!ID_RE.test(questionId)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "题目 id 不合法" });
        return true;
      }
      fetchJson(sharedBase + "/questions/" + encodeURIComponent(questionId)).then(done, fail);
      return true;
    }

    if (method === "bank.random") {
      var randomParams = new URLSearchParams();
      randomParams.set("grade", filterValue(payload, "grade", 32));
      randomParams.set("difficulty", filterValue(payload, "difficulty", 32));
      randomParams.set("type", filterValue(payload, "type", 32));
      var randomSearch = textValue(payload, "q", 100);
      if (randomSearch) randomParams.set("q", randomSearch);
      var randomTopic = textValue(payload, "topic", 20);
      if (randomTopic) {
        if (!TOPIC_ID_RE.test(randomTopic)) {
          replyHost(tab, message, false, { code: "BAD_REQUEST", message: "考向节点 id 不合法" });
          return true;
        }
        randomParams.set("topic", randomTopic);
      }
      fetchJson(base + "/random?" + randomParams.toString()).then(done, fail);
      return true;
    }

    if (method === "bank.topics") {
      var topicParams = new URLSearchParams();
      var parentId = textValue(payload, "parent_id", 20);
      if (parentId && !TOPIC_ID_RE.test(parentId)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "大纲节点 parent_id 不合法" });
        return true;
      }
      if (parentId) topicParams.set("parent_id", parentId);
      var topicSearch = textValue(payload, "q", 100);
      if (topicSearch) topicParams.set("q", topicSearch);
      fetchJson(sharedBase + "/topics?" + topicParams.toString()).then(done, fail);
      return true;
    }

    if (method === "bank.topic_notes") {
      var noteTopic = textValue(payload, "topic_id", 20);
      if (!TOPIC_ID_RE.test(noteTopic)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "考向节点 topic_id 不合法" });
        return true;
      }
      fetchJson(sharedBase + "/topics/" + encodeURIComponent(noteTopic) + "/notes").then(done, fail);
      return true;
    }

    if (method === "bank.sources") {
      var sourceQuestionId = textValue(payload, "id", 80);
      if (!ID_RE.test(sourceQuestionId)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "题目 id 不合法" });
        return true;
      }
      fetchJson(sharedBase + "/questions/" + encodeURIComponent(sourceQuestionId) + "/sources")
        .then(done, fail);
      return true;
    }

    return false;
  }

  /** relay() 的「Basket」分支族：不属本族立刻返回 false，办完返回 true。 */
  function relayBasket(ctx) {
    var tab = ctx.tab, message = ctx.message, method = ctx.method, payload = ctx.payload;
    var pluginId = ctx.pluginId, base = ctx.base, sharedBase = ctx.sharedBase;
    var done = ctx.done, fail = ctx.fail, failWith = ctx.failWith;
    var emitPendingUpdated = ctx.emitPendingUpdated;

    if (method.indexOf("basket.") !== 0) return false;

    if (method === "basket.list") {
      fetchJson("/api/basket?expand=" + (payload.expand === true ? "true" : "false")).then(done, fail);
      return true;
    }

    if (method === "basket.add" || method === "basket.active_add") {
      var ids = payload.ids;
      if (typeof payload.id === "string") ids = [payload.id];
      if (!Array.isArray(ids) || !ids.length) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "ids 必须是非空数组" });
        return true;
      }
      if (ids.length > 200) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "一次最多加 200 题" });
        return true;
      }
      var cleanIds = [];
      for (var i = 0; i < ids.length; i += 1) {
        var id = typeof ids[i] === "string" ? ids[i] : "";
        if (!ID_RE.test(id)) {
          replyHost(tab, message, false, { code: "BAD_REQUEST", message: "题目 id 不合法" });
          return true;
        }
        cleanIds.push(id);
      }
      // 题篮条目按「题库归属」记账：浏览型插件自己没有库，就要把题目记在当前
      // 活跃 provider 名下，否则读题篮时找不到全文（与 bank.active_list 同源）。
      var basketOwner = pluginId;
      if (method === "basket.active_add") basketOwner = stageState.bankProviderId;
      var addToBasket = function () {
        withWriteToken("/api/basket", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ plugin_id: basketOwner, ids: cleanIds })
        }).then(function (result) {
          done(result);
          noteBasketChange(tab, "add", result, cleanIds.length);
        }, fail);
      };
      if (method === "basket.active_add") {
        loadBankProvider().then(addToBasket, addToBasket);
      } else {
        addToBasket();
      }
      return true;
    }

    if (method === "basket.remove") {
      var removeId = textValue(payload, "question_id", 80) || textValue(payload, "id", 80);
      if (!ID_RE.test(removeId)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "题目 id 不合法" });
        return true;
      }
      withWriteToken("/api/basket/" + encodeURIComponent(removeId), { method: "DELETE" })
        .then(function (result) {
          done(result);
          noteBasketChange(tab, "remove", result, 1);
        }, fail);
      return true;
    }

    if (method === "basket.clear") {
      withWriteToken("/api/basket", { method: "DELETE" }).then(function (result) {
        done(result);
        noteBasketChange(tab, "clear", result, 0);
      }, fail);
      return true;
    }

    return false;
  }

    return {
      relayBank: relayBank,
      relayBasket: relayBasket,
      relayIngest: relayIngest,
    };
  }

  global.JzoStageRelayBank = { create: create };
})(window);
