/**
 * 待审任务与查重清洗工作台（org.jiuzhang.bank-ui / ui_review.js）。
 *
 * 从 plugin.js 拆出（PLUGIN_SPEC §2.8.1「单文件不得过 800 行」）：
 * - 待审：按迁移标记（缺答案依据、题型待判、只挂到节层…）分组列出，逐条判
 *   「保留 / 丢弃 / 交录题端改」，翻页令牌与 loadQuestions 同款——慢响应不许覆盖新结果；
 * - 查重：题面指纹相同才算重复，主记录与副本各留答案与解析，审一组存一组，
 *   合并不重扫（「一键扫描」是显式动作，回流刷新不能把老师正在比的题抽走）。
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

    // ---------- 查重清洗（军令 #18-终 阶段五） ----------
    // 双栏 1:1 落在画布内：左栏/右栏/底栏永远归宿主，插件不得反向操控宿主布局
    // （PLUGIN_SPEC §2.4、§2.9），而且宿主右栏上限 520px、与画布成不了 1:1。
    // 所以审查模式接管的是插件自己的三栏浏览布局（大纲 | 列表 | 详情 → 全宽双栏题卡）。
    var DUPE_FIELD_LABELS = {
      answer: "答案",
      difficulty: "难度",
      grade: "年级",
      solution: "解析",
      sources: "来源关系",
      topics: "考向挂载",
      extensions: "单题备注"
    };

    function loadDedupe() {
      state.view = "dedupe";
      if (state.dupeLoading || state.dupeBusy) return null;
      state.dupeLoading = true;
      state.dupeError = "";
      renderAll();
      return hostCall("bank.dedupe_scan", {}).then(function (result) {
        state.dupeQueue = (result && result.groups) || [];
        state.dupeScanned = (result && result.scanned) || 0;
        state.dupeRedundant = (result && result.redundant) || 0;
        state.dupeTruncated = (result && result.truncated) || 0;
        state.dupePrimary = "";
        state.dupeLoading = false;
        renderAll();
        dock("查重扫描完成：" + state.dupeScanned + " 题里有 " + state.dupeQueue.length + " 组重复");
      }, function (error) {
        state.dupeLoading = false;
        state.dupeQueue = [];
        state.dupeError = error.message;
        renderAll();
        toast("查重扫描失败：" + error.message);
      });
    }

    function dupeChips(question) {
      var chips = el("div", "cb-dupe-chips");
      chips.appendChild(el("span", "cb-chip", typeLabel(question.type)));
      var difficulty = el("span", "cb-chip", difficultyLabel(question.difficulty));
      difficulty.setAttribute("data-kind", question.difficulty);
      chips.appendChild(difficulty);
      chips.appendChild(el("span", "cb-chip", question.grade || "未标注"));
      var taxonomy = question.taxonomy || {};
      var topics = taxonomy.topic_ids || [];
      if (topics.length) {
        chips.appendChild(el("span", "cb-chip", "考向 " + topics.length + " 个"
          + (taxonomy.chapter ? "（" + taxonomy.chapter + "）" : "")));
      }
      if (question.source && question.source.paper_title) {
        chips.appendChild(el("span", "cb-chip", sourceLine(question)));
      }
      migrationFlags(question).forEach(function (flag) {
        chips.appendChild(el("span", "cb-chip cb-chip-review", flagLabel(flag)));
      });
      chips.appendChild(el("span", "cb-review-id", question.id));
      return chips;
    }

    function markDupeKept(questionId) {
      state.dupePrimary = questionId;
      // 只改标记不整块重画：renderAll 会把焦点从老师刚按的单选钮上抢走
      Array.prototype.forEach.call(root.querySelectorAll(".cb-dupe-card"), function (card) {
        var kept = card.getAttribute("data-dupe-id") === questionId;
        card.classList.toggle("cb-dupe-kept", kept);
        var radio = card.querySelector("input[type=radio]");
        if (radio) radio.checked = kept;
      });
      var button = root.querySelector(".cb-dupe-merge");
      if (button) button.disabled = !questionId || state.dupeBusy;
      var tip = root.querySelector(".cb-dupe-merge-tip");
      if (tip) {
        var group = state.dupeQueue[0];
        tip.textContent = questionId && group
          ? "将删除其余 " + (group.ids.length - 1) + " 题，考向/来源/备注并进保留项"
          : "先点一张卡上的「保留这题」";
      }
    }

    function buildDupeCard(question) {
      var card = el("article", "cb-dupe-card");
      card.setAttribute("data-dupe-id", question.id);

      var pick = el("label", "cb-dupe-pick");
      var radio = document.createElement("input");
      radio.type = "radio";
      radio.name = "cb-dupe-primary";
      radio.value = question.id;
      radio.checked = state.dupePrimary === question.id;
      radio.addEventListener("change", function () { markDupeKept(question.id); });
      pick.appendChild(radio);
      pick.appendChild(el("span", null, "保留这题"));
      card.appendChild(pick);
      if (state.dupePrimary === question.id) card.classList.add("cb-dupe-kept");

      card.appendChild(dupeChips(question));

      var body = el("div", "cb-dupe-body");
      appendRich(body, question.stem);
      if (question.options && question.options.length) {
        var options = el("ol", "cb-options");
        question.options.forEach(function (option) {
          var item = el("li", "cb-option");
          item.appendChild(el("span", "cb-key", option.key + "."));
          var text = el("span");
          appendRich(text, option.content);
          item.appendChild(text);
          options.appendChild(item);
        });
        body.appendChild(options);
      }
      var answer = el("p", "cb-dupe-answer");
      answer.appendChild(el("span", "cb-answer-label", "答案："));
      answer.appendChild(document.createTextNode(
        answerText(question) || "待补 — 原资料里没有可依据的答案"));
      body.appendChild(answer);
      if (state.dupeShowSolution && question.solution) {
        var solution = el("div", "cb-solution");
        solution.appendChild(el("span", "cb-answer-label", "解析："));
        appendRich(solution, question.solution);
        body.appendChild(solution);
      }
      card.appendChild(body);
      return card;
    }

    function mergeDupeGroup(group) {
      var primary = state.dupePrimary;
      var copies = group.ids.filter(function (id) { return id !== primary; });
      if (!primary || !copies.length || state.dupeBusy) return;
      state.dupeBusy = true;
      renderAll();
      hostCall("bank.dedupe_merge", { primary_id: primary, copy_ids: copies })
        .then(function (result) {
          state.dupeBusy = false;
          state.dupeQueue = state.dupeQueue.slice(1);   // 审一组存一组：落库即出队，不用重扫
          state.dupePrimary = "";
          state.dupeMerged += copies.length;
          state.dupeScanned = Math.max(0, state.dupeScanned - copies.length);
          state.dupeRedundant = Math.max(0, state.dupeRedundant - copies.length);
          renderAll();
          var moved = (result && result.moved) || {};
          toast("已收敛 " + copies.length + " 题：考向 +" + (moved.topics || []).length
            + " · 来源 +" + (moved.sources || []).length
            + " · 备注 +" + (moved.extensions || []).length);
          dock("查重合并完成：保留 " + primary + "，删除 " + copies.join("、"));
        }, function (error) {
          state.dupeBusy = false;
          renderAll();
          toast("合并失败，题库一字未动：" + error.message);
        });
    }

    function renderDedupeGroup(host, group) {
      var head = el("div", "cb-dupe-head");
      var difference = (group.differing_fields || []).map(function (key) {
        return DUPE_FIELD_LABELS[key] || key;
      });
      head.appendChild(el("p", "cb-dupe-title",
        group.ids.length + " 道题面完全相同（" + typeLabel(group.type) + "）· 还剩 "
          + state.dupeQueue.length + " 组"));
      head.appendChild(el("p", "cb-dupe-diff", difference.length
        ? "组内不同的只有：" + difference.join("、") + "——都是「录了两遍」留下的，不冲突"
        : "组内每一项都一样，留一条就够"));
      host.appendChild(head);

      var cards = el("div", "cb-dupe-cards");
      cards.setAttribute("role", "radiogroup");
      cards.setAttribute("aria-label", "重复题组，单选保留项");
      group.documents.forEach(function (question) { cards.appendChild(buildDupeCard(question)); });
      host.appendChild(cards);

      var actions = el("div", "cb-dupe-actions");
      var toggle = el("button", "cb-btn", state.dupeShowSolution ? "收起解析" : "展开解析");
      toggle.type = "button";
      toggle.addEventListener("click", function () {
        state.dupeShowSolution = !state.dupeShowSolution;
        renderAll();
      });
      actions.appendChild(toggle);

      var skip = el("button", "cb-btn", "跳过这组");
      skip.type = "button";
      skip.addEventListener("click", function () {
        state.dupeQueue = state.dupeQueue.slice(1).concat([group]);
        state.dupeSkipped += 1;
        state.dupePrimary = "";
        renderAll();
      });
      actions.appendChild(skip);

      var tip = el("span", "cb-dupe-merge-tip",
        state.dupePrimary ? "将删除其余 " + (group.ids.length - 1) + " 题，考向/来源/备注并进保留项"
          : "先点一张卡上的「保留这题」");
      actions.appendChild(tip);

      var merge = el("button", "cb-btn cb-btn-primary cb-dupe-merge", "确认合并");
      merge.type = "button";
      merge.disabled = !state.dupePrimary || state.dupeBusy;
      merge.setAttribute("aria-busy", String(state.dupeBusy));
      merge.addEventListener("click", function () { mergeDupeGroup(group); });
      actions.appendChild(merge);
      host.appendChild(actions);
    }

    function renderDedupePanel(host) {
      var panel = el("div", "cb-dupe");
      var bar = el("div", "cb-dupe-bar");
      var scan = el("button", "cb-btn cb-btn-primary", "一键扫描");
      scan.type = "button";
      scan.disabled = state.dupeLoading || state.dupeBusy;
      scan.setAttribute("aria-busy", String(state.dupeLoading));
      scan.addEventListener("click", function () { loadDedupe(); });
      bar.appendChild(scan);
      var status = el("p", "cb-dupe-status",
        state.dupeLoading ? "正在按指纹归一全库题面…"
          : (state.dupeScanned
            ? "已扫 " + state.dupeScanned + " 题 · 重复 " + state.dupeRedundant + " 题可清"
              + (state.dupeMerged ? " · 本轮已收敛 " + state.dupeMerged + " 题" : "")
              + (state.dupeSkipped ? " · 跳过 " + state.dupeSkipped + " 组" : "")
            : "还没扫描。扫描只读，不动库里一个字。"));
      status.setAttribute("aria-live", "polite");
      bar.appendChild(status);
      panel.appendChild(bar);
      if (state.dupeTruncated) {
        panel.appendChild(el("p", "cb-review-note",
          "重复组太多，本次只回了前 " + state.dupeQueue.length + " 组（还有 "
            + state.dupeTruncated + " 组被截在外），清完再扫一次。"));
      }

      if (state.dupeError) {
        panel.appendChild(el("p", "cb-tree-error", "扫描失败：" + state.dupeError));
      } else if (state.dupeLoading) {
        panel.appendChild(el("p", "cb-loading", "正在读取重复组…"));
      } else if (!state.dupeQueue.length) {
        panel.appendChild(el("p", "cb-empty", state.dupeScanned
          ? "没有需要清洗的重复组了——题面指纹全库唯一。"
          : "点【一键扫描】找出题面完全相同的题（排版差异、选项顺序、配图都算在内）。"));
      } else {
        var group = state.dupeQueue[0];
        if (group.ids.length <= 1) {
          // 组里只剩一条就不叫重复了（多半是别处刚删过题），直接出队而不是空转一轮扫描
          state.dupeQueue = state.dupeQueue.slice(1);
          renderDedupePanel(host);
          return;
        }
        renderDedupeGroup(panel, group);
      }
      host.appendChild(panel);
    }

    return {
      loadReview: loadReview,
      renderReviewPanel: renderReviewPanel,
      loadDedupe: loadDedupe,
      renderDedupePanel: renderDedupePanel
    };
  }

  global.JzoBankReview = { create: create };
})(window);
