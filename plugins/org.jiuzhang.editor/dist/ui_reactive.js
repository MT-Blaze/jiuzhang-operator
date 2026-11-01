/**
 * 微型响应式引擎（约 100 行原生 JS）：数据一变，渲染函数自己重跑。
 *
 *   var ui = JzoReactive.reactive({ hover: -1 });
 *   JzoReactive.watch(function () { panelRoot.setAttribute("data-hover", String(ui.hover)); });
 *   ui.hover = 3;              // 下一个微任务里渲染函数自己再跑一次
 *
 * 只用 Proxy + 微任务队列，不引任何第三方库；同一轮里的多次赋值只渲染一次。
 * 渲染怎么画 DOM 由调用方决定：引擎只管「数据变了就通知」。
 */
(function (global) {
  "use strict";
  var RAW = "__jzoRail__";
  var proxies = new WeakMap();
  var watchers = [];
  var pending = false;

  function isPlain(value) {
    return value !== null && typeof value === "object";
  }

  function unwrap(value) {
    return value && value[RAW] ? value[RAW] : value;
  }

  function flush() {
    pending = false;
    // 拷贝一份再跑：渲染函数里注册的新 watcher 留到下一轮，不在这一轮里插队。
    watchers.slice().forEach(function (render) {
      try { render(); } catch (error) { /* 一个渲染函数坏了不连坐其它渲染 */ }
    });
  }

  function schedule() {
    if (pending) return;
    pending = true;
    if (typeof Promise === "function") Promise.resolve().then(flush);
    else global.setTimeout(flush, 0);
  }

  function wrap(target) {
    if (!isPlain(target)) return target;
    var cached = proxies.get(target);
    if (cached) return cached;
    var proxy = new Proxy(target, {
      get: function (obj, key) {
        if (key === RAW) return true;
        return wrap(obj[key]);
      },
      set: function (obj, key, value) {
        var before = obj[key];
        var next = unwrap(value);
        if (before === next) return true;
        obj[key] = next;
        schedule();
        return true;
      },
      deleteProperty: function (obj, key) {
        if (!(key in obj)) return true;
        delete obj[key];
        schedule();
        return true;
      }
    });
    proxies.set(target, proxy);
    return proxy;
  }

  /**
   * 把一个普通对象包成响应式对象（深层生效：嵌套对象的任何改动也算数）。
   * 非对象原样返回，读取原始对象用 ``JzoReactive.raw(value)``。
   */
  function reactive(target) {
    return wrap(isPlain(target) ? target : {});
  }

  /** 登记一个渲染函数：登记时先跑一次，之后任何数据变动都再跑一次（同一轮只跑一次）。 */
  function watch(render) {
    if (typeof render !== "function") return function () {};
    if (watchers.indexOf(render) < 0) watchers.push(render);
    schedule();
    return render;
  }

  /** 注销渲染函数（页面拆掉时用，免得闭包跟着 iframe 一起漏）。 */
  function unwatch(render) {
    var index = watchers.indexOf(render);
    if (index >= 0) watchers.splice(index, 1);
  }

  /** 手动跑一次全部渲染，或用 ``nextTick`` 在下一轮微任务里跑自己的函数。 */
  function nextTick(task) {
    if (typeof task === "function") queueMicrotaskLike(task);
    else schedule();
  }

  function queueMicrotaskLike(task) {
    if (typeof Promise === "function") Promise.resolve().then(task);
    else global.setTimeout(task, 0);
  }

  global.JzoReactive = {
    reactive: reactive,
    watch: watch,
    unwatch: unwatch,
    nextTick: nextTick,
    raw: unwrap
  };
})(window);
