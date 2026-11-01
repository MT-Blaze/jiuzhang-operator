/**
 * ui_school_dict.js —— plugin.js 的「学校字典」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var dock = deps.dock;
    var dockWarn = deps.dockWarn;
    var el = deps.el;
    var errorDetail = deps.errorDetail;
    var hostCall = deps.hostCall;
    var panel = coreState.panel;
    var panelApproveEl = deps.dom.panelApproveEl;
    var panelMetaBodyEl = deps.dom.panelMetaBodyEl;
    var panelMetaExamTypeEl = deps.dom.panelMetaExamTypeEl;
    var panelMetaRegionEl = deps.dom.panelMetaRegionEl;
    var panelMetaSceneEl = deps.dom.panelMetaSceneEl;
    var panelMetaSchoolsEl = deps.dom.panelMetaSchoolsEl;
    var panelSay = deps.panelSay;
    var panelSchoolConfirmEl = deps.dom.panelSchoolConfirmEl;
    var panelSchoolConfirmOkEl = deps.dom.panelSchoolConfirmOkEl;
    var panelSchoolConfirmTextEl = deps.dom.panelSchoolConfirmTextEl;
    var panelSchoolErrorEl = deps.dom.panelSchoolErrorEl;
    var panelSchoolFullNameEl = deps.dom.panelSchoolFullNameEl;
    var panelSchoolInputEl = deps.dom.panelSchoolInputEl;
    var panelSchoolListEl = deps.dom.panelSchoolListEl;
    var panelSchoolMenuEl = deps.dom.panelSchoolMenuEl;
    var panelTagMenuEl = deps.dom.panelTagMenuEl;
    var queueMetaSync = deps.queueMetaSync;

  // ---------- 学校字典：题目只存 school_id，校名一律回字典查 ----------

  // 简称冲突的实时账本：谁占了这个简称、占给谁，一句话都不许含糊。
  var schoolConflict = null;
  var schoolConflictSeq = 0;
  var schoolConflictTimer = 0;

  function schoolConflictText(record) {
    return "❌ 简称冲突，已被【" + String(record.full_name || record.short_name || "") + "】占用";
  }

  /**
   * 冲突期间锁死两条路：建档确认与存入主库。
   * 简称撞车的这一批不许带着脏学校名进主库——宁可老师改个名再动。
   */
  function syncSchoolLock() {
    var locked = Boolean(schoolConflict);
    if (panelSchoolConfirmOkEl) {
      var ready = Boolean(panel.schoolConfirmReady)
        && !panel.schoolConfirmBusy && !locked;
      panelSchoolConfirmOkEl.disabled = !ready;
      panelSchoolConfirmOkEl.setAttribute("aria-disabled", ready ? "false" : "true");
    }
    if (panelApproveEl) {
      var canApprove = !panel.approveBusy && !locked;
      panelApproveEl.disabled = !canApprove;
      panelApproveEl.setAttribute("aria-disabled", canApprove ? "false" : "true");
      panelApproveEl.setAttribute("title", locked
        ? String((schoolConflict && schoolConflict.message) || "简称冲突，先改掉再入库")
        : "把这一题存进主库");
    }
  }

  /** 撞与不撞都得把菜单重画一遍：先到先得的那份「＋ 新建学校」不许留在桌上。 */
  function repaintSchoolMenu() {
    if (!panelSchoolMenuEl || panelSchoolMenuEl.hidden) return;
    renderSchoolMenu(panel.schoolOptions,
      panelSchoolInputEl ? String(panelSchoolInputEl.value || "").trim() : "");
  }

  function setSchoolConflict(record) {
    var message = schoolConflictText(record);
    schoolConflict = {
      short_name: String(record.short_name || ""),
      full_name: String(record.full_name || ""),
      message: message
    };
    setSchoolError(message);
    syncSchoolLock();
    repaintSchoolMenu();
  }

  function clearSchoolConflict() {
    if (!schoolConflict) return;
    schoolConflict = null;
    setSchoolError("");
    syncSchoolLock();
    repaintSchoolMenu();
  }

  function setSchoolError(text) {
    if (panelSchoolErrorEl) {
      var message = String(text || "");
      panelSchoolErrorEl.textContent = message;
      panelSchoolErrorEl.hidden = !message;
    }
    if (panelSchoolInputEl) {
      // 简称撞车时输入框当场爆红：CSS 只认 aria-invalid 与 .is-invalid 两种记号。
      panelSchoolInputEl.setAttribute("aria-invalid", text ? "true" : "false");
      panelSchoolInputEl.classList.toggle("is-invalid", Boolean(text));
    }
  }

  function schoolChip(record) {
    var shortName = String(record.short_name || record.full_name || "");
    var chip = el("span", "ep-school");
    chip.setAttribute("data-school-id", String(record.id || ""));
    chip.setAttribute("title", String(record.full_name || shortName));
    chip.appendChild(el("span", "ep-school-name", shortName));
    var remove = el("button", "ep-school-x", "×");
    remove.type = "button";
    remove.setAttribute("aria-label", "去掉 " + shortName);
    remove.addEventListener("click", function () {
      panel.schools = panel.schools.filter(function (item) {
        return String(item.id || "") !== String(record.id || "");
      });
      // 老师亲手摘掉的，旧回执不许把它请回来。
      panel.schoolDropped[String(record.id || "")] = true;
      delete panel.schoolAdded[String(record.id || "")];
      renderSchools();
      queueMetaSync();
    });
    chip.appendChild(remove);
    return chip;
  }

  /** 明细学校胶囊：主体填了才冒出来；点 × 去掉一所。 */
  function renderSchools() {
    if (!panelMetaSchoolsEl || !panelSchoolListEl) return;
    var body = panelMetaBodyEl ? String(panelMetaBodyEl.value || "").trim() : "";
    panelMetaSchoolsEl.hidden = !body;
    panelSchoolListEl.textContent = "";
    panel.schools.forEach(function (record) {
      panelSchoolListEl.appendChild(schoolChip(record || {}));
    });
  }

  function hideSchoolMenu() {
    if (panelSchoolMenuEl) panelSchoolMenuEl.hidden = true;
    if (panelSchoolInputEl) panelSchoolInputEl.setAttribute("aria-expanded", "false");
  }

  /**
   * 输入简称时立刻问一次字典：这个简称是不是已经被别的学校占了。
   * 占了就当场爆红并锁死建档与入库——底座那一层还会再拦一次，
   * 但老师不该等到点确认才知道自己撞了名。
   */
  function checkSchoolConflict(query) {
    var text = String(query || "").trim();
    if (!text) { clearSchoolConflict(); return; }
    var seq = schoolConflictSeq + 1;
    schoolConflictSeq = seq;
    hostCall("meta.schools", { q: text, limit: 8 }).then(function (result) {
      if (seq !== schoolConflictSeq) return;
      var rows = (result && Array.isArray(result.schools)) ? result.schools : [];
      var hit = null;
      rows.forEach(function (record) {
        if (hit) return;
        if (String((record && record.short_name) || "") === text) hit = record;
      });
      if (hit) setSchoolConflict(hit);
      else clearSchoolConflict();
    }, function () {
      // 字典没查成：不替老师下结论，也不解除已有拦截。
      if (seq !== schoolConflictSeq) return;
    });
  }

  /** 打字一路走一路问会把字典问爆：停手 150ms 再查这一次。 */
  function scheduleSchoolConflict(query) {
    window.clearTimeout(schoolConflictTimer);
    schoolConflictTimer = window.setTimeout(function () {
      checkSchoolConflict(query);
    }, 150);
  }

  function menuItem(text, hint) {
    var item = el("button", "ep-menu-item");
    item.type = "button";
    item.setAttribute("role", "option");
    item.appendChild(el("span", "ep-menu-text", text));
    if (hint) item.appendChild(el("span", "ep-menu-hint", hint));
    return item;
  }

  function renderSchoolMenu(matches, query) {
    if (!panelSchoolMenuEl) return;
    panelSchoolMenuEl.textContent = "";
    var added = {};
    panel.schools.forEach(function (item) { added[String(item.id || "")] = true; });
    var visible = (matches || []).filter(function (record) {
      return record && record.id && !added[String(record.id)];
    });
    visible.forEach(function (record) {
      var shortName = String(record.short_name || record.full_name || "");
      var item = menuItem(shortName, String(record.full_name || ""));
      item.setAttribute("data-school-id", String(record.id));
      item.addEventListener("mousedown", function (event) {
        // mousedown 而不是 click：input 失焦会先把菜单收掉，click 就永远等不到。
        event.preventDefault();
        addSchoolRecord(record);
        if (panelSchoolInputEl) panelSchoolInputEl.value = "";
        hideSchoolMenu();
        // 选中字典里的这所学校，简称冲突自然解除：老师要的正是这一所。
        clearSchoolConflict();
      });
      panelSchoolMenuEl.appendChild(item);
    });
    if (query && !schoolConflict) {
      var create = menuItem("＋ 新建学校「" + query + "」", "AI 补全全称后确认");
      create.setAttribute("data-school-create", query);
      create.addEventListener("mousedown", function (event) {
        event.preventDefault();
        hideSchoolMenu();
        requestSchoolSuggest(query);
      });
      panelSchoolMenuEl.appendChild(create);
    }
    panelSchoolMenuEl.hidden = !panelSchoolMenuEl.children.length;
    if (panelSchoolInputEl) {
      panelSchoolInputEl.setAttribute("aria-expanded", panelSchoolMenuEl.hidden ? "false" : "true");
    }
  }

  function searchSchools(query) {
    return hostCall("meta.schools", { q: String(query || ""), limit: 8 }).then(function (result) {
      var rows = (result && Array.isArray(result.schools)) ? result.schools : [];
      panel.schoolOptions = rows;
      renderSchoolMenu(rows, String(query || "").trim());
      return rows;
    }).catch(function (error) {
      hideSchoolMenu();
      dockWarn("学校字典没查成：" + ((error && error.message) || "未知原因"), errorDetail(error));
      return [];
    });
  }

  /**
   * 作废在途与待发的撞名查询。
   * 老师已经认领或刚建档的这所学校，绝不能被一条晚到的旧回执重新锁回去——
   * 建档前那次输入「哈九中」的查询可能正好在建档成功后落地，撞上自己刚建的档。
   */
  function invalidateSchoolLookup() {
    window.clearTimeout(schoolConflictTimer);
    schoolConflictTimer = 0;
    schoolConflictSeq += 1;
  }

  function addSchoolRecord(record) {
    if (!record || !record.id) return;
    invalidateSchoolLookup();
    var id = String(record.id);
    var exists = panel.schools.some(function (item) { return String(item.id || "") === id; });
    if (exists) {
      panelSay("「" + String(record.short_name || record.full_name) + "」已经在明细里了。",
        "warn", "invalid");
      return;
    }
    if (panel.schools.length >= 24) {
      panelSay("明细学校最多 24 所。", "warn", "invalid");
      return;
    }
    panel.schools.push({
      id: id,
      full_name: String(record.full_name || ""),
      short_name: String(record.short_name || record.full_name || "")
    });
    // 本地先记一笔：这所在还没进回执快照，晚到的旧回执不许把它抹掉。
    panel.schoolAdded[id] = true;
    delete panel.schoolDropped[id];
    // 老师点的就是字典里这一所：撞名已经不是问题了，锁当场解开。
    clearSchoolConflict();
    renderSchools();
    queueMetaSync();
  }

  function requestSchoolSuggest(shortName) {
    var text = String(shortName || "").trim();
    if (!text) return;
    if (schoolConflict) {
      setSchoolError(schoolConflict.message);
      return;
    }
    panel.schoolPending = { short_name: text };
    if (panelSchoolConfirmEl) panelSchoolConfirmEl.hidden = false;
    if (panelSchoolConfirmTextEl) {
      panelSchoolConfirmTextEl.textContent = "字典里没有「" + text + "」，正在让 AI 补全全称…";
    }
    if (panelSchoolFullNameEl) panelSchoolFullNameEl.value = "";
    panel.schoolConfirmBusy = true;
    panel.schoolConfirmReady = false;
    syncSchoolLock();
    var region = panelMetaRegionEl ? String(panelMetaRegionEl.value || "").trim() : "";
    hostCall("meta.school_suggest", { short_name: text, region: region }).then(function (result) {
      var full = String((result && result.full_name) || "");
      if (panelSchoolFullNameEl) panelSchoolFullNameEl.value = full;
      if (panelSchoolConfirmTextEl) {
        panelSchoolConfirmTextEl.textContent = full
          ? "AI 建议全称「" + full + "」，确认无误就建档；不对就手改。"
          : "AI 没补出全称，请手填后确认。";
      }
      panel.schoolConfirmBusy = false;
      panel.schoolConfirmReady = true;
      syncSchoolLock();
    }, function (error) {
      if (panelSchoolConfirmTextEl) {
        panelSchoolConfirmTextEl.textContent = "AI 补全没成功（"
          + ((error && error.message) || "未知原因") + "），请手填全称后确认。";
      }
      panel.schoolConfirmBusy = false;
      panel.schoolConfirmReady = true;
      syncSchoolLock();
      dockWarn("学校全称补全没成功：" + ((error && error.message) || "未知原因"),
        errorDetail(error));
    });
  }

  function cancelSchoolConfirm() {
    panel.schoolPending = null;
    panel.schoolConfirmBusy = false;
    panel.schoolConfirmReady = false;
    if (panelSchoolConfirmEl) panelSchoolConfirmEl.hidden = true;
    if (panelSchoolFullNameEl) panelSchoolFullNameEl.value = "";
    clearSchoolConflict();
    setSchoolError("");
    syncSchoolLock();
  }

  function confirmSchoolCreate() {
    var pendingSchool = panel.schoolPending;
    if (!pendingSchool) return;
    if (schoolConflict) {
      setSchoolError(schoolConflict.message);
      return;
    }
    var fullName = panelSchoolFullNameEl ? String(panelSchoolFullNameEl.value || "").trim() : "";
    if (!fullName) {
      setSchoolError("请先填学校全称，确认后才建档。");
      if (panelSchoolFullNameEl) panelSchoolFullNameEl.focus();
      return;
    }
    panel.schoolConfirmBusy = true;
    syncSchoolLock();
    hostCall("meta.school_create", {
      full_name: fullName,
      short_name: String(pendingSchool.short_name || "")
    }).then(function (result) {
      var record = (result && result.school) || {};
      panel.schoolConfirmBusy = false;
      panel.schoolConfirmReady = false;
      syncSchoolLock();
      if (!record.id) return;
      cancelSchoolConfirm();
      addSchoolRecord(record);
      if (panelSchoolInputEl) panelSchoolInputEl.value = "";
      hideSchoolMenu();
      dock("学校已建档：" + String(record.full_name || "") + "（" + String(record.short_name || "") + "）。");
    }, function (error) {
      panel.schoolConfirmBusy = false;
      syncSchoolLock();
      // 简称撞车按底座的原话回显：❌ 简称冲突，已被【哈尔滨师范大学附属中学】占用
      var message = String((error && error.message) || "学校建档没成功");
      setSchoolError(message);
      if (message.indexOf("简称冲突") >= 0) {
        schoolConflict = {
          short_name: String(pendingSchool.short_name || ""),
          full_name: "",
          message: message
        };
        syncSchoolLock();
      }
      dockWarn("学校建档没成功：" + ((error && error.message) || "未知原因"),
        errorDetail(error));
    });
  }

  function onSchoolEnter() {
    var query = panelSchoolInputEl ? String(panelSchoolInputEl.value || "").trim() : "";
    if (!query) return;
    var exact = (panel.schoolOptions || []).filter(function (record) {
      return String(record.short_name || "") === query || String(record.full_name || "") === query;
    })[0];
    if (exact) {
      addSchoolRecord(exact);
      panelSchoolInputEl.value = "";
      hideSchoolMenu();
      return;
    }
    if (schoolConflict) {
      setSchoolError(schoolConflict.message);
      return;
    }
    hideSchoolMenu();
    requestSchoolSuggest(query);
  }

  // ---------- 交叉标签：按场景权重排序，模糊匹配，回车即记 ----------

  function hideTagMenu() {
    if (panelTagMenuEl) panelTagMenuEl.hidden = true;
    if (panelMetaExamTypeEl) panelMetaExamTypeEl.setAttribute("aria-expanded", "false");
  }

  function renderTagMenu(items) {
    if (!panelTagMenuEl) return;
    panelTagMenuEl.textContent = "";
    panel.tagOptions = (items || []).slice();
    panel.tagOptions.forEach(function (tag) {
      var hint = String(tag.pinyin || "").toUpperCase();
      if (tag.scene_weight) hint = (hint ? hint + " · " : "") + "本场景常用";
      var item = menuItem(String(tag.name || ""), hint);
      item.setAttribute("data-tag", String(tag.name || ""));
      item.addEventListener("mousedown", function (event) {
        event.preventDefault();
        pickTag(String(tag.name || ""));
      });
      panelTagMenuEl.appendChild(item);
    });
    panelTagMenuEl.hidden = !panelTagMenuEl.children.length;
    if (panelMetaExamTypeEl) {
      panelMetaExamTypeEl.setAttribute("aria-expanded", panelTagMenuEl.hidden ? "false" : "true");
    }
  }

  // 候选菜单的回执序号：晚到的旧回执不许盖掉刚画出来的新菜单。
  var tagMenuSeq = 0;

  function loadTags(query) {
    var scene = panelMetaSceneEl ? String(panelMetaSceneEl.value || "") : "";
    var seq = tagMenuSeq + 1;
    tagMenuSeq = seq;
    return hostCall("meta.tags", { scene: scene, q: String(query || ""), limit: 8 })
      .then(function (result) {
        if (seq !== tagMenuSeq) return [];
        var rows = (result && Array.isArray(result.tags)) ? result.tags : [];
        renderTagMenu(rows);
        return rows;
      }).catch(function (error) {
        if (seq !== tagMenuSeq) return [];
        hideTagMenu();
        dockWarn("交叉标签没拉下来：" + ((error && error.message) || "未知原因"),
          errorDetail(error));
        return [];
      });
  }

  function pickTag(name) {
    var text = String(name || "").trim();
    if (!text) return;
    if (panelMetaExamTypeEl) panelMetaExamTypeEl.value = text;
    hideTagMenu();
    queueMetaSync();
  }

  function onTagEnter() {
    var text = panelMetaExamTypeEl ? String(panelMetaExamTypeEl.value || "").trim() : "";
    if (!text) return;
    var known = (panel.tagOptions || []).some(function (tag) {
      return String(tag.name || "") === text;
    });
    if (known) {
      hideTagMenu();
      queueMetaSync();
      return;
    }
    var scene = panelMetaSceneEl ? String(panelMetaSceneEl.value || "") : "";
    hostCall("meta.tag_remember", { name: text, scene: scene }).then(function () {
      hideTagMenu();
      dock("新标签「" + text + "」已记进本地标签库，下次打字就会弹出来。", "note");
      queueMetaSync();
    }, function (error) {
      hideTagMenu();
      dockWarn("标签没记进本地库：" + ((error && error.message) || "未知原因"),
        errorDetail(error));
      queueMetaSync();
    });
  }

    // 换批时把上一批打了一半的撞名检查整段作废：撤计时器、推进序号让在途回音失效。
  // 这几个序号是模块私有的可变标量，外面只能走这个方法，不能按值拿走。
  function resetConflictCheck() {
    window.clearTimeout(schoolConflictTimer);
    schoolConflictSeq += 1;
  }

  return {
      resetConflictCheck: resetConflictCheck,
      addSchoolRecord: addSchoolRecord,
      cancelSchoolConfirm: cancelSchoolConfirm,
      checkSchoolConflict: checkSchoolConflict,
      clearSchoolConflict: clearSchoolConflict,
      confirmSchoolCreate: confirmSchoolCreate,
      hideSchoolMenu: hideSchoolMenu,
      hideTagMenu: hideTagMenu,
      loadTags: loadTags,
      menuItem: menuItem,
      onSchoolEnter: onSchoolEnter,
      onTagEnter: onTagEnter,
      pickTag: pickTag,
      renderSchoolMenu: renderSchoolMenu,
      renderSchools: renderSchools,
      renderTagMenu: renderTagMenu,
      repaintSchoolMenu: repaintSchoolMenu,
      requestSchoolSuggest: requestSchoolSuggest,
      scheduleSchoolConflict: scheduleSchoolConflict,
      schoolChip: schoolChip,
      schoolConflictText: schoolConflictText,
      searchSchools: searchSchools,
      setSchoolConflict: setSchoolConflict,
      setSchoolError: setSchoolError,
      syncSchoolLock: syncSchoolLock,
    };
  }

  global.JzoEditorSchoolDict = { create: create };
})(window);
