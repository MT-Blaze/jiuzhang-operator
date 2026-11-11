/**
 * 右栏「字典维护导航」：三大分类各一枚页签入口。
 * 点分类 = 请舞台新开（或激活）同名字典页签，绝不覆盖看板/录题等现有页签。
 * 分类与表名只认 DcCatalog（与字典控制台共用同一份目录），这里不复制业务口径。
 * 整块下架：删本文件、workspace.html 的 #wsDictNav 节与 workspace_canvas.css 的 .ws-dict-nav 段。
 */
(function () {
  "use strict";

  var navBody = document.getElementById("wsDictNavBody");
  var navToggle = document.getElementById("wsDictNavToggle");
  if (!navBody || !navToggle) return;

  var TAB_PREFIX = "dict:";

  function openCategory(category) {
    if (!window.JzoStage || typeof window.JzoStage.openFrame !== "function") return;
    var src = "/dict?embedded=1&cat=" + encodeURIComponent(category.key);
    window.JzoStage.openFrame(TAB_PREFIX + category.key, category.title, src);
    // 舞台切页会触发右栏主权对账；字典页没有插件住户，这里把老师亲手用的右栏钉住。
    if (window.JzoWorkspace && typeof window.JzoWorkspace.openContextRail === "function") {
      window.JzoWorkspace.openContextRail();
    }
  }

  function buildCategory(category) {
    var card = document.createElement("div");
    card.className = "ws-dict-cat";

    var head = document.createElement("div");
    head.className = "ws-dict-cat-head";

    var open = document.createElement("button");
    open.type = "button";
    open.className = "ws-dict-cat-open";
    open.setAttribute("data-dict-cat", category.key);
    open.setAttribute("aria-label", "在画布新开「" + category.title + "」页签");
    var name = document.createElement("span");
    name.textContent = category.title;
    var count = document.createElement("span");
    count.className = "ws-dict-cat-count";
    count.textContent = category.items.length + " 张表";
    open.appendChild(name);
    open.appendChild(count);
    open.addEventListener("click", function () { openCategory(category); });
    head.appendChild(open);

    var listId = "wsDictCat_" + category.key;
    var toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "ws-dict-cat-toggle";
    toggle.setAttribute("aria-expanded", "true");
    toggle.setAttribute("aria-controls", listId);
    toggle.setAttribute("aria-label", "折叠或展开「" + category.title + "」的表清单");
    toggle.textContent = "▾";
    head.appendChild(toggle);

    var list = document.createElement("ul");
    list.className = "ws-dict-cat-list";
    list.id = listId;
    category.items.forEach(function (item) {
      var li = document.createElement("li");
      var strong = document.createElement("strong");
      strong.textContent = item.name;
      li.appendChild(strong);
      li.appendChild(document.createTextNode(" · " + item.desc));
      list.appendChild(li);
    });

    toggle.addEventListener("click", function () {
      var expanded = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!expanded));
      list.hidden = expanded;
      toggle.textContent = expanded ? "▸" : "▾";
    });

    card.appendChild(head);
    card.appendChild(list);
    return card;
  }

  function build() {
    var catalog = window.DcCatalog;
    if (!catalog || !Array.isArray(catalog.CATEGORIES)) {
      navBody.textContent = "";
      var note = document.createElement("p");
      note.className = "ws-dict-nav-state";
      note.textContent = "字典目录未就绪，请刷新页面后重试。";
      navBody.appendChild(note);
      return;
    }
    navBody.textContent = "";
    catalog.CATEGORIES.forEach(function (category) {
      navBody.appendChild(buildCategory(category));
    });
  }

  navToggle.addEventListener("click", function () {
    var expanded = navToggle.getAttribute("aria-expanded") === "true";
    navToggle.setAttribute("aria-expanded", String(!expanded));
    navBody.hidden = expanded;
    navToggle.querySelector(".ws-dict-nav-caret").textContent = expanded ? "▸" : "▾";
  });

  build();
})();
