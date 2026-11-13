/**
 * 知识点与考向树 · 考向清单（2026-11-13 从 linkage_tree.js 拆出）：
 * 每个主知识点自己懒加载自己的考向，末位低饱和幽灵行新增、空状态带「＋ 添加」。
 * 双击考向改名、悬停删除；辅助知识点标签仍由 DcLinkTags.mountCell 负责。
 * 整块下架：删本文件、linkage_tree.js 的 DcLinkageDirections.mount 调用即可。
 */
(function () {
  "use strict";

  var DIRECTION_URL = "/api/bank/engine/dict/dim_exam_directions";

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function alertError(title, error, anchor) {
    window.DcDialog.alert({
      title: title,
      message: error && error.message ? error.message : String(error),
      anchor: anchor
    });
  }

  /**
   * spec = {point, prefix, status(text), onCount(count)}；
   * 返回 {el, open(), close(), ensure(force), add(anchor)}，ul 由调用方挂进知识点行。
   */
  function mount(spec) {
    var point = spec.point;
    var prefix = spec.prefix;
    var G = window.DcLinkGuide;
    var list = el("ul", "dkl-list dkl-children dkl-direction-list");
    list.setAttribute("role", "group");
    list.hidden = true;
    // 考向行里的拖拽 / Alt+方向键只服务标签，别冒泡成「拖动整个知识点」。
    list.addEventListener("dragstart", function (event) { event.stopPropagation(); });
    list.addEventListener("keydown", function (event) {
      if (!event.altKey) return;
      if (event.key === "ArrowUp" || event.key === "ArrowDown") event.stopPropagation();
    });

    var rows = null;
    var painted = false;

    function setStatus(text) {
      if (typeof spec.status === "function") spec.status(text);
    }

    function notifyCount() {
      if (typeof spec.onCount === "function") spec.onCount((rows || []).length);
    }

    function dirHead() {
      var headLi = el("li", "dkl-dir-head");
      var main = el("div", "dkl-dir-main");
      headLi.appendChild(G.lines(prefix, null));
      main.appendChild(G.span(prefix, false, true, true));
      main.appendChild(el("span", "dkl-dir-col", "考向"));
      headLi.appendChild(main);
      headLi.appendChild(el("span", "dkl-dir-col", "辅助知识点"));
      headLi.appendChild(el("span", "dkl-dir-col dkl-dir-col-ops", "操作"));
      return headLi;
    }

    function directionRow(dir, last) {
      var dirLi = el("li", "dkl-node dkl-direction");
      dirLi.setAttribute("data-direction-id", String(dir.id));
      dirLi.setAttribute("role", "treeitem");
      var dirRow = el("div", "dkl-row dkl-row-direction");
      dirRow.appendChild(G.lines(prefix, last));
      var main = el("div", "dkl-dir-main");
      main.appendChild(G.span(prefix, last, false, true));
      main.appendChild(G.nameButton(dir.name, "考向「" + dir.name + "」", function (button) {
        window.DcRowOps.editCell({ url: DIRECTION_URL }, button, dir,
          { key: "name", label: "名称" });
      }));
      dirRow.appendChild(main);
      var cell = window.DcLinkTags.mountCell({
        directionId: dir.id,
        directionName: dir.name,
        primaryPointId: point.id,
        rowHost: dirLi,
        onChange: setStatus
      });
      dirRow.appendChild(cell.el);
      var dirOps = el("div", "dkl-ops");
      dirOps.appendChild(G.opButton("删除", true, "删除考向「" + dir.name + "」", function (button) {
        removeDirection(dir, button, dirLi);
      }));
      dirRow.appendChild(dirOps);
      dirLi.appendChild(dirRow);
      return dirLi;
    }

    function removeDirection(dir, anchor, dirLi) {
      window.DcDialog.open({
        title: "删除确认",
        message: "确认删除考向「" + dir.name + "」？将同时解除它与当前知识点的关联。",
        confirmText: "删除",
        anchor: anchor,
        onConfirm: function () {
          window.DcClient.writeJson(
            "/api/bank/engine/linkage/points/" + point.id + "/directions/" + dir.id,
            null, "DELETE"
          ).then(function () {
            rows = (rows || []).filter(function (item) { return item.id !== dir.id; });
            dirLi.remove();
            if (!rows.length) paintDirections();
            else notifyCount();
            setStatus("已删除考向「" + dir.name + "」。");
          }).catch(function (error) {
            if (error.status === 409 && error.detail && error.detail.code === "referenced") {
              window.DcDialog.alert({
                title: "已被引用，无法删除",
                message: window.DcRowOps.referenceMessage(error, dir),
                anchor: anchor
              });
            } else {
              alertError("删除失败", error, anchor);
            }
          });
        }
      });
    }

    function add(anchor) {
      window.DcLinkageAdd.direction({
        point: point, host: list, prefix: prefix, anchor: anchor,
        before: list.querySelector(":scope > .dc-ghost-item")
          || list.querySelector(":scope > .dkl-empty"),
        onDone: function () {
          return ensure(true).then(function () {
            setStatus("已新增考向。");
          });
        }
      });
    }

    function paintDirections() {
      list.textContent = "";
      list.appendChild(dirHead());
      if (!rows.length) {
        list.appendChild(G.empty(prefix, "该知识点暂无考向。", {
          label: "为「" + point.name + "」新增考向",
          onClick: add
        }));
      } else {
        rows.forEach(function (dir) {
          list.appendChild(directionRow(dir, false));
        });
        list.appendChild(G.ghost(prefix, "添加考向",
          "为「" + point.name + "」新增考向", add));
      }
      painted = true;
      notifyCount();
    }

    function ensure(force) {
      if (!force && rows) {
        paintDirections();
        return Promise.resolve();
      }
      return window.DcClient.fetchJson(
        "/api/bank/engine/linkage/points/" + point.id + "/directions"
      ).then(function (data) {
        rows = data.items || [];
        paintDirections();
      }).catch(function (error) {
        list.textContent = "";
        list.appendChild(G.empty(prefix, "考向加载失败：" + error.message));
      });
    }

    return {
      el: list,
      open: function () {
        list.hidden = false;
        return painted ? Promise.resolve() : ensure(false);
      },
      close: function () { list.hidden = true; },
      ensure: ensure,
      add: add
    };
  }

  window.DcLinkageDirections = { mount: mount };
})();
