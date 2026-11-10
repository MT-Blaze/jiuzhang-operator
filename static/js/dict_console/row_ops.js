/**
 * 字典行操作（阶段二）：双击单元格编辑、新增行、删除防呆。
 * 编辑：双击或聚焦后 Enter/F2 变 input，blur 即 PUT 保存，Esc 放弃；
 * 删除：先确认再 DELETE，被引用时后端回 409，弹「已被引用，禁止删除」并列出引用来源。
 * 全部文案走 textContent，写请求经 DcClient.writeJson 自动取新鲜令牌。
 */
(function () {
  "use strict";

  function cellText(value) {
    return value == null ? "" : String(value);
  }

  function rowName(row) {
    return row.name || row.short_name || row.code || ("#" + row.id);
  }

  function flash(td) {
    td.classList.add("dc-cell-saved");
    window.setTimeout(function () { td.classList.remove("dc-cell-saved"); }, 900);
  }

  /** 双击 / 键盘进入编辑：input 替换单元格内容，blur 保存。 */
  function editCell(controller, td, row, field) {
    if (td.querySelector("input")) return;
    var original = cellText(row[field.key]);
    var input = document.createElement("input");
    input.type = "text";
    input.className = "dc-cell-input";
    input.value = original;
    input.setAttribute("aria-label", "编辑" + field.label);
    td.textContent = "";
    td.appendChild(input);
    input.focus();
    input.select();

    var done = false;
    function finish(save) {
      if (done) return;
      done = true;
      var value = input.value;
      if (!save || value === original) {
        td.textContent = original;
        return;
      }
      var payload = {};
      payload[field.key] = value;
      window.DcClient.writeJson(controller.url + "/" + row.id, payload, "PUT").then(function (saved) {
        row[field.key] = saved[field.key];
        td.textContent = cellText(saved[field.key]);
        flash(td);
      }).catch(function (error) {
        td.textContent = original;
        window.DcDialog.alert({ title: "保存失败", message: error.message, anchor: td });
      });
    }
    input.addEventListener("blur", function () { finish(true); });
    input.addEventListener("keydown", function (event) {
      if (event.key === "Enter") { event.preventDefault(); input.blur(); }
      if (event.key === "Escape") { event.preventDefault(); finish(false); td.focus(); }
    });
  }

  /** 新增行：表头下插一行空 input，保存走 POST，取消移除。 */
  function addRow(controller) {
    if (controller.els.tbody.querySelector(".dc-row-new")) return;
    var tr = document.createElement("tr");
    tr.className = "dc-row-new";
    var inputs = {};
    controller.fields.forEach(function (field) {
      var td = document.createElement("td");
      if (field.editable) {
        var input = document.createElement("input");
        input.type = "text";
        input.className = "dc-cell-input";
        input.placeholder = field.label;
        input.setAttribute("aria-label", "新增" + field.label);
        inputs[field.key] = input;
        td.appendChild(input);
        input.addEventListener("keydown", function (event) {
          if (event.key === "Escape") { event.preventDefault(); tr.remove(); }
        });
      } else {
        td.className = "dc-cell-id";
        td.textContent = "自动";
      }
      tr.appendChild(td);
    });
    var action = document.createElement("td");
    var save = document.createElement("button");
    save.type = "button";
    save.className = "dc-btn dc-btn-primary dc-row-btn";
    save.textContent = "保存";
    var cancel = document.createElement("button");
    cancel.type = "button";
    cancel.className = "dc-btn dc-row-btn";
    cancel.textContent = "取消";
    action.appendChild(save);
    action.appendChild(cancel);
    tr.appendChild(action);
    controller.els.tbody.insertBefore(tr, controller.els.tbody.firstChild);
    var first = inputs[Object.keys(inputs)[0]];
    if (first) first.focus();

    cancel.addEventListener("click", function () { tr.remove(); });
    save.addEventListener("click", function () {
      var payload = {};
      Object.keys(inputs).forEach(function (key) {
        if (inputs[key].value.trim() !== "") payload[key] = inputs[key].value;
      });
      save.disabled = true;
      save.setAttribute("aria-busy", "true");
      window.DcClient.writeJson(controller.url, payload, "POST").then(function () {
        tr.remove();
        controller.reload(true).then(function () { controller.setStatus("已新增一行。"); });
      }).catch(function (error) {
        save.disabled = false;
        save.setAttribute("aria-busy", "false");
        window.DcDialog.alert({ title: "新增失败", message: error.message, anchor: save });
      });
    });
  }

  function referenceMessage(error, row) {
    var detail = error.detail;
    var lines = ["「" + rowName(row) + "」已被引用，禁止删除。"];
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

  /** 删除：确认 → DELETE；409 被引用弹防呆对话框，成功则刷新表格。 */
  function deleteRow(controller, row, anchor) {
    window.DcDialog.open({
      title: "删除确认",
      message: "确认删除「" + rowName(row) + "」？此操作不可撤销。",
      confirmText: "删除",
      anchor: anchor,
      onConfirm: function () {
        window.DcClient.writeJson(controller.url + "/" + row.id, null, "DELETE").then(function () {
          controller.reload(false).then(function () {
            controller.setStatus("已删除「" + rowName(row) + "」。");
          });
        }).catch(function (error) {
          if (error.status === 409 && error.detail && error.detail.code === "referenced") {
            window.DcDialog.alert({
              title: "已被引用，禁止删除", message: referenceMessage(error, row), anchor: anchor
            });
          } else {
            window.DcDialog.alert({ title: "删除失败", message: error.message, anchor: anchor });
          }
        });
      }
    });
  }

  window.DcRowOps = { editCell: editCell, addRow: addRow, deleteRow: deleteRow };
})();