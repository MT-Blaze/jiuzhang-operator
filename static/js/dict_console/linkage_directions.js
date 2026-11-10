/**
 * 四栏联动 · 右栏考向清单（阶段三）。
 * 来自 knowledge_exam_map 关联：新增考向（学科继承知识点）、双击 / F2 改名、
 * 删除走阶段二防呆——排除当前关联后仍被引用 → 409 + 「已被引用，禁止删除」。
 * 写请求全部经 DcClient.writeJson（一次性轮换令牌）。
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

  function referenceMessage(error, name) {
    var detail = error.detail;
    var lines = ["「" + name + "」已被引用，禁止删除。"];
    var refs = detail && Array.isArray(detail.references) ? detail.references : [];
    if (refs.length) {
      lines.push("", "引用来源：");
      refs.forEach(function (hit) {
        lines.push("· " + hit.label + "（" + hit.column + "）：" + hit.count + " 行");
      });
      lines.push("", "请先处理这些引用，再回来删除。");
    }
    return lines.join("\n");
  }

  function mount(body, hooks) {
    body.textContent = "";
    var tools = el("div", "dcl-tools");
    var add = el("button", "dc-btn dcl-add", "新增考向");
    add.type = "button";
    add.disabled = true;
    tools.appendChild(add);
    var state = el("p", "dcl-state", "");
    state.setAttribute("role", "status");
    state.setAttribute("aria-live", "polite");
    var list = el("ul", "dcl-list");
    list.setAttribute("aria-label", "考向清单");
    body.appendChild(tools);
    body.appendChild(state);
    body.appendChild(list);
    var pointId = null;
    var rows = [];
    var selectedId = null;

    function remove(row, anchor) {
      window.DcDialog.open({
        title: "删除确认",
        message: "确认删除考向「" + row.name + "」？将同时解除它与当前知识点的关联。",
        confirmText: "删除",
        anchor: anchor,
        onConfirm: function () {
          window.DcClient.writeJson(
            "/api/bank/engine/linkage/points/" + pointId + "/directions/" + row.id,
            null, "DELETE"
          ).then(function () {
            if (selectedId === row.id) { selectedId = null; hooks.onSelect(null); }
            load(pointId).then(function () { state.textContent = "已删除「" + row.name + "」。"; });
          }).catch(function (error) {
            if (error.status === 409 && error.detail && error.detail.code === "referenced") {
              window.DcDialog.alert({
                title: "已被引用，禁止删除", message: referenceMessage(error, row.name), anchor: anchor
              });
            } else {
              window.DcDialog.alert({ title: "删除失败", message: error.message, anchor: anchor });
            }
          });
        }
      });
    }

    function render() {
      list.textContent = "";
      if (!rows.length) {
        list.appendChild(el("li", "dcl-empty", pointId ? "该知识点暂无关联考向，点【新增考向】建立。" : "先在中栏选择知识点。"));
        return;
      }
      rows.forEach(function (row) {
        var li = el("li", "dcl-item");
        li.setAttribute("data-id", String(row.id));
        if (row.id === selectedId) li.classList.add("dcl-selected");
        var button = el("button", "dcl-item-main", row.name);
        button.type = "button";
        button.setAttribute("aria-label", "考向「" + row.name + "」：单击选中，双击改名");
        button.addEventListener("click", function () {
          selectedId = row.id;
          Array.prototype.forEach.call(list.children, function (item) {
            item.classList.toggle("dcl-selected", item.getAttribute("data-id") === String(row.id));
          });
          hooks.onSelect(row.id);
        });
        button.addEventListener("dblclick", function () {
          window.DcRowOps.editCell({ url: DIRECTION_URL }, button, row, { key: "name", label: "名称" });
        });
        button.addEventListener("keydown", function (event) {
          if (event.key === "F2") {
            event.preventDefault();
            window.DcRowOps.editCell({ url: DIRECTION_URL }, button, row, { key: "name", label: "名称" });
          }
        });
        var del = el("button", "dc-btn dcl-item-del", "删除");
        del.type = "button";
        del.setAttribute("aria-label", "删除考向 " + row.name);
        del.addEventListener("click", function () { remove(row, del); });
        li.appendChild(button);
        li.appendChild(del);
        list.appendChild(li);
      });
    }

    function load(id) {
      pointId = id;
      selectedId = null;
      rows = [];
      add.disabled = !id;
      if (!id) { render(); state.textContent = ""; return Promise.resolve(); }
      state.textContent = "正在读取考向…";
      return window.DcClient.fetchJson(
        "/api/bank/engine/linkage/points/" + id + "/directions"
      ).then(function (data) {
        if (!body.isConnected) return;
        rows = data.items || [];
        render();
        state.textContent = "共 " + rows.length + " 个考向";
      }).catch(function (error) {
        if (!body.isConnected) return;
        state.textContent = "加载失败：" + error.message;
      });
    }

    add.addEventListener("click", function () {
      if (!pointId || list.querySelector(".dcl-item-new")) return;
      var li = el("li", "dcl-item dcl-item-new");
      var input = document.createElement("input");
      input.type = "text";
      input.className = "dc-cell-input dcl-new-input";
      input.placeholder = "新考向名称";
      input.setAttribute("aria-label", "新考向名称");
      var save = el("button", "dc-btn dc-btn-primary dcl-item-btn", "保存");
      save.type = "button";
      var cancel = el("button", "dc-btn dcl-item-btn", "取消");
      cancel.type = "button";
      li.appendChild(input);
      li.appendChild(save);
      li.appendChild(cancel);
      list.insertBefore(li, list.firstChild);
      input.focus();
      cancel.addEventListener("click", function () { li.remove(); add.focus(); });
      input.addEventListener("keydown", function (event) {
        if (event.key === "Escape") { event.preventDefault(); li.remove(); add.focus(); }
        if (event.key === "Enter") { event.preventDefault(); save.click(); }
      });
      save.addEventListener("click", function () {
        var name = input.value.trim();
        if (!name) { input.focus(); return; }
        save.disabled = true;
        save.setAttribute("aria-busy", "true");
        window.DcClient.writeJson(
          "/api/bank/engine/linkage/points/" + pointId + "/directions", { name: name }, "POST"
        ).then(function () {
          li.remove();
          load(pointId).then(function () { state.textContent = "已新增考向「" + name + "」。"; });
        }).catch(function (error) {
          save.disabled = false;
          save.setAttribute("aria-busy", "false");
          window.DcDialog.alert({ title: "新增失败", message: error.message, anchor: save });
        });
      });
    });

    render();
    return { load: load };
  }

  window.DcLinkDirections = { mount: mount };
})();