/**
 * 待审任务工作台（org.jiuzhang.bank-engine / ui_review.js）。
 *
 * 从 plugin.js 拆出（PLUGIN_SPEC §2.8.1「单文件不得过 800 行」）：
 * - 待审：按迁移标记（缺答案依据、题型待判、只挂到节层…）分组列出，逐条判
 *   「保留 / 丢弃 / 交录题端改」，翻页令牌与 loadQuestions 同款——慢响应不许覆盖新结果。
 *
 * 本模块只画面板；写库动作一律经 ctx.hostCall 发一条宿主请求，由底座执行。
 * 题块怎么渲染（el / appendRich / 标签翻译）来自 ui_browse.js，由 plugin.js 转交。
 */
(function (global) {
  "use strict";

  var REVIEW_PAGE_SIZE = 6;

  function create(ctx) {
    var state = ctx.state;
    var root = ctx.root;
    var hostCall = ctx.hostCall;
    var dock = ctx.dock;
    var toast = ctx.toast;
    var renderAll = ctx.renderAll;
    var openEditor = ctx.openEditor;
    var el = ctx.el;
    var appendRich = ctx.appendRich;
    var answerText = ctx.answerText;
    var difficultyLabel = ctx.difficultyLabel;
    var typeLabel = ctx.typeLabel;
    var sourceLine = ctx.sourceLine;
    var migrationFlags = ctx.migrationFlags;
    var mountPager = ctx.mountPager;

    // 待审队列的并发令牌：连点翻页时只认最后一次响应
    var reviewToken = 0;

    // ---------- 人工审核（待审任务） ----------
    var FLAG_LABELS = {
      answer_absent: "没有答案依据",
      answer_region_empty: "答案区是空白",
      type_manual_review: "题型待人工判",
      structure_conflict: "选项内嵌正文",
      topic_unmapped: "只挂到节层",
      needs_conclusion: "结论未单独成字段",
      solution_absent: "连答案正文都没有"
    };

    function flagLabel(flag) { return FLAG_LABELS[flag] || flag; }

    function loadReview(page) {
      state.view = "review";
      state.reviewLoading = true;
      state.reviewError = "";
      if (page) state.reviewPage = page;
      // 与 loadQuestions 同款令牌：连点翻页或回流刷新并发时，慢响应不许覆盖新结果
      var token = ++reviewToken;
      renderAll();
      return hostCall("bank.review", {
        flag: state.reviewFlag,
        page: state.reviewPage,
        page_size: REVIEW_PAGE_SIZE
      }).then(function (result) {
        if (token !== reviewToken) return;
        state.reviewItems = (result && result.items) || [];
        state.reviewTotal = (result && result.total) || 0;
        state.reviewPages = (result && result.total_pages) || 1;
        state.reviewSummary = (result && result.summary) || { total: 0, flags: [] };
        state.reviewLoading = false;
        renderAll();
      }).catch(function (error) {
        if (token !== reviewToken) return;
        state.reviewLoading = false;
        state.reviewItems = [];
        state.reviewError = error.message;
        renderAll();
      });
    }

    function buildReviewCard(question) {
      var card = el("article", "cb-review-card");
      card.setAttribute("data-review-id", question.id);

      var head = el("div", "cb-review-head");
      head.appendChild(el("p", "cb-review-stem", question.stem.slice(0, 160)));
      var chips = el("div", "cb-review-chips");
      chips.appendChild(el("span", "cb-chip", typeLabel(question.type)));
      chips.appendChild(el("span", "cb-chip", difficultyLabel(question.difficulty)));
      chips.appendChild(el("span", "cb-chip", question.grade || "未标注"));
      migrationFlags(question).forEach(function (flag) {
        chips.appendChild(el("span", "cb-chip cb-chip-review", flagLabel(flag)));
      });
      chips.appendChild(el("span", "cb-review-id", question.id));
      head.appendChild(chips);
      card.appendChild(head);

      // 三端分离：题库是存储端，只读。改题目一律交给录题工作台（输入端）。
      var body = el("div", "cb-review-body");
      var edit = el("button", "cb-btn cb-btn-primary", "去编辑");
      edit.type = "button";
      edit.addEventListener("click", function () { openEditor(question.id); });
      body.appendChild(edit);
      var hints = {
        answer_absent: "补答案：点「去编辑」在录题工作台里选选项字母或填答案正文。",
        answer_region_empty: "补答案：原卷有【答案】标记但标记后是空白。",
        type_manual_review: "判题型：通篇解析没有结论标记，需要老师定单选/多选/填空/解答。",
        structure_conflict: "拆结构：选项内嵌在题干里，需要在录题工作台重排选项或改判解答题。",
        topic_unmapped: "挂考向：在录题工作台的考向大纲树里选一个节点。",
        needs_conclusion: "补结论：把最终答案单独填进答案栏。",
        solution_absent: "补答案：旧库连答案正文都没有。"
      };
      var first = migrationFlags(question)[0];
      body.appendChild(el("p", "cb-review-hint", hints[first] || "确认无误后可在录题工作台里清掉标记。"));
      card.appendChild(body);
      return card;
    }

    function renderReviewPanel(host) {
      var panel = el("div", "cb-review");

      var aside = el("div", "cb-review-filters");
      aside.appendChild(el("h2", "cb-review-heading", "待审标记"));
      var allButton = el("button", "cb-review-flag" + (state.reviewFlag ? "" : " cb-tree-active"),
        "全部待审 " + (state.reviewSummary.total || 0));
      allButton.type = "button";
      allButton.addEventListener("click", function () {
        state.reviewFlag = "";
        loadReview(1);
      });
      aside.appendChild(allButton);
      (state.reviewSummary.flags || []).forEach(function (item) {
        var button = el("button",
          "cb-review-flag" + (state.reviewFlag === item.name ? " cb-tree-active" : ""),
          flagLabel(item.name) + " · " + item.count);
        button.type = "button";
        button.addEventListener("click", function () {
          state.reviewFlag = item.name;
          loadReview(1);
        });
        aside.appendChild(button);
      });
      aside.appendChild(el("p", "cb-review-note",
        "标记来自灌库校验：答案取不到字母的一律留空，不拿 A 冒充。修一条清一条。"));
      panel.appendChild(aside);

      var list = el("div", "cb-review-list");
      if (state.reviewLoading && !state.reviewItems.length) {
        list.appendChild(el("p", "cb-loading", "正在读取待审队列…"));
      } else if (state.reviewError) {
        list.appendChild(el("p", "cb-tree-error", "待审队列读取失败：" + state.reviewError));
        var retry = el("button", "cb-btn", "重试");
        retry.type = "button";
        retry.addEventListener("click", function () { loadReview(); });
        list.appendChild(retry);
      } else if (!state.reviewItems.length) {
        list.appendChild(el("p", "cb-empty", "这一类没有待审题了——真题的人工审核已清账。"));
      } else {
        state.reviewItems.forEach(function (question) {
          list.appendChild(buildReviewCard(question));
        });
        if (state.reviewPages > 1) {
          list.appendChild(mountPager(state.reviewPage, state.reviewPages, state.reviewTotal, loadReview));
        }
      }
      panel.appendChild(list);
      host.appendChild(panel);
    }

    return {
      loadReview: loadReview,
      renderReviewPanel: renderReviewPanel
    };
  }

  global.JzoBankReview = { create: create };
})(window);
