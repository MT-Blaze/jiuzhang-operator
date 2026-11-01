/**
 * stage_tabbar.js —— stage.js 的「页签栏」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：底座 JS 单文件不超 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var TAB_GROUP_MIN = deps.TAB_GROUP_MIN;
    var TAB_OVERFLOW = deps.TAB_OVERFLOW;
    var UNGROUPED_KEY = deps.UNGROUPED_KEY;
    var dock = deps.dock;
    var liveFrames = deps.liveFrames;
    var notify = deps.notify;
    var orderPluginTabs = deps.orderPluginTabs;
    var stageState = deps.stageState;
    var tabsEl = deps.tabsEl;

  // ---------- 页签栏：分组合并、溢出横滚、沉浸全屏与浅休眠（军令 #16 模块三） ----------

  /** 分组归属只认清单里的 folder_id（后端从偏好树反查）；没进组的共用「未分组」。 */
  function groupKeyOf(tab) {
    var folder = String((tab.plugin && tab.plugin.folder_id) || "");
    return folder || UNGROUPED_KEY;
  }

  function groupTitle(key) {
    if (key === UNGROUPED_KEY) return "未分组";
    for (var i = 0; i < stageState.groupTree.length; i += 1) {
      var node = stageState.groupTree[i];
      if (node && node.kind === "folder" && node.id === key) {
        return String(node.name || "未命名文件夹");
      }
    }
    return "分组";
  }

  /** 左栏那棵树是分组名的唯一来源：workspace 每拉到一次清单、每改一次树都同步过来。 */
  function setSidebarTree(tree) {
    stageState.groupTree = Array.isArray(tree) ? tree : [];
    Object.keys(stageState.holders).forEach(function (key) {
      var label = stageState.holders[key].btn.querySelector(".ws-tab-label");
      if (label) label.textContent = groupTitle(key);
    });
    orderPluginTabs();
  }

  function groupHolder(key) {
    var holder = stageState.holders[key];
    if (holder) return holder;
    var chip = document.createElement("div");
    chip.className = "ws-tab-group";
    chip.setAttribute("data-group", key);
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "ws-tab ws-tab-group-chip";
    btn.setAttribute("aria-expanded", "false");
    var label = document.createElement("span");
    label.className = "ws-tab-label";
    label.textContent = groupTitle(key);
    var count = document.createElement("span");
    count.className = "ws-tab-count";
    count.setAttribute("aria-hidden", "true");
    var caret = document.createElement("span");
    caret.className = "ws-tab-caret";
    caret.setAttribute("aria-hidden", "true");
    caret.textContent = "\u25be";
    btn.appendChild(label);
    btn.appendChild(count);
    btn.appendChild(caret);
    var list = document.createElement("div");
    list.className = "ws-tab-group-list";
    list.setAttribute("role", "group");
    // 下拉里点开一页时要凭这张列表反查它属于哪一组，所以组 key 也得落在列表上
    list.setAttribute("data-group", key);
    list.hidden = true;
    btn.addEventListener("click", function () { toggleGroup(key); });
    chip.appendChild(btn);
    chip.appendChild(list);
    holder = { chip: chip, btn: btn, list: list, count: count, label: label };
    stageState.holders[key] = holder;
    return holder;
  }

  function collapse(key) {
    var holder = stageState.holders[key];
    if (!holder) return;
    holder.list.hidden = true;
    holder.btn.setAttribute("aria-expanded", "false");
    holder.btn.setAttribute("aria-haspopup", "false");
    if (stageState.expandedKey === key) stageState.expandedKey = "";
  }

  /** 军令逐字「单击下拉展开子 Tab」：点组名就摊开，同一时刻只摊开一个。 */
  function toggleGroup(key) {
    var holder = stageState.holders[key];
    if (!holder) return;
    if (stageState.expandedKey === key) {
      collapse(key);
      return;
    }
    Object.keys(stageState.holders).forEach(function (other) { collapse(other); });
    stageState.expandedKey = key;
    placeGroupList(holder);
    holder.list.hidden = false;
    holder.btn.setAttribute("aria-expanded", "true");
    holder.btn.setAttribute("aria-haspopup", "true");
    var first = holder.list.querySelector(".ws-tab");
    if (first && typeof first.focus === "function") first.focus();
  }

  /**
   * 下拉用 fixed 定位挂在页签栏外面：`#wsTabs` 为了横滚必须裁剪溢出，
   * 子页签列表跟着被裁掉就等于「点开看不见」；fixed 相对视口，不受那层裁剪管。
   */
  function placeGroupList(holder) {
    var rect = holder.btn.getBoundingClientRect();
    var width = Math.max(180, Math.min(280, rect.width + 60));
    var left = Math.max(8, Math.min(rect.left, window.innerWidth - width - 8));
    holder.list.style.left = Math.round(left) + "px";
    holder.list.style.top = Math.round(rect.bottom + 4) + "px";
    holder.list.style.width = Math.round(width) + "px";
    holder.list.style.maxHeight = Math.max(120, window.innerHeight - rect.bottom - 16) + "px";
  }

  // 摊开的下拉是「临时态」：点别处就收，不许一直盖着页签栏
  document.addEventListener("click", function (event) {
    if (!stageState.expandedKey) return;
    var holder = stageState.holders[stageState.expandedKey];
    if (holder && event.target && holder.chip.contains(event.target)) return;
    collapse(stageState.expandedKey);
  });

  /** 从下拉里点开一页就收摊：菜单一直盖着页签栏，后面的页签一个都点不到。 */
  function dismissGroup(tab) {
    var parent = tab && tab.button ? tab.button.parentNode : null;
    if (!parent || !parent.classList || !parent.classList.contains("ws-tab-group-list")) return;
    collapse(parent.getAttribute("data-group") || "");
  }

  function slideTabs(step) {
    if (!tabsEl) return;
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (typeof tabsEl.scrollBy === "function") {
      tabsEl.scrollBy({ left: step * 140, behavior: reduce ? "auto" : "smooth" });
    } else {
      tabsEl.scrollLeft += step * 140;
    }
  }

  function ensureScrollButtons() {
    if (stageState.scrollBtns || !tabsEl || !tabsEl.parentNode) return;
    var wrap = tabsEl.parentNode;

    function make(dir, text, aria) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "ws-tab-scroll-btn";
      button.textContent = text;
      button.setAttribute("aria-label", aria);
      button.addEventListener("click", function () { slideTabs(dir); });
      return button;
    }

    var left = make(-1, "\u2039", "页签栏向左滚");
    var right = make(1, "\u203a", "页签栏向右滚");
    wrap.insertBefore(left, tabsEl);
    wrap.appendChild(right);
    tabsEl.addEventListener("wheel", function (event) {
      // 只在真的横滚得动时接管滚轮，否则不许抢纵向滚动的地盘
      if (!stageState.scrollBtns || stageState.scrollBtns.right.hidden) return;
      var delta = Math.abs(event.deltaY) > Math.abs(event.deltaX) ? event.deltaY : event.deltaX;
      if (!delta) return;
      event.preventDefault();
      tabsEl.scrollLeft += delta;
    }, { passive: false });
    tabsEl.addEventListener("scroll", function () { paintOverflowBar(); });
    window.addEventListener("resize", function () { paintOverflowBar(); });
    stageState.scrollBtns = { left: left, right: right };
  }

  /** 溢出（军令逐字「超过 10 个 Tab」）：固定 120px + 滚轮 + 左右小箭头，三样一起上。 */
  function paintOverflowBar(many) {
    var page = document.querySelector(".ws-page");
    if (!page || !tabsEl) return;
    // scroll/resize 那两条回调是不带参数进来的：这里必须自己把页签数回来。
    // 照原样读 undefined 会把「挤爆态」的类一滚就摘掉，箭头跟着消失，
    // 结果是滚到一半再也滚不动——正是老师最烦的半截子交互。
    var isMany = typeof many === "boolean"
      ? many
      : stageState.tabs.filter(function (tab) { return tab.kind === "plugin"; }).length > TAB_OVERFLOW;
    if (isMany) page.classList.add("ws-tabs-many");
    else page.classList.remove("ws-tabs-many");
    ensureScrollButtons();
    if (!stageState.scrollBtns) return;
    var needs = isMany && tabsEl.scrollWidth > tabsEl.clientWidth + 1;
    stageState.scrollBtns.left.hidden = !needs;
    stageState.scrollBtns.right.hidden = !needs;
  }

  /**
   * 重排页签栏。没挤爆时逐个平铺（老师习惯了一插件一页）；挤爆了才合并：
   * 同组（同一文件夹，或都没进组）凑满 TAB_GROUP_MIN 页收成「分组名页签」，单击摊开子页签。
   */
  function renderTabBar(orderedPluginTabs, many) {
    if (!tabsEl) return;
    var buckets = [];
    var byKey = {};
    orderedPluginTabs.forEach(function (tab) {
      if (!tab.button) return;
      var key = many ? groupKeyOf(tab) : "";
      if (!byKey[key]) {
        byKey[key] = { key: key, members: [] };
        buckets.push(byKey[key]);
      }
      byKey[key].members.push(tab);
    });
    stageState.tabs.forEach(function (tab) {
      if (tab.kind === "plugin" || !tab.button) return;
      if (tab.button.parentNode !== tabsEl) tabsEl.appendChild(tab.button);
    });
    var alive = {};
    buckets.forEach(function (bucket) {
      if (!many || bucket.members.length < TAB_GROUP_MIN) {
        bucket.members.forEach(function (tab) {
          if (tab.button.parentNode !== tabsEl) tabsEl.appendChild(tab.button);
          tab.button.classList.remove("ws-tab-in-group");
        });
        return;
      }
      var holder = groupHolder(bucket.key);
      alive[bucket.key] = true;
      holder.count.textContent = String(bucket.members.length);
      if (holder.chip.parentNode !== tabsEl) tabsEl.appendChild(holder.chip);
      bucket.members.forEach(function (tab) {
        if (tab.button.parentNode !== holder.list) holder.list.appendChild(tab.button);
        tab.button.classList.add("ws-tab-in-group");
      });
    });
    Object.keys(stageState.holders).forEach(function (key) {
      if (alive[key]) return;
      var holder = stageState.holders[key];
      if (holder.chip.parentNode) holder.chip.parentNode.removeChild(holder.chip);
      delete stageState.holders[key];
    });
    Object.keys(stageState.holders).forEach(function (key) {
      if (key !== stageState.expandedKey) collapse(key);
    });
    paintGroupStates();
  }

  /** 切页后只补涂组页签的「当前在这一组」标记，不重排 DOM（重排会打断焦点）。 */
  function paintGroupStates() {
    Object.keys(stageState.holders).forEach(function (key) {
      var holder = stageState.holders[key];
      var members = stageState.tabs.filter(function (tab) {
        return tab.kind === "plugin" && groupKeyOf(tab) === key;
      });
      var current = members.filter(function (tab) { return tab.key === stageState.activeKey; })[0];
      holder.btn.classList.toggle("is-active", Boolean(current));
      holder.btn.title = current
        ? "组：" + groupTitle(key) + "（当前页：" + current.title + "）"
        : "组：" + groupTitle(key);
    });
  }

  /**
   * 双击任意页签 = 沉浸全屏：真全屏让浏览器地址栏退场，左栏随之收起，
   * 右栏与输出日志照旧在场（老师要的是「这一页独占」，不是「只剩这一页」）。
   * 退出走同一次双击或浏览器原生的 Esc。
   */
  function toggleImmersive(key) {
    if (stageState.immersiveKey === key) {
      setImmersive(false, "");
      return;
    }
    setImmersive(true, key);
    dock("沉浸全屏：左栏已收起、浏览器地址栏退场；右栏与输出日志照旧。"
      + "再双击该页签或按 Esc 退出。", "stage.immersive");
  }

  function setImmersive(on, key) {
    stageState.immersiveKey = on ? key : "";
    var page = document.querySelector(".ws-page");
    if (page) {
      // 覆盖层呼入位每次进沉浸都擦干净：上一回按 Ctrl+B 唤出来的浮层，
      // 不该在下一张卷子独占屏幕时自己冒回来。
      page.removeAttribute("data-immersive-rail");
      if (on) page.setAttribute("data-immersive", "on");
      else page.removeAttribute("data-immersive");
    }
    var root = document.documentElement;
    if (on && !document.fullscreenElement && typeof root.requestFullscreen === "function") {
      try {
        var asking = root.requestFullscreen();
        if (asking && typeof asking.catch === "function") asking.catch(function () {});
      } catch (error) {
        // 浏览器不给真全屏（无手势、被策略拦）时，CSS 沉浸照旧生效，不为此打断操作
      }
    } else if (!on && document.fullscreenElement && typeof document.exitFullscreen === "function") {
      try {
        var leaving = document.exitFullscreen();
        if (leaving && typeof leaving.catch === "function") leaving.catch(function () {});
      } catch (error) {
        /* 已经退了：属性已摘，不必再管 */
      }
    }
  }

  /** 退沉浸只走这一张嘴：谁先落地谁记话，后到的那条通道自动哑火。 */
  function exitImmersive(via) {
    if (!stageState.immersiveKey) return;
    setImmersive(false, "");
    dock("已退出沉浸全屏（" + via + "）。", "stage.immersive");
  }

  document.addEventListener("fullscreenchange", function () {
    if (document.fullscreenElement) return;
    // 浏览器原生 Esc 退全屏时顺手把 data-immersive 一起摘掉，不留半吊子状态
    exitImmersive("Esc");
  });

  document.addEventListener("keydown", function (event) {
    if (!stageState.immersiveKey || event.key !== "Escape" || event.ctrlKey
      || event.metaKey || event.altKey || event.shiftKey) return;
    if (document.querySelector(".ws-dialog-backdrop")) return;   // 弹窗还要用 Esc 关掉，别抢
    // 有的浏览器（含自动化环境）把 Esc 留给页面自己处理，这条是原生退全屏的兜底
    exitImmersive("Esc");
  });

  function weightOf(tab) {
    var stage = tab.plugin && tab.plugin.stage;
    return stage && stage.weight === "light" ? "light" : "heavy";
  }

  function heavyLiveFrames() {
    return liveFrames().filter(function (tab) { return weightOf(tab) === "heavy"; });
  }

  /**
   * 浅休眠：light 插件切后台不摘文档，只发 plugin.suspend 让它自己收定时器，
   * 回到前台补发 plugin.resume。深休眠（摘掉 iframe）仍只数 heavy 的 LRU 账。
   */
  function applySleepPolicy() {
    stageState.tabs.forEach(function (tab) {
      if (tab.kind !== "plugin" || tab.state !== "live" || weightOf(tab) !== "light") return;
      var background = tab.key !== stageState.activeKey;
      if (background && !tab.suspended) {
        tab.suspended = true;
        notify(tab, "plugin.suspend", { reason: "background" });
      } else if (!background && tab.suspended) {
        tab.suspended = false;
        notify(tab, "plugin.resume", { reason: "foreground" });
      }
    });
  }

  function pushParams(tab) {
    // 挂载/唤醒后补发一次当前面板参数，插件不必等下一次改动才对齐
    var snapshot = window.JzoUiState && typeof window.JzoUiState.snapshot === "function"
      ? window.JzoUiState.snapshot()
      : null;
    if (snapshot) notify(tab, "ui.params.changed", snapshot);
  }

  /**
   * 「设置与控制台」是宿主自有的画布页签（不是沙箱插件）：
   * 系统管理面板必须能读工作区、装卸插件、切题库——这些能力一旦放进不透明源的
   * iframe，就得为它单开一组宿主转发方法，等于给沙箱多开一个攻击面；
   * 而且插件可卸载，控制台被卸掉就把底座变砖了。同源自检 + /settings 强制兜底
   * 才是「防变砖」的正解（军令的例外兜底条款）。
   */
  function hydrateConsole(key) {
    if (key !== "console") return;
    var frame = document.getElementById("wsConsoleFrame");
    // 哨兵值是 HTML 里写死的 about:blank（不是「没设过 src」），必须按值比，
    // 用 !getAttribute('src') 判空会永远为假、页签里就只剩一张白纸。
    if (frame && (!frame.getAttribute("src") || frame.getAttribute("src") === "about:blank")) {
      frame.setAttribute("src", "/settings?embedded=1");
    }
  }

    return {
      applySleepPolicy: applySleepPolicy,
      collapse: collapse,
      dismissGroup: dismissGroup,
      ensureScrollButtons: ensureScrollButtons,
      exitImmersive: exitImmersive,
      groupHolder: groupHolder,
      groupKeyOf: groupKeyOf,
      groupTitle: groupTitle,
      heavyLiveFrames: heavyLiveFrames,
      hydrateConsole: hydrateConsole,
      paintGroupStates: paintGroupStates,
      paintOverflowBar: paintOverflowBar,
      placeGroupList: placeGroupList,
      pushParams: pushParams,
      renderTabBar: renderTabBar,
      setImmersive: setImmersive,
      setSidebarTree: setSidebarTree,
      slideTabs: slideTabs,
      toggleGroup: toggleGroup,
      toggleImmersive: toggleImmersive,
      weightOf: weightOf,
    };
  }

  global.JzoStageTabbar = { create: create };
})(window);
