/**
 * 四栏联动 · 中栏章节知识点（阶段三）。
 * 来自 chapter_knowledge_map 关联：单击选中驱动右栏，双击 / F2 改名
 * （复用 DcRowOps.editCell → PUT /dict/dim_knowledge_points），
 * 拖拽或 Alt+方向键排序 → sort_order 持久化到桥表，刷新仍在。
 */
(function () {
  "use strict";

  var POINT_URL = "/api/bank/engine/dict/dim_knowledge_points";

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function mount(body, hooks) {
    body.textContent = "";
    var state = el("p", "dcl-state", "");
    state.setAttribute("role", "status");
    state.setAttribute("aria-live", "polite");
    var list = el("ul", "dcl-list");
    list.setAttribute("aria-label", "章节知识点清单");
    body.appendChild(state);
    body.appendChild(list);
    var chapterId = null;
    var rows = [];
    var selectedId = null;

    function editName(button, point) {
      window.DcRowOps.editCell({ url: POINT_URL }, button, point, { key: "name", label: "名称" });
    }

    function render() {
      list.textContent = "";
      if (!rows.length) {
        list.appendChild(el("li", "dcl-empty", chapterId ? "该章节暂无关联知识点。" : "先在左栏选择章节。"));
        return;
      }
      rows.forEach(function (point) {
        var li = el("li", "dcl-item");
        li.setAttribute("data-id", String(point.id));
        li.draggable = true;
        if (point.id === selectedId) li.classList.add("dcl-selected");
        var grip = el("span", "dcl-grip", "⠿");
        grip.setAttribute("aria-hidden", "true");
        var button = el("button", "dcl-item-main", point.name);
        button.type = "button";
        button.setAttribute("aria-label", "知识点「" + point.name + "」：单击选中，双击改名，Alt+方向键排序");
        button.addEventListener("click", function () {
          selectedId = point.id;
          Array.prototype.forEach.call(list.children, function (item) {
            item.classList.toggle("dcl-selected", item.getAttribute("data-id") === String(point.id));
          });
          hooks.onSelect(point.id);
        });
        button.addEventListener("dblclick", function () { editName(button, point); });
        button.addEventListener("keydown", function (event) {
          if (event.key === "F2") { event.preventDefault(); editName(button, point); }
        });
        li.appendChild(grip);
        li.appendChild(button);
        list.appendChild(li);
      });
    }

    function load(id) {
      chapterId = id;
      selectedId = null;
      rows = [];
      if (!id) {
        render();
        state.textContent = "";
        return Promise.resolve();
      }
      state.textContent = "正在读取知识点…";
      return window.DcClient.fetchJson(
        "/api/bank/engine/linkage/chapters/" + id + "/points"
      ).then(function (data) {
        if (!body.isConnected) return;
        rows = data.items || [];
        render();
        state.textContent = "共 " + rows.length + " 个知识点";
      }).catch(function (error) {
        if (!body.isConnected) return;
        state.textContent = "加载失败：" + error.message;
      });
    }

    window.DcDnd.attach(list, {
      onOrder: function (ids) {
        if (!chapterId || !ids.length) return;
        window.DcClient.writeJson(
          "/api/bank/engine/linkage/chapters/" + chapterId + "/points/order",
          { point_ids: ids }, "PUT"
        ).then(function () {
          var byId = {};
          rows.forEach(function (point) { byId[point.id] = point; });
          rows = ids.map(function (id) { return byId[id]; }).filter(Boolean);
          state.textContent = "排序已保存。";
        }).catch(function (error) {
          window.DcDialog.alert({ title: "排序保存失败", message: error.message });
          load(chapterId);
        });
      }
    });

    render();
    return { load: load };
  }

  window.DcLinkPoints = { mount: mount };
})();