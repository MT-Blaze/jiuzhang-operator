/**
 * ui_ai.js —— plugin.js 的「辅助栏 AI 帮改」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var AI_ASK_MAX = coreState.AI_ASK_MAX;
    var AI_REQUEST_TIMEOUT_MS = coreState.AI_REQUEST_TIMEOUT_MS;
    var AI_STATE_LABELS = coreState.AI_STATE_LABELS;
    var FIELD_MAX = coreState.FIELD_MAX;
    var OPTION_KEYS = coreState.OPTION_KEYS;
    var explainHostError = deps.explainHostError;
    var fieldLabel = deps.fieldLabel;
    var fieldRanges = deps.fieldRanges;
    var hostCall = deps.hostCall;
    var panel = coreState.panel;
    var panelItem = deps.panelItem;
    var panelSay = deps.panelSay;
    var parseExamSource = deps.parseExamSource;
    var patchIdFor = deps.patchIdFor;
    var trunc = deps.trunc;
    var panelAiApplyEl = deps.dom.panelAiApplyEl;
    var panelAiAskEl = deps.dom.panelAiAskEl;
    var panelAiCleanEl = deps.dom.panelAiCleanEl;
    var panelAiDiscardEl = deps.dom.panelAiDiscardEl;
    var panelAiFieldEl = deps.dom.panelAiFieldEl;
    var panelAiFoldEl = deps.dom.panelAiFoldEl;
    var panelAiNoteEl = deps.dom.panelAiNoteEl;
    var panelAiPreviewEl = deps.dom.panelAiPreviewEl;
    var panelAiSecEl = deps.dom.panelAiSecEl;
    var panelAiSendEl = deps.dom.panelAiSendEl;
    var panelAiStateEl = deps.dom.panelAiStateEl;
    var panelCleanApplySolutionEl = deps.dom.panelCleanApplySolutionEl;
    var panelCleanApplyStemEl = deps.dom.panelCleanApplyStemEl;
    var panelCleanBoxEl = deps.dom.panelCleanBoxEl;
    var panelCleanDropSolutionEl = deps.dom.panelCleanDropSolutionEl;
    var panelCleanDropStemEl = deps.dom.panelCleanDropStemEl;
    var panelCleanSummaryEl = deps.dom.panelCleanSummaryEl;
    var publish = deps.publish;

  // ---------- 辅助栏 AI 帮改（档 1）：预览归面板，替换归老师那一下点击 ----------
  function setEpEnabled(node, enabled) {
    if (!node) return;
    if (enabled) {
      node.disabled = false;
      node.removeAttribute("aria-disabled");
    } else {
      node.disabled = true;
      node.setAttribute("aria-disabled", "true");
    }
  }

  function aiClear(note) {
    panel.ai = { state: "idle", field: "", key: "", value: "", note: note || "", mock: false, busy: false };
    dropCleanPreview();
    renderAi();
  }

  // ---------- LaTeX 清洗预览（4.3）：先看左右对照，逐段点【采用】才回填 ----------
  var cleanTimer = 0;
  var CLEAN_OPEN_TIMEOUT_MS = 2000;

  function sectionOf(field) {
    var clean = panel.clean;
    if (!clean || !Array.isArray(clean.sections)) return null;
    var found = null;
    clean.sections.forEach(function (section) {
      if (section.field === field) found = section;
    });
    return found;
  }

  function clearCleanTimer() {
    if (cleanTimer) {
      window.clearTimeout(cleanTimer);
      cleanTimer = 0;
    }
  }

  function publishClean(open) {
    if (!publish || !panel.clean) return;
    publish("editor.clean_review", {
      open: Boolean(open),
      key: panel.clean.key,
      sections: open ? panel.clean.sections.map(function (section) {
        return {
          field: section.field,
          label: section.label,
          before: section.before,
          after: section.after,
          changed: section.changed,
          rules: section.rules
        };
      }) : []
    });
  }

  /** 换题 / 重扫时把旧预览撤干净：浮层跟着收，按钮跟着灰。 */
  function dropCleanPreview() {
    clearCleanTimer();
    if (!panel.clean) return;
    publishClean(false);
    panel.clean = null;
    renderClean();
  }

  function cleanTerminal(section) {
    return !section.changed || section.applied || section.dropped;
  }

  function finishCleanIfDone() {
    var clean = panel.clean;
    if (!clean) return;
    var changed = clean.sections.filter(function (section) { return section.changed; });
    if (!changed.length) return;
    var pending = changed.filter(function (section) { return !cleanTerminal(section); });
    if (pending.length) return;
    clean.state = "done";
    publishClean(false);
    var applied = changed.filter(function (section) { return section.applied; }).length;
    panelSay(applied ? "已替换 " + applied + " 段 LaTeX，画布源码待保存。" : "清洗预览已全部放弃，画布源码没动。",
      applied ? "ok" : "info", "cleaned");
  }

  function paintCleanButtons(field, applyEl, dropEl) {
    var clean = panel.clean;
    var section = sectionOf(field);
    var label = section ? section.label : fieldLabel(field);
    var visible = Boolean(clean && section && section.changed && !section.applied && !section.dropped);
    var locked = Boolean(clean && clean.degraded);
    var hasOptions = Boolean(section && section.options && section.options.length);
    if (applyEl) {
      applyEl.hidden = !visible;
      applyEl.disabled = !visible || locked || hasOptions;
      applyEl.textContent = "采用替换（" + label + "）";
    }
    if (dropEl) {
      dropEl.hidden = !visible;
      dropEl.disabled = !visible || locked;
      dropEl.textContent = "放弃（" + label + "）";
    }
  }

  /** 面板只报段名、规则与字数；清洗前后的正文只进画布浮层，不进辅助栏 DOM。 */
  function renderClean() {
    var clean = panel.clean;
    if (panelCleanBoxEl) panelCleanBoxEl.hidden = !clean;
    if (!clean) return;
    var lines = clean.sections.map(function (section) {
      var line = section.label + "：";
      if (!section.changed) {
        line += "未改动";
      } else {
        line += "清洗后 " + section.after.length + " 字（原 " + section.before.length + " 字）";
        if (section.rules && section.rules.length) line += " · 规则 " + section.rules.join("、");
      }
      if (section.applied) line += " · 已替换";
      else if (section.dropped) line += " · 已放弃";
      else if (section.options && section.options.length) line += " · 含选项块，不能自动替换";
      return line;
    });
    if (clean.degraded) lines.push("画布未打开，无法替换：只保留摘要，四个按钮已锁定。");
    if (panelCleanSummaryEl) panelCleanSummaryEl.textContent = lines.join("\n");
    paintCleanButtons("stem", panelCleanApplyStemEl, panelCleanDropStemEl);
    paintCleanButtons("solution", panelCleanApplySolutionEl, panelCleanDropSolutionEl);
  }

  /** 画布没在 2 秒内回执 opened，就不能让老师按到死键：整块降级为纯摘要。 */
  function armCleanTimeout() {
    clearCleanTimer();
    cleanTimer = window.setTimeout(function () {
      cleanTimer = 0;
      if (!panel.clean || panel.clean.state !== "reviewing" || panel.clean.degraded) return;
      panel.clean.degraded = true;
      panel.clean.reason = "timeout";
      renderClean();
      panelSay("画布未打开，无法替换：已降级为纯摘要。", "warn", "clean_degraded");
    }, CLEAN_OPEN_TIMEOUT_MS);
  }

  /** 画布回执：opened / closed / tab_not_live 三种话，都按 key 对号。 */
  function onCleanState(payload) {
    var clean = panel.clean;
    if (!clean) return;
    var key = String((payload && payload.key) || "");
    if (key && key !== String(clean.key)) return;
    var phase = String((payload && payload.phase) || "");
    if (phase === "opened") {
      clearCleanTimer();
      if (clean.degraded && clean.reason === "timeout") {
        clean.degraded = false;
        clean.reason = "";
        renderClean();
      }
      return;
    }
    if (phase === "tab_not_live") {
      clearCleanTimer();
      clean.degraded = true;
      clean.reason = "tab_not_live";
      renderClean();
      panelSay("画布未打开，无法替换：已降级为纯摘要。", "warn", "clean_degraded");
      return;
    }
    if (phase === "closed") {
      clearCleanTimer();
      if (panelAiCleanEl && typeof panelAiCleanEl.focus === "function") panelAiCleanEl.focus();
    }
  }

  /** 单段采用：只回填这一段，另一段照旧等老师拍板。 */
  function onCleanApply(field) {
    var clean = panel.clean;
    var section = sectionOf(field);
    if (!clean || clean.state !== "reviewing" || !section || clean.degraded) return Promise.resolve(null);
    if (!section.changed || section.applied || section.dropped) return Promise.resolve(null);
    if (section.options && section.options.length) {
      panelSay(section.label + "含选项块，整段替换会破坏结构，请手工处理。", "warn", "clean_blocked");
      return Promise.resolve(null);
    }
    return hostCall("editor.apply_patch", {
      id: patchIdFor(clean.key), field: field, value: section.after
    }).then(function (result) {
      section.applied = true;
      renderClean();
      finishCleanIfDone();
      renderClean();
      return result;
    }, function (error) {
      panelSay("替换失败：" + explainHostError(error) + "，画布源码没动。", "error", "failed");
      return null;
    });
  }

  /** 放弃只改本地态，一个字节都不发给画布。 */
  function onCleanDrop(field) {
    var clean = panel.clean;
    var section = sectionOf(field);
    if (!clean || clean.state !== "reviewing" || !section || clean.degraded) return;
    if (!section.changed || section.applied || section.dropped) return;
    section.dropped = true;
    finishCleanIfDone();
    renderClean();
  }

  /**
   * 面板 AI 区唯一的出口：可用性与话术全部从 panel.ai + 当前选区算出来。
   * 预览正文只走 textContent——模型回什么都不许被当成 DOM 结构解析（AGENTS §5）。
   */
  /** AI 帮改那块平时收起；老师自己点开，或改写结果回来了由底座替他展开。 */
  function setAiFold(open) {
    if (panelAiSecEl) panelAiSecEl.setAttribute("data-fold", open ? "open" : "closed");
    if (panelAiFoldEl) panelAiFoldEl.setAttribute("aria-expanded", open ? "true" : "false");
  }

  function aiFoldOpen() {
    return Boolean(panelAiSecEl) && panelAiSecEl.getAttribute("data-fold") === "open";
  }

  function renderAi() {
    var caret = (panel.selection && panel.selection.caret) || null;
    var field = caret && caret.field ? caret.field : "";
    if (panelAiFieldEl) {
      var hint;
      if (!panel.selection) hint = "辅助栏还没收到当前题的源码。";
      else if (!field) hint = "把光标放进题干段或解析段，AI 才知道要改哪一段——选项与「答案：」行由格式宪法锁死，改不到。";
      else hint = "改写字段：" + fieldLabel(field)
        + (caret.has_selection ? "（已选中 " + String(caret.text || "").length + " 字，改写整段）" : "（改写整段）");
      panelAiFieldEl.textContent = hint;
      panelAiFieldEl.setAttribute("data-ai-field", field);
    }
    if (panelAiStateEl) {
      panelAiStateEl.textContent = AI_STATE_LABELS[panel.ai.state] || panel.ai.state;
      panelAiStateEl.setAttribute("data-ai-state", panel.ai.state);
    }
    if (panelAiNoteEl) {
      panelAiNoteEl.textContent = panel.ai.note;
      panelAiNoteEl.setAttribute("data-ai-mock", panel.ai.mock ? "true" : "");
    }
    if (panelAiPreviewEl) {
      panelAiPreviewEl.textContent = panel.ai.value
        || "改写结果会出现在这里，点【采用】才会替换画布源码。";
      panelAiPreviewEl.setAttribute("data-ai-field", panel.ai.field);
      panelAiPreviewEl.setAttribute("data-ai-value", panel.ai.value ? "ready" : "empty");
      // 请求发出去或结果回来了，收起的那块得自己掀开——不然老师看不见进度。
      if (!aiFoldOpen() && (panel.ai.value || panel.ai.busy || panel.ai.state !== "idle")) {
        setAiFold(true);
      }
    }
    var ask = panelAiAskEl ? String(panelAiAskEl.value || "").trim() : "";
    var idle = !panel.ai.busy;
    setEpEnabled(panelAiSendEl, Boolean(field && ask) && panel.ai.state !== "cleaning" && idle);
    setEpEnabled(panelAiCleanEl, Boolean(panel.selection) && panel.ai.state !== "sending" && idle);
    // 【采用】只在「待老师裁决」时亮：模型一回答完就自动覆盖老师源码，是档 1 的红线
    setEpEnabled(panelAiApplyEl, panel.ai.state === "ready" && Boolean(panel.ai.field && panel.ai.value) && idle);
    setEpEnabled(panelAiDiscardEl, panel.ai.state !== "idle" && panel.ai.state !== "sending" && idle);
    [panelAiSendEl, panelAiCleanEl, panelAiApplyEl].forEach(function (node) {
      if (!node) return;
      if (panel.ai.busy) node.setAttribute("aria-busy", "true");
      else node.removeAttribute("aria-busy");
    });
  }

  /**
   * 交给模型的上下文只取契约里看得见的正文与难度，绝不带 extensions、题号以外的身份、更不带令牌——
   * 底座 build_refine_user_message 也只做同样的取舍，两头都别把私有数据喂出去。
   */
  function refineContext(source, field, original) {
    var parsed = parseExamSource(String(source || ""));
    var entry = panel.currentEntry || {};
    var question = {
      type: entry.type || parsed.type || "",
      difficulty: entry.difficulty || "L1",
      stem: parsed.stem || "",
      answer: parsed.answer || "",
      solution: parsed.analysis || "",
      options: parsed.choices.map(function (content, position) {
        return { key: OPTION_KEYS[position] || "A", content: String(content == null ? "" : content) };
      })
    };
    question[field] = original;
    return question;
  }

  function segmentOf(source, field) {
    var range = fieldRanges(source)[field === "solution" ? "solution" : "stem"];
    if (!range) return "";
    return String(source || "").slice(range.start, range.end).trim();
  }

  function onAiSend() {
    var item = panelItem();
    var caret = (panel.selection && panel.selection.caret) || null;
    if (!item || !caret || !caret.field) {
      panelSay("先把光标放进题干段或解析段，AI 才知道改哪一段。", "warn", "idle");
      return;
    }
    if (panel.ai.busy) return;
    var ask = panelAiAskEl ? String(panelAiAskEl.value || "").trim() : "";
    if (!ask) {
      panelSay("指令是空的：说一句要怎么改，再点发送。", "warn", "idle");
      return;
    }
    var original = segmentOf(item.source, caret.field);
    if (!original) {
      panelSay("源码里找不到" + fieldLabel(caret.field) + "段的正文：切到源码补上环境骨架再试。", "error", "invalid");
      return;
    }
    panel.ai = {
      state: "sending", field: caret.field, key: item.key, value: "", note: "", mock: false, busy: true
    };
    renderAi();
    panelSay("改写请求已发出，最长等 " + Math.round(AI_REQUEST_TIMEOUT_MS / 1000) + " 秒…", "info", "sending");
    hostCall("agent.refine", {
      instruction: ask.slice(0, AI_ASK_MAX),
      question: refineContext(item.source, caret.field, original),
      field: caret.field,
      task_id: patchIdFor(item.key).slice(0, 60)
    }, AI_REQUEST_TIMEOUT_MS).then(function (result) {
      panel.ai.busy = false;
      var value = String((result && result.value) || "").trim();
      if (!result || result.ok === false || !value) {
        panel.ai.state = "error";
        panel.ai.note = "模型没给回可采用的正文"
          + ((result && result.note) ? "：" + trunc(result.note, 120) : "；没配 Provider 时底座只会原样回显。");
        renderAi();
        panelSay("改写失败，画布源码没动。", "error", "failed");
        return;
      }
      panel.ai.state = "ready";
      panel.ai.field = result.field === "solution" ? "solution" : caret.field;
      panel.ai.value = trunc(value, FIELD_MAX);
      // 宿主摊平时把 mock 标记丢了：原文与新文逐字相同，就是回显而不是改写，别装作模型改过
      panel.ai.mock = panel.ai.value === original;
      panel.ai.note = panel.ai.mock
        ? "内容与原文逐字相同，多半是回显（本机还没配 Provider）。"
        : trunc(result.note || "", 120);
      renderAi();
      panelSay("改写结果已就绪，看过预览再点【采用】。", "ok", "ready");
    }, function (error) {
      panel.ai.busy = false;
      panel.ai.state = "error";
      panel.ai.note = explainHostError(error);
      renderAi();
      panelSay("改写请求没走通：" + explainHostError(error), "error", "failed");
    });
  }

  /** 采用：面板只发请求，替换由画布执行；两步之间不许把「已发出」说成「已改好」。 */
  function onAiApply() {
    if (panel.ai.state !== "ready" || !panel.ai.field || !panel.ai.value) return;
    var item = panelItem();
    if (!item) {
      panelSay("辅助栏没收到当前题了，回画布点一下那道题再采用。", "warn", "idle");
      return;
    }
    if (item.key !== panel.ai.key) {
      panelSay("当前题已经换成「" + item.key + "」，这份改写属于「" + panel.ai.key + "」，没有回填。", "error", "failed");
      return;
    }
    panel.ai.busy = true;
    renderAi();
    hostCall("editor.apply_patch", {
      id: patchIdFor(panel.ai.key), field: panel.ai.field, value: panel.ai.value
    }).then(function () {
      panel.ai.busy = false;
      panelSay("改写已发给画布的" + fieldLabel(panel.ai.field) + "段——替换结果看中栏提示，保存才入库。", "info", "sent");
    }, function (error) {
      panel.ai.busy = false;
      renderAi();
      panelSay("回填请求没送到画布：" + explainHostError(error), "error", "failed");
    });
  }

  function onAiDiscard() {
    var ask = panelAiAskEl ? panelAiAskEl.value : "";
    panel.ai = { state: "idle", field: "", key: "", value: "", note: "已放弃这次改写。", mock: false, busy: false };
    renderAi();
    if (panelAiAskEl) panelAiAskEl.value = ask;
    panelSay("已放弃这次改写，画布源码没动。", "info", "idle");
  }

  /**
   * 题干段与解析段并发清洗：只生成预览，绝不回填。
   * 任一段清洗不出正文就整次中止；画布没回执 opened 就降级为纯摘要，按钮全锁。
   */
  function cleanViaHost() {
    var item = panelItem();
    if (!item) {
      panelSay("辅助栏还没收到当前题的源码，等画布发一次选区。", "warn", "idle");
      return;
    }
    if (panel.ai.busy) return;
    var jobs = ["stem", "solution"].reduce(function (acc, field) {
      var body = segmentOf(item.source, field);
      if (body) acc.push({ field: field, text: body });
      return acc;
    }, []);
    if (!jobs.length) {
      panelSay("源码里没有可清洗的题干段或解析段。", "warn", "idle");
      return;
    }
    panel.ai = { state: "cleaning", field: "", key: item.key, value: "", note: "", mock: false, busy: true };
    dropCleanPreview();
    renderAi();
    Promise.all(jobs.map(function (job) {
      return hostCall("text.clean_latex", { text: job.text });
    })).then(function (results) {
      var sections = jobs.map(function (job, index) {
        var result = results[index] || {};
        var after = String(result.text || "").trim();
        return {
          field: job.field,
          label: fieldLabel(job.field),
          before: String(job.text || ""),
          after: after,
          changed: Boolean(result.changed) && after.length > 0,
          rules: Array.isArray(result.rules) ? result.rules.map(String) : [],
          options: Array.isArray(result.options) ? result.options : [],
          ok: after.length > 0,
          applied: false,
          dropped: false
        };
      });
      var unusable = sections.filter(function (section) { return !section.ok; });
      if (unusable.length) {
        panel.ai.busy = false;
        panel.ai.state = "error";
        panel.ai.note = "有段落没清洗出正文（" + unusable.map(function (section) { return section.label; }).join("、") + "），源码保持原样。";
        renderAi();
        panelSay("清洗中止，画布源码没动。", "error", "failed");
        return null;
      }
      var changed = sections.filter(function (section) { return section.changed; });
      panel.clean = { key: item.key, sections: sections, state: "reviewing", degraded: false, reason: "" };
      if (!changed.length) {
        panel.clean.state = "done";
        panel.ai.busy = false;
        panel.ai.state = "idle";
        panel.ai.note = "两段都符合规范，没有改动。";
        renderAi();
        renderClean();
        panelSay(panel.ai.note, "ok", "cleaned");
        return null;
      }
      panel.ai.busy = false;
      panel.ai.state = "idle";
      panel.ai.note = "清洗预览已生成：" + changed.length + " 段有改动，逐段点【采用替换】才回填。";
      renderAi();
      renderClean();
      publishClean(true);
      armCleanTimeout();
      panelSay(panel.ai.note, "ok", "cleaned");
      return null;
    }, function (error) {
      panel.ai.busy = false;
      panel.ai.state = "error";
      panel.ai.note = "清洗失败：" + explainHostError(error) + "，源码保持原样。";
      renderAi();
      panelSay("清洗失败，画布源码没动。", "error", "failed");
    });
  }

    return {
      aiClear: aiClear,
      aiFoldOpen: aiFoldOpen,
      cleanViaHost: cleanViaHost,
      onAiApply: onAiApply,
      onAiDiscard: onAiDiscard,
      onAiSend: onAiSend,
      onCleanApply: onCleanApply,
      onCleanDrop: onCleanDrop,
      onCleanState: onCleanState,
      refineContext: refineContext,
      renderAi: renderAi,
      renderClean: renderClean,
      segmentOf: segmentOf,
      setAiFold: setAiFold,
      setEpEnabled: setEpEnabled,
    };
  }

  global.JzoEditorAi = { create: create };
})(window);
