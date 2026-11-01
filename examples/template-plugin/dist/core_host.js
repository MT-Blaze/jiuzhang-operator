/*
 * 模板插件 · 宿主通道（core_ 前缀 = 不碰 DOM 的纯逻辑，PLUGIN_SPEC §2.8.1）。
 *
 * 本文件只管「怎么和宿主说话」，不认任何界面元素：
 *   channel.callHost(method, payload)  → Promise，宿主回同 id 的 response
 *   channel.notifyHost(event, payload) → 单向广播，事件名须在 plugin.json 的 bus.publish 白名单里
 *   channel.replyTo / failTo           → 替宿主的请求回包
 *   channel.attach(onInbound)          → 把入站消息分流给调用方
 *
 * 【AI 开发铁律】完整版见 PLUGIN_SPEC §2.8：
 *   1. 严禁点对点耦合：插件之间不直连，跨插件协作只经底座事件总线与能力字典中转。
 *   2. 数据读写走宿主 API：插件碰不到数据库/文件/密钥，题库数据只能向宿主发请求换取。
 *   3. 状态同步走事件总线：改状态用通知广播，严禁调用其他插件的函数。
 *   4. UI 隔离在沙箱 iframe：本文件跑在 sandbox="allow-scripts" 的独立源里，
 *      碰不到父窗口 DOM/Cookie/localStorage；与宿主唯一通道是 window.parent.postMessage。
 *   5. 只用原生 JS/CSS：不引重型框架，也不联网加载任何资源（CSP 会拦）。
 *   6. 单文件不超 800 行：JS 按职能拆 core_* / ui_*，CSS 按域拆，渲染走数据驱动。
 */
(function (global) {
  "use strict";

  /* —— 铁律 2：方法分三类，别混（PLUGIN_SPEC §2.6）——
   *   公共真题库（跨页签共享，读当前活跃 provider）：
   *     bank.get / bank.review / bank.topics / bank.topic_notes / bank.create / bank.update / bank.delete
   *   插件自带的库（按本页签 plugin.id 走，需随包放 bank/schema.sql）：
   *     bank.list / bank.stats / bank.random
   *   工作区题篮（与具体哪个库无关）：basket.list / basket.add / basket.remove / basket.clear
   */
  var DEFAULT_TIMEOUT_MS = 20000;

  function create(options) {
    var protocol = options.protocol;
    var parentWindow = options.parentWindow || global.parent;
    var timeoutMs = options.timeoutMs || DEFAULT_TIMEOUT_MS;
    var seq = 0;
    var pending = {};

    function newRequestId() {
      // 请求 id 必须匹配 ^[A-Za-z0-9_-]{1,80}$：带点号（例如拿插件 id 当片段）宿主当场拒发，
      // 回 BAD_REQUEST_ID 并在底栏记一笔 plugin.error（历史坑：org.example.template_99）。
      seq += 1;
      return "p" + seq + "_" + Date.now().toString(36);
    }

    function post(message) {
      parentWindow.postMessage(message, "*");
    }

    function callHost(method, payload) {
      return new Promise(function (resolve, reject) {
        var requestId = newRequestId();
        pending[requestId] = { resolve: resolve, reject: reject, timer: setTimeout(function () {
          delete pending[requestId];
          reject(new Error("宿主响应超时：" + method));
        }, timeoutMs) };
        post({
          protocol: protocol, id: requestId, kind: "request",
          method: method, payload: payload || {}
        });
      });
    }

    /* —— 铁律 3：通知不要求回复，且必须幂等（同一事件重发不得产生副作用）。 —— */
    function notifyHost(event, payload) {
      post({ protocol: protocol, kind: "notification", event: event, payload: payload || {} });
    }

    function replyTo(target, requestId, result) {
      if (!target) return;
      post({ protocol: protocol, id: requestId, kind: "response", ok: true, result: result });
    }

    function failTo(target, requestId, code, message) {
      if (!target) return;
      post({
        protocol: protocol, id: requestId, kind: "response", ok: false,
        error: { code: code, message: message, retryable: false }
      });
    }

    /**
     * 入站分流：只认本协议的封包（铁律 4），其余一律不猜。
     * onInbound({kind, method, event, payload, source, id}) —— 只有 kind==="request" 必须回包。
     */
    function attach(onInbound) {
      global.addEventListener("message", function (event) {
        var message = event.data;
        if (!message || message.protocol !== protocol) return;
        if (message.kind === "response") {
          var task = pending[message.id];
          if (!task) return;
          delete pending[message.id];
          clearTimeout(task.timer);
          if (message.ok) task.resolve(message.result);
          else task.reject(new Error((message.error && message.error.message) || "宿主调用失败"));
          return;
        }
        onInbound({
          kind: message.kind, method: message.method, event: message.event,
          payload: message.payload, source: event.source, id: message.id
        });
      });
    }

    return {
      callHost: callHost,
      notifyHost: notifyHost,
      replyTo: replyTo,
      failTo: failTo,
      attach: attach
    };
  }

  global.JzoTemplateCore = { create: create };
})(window);
