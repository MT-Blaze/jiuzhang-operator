/**
 * 知识点与考向 · 六级折叠树（2026-11-13）：版本 → 册次 → 章 → 节 → 知识点 → 考向。
 * 每行悬停只露一个「+」，加什么由行所在层级决定：版本加册次、册次加章、章加节、
 * 节加知识点、知识点加考向；考向是最底层，不再给 +。空状态旁同样带「＋ 添加」；
 * 请求地址统一收在 DcLinkageAdd，考向清单在 DcLinkageDirections。
 * 整块下架：删本目录 linkage*.js / tree_add.js + linkage CSS + panels.js 的 mount 调用。
 */
(function () {
  "use strict";

  var VERSION_URL = "/api/bank/engine/dict/dim_textbook_versions";
  var BOOK_URL = "/api/bank/engine/dict/dim_textbooks";
  var CHAPTER_URL = "/api/bank/engine/dict/dim_textbook_chapters";
  var POINT_URL = "/api/bank/engine/dict/dim_knowledge_points";

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function mount(panel, ctx) {
    var T = window.DcTreeAdd;
    var G = window.DcLinkGuide;
    var wrap = el("section", "dkl-wrap");
    wrap.setAttribute("aria-label", "知识点与考向折叠树");

    var toolbar = el("div", "dkl-toolbar");
    toolbar.appendChild(el("span", "dkl-toolbar-label", "教材版本"));
    var addVersionBtn = el("button", "dkl-toolbar-add", "＋ 新增版本");
    addVersionBtn.type = "button";
    addVersionBtn.setAttribute("aria-label", "新增教材版本");
    toolbar.appendChild(addVersionBtn);

    var tree = el("div", "dkl-tree");
    // 树上方不留任何可见文字：状态只喂屏幕阅读器，避免切换列表时闪动。
    var live = el("p", "dc-sr-only", "");
    live.setAttribute("role", "status");
    live.setAttribute("aria-live", "polite");
    wrap.appendChild(toolbar);
    wrap.appendChild(tree);
    wrap.appendChild(live);
    panel.appendChild(wrap);

    var expanded = { v: true, b: {}, c: {}, p: {} };
    var pointsCache = {};
    var versions = [];
    var loadSeq = 0;
    function setStatus(text) { live.textContent = text; }
    function dictController(url, reload) {
      return { url: url, ctx: ctx, reload: reload, setStatus: setStatus };
    }

    // ---------- 知识点 / 考向（第四、五级，考向最底层不给 +） ----------
    function pointNode(chapter, point, prefix, isLast, reloadPoints) {
      var li = el("li", "dkl-node dkl-point");
      li.setAttribute("data-id", String(point.id));
      li.setAttribute("role", "treeitem");
      li.draggable = true;
      var row = el("div", "dkl-row dkl-row-point");
      row.appendChild(G.span(prefix, isLast));
      var caret = el("button", "dkl-caret", "▸");
      caret.type = "button";
      caret.setAttribute("aria-expanded", "false");
      caret.setAttribute("aria-label", "展开或折叠「" + point.name + "」的考向");
      row.appendChild(caret);
      var badge = el("span", "dkl-badge", "");
      row.appendChild(G.nameButton(point.name, "主知识点「" + point.name + "」", function (button) {
        window.DcRowOps.editCell(dictController(POINT_URL), button, point,
          { key: "name", label: "名称" });
      }, function () {
        if (dirs.el.hidden) openPoint(); else closePoint();
      }));
      row.appendChild(badge);
      var grip = el("span", "dkl-grip", "⠿");
      grip.setAttribute("aria-hidden", "true");
      row.appendChild(grip);
      var ops = el("div", "dkl-ops");
      ops.appendChild(T.plus({
        label: "为「" + point.name + "」新增考向",
        onClick: function (button) {
          var ready = dirs.el.hidden ? openPoint() : Promise.resolve();
          ready.then(function () { dirs.add(button); });
        }
      }));
      ops.appendChild(G.opButton("删除", true, "删除主知识点「" + point.name + "」", function (button) {
        window.DcRowOps.deleteRow(dictController(POINT_URL, function () {
          delete expanded.p[point.id];
          return reloadPoints();
        }), point, button);
      }));
      row.appendChild(ops);
      li.appendChild(row);
      var dirs = window.DcLinkageDirections.mount({
        point: point,
        prefix: G.childPrefix(prefix, isLast),
        status: setStatus,
        onCount: function (count) { badge.textContent = count + " 个考向"; }
      });
      li.appendChild(dirs.el);
      function openPoint() {
        expanded.p[point.id] = true;
        caret.textContent = "▾";
        caret.setAttribute("aria-expanded", "true");
        return dirs.open();
      }
      function closePoint() {
        expanded.p[point.id] = false;
        caret.textContent = "▸";
        caret.setAttribute("aria-expanded", "false");
        dirs.close();
      }
      caret.addEventListener("click", function () {
        if (dirs.el.hidden) openPoint(); else closePoint();
      });
      if (expanded.p[point.id]) openPoint(); else closePoint();
      return li;
    }

    // ---------- 章 / 节（第三、四级，可嵌套） ----------
    function chapterNode(book, node, prefix, isLast, depth) {
      var chapter = node.chapter;
      var kids = node.children || [];
      var isSection = depth >= 1;
      var li = el("li", "dkl-node dkl-chapter" + (isSection ? " dkl-section" : ""));
      li.setAttribute("data-chapter-id", String(chapter.id));
      li.setAttribute("role", "treeitem");
      var row = el("div", "dkl-row dkl-row-chapter");
      row.appendChild(G.span(prefix, isLast));
      var caret = el("button", "dkl-caret", "▸");
      caret.type = "button";
      caret.setAttribute("aria-expanded", "false");
      caret.setAttribute("aria-label", "展开或折叠「" + chapter.name + "」");
      row.appendChild(caret);
      row.appendChild(G.nameButton(chapter.name, "章节「" + chapter.name + "」", function (button) {
        window.DcRowOps.editCell(dictController(CHAPTER_URL), button, chapter,
          { key: "name", label: "名称" });
      }, function () {
        if (children.hidden) openChapter(); else closeChapter();
      }));
      // 现存章节编码多是 tp_* 技术码，只有纯数字编码（如 1.2）才值得露出来。
      if (chapter.code && /^[\d.]+$/.test(chapter.code)) row.appendChild(el("span", "dkl-sub", chapter.code));
      var badge = el("span", "dkl-badge", "");
      row.appendChild(badge);
      var ops = el("div", "dkl-ops");
      ops.appendChild(T.plus({
        label: isSection ? "为「" + chapter.name + "」新增知识点" : "为「" + chapter.name + "」新增节",
        onClick: function (button) {
          if (isSection) addPoint(button); else addSection(button);
        }
      }));
      ops.appendChild(G.opButton("删除", true, "删除章节「" + chapter.name + "」", function (button) {
        window.DcRowOps.deleteRow(dictController(CHAPTER_URL, function () {
          delete expanded.c[chapter.id];
          load();
          return Promise.resolve();
        }), chapter, button);
      }));
      row.appendChild(ops);
      li.appendChild(row);
      var subPrefix = G.childPrefix(prefix, isLast);
      var children = el("ul", "dkl-list dkl-children");
      children.setAttribute("role", "group");
      children.hidden = true;
      kids.forEach(function (child) {
        children.appendChild(chapterNode(book, child, subPrefix, false, depth + 1));
      });
      var host = el("li", "dkl-points-host");
      var pointList = el("ul", "dkl-list dkl-point-list");
      pointList.setAttribute("aria-label", "「" + chapter.name + "」的主知识点");
      host.appendChild(pointList);
      children.appendChild(host);
      li.appendChild(children);
      var pointsPainted = false;

      function paintPoints() {
        var rows = pointsCache[chapter.id] || [];
        pointList.textContent = "";
        rows.forEach(function (point, index) {
          pointList.appendChild(pointNode(chapter, point, subPrefix,
            index === rows.length - 1, function () { return ensurePoints(true); }));
        });
        if (!rows.length && !kids.length) {
          if (isSection) {
            pointList.appendChild(G.empty(subPrefix, "该章节暂无主知识点。", {
              label: "为「" + chapter.name + "」新增知识点",
              onClick: function (button) { addPoint(button); }
            }));
          } else {
            pointList.appendChild(G.empty(subPrefix, "该章暂无节。", {
              label: "为「" + chapter.name + "」新增节",
              onClick: function (button) { addSection(button); }
            }));
          }
        }
        badge.textContent = isSection ? rows.length + " 个知识点" : kids.length + " 节";
        pointsPainted = true;
      }

      function ensurePoints(force) {
        if (!force && pointsCache[chapter.id]) {
          paintPoints();
          return Promise.resolve();
        }
        return window.DcClient.fetchJson(
          "/api/bank/engine/linkage/chapters/" + chapter.id + "/points"
        ).then(function (data) {
          pointsCache[chapter.id] = data.items || [];
          paintPoints();
        }).catch(function (error) {
          pointList.textContent = "";
          pointList.appendChild(G.empty(subPrefix, "知识点加载失败：" + error.message));
        });
      }

      function openChapter() {
        expanded.c[chapter.id] = true;
        children.hidden = false;
        caret.textContent = "▾";
        caret.setAttribute("aria-expanded", "true");
        return pointsPainted ? Promise.resolve() : ensurePoints(false);
      }

      function closeChapter() {
        expanded.c[chapter.id] = false;
        children.hidden = true;
        caret.textContent = "▸";
        caret.setAttribute("aria-expanded", "false");
      }

      function addPoint(anchor) {
        var ready = children.hidden ? openChapter() : Promise.resolve();
        ready.then(function () {
          window.DcLinkageAdd.point(chapter, (pointsCache[chapter.id] || []).length, anchor, function () {
            ensurePoints(true).then(function () {
              setStatus("已在「" + chapter.name + "」下新增知识点。");
            });
          });
        });
      }

      function addSection(anchor) {
        window.DcLinkageAdd.chapter(book, chapter, kids, anchor, function () {
          expanded.c[chapter.id] = true;
          setStatus("已在「" + chapter.name + "」下新增节。");
          load();
        });
      }

      caret.addEventListener("click", function () {
        if (children.hidden) openChapter(); else closeChapter();
      });
      window.DcDnd.attach(pointList, {
        onOrder: function (ids) {
          if (!ids.length) return;
          window.DcClient.writeJson(
            "/api/bank/engine/linkage/chapters/" + chapter.id + "/points/order",
            { point_ids: ids }, "PUT"
          ).then(function () {
            var byId = {};
            (pointsCache[chapter.id] || []).forEach(function (point) { byId[point.id] = point; });
            pointsCache[chapter.id] = ids.map(function (id) { return byId[id]; }).filter(Boolean);
            paintPoints();
            setStatus("主知识点顺序已保存。");
          }).catch(function (error) {
            window.DcDialog.alert({ title: "排序保存失败", message: error.message });
            ensurePoints(true);
          });
        }
      });
      if (expanded.c[chapter.id]) openChapter(); else closeChapter();
      return li;
    }

    // ---------- 册次（第二级，默认展开） ----------
    function bookNode(version, item, prefix, isLast) {
      var book = item.textbook || {};
      var chapters = item.chapters || [];
      var li = el("li", "dkl-node dkl-book");
      li.setAttribute("data-book-id", String(book.id));
      li.setAttribute("role", "treeitem");
      var row = el("div", "dkl-row dkl-row-book");
      row.appendChild(G.span(prefix, isLast));
      var caret = el("button", "dkl-caret", "▾");
      caret.type = "button";
      caret.setAttribute("aria-expanded", "true");
      caret.setAttribute("aria-label", "展开或折叠「" + (book.volume_name || book.name) + "」");
      row.appendChild(caret);
      row.appendChild(G.nameButton(book.volume_name || book.name,
        "册次「" + (book.volume_name || book.name) + "」", function (button) {
          window.DcRowOps.editCell(dictController(BOOK_URL), button, book,
            { key: "volume_name", label: "册次名" });
        }, function () {
          if (children.hidden) openBook(); else closeBook();
        }));
      if (book.name && book.name !== book.volume_name) {
        row.appendChild(el("span", "dkl-sub", book.name));
      }
      row.appendChild(el("span", "dkl-badge", chapters.length + " 章"));
      var ops = el("div", "dkl-ops");
      ops.appendChild(T.plus({
        label: "给「" + (book.volume_name || book.name) + "」新增章",
        onClick: function (button) { addChapter(button); }
      }));
      row.appendChild(ops);
      li.appendChild(row);
      var subPrefix = G.childPrefix(prefix, isLast);
      var children = el("ul", "dkl-list dkl-children");
      children.setAttribute("role", "group");
      chapters.forEach(function (child, index) {
        children.appendChild(chapterNode(book, child, subPrefix, index === chapters.length - 1, 0));
      });
      if (!chapters.length) {
        children.appendChild(G.empty(subPrefix, "本册暂无章节。", {
          label: "给「" + (book.volume_name || book.name) + "」新增章",
          onClick: function (button) { addChapter(button); }
        }));
      }
      li.appendChild(children);

      function openBook() {
        expanded.b[book.id] = true;
        children.hidden = false;
        caret.textContent = "▾";
        caret.setAttribute("aria-expanded", "true");
      }
      function closeBook() {
        expanded.b[book.id] = false;
        children.hidden = true;
        caret.textContent = "▸";
        caret.setAttribute("aria-expanded", "false");
      }
      function addChapter(anchor) {
        if (children.hidden) openBook();
        window.DcLinkageAdd.chapter(book, null, chapters, anchor, function () {
          expanded.b[book.id] = true;
          setStatus("已给「" + (book.volume_name || book.name) + "」新增章。");
          load();
        });
      }
      caret.addEventListener("click", function () {
        if (children.hidden) openBook(); else closeBook();
      });
      if (expanded.b[book.id] === false) closeBook(); else openBook();
      return li;
    }

    // ---------- 教材版本（第一级） ----------
    function versionNode(version, books) {
      var li = el("li", "dkl-node dkl-version");
      li.setAttribute("role", "treeitem");
      var row = el("div", "dkl-row dkl-row-version");
      var caret = el("button", "dkl-caret", "▾");
      caret.type = "button";
      caret.setAttribute("aria-expanded", "true");
      caret.setAttribute("aria-label", "展开或折叠「" + version.name + "」");
      row.appendChild(caret);
      row.appendChild(G.nameButton(version.name || ("版本 #" + version.id),
        "教材版本「" + (version.name || version.id) + "」", function (button) {
          window.DcRowOps.editCell(dictController(VERSION_URL), button, version,
            { key: "name", label: "版本名" });
        }, function () {
          if (children.hidden) openVersion(); else closeVersion();
        }));
      row.appendChild(el("span", "dkl-badge", books.length + " 册"));
      var ops = el("div", "dkl-ops");
      ops.appendChild(T.plus({
        label: "在「" + (version.name || version.id) + "」下新增册次",
        onClick: function (button) { addBook(button); }
      }));
      row.appendChild(ops);
      li.appendChild(row);
      var children = el("ul", "dkl-list dkl-children");
      children.setAttribute("role", "group");
      books.forEach(function (item, index) {
        children.appendChild(bookNode(version, item, [], index === books.length - 1));
      });
      if (!books.length) {
        children.appendChild(G.empty([], "该版本下还没有册次。", {
          label: "在「" + (version.name || version.id) + "」下新增册次",
          onClick: function (button) { addBook(button); }
        }));
      }
      li.appendChild(children);

      function openVersion() {
        expanded.v = true;
        children.hidden = false;
        caret.textContent = "▾";
        caret.setAttribute("aria-expanded", "true");
      }
      function closeVersion() {
        expanded.v = false;
        children.hidden = true;
        caret.textContent = "▸";
        caret.setAttribute("aria-expanded", "false");
      }
      function addBook(anchor) {
        if (children.hidden) openVersion();
        window.DcLinkageAdd.book(version, books, anchor, function () {
          expanded.v = true;
          setStatus("已在「" + (version.name || version.id) + "」下新增册次。");
          load();
        });
      }
      caret.addEventListener("click", function () {
        if (children.hidden) openVersion(); else closeVersion();
      });
      if (expanded.v) openVersion(); else closeVersion();
      return li;
    }

    // ---------- 装载 ----------
    function addVersion(anchor) {
      var nextSort = versions.reduce(function (max, item) {
        return Math.max(max, Number(item.sort_order) || 0);
      }, 0) + 1;
      window.DcLinkageAdd.version(anchor, nextSort, function (created) {
        var now = ctx.globals.current();
        ctx.globals.apply({ stage: now.stage, subject_id: now.subject_id, version_id: created.id, version_name: created.name });
        setStatus("已新增教材版本「" + created.name + "」，已切换到该版本。");
      });
    }
    addVersionBtn.addEventListener("click", function () { addVersion(addVersionBtn); });

    function notice(text) {
      var ul = el("ul", "dkl-list dkl-books");
      ul.setAttribute("role", "tree");
      ul.appendChild(G.empty([], text));
      tree.appendChild(ul);
    }

    function load() {
      var versionId = ctx.globals.query().version_id;
      var seq = ++loadSeq;
      tree.textContent = "";
      pointsCache = {};
      if (!versionId) {
        notice("还没有选定教材版本：点上方【＋ 新增版本】新建，或到右侧全局设置里选一个。");
        return;
      }
      Promise.all([
        window.DcClient.fetchJson("/api/bank/engine/textbook-versions"),
        window.DcClient.fetchJson(
          "/api/bank/engine/linkage/version-tree?version_id=" + encodeURIComponent(versionId)
        )
      ]).then(function (results) {
        if (!wrap.isConnected || seq !== loadSeq) return;
        versions = results[0].items || [];
        var version = versions.filter(function (item) {
          return String(item.id) === String(versionId);
        })[0];
        if (!version) {
          version = { id: Number(versionId), name: "版本 #" + versionId,
            subject_id: Number(ctx.globals.query().subject_id || 0) };
        }
        var books = results[1].items || [];
        var ul = el("ul", "dkl-list dkl-books");
        ul.setAttribute("role", "tree");
        ul.appendChild(versionNode(version, books));
        tree.appendChild(ul);
      }).catch(function (error) {
        if (!wrap.isConnected || seq !== loadSeq) return;
        notice("知识点树加载失败：" + error.message);
      });
    }

    function onGlobals() {
      if (!wrap.isConnected) {
        document.removeEventListener(window.DcGlobals.EVENT_NAME, onGlobals);
        return;
      }
      expanded = { v: true, b: {}, c: {}, p: {} };
      load();
    }
    document.addEventListener(window.DcGlobals.EVENT_NAME, onGlobals);
    load();
    return wrap;
  }

  window.DcLinkTree = { mount: mount };
})();
