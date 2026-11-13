/**
 * 知识点与考向 · 六级折叠树（2026-11-13）：版本 → 册次 → 章 → 节 → 知识点 → 考向。
 * 行尾不再挂「+」：子节点列表最下方统一一行低饱和幽灵行，点它就地长出输入框；
 * 空状态旁保留「＋ 添加」；右侧只留排序芯片与删除。
 * 版本加册次、册次加章、章加节、节加知识点、知识点加考向；考向是最底层，没有下一级。
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

  function caretButton(label, isOpen) {
    var caret = el("button", "dkl-caret", isOpen ? "▾" : "▸");
    caret.type = "button";
    caret.setAttribute("aria-expanded", isOpen ? "true" : "false");
    caret.setAttribute("aria-label", label);
    return caret;
  }

  function toggleOn(button, isClosed, open, close) {
    button.addEventListener("click", function () {
      if (isClosed()) open(); else close();
    });
  }

  /** 一行折叠逻辑：箭头、aria-expanded、容器 hidden 与展开记忆一次配好。 */
  function foldOf(caret, box, track, key, onOpen) {
    var fold = {
      open: function () {
        track[key] = true;
        box.hidden = false;
        caret.textContent = "▾";
        caret.setAttribute("aria-expanded", "true");
        return onOpen ? onOpen() : Promise.resolve();
      },
      close: function () {
        track[key] = false;
        box.hidden = true;
        caret.textContent = "▸";
        caret.setAttribute("aria-expanded", "false");
      },
      isClosed: function () { return box.hidden; }
    };
    toggleOn(caret, fold.isClosed, fold.open, fold.close);
    return fold;
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
    var rootList = null;
    var loadSeq = 0;
    function setStatus(text) { live.textContent = text; }
    function dictController(url, reload) {
      return { url: url, ctx: ctx, reload: reload, setStatus: setStatus };
    }

    // ---------- 知识点 / 考向（第四、五级，考向最底层不给 +） ----------
    function pointNode(chapter, point, prefix, isLast, reloadPoints, reorderPoint) {
      var li = el("li", "dkl-node dkl-point");
      li.setAttribute("data-id", String(point.id));
      li.setAttribute("role", "treeitem");
      li.draggable = true;
      var row = el("div", "dkl-row dkl-row-point");
      row.appendChild(G.span(prefix, isLast));
      var caret = caretButton("展开或折叠「" + point.name + "」的考向", false);
      row.appendChild(caret);
      var badge = el("span", "dkl-badge", "");
      row.appendChild(G.nameButton(point.name, "主知识点「" + point.name + "」", function (button) {
        window.DcRowOps.editCell(dictController(POINT_URL), button, point,
          { key: "name", label: "名称" });
      }, function () {
        if (fold.isClosed()) fold.open(); else fold.close();
      }));
      row.appendChild(badge);
      row.appendChild(G.sort(point.sort_order, "知识点「" + point.name + "」的排序号",
        function (value) { return reorderPoint(point, value); }));
      var grip = el("span", "dkl-grip", "⠿");
      grip.setAttribute("aria-hidden", "true");
      row.appendChild(grip);
      var ops = el("div", "dkl-ops");
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
      var fold = foldOf(caret, dirs.el, expanded.p, point.id, function () {
        return dirs.open();
      });
      if (expanded.p[point.id]) fold.open(); else fold.close();
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
      var caret = caretButton("展开或折叠「" + chapter.name + "」", false);
      row.appendChild(caret);
      row.appendChild(G.nameButton(chapter.name, "章节「" + chapter.name + "」", function (button) {
        window.DcRowOps.editCell(dictController(CHAPTER_URL), button, chapter,
          { key: "name", label: "名称" });
      }, function () {
        if (fold.isClosed()) fold.open(); else fold.close();
      }));
      // 现存章节编码多是 tp_* 技术码，只有纯数字编码（如 1.2）才值得露出来。
      if (chapter.code && /^[\d.]+$/.test(chapter.code)) row.appendChild(el("span", "dkl-sub", chapter.code));
      var badge = el("span", "dkl-badge", "");
      row.appendChild(badge);
      row.appendChild(G.sort(chapter.sort_order, "章节「" + chapter.name + "」的排序号",
        function (value) { return window.DcLinkageSort.save(CHAPTER_URL, chapter, value, load); }));
      var ops = el("div", "dkl-ops");
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
      // 有子节点时，末位统一交给幽灵行：章节行的竖线一直落到它身上。
      var sectionGhost = kids.length ? G.ghost(subPrefix, "添加节",
        "为「" + chapter.name + "」新增节", function (button) { addSection(button); }) : null;
      if (sectionGhost) children.appendChild(sectionGhost);
      children.appendChild(host);
      li.appendChild(children);
      var pointsPainted = false;

      function paintPoints() {
        var rows = pointsCache[chapter.id] || [];
        pointList.textContent = "";
        rows.forEach(function (point) {
          pointList.appendChild(pointNode(chapter, point, subPrefix,
            false, function () { return ensurePoints(true); }, reorderPoint));
        });
        if (rows.length) {
          pointList.appendChild(G.ghost(subPrefix, "添加知识点",
            "为「" + chapter.name + "」新增知识点", function (button) { addPoint(button); }));
        } else if (!kids.length) {
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

      var fold = foldOf(caret, children, expanded.c, chapter.id, function () {
        return pointsPainted ? Promise.resolve() : ensurePoints(false);
      });

      function addPoint(anchor) {
        fold.open().then(function () {
          window.DcLinkageAdd.point({
            chapter: chapter, host: pointList, prefix: subPrefix, anchor: anchor,
            before: pointList.querySelector(":scope > .dc-ghost-item")
              || pointList.querySelector(":scope > .dkl-empty"),
            onDone: function () {
              ensurePoints(true).then(function () {
                setStatus("已在「" + chapter.name + "」下新增知识点。");
              });
            }
          });
        });
      }

      function addSection(anchor) {
        fold.open();
        window.DcLinkageAdd.chapter({
          book: book, parent: chapter, siblings: kids || [],
          host: children, before: sectionGhost, prefix: subPrefix, anchor: anchor,
          onDone: function () {
            fold.open();
            setStatus("已在「" + chapter.name + "」下新增节。");
            load();
          }
        });
      }

      function reorderPoint(point, value) {
        return window.DcLinkageSort.reorderPoints(
          chapter.id, point.id, pointsCache[chapter.id] || [], value,
          function () { return ensurePoints(true); }
        ).then(function () { setStatus("主知识点顺序已保存。"); });
      }

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
      if (expanded.c[chapter.id]) fold.open(); else fold.close();
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
      var caret = caretButton("展开或折叠「" + (book.volume_name || book.name) + "」", true);
      row.appendChild(caret);
      row.appendChild(G.nameButton(book.volume_name || book.name,
        "册次「" + (book.volume_name || book.name) + "」", function (button) {
          window.DcRowOps.editCell(dictController(BOOK_URL), button, book,
            { key: "volume_name", label: "册次名" });
        }, function () {
          if (fold.isClosed()) fold.open(); else fold.close();
        }));
      if (book.name && book.name !== book.volume_name) {
        row.appendChild(el("span", "dkl-sub", book.name));
      }
      row.appendChild(el("span", "dkl-badge", chapters.length + " 章"));
      row.appendChild(G.sort(book.sort_order, "册次「" + (book.volume_name || book.name) + "」的排序号",
        function (value) { return window.DcLinkageSort.save(BOOK_URL, book, value, load); }));
      li.appendChild(row);
      var subPrefix = G.childPrefix(prefix, isLast);
      var children = el("ul", "dkl-list dkl-children");
      children.setAttribute("role", "group");
      chapters.forEach(function (child) {
        children.appendChild(chapterNode(book, child, subPrefix, false, 0));
      });
      if (!chapters.length) {
        children.appendChild(G.empty(subPrefix, "本册暂无章节。", {
          label: "给「" + (book.volume_name || book.name) + "」新增章",
          onClick: function (button) { addChapter(button); }
        }));
      } else {
        children.appendChild(G.ghost(subPrefix, "添加章",
          "给「" + (book.volume_name || book.name) + "」新增章",
          function (button) { addChapter(button); }));
      }
      li.appendChild(children);

      var fold = foldOf(caret, children, expanded.b, book.id);
      function addChapter(anchor) {
        fold.open();
        window.DcLinkageAdd.chapter({
          book: book, parent: null, siblings: chapters,
          host: children, prefix: subPrefix, anchor: anchor,
          before: children.querySelector(":scope > .dc-ghost-item")
            || children.querySelector(":scope > .dkl-empty"),
          onDone: function () {
            fold.open();
            setStatus("已给「" + (book.volume_name || book.name) + "」新增章。");
            load();
          }
        });
      }
      if (expanded.b[book.id] === false) fold.close(); else fold.open();
      return li;
    }

    // ---------- 教材版本（第一级） ----------
    function versionNode(version, books) {
      var li = el("li", "dkl-node dkl-version");
      li.setAttribute("role", "treeitem");
      var row = el("div", "dkl-row dkl-row-version");
      var caret = caretButton("展开或折叠「" + version.name + "」", true);
      row.appendChild(caret);
      row.appendChild(G.nameButton(version.name || ("版本 #" + version.id),
        "教材版本「" + (version.name || version.id) + "」", function (button) {
          window.DcRowOps.editCell(dictController(VERSION_URL), button, version,
            { key: "name", label: "版本名" });
        }, function () {
          if (fold.isClosed()) fold.open(); else fold.close();
        }));
      row.appendChild(el("span", "dkl-badge", books.length + " 册"));
      row.appendChild(G.sort(version.sort_order, "版本「" + (version.name || version.id) + "」的排序号",
        function (value) { return window.DcLinkageSort.save(VERSION_URL, version, value, load); }));
      li.appendChild(row);
      var children = el("ul", "dkl-list dkl-children");
      children.setAttribute("role", "group");
      books.forEach(function (item) {
        children.appendChild(bookNode(version, item, [], false));
      });
      if (!books.length) {
        children.appendChild(G.empty([], "该版本下还没有册次。", {
          label: "在「" + (version.name || version.id) + "」下新增册次",
          onClick: function (button) { addBook(button); }
        }));
      } else {
        children.appendChild(G.ghost([], "添加册次",
          "在「" + (version.name || version.id) + "」下新增册次",
          function (button) { addBook(button); }));
      }
      li.appendChild(children);

      var fold = foldOf(caret, children, expanded, "v");
      function addBook(anchor) {
        fold.open();
        window.DcLinkageAdd.book({
          version: version, books: books, host: children, prefix: [], anchor: anchor,
          before: children.querySelector(":scope > .dc-ghost-item")
            || children.querySelector(":scope > .dkl-empty"),
          onDone: function () {
            fold.open();
            setStatus("已在「" + (version.name || version.id) + "」下新增册次。");
            load();
          }
        });
      }
      if (expanded.v) fold.open(); else fold.close();
      return li;
    }

    // ---------- 装载 ----------
    function addVersion(anchor) {
      if (!rootList || !rootList.isConnected) {
        rootList = el("ul", "dkl-list dkl-books");
        rootList.setAttribute("role", "tree");
        tree.appendChild(rootList);
      }
      window.DcLinkageAdd.version({
        host: rootList, anchor: anchor, versions: versions,
        before: rootList.querySelector(":scope > .dkl-empty"),
        onDone: function (created) {
          var now = ctx.globals.current();
          ctx.globals.apply({
            stage: now.stage, subject_id: now.subject_id,
            version_id: created.id, version_name: created.name
          });
          setStatus("已新增教材版本「" + created.name + "」，已切换到该版本。");
        }
      });
    }
    addVersionBtn.addEventListener("click", function () { addVersion(addVersionBtn); });

    function notice(text) {
      var ul = el("ul", "dkl-list dkl-books");
      ul.setAttribute("role", "tree");
      ul.appendChild(G.empty([], text));
      tree.appendChild(ul);
      rootList = ul;
    }

    function load() {
      var versionId = ctx.globals.query().version_id;
      var seq = ++loadSeq;
      tree.textContent = "";
      rootList = null;
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
        rootList = ul;
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
