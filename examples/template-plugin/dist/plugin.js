/*
 * 九章算子第三方插件模板 —— 改 3 个地方即可变成你自己的插件：
 *   1. plugin.json 的 id / name / version（目录名必须与 id 一字不差）
 *   2. 本文件顶部的 PLUGIN_ID
 *   3. index.html 的标题与界面
 *
 * 【AI 开发铁律】（完整版见 PLUGIN_SPEC.md §2.8 / README「如何用 AI 开发九章算子插件？」）
 *   1. 严禁点对点耦合：插件之间不直连，跨插件协作只能经底座事件总线中转。
 *   2. 数据读写走宿主 API：插件碰不到数据库/文件/密钥，题库数据只能向宿主发请求换取（见 callHost）。
 *   3. 状态同步走事件总线：改状态用通知广播（见 notifyHost），严禁调用其他插件的函数。
 *   4. UI 隔离在沙箱 iframe：本文件运行在 sandbox="allow-scripts" 的独立源里，
 *      碰不到父窗口 DOM/Cookie/localStorage；与宿主唯一的通道就是 window.parent.postMessage。
 *   5. 只用原生 JS/CSS：不引入 React/Vue/jQuery 等重型框架，也不联网加载任何资源（CSP 会拦截）。
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

  var params = {};          // 右栏面板当前值，由 ui.params.changed 通知维护
  var seq = 0;              // 请求编号，保证 id 唯一
  var pending = {};         // 等待宿主回包的请求：{ id: {resolve, reject, timer} }

  function $(id) { return document.getElementById(id); }

  function setStatus(text) {
    $("status").textContent = text;
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function reply(target, requestId, result) {
    if (!target) return;
    target.postMessage({ protocol: PROTOCOL, id: requestId, kind: "response", ok: true, result: result }, "*");
  }

  function fail(target, requestId, code, message) {
    if (!target) return;
    target.postMessage({
      protocol: PROTOCOL, id: requestId, kind: "response", ok: false,
      error: { code: code, message: message, retryable: false }
    }, "*");
  }

  /* —— 铁律 2：调用宿主 API ——
   * 向宿主发一条 request，宿主查完回一条同 id 的 response。插件永远拿不到令牌，也无法直连数据库。
   * 方法分三类，别混（PLUGIN_SPEC §2.6）：
   *   公共真题库（跨页签共享，读当前活跃 provider，装好底座就有数据）：
   *     bank.get / bank.review / bank.topics / bank.topic_notes / bank.create / bank.update / bank.delete
   *   插件自带的库（按本页签 plugin.id 走，需随包放 bank/schema.sql，多库并存）：
   *     bank.list / bank.stats / bank.random
   *   工作区题篮（与具体哪个库无关）：basket.list / basket.add / basket.remove / basket.clear
   * 请求 id 必须匹配 ^[A-Za-z0-9_-]{1,80}$（不带点号，否则宿主当场拒发并回 BAD_REQUEST_ID），
   * 且带超时兜底——宿主不回包时给出可读提示，不静默吞掉。 */
  function callHost(method, payload) {
    return new Promise(function (resolve, reject) {
      seq += 1;
      var requestId = "p" + seq + "_" + Date.now().toString(36);
      pending[requestId] = { resolve: resolve, reject: reject, timer: setTimeout(function () {
        delete pending[requestId];
        reject(new Error("宿主响应超时：" + method));
      }, 20000) };
      window.parent.postMessage({
        protocol: PROTOCOL, id: requestId, kind: "request", method: method, payload: payload || {}
      }, "*");
    });
  }

  /* —— 铁律 3：经事件总线广播状态 ——
   * 发一条 notification，事件名必须在 plugin.json 的 bus.publish 白名单里（如 region.dock），
   * 否则宿主会丢弃并在底栏记账。通知不要求回复，且必须幂等。 */
  function notifyHost(event, payload) {
    window.parent.postMessage({ protocol: PROTOCOL, kind: "notification", event: event, payload: payload || {} }, "*");
  }

  function showQuestions(items) {
    var list = $("list");
    list.textContent = "";
    items.forEach(function (q) {
      var card = document.createElement("div");
      card.className = "item";
      card.textContent = (q.id || "") + " ｜ " + (q.stem || "").slice(0, 80);
      list.appendChild(card);
    });
  }

  // 宿主 → 插件：一切入站消息都从这里分流
  window.addEventListener("message", function (event) {
    var message = event.data;
    if (!message || message.protocol !== PROTOCOL) return;   // 铁律 4：只认协议封包，别的不猜

    // ① 宿主对 callHost 的回包：按 id 找到等待中的请求兑现Promise
    if (message.kind === "response") {
      var task = pending[message.id];
      if (!task) return;
      delete pending[message.id];
      clearTimeout(task.timer);
      if (message.ok) task.resolve(message.result);
      else task.reject(new Error((message.error && message.error.message) || "宿主调用失败"));
      return;
    }

    // ② 单向通知：不回复，但要幂等（同一事件重发不得产生副作用）
    if (message.kind === "notification") {
      if (message.event === "ui.params.changed") {
        params = (message.payload && message.payload.values) || {};
        setStatus("面板参数已更新：" + JSON.stringify(params));
      } else if (message.event === "question.updated") {
        setStatus("有题目被修改，可重新点按钮拉取。");
      } else if (message.event === "command.pending") {
        // 宿主在命令超过 1 秒未回时先发的排队提示；请求仍然有效，继续等 response。
        setStatus("命令仍在排队：" + String((message.payload && message.payload.command_id) || ""));
      }
      return;
    }

    // ③ 宿主的请求：必须回 response
    if (message.kind !== "request") return;
    var method = message.method;

    if (method === "plugin.activate") {
      setStatus("已激活，宿主随时可下发请求。");
      reply(event.source, message.id, { ready: true, plugin_id: PLUGIN_ID, api_version: "1.0" });
      return;
    }
    if (method === "plugin.deactivate") {
      setStatus("已停用。");
      reply(event.source, message.id, { ready: false });
      return;
    }
    if (method === "question.render") {
      // 单题卡片渲染：宿主逐题下发时走这里（PLUGIN_SPEC §2.3.3）。
      // 返回的 HTML 会被宿主白名单净化：<script>、内联事件、javascript: 链接都会被剥掉。
      var question = (message.payload || {}).question || {};
      if (typeof question.stem !== "string") {
        fail(event.source, message.id, "INVALID_PAYLOAD", "题目载荷缺少 stem。");
        return;
      }
      reply(event.source, message.id, {
        html: '<article class="my-card">' + escapeHtml(question.stem) + "</article>",
        height: 96
      });
      return;
    }
    if (method === "command.execute") {
      // 能力路由字典（PLUGIN_SPEC §2.14）：别的插件经宿主转发来的命令在这里执行。
      // 只执行清单 contributes.commands 里声明过的 id；context 是调用方带来的上下文
      // （如题目 id 列表），from 是调用方插件 id——你不需要、也拿不到对方的 iframe。
      var commandPayload = message.payload || {};
      if (commandPayload.command_id !== ECHO_COMMAND) {
        fail(event.source, message.id, "UNKNOWN_COMMAND",
          "本插件没有声明命令：" + String(commandPayload.command_id || ""));
        return;
      }
      reply(event.source, message.id, {
        command_id: commandPayload.command_id,
        from: typeof commandPayload.from === "string" ? commandPayload.from : "",
        echo: commandPayload.context || {}
      });
      return;
    }
    if (method === "theme.changed" || method === "locale.changed") {
      reply(event.source, message.id, { accepted: true });
      return;
    }
    fail(event.source, message.id, "UNSUPPORTED_METHOD", "未实现的方法：" + String(method));
  });

  // 演示按钮：走公共真题库通道取一页题（底座装了题库插件就有数据，空库时如实显示 0 题）
  $("load-btn").addEventListener("click", function () {
    setStatus("正在向宿主请求 bank.review …");
    callHost("bank.review", { page: 1, page_size: 10 }).then(function (result) {
      var items = (result && result.items) || [];
      showQuestions(items);
      setStatus("取到 " + items.length + " 题（共 " + ((result && result.total) || 0) + " 题）。");
    }).catch(function (err) {
      setStatus("宿主调用失败：" + err.message);
    });
  });

  // 演示按钮：经事件总线向底栏广播（bus.publish 白名单里声明了 region.dock）
  $("dock-btn").addEventListener("click", function () {
    notifyHost("region.dock", { text: "模板插件向底栏问了一声好。", pluginId: PLUGIN_ID });
    setStatus("已广播 region.dock 通知。");
  });

  // 调用方按钮：像别的插件那样查宿主内存里的能力字典（不涉及任何直连）
  $("list-cmd-btn").addEventListener("click", function () {
    setStatus("正在向宿主请求 command.list …");
    callHost("command.list").then(function (result) {
      var commands = (result && result.commands) || [];
      var list = $("list");
      list.textContent = "";
      commands.forEach(function (item) {
        var card = document.createElement("div");
        card.className = "item";
        card.textContent = item.id + " ｜ " + (item.title || "")
          + " ｜ 提供方：" + (item.plugin_name || item.plugin_id || "?")
          + (item.requires_user ? " ｜ 执行前需用户确认" : "");
        list.appendChild(card);
      });
      setStatus("能力字典共 " + commands.length + " 条。");
    }).catch(function (err) {
      setStatus("读取能力字典失败：" + err.message);
    });
  });

  // 调用方按钮：经宿主调度本插件自己的命令，演示「请求 → 宿主转发 → 目标回包」整圈
  $("echo-cmd-btn").addEventListener("click", function () {
    setStatus("正在经宿主调度 " + ECHO_COMMAND + " …");
    callHost("command.execute", {
      command_id: ECHO_COMMAND,
      context: { from_template: true, note: "调用方按钮演示" }
    }).then(function (result) {
      var inner = (result && result.result) || {};
      setStatus("命令执行成功，目标插件 " + ((result && result.plugin_id) || "?")
        + " 回显：" + JSON.stringify(inner.echo || {}));
    }).catch(function (err) {
      setStatus("命令执行失败：" + err.message);
    });
  });
})();
