/**
 * split_board_zoom.js —— 切题画板的缩放记忆。
 *
 * 只借宿主 draft.save / draft.load 把比例存进当前工作区的数据舱；
 * 插件侧不碰任何浏览器本地存储。读失败、读回 null、类型不对一律退回 100%。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var hostCall = deps.hostCall;
    var key = deps.key;
    var min = deps.min;
    var max = deps.max;
    var delay = Number(deps.delay) > 0 ? Number(deps.delay) : 260;
    var timer = 0;

    function clamp(value, low, high) {
      if (high < low) return low;
      return Math.min(high, Math.max(low, value));
    }

    function read() {
      try {
        return hostCall("draft.load", { key: key }).then(function (result) {
          try {
            if (!result || result.ok === false) return 1;
            var value = result.value;
            var raw = (value && typeof value === "object") ? value.scale : value;
            var num = Number(raw);
            if (!isFinite(num) || num <= 0) return 1;
            return clamp(num, min, max);
          } catch (error) {
            return 1;
          }
        }, function () {
          return 1;
        });
      } catch (error) {
        return Promise.resolve(1);
      }
    }

    function save(scale) {
      var num = Number(scale);
      if (!isFinite(num) || num <= 0) return;
      try {
        hostCall("draft.save", {
          key: key,
          value: { scale: Math.round(clamp(num, min, max) * 1000) / 1000 }
        }).catch(function () { /* 缩放偏好存不下，不影响切题 */ });
      } catch (error) { /* 宿主没有这口子就只在本会话生效 */ }
    }

    function queue(scale) {
      if (timer) window.clearTimeout(timer);
      timer = window.setTimeout(function () {
        timer = 0;
        save(scale);
      }, delay);
    }

    function flush(scale) {
      if (!timer) return;
      window.clearTimeout(timer);
      timer = 0;
      save(scale);
    }

    return { read: read, save: save, queue: queue, flush: flush };
  }

  global.JzoEditorSplitBoardZoom = { create: create };
})(window);
