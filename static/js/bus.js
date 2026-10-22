/**
 * HostBus：底座内的极简事件总线（四区骨架）。
 *
 * 定位（AGENTS §2）：插件之间不得直接调用或共享全局状态，跨区协作一律经总线。
 * 左、右、下三区由底座托管，中栏画布上的插件只能「发事件 / 收事件」，
 * 拿不到别的区的 DOM，也拿不到彼此的引用。
 *
 * 主题格式：小写点分，2–4 段，允许 `*`（匹配一段）与 `**`（匹配余下全部）。
 *   ui.params.changed   右栏面板参数被人或 AI 改动
 *   layout.changed      拖拽手柄改了某区尺寸
 *   region.dock         要求底栏输出一行
 *   stage.tab.opened    画布标签页状态变化
 *
 * 安全：payload 一律视为不可信。总线只传引用不做深拷贝，
 * 但订阅方要落 DOM 时必须自己用 textContent（AGENTS §5）。
 */
(function () {
  "use strict";

  var TOPIC_RE = /^[a-z][a-z0-9_]*(\.[a-z0-9_*]+){1,3}$/;
  var MAX_LISTENERS_PER_TOPIC = 32;

  // topic -> [{ pattern, fn }]；pattern 支持通配，key 用规范化后的字面主题
  var registry = new Map();
  var recent = [];
  var RECENT_MAX = 60;

  function normalize(topic) {
    return String(topic == null ? "" : topic).trim().toLowerCase();
  }

  function validTopic(topic) {
    return TOPIC_RE.test(topic);
  }

  function segments(pattern) {
    return pattern.split(".");
  }

  /** 通配匹配：`*` 吃一段，`**` 吃掉余下全部段。 */
  function matches(pattern, topic) {
    if (pattern === topic) return true;
    var p = segments(pattern);
    var t = segments(topic);
    for (var i = 0; i < p.length; i += 1) {
      if (p[i] === "**") return true;
      if (i >= t.length) return false;
      if (p[i] === "*") continue;
      if (p[i] !== t[i]) return false;
    }
    return p.length === t.length;
  }

  function on(pattern, fn) {
    var key = normalize(pattern);
    if (!validTopic(key) || typeof fn !== "function") return function () {};
    var list = registry.get(key);
    if (!list) {
      list = [];
      registry.set(key, list);
    }
    if (list.length >= MAX_LISTENERS_PER_TOPIC) return function () {};
    var entry = { pattern: key, fn: fn };
    list.push(entry);
    return function off() {
      var current = registry.get(key);
      if (!current) return;
      var index = current.indexOf(entry);
      if (index >= 0) current.splice(index, 1);
      if (!current.length) registry.delete(key);
    };
  }

  /**
   * 派发事件。订阅方抛错不许打断其余订阅方，也不许冒泡到调用点——
   * 一个坏插件不能拖垮底座（AGENTS §2「插件坏了，底座还能用」）。
   */
  function emit(topic, payload, meta) {
    var key = normalize(topic);
    if (!validTopic(key)) return 0;
    var event = {
      topic: key,
      payload: payload === undefined ? null : payload,
      source: (meta && meta.source) || "host",
      at: Date.now()
    };
    recent.push(event);
    while (recent.length > RECENT_MAX) recent.shift();

    var delivered = 0;
    registry.forEach(function (list, pattern) {
      if (!matches(pattern, key)) return;
      list.slice().forEach(function (entry) {
        try {
          entry.fn(event);
          delivered += 1;
        } catch (error) {
          // 订阅方自己炸了：记下来，继续派发给别人
          if (window.console && console.warn) {
            console.warn("[HostBus] 订阅 " + pattern + " 处理 " + key + " 失败：", error);
          }
        }
      });
    });
    return delivered;
  }

  function history() {
    return recent.slice();
  }

  window.JzoBus = {
    on: on,
    emit: emit,
    matches: matches,
    validTopic: validTopic,
    history: history
  };
})();
