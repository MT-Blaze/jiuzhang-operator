/**
 * stage_relay_io.js —— stage.js 的「524」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：底座 JS 单文件不超 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var AGENT_TIMEOUT_MS = deps.AGENT_TIMEOUT_MS;
    var CLEAN_TEXT_MAX = deps.CLEAN_TEXT_MAX;
    var emit = deps.emit;
    var fetchBinary = deps.fetchBinary;
    var fetchJson = deps.fetchJson;
    var intValue = deps.intValue;
    var plainObject = deps.plainObject;
    var replyHost = deps.replyHost;
    var textValue = deps.textValue;
    var withWriteToken = deps.withWriteToken;

  // 重题池的四个动作（军令 #32 · 第五步）：与底座 pending_pool.ACTIONS 逐字同集合。
  // 【覆盖】【放弃】已退役，这里不给它们留通道。
  var POOL_ACTIONS = ["merge_metadata", "add_solution", "keep_separate", "delete"];
  var POOL_TIERS = ["strict", "standard", "loose"];

  /** 档位只作读侧过滤：认不得的值一律当「没传」，绝不猜一个档。 */
  function poolTierValue(raw) {
    var tier = String(raw == null ? "" : raw);
    return POOL_TIERS.indexOf(tier) >= 0 ? "?tier=" + tier : "";
  }


  /** relay() 的「Text」分支族：不属本族立刻返回 false，办完返回 true。 */
  function relayText(ctx) {
    var tab = ctx.tab, message = ctx.message, method = ctx.method, payload = ctx.payload;
    var pluginId = ctx.pluginId, base = ctx.base, sharedBase = ctx.sharedBase;
    var done = ctx.done, fail = ctx.fail, failWith = ctx.failWith;
    var emitPendingUpdated = ctx.emitPendingUpdated;

    if (method.indexOf("text.") !== 0 && method.indexOf("asset.") !== 0) return false;

    if (method === "text.clean_latex") {
      // 纯文本规则清洗：宿主只做长度与回包校验。超长直接拒，绝不先截断再回填——
      // 半截文本回到老师表单，比清洗失败更糟。
      var dirtyText = typeof payload.text === "string" ? payload.text : "";
      if (!dirtyText.trim()) { failWith("BAD_REQUEST", "text 不能为空"); return true; }
      if (dirtyText.length > CLEAN_TEXT_MAX) {
        failWith("BAD_REQUEST", "文本过长（上限 " + CLEAN_TEXT_MAX + " 字）");
        return true;
      }
      fetchJson("/api/agent/clean_latex", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // mode 只有两个合法值：contract（默认，#21 口径）与 exam_source（录题源码，
        // 不碰环境骨架）。规则表在底座（latex_style_dict），插件侧一律不自己再写一份。
        body: JSON.stringify({
          text: dirtyText,
          mode: payload.mode === "exam_source" ? "exam_source" : "contract"
        })
      }).then(function (response) {
        var data = plainObject(response && response.data);
        if (typeof data.text !== "string") {
          failWith("HOST_BAD_PAYLOAD", "清洗结果缺少 text 字段");
          return;
        }
        done({
          ok: true,
          text: data.text,
          changed: Boolean(data.changed),
          rules: Array.isArray(data.rules) ? data.rules.slice(0, 12).map(function (rule) {
            return String(rule).slice(0, 20);
          }) : [],
          options: (Array.isArray(data.options) ? data.options : []).slice(0, 8).map(function (item, index) {
            var entry = plainObject(item);
            return {
              key: textValue(entry, "key", 2) || String.fromCharCode(65 + index),
              content: textValue(entry, "content", 2000)
            };
          }).filter(function (item) { return item.content; })
        });
      }, fail);
      return true;
    }

    if (method === "asset.upload") {
      // 框选切图只交 data URL，落盘位置与文件名全由底座决定；插件仍然看不到令牌。
      var assetPermissions = (tab.plugin && tab.plugin.permissions) || [];
      if (assetPermissions.indexOf("assets:write") < 0) {
        replyHost(tab, message, false, {
          code: "FORBIDDEN",
          message: "插件未声明 assets:write 权限，不能上传配图"
        });
        return true;
      }
      var dataUrl = typeof payload.data_url === "string" ? payload.data_url : "";
      if (!dataUrl) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "缺少待上传的 data_url" });
        return true;
      }
      if (dataUrl.length > 12 * 1024 * 1024) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "图片过大（解码后上限 8 MiB）" });
        return true;
      }
      withWriteToken("/api/assets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data_url: dataUrl })
      }).then(done, fail);
      return true;
    }

    if (method === "asset.read") {
      // 读托管配图：只认底座自己发出去的地址，别的路径一律不读。
      var assetReadPermissions = (tab.plugin && tab.plugin.permissions) || [];
      if (assetReadPermissions.indexOf("assets:read") < 0) {
        replyHost(tab, message, false, {
          code: "FORBIDDEN",
          message: "插件未声明 assets:read 权限，不能读取托管配图"
        });
        return true;
      }
      var assetUri = textValue(payload, "uri", 200);
      if (!/^\/static\/(pending|uploads|icons|assets)\/[A-Za-z0-9._-]+\.(png|jpg|jpeg|webp|svg)$/.test(assetUri)) {
        replyHost(tab, message, false, {
          code: "BAD_REQUEST",
          message: "只许读底座托管的配图地址"
        });
        return true;
      }
      fetchBinary(assetUri).then(function (binary) {
        done({ data_url: binary.dataUrl, mime: binary.mime, bytes: binary.bytes });
      }, fail);
      return true;
    }

    return false;
  }

  /** 校验「要剔除的中转站编号数组」：不是数组、超上限或有一项不合规都回 null。 */
  function pendingIdList(raw) {
    if (!Array.isArray(raw) || raw.length > 500) return null;
    var ids = [];
    for (var index = 0; index < raw.length; index += 1) {
      var value = typeof raw[index] === "string" ? raw[index] : "";
      if (!/^p_[A-Za-z0-9_-]{8,64}$/.test(value)) return null;
      ids.push(value);
    }
    return ids;
  }


  /** relay() 的「Pending」分支族：不属本族立刻返回 false，办完返回 true。 */
  function relayPending(ctx) {
    var tab = ctx.tab, message = ctx.message, method = ctx.method, payload = ctx.payload;
    var pluginId = ctx.pluginId, base = ctx.base, sharedBase = ctx.sharedBase;
    var done = ctx.done, fail = ctx.fail, failWith = ctx.failWith;
    var emitPendingUpdated = ctx.emitPendingUpdated;

    if (method.indexOf("pending.") !== 0) return false;

    if (method === "pending.batch_list" || method === "pending.list"
        || method === "pending.duplicate" || method === "pending.batch_duplicates") {
      // 读中转站：批次卡片与批次里的待审题目。开放给任何声明了 questions:read 的插件。
      var readPermissions = (tab.plugin && tab.plugin.permissions) || [];
      if (readPermissions.indexOf("questions:read") < 0) {
        replyHost(tab, message, false, {
          code: "FORBIDDEN",
          message: "插件未声明 questions:read 权限，不能读取中转站"
        });
        return true;
      }
      if (method === "pending.batch_list") {
        fetchJson("/api/pending/batches").then(done, fail);
        return true;
      }
      if (method === "pending.duplicate") {
        // 入库前的后台查重：只读，回两侧完整文档，插件自己做左右渲染对比。
        var dupPendingId = textValue(payload, "pending_id", 80);
        if (!/^p_[A-Za-z0-9_-]{8,64}$/.test(dupPendingId)) {
          replyHost(tab, message, false, { code: "BAD_REQUEST", message: "中转站编号不合法" });
          return true;
        }
        fetchJson("/api/pending/items/" + encodeURIComponent(dupPendingId) + "/duplicate")
          .then(done, fail);
        return true;
      }
      var pendingBatchId = textValue(payload, "batch_id", 40);
      if (!/^B-\d{3,}$/.test(pendingBatchId)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "批次编号不合法" });
        return true;
      }
      if (method === "pending.batch_duplicates") {
        // 一键剔除前的清单：只读，回 batch / bank 两组重复与默认勾选集，插件据此弹窗。
        fetchJson("/api/pending/batches/" + encodeURIComponent(pendingBatchId) + "/duplicates")
          .then(done, fail);
        return true;
      }
      fetchJson("/api/pending/batches/" + encodeURIComponent(pendingBatchId) + "/questions")
        .then(done, fail);
      return true;
    }

    if (method === "pending.save_draft" || method === "pending.approve"
        || method === "pending.delete" || method === "pending.purge_duplicates") {
      // 写中转站与写主库同权：必须先声明 questions:write，令牌仍留在宿主侧。
      var pendingPermissions = (tab.plugin && tab.plugin.permissions) || [];
      if (pendingPermissions.indexOf("questions:write") < 0) {
        replyHost(tab, message, false, {
          code: "FORBIDDEN",
          message: "插件未声明 questions:write 权限，不能改动中转站"
        });
        return true;
      }
      var jsonHeaders = { "Content-Type": "application/json" };
      if (method === "pending.purge_duplicates") {
        // 一键剔除：勾选集升序提交，expected_drop_ids 是同一集合的回显，只做载荷自洽校验；
        // 真正的护栏在服务端（按本次主库快照逐条判重 + 保留者保护 + 剔空硬闸）。
        var purgeBatchId = textValue(payload, "batch_id", 40);
        if (!/^B-\d{3,}$/.test(purgeBatchId)) {
          replyHost(tab, message, false, { code: "BAD_REQUEST", message: "批次编号不合法" });
          return true;
        }
        var purgeDrops = pendingIdList(payload.drop_ids);
        var purgeExpected = pendingIdList(payload.expected_drop_ids);
        if (purgeDrops === null || purgeExpected === null) {
          replyHost(tab, message, false, {
            code: "BAD_REQUEST",
            message: "drop_ids / expected_drop_ids 必须是中转站编号数组（最多 500 项）"
          });
          return true;
        }
        withWriteToken("/api/pending/batches/" + encodeURIComponent(purgeBatchId)
          + "/purge-duplicates", {
          method: "POST",
          headers: jsonHeaders,
          body: JSON.stringify({
            drop_ids: purgeDrops,
            expected_drop_ids: purgeExpected,
            allow_empty: payload.allow_empty === true
          })
        }).then(function (result) {
          var gone = (result && Array.isArray(result.deleted)) ? result.deleted : purgeDrops;
          emitPendingUpdated("delete", gone, result);
          done(result);
        }, fail);
        return true;
      }
      if (method === "pending.save_draft") {
        var draftQuestions = payload.questions;
        if (!Array.isArray(draftQuestions) || !draftQuestions.length) {
          replyHost(tab, message, false, { code: "BAD_REQUEST", message: "缺少待暂存的题目数组" });
          return true;
        }
        if (draftQuestions.length > 500) {
          replyHost(tab, message, false, { code: "BAD_REQUEST", message: "一次最多暂存 500 道题" });
          return true;
        }
        var draftBody = { questions: draftQuestions };
        var draftBatch = textValue(payload, "batch_id", 40);
        if (draftBatch) draftBody.batch_id = draftBatch;
        var draftBackup = textValue(payload, "source_backup", 240);
        if (draftBackup) draftBody.source_backup = draftBackup;
        var draftOrigin = textValue(payload, "origin", 60);
        if (draftOrigin) draftBody.origin = draftOrigin;
        withWriteToken("/api/pending/batches", {
          method: "POST",
          headers: jsonHeaders,
          body: JSON.stringify(draftBody)
        }).then(function (result) {
          emitPendingUpdated("save_draft", (result && result.saved_ids) || [], result);
          done(result);
        }, fail);
        return true;
      }
      var pendingId = textValue(payload, "pending_id", 80);
      if (!/^p_[A-Za-z0-9_-]{8,64}$/.test(pendingId)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "中转站编号不合法" });
        return true;
      }
      if (method === "pending.delete") {
        withWriteToken("/api/pending/items/" + encodeURIComponent(pendingId) + "/delete", {
          method: "POST",
          headers: jsonHeaders,
          body: JSON.stringify({})
        }).then(function (result) {
          emitPendingUpdated("delete", [pendingId], result);
          done(result);
        }, fail);
        return true;
      }
      // 存入主库：查重命中时后端回 409，插件拿 detail.existing_id 去问老师要不要强行覆盖。
      // 军令 #31：老师面对「高度相似」时的三种裁决里，覆盖与合并写成 action 递下去；
      // 「放弃」不写库，插件本地收口，根本不发这一趟。
      var dupAction = textValue(payload, "action", 40);
      if (dupAction && dupAction !== "overwrite" && dupAction !== "merge_solution") {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "不认识的入库动作" });
        return true;
      }
      withWriteToken("/api/pending/items/" + encodeURIComponent(pendingId) + "/approve", {
        method: "POST",
        headers: jsonHeaders,
        body: JSON.stringify({ force: payload.force === true, action: dupAction })
      }).then(function (result) {
        emitPendingUpdated("approve", [pendingId], result);
        emit("system.question_updated", {
          action: "create",
          id: result && result.question_id,
          pluginId: tab.plugin.id
        });
        done(result);
      }, fail);
      return true;
    }

    if (method === "pending.pool_list" || method === "pending.pool_get") {
      // 重题池只读（军令 #32 · 第五步）：列表与单条都是「渲染对比」的原料。
      var poolReadPermissions = (tab.plugin && tab.plugin.permissions) || [];
      if (poolReadPermissions.indexOf("questions:read") < 0) {
        replyHost(tab, message, false, {
          code: "FORBIDDEN",
          message: "插件未声明 questions:read 权限，不能读取重题池"
        });
        return true;
      }
      var poolTier = poolTierValue(payload.tier);
      if (method === "pending.pool_list") {
        fetchJson("/api/pending/pool" + poolTier).then(done, fail);
        return true;
      }
      var poolGetId = textValue(payload, "pool_id", 80);
      if (!/^pool_[A-Za-z0-9_-]{8,64}$/.test(poolGetId)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "重题池编号不合法" });
        return true;
      }
      fetchJson("/api/pending/pool/" + encodeURIComponent(poolGetId) + poolTier).then(done, fail);
      return true;
    }

    if (method === "pending.pool_act") {
      // 池内四个动作（合并元数据 / 新增解析 / 不重复 / 删除）都写主库或写裁决记录：
      // 与入库同权、同走一次性写令牌；动作名必须在白名单里，底座不做「猜一个最像的」。
      var poolActPermissions = (tab.plugin && tab.plugin.permissions) || [];
      if (poolActPermissions.indexOf("questions:write") < 0) {
        replyHost(tab, message, false, {
          code: "FORBIDDEN",
          message: "插件未声明 questions:write 权限，不能裁决重题池"
        });
        return true;
      }
      var poolActId = textValue(payload, "pool_id", 80);
      var poolAction = textValue(payload, "action", 40);
      if (!/^pool_[A-Za-z0-9_-]{8,64}$/.test(poolActId)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "重题池编号不合法" });
        return true;
      }
      if (POOL_ACTIONS.indexOf(poolAction) < 0) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "不认识的池内动作" });
        return true;
      }
      withWriteToken("/api/pending/pool/" + encodeURIComponent(poolActId) + "/act", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: poolAction })
      }).then(function (result) {
        // 并元数据 / 新增解析 / 不重复都会动主库，各端要跟着回流；删除只动池子。
        if (result && result.written) {
          emit("system.question_updated", {
            action: poolAction === "keep_separate" ? "create" : "update",
            id: (result && (result.created_id || result.main_id)) || "",
            pluginId: tab.plugin.id
          });
        }
        done(result);
      }, fail);
      return true;
    }

    if (method === "pending.set_meta" || method === "pending.meta_history") {
      // 批次公共元数据：改一次，这一批所有题（含已入库的）立刻跟着改。
      var metaPermissions = (tab.plugin && tab.plugin.permissions) || [];
      var metaNeed = method === "pending.set_meta" ? "questions:write" : "questions:read";
      if (metaPermissions.indexOf(metaNeed) < 0) {
        replyHost(tab, message, false, {
          code: "FORBIDDEN",
          message: "插件未声明 " + metaNeed + " 权限，不能改批次公共元数据"
        });
        return true;
      }
      if (method === "pending.meta_history") {
        fetchJson("/api/pending/meta/history").then(done, fail);
        return true;
      }
      var metaBatchId = textValue(payload, "batch_id", 40);
      if (!/^B-\d{3,}$/.test(metaBatchId)) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "批次编号不合法" });
        return true;
      }
      var rawYear = payload.year;
      var metaYear = null;
      if (rawYear !== undefined && rawYear !== null && rawYear !== "") {
        var parsedYear = Number(rawYear);
        if (Number.isFinite(parsedYear)) metaYear = Math.floor(parsedYear);
      }
      var metaSchools = [];
      if (Array.isArray(payload.schools)) {
        payload.schools.slice(0, 24).forEach(function (item) {
          var school = textValue({ v: item }, "v", 60);
          if (school && metaSchools.indexOf(school) < 0) metaSchools.push(school);
        });
      }
      // 明细学校优先走字典 ID；老插件仍送校名时保留 schools 字段，底座负责建档换 ID。
      var metaSchoolIds = [];
      if (Array.isArray(payload.school_ids)) {
        payload.school_ids.slice(0, 24).forEach(function (item) {
          var schoolId = textValue({ v: item }, "v", 40);
          if (/^sch_[A-Za-z0-9_-]{4,40}$/.test(schoolId)
              && metaSchoolIds.indexOf(schoolId) < 0) {
            metaSchoolIds.push(schoolId);
          }
        });
      }
      var metaBody = {
        year: metaYear,
        region: textValue(payload, "region", 60),
        grade: textValue(payload, "grade", 20),
        body: textValue(payload, "body", 60),
        exam_type: textValue(payload, "exam_type", 60),
        subject: textValue(payload, "subject", 40),
        scene_type: textValue(payload, "scene_type", 60),
        schools: metaSchools,
        school_ids: metaSchoolIds,
        // 双向联动：手改标准名时 name_mode=manual；元数据一动，底座自动回 auto。
        name_mode: payload.name_mode === "manual" ? "manual" : "auto",
        standard_name: textValue(payload, "standard_name", 120)
      };
      withWriteToken("/api/pending/batches/" + encodeURIComponent(metaBatchId) + "/meta", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(metaBody)
      }).then(function (result) {
        emitPendingUpdated("meta", [], result);
        done(result);
      }, fail);
      return true;
    }

    return false;
  }

  /** relay() 的「Meta」分支族：不属本族立刻返回 false，办完返回 true。 */
  function relayMeta(ctx) {
    var tab = ctx.tab, message = ctx.message, method = ctx.method, payload = ctx.payload;
    var pluginId = ctx.pluginId, base = ctx.base, sharedBase = ctx.sharedBase;
    var done = ctx.done, fail = ctx.fail, failWith = ctx.failWith;
    var emitPendingUpdated = ctx.emitPendingUpdated;

    if (method.indexOf("meta.") !== 0) return false;

    if (method === "meta.scenes" || method === "meta.schools" || method === "meta.tags") {
      // 字典读：场景、学校、交叉标签。任何有 questions:read 的插件都能查。
      var dictPerms = (tab.plugin && tab.plugin.permissions) || [];
      if (dictPerms.indexOf("questions:read") < 0) {
        replyHost(tab, message, false, {
          code: "FORBIDDEN",
          message: "插件未声明 questions:read 权限，不能读数据字典"
        });
        return true;
      }
      if (method === "meta.scenes") {
        fetchJson("/api/meta/scenes").then(done, fail);
        return true;
      }
      var dictQuery = textValue(payload, "q", 60);
      var dictLimit = intValue(payload, "limit", 30, 1, 50);
      if (method === "meta.schools") {
        fetchJson("/api/meta/schools?limit=" + dictLimit
          + (dictQuery ? "&q=" + encodeURIComponent(dictQuery) : "")).then(done, fail);
        return true;
      }
      var dictScene = textValue(payload, "scene", 40);
      fetchJson("/api/meta/tags?limit=" + dictLimit
        + (dictScene ? "&scene=" + encodeURIComponent(dictScene) : "")
        + (dictQuery ? "&q=" + encodeURIComponent(dictQuery) : "")).then(done, fail);
      return true;
    }

    if (method === "meta.school_create" || method === "meta.school_suggest"
        || method === "meta.tag_remember") {
      // 字典写：建档、AI 补全、记住手打标签。令牌照旧只在宿主手里。
      var dictWrites = (tab.plugin && tab.plugin.permissions) || [];
      if (dictWrites.indexOf("questions:write") < 0) {
        replyHost(tab, message, false, {
          code: "FORBIDDEN",
          message: "插件未声明 questions:write 权限，不能改数据字典"
        });
        return true;
      }
      var dictHeaders = { "Content-Type": "application/json" };
      if (method === "meta.school_suggest") {
        var suggestName = textValue(payload, "short_name", 60);
        if (!suggestName) {
          replyHost(tab, message, false, { code: "BAD_REQUEST", message: "先填一个简称，才能让 AI 补全" });
          return true;
        }
        withWriteToken("/api/meta/schools/suggest", {
          method: "POST",
          headers: dictHeaders,
          timeout: AGENT_TIMEOUT_MS,
          body: JSON.stringify({
            short_name: suggestName,
            region: textValue(payload, "region", 60)
          })
        }).then(done, fail);
        return true;
      }
      if (method === "meta.tag_remember") {
        var tagName = textValue(payload, "name", 32);
        if (!tagName) {
          replyHost(tab, message, false, { code: "BAD_REQUEST", message: "标签不能为空" });
          return true;
        }
        withWriteToken("/api/meta/tags", {
          method: "POST",
          headers: dictHeaders,
          body: JSON.stringify({ name: tagName, scene: textValue(payload, "scene", 40) })
        }).then(done, fail);
        return true;
      }
      var schoolFull = textValue(payload, "full_name", 120);
      if (!schoolFull) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "学校全称不能为空" });
        return true;
      }
      withWriteToken("/api/meta/schools", {
        method: "POST",
        headers: dictHeaders,
        body: JSON.stringify({
          full_name: schoolFull,
          short_name: textValue(payload, "short_name", 60)
        })
      }).then(done, fail);
      return true;
    }

    return false;
  }

    return {
      relayMeta: relayMeta,
      relayPending: relayPending,
      relayText: relayText,
    };
  }

  global.JzoStageRelayIo = { create: create };
})(window);
