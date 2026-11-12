/**
 * ui_meta_hist.js —— plugin.js 的「批次公共元数据」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var dockWarn = deps.dockWarn;
    var errorDetail = deps.errorDetail;
    var hostCall = deps.hostCall;
    var panel = coreState.panel;
    var panelMetaSceneEl = deps.dom.panelMetaSceneEl;
    var refreshDicts = deps.refreshDicts;

  // ---------- 批次公共元数据（辅助栏顶部） ----------

  /** 标准名：按考试类型规则动态拼装，空段不占位；底座也用同一口径重算，客户端说了不算。 */
  function standardNameOf(meta) {
    var m = meta || {};
    var examType = String(m.exam_type || m.scene_type || "").trim();
    var parts = [];
    if (m.year != null && m.year !== "") parts.push(String(m.year) + "年");
    var org = String(m.body || "").trim();
    if (org) parts.push(org);
    var grade = String(m.grade || "").trim();
    if (grade) parts.push(grade);
    if (examType === "月考") {
      if (m.month) parts.push(String(m.month) + "月");
      parts.push("月考");
    } else if (examType === "模拟考" || examType === "模考") {
      parts.push(m.mock_round ? String(m.mock_round) + "模" : "模拟考");
    } else if (examType === "期中" || examType === "期末") {
      if (m.semester) parts.push(String(m.semester));
      parts.push(examType);
    } else if (examType) {
      parts.push(examType);
    }
    var subject = String(m.subject || "").trim();
    if (subject) parts.push(subject);
    return parts.join("").slice(0, 120);
  }

  /** 历史值：地区 / 主体 / 学科各一份联想，另有主体 → 明细学校的对应。 */
  function loadMetaHistory() {
    return hostCall("pending.meta_history", {}).then(function (result) {
      panel.history = (result && result.history) || {};
      panel.groups = (result && result.groups) || {};
      if (typeof refreshDicts === "function") refreshDicts();
      return panel.history;
    }).catch(function () {
      return null;
    });
  }

  // ---------- 场景表：11 个主场景，底座说了算 ----------

  /** 场景不再住原生 select：只把字典交回候选框，值由 ui_std_name 回填。 */
  function renderSceneOptions() {
    if (typeof refreshDicts === "function") refreshDicts();
  }

  function loadScenes() {
    if (panel.scenes.length) return Promise.resolve(panel.scenes);
    return hostCall("meta.scenes", {}).then(function (result) {
      var rows = (result && Array.isArray(result.scenes)) ? result.scenes : [];
      panel.scenes = rows.map(function (row) { return String((row && row.name) || ""); })
        .filter(Boolean);
      renderSceneOptions();
      return panel.scenes;
    }).catch(function (error) {
      dockWarn("场景表没拉下来：" + ((error && error.message) || "未知原因"), errorDetail(error));
      return [];
    });
  }

    return {
      loadMetaHistory: loadMetaHistory,
      loadScenes: loadScenes,
      renderSceneOptions: renderSceneOptions,
      standardNameOf: standardNameOf,
    };
  }

  global.JzoEditorMetaHist = { create: create };
})(window);
