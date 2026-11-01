/**
 * ws_sidebar.js —— workspace.js 的「已安装插件：动态渲染左栏插件区」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1 同款口径：底座 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var dockLine = deps.dockLine;
    var enterPluginMode = deps.enterPluginMode;
    var fetchWriteToken = deps.fetchWriteToken;
    var pluginCountEl = deps.pluginCountEl;
    var pluginListEl = deps.pluginListEl;
    var wsState = deps.wsState;

  // ============ 已安装插件：动态渲染左栏插件区 ============
  var KIND_LABELS = { renderer: "渲染", importer: "导入", exporter: "导出", tool: "工具" };

  function pluginPriority(plugin) {
    var stage = plugin && plugin.stage;
    var value = stage && typeof stage.priority === "number" ? stage.priority : 0;
    return Math.max(-100, Math.min(100, value));
  }

  // 左栏插件的直白功能副标题：优先用 curated 文案，
  // 其次回落插件 description，最后才是类型标签——老师一眼看懂这插件干什么，而不是版本加点类型。
  var PLUGIN_TAGLINES = {
    "org.jiuzhang.bank-ui": "大纲、题目与查重审查",
    "org.jiuzhang.editor": "录题、改题、删题工作台",
    "org.jiuzhang.paper-gen": "题篮排成 A4 练习卷",
    "org.jiuzhang.handout": "Markdown 讲义实时排 A4"
  };

  function pluginSidebarSubtitle(plugin) {
    var tagline = PLUGIN_TAGLINES[plugin.id];
    if (tagline) return tagline;
    var desc = String(plugin.description || "").trim();
    if (desc) return desc.split(/[：:。\n]/)[0].slice(0, 24);
    return KIND_LABELS[plugin.kind] || "插件";
  }

  // ============ 左栏树：顺序与分组的唯一事实来源在后端（军令 #16） ============

  /** 宿主自有的写口：代取一次性令牌 POST，失败时把后端给的中文原因原样抛出。 */
  function postJson(url, body) {
    return fetchWriteToken()
      .then(function (token) {
        return fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-JZO-Token": token },
          body: JSON.stringify(body || {})
        });
      })
      .then(function (r) {
        return window.JzoHttp.readText(r, function (text, data) {
          if (!r.ok) {
            throw window.JzoHttp.fromResponse(r, text, data, {
              method: "POST", url: url, payload: body
            });
          }
          return data;
        });
      })
      .finally(function () { wsState.writeToken = null; });
  }

  /** 改树：先照新树渲染（点一下就见结果），再落盘；写不回去就回滚并记一笔红字。 */
  /** 左栏这边改了偏好（分组/昵称/启停），控制台页签里那份卡片要当场跟上。 */
  function notifyConsolePrefs() {
    var frame = document.getElementById("wsConsoleFrame");
    if (!frame || !frame.contentWindow) return;
    try {
      frame.contentWindow.postMessage({ jzo: "prefs.changed" }, window.location.origin);
    } catch (error) {
      /* 控制台还没起来：它下次自己 loadInstalled 时读到的就是新状态 */
    }
  }

  /**
   * 画布页签的分组合并只认左栏这棵树（组名也从这里取）：
   * 树一有变化就同步给舞台，绝不让页签栏和左栏各摆各的。
   */
  function syncStageTree() {
    if (window.JzoStage && typeof window.JzoStage.setSidebarTree === "function") {
      window.JzoStage.setSidebarTree(wsState.sidebarTree);
    }
  }

  function commitTree(next) {
    var before = wsState.sidebarTree;
    wsState.sidebarTree = next;
    renderPlugins(wsState.installedPlugins);
    syncStageTree();
    return postJson("/api/plugins/sidebar", { sidebar: next })
      .then(function (data) {
        if (data && Array.isArray(data.sidebar)) {
          wsState.sidebarTree = window.JzoPrefs ? window.JzoPrefs.readTree(data) : wsState.sidebarTree;
          renderPlugins(wsState.installedPlugins);
          notifyConsolePrefs();
          syncStageTree();
        }
      })
      .catch(function (error) {
        wsState.sidebarTree = before;
        renderPlugins(wsState.installedPlugins);
        syncStageTree();
        dockLine("左栏分组没能保存：" + error.message, "prefs.sidebar.error", "error");
      });
  }

  function pluginVisible(plugin) {
    return !!plugin && plugin.enabled !== false && plugin.show_in_sidebar !== false;
  }

  function keyPluginId(key) {
    var text = String(key || "");
    return text.indexOf("plugin:") === 0 ? text.slice("plugin:".length) : "";
  }

  function findInstalled(pluginId) {
    for (var i = 0; i < wsState.installedPlugins.length; i += 1) {
      if (wsState.installedPlugins[i].id === pluginId) return wsState.installedPlugins[i];
    }
    return null;
  }

  // 大字显示老师起的昵称，没起过就用官方原名；原名与版本收进 tooltip——
  // 一行不啰嗦，悬停全看见（军令 #16 模块二第 1 条的左栏侧镜像）。
  function rowTitle(plugin) {
    return window.JzoPrefs
      ? window.JzoPrefs.displayName(plugin)
      : String(plugin.name || plugin.id || "未命名插件");
  }

  function rowTip(plugin) {
    var tip = (plugin.nickname ? "原名 " + String(plugin.name || "") + " · " : "") +
      "v" + (plugin.version || "?");
    return tip;
  }

  function buildPluginRow(plugin) {
    var li = document.createElement("li");
    li.className = "ws-plugin-row";
    li.setAttribute("data-key", "plugin:" + String(plugin.id || ""));
    li.setAttribute("draggable", "true");
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "ws-plugin-item";
    btn.setAttribute("data-plugin-id", String(plugin.id || ""));
    btn.setAttribute("aria-current", String(Boolean(wsState.activePlugin && wsState.activePlugin.id === plugin.id)));
    var name = document.createElement("span");
    name.className = "ws-plugin-item-name";
    name.textContent = rowTitle(plugin);
    var meta = document.createElement("span");
    meta.className = "ws-plugin-item-meta";
    meta.textContent = pluginSidebarSubtitle(plugin);
    btn.title = rowTip(plugin);
    btn.appendChild(name);
    btn.appendChild(meta);
    li.appendChild(btn);
    return li;
  }

  /**
   * 左栏点击走容器级委托，而不是逐按钮绑 listener。
   *
   * 逐按钮绑的状态藏在被重建的 DOM 里：只要清单刷新（每 5 秒轮询、窗口聚焦、
   * 控制台改昵称）把整栏重画一次，正在按下的那颗按钮就被换掉，浏览器把这次
   * mousedown/mouseup 判成空点——表现就是「第一次点击没反应」。
   * 委托挂在永不重建的容器上，按钮怎么换都接得住。
   */
  function wirePluginClicks() {
    if (!pluginListEl) return;
    pluginListEl.addEventListener("click", function (event) {
      var btn = event.target && event.target.closest ? event.target.closest(".ws-plugin-item") : null;
      if (!btn || !pluginListEl.contains(btn)) return;
      var plugin = findInstalled(btn.getAttribute("data-plugin-id") || "");
      if (!plugin) return;
      wsState.userPickedPlugin = true;
      enterPluginMode(plugin, btn);
    });
  }

  function buildFolderRow(folder, kids) {
    var li = document.createElement("li");
    var collapsed = wsState.collapsedFolders[folder.id] === true;
    li.className = "ws-plugin-row ws-plugin-folder";
    li.setAttribute("data-key", String(folder.id));
    li.setAttribute("data-collapsed", String(collapsed));
    li.setAttribute("draggable", "true");
    var head = document.createElement("button");
    head.type = "button";
    head.className = "ws-plugin-folder-head";
    head.setAttribute("aria-expanded", String(!collapsed));
    head.setAttribute("aria-controls", "ws-folder-" + String(folder.id).replace(/[^A-Za-z0-9_-]/g, ""));
    var caret = document.createElement("span");
    caret.className = "ws-plugin-folder-caret";
    caret.setAttribute("aria-hidden", "true");
    caret.textContent = collapsed ? "▸" : "▾";
    var label = document.createElement("span");
    label.className = "ws-plugin-folder-name";
    label.textContent = folder.name || "未命名文件夹";
    var count = document.createElement("span");
    count.className = "ws-plugin-folder-count";
    count.textContent = String(kids.length);
    head.appendChild(caret);
    head.appendChild(label);
    head.appendChild(count);
    head.addEventListener("click", function () {
      wsState.collapsedFolders[folder.id] = wsState.collapsedFolders[folder.id] !== true;
      renderPlugins(wsState.installedPlugins);
    });
    li.appendChild(head);
    var list = document.createElement("ul");
    list.className = "ws-plugin-folder-list";
    list.id = "ws-folder-" + String(folder.id).replace(/[^A-Za-z0-9_-]/g, "");
    kids.forEach(function (plugin) { list.appendChild(buildPluginRow(plugin)); });
    li.appendChild(list);
    return li;
  }

  function clearDropMarks() {
    if (!pluginListEl) return;
    var rows = pluginListEl.querySelectorAll(".ws-plugin-row[data-drop]");
    for (var i = 0; i < rows.length; i += 1) rows[i].removeAttribute("data-drop");
  }

  // 原生 HTML5 拖拽：落在插件行上按上半/下半决定插前还是插后，落在文件夹头上即「放进该组」。
  // 结果是一次树改写，落盘到后端（顺序的唯一事实来源），不再写浏览器存储。
  function wirePluginDrag() {
    if (!pluginListEl) return;
    var draggingKey = "";
    pluginListEl.addEventListener("dragstart", function (event) {
      var row = event.target && event.target.closest ? event.target.closest(".ws-plugin-row") : null;
      if (!row) return;
      draggingKey = row.getAttribute("data-key") || "";
      row.classList.add("is-dragging");
      if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = "move";
        try { event.dataTransfer.setData("text/plain", draggingKey); } catch (error) { /* 旧浏览器忽略 */ }
      }
    });
    pluginListEl.addEventListener("dragover", function (event) {
      if (!draggingKey) return;
      var row = event.target && event.target.closest ? event.target.closest(".ws-plugin-row") : null;
      clearDropMarks();
      if (!row || row.getAttribute("data-key") === draggingKey) return;
      event.preventDefault();
      if (event.dataTransfer) event.dataTransfer.dropEffect = "move";
      if (row.classList.contains("ws-plugin-folder") && event.clientY > row.getBoundingClientRect().top + 26) {
        row.setAttribute("data-drop", "into");
        return;
      }
      var rect = row.getBoundingClientRect();
      row.setAttribute("data-drop", event.clientY < rect.top + rect.height / 2 ? "before" : "after");
    });
    pluginListEl.addEventListener("drop", function (event) {
      var dragged = draggingKey;
      var row = event.target && event.target.closest ? event.target.closest(".ws-plugin-row") : null;
      var targetKey = row ? (row.getAttribute("data-key") || "") : "";
      var mode = row ? (row.getAttribute("data-drop") || "") : "";
      draggingKey = "";
      clearDropMarks();
      if (!dragged || !targetKey || targetKey === dragged || !mode) return;
      event.preventDefault();
      if (!window.JzoPrefs) return;
      commitTree(window.JzoPrefs.moveEntry(wsState.sidebarTree, dragged, { mode: mode, anchor: targetKey }));
    });
    pluginListEl.addEventListener("dragend", function () {
      draggingKey = "";
      clearDropMarks();
      var dragging = pluginListEl.querySelectorAll(".ws-plugin-row.is-dragging");
      for (var i = 0; i < dragging.length; i += 1) dragging[i].classList.remove("is-dragging");
    });
  }

  /** 左栏视图签名：只收「画出来会变样」的字段，签名没变就一次 DOM 都不动。 */
  function viewSignatureOf(plugins) {
    try {
      return JSON.stringify({
        plugins: (plugins || []).map(function (plugin) {
          return [
            plugin.id, plugin.version, plugin.name, plugin.nickname, plugin.kind,
            plugin.description, plugin.enabled, plugin.show_in_sidebar,
            plugin.stage ? plugin.stage.priority : null
          ];
        }),
        tree: wsState.sidebarTree,
        folded: wsState.collapsedFolders
      });
    } catch (error) {
      return "";   // 序列化不了就照旧重建，绝不让左栏冻在旧视图上
    }
  }

  function renderPlugins(plugins) {
    if (!pluginListEl) return;
    var signature = viewSignatureOf(plugins);
    if (signature && signature === wsState.pluginViewSignature && pluginListEl.childElementCount) return;
    // 三态管理落到导航：停用的（enabled=false）与不占位的（show_in_sidebar=false）都不进左栏。
    var list = (plugins || []).filter(pluginVisible);
    var byId = {};
    list.forEach(function (plugin) { byId[plugin.id] = plugin; });
    var placed = {};
    var rows = [];

    function take(pluginId) {
      if (!pluginId || placed[pluginId] || !byId[pluginId]) return null;
      placed[pluginId] = true;
      return byId[pluginId];
    }

    (wsState.sidebarTree || []).forEach(function (item) {
      if (item.kind === "folder") {
        var kids = [];
        (item.children || []).forEach(function (childKey) {
          var plugin = take(keyPluginId(childKey));
          if (plugin) kids.push(plugin);
        });
        // 全员停用/卸载的文件夹不留空壳：整个不渲染，树上仍保留用户排好的位置
        if (kids.length) rows.push(buildFolderRow(item, kids));
        return;
      }
      var plugin = take(keyPluginId(item.id));
      if (plugin) rows.push(buildPluginRow(plugin));
    });

    // 默认顺序兜底（树上还没排过的、刚装进来的）：stage.priority 高者在前，同优先级按名称稳定排。
    var tail = list.filter(function (plugin) { return !placed[plugin.id]; });
    tail.sort(function (a, b) {
      var delta = pluginPriority(b) - pluginPriority(a);
      if (delta !== 0) return delta;
      return String(a.name || a.id || "").localeCompare(String(b.name || b.id || ""), "zh-CN");
    });
    tail.forEach(function (plugin) { rows.push(buildPluginRow(plugin)); });

    pluginListEl.textContent = "";
    rows.forEach(function (row) { pluginListEl.appendChild(row); });
    if (!list.length) {
      var empty = document.createElement("li");
      empty.className = "ws-plugin-empty";
      empty.textContent = "暂无插件";
      pluginListEl.appendChild(empty);
    }
    if (pluginCountEl) {
      pluginCountEl.hidden = false;
      pluginCountEl.textContent = String(list.length);
    }
    wsState.pluginViewSignature = signature;
  }

    return {
      KIND_LABELS: KIND_LABELS,
      PLUGIN_TAGLINES: PLUGIN_TAGLINES,
      buildFolderRow: buildFolderRow,
      buildPluginRow: buildPluginRow,
      clearDropMarks: clearDropMarks,
      commitTree: commitTree,
      findInstalled: findInstalled,
      keyPluginId: keyPluginId,
      notifyConsolePrefs: notifyConsolePrefs,
      pluginPriority: pluginPriority,
      pluginSidebarSubtitle: pluginSidebarSubtitle,
      pluginVisible: pluginVisible,
      postJson: postJson,
      renderPlugins: renderPlugins,
      rowTip: rowTip,
      rowTitle: rowTitle,
      syncStageTree: syncStageTree,
      viewSignatureOf: viewSignatureOf,
      wirePluginClicks: wirePluginClicks,
      wirePluginDrag: wirePluginDrag,
    };
  }

  global.JzoWsSidebar = { create: create };
})(window);
