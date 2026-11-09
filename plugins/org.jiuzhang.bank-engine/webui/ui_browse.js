/**
 * 题面浏览：富文本、列表、大纲树与详情（org.jiuzhang.bank-engine / ui_browse.js）。
 *
 * 从 plugin.js 拆出（PLUGIN_SPEC §2.8.1「单文件不得过 500 行」）：
 * - 安全渲染与通用格式化分别在 ui_rich.js / ui_format.js，本文件只管装配；
 * - 列表：一行一题，标签翻译与迁移标记走通用格式化；
 * - 大纲树：册/章/节/考向按 bank.topics 懒加载，开合与已取回的层记在 tree；
 * - 详情：题干、选项、答案与解析，外加该考向的笔记（军令 #21 任务二）。
 *
 * 数据仍由宿主供给：本模块只经 ctx.hostCall 申请「活跃题库」的题与大纲，
 * 拿不到数据库、文件系统与令牌；改条件与装配视图归 plugin.js。
 */
(function (global) {
  "use strict";

  function create(ctx) {
    var state = ctx.state;
    var hostCall = ctx.hostCall;
    var dock = ctx.dock;
    var toast = ctx.toast;
    var renderAll = ctx.renderAll;
    var loadQuestions = ctx.loadQuestions;
    var openEditor = ctx.openEditor;
    var addToBasket = ctx.addToBasket;
    var inBasket = ctx.inBasket;

    // 大纲树：册/章/节/考向按需懒加载，expanded 记开合，children 记已取回的一层
    var tree = { roots: null, children: {}, expanded: {}, loading: false, error: "" };

    // 考向笔记：点大纲节点就把该考向的方法/易错点取到右栏。
    // 只留当前节点的结果；老师连点两个节点时用 seq 丢掉先发后到的旧响应。
    var notes = { topicId: "", loading: false, items: [], error: "", seq: 0 };

    var rich = window.JzoBankRich.create();
    var appendRich = rich.appendRich;

    // ---------- 列表 ----------
    var fmt = window.JzoBankFormat.create();
    var el = fmt.el;
    var difficultyLabel = fmt.difficultyLabel;
    var typeLabel = fmt.typeLabel;
    var sourceLine = fmt.sourceLine;
    var migrationFlags = fmt.migrationFlags;
    var mountPager = fmt.mountPager;
    var answerText = fmt.answerText;

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

      var pick = el("button", "cb-btn", inBasket(question.id) ? "已入篮" : "入篮");
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
      loadTopicNotes(node.id);
      dock("按大纲取题：" + node.name);
      return undefined;
    }

    function clearTopic() {
      state.topic = "";
      state.topicName = "";
      state.page = 1;
      notes.seq += 1;
      notes.topicId = "";
      notes.items = [];
      notes.error = "";
      notes.loading = false;
      loadQuestions();
    }

    function loadTopicNotes(topicId) {
      var token = ++notes.seq;
      notes.topicId = topicId;
      notes.loading = true;
      notes.items = [];
      notes.error = "";
      renderAll();
      hostCall("bank.topic_notes", { topic_id: topicId }).then(function (result) {
        if (token !== notes.seq) return;
        notes.loading = false;
        notes.items = (result && result.notes) || [];
        renderAll();
      }).catch(function (error) {
        if (token !== notes.seq) return;
        // 取不到就如实报错并留重试，不拿「还没有笔记」冒充
        notes.loading = false;
        notes.error = error.message;
        renderAll();
      });
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
    var NOTE_LABELS = { method: "方法", pitfall: "易错点", knowledge: "知识点", insight: "洞察" };

    function renderTopicNotes(host) {
      if (!state.topic) return;
      var section = el("section", "cb-notes");
      section.setAttribute("data-topic-id", state.topic);
      section.setAttribute("aria-label", "考向教研笔记：" + state.topicName);

      var head = el("div", "cb-notes-head");
      head.appendChild(el("h2", "cb-notes-title", "教研笔记"));
      head.appendChild(el("span", "cb-notes-topic", state.topicName));
      if (!notes.loading && !notes.error) {
        head.appendChild(el("span", "cb-notes-count", notes.items.length + " 条"));
      }
      section.appendChild(head);

      if (notes.loading) {
        section.appendChild(el("p", "cb-notes-hint", "正在读取笔记…"));
      } else if (notes.error) {
        section.appendChild(el("p", "cb-notes-error", "笔记没取到：" + notes.error));
        var retry = el("button", "cb-btn", "重试");
        retry.type = "button";
        retry.addEventListener("click", function () { loadTopicNotes(state.topic); });
        section.appendChild(retry);
      } else if (!notes.items.length) {
        section.appendChild(el("p", "cb-notes-hint", "这个考向还没有教研笔记。"));
      } else {
        notes.items.forEach(function (note) {
          var item = el("article", "cb-note");
          item.setAttribute("data-note-type", note.note_type || "");
          item.appendChild(el("span", "cb-note-type",
            NOTE_LABELS[note.note_type] || note.note_type || "笔记"));
          var body = el("div", "cb-note-body");
          appendRich(body, note.content);
          item.appendChild(body);
          section.appendChild(item);
        });
      }
      host.appendChild(section);
    }

    function renderDetail(host) {
      var side = el("div", "cb-side");
      renderTopicNotes(side);
      var question = state.selected;
      if (!question) {
        side.appendChild(el("p", "cb-empty" + (state.topic ? " cb-empty-slim" : ""),
          state.topic ? "这个考向下还没有选题；从中间列表点一道看题干与解析。"
            : "从左侧选一道题，这里显示题干、选项与解析。"));
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

      var add = el("button", "cb-btn cb-btn-primary", inBasket(question.id) ? "已在题篮" : "加入题篮");
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

    return {
      el: el,
      appendRich: appendRich,
      answerText: answerText,
      difficultyLabel: difficultyLabel,
      typeLabel: typeLabel,
      sourceLine: sourceLine,
      migrationFlags: migrationFlags,
      mountPager: mountPager,
      loadTree: loadTree,
      renderTree: renderTree,
      renderList: renderList,
      renderDetail: renderDetail
    };
  }

  global.JzoBankBrowse = { create: create };
})(window);
