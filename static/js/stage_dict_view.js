/**
 * 字典页原地层：中央画布不再为字典新开页签。
 *
 * 看板页签的面板里叠一层同源 iframe（/dict?embedded=1），点右栏小标签只翻
 * 这一层与插件帧的 hidden——页签 key 不变，右栏主权对账不触发，辅助栏那帧
 * 从头到尾不重挂、不重绘。再点同一枚标签即收起本层，看板原样回来。
 * 整块下架：删本文件、workspace_dict_inplace.css 与 stage_dict.js 里的 toggle 调用。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var dock = deps.dock;
    var bizDock = deps.bizDock || dock;
    var frames = [];

    // 字典控制台的写操作回执（新增/改名/删除成功或失败）经 postMessage 递回宿主：
    // 只认本模块亲手造的帧，业务日志进【运行日志】，底座事件不从这里过。
    if (typeof window.addEventListener === "function") {
      window.addEventListener("message", function (event) {
        if (event.origin !== window.location.origin) return;
        var data = event.data;
        if (!data || data.jzo !== "dict.ops") return;
        var known = frames.some(function (view) {
          return view.frame && view.frame.isConnected && view.frame.contentWindow === event.source;
        });
        if (!known) return;
        bizDock(String(data.text || ""), String(data.topic || "dict.api"), String(data.level || ""));
      });
    }

    /** 休眠会清空面板，旧层随之脱离文档；账必须跟着销，不能拿死节点当活层。 */
    function viewOf(tab) {
      var view = tab.dictView;
      if (!view) return null;
      if (view.layer.parentNode === tab.panel) return view;
      tab.dictView = null;
      return null;
    }

    function build(tab, target) {
      var layer = document.createElement("div");
      layer.className = "ws-dict-inplace";
      layer.hidden = true;

      var frame = document.createElement("iframe");
      frame.className = "ws-dict-inplace-frame";
      frame.setAttribute("title", target.title);
      frame.setAttribute("loading", "lazy");
      frame.src = target.src;
      layer.appendChild(frame);
      tab.panel.appendChild(layer);

      var view = { layer: layer, frame: frame, token: "", cat: "", sub: "" };
      tab.dictView = view;
      frames.push(view);
      return view;
    }

    /** 同分类内换表走控制台自己的路由，不重载文档，滚动位置与展开态都留住。 */
    function route(view, target) {
      if (view.cat === target.cat && view.sub === target.sub) return;
      view.cat = target.cat;
      view.sub = target.sub;
      view.frame.setAttribute("title", target.title);
      var win = view.frame.contentWindow;
      var api = win && win.DcEmbedded;
      if (api && typeof api.go === "function") {
        api.go(target.cat, target.sub);
        return;
      }
      view.frame.src = target.src;
    }

    function paint(tab, view, on) {
      view.layer.hidden = !on;
      if (tab.frame) tab.frame.hidden = on;
    }

    /**
     * 点一枚标签：已激活的同一枚 → 收起回看板；其余 → 原地显示该表。
     * 身份认「分类 + 表」而不是二级标签：区划与学校共用一棵树，
     * 从区划点学校是换表，不该被当成「再点一次」而收掉。
     */
    function toggle(tab, target) {
      var view = viewOf(tab);
      if (view && !view.layer.hidden && view.token === target.token) {
        paint(tab, view, false);
        dock("已收起「" + target.title + "」，画布回到数据看板。", "stage.dict.closed");
        return { active: false, key: target.key, title: target.title };
      }
      if (!view) view = build(tab, target);
      else route(view, target);
      view.token = target.token;
      paint(tab, view, true);
      dock("已在画布原地打开「" + target.title + "」，再点一次该标签即返回看板。", "stage.dict.opened");
      return { active: true, key: target.key, title: target.title };
    }

    /** 宿主右栏保存全局设置后，原地灌进已打开的字典页，不重载 iframe。 */
    function applyGlobals(tab, globals) {
      var view = viewOf(tab);
      if (!view) return false;
      var frame = view.frame;
      var api = frame.contentWindow && frame.contentWindow.DcGlobals;
      if (api && typeof api.apply === "function") {
        api.apply(globals);
        return true;
      }
      frame.addEventListener("load", function once() {
        frame.removeEventListener("load", once);
        var next = frame.contentWindow && frame.contentWindow.DcGlobals;
        if (next && typeof next.apply === "function") next.apply(globals);
      });
      return true;
    }

    return { toggle: toggle, applyGlobals: applyGlobals };
  }

  global.JzoStageDictView = { create: create };
})(window);