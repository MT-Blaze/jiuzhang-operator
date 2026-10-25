/**
 * 真题题库视图插件运行时（org.jiuzhang.bank-ui）。
 *
 * 本插件只有界面，没有题库：列表/大纲/待审/查重一律经 jzo-plugin/1 协议向宿主
 * 申请「活跃题库」的数据，宿主再交给题库引擎（app/core/bank.py）查询。
 * 插件拿不到数据库、文件系统与令牌。
 *
 * 右栏面板（ui.params.changed）是筛选的权威来源；本页顶部只保留搜索与刷新，
 * 避免同一条件出现两个写入者。
 */
(function () {
  "use strict";

  var PROTOCOL = "jzo-plugin/1";
  var PLUGIN_ID = "org.jiuzhang.bank-ui";
  var PAGE_SIZE = 12;
  var REVIEW_PAGE_SIZE = 6;
  var REQUEST_TIMEOUT_MS = 15000;

  var root = document.getElementById("root");
  var stageMode = false;
  var requestSeq = 0;
  var pending = new Map();
  var loadToken = 0;
  var reviewToken = 0;
  var toastTimer = null;
  var basketIds = Object.create(null);

  var state = {
    grade: "全部",
    difficulty: "全部",
    type: "全部",
    topic: "",
    topicName: "",
    search: "",
    page: 1,
    pageSize: PAGE_SIZE,
    total: 0,
    items: [],
    selected: null,
    showSolution: false,
    loading: false,
    view: "list",
    reviewFlag: "",
    reviewPage: 1,
    reviewPages: 1,
    reviewTotal: 0,
    reviewItems: [],
    reviewSummary: { total: 0, flags: [] },
    reviewLoading: false,
    reviewError: "",
    // 查重清洗（军令 #18-终 阶段五）：扫描结果留在本地，审一组存一组，
    // 合并不重扫——「一键扫描」是显式动作，回流刷新不能把老师正在比的题抽走。
    dupeQueue: [],
    dupePrimary: "",
    dupeShowSolution: false,
    dupeLoading: false,
    dupeBusy: false,
    dupeError: "",
    dupeScanned: 0,
    dupeRedundant: 0,
    dupeTruncated: 0,
    dupeMerged: 0,
    dupeSkipped: 0
  };

  // 大纲树：册/章/节/考向按需懒加载，expanded 记开合，children 记已取回的一层
  var tree = { roots: null, children: {}, expanded: {}, loading: false, error: "" };

  // ---------- 宿主通信 ----------
  function hostCall(method, payload) {
    return new Promise(function (resolve, reject) {
      requestSeq += 1;
      var id = "p" + requestSeq + "_" + Date.now().toString(36);
      var timer = window.setTimeout(function () {
        pending.delete(id);
        reject(new Error("宿主响应超时（" + Math.round(REQUEST_TIMEOUT_MS / 1000) + "s）"));
      }, REQUEST_TIMEOUT_MS);
      pending.set(id, {
        resolve: function (result) { window.clearTimeout(timer); resolve(result); },
        reject: function (error) { window.clearTimeout(timer); reject(error); }
      });
      try {
        window.parent.postMessage({
          protocol: PROTOCOL,
          id: id,
          kind: "request",
          method: method,
          payload: payload || {}
        }, "*");
      } catch (error) {
        pending.delete(id);
        window.clearTimeout(timer);
        reject(error);
      }
    });
  }

  function dock(text) {
    try {
      window.parent.postMessage({
        protocol: PROTOCOL,
        kind: "notification",
        event: "region.dock",
        payload: { text: String(text).slice(0, 200) }
      }, "*");
    } catch (error) {
      /* 通知丢一帧不致命 */
    }
  }

  function applyParams(values, by) {
    if (!values || typeof values !== "object") return;
    var changed = false;
    ["grade", "difficulty", "type"].forEach(function (key) {
      if (typeof values[key] === "string" && values[key] && values[key] !== state[key]) {
        state[key] = values[key];
        changed = true;
      }
    });
    if (changed) {
      state.page = 1;
      state.showSolution = false;
      loadQuestions();
      dock("题库筛选：" + describeFilters() + "（" + (by === "human" ? "人工" : "同步") + "）");
    }
  }

  function describeFilters() {
    return "年级 " + state.grade + " · 难度 " + state.difficulty + " · 题型 " + state.type +
      (state.topic ? " · 考向「" + state.topicName + "」" : "") +
      (state.search ? " · 关键词「" + state.search + "」" : "");
  }

  /**
   * 军令 #15 任务 3 的落点：AI 只说「去哪、带什么词」，底座把检索词送到这里，
   * 插件改自己的筛选态重查一次。工具栏里的搜索框由 renderAll 从 state.search 回填，
   * 因此这里不伸手碰任何输入框。
   */
  function applyBankQuery(payload) {
    var raw = payload && typeof payload.query === "string" ? payload.query : "";
    var query = raw.trim().slice(0, 100);
    if (!query) {
      dock("宿主送来的题库检索是空的，本视图保持原样。");
      return;
    }
    // 检索词只有列表视图会消费：待审/查重视图下必须先切回列表，
    // 否则 loadQuestions() 白打一次接口、界面还停在原面板，AI 送来的词被静默吞掉。
    if (state.view !== "list") state.view = "list";
    state.search = query;
    state.page = 1;
    state.showSolution = false;
    loadQuestions();
    dock("AI 跳转带来的关键词「" + query + "」已填入搜索框。");
  }

  // ---------- 安全渲染 ----------
  function renderMathToken(text) {
    var span = document.createElement("span");
    var display = text.slice(0, 2) === "$$";
    var body = display ? text.slice(2, -2) : text.slice(1, -1);
    if (window.katex && typeof window.katex.renderToString === "function") {
      try {
        span.innerHTML = window.katex.renderToString(body, {
          displayMode: display,
          throwOnError: false,
          trust: false,
          strict: "ignore"
        });
        span.className = display ? "cb-math-block" : "cb-math";
        return span;
      } catch (error) {
        /* 落到纯文本 */
      }
    }
    span.textContent = text;
    return span;
  }

  function appendInline(target, text) {
    var pattern = /(\$\$[\s\S]*?\$\$|\$[^$\n]*?\$|\*\*[^*]+\*\*)/g;
    var last = 0;
    var match;
    while ((match = pattern.exec(text)) !== null) {
      if (match.index > last) target.appendChild(document.createTextNode(text.slice(last, match.index)));
      var token = match[0];
      if (token.slice(0, 1) === "$") {
        target.appendChild(renderMathToken(token));
      } else {
        var strong = document.createElement("strong");
        strong.textContent = token.slice(2, -2);
        target.appendChild(strong);
      }
      last = pattern.lastIndex;
    }
    if (last < text.length) target.appendChild(document.createTextNode(text.slice(last)));
  }

  function appendRich(target, source, imageMap) {
    var text = String(source == null ? "" : source);
    var blocks = text.split(/\n{2,}/);
    blocks.forEach(function (block) {
      var trimmed = block.trim();
      if (!trimmed) return;
      var image = trimmed.match(/^!\[([^\]]*)\]\((\/static\/uploads\/[^)\s]+)\)$/);
      if (image) {
        var img = document.createElement("img");
        img.className = "cb-img";
        img.src = image[2];
        img.alt = image[1] || "配图";
        img.loading = "lazy";
        target.appendChild(img);
        return;
      }
      var paragraph = document.createElement("p");
      paragraph.style.margin = "0 0 8px";
      appendInline(paragraph, trimmed);
      target.appendChild(paragraph);
      if (imageMap) {
        // 段落中残留的图片语法（迁移后的正文一般已是独立段落，这里兜底）
        Array.prototype.forEach.call(paragraph.querySelectorAll("img"), function (node) {
          if (node.getAttribute("src").indexOf("/static/uploads/") !== 0) node.remove();
        });
      }
    });
  }

  // ---------- 列表 ----------
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  // 契约 2.0 只发 L1–L4；旧键留着只为渲染历史缓存里的题卡
  function difficultyLabel(value) {
    return {
      L1: "基础", L2: "中档", L3: "难", L4: "压轴",
      basic: "基础", medium: "中档", hard: "难", novel: "压轴"
    }[value] || value;
  }

  function typeLabel(value) {
    return {
      single_choice: "单选", multiple_choice: "多选", fill_blank: "填空",
      solution: "解答", proof: "证明", unknown: "待定"
    }[value] || value;
  }

  function sourceLine(question) {
    var source = question.source || {};
    return [source.paper_title, source.question_no ? "原卷 " + source.question_no + " 题" : ""]
      .filter(Boolean).join(" · ");
  }

  function migrationFlags(question) {
    var entry = (question.extensions || {})["org.jiuzhang.core-bank.migration"];
    var flags = entry && entry.flags;
    return Array.isArray(flags) ? flags : [];
  }

  function buildRow(question, index) {
    var row = document.createElement("article");
    row.className = "cb-row";
    row.tabIndex = 0;
    row.setAttribute("role", "button");
    row.setAttribute("aria-current", String(Boolean(state.selected && state.selected.id === question.id)));
    row.setAttribute("data-id", question.id);

    row.appendChild(el("span", "cb-no", String((state.page - 1) * state.pageSize + index + 1)));
    var main = el("div");
    var stem = el("p", "cb-stem");
    appendInline(stem, question.stem.slice(0, 260));
    main.appendChild(stem);
    var meta = el("div", "cb-meta");
    var grade = el("span", "cb-chip", question.grade || "未标注");
    meta.appendChild(grade);
    var difficulty = el("span", "cb-chip", difficultyLabel(question.difficulty));
    difficulty.setAttribute("data-kind", question.difficulty);
    meta.appendChild(difficulty);
    meta.appendChild(el("span", "cb-chip", typeLabel(question.type)));
    var flags = migrationFlags(question);
    if (flags.length) {
      meta.appendChild(el("span", "cb-chip cb-chip-review", "待审 " + flags.length + " 项"));
    }
    if (question.taxonomy && question.taxonomy.chapter) {
      meta.appendChild(el("span", "cb-chip", question.taxonomy.chapter));
    }
    if (question.source && question.source.paper_title) {
      meta.appendChild(el("span", "cb-chip", sourceLine(question)));
    }
    main.appendChild(meta);
    row.appendChild(main);

    var pick = el("button", "cb-btn", basketIds[question.id] ? "已入篮" : "入篮");
    pick.type = "button";
    pick.setAttribute("aria-label", "把第 " + ((state.page - 1) * state.pageSize + index + 1) + " 题加入题篮");
    pick.addEventListener("click", function (event) {
      event.stopPropagation();
      addToBasket([question.id]);
    });
    row.appendChild(pick);

    function select() {
      state.selected = question;
      state.showSolution = false;
      renderAll();
    }
    row.addEventListener("click", select);
    row.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        select();
      }
    });
    return row;
  }

  // 列表视图与待审视图的分页器是同一个形状（上一页—页码—下一页），只差数据源与翻页动作。
  function mountPager(page, pages, total, onGo) {
    var pager = el("div", "cb-pager");
    var prev = el("button", "cb-btn", "上一页");
    prev.type = "button";
    prev.disabled = page <= 1;
    prev.addEventListener("click", function () { if (page > 1) onGo(page - 1); });
    var next = el("button", "cb-btn", "下一页");
    next.type = "button";
    next.disabled = page >= pages;
    next.addEventListener("click", function () { if (page < pages) onGo(page + 1); });
    pager.appendChild(prev);
    pager.appendChild(el("span", null, "第 " + page + " / " + pages + " 页 · 共 " + total + " 题"));
    pager.appendChild(next);
    return pager;
  }

  // 答案口径只有一处真相：选项题报选项键、其余报正文，两者都没有就是「待补」。
  function answerText(question) {
    var answer = question.answer;
    if (answer && answer.kind === "choice") return (answer.choice_keys || []).join("、");
    if (answer && answer.content) return String(answer.content);
    return "";
  }

  // ---------- 大纲树（bank.topics 懒加载） ----------
  function fetchTopics(parentId) {
    var payload = parentId ? { parent_id: parentId } : {};
    return hostCall("bank.topics", payload).then(function (result) {
      return (result && result.items) || [];
    });
  }

  function loadTree() {
    if (tree.loading) return Promise.resolve();
    tree.loading = true;
    tree.error = "";
    renderAll();
    return fetchTopics("")
      .then(function (items) {
        tree.roots = items;
        tree.loading = false;
        renderAll();
      })
      .catch(function (error) {
        // 树坏了不能拖垮题库：列表照常，只在树栏里报错并给出重试
        tree.roots = null;
        tree.children = {};
        tree.loading = false;
        tree.error = error.message;
        renderAll();
      });
  }

  function toggleNode(node) {
    if (tree.expanded[node.id]) {
      tree.expanded[node.id] = false;
      renderAll();
      return;
    }
    tree.expanded[node.id] = true;
    if (tree.children[node.id]) {
      renderAll();
      return;
    }
    fetchTopics(node.id).then(function (items) {
      tree.children[node.id] = items;
      renderAll();
    }).catch(function (error) {
      // 取不到不许伪装成「这一层没有子节点」：那会让老师以为大纲是空的，还查不出为什么。
      // 收回展开态并播报失败原因，节点保持可再点一次重试。
      delete tree.children[node.id];
      tree.expanded[node.id] = false;
      renderAll();
      toast("这一层子节点没取到：" + error.message);
    });
  }

  function selectTopic(node) {
    if (state.topic === node.id) return clearTopic();
    state.topic = node.id;
    state.topicName = node.name;
    state.page = 1;
    state.showSolution = false;
    if (node.has_children && !tree.children[node.id]) toggleNode(node);
    loadQuestions();
    dock("按大纲取题：" + node.name);
    return undefined;
  }

  function clearTopic() {
    state.topic = "";
    state.topicName = "";
    state.page = 1;
    loadQuestions();
  }

  function renderTopicNode(node) {
    var item = el("li", "cb-tree-item");
    item.setAttribute("role", "treeitem");
    item.setAttribute("aria-expanded", String(Boolean(tree.expanded[node.id])));
    item.setAttribute("aria-selected", String(state.topic === node.id));

    var row = el("div", "cb-tree-row");
    if (node.has_children) {
      var caret = el("button", "cb-caret", tree.expanded[node.id] ? "▾" : "▸");
      caret.type = "button";
      caret.setAttribute("aria-label", (tree.expanded[node.id] ? "收起 " : "展开 ") + node.name);
      caret.addEventListener("click", function () { toggleNode(node); });
      row.appendChild(caret);
    } else {
      row.appendChild(el("span", "cb-caret cb-caret-leaf", "·"));
    }

    var pick = el("button", "cb-tree-name" + (state.topic === node.id ? " cb-tree-active" : ""), node.name);
    pick.type = "button";
    pick.setAttribute("data-layer", node.layer || "");
    if (state.topic === node.id) pick.setAttribute("aria-current", "true");
    pick.addEventListener("click", function () { selectTopic(node); });
    row.appendChild(pick);

    row.appendChild(el("span", "cb-tree-count", String(node.question_count || 0)));
    if (node.note_count) row.appendChild(el("span", "cb-tree-notes", "笔记 " + node.note_count));
    if (node.status === "draft") row.appendChild(el("span", "cb-tree-draft", "待补录"));
    item.appendChild(row);

    if (node.has_children && tree.expanded[node.id]) {
      var branch = el("ul", "cb-tree-branch");
      branch.setAttribute("role", "group");
      var kids = tree.children[node.id];
      if (kids && !kids.length) {
        branch.appendChild(el("li", "cb-tree-empty", "这一层还没有子节点"));
      } else if (!kids) {
        branch.appendChild(el("li", "cb-tree-loading", "正在读取…"));
      } else {
        kids.forEach(function (child) { branch.appendChild(renderTopicNode(child)); });
      }
      item.appendChild(branch);
    }
    return item;
  }

  function renderTree(host) {
    var rail = el("aside", "cb-tree");
    rail.setAttribute("aria-label", "考向大纲树");

    var head = el("div", "cb-tree-head");
    head.appendChild(el("h2", "cb-tree-title", "大纲树"));
    var all = el("button", "cb-tree-all" + (state.topic ? "" : " cb-tree-active"), "全部题目");
    all.type = "button";
    all.addEventListener("click", clearTopic);
    head.appendChild(all);
    rail.appendChild(head);

    if (tree.loading && !tree.roots) {
      rail.appendChild(el("p", "cb-tree-loading", "正在读取大纲…"));
    } else if (tree.error) {
      rail.appendChild(el("p", "cb-tree-error", "大纲树读取失败：" + tree.error));
      var retry = el("button", "cb-btn", "重试");
      retry.type = "button";
      retry.addEventListener("click", loadTree);
      rail.appendChild(retry);
    } else if (tree.roots && tree.roots.length) {
      var trunk = el("ul", "cb-tree-branch cb-tree-root");
      trunk.setAttribute("role", "tree");
      tree.roots.forEach(function (node) { trunk.appendChild(renderTopicNode(node)); });
      rail.appendChild(trunk);
    } else {
      rail.appendChild(el("p", "cb-tree-empty", "大纲还是空的：先灌库再回来。"));
    }
    host.appendChild(rail);
  }

  function renderList(host) {
    var list = el("div", "cb-list");
    if (state.loading && !state.items.length) {
      list.appendChild(el("p", "cb-loading", "正在读取题库…"));
    } else if (!state.items.length) {
      list.appendChild(el("p", "cb-empty", "当前筛选下没有题目。试试在右侧面板把年级改成「全部」。"));
    } else {
      state.items.forEach(function (question, index) {
        list.appendChild(buildRow(question, index));
      });
      list.appendChild(mountPager(state.page, Math.max(1, Math.ceil(state.total / state.pageSize)),
        state.total, function (page) { state.page = page; loadQuestions(); }));
    }
    host.appendChild(list);
  }

  // ---------- 详情 ----------
  function renderDetail(host) {
    var side = el("div", "cb-side");
    var question = state.selected;
    if (!question) {
      side.appendChild(el("p", "cb-empty", "从左侧选一道题，这里显示题干、选项与解析。"));
      host.appendChild(side);
      return;
    }

    var detail = el("div", "cb-detail");
    detail.setAttribute("data-question-id", question.id);
    detail.appendChild(el("h2", null, sourceLine(question) || "题目详情"));
    var meta = el("div", "cb-detail-meta");
    meta.textContent = [
      question.grade || "未标注",
      difficultyLabel(question.difficulty),
      typeLabel(question.type),
      question.taxonomy && question.taxonomy.chapter ? question.taxonomy.chapter : "",
      question.id
    ].filter(Boolean).join(" · ");
    detail.appendChild(meta);

    var card = el("div", "cb-question");
    appendRich(card, question.stem);
    if (question.options && question.options.length) {
      var options = el("ol", "cb-options");
      question.options.forEach(function (option) {
        var item = el("li", "cb-option");
        item.appendChild(el("span", "cb-key", option.key + "."));
        var body = el("span");
        appendRich(body, option.content);
        (option.image_ids || []).forEach(function (imageId) {
          var image = (question.images || []).filter(function (candidate) { return candidate.id === imageId; })[0];
          if (image && image.uri) {
            var img = document.createElement("img");
            img.className = "cb-img";
            img.src = image.uri;
            img.alt = image.alt || "选项配图";
            body.appendChild(img);
          }
        });
        item.appendChild(body);
        options.appendChild(item);
      });
      card.appendChild(options);
    }

    if (question.answer) {
      var answer = el("div", "cb-answer");
      answer.appendChild(el("span", "cb-answer-label", "答案："));
      var shown = answerText(question);
      if (shown) answer.appendChild(document.createTextNode(shown));
      card.appendChild(answer);
    } else {
      // 新库里 answer 是 NULL（旧库拿硬编码 A 冒充过 31 道选择题）：如实说待补，不显示空白
      var pending = el("div", "cb-answer cb-answer-pending");
      pending.appendChild(el("span", "cb-answer-label", "答案："));
      pending.appendChild(document.createTextNode("待补 — 这道题在原资料里没有可依据的答案，底座不拿字母冒充"));
      card.appendChild(pending);
      var detailFlags = migrationFlags(question);
      if (detailFlags.length) {
        card.appendChild(el("p", "cb-flags", "迁移标记：" + detailFlags.join(" · ")));
      }
    }

    if (state.showSolution && question.solution) {
      var solution = el("div", "cb-solution");
      solution.appendChild(el("span", "cb-answer-label", "解析："));
      appendRich(solution, question.solution);
      card.appendChild(solution);
    }

    var actions = el("div", "cb-actions");
    var toggle = el("button", "cb-btn", state.showSolution ? "收起解析" : "显示解析");
    toggle.type = "button";
    toggle.disabled = !question.solution;
    toggle.addEventListener("click", function () {
      state.showSolution = !state.showSolution;
      renderAll();
    });
    actions.appendChild(toggle);

    var add = el("button", "cb-btn cb-btn-primary", basketIds[question.id] ? "已在题篮" : "加入题篮");
    add.type = "button";
    add.addEventListener("click", function () { addToBasket([question.id]); });
    actions.appendChild(add);

    var edit = el("button", "cb-btn", "去编辑");
    edit.type = "button";
    edit.addEventListener("click", function () { openEditor(question.id); });
    actions.appendChild(edit);
    card.appendChild(actions);
    detail.appendChild(card);
    side.appendChild(detail);
    host.appendChild(side);
  }

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

  // 向宿主发一个授权事件（三端分离里唯一允许的跨端动作：请求打开录题工作台）
  function publish(event, payload) {
    try {
      window.parent.postMessage({
        protocol: PROTOCOL,
        kind: "notification",
        event: event,
        payload: payload || {}
      }, "*");
    } catch (error) {
      /* 跳转丢了不致命，底栏会没声音而已 */
    }
  }

  function openEditor(questionId) {
    if (!questionId) return;
    publish("system.open_editor", { question_id: questionId });
    dock("已请求打开录题工作台：" + questionId);
  }

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

  function renderAll() {
    if (!stageMode || !root) return;
    root.textContent = "";
    var head = el("header", "cb-head");
    head.appendChild(el("h1", "cb-title", "真题题库"));
    head.appendChild(el("p", "cb-sub", "本地 SQLite · 共 " + state.total + " 题 · 左栏点大纲取题，筛选条件以右侧面板为准"));
    var count = el("span", "cb-count", "题篮 " + Object.keys(basketIds).length);
    count.id = "cbBasketCount";
    head.appendChild(count);
    root.appendChild(head);

    var toolbar = el("div", "cb-toolbar");
    var search = document.createElement("input");
    search.className = "cb-search";
    search.type = "search";
    search.placeholder = "搜索题干关键词（回车确认）";
    search.value = state.search;
    search.setAttribute("aria-label", "搜索题干关键词");
    search.addEventListener("keydown", function (event) {
      if (event.key === "Enter") {
        state.search = search.value.trim().slice(0, 100);
        state.page = 1;
        loadQuestions();
      }
    });
    toolbar.appendChild(search);

    var refresh = el("button", "cb-btn", "刷新");
    refresh.type = "button";
    refresh.disabled = state.loading;
    refresh.setAttribute("aria-busy", String(state.loading));
    // 刷新要刷「正在看的那个视图」：待审与查重视图不消费 state.items，
    // 无脑 loadQuestions() 会让这两个视图下的【刷新】点了像没反应。
    refresh.addEventListener("click", function () {
      loadTree();
      if (state.view === "review") loadReview(state.reviewPage);
      else if (state.view === "dedupe") loadDedupe();
      else loadQuestions();
    });
    toolbar.appendChild(refresh);

    var views = el("div", "cb-views");
    views.setAttribute("role", "tablist");
    views.setAttribute("aria-label", "题库视图");
    var listButton = el("button", "cb-btn" + (state.view === "list" ? " cb-btn-primary" : ""), "题目列表");
    listButton.type = "button";
    listButton.setAttribute("role", "tab");
    listButton.setAttribute("aria-selected", String(state.view === "list"));
    listButton.addEventListener("click", function () {
      if (state.view !== "list") {
        state.view = "list";
        loadQuestions();
      }
    });
    var reviewCount = state.reviewSummary.total;
    var reviewButton = el("button", "cb-btn" + (state.view === "review" ? " cb-btn-primary" : ""),
      "待审任务" + (reviewCount ? " " + reviewCount : ""));
    reviewButton.type = "button";
    reviewButton.setAttribute("role", "tab");
    reviewButton.setAttribute("aria-selected", String(state.view === "review"));
    reviewButton.setAttribute("data-review-tab", "true");
    reviewButton.addEventListener("click", function () { loadReview(1); });
    views.appendChild(listButton);
    views.appendChild(reviewButton);
    var dupeCount = state.view === "dedupe" ? state.dupeQueue.length : state.dupeRedundant;
    var dupeButton = el("button", "cb-btn" + (state.view === "dedupe" ? " cb-btn-primary" : ""),
      "查重清洗" + (dupeCount ? " " + dupeCount : ""));
    dupeButton.type = "button";
    dupeButton.setAttribute("role", "tab");
    dupeButton.setAttribute("aria-selected", String(state.view === "dedupe"));
    dupeButton.setAttribute("data-dupe-tab", "true");
    dupeButton.addEventListener("click", function () { loadDedupe(); });
    views.appendChild(dupeButton);
    toolbar.appendChild(views);

    var hintLabels = { review: "人工审核：修一条清一条", dedupe: "题面指纹相同才算重复：答案与解析各留各的，不强行合并" };
    var hint = el("span", "cb-sub", hintLabels[state.view] || describeFilters());
    hint.setAttribute("data-filter-summary", "true");
    toolbar.appendChild(hint);
    root.appendChild(toolbar);

    var wide = state.view === "review" || state.view === "dedupe";
    var body = el("div", wide ? "cb-body cb-body-review" : "cb-body");
    if (state.view === "review") {
      renderReviewPanel(body);
    } else if (state.view === "dedupe") {
      renderDedupePanel(body);
    } else {
      renderTree(body);
      renderList(body);
      renderDetail(body);
    }
    root.appendChild(body);
  }

  // ---------- 数据 ----------
  function loadQuestions() {
    if (!stageMode) return;
    var token = ++loadToken;
    state.loading = true;
    renderAll();
    var params = {
      grade: state.grade,
      difficulty: state.difficulty,
      type: state.type,
      topic: state.topic,
      q: state.search,
      page: state.page,
      page_size: state.pageSize
    };
    // 视图插件自己没有题库：永远读「当前活跃 provider」的库，不拿页签 id 猜库。
    return hostCall("bank.active_list", params)
      .then(function (result) {
        if (token !== loadToken) return;
        state.items = (result && result.items) || [];
        state.total = (result && result.total) || 0;
        if (state.selected && !state.items.some(function (item) { return item.id === state.selected.id; })) {
          state.selected = null;
        }
        if (!state.selected && state.items.length) state.selected = state.items[0];
        state.loading = false;
        renderAll();
        dock("题库已载入：" + state.total + " 题（" + describeFilters() + "）");
      })
      .catch(function (error) {
        if (token !== loadToken) return;
        state.loading = false;
        state.items = [];
        state.total = 0;
        renderAll();
        toast("读取题库失败：" + error.message);
        dock("读取题库失败：" + error.message);
      });
  }

  var refreshTimer = null;

  function scheduleRefresh() {
    // 宿主对新旧两个事件名各广播一次，这里去重成一次刷新，避免连打两遍接口
    if (state.view === "dedupe") return;
    // 查重队列是本地态：合并后宿主会广播本题更新，此刻重扫会把老师正在比的题抽走
    if (refreshTimer) window.clearTimeout(refreshTimer);
    refreshTimer = window.setTimeout(function () {
      refreshTimer = null;
      if (state.view === "review") loadReview(); else loadQuestions();
    }, 260);
  }

  function loadBasket() {
    return hostCall("basket.list", {})
      .then(function (result) {
        basketIds = Object.create(null);
        ((result && result.items) || []).forEach(function (item) {
          if (item && item.question_id) basketIds[item.question_id] = true;
        });
        renderAll();
      })
      .catch(function () { /* 题篮不可用不影响题库浏览 */ });
  }

  function addToBasket(ids) {
    return hostCall("basket.active_add", { ids: ids })
      .then(function (result) {
        ids.forEach(function (id) { basketIds[id] = true; });
        var total = result && typeof result.total === "number" ? result.total : Object.keys(basketIds).length;
        toast("已加入题篮（共 " + total + " 题）");
        dock("已加入题篮：共 " + total + " 题");
        renderAll();
      })
      .catch(function (error) {
        toast("加入题篮失败：" + error.message);
      });
  }

  function toast(text) {
    var node = root && root.querySelector(".cb-toast");
    if (!node) {
      if (!root) return;
      node = el("div", "cb-toast");
      root.appendChild(node);
    }
    node.textContent = text;
    node.setAttribute("data-show", "true");
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(function () {
      node.setAttribute("data-show", "false");
    }, 2200);
  }

  // ---------- 能力路由字典（军令 #20） ----------
  var FILTER_SETS = {
    grade: ["全部", "高一", "高二", "高三"],
    difficulty: ["全部", "L1", "L2", "L3", "L4"],
    type: ["全部", "single_choice", "multiple_choice", "fill_blank", "solution"]
  };
  var QUESTION_ID_RE = /^q_[A-Za-z0-9_-]{1,78}$/;

  function commandReject(source, message, code, text) {
    respond(source, message.id, false, null, code, text);
  }

  function rejectUnknown(context, allowed) {
    var unknown = Object.keys(context).filter(function (key) {
      return allowed.indexOf(key) < 0;
    });
    return unknown.length ? "不认识的参数：" + unknown.join("、") : "";
  }

  function filterFromContext(context) {
    var result = { ok: true, values: {} };
    var unknown = rejectUnknown(context, ["grade", "difficulty", "type", "search"]);
    if (unknown) {
      result.ok = false;
      result.message = unknown;
      return result;
    }
    Object.keys(FILTER_SETS).forEach(function (key) {
      if (context[key] === undefined) return;
      if (typeof context[key] !== "string" || FILTER_SETS[key].indexOf(context[key]) < 0) {
        result.ok = false;
        result.message = key + " 只接受 " + FILTER_SETS[key].join("/");
        return;
      }
      result.values[key] = context[key];
    });
    if (context.search !== undefined
        && (typeof context.search !== "string" || context.search.length > 100)) {
      result.ok = false;
      result.message = "search 必须是不超过 100 字的字符串";
    }
    return result;
  }

  function handleCommandExecute(source, message) {
    var payload = message.payload || {};
    var commandId = typeof payload.command_id === "string" ? payload.command_id : "";
    var context = payload.context && typeof payload.context === "object" ? payload.context : {};

    if (commandId === "org.jiuzhang.action.view.filter_questions") {
      var parsed = filterFromContext(context);
      if (!parsed.ok) return commandReject(source, message, "BAD_PARAMS", parsed.message);
      Object.keys(parsed.values).forEach(function (key) { state[key] = parsed.values[key]; });
      if (typeof context.search === "string") state.search = context.search.trim().slice(0, 100);
      state.view = "list";
      state.page = 1;
      state.showSolution = false;
      var reload = loadQuestions();
      if (!reload || typeof reload.then !== "function") {
        return commandReject(source, message, "COMMAND_BUSY", "题库正在加载，请稍后再试");
      }
      reload.then(function () {
        respond(source, message.id, true, {
          total: state.total,
          filters: {
            grade: state.grade,
            difficulty: state.difficulty,
            type: state.type,
            search: state.search
          }
        });
      });
      return;
    }

    if (commandId === "org.jiuzhang.action.view.review_queue") {
      var reviewUnknown = rejectUnknown(context, ["flag"]);
      if (reviewUnknown) {
        return commandReject(source, message, "BAD_PARAMS", reviewUnknown);
      }
      if (context.flag !== undefined && (typeof context.flag !== "string" || context.flag.length > 40)) {
        return commandReject(source, message, "BAD_PARAMS", "flag 必须是不超过 40 字的字符串");
      }
      state.reviewFlag = typeof context.flag === "string" ? context.flag.trim() : "";
      var reviewCall = loadReview(1);
      if (!reviewCall || typeof reviewCall.then !== "function") {
        return commandReject(source, message, "COMMAND_BUSY", "待审队列正在加载，请稍后再试");
      }
      reviewCall.then(function () {
        respond(source, message.id, true, {
          total: state.reviewTotal,
          pages: state.reviewPages,
          flag: state.reviewFlag,
          flags: state.reviewSummary.flags || []
        });
      });
      return;
    }

    if (commandId === "org.jiuzhang.action.data.dedupe_scan") {
      if (Object.keys(context).length) {
        return commandReject(source, message, "BAD_PARAMS", "查重扫描不接受参数");
      }
      var scanCall = loadDedupe();
      if (!scanCall || typeof scanCall.then !== "function") {
        return commandReject(source, message, "COMMAND_BUSY", "查重正在运行，请稍后再试");
      }
      scanCall.then(function () {
        respond(source, message.id, true, {
          scanned: state.dupeScanned,
          queued: state.dupeQueue.length,
          redundant: state.dupeRedundant,
          truncated: state.dupeTruncated,
          groups: state.dupeQueue.slice(0, 5).map(function (group) {
            return { ids: (group.ids || []).slice(0, 10) };
          })
        });
      });
      return;
    }

    if (commandId === "org.jiuzhang.action.data.dedupe_merge") {
      var mergeUnknown = rejectUnknown(context, ["primary_id", "copy_ids"]);
      if (mergeUnknown) {
        return commandReject(source, message, "BAD_PARAMS", mergeUnknown);
      }
      var primary = typeof context.primary_id === "string" ? context.primary_id : "";
      var copies = Array.isArray(context.copy_ids) ? context.copy_ids : [];
      var validCopies = copies.filter(function (item) {
        return typeof item === "string" && QUESTION_ID_RE.test(item);
      });
      if (!QUESTION_ID_RE.test(primary) || !validCopies.length || validCopies.length !== copies.length) {
        return commandReject(source, message, "BAD_PARAMS",
          "primary_id 与 copy_ids 必须是合法的题目 id（q_ 开头）");
      }
      if (validCopies.length > 20) {
        return commandReject(source, message, "BAD_PARAMS", "一次最多合并 20 条副本");
      }
      if (validCopies.indexOf(primary) >= 0) {
        return commandReject(source, message, "BAD_PARAMS", "主记录不能同时出现在副本里");
      }
      if (state.dupeBusy) {
        return commandReject(source, message, "COMMAND_BUSY", "上一次合并没有完成，请稍后再试");
      }
      state.dupeBusy = true;
      hostCall("bank.dedupe_merge", { primary_id: primary, copy_ids: validCopies })
        .then(function (result) {
          state.dupeBusy = false;
          state.dupeQueue = state.dupeQueue.filter(function (group) {
            return (group.ids || []).indexOf(primary) < 0;
          });
          state.dupePrimary = "";
          state.dupeMerged += validCopies.length;
          state.dupeScanned = Math.max(0, state.dupeScanned - validCopies.length);
          state.dupeRedundant = Math.max(0, state.dupeRedundant - validCopies.length);
          renderAll();
          respond(source, message.id, true, result || {
            primary_id: primary,
            merged: validCopies,
            removed: validCopies
          });
        }, function (error) {
          state.dupeBusy = false;
          renderAll();
          commandReject(source, message, "COMMAND_FAILED", "合并失败：" + error.message);
        });
      return;
    }

    commandReject(source, message, "UNKNOWN_COMMAND", "未声明的方法：" + commandId);
  }

  // ---------- 协议 ----------
  window.addEventListener("message", function (event) {
    var message = event.data;
    if (!message || message.protocol !== PROTOCOL) return;

    if (message.kind === "response" && pending.has(message.id)) {
      var waiter = pending.get(message.id);
      pending.delete(message.id);
      if (message.ok) waiter.resolve(message.result || {});
      else waiter.reject(new Error((message.error && message.error.message) || "宿主返回失败"));
      return;
    }

    if (message.kind === "notification") {
      if (message.event === "ui.params.changed") {
        var payload = message.payload || {};
        applyParams(payload.values, payload.by);
      }
      if (message.event === "system.question_updated" || message.event === "question.updated") {
        // 回流刷新：录题端改完题宿主广播一声，这里静默重取，不用老师按 F5
        scheduleRefresh();
      }
      if (message.event === "system.bank_query") {
        applyBankQuery(message.payload || {});
      }
      return;
    }

    if (message.kind !== "request") return;
    if (message.method === "plugin.activate") {
      stageMode = true;
      root.hidden = false;
      var values = (message.payload && message.payload.values) || {};
      applyParams(values, "init");
      loadTree();
      loadBasket().then(function () {
        if (!state.selected) loadQuestions();
      });
      return respond(event.source, message.id, true, { ready: true, plugin_id: PLUGIN_ID });
    }
    if (message.method === "plugin.deactivate") {
      root.hidden = true;
      return respond(event.source, message.id, true, { ready: false });
    }
    if (message.method === "question.render") {
      var question = (message.payload && message.payload.question) || {};
      return respond(event.source, message.id, true, {
        html: '<article class="cb-question">' + escapeHtml(question.stem || "") + "</article>",
        height: 120
      });
    }
    if (message.method === "command.execute") {
      return handleCommandExecute(event.source, message);
    }
    respond(event.source, message.id, false, null, "UNSUPPORTED_METHOD", "未实现的方法：" + message.method);
  });

  function escapeHtml(text) {
    return String(text == null ? "" : text)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function respond(target, id, ok, result, code, message) {
    var packet = { protocol: PROTOCOL, id: id, kind: "response", ok: ok };
    if (ok) packet.result = result || {};
    else packet.error = { code: code || "ERROR", message: message || "失败", retryable: false };
    try { target.postMessage(packet, "*"); } catch (error) { /* 宿主已走 */ }
  }

  // 独立打开（无宿主）时给一条明确说明，不假装有数据
  if (window.parent === window && root) {
    root.hidden = false;
    root.appendChild(el("p", "cb-empty", "请从九章算子工作台左侧打开「真题题库」；插件单独打开时拿不到宿主题库。"));
  }
})();
