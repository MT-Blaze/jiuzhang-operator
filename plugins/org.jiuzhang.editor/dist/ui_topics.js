/**
 * ui_topics.js —— 考向挂载的唯一动作（PLUGIN_SPEC §2.8.1：单文件不超 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 * 考向大纲树已随「UI 极致瘦身令」下线（2026-11-02）：挂载只走段一的幽灵胶囊，
 * 本模块只留下胶囊串与画布共用的那一个开关动作。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var TOPIC_LIMIT = coreState.TOPIC_LIMIT;
    var panel = coreState.panel;
    var panelSay = deps.panelSay;
    var queueMetaSave = deps.queueMetaSave;
    var renderMounted = deps.renderMounted;
    var renderPanelMetrics = deps.renderPanelMetrics;

  // ---------- 考向挂载 / 摘除（可挂多个，上限 TOPIC_LIMIT） ----------
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
      toggleTopic: toggleTopic,
    };
  }

  global.JzoEditorTopics = { create: create };
})(window);
