/**
 * 幽灵胶囊与标签 / 考向胶囊串（军令 #29 / #30）。
 *
 * 胶囊串的尾巴永远挂着一颗虚线空壳「+ 请添加…」；鼠标停在上面 150ms，
 * 它自己活过来变成实心胶囊并接上光标；打字弹出候选（考向带路径），
 * 回车取第一条上屏，随即长出下一颗空壳；鼠标移出，空壳只是睡回去，不消失。
 *
 * 空壳的「活没活过来」「候选是哪几条」「高亮在第几条」都记在 JzoReactive 的
 * 响应式状态里，DOM 只由渲染函数按状态画——事件处理器不再自己伸手改 DOM。
 */
(function (global) {
  "use strict";

  var GHOST_TEXT = "+ 请添加…";
  // 宿主每 10 秒最多放 80 个请求：候选条数、搜索节奏、路径解析都得有节制。
  var GHOST_TOPIC_LIMIT = 8;
  var GHOST_SEARCH_DELAY_MS = 180;

  function create(ctx) {
    var ui = global.JzoReactive.reactive({
      tag: { state: "idle", items: [], active: -1 },
      topic: { state: "idle", items: [], active: -1 }
    });
    var GHOST_DELAY_MS = ctx.delay || 150;
    // 幽灵胶囊的 DOM 与计时器（不是数据，不进响应式状态）。
    var ghostState = { tag: null, topic: null };

    function ghostHost(kind) {
      return kind === "topic" ? ctx.mountedList : ctx.tagList;
    }

    function ghostMenu(kind) {
      return kind === "topic" ? ctx.topicMenu : ctx.tagMenu;
    }

    function ensureGhost(kind) {
      var host = ghostHost(kind);
      if (!host) return null;
      var rec = ghostState[kind];
      if (rec && rec.ghost && rec.ghost.parentNode === host) return rec;
      var ghost = ctx.el("span", "ep-ghost");
      ghost.setAttribute("data-kind", kind);
      ghost.setAttribute("data-state", "idle");
      var input = document.createElement("input");
      input.className = "ep-ghost-input";
      input.type = "text";
      input.maxLength = 24;
      input.autocomplete = "off";
      input.setAttribute("aria-label", kind === "topic" ? "搜索并挂载考向" : "搜索并添加标签");
      input.setAttribute("placeholder", "打字搜索");
      input.addEventListener("input", function () { onGhostInput(kind); });
      input.addEventListener("keydown", function (event) { onGhostKey(kind, event); });
      input.addEventListener("blur", function () {
        window.setTimeout(function () { closeGhostMenu(kind); }, 150);
      });
      ghost.appendChild(ctx.el("span", "ep-ghost-text", GHOST_TEXT));
      ghost.appendChild(input);
      ghost.addEventListener("mouseenter", function () { armGhost(kind); });
      ghost.addEventListener("mouseleave", function () { disarmGhost(kind); });
      rec = { ghost: ghost, input: input, timer: 0, searchTimer: 0 };
      ghostState[kind] = rec;
      ui[kind].state = "idle";
      host.appendChild(ghost);
      return rec;
    }

    /** 清掉胶囊串里的旧胶囊，但留住尾巴上那颗幽灵空壳——重建它会把光标弄丢。 */
    function chipRow(kind) {
      var host = ghostHost(kind);
      if (!host) return null;
      var rec = ghostState[kind];
      var ghost = rec ? rec.ghost : null;
      Array.prototype.slice.call(host.children).forEach(function (node) {
        if (node !== ghost) host.removeChild(node);
      });
      return ensureGhost(kind);
    }

    /** 胶囊插在幽灵空壳前面：空壳必须留在最后一位，而且不能被搬动——搬一下光标就没了。 */
    function insertChip(host, chip, rec) {
      var ghost = rec ? rec.ghost : null;
      if (ghost && ghost.parentNode === host) host.insertBefore(chip, ghost);
      else host.appendChild(chip);
    }

    function armGhost(kind) {
      var rec = ghostState[kind];
      if (!rec) return;
      if (ui[kind].state === "active") return;
      window.clearTimeout(rec.timer);
      rec.timer = window.setTimeout(function () { activateGhost(kind); }, GHOST_DELAY_MS);
    }

    function disarmGhost(kind) {
      var rec = ghostState[kind];
      if (!rec) return;
      window.clearTimeout(rec.timer);
      rec.timer = 0;
    }

    function activateGhost(kind) {
      var rec = ghostState[kind];
      if (!rec) return;
      ui[kind].state = "active";
      if (!rec.input) return;
      // 状态先由响应式引擎落到 DOM，再逼一次布局接光标：此刻输入框可能还是 display:none，
      // 提前 focus 会静默失败。
      global.JzoReactive.nextTick(function () {
        var current = ghostState[kind];
        if (!current || !current.input || ui[kind].state !== "active") return;
        void current.input.offsetWidth;
        try { global.focus(); } catch (error) { /* 抢不到焦点就算了，光标照样能闪 */ }
        current.input.focus();
      });
    }

    /** 鼠标移出输入区：只把空壳放回「睡着」的虚线态；写了字的留着，别把老师打了一半的话弄丢。 */
    function onGhostLeave(kind) {
      var rec = ghostState[kind];
      if (!rec) return;
      disarmGhost(kind);
      window.clearTimeout(rec.searchTimer);
      rec.searchTimer = 0;
      var typed = rec.input ? String(rec.input.value || "").trim() : "";
      if (typed) return;
      // 空胶囊是「这里点一下就能输入」的唯一提示，鼠标移开也不许消失。
      ui[kind].state = "idle";
      closeGhostMenu(kind);
    }

    function wireGhostCell(kind) {
      var host = ghostHost(kind);
      if (!host) return;
      var cell = host.parentNode;
      if (!cell || !cell.classList || !cell.classList.contains("ep-cell")) return;
      cell.addEventListener("mouseenter", function () {
        ensureGhost(kind);
      });
      cell.addEventListener("mouseleave", function () { onGhostLeave(kind); });
    }

    function onGhostInput(kind) {
      var rec = ghostState[kind];
      if (!rec) return;
      var query = rec.input ? String(rec.input.value || "").trim() : "";
      if (!query) { closeGhostMenu(kind); return; }
      // 每敲一个字就发一次请求，几十个字就能把宿主的限流闸门顶开：等手停下来再查。
      window.clearTimeout(rec.searchTimer);
      rec.searchTimer = window.setTimeout(function () {
        if (kind === "topic") searchGhostTopics(query);
        else searchGhostTags(query);
      }, GHOST_SEARCH_DELAY_MS);
    }

    function onGhostKey(kind, event) {
      var rec = ghostState[kind];
      if (!rec) return;
      var key = String(event.key || "");
      if (key === "Enter") {
        event.preventDefault();
        if (ui[kind].items.length) {
          pickGhostItem(kind, ui[kind].active >= 0 ? ui[kind].active : 0);
          return;
        }
        var typed = rec.input ? String(rec.input.value || "").trim() : "";
        if (!typed) return;
        // 考向只能从大纲树里取：凭空造一个节点等于在题库里造假考向。
        if (kind === "topic") return;
        closeGhostMenu(kind);
        resetGhost(kind);
        ctx.commitTags(ctx.splitTags(ctx.tagsValue()).concat([typed]));
        return;
      }
      if (key === "Escape") {
        event.preventDefault();
        if (rec.input) rec.input.value = "";
        closeGhostMenu(kind);
        ui[kind].state = "idle";
        return;
      }
      if (key === "ArrowDown" || key === "ArrowUp") {
        if (!ui[kind].items.length) return;
        event.preventDefault();
        var step = key === "ArrowDown" ? 1 : -1;
        var count = ui[kind].items.length;
        ui[kind].active = (ui[kind].active + step + count) % count;
        return;
      }
      if (key === "Backspace" && rec.input && !rec.input.value && kind === "tag") {
        var list = ctx.splitTags(ctx.tagsValue());
        if (!list.length) return;
        list.pop();
        ctx.commitTags(list);
      }
    }

    /** 落定一颗，下一颗空壳立刻接上：老师可以连着挂好几个，中间不必再点一次。 */
    function resetGhost(kind) {
      var rec = ghostState[kind];
      if (!rec) return;
      if (rec.input) rec.input.value = "";
      ui[kind].state = "active";
      if (rec.input) rec.input.focus();
    }

    function pickGhostItem(kind, index) {
      var item = ui[kind].items[index];
      if (!item) return;
      closeGhostMenu(kind);
      resetGhost(kind);
      if (kind === "topic") {
        var node = item.value;
        ctx.toggleTopic({ id: node.id, name: node.name });
        return;
      }
      ctx.commitTags(ctx.splitTags(ctx.tagsValue()).concat([item.name]));
    }

    function showGhostMenu(kind, items) {
      ui[kind].items = items || [];
      ui[kind].active = ui[kind].items.length ? 0 : -1;
    }

    /** 候选菜单的签名：内容没变就不重建按钮，免得老师鼠标停在候选上时被换掉。 */
    var menuSign = { tag: "", topic: "" };

    function renderGhostMenu(kind) {
      var menu = ghostMenu(kind);
      if (!menu) return;
      var items = ui[kind].items || [];
      var sign = items.map(function (item) {
        return [item.name, item.path || "", item.hint || ""].join("\u0001");
      }).join("\u0002") + "\u0003" + ui[kind].active;
      if (sign === menuSign[kind]) return;
      menuSign[kind] = sign;
      menu.textContent = "";
      items.forEach(function (item, index) {
        var node = ctx.el("button", "ep-menu-item");
        node.type = "button";
        node.setAttribute("role", "option");
        node.setAttribute("data-index", String(index));
        if (index === ui[kind].active) node.setAttribute("data-active", "true");
        node.appendChild(ctx.el("span", "ep-menu-text", item.name));
        var tail = item.path || item.hint || "";
        if (tail) node.appendChild(ctx.el("span", "ep-menu-path", tail));
        node.addEventListener("mousedown", function (event) {
          // mousedown 而不是 click：input 一失焦菜单就没了，click 永远等不到。
          event.preventDefault();
          pickGhostItem(kind, index);
        });
        menu.appendChild(node);
      });
      menu.hidden = !menu.children.length;
    }

    function closeGhostMenu(kind) {
      var menu = ghostMenu(kind);
      if (menu) menu.hidden = true;
      menuSign[kind] = "";
      ui[kind].items = [];
      ui[kind].active = -1;
    }

    /** 状态 → DOM：空壳的活/睡、显示/隐藏、候选菜单，全由这一处画。 */
    global.JzoReactive.watch(function () {
      ["tag", "topic"].forEach(function (kind) {
        var rec = ghostState[kind];
        if (!rec || !rec.ghost) return;
        rec.ghost.setAttribute("data-state", ui[kind].state);
        renderGhostMenu(kind);
      });
    });

    function searchGhostTags(query) {
      var wire = ghostState.tag;
      var seq = wire ? (wire.seq || 0) + 1 : 1;
      if (wire) wire.seq = seq;
      ctx.hostCall("meta.tags", { scene: ctx.scene(), q: query, limit: 8 }).then(function (result) {
        if (!ghostState.tag || ghostState.tag.seq !== seq) return;
        var rows = (result && Array.isArray(result.tags)) ? result.tags : [];
        showGhostMenu("tag", rows.map(function (tag) {
          return {
            name: String(tag.name || ""),
            hint: tag.scene_weight ? "本场景常用" : "",
            value: String(tag.name || "")
          };
        }));
      }, function () { closeGhostMenu("tag"); });
    }

    function searchGhostTopics(query) {
      var wire = ghostState.topic;
      var seq = wire ? (wire.seq || 0) + 1 : 1;
      if (wire) wire.seq = seq;
      ctx.hostCall("bank.topics", { q: query }).then(function (result) {
        if (!ghostState.topic || ghostState.topic.seq !== seq) return;
        var rows = (result && Array.isArray(result.items)) ? result.items : [];
        // 候选条数要有上限：底下是全库大纲，一口气铺满会把菜单撑爆。
        var items = rows.slice(0, GHOST_TOPIC_LIMIT).map(function (node) {
          return { name: String(node.name || ""), path: "", hint: "", value: node };
        });
        showGhostMenu("topic", items);
        // 路径里祖先的名字要现查：bank.topics 给的是一串 id，不给人看的名字。
        items.forEach(function (item, index) {
          resolveTopicPath(item.value && item.value.path, item.name).then(function (text) {
            if (!ghostState.topic || !ui.topic.items[index]) return;
            ui.topic.items[index].path = text;
          });
        });
      }, function () { closeGhostMenu("topic"); });
    }

    /** 问一层子节点，把这层所有 id → 名字收进缓存。
     *  同一层只问一次，并发的解析共用同一个在途请求。 */
    function fetchTopicChildren(parentId) {
      var store = ctx.topicStore;
      var key = String(parentId || "");
      if (store.topicChildren[key]) return Promise.resolve(store.topicChildren[key]);
      if (store.topicPending[key]) return store.topicPending[key];
      var request = ctx.hostCall("bank.topics", key ? { parent_id: key } : {}).then(function (result) {
        var items = (result && Array.isArray(result.items)) ? result.items : [];
        var names = {};
        items.forEach(function (node) {
          names[node.id] = node.name;
          store.topicNames[node.id] = node.name;
        });
        store.topicChildren[key] = names;
        delete store.topicPending[key];
        return names;
      }, function () {
        delete store.topicPending[key];
        return {};
      });
      store.topicPending[key] = request;
      return request;
    }

    /** bank.topics 的 path 是 id 链：逐级把祖先的名字问出来，拼成给人看的「册 › 章 › 考向」。
     *  叶子自己的名字搜索时就知道了，不必再为它多问一趟。 */
    function resolveTopicPath(path, leafName) {
      var chain = String(path || "").split("/").filter(Boolean);
      if (!chain.length) return Promise.resolve("");
      var store = ctx.topicStore;
      var step = function (index) {
        if (index >= chain.length - 1) return Promise.resolve();
        if (store.topicNames[chain[index]]) return step(index + 1);
        var parentId = index === 0 ? "" : chain[index - 1];
        return fetchTopicChildren(parentId).then(function () { return step(index + 1); });
      };
      return step(0).then(function () {
        return chain.map(function (id, index) {
          if (index === chain.length - 1 && leafName) return leafName;
          return store.topicNames[id] || "";
        }).filter(Boolean).join(" › ");
      });
    }

    /** 标签胶囊：#epTags 只当「逗号串」的存档位，界面上的真身是这一串小胶囊。 */
    function renderTags() {
      if (!ctx.tagList) return;
      var fresh = chipRow("tag");
      var tags = ctx.splitTags(ctx.tagsValue());
      tags.forEach(function (tag) {
        var chip = ctx.el("span", "ep-chip");
        chip.setAttribute("role", "listitem");
        chip.setAttribute("data-tag", tag);
        chip.appendChild(ctx.el("span", "ep-chip-name", tag));
        var removeBtn = ctx.el("button", "ep-chip-x", "×");
        removeBtn.type = "button";
        removeBtn.setAttribute("aria-label", "摘除标签 " + tag);
        removeBtn.addEventListener("click", function () {
          ctx.commitTags(ctx.splitTags(ctx.tagsValue()).filter(function (one) { return one !== tag; }));
        });
        chip.appendChild(removeBtn);
        insertChip(ctx.tagList, chip, fresh);
      });
    }

    function renderMounted() {
      if (!ctx.mountedList) return;
      var entry = ctx.entry() || {};
      var ids = entry.topic_ids || [];
      var names = entry.topic_names || {};
      var fresh = chipRow("topic");
      // 一道没挂时不写提示话：尾巴上那颗虚线幽灵胶囊本身就是「点一下就能输入」。
      ids.forEach(function (id) {
        var chip = ctx.el("span", "ep-chip");
        chip.setAttribute("data-topic", id);
        chip.appendChild(ctx.el("span", "ep-chip-name", names[id] || id));
        var removeBtn = ctx.el("button", "ep-chip-x", "摘");
        removeBtn.type = "button";
        removeBtn.setAttribute("aria-label", "摘除考向 " + (names[id] || id));
        removeBtn.addEventListener("click", function () {
          ctx.toggleTopic({ id: id, name: names[id] || id });
        });
        chip.appendChild(removeBtn);
        insertChip(ctx.mountedList, chip, fresh);
      });
    }

    return {
      state: ui,
      renderTags: renderTags,
      renderMounted: renderMounted,
      wireCell: wireGhostCell,
      closeMenus: function () { closeGhostMenu("tag"); closeGhostMenu("topic"); }
    };
  }

  global.JzoEditorCapsule = { create: create, text: GHOST_TEXT };
})(window);
