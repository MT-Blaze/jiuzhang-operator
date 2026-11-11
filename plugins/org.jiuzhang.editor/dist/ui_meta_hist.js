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
    var panelBodyListEl = deps.dom.panelBodyListEl;
    var panelMetaSceneEl = deps.dom.panelMetaSceneEl;
    var panelRegionListEl = deps.dom.panelRegionListEl;
    var panelSubjectListEl = deps.dom.panelSubjectListEl;

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
    } else if (examType === "模考") {
      parts.push(m.mock_round ? String(m.mock_round) + "模" : "模考");
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

  function fillDataList(node, values) {
    if (!node) return;
    node.textContent = "";
    (values || []).forEach(function (value) {
      var text = String(value || "");
      if (!text) return;
      var option = document.createElement("option");
      option.value = text;
      node.appendChild(option);
    });
  }

  /** 历史值：地区 / 主体 / 学科各一份联想，另有主体 → 明细学校的对应。 */
  function loadMetaHistory() {
    return hostCall("pending.meta_history", {}).then(function (result) {
      panel.history = (result && result.history) || {};
      panel.groups = (result && result.groups) || {};
      fillDataList(panelRegionListEl, panel.history.region);
      fillDataList(panelBodyListEl, panel.history.body);
      fillDataList(panelSubjectListEl, panel.history.subject);
      return panel.history;
    }).catch(function () {
      return null;
    });
  }

  // ---------- 场景表：11 个主场景，底座说了算 ----------

  function renderSceneOptions() {
    if (!panelMetaSceneEl) return;
    var current = String(panelMetaSceneEl.value || (panel.batchMeta || {}).scene_type || "");
    panelMetaSceneEl.textContent = "";
    var blank = document.createElement("option");
    blank.value = "";
    blank.textContent = "未分类";
    panelMetaSceneEl.appendChild(blank);
    panel.scenes.forEach(function (name) {
      var option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      panelMetaSceneEl.appendChild(option);
    });
    if (current && panel.scenes.indexOf(current) < 0) {
      var extra = document.createElement("option");
      extra.value = current;
      extra.textContent = current;
      panelMetaSceneEl.appendChild(extra);
    }
    panelMetaSceneEl.value = current;
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
      fillDataList: fillDataList,
      loadMetaHistory: loadMetaHistory,
      loadScenes: loadScenes,
      renderSceneOptions: renderSceneOptions,
      standardNameOf: standardNameOf,
    };
  }

  global.JzoEditorMetaHist = { create: create };
})(window);
