/**
 * 实体维度 · 教材与章节（2026-11-11）：
 * 底层仍是 dim_textbook_versions / dim_textbooks / dim_textbook_chapters 三张独立表，
 * 前端按 version_id、textbook_id、parent_id 合树：版本 → 册次 → 章 → 节。
 * 默认只露全部版本；点版本展开册次，点册次展开章，逐层下拉，章节按需构建。
 * 双击节点文字原地改名（无改名按钮），删除悬停该行才显示；
 * 册次＋默认新增顶层章，章节＋默认新增子章节。
 * 整块下架：删本文件与 entities.css 的 det-* 段即可。
 */
(function () {
  "use strict";

  var S = window.DcEntityShared;
  var VERSION_URL = "/api/bank/engine/dict/dim_textbook_versions";
  var BOOK_URL = "/api/bank/engine/dict/dim_textbooks";
  var CHAPTER_URL = "/api/bank/engine/dict/dim_textbook_chapters";

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
      subjects: {}, expanded: new Set(), keyword: "", seq: 0, loaded: false
    };

    function setStatus(text) { stateEl.textContent = text; }

    function byOrder(a, b) {
      var ao = Number(a.sort_order) || 0;
      var bo = Number(b.sort_order) || 0;
      return ao - bo || Number(a.id) - Number(b.id);
    }

    function bookLabel(book) {
      return book.volume_name || book.name;
    }

    function subjectName(subjectId) {
      return state.subjects[subjectId] || "";
    }

    function select(li) {
      var old = tree.querySelector(".det-row.is-selected");
      if (old) old.classList.remove("is-selected");
      li.querySelector(".det-row").classList.add("is-selected");
    }

    var makeRow = S.bindTree(state.expanded, select);
    var childList = S.childList;

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
        state.subjects = {};
        (results[2].subjects || []).forEach(function (item) {
          state.subjects[item.id] = item.name;
        });
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
        state.loaded = true;
        render();
        var chapterTotal = Object.keys(state.chapters).reduce(function (sum, key) {
          return sum + countNodes(state.chapters[key]);
        }, 0);
        setStatus(state.keyword ? "" : "共 " + state.versions.length + " 版 · "
          + books.length + " 册 · " + chapterTotal + " 个章节节点。双击节点可改名。");
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

    function chapterRoots(book) {
      return state.chapters[book.id] || [];
    }

    function refresh(message) {
      return reloadAll().then(function () { if (message) setStatus(message); });
    }

    function renamed() {
      refresh("已改名。");
    }

    function removeVersion(version, anchor) {
      S.remove({ url: VERSION_URL, row: version, anchor: anchor, reload: reloadAll, setStatus: setStatus });
    }

    function addBook(version, anchor) {
      var siblings = state.books[version.id] || [];
      S.add({
        title: "在「" + version.name + "」下新增册次",
        message: "册次名只填“必修一 / 七年级上册”，完整书名保留版本与册次全称。",
        anchor: anchor,
        url: BOOK_URL,
        fields: [
          { key: "volume_name", label: "册次名", required: true, placeholder: "如 必修一" },
          { key: "name", label: "完整书名", required: true, placeholder: "如 人教A版数学必修一" },
          { key: "code", label: "册次编码", required: true, placeholder: "如 rja_m_1" }
        ],
        build: function (values) {
          return {
            name: values.name, code: values.code, volume_name: values.volume_name,
            version_id: version.id, subject_id: version.subject_id,
            sort_order: S.nextOrder(siblings)
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
          { key: "publisher", label: "出版社", placeholder: "如 人民教育出版社" }
        ],
        build: function (values) {
          return {
            name: values.name, code: values.code, publisher: values.publisher,
            subject_id: subjectId, sort_order: S.nextOrder(state.versions)
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

    function renderChapter(book, node, depth, crumb) {
      var chapter = node.chapter;
      var kids = node.children || [];
      var key = "h:" + chapter.id;
      var expanded = state.expanded.has(key);
      var box = kids.length ? childList(depth + 1, expanded) : null;
      return makeRow({
        level: Math.min(depth + 3, 5), depth: depth, name: chapter.name, sub: chapter.code,
        crumb: crumb,
        badge: kids.length ? kids.length + " 节" : "",
        key: key,
        hasChildren: kids.length > 0,
        expanded: expanded,
        children: box,
        addText: "节", addLabel: "在「" + chapter.name + "」下新增子章节",
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
            box.appendChild(renderChapter(book, kid, depth + 1, ""));
          });
        } : null
      });
    }

    function renderBook(version, book) {
      var roots = chapterRoots(book);
      var key = "b:" + book.id;
      var expanded = state.expanded.has(key);
      var box = childList(1, expanded);
      var full = book.name && book.name !== bookLabel(book) ? book.name : "";
      return makeRow({
        level: 2, depth: 1, name: bookLabel(book),
        sub: (full ? full + " · " : "") + (book.code || ""),
        badge: roots.length + " 章 · " + countNodes(roots) + " 节点",
        key: key,
        hasChildren: roots.length > 0,
        expanded: expanded,
        children: box,
        addText: "章", addLabel: "给「" + bookLabel(book) + "」新增顶层章",
        add: function (btn) { addChapterUnderBook(book, btn); },
        edit: {
          url: BOOK_URL + "/" + book.id, field: "volume_name",
          value: bookLabel(book), label: "册次名", onDone: renamed
        },
        remove: function (btn) { removeBook(book, btn); },
        lazy: roots.length ? function () {
          roots.forEach(function (node) {
            box.appendChild(renderChapter(book, node, 2, ""));
          });
        } : null
      });
    }

    function renderVersion(version) {
      var books = state.books[version.id] || [];
      var key = "v:" + version.id;
      var expanded = state.expanded.has(key);
      var box = books.length ? childList(1, expanded) : null;
      if (box) {
        books.forEach(function (book) { box.appendChild(renderBook(version, book)); });
      }
      var chapterTotal = books.reduce(function (sum, book) {
        return sum + countNodes(chapterRoots(book));
      }, 0);
      return makeRow({
        level: 1, depth: 0, name: version.name,
        sub: [version.publisher, version.code].filter(Boolean).join(" · "),
        tag: subjectName(version.subject_id),
        badge: books.length + " 册 · " + chapterTotal + " 章",
        key: key,
        hasChildren: books.length > 0,
        expanded: expanded,
        children: box,
        addText: "册", addLabel: "在「" + version.name + "」下新增册次",
        add: function (btn) { addBook(version, btn); },
        edit: {
          url: VERSION_URL + "/" + version.id, field: "name",
          value: version.name, label: "版本名称", onDone: renamed
        },
        remove: function (btn) { removeVersion(version, btn); }
      });
    }

    function renderSearch(keyword) {
      var needle = keyword.toLowerCase();
      var hits = 0;
      var shown = 0;
      var LIMIT = 300;
      function hit(value) {
        return value != null && String(value).toLowerCase().indexOf(needle) !== -1;
      }
      var ul = S.el("ul", "det-list");
      state.versions.forEach(function (version) {
        if (hit(version.name) || hit(version.code)) {
          hits += 1;
          ul.appendChild(renderVersion(version));
        }
        (state.books[version.id] || []).forEach(function (book) {
          var bookName = bookLabel(book);
          if (hit(bookName) || hit(book.name) || hit(book.code)) {
            hits += 1;
            var bookLi = renderBook(version, book);
            bookLi.querySelector(".det-crumb").textContent = version.name;
            ul.appendChild(bookLi);
          }
          function walk(nodes, trail) {
            nodes.forEach(function (node) {
              var chapter = node.chapter;
              if (hit(chapter.name) || hit(chapter.code)) {
                hits += 1;
                if (shown < LIMIT) {
                  var li = renderChapter(book, node, 2 + trail.length, "");
                  li.querySelector(".det-crumb").textContent =
                    version.name + " › " + bookName + (trail.length ? " › " + trail.join(" › ") : "");
                  ul.appendChild(li);
                  shown += 1;
                }
              }
              walk(node.children || [], trail.concat(chapter.name));
            });
          }
          walk(chapterRoots(book), []);
        });
      });
      tree.textContent = "";
      if (!hits) {
        tree.appendChild(S.el("p", "det-empty", "没有匹配的版本 / 册次 / 章节。"));
        count.textContent = "命中 0 项";
        return;
      }
      tree.appendChild(ul);
      count.textContent = hits > LIMIT ? "命中 " + hits + " 项（仅显示前 " + LIMIT + "）"
        : "命中 " + hits + " 项";
    }

    function render() {
      if (state.keyword) {
        renderSearch(state.keyword);
        return;
      }
      tree.textContent = "";
      var ul = S.el("ul", "det-list");
      state.versions.forEach(function (version) {
        ul.appendChild(renderVersion(version));
      });
      if (state.orphans.length) {
        var orphanOpen = state.expanded.has("v:orphan");
        var box = childList(1, orphanOpen);
        state.orphans.forEach(function (book) {
          box.appendChild(renderBook({ id: "orphan", name: "未挂版本", subject_id: null }, book));
        });
        ul.appendChild(makeRow({
          level: 1, depth: 0, name: "未挂版本", sub: "version_id 为空",
          badge: state.orphans.length + " 册",
          key: "v:orphan",
          hasChildren: true,
          expanded: orphanOpen,
          children: box
        }));
      }
      tree.appendChild(ul);
      var bookTotal = state.versions.reduce(function (sum, version) {
        return sum + (state.books[version.id] || []).length;
      }, state.orphans.length);
      var chapterTotal = Object.keys(state.chapters).reduce(function (sum, key) {
        return sum + countNodes(state.chapters[key]);
      }, 0);
      count.textContent = "共 " + state.versions.length + " 版 · " + bookTotal + " 册 · "
        + chapterTotal + " 章节";
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
