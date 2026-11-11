/**
 * 字典导航 Host API：目录只读宿主已加载的 DcCatalog，开页只收合法分类键。
 *
 * 字典导航属于数据看板插件自己的 sidebar.right 面板；底座在这里只做两件事：
 * 把目录以只读副本交给插件，以及替插件打开宿主自有的 /dict 画布页签。
 * 插件拿不到任意 URL，也碰不到字典页的 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var openFrame = deps.openFrame;
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
      var tabKey = "dict:" + category.key;
      openFrame(tabKey, category.title,
        "/dict?embedded=1&cat=" + encodeURIComponent(category.key));
      replyHost(tab, message, true, { key: tabKey, title: category.title });
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
