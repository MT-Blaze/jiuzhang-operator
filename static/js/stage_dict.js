/**
 * 字典导航 Host API：目录只读宿主已加载的 DcCatalog，开页只收合法分类键与表名。
 *
 * 字典导航属于数据看板插件自己的 sidebar.right 面板；底座在这里只做两件事：
 * 把目录以只读副本交给插件，以及把指定字典表原地铺进当前画布（stage_dict_view）。
 * 插件拿不到任意 URL，也碰不到字典页的 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var dictView = deps.dictView;
    var canvasTab = deps.canvasTab;
    var replyHost = deps.replyHost;
    var textValue = deps.textValue;

    function catalogue() {
      var api = window.DcCatalog;
      if (!api || !Array.isArray(api.CATEGORIES)) return [];
      return api.CATEGORIES.map(function (category) {
        return {
          key: category.key,
          title: category.title,
          desc: category.desc,
          items: (category.items || []).map(function (item) {
            return { table: item.table, name: item.name, desc: item.desc };
          })
        };
      });
    }

    function open(tab, message, payload) {
      var categoryKey = textValue(payload, "category", 40);
      var api = window.DcCatalog;
      var category = api && typeof api.byKey === "function" ? api.byKey(categoryKey) : null;
      if (!category) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "未知的字典分类" });
        return;
      }
      var table = textValue(payload, "table", 60);
      var sub = table ? api.subOf(category, table) : null;
      if (table && !sub) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "未知的字典表" });
        return;
      }
      if (!sub) sub = api.subsOf(category)[0] || null;
      if (!sub) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "该分类没有可显示的字典表" });
        return;
      }
      // 请求来自右栏辅助栏，那把句柄只有 frame 没有 panel：字典层必须铺进
      // 当前画布页签的面板，回执仍走发请求的那一帧。
      var canvas = canvasTab();
      if (!canvas || !canvas.panel) {
        replyHost(tab, message, false, { code: "BAD_REQUEST", message: "当前没有可承载字典表的画布页签" });
        return;
      }
      var result = dictView.toggle(canvas, {
        key: "dict:" + sub.key,
        title: sub.label,
        token: category.key + "|" + (table || sub.key),
        cat: category.key,
        sub: sub.key,
        src: "/dict?embedded=1&cat=" + encodeURIComponent(category.key)
          + "&sub=" + encodeURIComponent(sub.key)
      });
      replyHost(tab, message, true, {
        key: result.key, title: result.title, active: result.active,
        category: category.key, table: table
      });
    }

    /** @returns {boolean} true 表示本方法已处理并已回执。 */
    function handle(tab, message, method, payload) {
      if (method === "dict.catalog") {
        replyHost(tab, message, true, { categories: catalogue() });
        return true;
      }
      if (method === "dict.open") {
        open(tab, message, payload);
        return true;
      }
      return false;
    }

    return { handle: handle };
  }

  global.JzoStageDict = { create: create };
})(window);