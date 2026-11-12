/**
 * 知识点与考向 · 折叠树（一条线钻到底）：册次 → 章节 → 主知识点 → 考向。
 * 逐级展开时才向上游拉数据；考向行最右一列是辅助知识点标签（DcLinkTags.mountCell），
 * 可全局搜索添加、点 × 解除、拖拽排序。章节 / 知识点 / 考向均支持双击改名、
 * 悬停删除，知识点在章节内可拖拽排序。
 * 整块下架：删本目录 linkage*.js + linkage CSS + panels.js 的 DcLinkage.mount 调用。
 */
(function () {
  "use strict";

  var CHAPTER_URL = "/api/bank/engine/dict/dim_textbook_chapters";
  var POINT_URL = "/api/bank/engine/dict/dim_knowledge_points";
  var DIRECTION_URL = "/api/bank/engine/dict/dim_exam_directions";

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function countNodes(nodes) {
    return (nodes || []).reduce(function (sum, node) {
      return sum + 1 + countNodes(node.children);
    }, 0);
  }

  function mount(panel, ctx) {
    var wrap = el("section", "dkl-wrap");
    wrap.setAttribute("aria-label", "知识点与考向折叠树");
    var head = el("div", "dkl-head");
    head.appendChild(el("p", "dkl-hint",
      "册次 → 章节 → 主知识点 → 考向；点箭头逐级展开，考向行右侧直接增删辅助知识点。"));
    var countEl = el("span", "dkl-count", "");
    head.appendChild(countEl);
    var state = el("p", "dkl-state", "");
    state.setAttribute("role", "status");
    state.setAttribute("aria-live", "polite");
    var tree = el("div", "dkl-tree");
    wrap.appendChild(head);
    wrap.appendChild(state);
    wrap.appendChild(tree);
    panel.appendChild(wrap);

    var expanded = { b: {}, c: {}, p: {} };
    var pointsCache = {};
    var directionsCache = {};
    var chapterReloaders = {};
    function setStatus(text) { state.textContent = text; }
    function dictController(url, reload) {
      return { url: url, ctx: ctx, reload: reload, setStatus: setStatus };
    }
    function editName(url, anchor, row) {
      window.DcRowOps.editCell({ url: url, ctx: ctx }, anchor, row, { key: "name", label: "名称" });
    }
    function nameButton(text, label, edit) {
      var button = el("button", "dkl-name", text);
      button.type = "button";
      button.title = "双击改名（F2）";
      button.setAttribute("aria-label", label + "：双击改名，F2 也可");
      button.addEventListener("dblclick", function () { edit(button); });
      button.addEventListener("keydown", function (event) {
        if (event.key !== "F2") return;
        event.preventDefault();
        edit(button);
      });
      return button;
    }
    function opButton(text, danger, label, onClick) {
      var button = el("button", "dkl-op" + (danger ? " dkl-op-danger" : ""), text);
      button.type = "button";
      button.setAttribute("aria-label", label);
      button.addEventListener("click", function () { onClick(button); });
      return button;
    }

    // ---------- 考向行（第三级） ----------
    function pointNode(chapter, point) {
      var li = el("li", "dkl-node dkl-point");
      li.setAttribute("data-id", String(point.id));
      li.setAttribute("role", "treeitem");
      li.draggable = true;
      var row = el("div", "dkl-row dkl-row-point");
      var grip = el("span", "dkl-grip", "⠿");
      grip.setAttribute("aria-hidden", "true");
      row.appendChild(grip);
      var caret = el("button", "dkl-caret", "▸");
      caret.type = "button";
      caret.setAttribute("aria-expanded", "false");
      caret.setAttribute("aria-label", "展开或折叠「" + point.name + "」的考向");
      row.appendChild(caret);
      row.appendChild(nameButton(point.name, "主知识点「" + point.name + "」", function (button) {
        editName(POINT_URL, button, point);
      }));
      var badge = el("span", "dkl-badge", "");
      row.appendChild(badge);
      var ops = el("div", "dkl-ops");
      var add = opButton("＋考向", false, "为「" + point.name + "」新增考向", function () {
        startAddDirection();
      });
      ops.appendChild(add);
      ops.appendChild(opButton("删除", true, "删除主知识点「" + point.name + "」", function (button) {
        window.DcRowOps.deleteRow(dictController(POINT_URL, function () {
          delete expanded.p[point.id];
          delete directionsCache[point.id];
          var reload = chapterReloaders[chapter.id];
          return reload ? reload() : Promise.resolve();
        }), point, button);
      }));
      row.appendChild(ops);
      li.appendChild(row);
      var children = el("ul", "dkl-list dkl-children dkl-direction-list");
      children.setAttribute("role", "group");
      children.hidden = true;
      li.appendChild(children);
      // 考向行里的拖拽 / Alt+方向键只服务标签，别冒泡成「拖动整个知识点」。
      children.addEventListener("dragstart", function (event) { event.stopPropagation(); });
      children.addEventListener("keydown", function (event) {
        if (!event.altKey) return;
        if (event.key === "ArrowUp" || event.key === "ArrowDown") event.stopPropagation();
      });
      var painted = false;
      function updateBadge() {
        var rows = directionsCache[point.id] || [];
        badge.textContent = rows.length + " 个考向";
        if (!rows.length && !children.querySelector(".dkl-dir-new")) {
          children.appendChild(el("li", "dkl-empty", "该知识点暂无考向，点「＋考向」新增。"));
        }
      }
      function dirHead() {
        var headLi = el("li", "dkl-dir-head");
        headLi.appendChild(el("span", "dkl-dir-col", "考向"));
        headLi.appendChild(el("span", "dkl-dir-col", "辅助知识点"));
        headLi.appendChild(el("span", "dkl-dir-col dkl-dir-col-ops", "操作"));
        return headLi;
      }
      function directionRow(dir) {
        var dirLi = el("li", "dkl-node dkl-direction");
        dirLi.setAttribute("data-direction-id", String(dir.id));
        dirLi.setAttribute("role", "treeitem");
        var dirRow = el("div", "dkl-row dkl-row-direction");
        dirRow.appendChild(nameButton(dir.name, "考向「" + dir.name + "」", function (button) {
          editName(DIRECTION_URL, button, dir);
        }));
        var cell = window.DcLinkTags.mountCell({
          directionId: dir.id,
          directionName: dir.name,
          primaryPointId: point.id,
          rowHost: dirLi,
          onChange: setStatus
        });
        dirRow.appendChild(cell.el);
        var dirOps = el("div", "dkl-ops");
        dirOps.appendChild(opButton("删除", true, "删除考向「" + dir.name + "」", function (button) {
          window.DcDialog.open({
            title: "删除确认",
            message: "确认删除考向「" + dir.name + "」？将同时解除它与当前知识点的关联。",
            confirmText: "删除",
            anchor: button,
            onConfirm: function () {
              window.DcClient.writeJson(
                "/api/bank/engine/linkage/points/" + point.id + "/directions/" + dir.id,
                null, "DELETE"
              ).then(function () {
                directionsCache[point.id] = (directionsCache[point.id] || []).filter(function (item) {
                  return item.id !== dir.id;
                });
                dirLi.remove();
                updateBadge();
                setStatus("已删除考向「" + dir.name + "」。");
              }).catch(function (error) {
                if (error.status === 409 && error.detail && error.detail.code === "referenced") {
                  window.DcDialog.alert({
                    title: "已被引用，无法删除",
                    message: window.DcRowOps.referenceMessage(error, dir),
                    anchor: button
                  });
                } else {
                  window.DcDialog.alert({ title: "删除失败", message: error.message, anchor: button });
                }
              });
            }
          });
        }));
        dirRow.appendChild(dirOps);
        dirLi.appendChild(dirRow);
        return dirLi;
      }
      function paintDirections() {
        var rows = directionsCache[point.id] || [];
        children.textContent = "";
        children.appendChild(dirHead());
        rows.forEach(function (dir) { children.appendChild(directionRow(dir)); });
        painted = true;
        updateBadge();
      }
      function ensureDirections(force) {
        if (!force && directionsCache[point.id]) {
          paintDirections();
          return Promise.resolve();
        }
        setStatus("正在读取「" + point.name + "」的考向…");
        return window.DcClient.fetchJson(
          "/api/bank/engine/linkage/points/" + point.id + "/directions"
        ).then(function (data) {
          directionsCache[point.id] = data.items || [];
          paintDirections();
          setStatus("");
        }).catch(function (error) {
          setStatus("考向加载失败：" + error.message);
        });
      }

      function openPoint() {
        expanded.p[point.id] = true;
        children.hidden = false;
        caret.textContent = "▾";
        caret.setAttribute("aria-expanded", "true");
        return painted ? Promise.resolve() : ensureDirections(false);
      }

      function closePoint() {
        expanded.p[point.id] = false;
        children.hidden = true;
        caret.textContent = "▸";
        caret.setAttribute("aria-expanded", "false");
      }

      caret.addEventListener("click", function () {
        if (children.hidden) openPoint(); else closePoint();
      });

      function startAddDirection() {
        var ready = children.hidden ? openPoint() : Promise.resolve();
        ready.then(function () {
          var input = document.createElement("input");
          input.type = "text";
          input.className = "dc-cell-input dkl-dir-input";
          input.placeholder = "新考向名称";
          input.setAttribute("aria-label", "新考向名称");
          var save = el("button", "dc-btn dc-btn-primary", "保存");
          save.type = "button";
          var cancel = el("button", "dc-btn", "取消");
          cancel.type = "button";
          var newLi = el("li", "dkl-node dkl-dir-new");
          var newRow = el("div", "dkl-row dkl-dir-new-row");
          newRow.appendChild(input);
          newRow.appendChild(save);
          newRow.appendChild(cancel);
          newLi.appendChild(newRow);
          var empty = children.querySelector(".dkl-empty");
          if (empty) empty.remove();
          var headLi = children.querySelector(".dkl-dir-head");
          children.insertBefore(newLi, headLi ? headLi.nextSibling : children.firstChild);
          input.focus();
          function finish() { newLi.remove(); updateBadge(); add.focus(); }
          cancel.addEventListener("click", finish);
          input.addEventListener("keydown", function (event) {
            if (event.key === "Escape") { event.preventDefault(); finish(); }
            if (event.key === "Enter") { event.preventDefault(); save.click(); }
          });
          save.addEventListener("click", function () {
            var name = input.value.trim();
            if (!name) { input.focus(); return; }
            save.disabled = true;
            save.setAttribute("aria-busy", "true");
            window.DcClient.writeJson(
              "/api/bank/engine/linkage/points/" + point.id + "/directions", { name: name }, "POST"
            ).then(function () {
              return ensureDirections(true);
            }).then(function () {
              setStatus("已新增考向「" + name + "」。");
              add.focus();
            }).catch(function (error) {
              save.disabled = false;
              save.removeAttribute("aria-busy");
              window.DcDialog.alert({ title: "新增失败", message: error.message, anchor: save });
            });
          });
        });
      }

      if (expanded.p[point.id]) openPoint(); else closePoint();
      return li;
    }

    // ---------- 章节（第一级，可嵌套） ----------

    function chapterNode(node) {
      var chapter = node.chapter;
      var li = el("li", "dkl-node dkl-chapter");
      li.setAttribute("data-chapter-id", String(chapter.id));
      li.setAttribute("role", "treeitem");
      var row = el("div", "dkl-row dkl-row-chapter");
      var caret = el("button", "dkl-caret", "▸");
      caret.type = "button";
      caret.setAttribute("aria-expanded", "false");
      caret.setAttribute("aria-label", "展开或折叠「" + chapter.name + "」");
      row.appendChild(caret);
      row.appendChild(nameButton(chapter.name, "章节「" + chapter.name + "」", function (button) {
        editName(CHAPTER_URL, button, chapter);
      }));
      // 现存章节编码多是 tp_* 技术码，只有纯数字编码（如 1.2）才值得露出来。
      if (chapter.code && /^[\d.]+$/.test(chapter.code)) row.appendChild(el("span", "dkl-sub", chapter.code));
      var badge = el("span", "dkl-badge", "");
      row.appendChild(badge);
      var ops = el("div", "dkl-ops");
      ops.appendChild(opButton("删除", true, "删除章节「" + chapter.name + "」", function (button) {
        window.DcRowOps.deleteRow(dictController(CHAPTER_URL, function () {
          delete expanded.c[chapter.id];
          load();
          return Promise.resolve();
        }), chapter, button);
      }));
      row.appendChild(ops);
      li.appendChild(row);
      var children = el("ul", "dkl-list dkl-children");
      children.setAttribute("role", "group");
      children.hidden = true;
      (node.children || []).forEach(function (child) { children.appendChild(chapterNode(child)); });
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
        rows.forEach(function (point) { pointList.appendChild(pointNode(chapter, point)); });
        if (!rows.length && !(node.children || []).length) {
          pointList.appendChild(el("li", "dkl-empty", "该章节暂无主知识点。"));
        }
        badge.textContent = rows.length + " 个知识点";
        pointsPainted = true;
      }

      function ensurePoints(force) {
        if (!force && pointsCache[chapter.id]) {
          paintPoints();
          return Promise.resolve();
        }
        setStatus("正在读取「" + chapter.name + "」的知识点…");
        return window.DcClient.fetchJson(
          "/api/bank/engine/linkage/chapters/" + chapter.id + "/points"
        ).then(function (data) {
          pointsCache[chapter.id] = data.items || [];
          paintPoints();
          setStatus("");
        }).catch(function (error) {
          setStatus("知识点加载失败：" + error.message);
        });
      }
      chapterReloaders[chapter.id] = function () { return ensurePoints(true); };

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

    // ---------- 册次（顶层，默认展开） ----------

    function bookNode(item) {
      var book = item.textbook || {};
      var chapters = item.chapters || [];
      var li = el("li", "dkl-node dkl-book");
      li.setAttribute("data-book-id", String(book.id));
      li.setAttribute("role", "treeitem");
      var row = el("div", "dkl-row dkl-row-book");
      var children = el("ul", "dkl-list dkl-children");
      children.setAttribute("role", "group");
      chapters.forEach(function (child) { children.appendChild(chapterNode(child)); });
      li.appendChild(children);

      var caret;
      if (chapters.length) {
        caret = el("button", "dkl-caret", "▾");
        caret.type = "button";
        caret.setAttribute("aria-label", "展开或折叠「" + (book.volume_name || book.name) + "」");
        caret.addEventListener("click", function () {
          expanded.b[book.id] = expanded.b[book.id] === false;
          paintBook();
        });
      } else {
        caret = el("span", "dkl-caret dkl-caret-empty", "");
        caret.setAttribute("aria-hidden", "true");
      }
      row.appendChild(caret);
      row.appendChild(el("span", "dkl-book-name", book.volume_name || book.name));
      if (book.name && book.name !== book.volume_name) {
        row.appendChild(el("span", "dkl-sub", book.name));
      }
      row.appendChild(el("span", "dkl-badge", chapters.length + " 章"));
      li.insertBefore(row, children);

      function paintBook() {
        var open = expanded.b[book.id] !== false;
        children.hidden = !open;
        caret.textContent = open ? "▾" : "▸";
        caret.setAttribute("aria-expanded", open ? "true" : "false");
      }
      paintBook();
      return li;
    }

    // ---------- 装载 ----------

    function load() {
      var versionId = ctx.globals.query().version_id;
      tree.textContent = "";
      chapterReloaders = {};
      countEl.textContent = "";
      if (!versionId) {
        setStatus("请先在右侧全局设置选择教材版本。");
        return;
      }
      setStatus("正在读取章节树…");
      window.DcClient.fetchJson(
        "/api/bank/engine/linkage/version-tree?version_id=" + encodeURIComponent(versionId)
      ).then(function (data) {
        if (!wrap.isConnected) return;
        var books = data.items || [];
        if (!books.length) {
          setStatus("该版本下还没有册次，先到「教材体系」建册次与章节。");
          return;
        }
        var ul = el("ul", "dkl-list dkl-books");
        ul.setAttribute("role", "tree");
        books.forEach(function (item) { ul.appendChild(bookNode(item)); });
        tree.appendChild(ul);
        var nodes = books.reduce(function (sum, item) { return sum + countNodes(item.chapters); }, 0);
        countEl.textContent = "共 " + books.length + " 册 · " + nodes + " 个章节节点";
        setStatus("");
      }).catch(function (error) {
        if (!wrap.isConnected) return;
        setStatus("章节树加载失败：" + error.message);
      });
    }

    function onGlobals() {
      if (!wrap.isConnected) {
        document.removeEventListener(window.DcGlobals.EVENT_NAME, onGlobals);
        return;
      }
      expanded = { b: {}, c: {}, p: {} };
      pointsCache = {};
      directionsCache = {};
      load();
    }
    document.addEventListener(window.DcGlobals.EVENT_NAME, onGlobals);
    load();
    return wrap;
  }

  window.DcLinkTree = { mount: mount };
})();
