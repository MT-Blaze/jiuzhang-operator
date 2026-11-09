/**
 * 能力路由：引擎数据命令与视图命令（org.jiuzhang.bank-engine / ui_commands.js）。
 *
 * 合并后的插件既要承接原引擎的 data.* 命令，也要承接原视图的 view.* 命令。
 * 数据仍经宿主通道（hostCall）读写，本文件不碰数据库，只做参数校验与形状转换。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var respond = deps.respond;
    var hostCall = deps.hostCall;
    var state = deps.state;
    var loadQuestions = deps.loadQuestions;
    var loadReview = deps.loadReview;

    var FILTER_SETS = {
      grade: ["全部", "高一", "高二", "高三"],
      difficulty: ["全部", "L1", "L2", "L3", "L4"],
      type: ["全部", "single_choice", "multiple_choice", "fill_blank", "solution"]
    };

    function commandReject(source, message, code, text) {
      respond(source, message.id, false, null, code, text);
    }

    function rejectUnknown(context, allowed) {
      var unknown = Object.keys(context).filter(function (key) {
        return allowed.indexOf(key) < 0;
      });
      return unknown.length ? "不认识的参数：" + unknown.join("、") : "";
    }

    function filterFromContext(context) {
      var result = { ok: true, values: {} };
      var unknown = rejectUnknown(context, ["grade", "difficulty", "type", "search"]);
      if (unknown) {
        result.ok = false;
        result.message = unknown;
        return result;
      }
      Object.keys(FILTER_SETS).forEach(function (key) {
        if (context[key] === undefined) return;
        if (typeof context[key] !== "string" || FILTER_SETS[key].indexOf(context[key]) < 0) {
          result.ok = false;
          result.message = key + " 只接受 " + FILTER_SETS[key].join("/");
          return;
        }
        result.values[key] = context[key];
      });
      if (context.search !== undefined
          && (typeof context.search !== "string" || context.search.length > 100)) {
        result.ok = false;
        result.message = "search 必须是不超过 100 字的字符串";
      }
      return result;
    }

    function respondAsync(source, message, promise) {
      promise.then(function (result) {
        respond(source, message.id, true, result || {});
      }, function (error) {
        commandReject(source, message, "COMMAND_FAILED",
          (error && error.message) || "题库暂时不可用，请稍后再试");
      });
    }

    function handleDataCommand(source, message, commandId, context) {
      if (commandId === "org.jiuzhang.action.data.bank_stats") {
        var statsUnknown = rejectUnknown(context, []);
        if (statsUnknown) {
          commandReject(source, message, "BAD_PARAMS", statsUnknown);
          return true;
        }
        respondAsync(source, message, hostCall("bank.active_stats", {}));
        return true;
      }

      if (commandId === "org.jiuzhang.action.data.bank_topics") {
        var topicsUnknown = rejectUnknown(context, ["parent_id", "textbook_id", "search"]);
        if (topicsUnknown) {
          commandReject(source, message, "BAD_PARAMS", topicsUnknown);
          return true;
        }
        if (context.parent_id !== undefined
            && (typeof context.parent_id !== "string" || context.parent_id.length > 64)) {
          commandReject(source, message, "BAD_PARAMS", "parent_id 必须是不超过 64 字的字符串");
          return true;
        }
        if (context.search !== undefined
            && (typeof context.search !== "string" || context.search.length > 60)) {
          commandReject(source, message, "BAD_PARAMS", "search 必须是不超过 60 字的字符串");
          return true;
        }
        var topicPayload = {};
        if (typeof context.parent_id === "string" && context.parent_id) {
          topicPayload.parent_id = context.parent_id;
        }
        if (typeof context.search === "string" && context.search) {
          topicPayload.q = context.search.trim();
        }
        respondAsync(source, message, hostCall("bank.topics", topicPayload));
        return true;
      }

      if (commandId === "org.jiuzhang.action.data.bank_search") {
        var searchUnknown = rejectUnknown(
          context, ["query", "grade", "difficulty", "type", "limit"]);
        if (searchUnknown) {
          commandReject(source, message, "BAD_PARAMS", searchUnknown);
          return true;
        }
        var limit = context.limit === undefined ? 5 : context.limit;
        if (typeof limit !== "number" || limit < 1 || limit > 20 || Math.floor(limit) !== limit) {
          commandReject(source, message, "BAD_PARAMS", "limit 必须是 1–20 的整数");
          return true;
        }
        var listPayload = {
          q: typeof context.query === "string" ? context.query.trim().slice(0, 100) : "",
          grade: typeof context.grade === "string" ? context.grade : "",
          difficulty: typeof context.difficulty === "string" ? context.difficulty : "",
          type: typeof context.type === "string" ? context.type : "",
          page: 1,
          page_size: limit
        };
        hostCall("bank.active_list", listPayload).then(function (result) {
          var rows = Array.isArray(result && result.items) ? result.items : [];
          respond(source, message.id, true, {
            total: (result && result.total) || rows.length,
            items: rows.slice(0, limit).map(function (item) {
              return {
                id: item.id,
                type: item.type,
                difficulty: item.difficulty,
                stem: String(item.stem || "").slice(0, 120)
              };
            })
          });
        }, function (error) {
          commandReject(source, message, "COMMAND_FAILED",
            (error && error.message) || "题库暂时不可用，请稍后再试");
        });
        return true;
      }

      return false;
    }

    function handle(source, message) {
      var payload = message.payload || {};
      var commandId = typeof payload.command_id === "string" ? payload.command_id : "";
      var context = payload.context && typeof payload.context === "object" ? payload.context : {};

      if (handleDataCommand(source, message, commandId, context)) return;

      if (commandId === "org.jiuzhang.action.view.filter_questions") {
        var parsed = filterFromContext(context);
        if (!parsed.ok) return commandReject(source, message, "BAD_PARAMS", parsed.message);
        Object.keys(parsed.values).forEach(function (key) { state[key] = parsed.values[key]; });
        if (typeof context.search === "string") state.search = context.search.trim().slice(0, 100);
        state.view = "list";
        state.page = 1;
        state.showSolution = false;
        var reload = loadQuestions();
        if (!reload || typeof reload.then !== "function") {
          return commandReject(source, message, "COMMAND_BUSY", "题库正在加载，请稍后再试");
        }
        reload.then(function () {
          respond(source, message.id, true, {
            total: state.total,
            filters: {
              grade: state.grade,
              difficulty: state.difficulty,
              type: state.type,
              search: state.search
            }
          });
        });
        return;
      }

      if (commandId === "org.jiuzhang.action.view.review_queue") {
        var reviewUnknown = rejectUnknown(context, ["flag"]);
        if (reviewUnknown) {
          return commandReject(source, message, "BAD_PARAMS", reviewUnknown);
        }
        if (context.flag !== undefined
            && (typeof context.flag !== "string" || context.flag.length > 40)) {
          return commandReject(source, message, "BAD_PARAMS", "flag 必须是不超过 40 字的字符串");
        }
        state.reviewFlag = typeof context.flag === "string" ? context.flag.trim() : "";
        var reviewCall = loadReview(1);
        if (!reviewCall || typeof reviewCall.then !== "function") {
          return commandReject(source, message, "COMMAND_BUSY", "待审队列正在加载，请稍后再试");
        }
        reviewCall.then(function () {
          respond(source, message.id, true, {
            total: state.reviewTotal,
            pages: state.reviewPages,
            flag: state.reviewFlag,
            flags: state.reviewSummary.flags || []
          });
        });
        return;
      }

      commandReject(source, message, "UNKNOWN_COMMAND", "未声明的方法：" + commandId);
    }

    return { handle: handle };
  }

  global.JzoBankCommands = { create: create };
})(window);
