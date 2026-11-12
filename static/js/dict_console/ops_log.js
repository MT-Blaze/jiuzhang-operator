/**
 * 字典控制台的业务日志出口：写操作的真实回执经 postMessage 递给工作台。
 *
 * 控制台可能单独开，也可能嵌在工作台画布里；只有嵌着时才有【运行日志】可写。
 * 这里只发一条消息，不碰父页 DOM、不用 localStorage（AGENTS §2 插件边界同款口径）。
 * 整块下架：删本文件、dict_console.html 里那行 script 与 client.js 的两处调用即可。
 */
(function () {
  "use strict";

  var FLAG = "dict.ops";

  function embedded() {
    return window.parent && window.parent !== window;
  }

  function post(level, text, topic) {
    if (!embedded()) return false;
    var body = String(text == null ? "" : text).slice(0, 400);
    if (!body) return false;
    try {
      window.parent.postMessage({
        jzo: FLAG,
        level: String(level || "info"),
        text: body,
        topic: String(topic || "dict.api")
      }, window.location.origin);
      return true;
    } catch (error) {
      return false;
    }
  }

  window.DcOpsLog = {
    ok: function (text, topic) { return post("ok", text, topic); },
    fail: function (text, topic) { return post("error", text, topic); },
    note: function (text, topic) { return post("info", text, topic); }
  };
})();
