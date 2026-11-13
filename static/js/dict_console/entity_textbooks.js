/**
 * 实体维度 · 教材与章节（2026-11-11）：
 * 树顶 学段 → 科目 两级由 textbook_stage_tree.js 提供；本文件负责
 * 版本 → 册次 → 章 → 节 的渲染与全部读写交互（改名 / 删除 / 新增册次与章节）。
 * 底层仍是 dim_textbook_versions / dim_textbooks / dim_textbook_chapters 三张独立表，
 * 前端按 version_id、textbook_id、parent_id 合成树；三档学段默认全部折叠。
 * 搜索命中时自动展开学段 / 科目 / 版本 / 册次父级，命中行标「命中」。
 * 整块下架：删本文件、textbook_stage_tree.js 与 entities.css 的 det-* 段即可。
 */
(function () {
  "use strict";

  var S = window.DcEntityShared;
  var ST = window.DcTextbookStageTree;
  var VERSION_URL = "/api/bank/engine/dict/dim_textbook_versions";
  var BOOK_URL = "/api/bank/engine/dict/dim_textbooks";
  var CHAPTER_URL = "/api/bank/engine/dict/dim_textbook_chapters";
  var HIT_LIMIT = 400;

  function countNodes(nodes) {
    return (nodes || []).reduce(function (sum, node) {
      return sum + 1 + countNodes(node.children);
    }, 0);
  }

  function mount(host, ctx) {
    var section = S.el("section", "det-panel dc-entity-textbooks");
    section.setAttribute("aria-label", "教材与章节");

    var tools = S.el("div", "dc-table-tools");
    var search = document.createElement("input");
    search.type = "search";
    search.className = "dc-table-search";
    search.placeholder = "搜索版本 / 册次 / 章节…（例如：函数）";
    search.setAttribute("aria-label", "搜索教材与章节");
    var addVersion = S.el("button", "dc-btn dc-table-add", "新增版本");
    addVersion.type = "button";
    var count = S.el("span", "dc-table-count", "");
    count.setAttribute("role", "status");
    tools.appendChild(search);
    tools.appendChild(addVersion);
    tools.appendChild(count);
    section.appendChild(tools);

    var tree = S.el("div", "det-tree");
    section.appendChild(tree);
    var stateEl = S.el("p", "dc-table-state", "");
    stateEl.setAttribute("role", "status");
    stateEl.setAttribute("aria-live", "polite");
    section.appendChild(stateEl);
    host.appendChild(section);

    var state = {
      versions: [], books: {}, chapters: {}, orphans: [],
      subjectMeta: [], groups: [],
      expanded: new Set(), keyword: "", hits: null, seq: 0, loaded: false
    };

    function setStatus(text) { stateEl.textContent = text; }

    function byOrder(a, b) {
      var ao = Number(a.sort_order) || 0;
      var bo = Number(b.sort_order) || 0;
      return ao - bo || Number(a.id) - Number(b.id);
    }

    function bookLabel(book) { return book.volume_name || book.name; }

    function select(li) {
      var old = tree.querySelector(".det-row.is-selected");
      if (old) old.classList.remove("is-selected");
      li.querySelector(".det-row").classList.add("is-selected");
    }

    var makeRow = S.bindTree(state.expanded, select);
    var childList = S.childList;

    // ---- 搜索命中：学段 / 科目 由展开键体现，版本 / 册次 / 章节各持一份集合 ----

    function chapterHasHit(node) {
      if (state.hits.chapters.has(node.chapter.id)) return true;
      return (node.children || []).some(chapterHasHit);
    }

    function bookHasHit(book) {
      if (state.hits.books.has(book.id)) return true;
      return chapterRoots(book).some(chapterHasHit);
    }

    function versionHasHit(version) {
      if (state.hits.versions.has(version.id)) return true;
      return (state.books[version.id] || []).some(bookHasHit);
    }

    function collectHits(keyword) {
      var needle = keyword.toLowerCase();
      var hits = { versions: new Set(), books: new Set(), chapters: new Set(), total: 0, shown: 0 };
      function hit(value) {
        return value != null && String(value).toLowerCase().indexOf(needle) !== -1;
      }
      function walk(nodes) {
        nodes.forEach(function (node) {
          var chapter = node.chapter;
          if (hit(chapter.name) || hit(chapter.code)) {
            hits.total += 1;
            if (hits.shown < HIT_LIMIT) { hits.chapters.add(chapter.id); hits.shown += 1; }
          }
          walk(node.children || []);
        });
      }
      function scan(book) {
        if (hit(bookLabel(book)) || hit(book.name) || hit(book.code)) {
          hits.books.add(book.id);
          hits.total += 1;
        }
        walk(chapterRoots(book));
      }
      state.versions.forEach(function (version) {
        if (hit(version.name) || hit(version.code)) {
          hits.versions.add(version.id);
          hits.total += 1;
        }
        (state.books[version.id] || []).forEach(scan);
      });
      state.orphans.forEach(scan);
      return hits;
    }

    /** 命中章节要把学段 / 科目 / 版本 / 册次以及祖先章节全部展开，不能只平铺结果。 */
    function expandAncestors() {
      function expandChapterNodes(nodes) {
        nodes.forEach(function (node) {
          (node.children || []).forEach(function (kid) {
            if (chapterHasHit(kid)) {
              state.expanded.add("h:" + node.chapter.id);
              expandChapterNodes([kid]);
            }
          });
        });
      }
      state.versions.forEach(function (version) {
        var books = state.books[version.id] || [];
        if (!state.hits.versions.has(version.id) && !books.some(bookHasHit)) return;
        (version.stages || []).forEach(function (stage) {
          state.expanded.add(ST.stageKey(stage));
          state.expanded.add(ST.subjectKey(stage, version.subject_id));
        });
        state.expanded.add("v:" + version.id);
        books.forEach(function (book) {
          if (!bookHasHit(book)) return;
          state.expanded.add("b:" + book.id);
          expandChapterNodes(chapterRoots(book));
        });
      });
    }

    function markHit(li, on) {
      if (!on || !li) return li;
      li.classList.add("det-hit-row");
      var row = li.querySelector(".det-row");
      if (row && !row.querySelector(".det-hit-flag")) {
        row.insertBefore(S.el("span", "det-hit-flag", "命中"), row.querySelector(".det-ops"));
      }
      return li;
    }

    // ---- 数据装载：版本 / 册次 / 章节 / 学科名，一次性拉回前端合树 ----

    function reloadAll() {
      var seq = (state.seq || 0) + 1;
      state.seq = seq;
      if (!state.loaded) setStatus("正在读取版本 / 册次 / 章节…");
      return Promise.all([
        window.DcClient.fetchJson("/api/bank/engine/textbook-versions"),
        window.DcClient.fetchJson("/api/bank/engine/textbooks"),
        window.DcClient.fetchJson("/api/bank/engine/meta"),
        S.listAll("dim_textbook_chapters")
      ]).then(function (results) {
        if (!section.isConnected || seq !== state.seq) return;
        state.versions = (results[0].items || []).slice().sort(byOrder);
        var books = (results[1].items || []).slice().sort(byOrder);
        state.subjectMeta = results[2].subjects || [];
        state.books = {};
        state.orphans = [];
        books.forEach(function (book) {
          if (book.version_id == null) state.orphans.push(book);
          else (state.books[book.version_id] = state.books[book.version_id] || []).push(book);
        });
        var grouped = {};
        (results[3].items || []).forEach(function (row) {
          (grouped[row.textbook_id] = grouped[row.textbook_id] || []).push(row);
        });
        state.chapters = {};
        Object.keys(grouped).forEach(function (bookId) {
          state.chapters[bookId] = buildChapterTree(grouped[bookId]);
        });
        state.groups = ST.group(state.versions, state.subjectMeta);
        state.loaded = true;
        render();
        setStatus("双击版本 / 册次 / 章节名称可改名。");
      }).catch(function (error) {
        if (!section.isConnected || seq !== state.seq) return;
        setStatus("加载失败：" + error.message);
      });
    }

    function buildChapterTree(rows) {
      var byId = {};
      rows.forEach(function (row) { byId[row.id] = { chapter: row, children: [] }; });
      var roots = [];
      rows.forEach(function (row) {
        var node = byId[row.id];
        var parent = row.parent_id == null ? null : byId[row.parent_id];
        if (parent) parent.children.push(node);
        else roots.push(node);
      });
      function sortNodes(nodes) {
        nodes.sort(function (a, b) { return byOrder(a.chapter, b.chapter); });
        nodes.forEach(function (node) { sortNodes(node.children); });
      }
      sortNodes(roots);
      return roots;
    }

    function chapterRoots(book) { return state.chapters[book.id] || []; }

    function refresh(message) {
      return reloadAll().then(function () { if (message) setStatus(message); });
    }

    function renamed() { refresh("已改名。"); }

    function removeVersion(version, anchor) {
      S.remove({ url: VERSION_URL, row: version, anchor: anchor, reload: reloadAll, setStatus: setStatus });
    }

    function addBook(version, anchor) {
      var siblings = state.books[version.id] || [];
      var next = S.nextOrder(siblings);
      S.add({
        title: "在「" + version.name + "」下新增册次",
        message: "册次名只填“必修一 / 七年级上册”，完整书名保留版本与册次全称。",
        anchor: anchor,
        url: BOOK_URL,
        fields: [
          { key: "volume_name", label: "册次名", required: true, placeholder: "如 必修一" },
          { key: "name", label: "完整书名", required: true, placeholder: "如 人教A版数学必修一" },
          { key: "code", label: "册次编码", required: true, placeholder: "如 rja_m_1" },
          { key: "sort_order", label: "排序号", value: String(next), placeholder: "0 起，数字越小越靠前" }
        ],
        build: function (values) {
          return {
            name: values.name, code: values.code, volume_name: values.volume_name,
            version_id: version.id, subject_id: version.subject_id,
            sort_order: S.orderValue(values.sort_order, next)
          };
        },
        onDone: function () {
          state.expanded.add("v:" + version.id);
          refresh("已新增册次。");
        }
      });
    }

    function addVersionRow(anchor) {
      var subjectId = ctx.globals.query().subject_id;
      if (!subjectId) {
        S.fail("还不能新增版本", new Error("请先在右侧全局设置选择学科，再新增教材版本。"), anchor);
        return;
      }
      S.add({
        title: "新增教材版本",
        message: "版本名只填“人教A版 / 苏教版”，不要把册次拼进版本名。",
        anchor: anchor,
        url: VERSION_URL,
        fields: [
          { key: "name", label: "版本名称", required: true, placeholder: "如 人教A版" },
          { key: "code", label: "版本编码", required: true, placeholder: "如 rja_math" },
          { key: "publisher", label: "出版社", placeholder: "如 人民教育出版社" },
          { key: "sort_order", label: "排序号", value: String(S.nextOrder(state.versions)),
            placeholder: "0 起，数字越小越靠前" }
        ],
        build: function (values) {
          return {
            name: values.name, code: values.code, publisher: values.publisher,
            subject_id: subjectId,
            sort_order: S.orderValue(values.sort_order, S.nextOrder(state.versions))
          };
        },
        onDone: function () { refresh("已新增版本。"); }
      });
    }

    function removeBook(book, anchor) {
      S.remove({ url: BOOK_URL, row: book, anchor: anchor, reload: reloadAll, setStatus: setStatus });
    }

    function addChapterUnderBook(book, anchor) {
      state.expanded.add("b:" + book.id);
      window.DcChapterOps.add(null, chapterRoots(book), book.id,
        function () { refresh("已新增章。"); });
    }

    function addChapterUnderNode(book, node, anchor) {
      state.expanded.add("b:" + book.id);
      state.expanded.add("h:" + node.chapter.id);
      window.DcChapterOps.add(node.chapter, node.children, book.id,
        function () { refresh("已新增子章节。"); });
    }

    // ---- 版本 → 册次 → 章 → 节（第四层及以下沿用原渲染与交互，不改数据口径） ----

    function renderChapter(book, node, depth, crumb, showAll) {
      var chapter = node.chapter;
      var kids = node.children || [];
      if (state.hits && !showAll) kids = kids.filter(chapterHasHit);
      var key = "h:" + chapter.id;
      var expanded = state.expanded.has(key);
      var box = kids.length ? childList(depth + 1, expanded) : null;
      var li = makeRow({
        level: Math.min(depth + 1, 6), depth: depth, name: chapter.name, sub: chapter.code,
        crumb: crumb,
        badge: kids.length ? kids.length + " 节" : "",
        key: key,
        hasChildren: kids.length > 0,
        expanded: expanded,
        children: box,
        addLabel: "在「" + chapter.name + "」下新增子章节",
        add: function (btn) { addChapterUnderNode(book, node, btn); },
        edit: {
          url: CHAPTER_URL + "/" + chapter.id, field: "name",
          value: chapter.name, label: "章节名称", onDone: renamed
        },
        remove: function () {
          window.DcChapterOps.remove(chapter, function () { refresh("已删除章节。"); });
        },
        lazy: box && kids.length ? function () {
          kids.forEach(function (kid) {
            box.appendChild(renderChapter(book, kid, depth + 1, "", showAll));
          });
        } : null
      });
      return markHit(li, !!state.hits && state.hits.chapters.has(chapter.id));
    }

    function renderBook(book, depth, showAll) {
      var all = chapterRoots(book);
      var roots = state.hits && !showAll ? all.filter(chapterHasHit) : all;
      var key = "b:" + book.id;
      var expanded = state.expanded.has(key);
      var box = childList(depth + 1, expanded);
      var full = book.name && book.name !== bookLabel(book) ? book.name : "";
      var li = makeRow({
        level: depth + 1, depth: depth, name: bookLabel(book),
        sub: (full ? full + " · " : "") + (book.code || ""),
        badge: all.length + " 章 · " + countNodes(all) + " 节点",
        key: key,
        hasChildren: roots.length > 0,
        expanded: expanded,
        children: box,
        addLabel: "给「" + bookLabel(book) + "」新增顶层章",
        add: function (btn) { addChapterUnderBook(book, btn); },
        edit: {
          url: BOOK_URL + "/" + book.id, field: "volume_name",
          value: bookLabel(book), label: "册次名", onDone: renamed
        },
        remove: function (btn) { removeBook(book, btn); },
        lazy: roots.length ? function () {
          roots.forEach(function (node) {
            box.appendChild(renderChapter(book, node, depth + 1, "", showAll));
          });
        } : null
      });
      return markHit(li, !!state.hits && state.hits.books.has(book.id));
    }

    function renderVersion(version) {
      var all = state.books[version.id] || [];
      var books = state.hits && !state.hits.versions.has(version.id)
        ? all.filter(bookHasHit) : all;
      var showAll = !!state.hits && state.hits.versions.has(version.id);
      var key = "v:" + version.id;
      var expanded = state.expanded.has(key);
      var box = books.length ? childList(3, expanded) : null;
      var chapterTotal = all.reduce(function (sum, book) {
        return sum + countNodes(chapterRoots(book));
      }, 0);
      var li = makeRow({
        level: 3, depth: 2, name: version.name,
        sub: [version.publisher, version.code].filter(Boolean).join(" · "),
        badge: all.length + " 册 · " + chapterTotal + " 章",
        key: key,
        hasChildren: books.length > 0,
        expanded: expanded,
        children: box,
        addLabel: "在「" + version.name + "」下新增册次",
        add: function (btn) { addBook(version, btn); },
        edit: {
          url: VERSION_URL + "/" + version.id, field: "name",
          value: version.name, label: "版本名称", onDone: renamed
        },
        remove: function (btn) { removeVersion(version, btn); },
        lazy: box && books.length ? function () {
          books.forEach(function (book) {
            box.appendChild(renderBook(book, 3,
              showAll || (!!state.hits && state.hits.books.has(book.id))));
          });
        } : null
      });
      return markHit(li, !!state.hits && state.hits.versions.has(version.id));
    }

    function updateCount() {
      if (state.hits) {
        var extra = state.hits.total > state.hits.shown && state.hits.shown >= HIT_LIMIT
          ? "（仅展开前 " + state.hits.shown + " 个命中章节）" : "";
        count.textContent = state.hits.total
          ? "命中 " + state.hits.total + " 项" + extra : "命中 0 项";
        return;
      }
      var bookTotal = state.versions.reduce(function (sum, version) {
        return sum + (state.books[version.id] || []).length;
      }, state.orphans.length);
      var chapterTotal = Object.keys(state.chapters).reduce(function (sum, key) {
        return sum + countNodes(state.chapters[key]);
      }, 0);
      count.textContent = "共 " + state.versions.length + " 版 · " + bookTotal + " 册 · "
        + chapterTotal + " 章节";
    }

    function render() {
      tree.textContent = "";
      if (state.keyword) {
        state.hits = collectHits(state.keyword);
        expandAncestors();
      } else {
        state.hits = null;
      }
      var ul = S.el("ul", "det-list");
      ST.render(ul, {
        groups: state.groups,
        expanded: state.expanded,
        makeRow: makeRow,
        childList: childList,
        renderVersion: renderVersion,
        hitMode: !!state.hits,
        versionsOf: function (item) {
          return state.hits ? item.versions.filter(versionHasHit) : item.versions;
        }
      });
      var pending = state.versions.filter(function (version) {
        return !(version.stages || []).length;
      });
      ST.renderFallback(ul, {
        pending: pending, orphans: state.orphans,
        expanded: state.expanded, makeRow: makeRow, childList: childList,
        hitMode: !!state.hits, renderVersion: renderVersion, renderBook: renderBook,
        versionVisible: versionHasHit, bookVisible: bookHasHit,
        bookShowAll: function (book) { return !!state.hits && state.hits.books.has(book.id); }
      });
      tree.appendChild(ul);
      if (state.hits && !state.hits.total) {
        tree.appendChild(S.el("p", "det-empty", "没有匹配的版本 / 册次 / 章节。"));
      }
      updateCount();
      var first = tree.querySelector(".det-hit-row");
      if (first && typeof first.scrollIntoView === "function") {
        first.scrollIntoView({ block: "nearest" });
      }
    }

    addVersion.addEventListener("click", function () { addVersionRow(addVersion); });

    var timer = null;
    search.addEventListener("input", function () {
      window.clearTimeout(timer);
      timer = window.setTimeout(function () {
        state.keyword = search.value.trim();
        render();
      }, 220);
    });

    reloadAll();
    return { reload: reloadAll };
  }

  window.DcEntityTextbooks = { mount: mount };
})();
