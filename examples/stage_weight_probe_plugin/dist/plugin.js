(function () {
  "use strict";

  var PROTOCOL = "jzo-plugin/1";
  var stateEl = document.getElementById("state");
  var logEl = document.getElementById("log");

  function note(text) {
    if (!logEl) return;
    var li = document.createElement("li");
    li.textContent = text;   // 宿主原文回显，绝不拼进 innerHTML
    logEl.appendChild(li);
  }

  function setMode(mode, text) {
    if (stateEl) {
      stateEl.setAttribute("data-mode", mode);
      stateEl.textContent = text;
    }
    note(text);
    // 沙箱里的话宿主听不见，借底座托管的输出日志区把原话带出去（PLUGIN_SPEC §2.5）
    try {
      window.parent.postMessage({
        protocol: PROTOCOL,
        kind: "notification",
        event: "region.dock",
        payload: { text: "[stage-weight] " + text }
      }, "*");
    } catch (error) {
      /* 投递失败只在本地留着，不影响取证脚本读这一栏 DOM */
    }
  }

  window.addEventListener("message", function (event) {
    var message = event.data;
    if (!message || message.protocol !== PROTOCOL) return;

    if (message.kind === "request") {
      var result = { ready: true, plugin_id: "org.example.stage-weight" };
      if (message.method === "plugin.deactivate") result = { ready: false };
      if (message.method === "question.render") {
        result = { html: "<p>探针不渲染题目</p>", height: 40 };
      }
      try {
        event.source.postMessage({
          protocol: PROTOCOL,
          id: message.id,
          kind: "response",
          ok: true,
          result: result
        }, "*");
      } catch (error) {
        /* 宿主已摘掉这帧，回复无处可去 */
      }
      return;
    }

    if (message.kind !== "notification") return;
    if (message.event === "plugin.suspend") {
      setMode("suspend", "收到 plugin.suspend：已收定时器（浅休眠，文档仍在）");
    } else if (message.event === "plugin.resume") {
      setMode("resume", "收到 plugin.resume：已恢复定时器（回到前台）");
    } else if (message.event === "plugin.deactivate") {
      setMode("idle", "收到 plugin.deactivate：本帧即将被摘掉");
    }
  });

  setMode("idle", "探针已挂载，等待宿主的休眠/唤醒通知");
})();
