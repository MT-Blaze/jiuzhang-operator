/**
 * 字典导航 Host API：目录只读宿主已加载的 DcCatalog，开页只收合法分类键与表名。
 *
 * 字典导航属于数据看板插件自己的 sidebar.right 面板；底座在这里只做两件事：
 * 把目录以只读副本交给插件，以及把指定字典表原地铺进当前画布（stage_dict_view）。
 * 插件拿不到任意 URL，也碰不到字典页的 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var dictView = deps.dictView;
    var canvasTab = deps.canvasTab;
    var fetchJson = deps.fetchJson;
    var replyHost = deps.replyHost;
    var textValue = deps.textValue;

    var GLOBALS_KEY = "jzo.dictConsole.globals.v1";
    var globalsMeta = null;

    function catalogue() {
      var api = window.DcCatalog;
      if (!api || !Array.isArray(api.CATEGORIES)) return [];
      return api.CATEGORIES.map(function (category) {
        return {
          key: category.key,
          title: category.title,
          desc: category.desc,
          items: (category.items || []).map(function (item) {
            return { table: item.table, name: item.name, desc: item.desc };
          })
        };
      });
    }

    function open(tab, message, payload) {
      var categoryKey = textValue(payload, "category", 40);
      var api = window.DcCatalog;
      var category = api && typeof api.byKey === "function" ? api.byKey(categoryKey) : null;
      if (!category) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "未知的字典分类" });
        return;
      }
      var table = textValue(payload, "table", 60);
      var sub = table ? api.subOf(category, table) : null;
      if (table && !sub) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "未知的字典表" });
        return;
      }
      if (!sub) sub = api.subsOf(category)[0] || null;
      if (!sub) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "该分类没有可显示的字典表" });
        return;
      }
      // 请求来自右栏辅助栏，那把句柄只有 frame 没有 panel：字典层必须铺进
      // 当前画布页签的面板，回执仍走发请求的那一帧。
      var canvas = canvasTab();
      if (!canvas || !canvas.panel) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "当前没有可承载字典表的画布页签" });
        return;
      }
      var result = dictView.toggle(canvas, {
        key: "dict:" + sub.key,
        title: sub.label,
        token: category.key + "|" + (table || sub.key),
        cat: category.key,
        sub: sub.key,
        src: "/dict?embedded=1&cat=" + encodeURIComponent(category.key)
          + "&sub=" + encodeURIComponent(sub.key)
      });
      replyHost(tab, message, true, {
        key: result.key, title: result.title, active: result.active,
        category: category.key, table: table
      });
    }

    // ---------- 全局设置通道（看板右栏插件不碰 localStorage，由宿主代存代取） ----------
    function emptyGlobals() {
      return { stage: "", subject_id: "", version_id: "" };
    }

    function readGlobals() {
      try {
        var saved = window.localStorage.getItem(GLOBALS_KEY);
        var parsed = saved ? JSON.parse(saved) : null;
        if (!parsed || typeof parsed !== "object") return emptyGlobals();
        return {
          stage: String(parsed.stage || ""),
          subject_id: parsed.subject_id == null ? "" : String(parsed.subject_id),
          version_id: parsed.version_id == null ? "" : String(parsed.version_id)
        };
      } catch (error) {
        return emptyGlobals();
      }
    }

    function writeGlobals(globals) {
      try {
        window.localStorage.setItem(GLOBALS_KEY, JSON.stringify(globals));
        return true;
      } catch (error) {
        return false;
      }
    }

    /** 学段 / 学科来自真实字典接口；教材版本按当前学段与学科单独拉，避免跨学段串味。 */
    function loadGlobalsMeta() {
      if (globalsMeta) return Promise.resolve(globalsMeta);
      return fetchJson("/api/bank/engine/meta").then(function (meta) {
        meta = meta || {};
        var stages = [];
        (meta.grades || []).forEach(function (grade) {
          if (grade && grade.stage && stages.indexOf(grade.stage) === -1) stages.push(grade.stage);
        });
        globalsMeta = {
          stages: stages,
          subjects: (meta.subjects || []).map(function (item) {
            return { id: item.id, name: item.name };
          })
        };
        return globalsMeta;
      });
    }

    function mapVersion(item) {
      return {
        id: item.id, name: item.name, subject_id: item.subject_id,
        stages: Array.isArray(item.stages) ? item.stages : []
      };
    }

    function loadVersionList(stage, subjectId) {
      var query = [];
      if (stage) query.push("stage=" + encodeURIComponent(stage));
      if (subjectId) query.push("subject_id=" + encodeURIComponent(subjectId));
      var url = "/api/bank/engine/textbook-versions";
      if (query.length) url += "?" + query.join("&");
      return fetchJson(url).then(function (body) {
        return ((body || {}).items || []).map(mapVersion);
      });
    }

    function optionsFailed(tab, message, error, prefix) {
      replyHost(tab, message, false, {
        code: "HOST_" + ((error && error.status) || 0),
        message: prefix + ((error && error.message) || "未知原因"),
        retryable: true
      });
    }

    function globalsGet(tab, message, payload) {
      var stage = textValue(payload, "stage", 20);
      var subjectId = Number(textValue(payload, "subject_id", 20)) || 0;
      Promise.all([
        loadGlobalsMeta(),
        loadVersionList(stage, subjectId)
      ]).then(function (results) {
        var meta = results[0];
        replyHost(tab, message, true, {
          current: readGlobals(),
          stages: meta.stages,
          subjects: meta.subjects,
          versions: results[1]
        });
      }, function (error) {
        optionsFailed(tab, message, error, "读取全局设置失败：");
      });
      return true;
    }

    function globalsSave(tab, message, payload) {
      var stage = textValue(payload, "stage", 20);
      var subjectText = textValue(payload, "subject_id", 20);
      var versionText = textValue(payload, "version_id", 20);
      var subjectId = Number(subjectText) || 0;
      var versionId = Number(versionText) || 0;
      Promise.all([
        loadGlobalsMeta(),
        loadVersionList(stage, subjectId)
      ]).then(function (results) {
        var meta = results[0];
        var versions = results[1];
        if (stage && meta.stages.indexOf(stage) === -1) {
          replyHost(tab, message, false, { code: "BAD_REQUEST", message: "未知的学段" });
          return;
        }
        var subject = meta.subjects.filter(function (item) {
          return Number(item.id) === subjectId;
        })[0];
        if (subjectId && !subject) {
          replyHost(tab, message, false, { code: "BAD_REQUEST", message: "未知的学科" });
          return;
        }
        // 版本清单已按学段 + 学科收口，不在清单里就是跨学段串味，直接拒绝。
        var version = versions.filter(function (item) {
          return Number(item.id) === versionId;
        })[0];
        if (versionId && !version) {
          replyHost(tab, message, false, { code: "BAD_REQUEST", message: "教材版本与当前学段 / 学科不匹配" });
          return;
        }
        var saved = {
          stage: stage,
          subject_id: subjectId ? String(subjectId) : "",
          version_id: versionId ? String(versionId) : ""
        };
        if (!writeGlobals(saved)) {
          replyHost(tab, message, false, {
            code: "STORAGE_FAILED",
            message: "本机存储不可用，全局设置未能保存"
          });
          return;
        }
        var canvas = canvasTab();
        if (canvas) dictView.applyGlobals(canvas, saved);
        replyHost(tab, message, true, { saved: true, current: saved });
      }, function (error) {
        optionsFailed(tab, message, error, "保存全局设置失败：");
      });
      return true;
    }

    /** @returns {boolean} true 表示本方法已处理并已回执。 */
    function handle(tab, message, method, payload) {
      if (method === "dict.catalog") {
        replyHost(tab, message, true, { categories: catalogue() });
        return true;
      }
      if (method === "dict.open") {
        open(tab, message, payload);
        return true;
      }
      if (method === "dict.globals_get") {
        return globalsGet(tab, message, payload);
      }
      if (method === "dict.globals_save") {
        return globalsSave(tab, message, payload);
      }
      return false;
    }

    return { handle: handle };
  }

  global.JzoStageDict = { create: create };
})(window);