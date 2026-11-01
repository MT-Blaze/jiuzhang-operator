/**
 * ui_topics.js —— plugin.js 的「考向（bank.topics」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var TOPIC_LIMIT = coreState.TOPIC_LIMIT;
    var el = deps.el;
    var explainHostError = deps.explainHostError;
    var hostCall = deps.hostCall;
    var panel = coreState.panel;
    var panelSay = deps.panelSay;
    var queueMetaSave = deps.queueMetaSave;
    var renderMounted = deps.renderMounted;
    var renderPanelMetrics = deps.renderPanelMetrics;
    var panelTopicErrorEl = deps.dom.panelTopicErrorEl;
    var panelTreeEl = deps.dom.panelTreeEl;

  // ---------- 考向（bank.topics 懒展开，可挂多个、可摘） ----------
  function topicNode(node, depth) {
    var row = el("div", "ep-topic-row");
    row.style.paddingLeft = (depth * 12) + "px";
    var expander = el("button", "ep-topic-expander", node.has_children ? "▸" : "·");
    expander.type = "button";
    expander.setAttribute("aria-label", (node.has_children ? "展开 " : "没有下级：") + node.name);
    if (!node.has_children) expander.disabled = true;
    var label = el("button", "ep-topic-name", node.name);
    label.type = "button";
    label.title = "题量 " + node.question_count + "；点一下挂到本题";
    row.appendChild(expander);
    row.appendChild(label);
    var kids = el("div", "ep-topic-kids");
    kids.hidden = true;
    row.appendChild(kids);
    expander.addEventListener("click", function () {
      var open = !kids.hidden;
      kids.hidden = open;
      expander.textContent = open ? "▸" : "▾";
      row.setAttribute("data-open", open ? "false" : "true");
      if (!open && !kids.childNodes.length) loadChildren(node, kids, depth + 1);
    });
    label.addEventListener("click", function () { toggleTopic(node); });
    return row;
  }

  function loadChildren(node, holder, depth) {
    hostCall("bank.topics", { parent_id: node.id }).then(function (result) {
      var items = (result && result.items) || [];
      if (!items.length) {
        holder.appendChild(el("p", "ep-note", "这一层没有下级节点。"));
        return;
      }
      items.forEach(function (child) { holder.appendChild(topicNode(child, depth)); });
    }, function (error) {
      holder.appendChild(el("p", "ep-note", "读考向失败：" + explainHostError(error)));
    });
  }

  function loadTopicRoots() {
    if (!panelTreeEl || panel.topics.roots) return;
    panelTreeEl.textContent = "";
    panelTreeEl.appendChild(el("p", "ep-note", "正在读大纲…"));
    hostCall("bank.topics", {}).then(function (result) {
      var items = (result && result.items) || [];
      panel.topics.roots = items;
      panelTreeEl.textContent = "";
      if (!items.length) {
        panelTreeEl.appendChild(el("p", "ep-note", "当前题库还没有大纲节点。"));
        return;
      }
      items.forEach(function (node) { panelTreeEl.appendChild(topicNode(node, 0)); });
      if (panelTopicErrorEl) panelTopicErrorEl.hidden = true;
    }, function (error) {
      panelTreeEl.textContent = "";
      if (panelTopicErrorEl) {
        panelTopicErrorEl.hidden = false;
        panelTopicErrorEl.textContent = "考向读不出来：" + explainHostError(error) + "（不影响保存）";
      }
    });
  }

  function toggleTopic(node) {
    var entry = panel.currentEntry || (panel.currentEntry = {});
    var ids = (entry.topic_ids || []).slice();
    var names = entry.topic_names || {};
    var position = ids.indexOf(node.id);
    if (position >= 0) {
      ids.splice(position, 1);
      delete names[node.id];
    } else if (ids.length >= TOPIC_LIMIT) {
      panelSay("考向最多挂 " + TOPIC_LIMIT + " 个，先摘掉一个。", "warn", "idle");
      return;
    } else {
      ids.push(node.id);
      names[node.id] = node.name;
    }
    entry.topic_ids = ids;
    entry.topic_names = names;
    panel.currentEntry = entry;
    if (panel.selection) {
      panel.meta[panel.selection.key] = entry;
      panel.selection.dirty = true;
    }
    queueMetaSave();
    renderMounted();
    renderPanelMetrics();
  }

    return {
      loadChildren: loadChildren,
      loadTopicRoots: loadTopicRoots,
      toggleTopic: toggleTopic,
      topicNode: topicNode,
    };
  }

  global.JzoEditorTopics = { create: create };
})(window);
