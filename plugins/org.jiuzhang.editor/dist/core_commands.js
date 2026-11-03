/**
 * core_commands.js —— plugin.js 的「能力路由」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var COMMAND_QUESTION_ID_RE = coreState.COMMAND_QUESTION_ID_RE;
    var hostCall = deps.hostCall;
    var loadForEdit = deps.loadForEdit;
    var respond = deps.respond;
    var saveViaCommand = deps.saveViaCommand;
    var scheduleRender = deps.scheduleRender;
    var state = coreState.state;

  // ---------- 能力路由字典（军令 #20 的四条命令，v2 继续沿用同一批 id） ----------
  function commandReject(source, message, code, text) {
    respond(source, message.id, false, null, code, text);
  }

  function handleCommandExecute(source, message) {
    var payload = message.payload || {};
    var commandId = typeof payload.command_id === "string" ? payload.command_id : "";
    var context = payload.context && typeof payload.context === "object" ? payload.context : {};

    if (commandId === "org.jiuzhang.action.input.open_question") {
      var unknown = Object.keys(context).filter(function (key) { return key !== "question_id"; });
      if (unknown.length) {
        return commandReject(source, message, "BAD_PARAMS", "不认识的参数：" + unknown.join("、"));
      }
      if (typeof context.question_id !== "string" || !COMMAND_QUESTION_ID_RE.test(context.question_id)) {
        return commandReject(source, message, "BAD_PARAMS", "question_id 必须是合法的题目 id（q_ 开头）");
      }
      loadForEdit(context.question_id, "command").then(function (loaded) {
        if (!loaded) {
          commandReject(source, message, "COMMAND_FAILED", "没能载入题目 " + context.question_id);
          return;
        }
        respond(source, message.id, true, { question_id: context.question_id, editing: true });
      });
      return;
    }

    if (commandId === "org.jiuzhang.action.process.clean_latex") {
      if (Object.keys(context).length) {
        return commandReject(source, message, "BAD_PARAMS", "清洗命令不接受参数");
      }
      // 判据 1.6：清洗规则表只准有一处，就是底座的 app/core/latex_style_dict.py。
      // 插件这侧一份正则都不留——整批源码逐题发给宿主的 text.clean_latex（mode=exam_source），
      // 由底座 question_parser.clean_exam_source 洗：同一张字典，但不拆 exam-zh 环境骨架。
      // 逐题串行，不并发；一轮洗完才回执，AI 拿到的数就是真的改了几题。
      var touched = 0;
      var skipped = 0;
      var failed = 0;
      var firstError = "";
      var chain = Promise.resolve();
      state.items.forEach(function (item) {
        var text = String(item.source == null ? "" : item.source);
        if (!text.trim()) {
          skipped += 1;
          return;
        }
        chain = chain.then(function () {
          return hostCall("text.clean_latex", { text: text, mode: "exam_source" }).then(function (result) {
            var cleaned = String(result && result.text || "");
            if (!result || !result.changed || !cleaned) {
              skipped += 1;
              return;
            }
            item.source = cleaned;
            item.dirty = true;
            touched += 1;
          }, function (error) {
            failed += 1;
            if (!firstError) firstError = (error && error.message) || "未知原因";
          });
        });
      });
      return chain.then(function () {
        if (touched) scheduleRender();
        respond(source, message.id, true, {
          touched: touched, skipped: skipped, failed: failed, message: firstError
        });
      });
    }

    if (commandId === "org.jiuzhang.action.input.save_question") {
      if (Object.keys(context).length) {
        return commandReject(source, message, "BAD_PARAMS", "保存命令不接受参数");
      }
      saveViaCommand("save").then(function (result) {
        respond(source, message.id, true, result);
      }, function (error) {
        commandReject(source, message, error && error.code === "LOCAL_INVALID" ? "BAD_REQUEST" : "COMMAND_FAILED",
          (error && error.message) || "保存失败");
      });
      return;
    }
    if (commandId === "org.jiuzhang.action.process.create_variant") {
      if (Object.keys(context).length) {
        return commandReject(source, message, "BAD_PARAMS", "派生变式命令不接受参数");
      }
      saveViaCommand("variant").then(function (result) {
        respond(source, message.id, true, result);
      }, function (error) {
        commandReject(source, message, error && error.code === "LOCAL_INVALID" ? "BAD_REQUEST" : "COMMAND_FAILED",
          (error && error.message) || "另存失败");
      });
      return;
    }
    commandReject(source, message, "UNKNOWN_COMMAND", "未声明的方法：" + commandId);
  }

    return {
      commandReject: commandReject,
      handleCommandExecute: handleCommandExecute,
    };
  }

  global.JzoEditorCommands = { create: create };
})(window);
