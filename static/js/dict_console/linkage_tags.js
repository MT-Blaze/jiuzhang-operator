/**
 * 知识点与考向树 · 考向行内的辅助知识点单元格。
 * 每个考向自己拉自己的辅助标签（/linkage/directions/{id}/tags），
 * ＋ 打开全局搜索，点添加即建关联；标签旁的 × 只解除关联，不删知识点本体。
 * 标签支持拖拽 / Alt+方向键排序，顺序落 knowledge_exam_map.sort_order。
 * 整块下架：删本文件、linkage_tree.js 的 DcLinkTags.mountCell 调用与 dkl-* CSS。
 */
(function () {
  "use strict";

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

  function tagsUrl(directionId) {
    return "/api/bank/engine/linkage/directions/" + directionId + "/tags";
  }

  /** spec: {directionId, directionName, primaryPointId, rowHost, onChange}。 */
  function mountCell(spec) {
    var host = el("div", "dkl-tags-cell");
    var list = el("ul", "dkl-tag-list");
    list.setAttribute("aria-label", "「" + spec.directionName + "」的辅助知识点标签");
    var add = el("button", "dkl-tag-add", "＋");
    add.type = "button";
    add.title = "从全局搜索添加辅助知识点";
    add.setAttribute("aria-label", "为「" + spec.directionName + "」添加辅助知识点");
    host.appendChild(list);
    host.appendChild(add);

    var rows = null;
    var pop = null;
    var timer = null;

    function notify(text) {
      if (typeof spec.onChange === "function") spec.onChange(text);
    }

    function render() {
      list.textContent = "";
      if (!rows) {
        list.appendChild(el("li", "dkl-tag-empty", "读取中…"));
        return;
      }
      if (!rows.length) {
        list.appendChild(el("li", "dkl-tag-empty", "无"));
        return;
      }
      rows.forEach(function (tag) {
        var chip = el("li", "dkl-tag");
        chip.setAttribute("data-id", String(tag.id));
        chip.draggable = true;
        chip.appendChild(el("span", "dkl-tag-name", tag.name));
        var remove = el("button", "dkl-tag-x", "\u00D7");
        remove.type = "button";
        remove.setAttribute("aria-label", "解除辅助知识点「" + tag.name + "」");
        remove.addEventListener("click", function (event) {
          event.stopPropagation();
          removeTag(tag, remove);
        });
        chip.appendChild(remove);
        list.appendChild(chip);
      });
    }

    function load() {
      var url = tagsUrl(spec.directionId)
        + "?exclude_point_id=" + encodeURIComponent(spec.primaryPointId);
      return window.DcClient.fetchJson(url).then(function (data) {
        rows = data.items || [];
        render();
      }).catch(function (error) {
        rows = null;
        render();
        notify("辅助标签加载失败：" + error.message);
      });
    }

    function removeTag(tag, anchor) {
      window.DcClient.writeJson(tagsUrl(spec.directionId) + "/" + tag.id, null, "DELETE")
        .then(function () {
          rows = rows.filter(function (row) { return row.id !== tag.id; });
          render();
          notify("已解除辅助知识点「" + tag.name + "」。");
        })
        .catch(function (error) { alertError("解除失败", error, anchor); });
    }

    function closePop() {
      if (!pop) return;
      pop.remove();
      pop = null;
      add.focus();
    }

    function addTag(point, button) {
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      window.DcClient.writeJson(tagsUrl(spec.directionId), { point_id: point.point_id }, "POST")
        .then(function () {
          closePop();
          return load();
        })
        .then(function () { notify("已添加辅助知识点「" + point.name + "」。"); })
        .catch(function (error) {
          button.disabled = false;
          button.removeAttribute("aria-busy");
          alertError("添加失败", error, button);
        });
    }

    function renderResults(items, results) {
      results.textContent = "";
      if (!items.length) {
        results.appendChild(el("li", "dkl-tag-empty", "没有匹配的知识点。"));
        return;
      }
      var tagged = {};
      (rows || []).forEach(function (row) { tagged[row.id] = true; });
      items.forEach(function (point) {
        var li = el("li", "dkl-tag-result");
        li.appendChild(el("span", "dkl-tag-result-name", point.name));
        var button = el("button", "dc-btn dkl-tag-result-add", "添加");
        button.type = "button";
        if (Number(point.point_id) === Number(spec.primaryPointId)) {
          button.disabled = true;
          button.textContent = "主知识点";
        } else if (tagged[point.point_id]) {
          button.disabled = true;
          button.textContent = "已添加";
        } else {
          button.addEventListener("click", function () { addTag(point, button); });
        }
        li.appendChild(button);
        results.appendChild(li);
      });
    }

    function openPop() {
      if (pop) return;
      var box = el("div", "dkl-tag-pop");
      var input = document.createElement("input");
      input.type = "search";
      input.className = "dc-table-search dkl-tag-input";
      input.placeholder = "全局搜索知识点…";
      input.setAttribute("aria-label", "搜索知识点以添加到「" + spec.directionName + "」");
      var results = el("ul", "dkl-tag-results");
      var tools = el("div", "dkl-tag-pop-tools");
      var close = el("button", "dc-btn dkl-tag-pop-close", "关闭");
      close.type = "button";
      close.addEventListener("click", closePop);
      tools.appendChild(close);
      box.appendChild(input);
      box.appendChild(results);
      box.appendChild(tools);
      spec.rowHost.appendChild(box);
      pop = box;
      input.focus();

      input.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
          event.preventDefault();
          event.stopPropagation();
          closePop();
        }
      });
      input.addEventListener("input", function () {
        window.clearTimeout(timer);
        var keyword = input.value.trim();
        if (!keyword) {
          results.textContent = "";
          return;
        }
        timer = window.setTimeout(function () {
          window.DcClient.fetchJson(
            "/api/bank/engine/knowledge-points?q=" + encodeURIComponent(keyword) + "&limit=8"
          ).then(function (data) {
            if (!pop || input.value.trim() !== keyword) return;
            renderResults(data.items || [], results);
          }).catch(function (error) { alertError("搜索失败", error, input); });
        }, 250);
      });
    }

    add.addEventListener("click", openPop);

    window.DcDnd.attach(list, {
      onOrder: function (ids) {
        var payload = { point_ids: ids, exclude_point_id: Number(spec.primaryPointId) };
        window.DcClient.writeJson(tagsUrl(spec.directionId) + "/order", payload, "PUT")
          .then(function () {
            var byId = {};
            (rows || []).forEach(function (row) { byId[row.id] = row; });
            rows = ids.map(function (id) { return byId[id]; }).filter(Boolean);
            notify("辅助标签排序已保存。");
          })
          .catch(function (error) {
            alertError("排序保存失败", error, add);
            load();
          });
      }
    });

    render();
    load();
    return { el: host, reload: load };
  }

  window.DcLinkTags = { mountCell: mountCell };
})();
