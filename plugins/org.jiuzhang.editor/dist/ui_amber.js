/**
 * ui_amber.js —— 琥珀灯（军令 #32 · 判据 5.2）。
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）
 *
 * 这盏灯只管一件事：这一题**还有未清项**，老师没弄完。
 * 三项按判据 5.2 的原话：待老师核（源码还没认全）／公式占位／缺考向。
 * 占位符那一项与底座 pending_pool 的入库前点名同一张名单、同一处扫描范围，
 * 插件不另立标准，也不替底座做决定——灯只报「有事」，能不能入库仍由后端判。
 *
 * 与另外两盏灯的分工（判据 5.2）：
 * - 青黛 #6b8ca6：悬停才亮，说的是「我在这儿」；
 * - 琥珀 #c08a2e：只要还有未清项就**常驻呼吸**，题卡与辅助栏边缘同时亮，清掉才熄；
 * - 红 #9b3b2d：从此只在重题池那一屏用，审核画布再也不出现红色。
 *
 * 两帧共用这一份判定：画布按整批算（题卡一盏盏点亮 + 判据 43 的预扫），
 * 辅助栏按当前题算（表单一动立刻重算，并把结论投给画布那一格）。
 */
(function (global) {
  "use strict";

  // 与底座 pending_pool._PLACEHOLDER_MARKS 同一份名单。识别留在题面上的占位文，
  // 三处都在正文里，藏不住；这里只「读」它判有没有清干净，不参与任何写入判断。
  var PLACEHOLDER_MARKS = ["（待识别", "(待识别", "待补", "【待", "___"];

  function create(deps) {
    var coreState = deps.coreState;
    var PLUGIN_ID = coreState.PLUGIN_ID;
    var panel = coreState.panel;
    var parseExamSource = deps.parseExamSource;
    var publish = deps.publish;
    var readForm = deps.readForm;
    var state = coreState.state;
    var metaFor = deps.metaFor;
    var parsedOf = deps.parsedOf;
    var hostCall = deps.hostCall;
    var panelSay = deps.panelSay;
    var jumpTo = deps.jumpTo;
    var refreshBatches = deps.refreshBatches;
    var panelPoolRefresh = deps.panelPoolRefresh;
    var panelApproveAllEl = deps.dom.panelApproveAllEl;
    var panelRoot = deps.dom.panelRoot;
    var renderBodyEl = deps.dom.renderBodyEl;
    // 辅助栏会被反复 activate，那颗钮的监听只挂一次。
    var approveWired = false;

  function textOf(value) {
    return String(value == null ? "" : value);
  }

  /**
   * 题面里还剩哪些占位文。扫描范围与底座 pending_pool._placeholder_hits 逐字对齐：
   * 题干（stem）＋解析（solution）＋每个选项（options.content）。
   * 底座不扫「答案」行，这里也不多扫一项——灯比后端严，就会出现「灯拦着、后端其实能存」
   * 的假阳性整批卡壳；这条差异已作为「后端不够用的字段」上报。
   */
  function placeholderHits(parsed) {
    var body = parsed || {};
    var texts = [body.stem, body.analysis];
    var choices = Array.isArray(body.choices) ? body.choices : [];
    choices.forEach(function (choice) { texts.push(choice); });
    return PLACEHOLDER_MARKS.filter(function (mark) {
      return texts.some(function (text) { return textOf(text).indexOf(mark) >= 0; });
    });
  }

  /**
   * 这一题还差什么：返回的是「老师看得懂的话」，空数组就是清干净了。
   * 三项与判据 5.2 列的一一对上：源码没认全＝待老师核，占位文＝公式占位，
   * meta.topic_ids 空＝缺考向。
   */
  function amberReasons(parsed, meta) {
    var body = parsed || {};
    var reasons = [];
    var errors = Array.isArray(body.errors) ? body.errors : [];
    if (errors.length) reasons.push("源码尚未认全");
    var hits = placeholderHits(body);
    if (hits.length) reasons.push("公式占位未清（" + hits.join("、") + "）");
    var topics = (meta && Array.isArray(meta.topic_ids)) ? meta.topic_ids : [];
    if (!topics.length) reasons.push("还没挂考向");
    return reasons;
  }

  function blockAt(index) {
    if (!renderBodyEl || !renderBodyEl.children) return null;
    return renderBodyEl.children[index] || null;
  }

  /** 画布上那道题的灯：只动 data-amber，样式在 effects.css。 */
  function paintBlock(index, reasons) {
    var block = blockAt(index);
    if (!block) return;
    if (reasons && reasons.length) {
      block.setAttribute("data-amber", "on");
      block.setAttribute("data-amber-reasons", reasons.join("；"));
    } else {
      block.removeAttribute("data-amber");
      block.removeAttribute("data-amber-reasons");
    }
  }

  /** 整屏逐格重画：怎么算不归本模块管，调用方给一题一份清单。 */
  function paintAll(reasonsOf) {
    if (!renderBodyEl) return;
    Array.prototype.forEach.call(renderBodyEl.children, function (_cell, index) {
      paintBlock(index, reasonsOf(index) || []);
    });
  }

  /** 辅助栏边缘那一圈：画布没开也照样亮，它报的是「当前这道题还没弄完」。 */
  function paintEdge(reasons) {
    if (!panelRoot) return;
    if (reasons && reasons.length) {
      panelRoot.setAttribute("data-amber", "on");
      panelRoot.setAttribute("data-amber-reasons", reasons.join("；"));
    } else {
      panelRoot.removeAttribute("data-amber");
      panelRoot.removeAttribute("data-amber-reasons");
    }
  }

  /** 这一题的未清项（画布口径）：源码走缓存的解析结果，元数据走宿主代持的草稿。 */
  function reasonsAt(index) {
    var item = state.items[index];
    if (!item) return [];
    return amberReasons(parsedOf(item), metaFor(item, {}));
  }

  /** 整批扫一遍（判据 43）：indexes 按录入序升序，top 就是「最上面那道」。 */
  function scan() {
    var indexes = [];
    for (var index = 0; index < state.items.length; index += 1) {
      if (reasonsAt(index).length) indexes.push(index);
    }
    return { count: indexes.length, indexes: indexes, top: indexes.length ? indexes[0] : -1 };
  }

  /** 画布侧一次性把整屏灯点亮。 */
  function repaintCanvas() {
    if (state.slot !== "stage.center") return;
    paintAll(reasonsAt);
  }

  /**
   * 辅助栏侧的实时灯：表单、考向胶囊一有动静就算一次，
   * 并把同一份结论投给画布那一格——「左侧题卡与右侧辅助栏边缘同时亮」靠这一句成立。
   */
  function repaintPanel() {
    if (state.slot === "stage.center") return;
    var sel = panel.selection;
    if (!sel || sel.mode !== "review" || !sel.source) {
      paintEdge([]);
      return;
    }
    var reasons = amberReasons(parseExamSource(String(sel.source || "")), readForm() || {});
    paintEdge(reasons);
    if (publish) {
      publish("editor.batch_review", {
        pluginId: PLUGIN_ID, from: "panel", action: "amber",
        index: Number(sel.index) || 0, reasons: reasons
      });
    }
  }

  // ---------- 【全部入库】（军令 #32 · 判据 43）----------
  // 顺序是死的：先整批扫琥珀灯 → 有未清项一题都不存、直接跳到最上面那道 →
  // 全清才逐题走「存入主库」同一条通道（pending.approve）。
  // 池内题不参与：抽走时后端已把它们从待审清单里摘掉，这里就照 state.items 报数，
  // 前端绝不再特判扣一遍——扣一次就对不上账。
  function approveTargets() {
    var targets = [];
    state.items.forEach(function (item) {
      if (item.pendingId && item.status !== "stored") targets.push(item);
    });
    return targets;
  }

  /** 辅助栏那颗钮：画布才有整批的题与滚动条，所以只发令、不在这一帧算账。 */
  function askApproveAll() {
    if (!publish) return;
    publish("editor.batch_review", { pluginId: PLUGIN_ID, from: "panel", action: "approve_all" });
  }

  function tellCanvas(detail) {
    if (!publish) return;
    var body = detail || {};
    body.pluginId = PLUGIN_ID;
    body.from = "canvas";
    body.action = "approve_all";
    publish("editor.batch_review", body);
  }

  /** 画布侧执行：扫灯→拦下或逐题入库，最后把结果回给辅助栏念。 */
  function runApproveAll() {
    if (state.slot !== "stage.center") return;
    if (panel.approveBusy) return;
    var loadDraft = deps.loadMetaDraft;
    var started = loadDraft ? loadDraft() : Promise.resolve(null);
    started.then(function () {
      var found = scan();
      if (found.count) {
        repaintCanvas();
        if (jumpTo) jumpTo(found.top);
        tellCanvas({ blocked: true, count: found.count, top: found.top, reasons: reasonsAt(found.top) });
        return null;
      }
      var targets = approveTargets();
      if (!targets.length) {
        tellCanvas({ blocked: false, stored: 0, failed: 0, empty: true });
        return null;
      }
      panel.approveBusy = true;
      var stored = 0;
      var failed = 0;
      var firstError = "";
      // 全批灯都灭了才动手：先把画布上改过的题静默写回中转池，否则【全部入库】
      // 存的是上一次存池的旧文，老师以为存的是刚改的那一版。
      // 这一步排在扫灯之后：扫过就说明干净，`stashOne` 那道 validateForSave 不会再拒存。
      var stashFirst = deps.stashBeforeLeave ? deps.stashBeforeLeave() : Promise.resolve(null);
      return stashFirst.then(function () {
        var chain = Promise.resolve();
        targets.forEach(function (item) {
          chain = chain.then(function () {
            return hostCall("pending.approve", { pending_id: item.pendingId }).then(function () {
              stored += 1;
              item.status = "stored";
            }, function (error) {
              failed += 1;
              if (!firstError) firstError = (error && error.message) || "未知原因";
            });
          });
        });
        return chain.then(function () {
          panel.approveBusy = false;
          // 账在画布这一帧：入库完了由它重拉批次卡片，辅助栏只负责把结果念出来。
          if (refreshBatches) refreshBatches();
          tellCanvas({ blocked: false, stored: stored, failed: failed, message: firstError });
        });
      });
    }).catch(function (error) {
      panel.approveBusy = false;
      tellCanvas({ blocked: false, stored: 0, failed: 0, message: (error && error.message) || "未知原因" });
    });
  }

  /** 辅助栏侧收口：话在这里说，画布只管办事。批次账已由画布自己重拉，这里不重复。 */
  function onCanvasApproveAll(detail) {
    var body = detail || {};
    if (body.blocked) {
      var why = Array.isArray(body.reasons) ? body.reasons.join("；") : "";
      panelSay("还差 " + (Number(body.count) || 0) + " 题没清完，一题都没存。"
        + "已跳到最上面那道（第 " + ((Number(body.top) || 0) + 1) + " 题）："
        + (why || "见题卡上的琥珀灯") + "。", "warn", "invalid");
      return;
    }
    if (body.empty) {
      panelSay("这一批没有待入库的题了（池内那条不参与整批入库）。", "info", "idle");
      return;
    }
    var stored = Number(body.stored) || 0;
    var failed = Number(body.failed) || 0;
    if (failed) {
      panelSay("整批入库停了：成功 " + stored + " 题，失败 " + failed
        + " 题。最后一句报错：" + (body.message || "未知原因"), "error", "failed");
    } else {
      panelSay("整批入库完成：共存入 " + stored + " 题。", "ok", "created");
    }
    // 池子列表住在辅助栏这一帧的内存里，画布够不着，只能这边自己重取。
    if (panelPoolRefresh) panelPoolRefresh();
  }

  /** 那颗钮只在辅助栏那帧接活：画布这一帧一颗按钮都不许有（军令 #23）。 */
  function wireApproveAll() {
    if (!panelApproveAllEl || state.slot === "stage.center") return;
    if (approveWired) return;
    approveWired = true;
    panelApproveAllEl.addEventListener("click", askApproveAll);
  }

    return {
      PLACEHOLDER_MARKS: PLACEHOLDER_MARKS,
      amberReasons: amberReasons,
      approveTargets: approveTargets,
      askApproveAll: askApproveAll,
      onCanvasApproveAll: onCanvasApproveAll,
      paintAll: paintAll,
      paintBlock: paintBlock,
      paintEdge: paintEdge,
      placeholderHits: placeholderHits,
      reasonsAt: reasonsAt,
      repaintCanvas: repaintCanvas,
      repaintPanel: repaintPanel,
      runApproveAll: runApproveAll,
      scan: scan,
      wireApproveAll: wireApproveAll,
    };
  }

  global.JzoEditorAmber = { create: create };
})(window);
