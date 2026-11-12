/**
 * ui_std_name.js —— 公共元数据面板的「标准名 + 批次同步」层。
 *
 * 标准名永远只读、按元数据自动拼接；批次公共字段改一处即整批 PATCH。
 * 字段与候选框在 ui_meta_fields.js，控件本体在 ui_meta_combo.js，正则解析在 core_meta_parse.js。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var panel = coreState.panel;
    var dom = deps.dom;
    var addSchoolRecord = deps.addSchoolRecord;
    var cancelSchoolConfirm = deps.cancelSchoolConfirm;
    var dockWarn = deps.dockWarn;
    var errorDetail = deps.errorDetail;
    var hostCall = deps.hostCall;
    var panelSay = deps.panelSay;
    var renderFoldSummary = deps.renderFoldSummary;
    var renderSchools = deps.renderSchools;
    var standardNameOf = deps.standardNameOf;
    var uiSchoolDict = deps.uiSchoolDict;

    var panelSrcNameEl = dom.panelSrcNameEl;
    var panelStdNameEl = dom.panelStdNameEl;
    var panelStdFlashEl = dom.panelStdFlashEl;
    var panelStdHintEl = dom.panelStdHintEl;
    var panelMetaYearEl = dom.panelMetaYearEl;
    var panelMetaMonthEl = dom.panelMetaMonthEl;
    var panelMetaMockRoundEl = dom.panelMetaMockRoundEl;
    var panelMonthFieldEl = dom.panelMonthFieldEl;
    var panelMockRoundFieldEl = dom.panelMockRoundFieldEl;
    var panelSemesterFieldEl = dom.panelSemesterFieldEl;

    var stdFlashTimer = 0;
    var metaSyncTimer = 0;

    var fields = window.JzoEditorMetaFields.create({
      coreState: coreState,
      dom: dom,
      hostCall: hostCall,
      onChange: function () { onMetaFieldChange(); },
      onPlainInput: function () { onPlainMetaInput(); },
      onSourceEdited: function () { panel.srcNameEdited = true; },
      onSourceBlur: function () { onSourceNameBlur(); },
      onBodySchool: function (record) { bindBodySchool(record); }
    });

    function text(value) { return String(value == null ? "" : value).trim(); }

    function isMock(examType) {
      return examType === "模拟考" || examType === "模考"
        || /[一二三四五六七八九十\d]+模/.test(examType);
    }

    function valueOf(name) { return fields.getValue(name); }

    // ---------- 标准名：只读，按元数据实时重拼 ----------

    function setStdMode(manual) {
      panel.stdManual = Boolean(manual);
      var mode = panel.stdManual ? "manual" : "auto";
      if (panelStdNameEl) panelStdNameEl.setAttribute("data-mode", mode);
      if (panelStdHintEl) {
        panelStdHintEl.setAttribute("data-mode", mode);
        panelStdHintEl.textContent = "标准名只读：跟着年份、主体、类型、学科自动拼接。";
      }
    }

    function setStdText(name) {
      var value = text(name);
      if (panelStdNameEl) {
        panelStdNameEl.textContent = value;
        panelStdNameEl.setAttribute("data-standard", value);
      }
    }

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
        year: valueOf("year") || meta.year,
        region: valueOf("region") || meta.region,
        body: valueOf("body") || meta.body,
        grade: valueOf("grade") || meta.grade,
        scene_type: valueOf("scene") || meta.scene_type,
        exam_type: valueOf("exam_type") || meta.exam_type,
        month: valueOf("month") || meta.month,
        mock_round: valueOf("mock_round") || meta.mock_round,
        semester: valueOf("semester") || meta.semester,
        subject: valueOf("subject") || meta.subject
      });
    }

    function renderTopLines(options) {
      var card = panel.batchCard || {};
      if (panelSrcNameEl) {
        var source = text(card.source_name);
        panelSrcNameEl.setAttribute("data-name", source);
        if (document.activeElement !== panelSrcNameEl && !panel.srcNameEdited) {
          panelSrcNameEl.value = source;
        }
        if (document.activeElement !== panelSrcNameEl && source
            && source === text(panelSrcNameEl.value)) {
          panel.srcNameEdited = false;
        }
      }
      setStdText(stdLiveName());
      renderFoldSummary();
      if (options && options.flash) flashStd();
    }

    function applyStdFromMeta(flash) {
      var meta = panel.batchMeta || {};
      setStdMode(false);
      setStdText(meta.standard_name || stdLiveName());
      if (flash) flashStd();
    }

    // ---------- 条件字段：月考看月份、模拟考看轮次、期中期末看学期 ----------

    function toggleExamFields() {
      var examType = valueOf("exam_type");
      var showMonth = examType === "月考";
      var showRound = isMock(examType);
      var showSemester = examType === "期中" || examType === "期末";
      if (panelMonthFieldEl) panelMonthFieldEl.hidden = !showMonth;
      if (panelMockRoundFieldEl) panelMockRoundFieldEl.hidden = !showRound;
      if (panelSemesterFieldEl) panelSemesterFieldEl.hidden = !showSemester;
    }

    // ---------- 主体是学校：第五行自动收起 ----------

    function releaseAutoSchool(body) {
      var id = text(panel.bodyAutoSchoolId);
      if (!id) return;
      var record = panel.schools.filter(function (item) {
        return text(item.id) === id;
      })[0];
      if (record && (body === text(record.short_name) || body === text(record.full_name))) return;
      panel.schools = panel.schools.filter(function (item) { return text(item.id) !== id; });
      panel.schoolDropped[id] = true;
      delete panel.schoolAdded[id];
      panel.bodyAutoSchoolId = "";
    }

    function bindBodySchool(record) {
      if (!record || !record.id) return;
      addSchoolRecord(record);
      panel.bodyAutoSchoolId = text(record.id);
      delete panel.schoolDropped[text(record.id)];
      renderSchools();
      fields.refresh();
    }

    function rememberBodySchool(meta) {
      panel.bodyAutoSchoolId = "";
      var body = text(meta && meta.body);
      if (!body) return;
      var hit = panel.schools.filter(function (item) {
        return text(item.short_name) === body || text(item.full_name) === body;
      })[0];
      if (hit) panel.bodyAutoSchoolId = text(hit.id);
    }

    // ---------- 字段变化：主体联动、条件显隐、标准名重拼、整批同步 ----------

    function onMetaFieldChange() {
      var body = valueOf("body");
      if (body !== panel.lastBody) {
        panel.lastBody = body;
        releaseAutoSchool(body);
        var known = panel.groups ? panel.groups[body] : null;
        if (known && known.length) hydrateGroupSchools(known);
      }
      toggleExamFields();
      renderSchools();
      renderTopLines({ flash: true });
      queueMetaSync();
    }

    function onPlainMetaInput() {
      renderTopLines({ flash: true });
      queueMetaSync();
    }

    function onSourceNameBlur() {
      var raw = text(panelSrcNameEl && panelSrcNameEl.value);
      if (panelSrcNameEl) panelSrcNameEl.setAttribute("data-name", raw);
      if (!raw) {
        panel.srcParsedName = "";
      } else if (raw !== panel.srcParsedName) {
        panel.srcParsedName = raw;
        fields.applyParsed(fields.parseSourceName(raw));
      }
      queueMetaSync();
    }

    function onSceneChange() { onMetaFieldChange(); }

    /** 标准名已只读：旧监听还挂着时也只当一次刷新，不改字。 */
    function onStdInput() {
      setStdMode(false);
      renderTopLines();
    }

    // ---------- 批次同步 ----------

    function schoolIds() {
      return panel.schools.map(function (item) { return text(item.id); }).filter(Boolean);
    }

    function applyMetaSync() {
      if (!panel.batchId) return Promise.resolve(null);
      window.clearTimeout(metaSyncTimer);
      var examType = valueOf("exam_type");
      var payload = {
        batch_id: panel.batchId,
        source_name: text(panelSrcNameEl && panelSrcNameEl.value),
        year: valueOf("year"),
        region: valueOf("region"),
        grade: valueOf("grade"),
        body: valueOf("body"),
        scene_type: valueOf("scene"),
        exam_type: examType,
        month: examType === "月考" ? valueOf("month") : "",
        mock_round: isMock(examType) ? valueOf("mock_round") : "",
        semester: (examType === "期中" || examType === "期末") ? valueOf("semester") : "",
        subject: valueOf("subject"),
        school_ids: schoolIds(),
        name_mode: "auto",
        standard_name: text(panelStdNameEl && panelStdNameEl.textContent)
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
        warnings.slice(0, 3).forEach(function (warning) { dockWarn(warning); });
        panelSay("公共元数据已同步：" + synced + " 道题"
          + (patched ? "，主库补写 " + patched + " 道" : "")
          + (skipped ? "，" + skipped + " 道没同步上" : "") + "。",
          skipped ? "warn" : "ok", "meta");
        return result;
      }).catch(function (error) {
        panel.metaSyncing = false;
        var message = (error && error.message) || "未知原因";
        panelSay("公共元数据没同步上：" + message, "error", "failed");
        dockWarn("公共元数据没同步上：" + message, errorDetail(error));
        return null;
      });
    }

    function queueMetaSync() {
      window.clearTimeout(metaSyncTimer);
      metaSyncTimer = window.setTimeout(applyMetaSync, 400);
    }

    // ---------- 回执合并与视图刷新 ----------

    /**
     * 回执只当加法：老师刚建档的学校还没进快照，晚到的旧回执不许把它抹掉；
     * 老师亲手摘掉的也不许被旧回执请回来。
     */
    function mergeSchools(details) {
      var rows = [];
      var known = {};
      (details || []).forEach(function (item) {
        var id = text(item && item.id);
        if (!id || panel.schoolDropped[id]) return;
        known[id] = true;
        rows.push({
          id: id,
          full_name: text(item && item.full_name),
          short_name: text(item && (item.short_name || item.full_name))
        });
      });
      panel.schools.forEach(function (item) {
        var id = text(item.id);
        if (!id || known[id] || !panel.schoolAdded[id]) return;
        known[id] = true;
        rows.push({
          id: id,
          full_name: text(item.full_name),
          short_name: text(item.short_name || item.full_name)
        });
      });
      return rows;
    }

    function renderMetaView() {
      var meta = panel.batchMeta || {};
      if (Array.isArray(meta.school_details)) {
        panel.schools = mergeSchools(meta.school_details);
      }
      fields.refresh();
      fields.setScene(meta.scene_type);
      renderSchools();
      renderTopLines();
      applyStdFromMeta(true);
    }

    function renderBatchMeta() {
      var meta = panel.batchMeta || {};
      if (text(panel.batchId) !== text(panel.schoolBatchId)) {
        panel.schoolBatchId = text(panel.batchId);
        panel.schoolAdded = {};
        panel.schoolDropped = {};
        panel.bodyAutoSchoolId = "";
        panel.srcParsedName = "";
        panel.srcNameEdited = false;
        uiSchoolDict.resetConflictCheck();
        cancelSchoolConfirm();
        if (dom.panelSchoolInputEl) dom.panelSchoolInputEl.value = "";
      }
      if (panelMetaYearEl) panelMetaYearEl.value = meta.year == null ? "" : text(meta.year);
      if (panelMetaMonthEl) panelMetaMonthEl.value = meta.month == null ? "" : text(meta.month);
      if (panelMetaMockRoundEl) {
        panelMetaMockRoundEl.value = meta.mock_round == null ? "" : text(meta.mock_round);
      }
      var details = Array.isArray(meta.school_details) ? meta.school_details : [];
      panel.schools = mergeSchools(details);
      rememberBodySchool(meta);
      fields.refresh();
      fields.syncFromMeta(meta);
      panel.lastBody = text(meta.body);
      setStdMode(false);
      toggleExamFields();
      renderSchools();
      renderTopLines();
      applyStdFromMeta(false);
    }

    /** 主体换了一个：历史里记过同一主体的，按字典把学校 ID 自动带出来。 */
    function hydrateGroupSchools(names) {
      var wanted = namesOf(names);
      if (!wanted.length) return Promise.resolve(null);
      return wanted.reduce(function (chain, name) {
        return chain.then(function () {
          return hostCall("meta.schools", { q: name, limit: 5 }).then(function (result) {
            var rows = (result && Array.isArray(result.schools)) ? result.schools : [];
            var hit = rows.filter(function (record) {
              return text(record.short_name) === name || text(record.full_name) === name;
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

    function namesOf(rows) {
      return (rows || []).map(function (row) {
        return text(typeof row === "string" ? row : (row && row.name));
      }).filter(Boolean);
    }

    // ---------- 批次切换 ----------

    function loadBatchMeta(batchId) {
      var id = text(batchId);
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
          if (text(cards[index].batch_id) === id) { card = cards[index]; break; }
        }
        if (!card) return null;
        panel.batchCard = card;
        panel.batchMeta = (card.meta && typeof card.meta === "object") ? card.meta : {};
        renderBatchMeta();
        return card;
      }).catch(function () { return null; });
    }

    function syncBatchContext(batchId) {
      var id = text(batchId);
      if (id === text(panel.batchId) && panel.batchCard) return Promise.resolve(null);
      return loadBatchMeta(id);
    }

    function bindFields() {
      fields.bindFields();
      setStdMode(false);
    }

    return {
      applyMetaSync: applyMetaSync,
      applyStdFromMeta: applyStdFromMeta,
      bindFields: bindFields,
      flashStd: flashStd,
      hydrateGroupSchools: hydrateGroupSchools,
      loadBatchMeta: loadBatchMeta,
      mergeSchools: mergeSchools,
      metaSyncTimer: metaSyncTimer,
      onMetaFieldChange: onMetaFieldChange,
      onSceneChange: onSceneChange,
      onStdInput: onStdInput,
      parseSourceName: function (raw) { return fields.parseSourceName(raw); },
      queueMetaSync: queueMetaSync,
      refreshDicts: function () { fields.refresh(); },
      renderBatchMeta: renderBatchMeta,
      renderMetaView: renderMetaView,
      renderTopLines: renderTopLines,
      setStdMode: setStdMode,
      stdFlashTimer: stdFlashTimer,
      stdLiveName: stdLiveName,
      syncBatchContext: syncBatchContext,
      toggleExamFields: toggleExamFields,
    };
  }

  global.JzoEditorStdName = { create: create };
})(window);
