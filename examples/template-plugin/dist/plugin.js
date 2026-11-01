/*
 * 九章算子第三方插件模板 · 装配层 —— 改 3 个地方即可变成你自己的插件：
 *   1. plugin.json 的 id / name / version（目录名必须与 id 一字不差）
 *   2. 本文件顶部的 PLUGIN_ID
 *   3. index.html 的标题与界面
 *
 * 文件分四份（PLUGIN_SPEC §2.8.1，铁律 6：单文件不超 800 行）：
 *   core_host.js    只和宿主说话，不碰 DOM
 *   ui_render.js    只管「数据 → DOM」，用公共资产 /static/common/ui_reactive.js
 *   plugin.js       本文件：取节点、建 ctx、接事件、把上面两块拼起来
 *   layout.css / ui.css   样式按域分文件（§2.8.2）
 *
 * 【能力路由字典】想把自己的能力开放给别的插件，在 plugin.json 里声明
 *   "contributes": {"commands": [{"id": "com.你的域名.动作", "title": "给老师看的名字"}]}，
 * 并像下面 command.execute 那样处理宿主转发来的执行请求。查别人有什么能力用
 * callHost("command.list")，调度用 callHost("command.execute", {command_id, context})——
 * 全程由宿主中转，插件之间不直连（PLUGIN_SPEC §2.14）。
 * 高副作用命令（导出、覆盖、批量删改）加 "requires_user": true：宿主会在转发前弹一次
 * 用户确认，用户点拒绝回 COMMAND_DENIED，请求根本到不了你的 iframe。
 * 命令执行超过 1 秒未回，宿主会先发一条 command.pending 通知（不是失败，继续等结果）。
 */
