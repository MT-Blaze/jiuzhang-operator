/**
 * 四栏联动 · 最右栏辅助知识点标签（阶段三，v9 起修正主辅口径）。
 * 选中考向后：标签只来自 knowledge_exam_map 的辅助行（sort_order > 0），
 * 并排除当前选中的主知识点——主知识点绝不会出现在自己的辅助列表里。
 * 全局搜索知识点（/api/bank/engine/knowledge-points）一键挂为标签，
 * 可移除（只解除关联）、拖拽 / Alt+方向键排序，刷新后顺序仍在。
 */
(function () {
  "use strict";

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function mount(body) {
    body.textContent = "";
    var search = document.createElement("input");
    search.type = "search";
    search.className = "dc-table-search dcl-tag-search";
    search.placeholder = "全局搜索知识点…";
    search.setAttribute("aria-label", "全局搜索知识点以添加辅助标签");
    search.disabled = true;
    var results = el("ul", "dcl-search-results");
    results.setAttribute("aria-label", "知识点搜索结果");
    results.hidden = true;
    var state = el("p", "dcl-state", "");
    state.setAttribute("role", "status");
    state.setAttribute("aria-live", "polite");
    var list = el("ul", "dcl-list dcl-tag-list");
    list.setAttribute("aria-label", "辅助知识点标签清单");
    body.appendChild(search);
    body.appendChild(results);
    body.appendChild(state);
    body.appendChild(list);
    var directionId = null;
    var pointId = null;
    var rows = [];

    function render() {
      list.textContent = "";
      if (!rows.length) {
        list.appendChild(el("li", "dcl-empty", directionId ? "暂无辅助标签，用上方搜索添加。" : "先在右栏选择考向。"));
        return;
      }
      rows.forEach(function (point) {
        var li = el("li", "dcl-item dcl-tag");
        li.setAttribute("data-id", String(point.id));
        li.draggable = true;
        var grip = el("span", "dcl-grip", "⠿");
        grip.setAttribute("aria-hidden", "true");
        var name = el("span", "dcl-tag-name", point.name);
        var del = el("button", "dc-btn dcl-tag-del", "×");
        del.type = "button";
        del.setAttribute("aria-label", "移除辅助标签 " + point.name);
        del.addEventListener("click", function () {
          window.DcClient.writeJson(
            "/api/bank/engine/linkage/directions/" + directionId + "/tags/" + point.id,
            null, "DELETE"
          ).then(function () {
            load(directionId).then(function () { state.textContent = "已移除「" + point.name + "」。"; });
          }).catch(function (error) {
            window.DcDialog.alert({ title: "移除失败", message: error.message, anchor: del });
          });
        });
        li.appendChild(grip);
        li.appendChild(name);
        li.appendChild(del);
        list.appendChild(li);
      });
    }

    function load(id, primaryPointId) {
      directionId = id;
      // undefined = 保留当前主知识点；null = 上游清空；数字 = 新选中的主知识点。
      if (primaryPointId !== undefined) pointId = primaryPointId;
      rows = [];
      search.disabled = !id;
      search.value = "";
      results.textContent = "";
      results.hidden = true;
      if (!id) { render(); state.textContent = ""; return Promise.resolve(); }
      state.textContent = "正在读取辅助标签…";
      var url = "/api/bank/engine/linkage/directions/" + id + "/tags";
      if (pointId) url += "?exclude_point_id=" + encodeURIComponent(pointId);
      return window.DcClient.fetchJson(url).then(function (data) {
        if (!body.isConnected) return;
        rows = data.items || [];
        render();
        state.textContent = "共 " + rows.length + " 个辅助标签";
      }).catch(function (error) {
        if (!body.isConnected) return;
        state.textContent = "加载失败：" + error.message;
      });
    }

    function addTag(point, button) {
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      window.DcClient.writeJson(
        "/api/bank/engine/linkage/directions/" + directionId + "/tags",
        { point_id: point.point_id }, "POST"
      ).then(function () {
        return load(directionId);
      }).then(function () {
        state.textContent = "已添加辅助标签「" + point.name + "」。";
      }).catch(function (error) {
        button.disabled = false;
        button.setAttribute("aria-busy", "false");
        window.DcDialog.alert({ title: "添加失败", message: error.message, anchor: button });
      });
    }

    function renderResults(items) {
      results.textContent = "";
      if (!items.length) {
        results.appendChild(el("li", "dcl-empty", "无匹配知识点。"));
        results.hidden = false;
        return;
      }
      var tagged = {};
      rows.forEach(function (point) { tagged[point.id] = true; });
      items.forEach(function (point) {
        var li = el("li", "dcl-search-item");
        var button = el("button", "dc-btn dcl-search-add", "添加");
        button.type = "button";
        button.setAttribute("aria-label", "添加「" + point.name + "」为辅助标签");
        if (point.point_id === pointId) {
          button.disabled = true;
          button.textContent = "主知识点";
        } else if (tagged[point.point_id]) {
          button.disabled = true;
          button.textContent = "已添加";
        }
        button.addEventListener("click", function () { addTag(point, button); });
        li.appendChild(el("span", "dcl-search-name", point.name));
        li.appendChild(button);
        results.appendChild(li);
      });
      results.hidden = false;
    }

    var timer = null;
    search.addEventListener("input", function () {
      window.clearTimeout(timer);
      timer = window.setTimeout(function () {
        var keyword = search.value.trim();
        if (!directionId || !keyword) { results.textContent = ""; results.hidden = true; return; }
        window.DcClient.fetchJson(
          "/api/bank/engine/knowledge-points?q=" + encodeURIComponent(keyword) + "&limit=8"
        ).then(function (data) {
          if (!body.isConnected || search.value.trim() !== keyword) return;
          renderResults(data.items || []);
        }).catch(function (error) {
          if (!body.isConnected) return;
          state.textContent = "搜索失败：" + error.message;
        });
      }, 250);
    });

    window.DcDnd.attach(list, {
      onOrder: function (ids) {
        if (!directionId || !ids.length) return;
        var payload = { point_ids: ids };
        if (pointId) payload.exclude_point_id = Number(pointId);
        window.DcClient.writeJson(
          "/api/bank/engine/linkage/directions/" + directionId + "/tags/order",
          payload, "PUT"
        ).then(function () {
          var byId = {};
          rows.forEach(function (point) { byId[point.id] = point; });
          rows = ids.map(function (pid) { return byId[pid]; }).filter(Boolean);
          state.textContent = "排序已保存。";
        }).catch(function (error) {
          window.DcDialog.alert({ title: "排序保存失败", message: error.message });
          load(directionId);
        });
      }
    });

    render();
    return { load: load };
  }

  window.DcLinkTags = { mount: mount };
})();