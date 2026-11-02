/**
 * ui_std_name.js —— plugin.js 的「标准名」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var addSchoolRecord = deps.addSchoolRecord;
    var cancelSchoolConfirm = deps.cancelSchoolConfirm;
    var dockWarn = deps.dockWarn;
    var errorDetail = deps.errorDetail;
    var hostCall = deps.hostCall;
    var loadTags = deps.loadTags;
    var panel = coreState.panel;
    var panelMetaBodyEl = deps.dom.panelMetaBodyEl;
    var panelMetaExamTypeEl = deps.dom.panelMetaExamTypeEl;
    var panelMetaGradeEl = deps.dom.panelMetaGradeEl;
    var panelMetaRegionEl = deps.dom.panelMetaRegionEl;
    var panelMetaSceneEl = deps.dom.panelMetaSceneEl;
    var panelMetaSubjectEl = deps.dom.panelMetaSubjectEl;
    var panelMetaYearEl = deps.dom.panelMetaYearEl;
    var panelSay = deps.panelSay;
    var panelSchoolInputEl = deps.dom.panelSchoolInputEl;
    var panelSrcNameEl = deps.dom.panelSrcNameEl;
    var panelStdFlashEl = deps.dom.panelStdFlashEl;
    var panelStdHintEl = deps.dom.panelStdHintEl;
    var panelStdNameEl = deps.dom.panelStdNameEl;
    var renderFoldSummary = deps.renderFoldSummary;
    var renderSceneOptions = deps.renderSceneOptions;
    var renderSchools = deps.renderSchools;
    var standardNameOf = deps.standardNameOf;
    var uiSchoolDict = deps.uiSchoolDict;

  // ---------- 标准名：自动拼接 + 手改暂停 + 元数据再动即恢复 ----------

  var stdFlashTimer = 0;

  function setStdMode(manual) {
    panel.stdManual = Boolean(manual);
    var mode = panel.stdManual ? "manual" : "auto";
    if (panelStdNameEl) panelStdNameEl.setAttribute("data-mode", mode);
    if (panelStdHintEl) {
      panelStdHintEl.setAttribute("data-mode", mode);
      panelStdHintEl.textContent = panel.stdManual
        ? "已暂停自动拼接；再动任意元数据即恢复自动重拼。"
        : "自动拼接；手改后暂停联动，再改元数据即恢复。";
    }
  }

  /** 标准名重拼完闪一下淡黄：让老师眼睛跟得上，但只亮一息，不抢视线。 */
  function flashStd() {
    if (!panelStdFlashEl) return;
    panelStdFlashEl.textContent = "已更新";
    panelStdFlashEl.setAttribute("data-show", "true");
    if (panelStdNameEl) panelStdNameEl.setAttribute("data-flash", "true");
    window.clearTimeout(stdFlashTimer);
    stdFlashTimer = window.setTimeout(function () {
      panelStdFlashEl.setAttribute("data-show", "false");
      if (panelStdNameEl) panelStdNameEl.setAttribute("data-flash", "false");
    }, 1400);
  }

  function stdLiveName() {
    var meta = panel.batchMeta || {};
    return standardNameOf({
      year: panelMetaYearEl ? panelMetaYearEl.value : meta.year,
      region: panelMetaRegionEl ? panelMetaRegionEl.value : meta.region,
      body: panelMetaBodyEl ? panelMetaBodyEl.value : meta.body,
      scene_type: panelMetaSceneEl ? panelMetaSceneEl.value : meta.scene_type,
      exam_type: panelMetaExamTypeEl ? panelMetaExamTypeEl.value : meta.exam_type,
      subject: panelMetaSubjectEl ? panelMetaSubjectEl.value : meta.subject
    });
  }

  /** 顶部两行：灰字是原文件名，黑字的标准名跟着元数据实时重拼，手改后停下。 */
  function renderTopLines(options) {
    var card = panel.batchCard || {};
    var meta = panel.batchMeta || {};
    if (panelSrcNameEl) {
      var name = String(card.source_name || "");
      panelSrcNameEl.textContent = name || "还没有批次";
      panelSrcNameEl.setAttribute("data-name", name);
    }
    if (panelStdNameEl) {
      if (!panel.stdManual) {
        // 自动拼接模式：老师一眼就看见这一批将被叫成什么。
        var standard = stdLiveName();
        panelStdNameEl.value = standard;
        panelStdNameEl.setAttribute("data-standard", standard);
      } else if (!panelStdNameEl.value) {
        panelStdNameEl.value = String(meta.standard_name || stdLiveName());
      }
      panelStdNameEl.setAttribute("data-mode", panel.stdManual ? "manual" : "auto");
    }
    renderFoldSummary();
    if (options && options.flash) flashStd();
  }

  /** 底座回执里的标准名与模式是最终事实：以它对齐一次，别让本地猜。 */
  function applyStdFromMeta(flash) {
    var meta = panel.batchMeta || {};
    setStdMode(String(meta.name_mode || "auto") === "manual");
    if (panelStdNameEl) {
      var name = String(meta.standard_name || stdLiveName());
      if (!panel.stdManual || !panelStdNameEl.value) panelStdNameEl.value = name;
      panelStdNameEl.setAttribute("data-standard", name);
    }
    if (flash) flashStd();
  }

  /**
   * 回执只当加法：老师刚建档的学校还没进快照，晚到的旧回执不许把它抹掉；
   * 老师亲手摘掉的也不许被旧回执请回来。
   */
  function mergeSchools(details) {
    var rows = [];
    var known = {};
    (details || []).forEach(function (item) {
      var id = String((item && item.id) || "");
      if (!id || panel.schoolDropped[id]) return;
      known[id] = true;
      rows.push({
        id: id,
        full_name: String((item && item.full_name) || ""),
        short_name: String((item && (item.short_name || item.full_name)) || "")
      });
    });
    panel.schools.forEach(function (item) {
      var id = String(item.id || "");
      if (!id || known[id] || !panel.schoolAdded[id]) return;
      known[id] = true;
      rows.push({
        id: id,
        full_name: String(item.full_name || ""),
        short_name: String(item.short_name || item.full_name || "")
      });
    });
    return rows;
  }

  function renderBatchMeta() {
    var meta = panel.batchMeta || {};
    // 换批就换一套本地记账：上一批的加与减跟这一批无关。
    if (String(panel.batchId || "") !== String(panel.schoolBatchId || "")) {
      panel.schoolBatchId = String(panel.batchId || "");
      panel.schoolAdded = {};
      panel.schoolDropped = {};
      // 上一批打了一半的简称与它带来的撞名拦截，不许跟着老师跑到这一批。
      uiSchoolDict.resetConflictCheck();
      cancelSchoolConfirm();
      if (panelSchoolInputEl) panelSchoolInputEl.value = "";
    }
    if (panelMetaYearEl) panelMetaYearEl.value = meta.year == null ? "" : String(meta.year);
    if (panelMetaRegionEl) panelMetaRegionEl.value = String(meta.region || "");
    if (panelMetaGradeEl) panelMetaGradeEl.value = String(meta.grade || "");
    if (panelMetaBodyEl) panelMetaBodyEl.value = String(meta.body || "");
    if (panelMetaExamTypeEl) panelMetaExamTypeEl.value = String(meta.exam_type || "");
    if (panelMetaSubjectEl) panelMetaSubjectEl.value = String(meta.subject || "");
    renderSceneOptions();
    if (panelMetaSceneEl) panelMetaSceneEl.value = String(meta.scene_type || "");
    var details = Array.isArray(meta.school_details) ? meta.school_details : [];
    panel.schools = mergeSchools(details);
    panel.lastBody = String(meta.body || "");
    setStdMode(String(meta.name_mode || "auto") === "manual");
    renderSchools();
    renderTopLines();
    applyStdFromMeta(false);
  }

  /**
   * 同步回来的只刷「看得见的部分」，**不碰老师正在打的字**——
   * 上一笔同步的回执晚到时，照抄回执会把老师新打的字抹掉。
   */
  function renderMetaView() {
    var meta = panel.batchMeta || {};
    if (Array.isArray(meta.school_details)) {
      panel.schools = mergeSchools(meta.school_details);
    }
    if (panelMetaSceneEl && String(panelMetaSceneEl.value || "") !== String(meta.scene_type || "")) {
      panelMetaSceneEl.value = String(meta.scene_type || "");
    }
    renderSchools();
    renderTopLines();
    applyStdFromMeta(true);
  }

  var metaSyncTimer = 0;

  /** 改一个公共字段 → 整批同步。攒 400ms 再发，免得连打五个字段发五回。 */
  function queueMetaSync() {
    window.clearTimeout(metaSyncTimer);
    metaSyncTimer = window.setTimeout(applyMetaSync, 400);
  }

  function applyMetaSync() {
    if (!panel.batchId) return Promise.resolve(null);
    var payload = {
      batch_id: panel.batchId,
      year: panelMetaYearEl ? String(panelMetaYearEl.value || "").trim() : "",
      region: panelMetaRegionEl ? String(panelMetaRegionEl.value || "").trim() : "",
      grade: panelMetaGradeEl ? String(panelMetaGradeEl.value || "").trim() : "",
      body: panelMetaBodyEl ? String(panelMetaBodyEl.value || "").trim() : "",
      scene_type: panelMetaSceneEl ? String(panelMetaSceneEl.value || "").trim() : "",
      exam_type: panelMetaExamTypeEl ? String(panelMetaExamTypeEl.value || "").trim() : "",
      subject: panelMetaSubjectEl ? String(panelMetaSubjectEl.value || "").trim() : "",
      // 题目只认字典 ID：名字一个字节都不往题目里写。
      school_ids: panel.schools.map(function (item) { return String(item.id || ""); })
        .filter(Boolean),
      name_mode: panel.stdManual ? "manual" : "auto",
      standard_name: panelStdNameEl ? String(panelStdNameEl.value || "").trim() : ""
    };
    panel.metaSyncing = true;
    return hostCall("pending.set_meta", payload).then(function (result) {
      panel.metaSyncing = false;
      panel.batchMeta = (result && result.meta) || payload;
      panel.batchCard = (result && result.batch) || panel.batchCard;
      renderMetaView();
      var synced = Number(result && result.synced) || 0;
      var patched = Number(result && result.patched) || 0;
      var skipped = Number(result && result.skipped) || 0;
      var warnings = (result && Array.isArray(result.warnings)) ? result.warnings : [];
      warnings.slice(0, 3).forEach(function (text) { dockWarn(text); });
      panelSay("公共元数据已同步：" + synced + " 道题"
        + (patched ? "，主库补写 " + patched + " 道" : "")
        + (skipped ? "，" + skipped + " 道没同步上" : "") + "。",
        skipped ? "warn" : "ok", "meta");
      return result;
    }).catch(function (error) {
      panel.metaSyncing = false;
      var text = (error && error.message) || "未知原因";
      panelSay("公共元数据没同步上：" + text, "error", "failed");
      dockWarn("公共元数据没同步上：" + text, errorDetail(error));
      return null;
    });
  }

  /** 主体换了一个：历史里记过同一主体的，按字典把学校 ID 自动带出来。 */
  function hydrateGroupSchools(names) {
    var wanted = (names || []).map(function (name) { return String(name || "").trim(); })
      .filter(Boolean);
    if (!wanted.length) return Promise.resolve(null);
    return wanted.reduce(function (chain, name) {
      return chain.then(function () {
        return hostCall("meta.schools", { q: name, limit: 5 }).then(function (result) {
          var rows = (result && Array.isArray(result.schools)) ? result.schools : [];
          var hit = rows.filter(function (record) {
            return String(record.short_name || "") === name || String(record.full_name || "") === name;
          })[0];
          if (hit) addSchoolRecord(hit);
          return null;
        }, function () { return null; });
      });
    }, Promise.resolve(null)).then(function () {
      renderSchools();
      return null;
    });
  }

  function onMetaFieldChange() {
    var body = panelMetaBodyEl ? String(panelMetaBodyEl.value || "").trim() : "";
    if (body !== panel.lastBody) {
      panel.lastBody = body;
      var known = panel.groups ? panel.groups[body] : null;
      if (known && known.length) hydrateGroupSchools(known);
    }
    // 元数据一动，手改过的标准名立刻交回自动拼接（军令 #28 双向联动）。
    if (panel.stdManual) setStdMode(false);
    renderSchools();
    renderTopLines({ flash: true });
    queueMetaSync();
  }

  function onSceneChange() {
    if (panel.stdManual) setStdMode(false);
    renderTopLines({ flash: true });
    // 场景一换，交叉标签的排序与候选立刻跟着换。
    loadTags(panelMetaExamTypeEl ? String(panelMetaExamTypeEl.value || "").trim() : "");
    queueMetaSync();
  }

  /** 老师手改标准名：自动拼接当场暂停，改完这一段就以手改为准。 */
  function onStdInput() {
    setStdMode(true);
    window.clearTimeout(metaSyncTimer);
    metaSyncTimer = window.setTimeout(applyMetaSync, 600);
  }

  /** 取这一批的公共元数据：批次卡片里就带着 meta。 */
  function loadBatchMeta(batchId) {
    var id = String(batchId || "");
    panel.batchId = id;
    if (!id) {
      panel.batchCard = null;
      panel.batchMeta = {};
      panel.schools = [];
      renderBatchMeta();
      return Promise.resolve(null);
    }
    return hostCall("pending.batch_list", {}).then(function (result) {
      var cards = (result && Array.isArray(result.batches)) ? result.batches : [];
      var card = null;
      for (var index = 0; index < cards.length; index += 1) {
        if (String(cards[index].batch_id || "") === id) { card = cards[index]; break; }
      }
      if (!card) return null;
      panel.batchCard = card;
      panel.batchMeta = (card.meta && typeof card.meta === "object") ? card.meta : {};
      renderBatchMeta();
      return card;
    }).catch(function () {
      return null;
    });
  }

  /** 换批次：把公共元数据面板切到这一批。 */
  function syncBatchContext(batchId) {
    var id = String(batchId || "");
    if (id === panel.batchId && panel.batchCard) return Promise.resolve(null);
    return loadBatchMeta(id);
  }

    return {
      applyMetaSync: applyMetaSync,
      applyStdFromMeta: applyStdFromMeta,
      flashStd: flashStd,
      hydrateGroupSchools: hydrateGroupSchools,
      loadBatchMeta: loadBatchMeta,
      mergeSchools: mergeSchools,
      metaSyncTimer: metaSyncTimer,
      onMetaFieldChange: onMetaFieldChange,
      onSceneChange: onSceneChange,
      onStdInput: onStdInput,
      queueMetaSync: queueMetaSync,
      renderBatchMeta: renderBatchMeta,
      renderMetaView: renderMetaView,
      renderTopLines: renderTopLines,
      setStdMode: setStdMode,
      stdFlashTimer: stdFlashTimer,
      stdLiveName: stdLiveName,
      syncBatchContext: syncBatchContext,
    };
  }

  global.JzoEditorStdName = { create: create };
})(window);