(function () {
  "use strict";

  var PROTOCOL = "jzo-plugin/1";
  var PLUGIN_ID = "org.example.template";
  var ECHO_COMMAND = "org.example.template.echo";

  var view = window.JzoTemplateUi.create({
    statusEl: document.getElementById("status"),
    listEl: document.getElementById("list")
  });
  var ui = view.ui;

  var host = window.JzoTemplateCore.create({ protocol: PROTOCOL });

  function setRows(kind, rows) {
    ui.rows = rows.map(function (row, index) {
      return { key: kind + "-" + index, text: row };
    });
  }

  // ---------- 宿主的请求：kind==="request" 必须回包 ----------

  function onInbound(message) {
    if (message.kind === "notification") {
      onNotification(message);
      return;
    }
    if (message.kind !== "request") return;
    var method = message.method;
    if (method === "plugin.activate") {
      ui.status = "已激活，宿主随时可下发请求。";
      host.replyTo(message.source, message.id,
        { ready: true, plugin_id: PLUGIN_ID, api_version: "1.0" });
      return;
    }
    if (method === "plugin.deactivate") {
      ui.status = "已停用。";
      host.replyTo(message.source, message.id, { ready: false });
      return;
    }
    if (method === "question.render") {
      renderQuestion(message);
      return;
    }
    if (method === "command.execute") {
      executeCommand(message);
      return;
    }
    if (method === "theme.changed" || method === "locale.changed") {
      host.replyTo(message.source, message.id, { accepted: true });
      return;
    }
    host.failTo(message.source, message.id, "UNSUPPORTED_METHOD", "未实现的方法：" + String(method));
  }

  /** 单向通知：不回复，但要幂等（同一事件重发不得产生副作用）。 */
  function onNotification(message) {
    if (message.event === "ui.params.changed") {
      var params = (message.payload && message.payload.values) || {};
      ui.status = "面板参数已更新：" + JSON.stringify(params);
    } else if (message.event === "question.updated") {
      ui.status = "有题目被修改，可重新点按钮拉取。";
    } else if (message.event === "command.pending") {
      // 宿主在命令超过 1 秒未回时先发的排队提示；请求仍然有效，继续等 response。
      ui.status = "命令仍在排队：" + String((message.payload && message.payload.command_id) || "");
    }
  }

  // 单题卡片渲染：宿主逐题下发时走这里（PLUGIN_SPEC §2.3.3）。
  // 返回的 HTML 会被宿主白名单净化：<script>、内联事件、javascript: 链接都会被剥掉。
  function renderQuestion(message) {
    var question = (message.payload || {}).question || {};
    if (typeof question.stem !== "string") {
      host.failTo(message.source, message.id, "INVALID_PAYLOAD", "题目载荷缺少 stem。");
      return;
    }
    var html = '<article class="my-card">' + view.escapeHtml(question.stem) + "</article>";
    ui.cardHtml = html;
    host.replyTo(message.source, message.id, { html: html, height: 96 });
  }

  // 能力路由字典（PLUGIN_SPEC §2.14）：别的插件经宿主转发来的命令在这里执行。
  // 只执行清单 contributes.commands 里声明过的 id；context 是调用方带来的上下文
  // （如题目 id 列表），from 是调用方插件 id——你不需要、也拿不到对方的 iframe。
  function executeCommand(message) {
    var commandPayload = message.payload || {};
    if (commandPayload.command_id !== ECHO_COMMAND) {
      host.failTo(message.source, message.id, "UNKNOWN_COMMAND",
        "本插件没有声明命令：" + String(commandPayload.command_id || ""));
      return;
    }
    host.replyTo(message.source, message.id, {
      command_id: commandPayload.command_id,
      from: typeof commandPayload.from === "string" ? commandPayload.from : "",
      echo: commandPayload.context || {}
    });
  }

  host.attach(onInbound);

  // ---------- 四个演示按钮：一律「只改数据」，画界面交给 ui_render.js ----------

  // 走公共真题库通道取一页题（底座装了题库插件就有数据，空库时如实显示 0 题）
  document.getElementById("load-btn").addEventListener("click", function () {
    ui.status = "正在向宿主请求 bank.review …";
    host.callHost("bank.review", { page: 1, page_size: 10 }).then(function (result) {
      var items = (result && result.items) || [];
      setRows("question", items.map(function (q) {
        return (q.id || "") + " ｜ " + String(q.stem || "").slice(0, 80);
      }));
      ui.status = "取到 " + items.length + " 题（共 " + ((result && result.total) || 0) + " 题）。";
    }).catch(function (err) {
      ui.status = "宿主调用失败：" + err.message;
    });
  });

  // 经事件总线向底栏广播（plugin.json 的 bus.publish 白名单里声明了 region.dock）
  document.getElementById("dock-btn").addEventListener("click", function () {
    host.notifyHost("region.dock", { text: "模板插件向底栏问了一声好。", pluginId: PLUGIN_ID });
    ui.status = "已广播 region.dock 通知。";
  });

  // 像别的插件那样查宿主内存里的能力字典（不涉及任何直连）
  document.getElementById("list-cmd-btn").addEventListener("click", function () {
    ui.status = "正在向宿主请求 command.list …";
    host.callHost("command.list").then(function (result) {
      var commands = (result && result.commands) || [];
      setRows("command", commands.map(function (item) {
        return item.id + " ｜ " + (item.title || "")
          + " ｜ 提供方：" + (item.plugin_name || item.plugin_id || "?")
          + (item.requires_user ? " ｜ 执行前需用户确认" : "");
      }));
      ui.status = "能力字典共 " + commands.length + " 条。";
    }).catch(function (err) {
      ui.status = "读取能力字典失败：" + err.message;
    });
  });

  // 经宿主调度本插件自己的命令，演示「请求 → 宿主转发 → 目标回包」整圈
  document.getElementById("echo-cmd-btn").addEventListener("click", function () {
    ui.status = "正在经宿主调度 " + ECHO_COMMAND + " …";
    host.callHost("command.execute", {
      command_id: ECHO_COMMAND,
      context: { from_template: true, note: "调用方按钮演示" }
    }).then(function (result) {
      var inner = (result && result.result) || {};
      ui.status = "命令执行成功，目标插件 " + ((result && result.plugin_id) || "?")
        + " 回显：" + JSON.stringify(inner.echo || {});
    }).catch(function (err) {
      ui.status = "命令执行失败：" + err.message;
    });
  });
})();
