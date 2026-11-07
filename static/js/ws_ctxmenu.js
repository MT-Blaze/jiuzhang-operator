/**
 * ws_ctxmenu.js —— workspace.js 的「右键菜单」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1 同款口径：底座 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var addBubble = deps.addBubble;
    var applyPrefsLayer = deps.applyPrefsLayer;
    var clearPluginPanel = deps.clearPluginPanel;
    var commitTree = deps.commitTree;
    var copyPlainText = deps.copyPlainText;
    var dockLine = deps.dockLine;
    var dockLog = deps.dockLog;
    var entryVisible = deps.entryVisible;
    var findInstalled = deps.findInstalled;
    var keyPluginId = deps.keyPluginId;
    var markActiveEntry = deps.markActiveEntry;
    var notifyConsolePrefs = deps.notifyConsolePrefs;
    var pluginListEl = deps.pluginListEl;
    var postJson = deps.postJson;
    var renderPluginPanel = deps.renderPluginPanel;
    var renderPlugins = deps.renderPlugins;
    var rowTitle = deps.rowTitle;
    var setStage = deps.setStage;
    var syncContextSlot = deps.syncContextSlot;
    var syncStageTree = deps.syncStageTree;
    var syncUiState = deps.syncUiState;
    var wsState = deps.wsState;

  // ============ 右键菜单（军令 #16 模块一） ============
  // 左栏：新建文件夹 / 停用插件 / 重命名；文件夹行另给重命名与解散（改组得能改回来）。
  // 底栏：只有复制，绝不给清空——清空是头部那颗按钮的活，右键一律不碰。
  // 中栏画布：一个监听都不挂，右键完全交给插件自己决定。
  function sidebarRowKey(target) {
    var row = target && target.closest ? target.closest(".ws-plugin-row") : null;
    return row ? (row.getAttribute("data-key") || "") : "";
  }

  function renamePlugin(plugin, anchor) {
    if (!window.JzoDialogs) return;
    window.JzoDialogs.text({
      title: "重命名插件",
      message: "只改这台机器上的叫法，插件本体与官方原名都不动。留空即回到原名。",
      fieldLabel: "自定义昵称",
      value: plugin.nickname || "",
      placeholder: plugin.name || "自定义昵称",
      maxLength: 40,
      requireText: false,
      emptyText: "",
      anchor: anchor,
      onAccept: function (text) {
        postJson("/api/plugins/" + encodeURIComponent(plugin.id) + "/nickname", { nickname: text })
          .then(function () {
            dockLine((text ? "插件「" + (plugin.name || plugin.id) + "」已改叫「" + text + "」。"
              : "插件「" + plugin.id + "」已回到官方原名。"), "prefs.nickname");
            notifyConsolePrefs();
            return loadPlugins({ announce: false });
          })
          .catch(function (error) {
            dockLine("改昵称失败：" + error.message, "prefs.nickname.error", "error");
          });
      }
    });
  }

  function disablePlugin(plugin, anchor) {
    if (!window.JzoDialogs) return;
    window.JzoDialogs.confirm({
      title: "停用插件",
      message: "停用「" + rowTitle(plugin) + "」只把它从导航摘掉并释放内存，代码与数据原地保留，随时可再启用。",
      confirmText: "停用",
      anchor: anchor,
      onAccept: function () {
        postJson("/api/plugins/" + encodeURIComponent(plugin.id) + "/enabled", { enabled: false })
          .then(function () {
            dockLine("插件「" + rowTitle(plugin) + "」已停用，可在【设置与控制台】里再启用。", "prefs.disable");
            notifyConsolePrefs();
            return loadPlugins({ announce: false });
          })
          .catch(function (error) {
            dockLine("停用插件失败：" + error.message, "prefs.disable.error", "error");
          });
      }
    });
  }

  function newFolderFor(pluginKey, anchor) {
    if (!window.JzoDialogs || !window.JzoPrefs) return;
    var plugin = findInstalled(keyPluginId(pluginKey));
    window.JzoDialogs.text({
      title: "新建文件夹",
      message: "新组建好后把「" + rowTitle(plugin || { id: keyPluginId(pluginKey) }) +
        "」收进去，之后可以继续往里拖。",
      fieldLabel: "文件夹名",
      value: "",
      placeholder: "例如：日常录题",
      maxLength: 24,
      anchor: anchor,
      onAccept: function (text) {
        commitTree(window.JzoPrefs.createFolderAt(wsState.sidebarTree, pluginKey, text));
        dockLine("已新建文件夹「" + text + "」。", "prefs.folder");
      }
    });
  }

  function wireSidebarMenu() {
    if (!pluginListEl || !window.JzoMenu) return;
    pluginListEl.addEventListener("contextmenu", function (event) {
      var key = sidebarRowKey(event.target);
      if (!key) return;
      var anchor = event.target.closest(".ws-plugin-row");
      event.preventDefault();
      var items = [];
      if (window.JzoPrefs.isFolderKey(key)) {
        var folderKey = key;
        items.push({
          label: "重命名",
          run: function () {
            window.JzoDialogs.text({
              title: "重命名文件夹",
              fieldLabel: "文件夹名",
              value: window.JzoPrefs.folderName(wsState.sidebarTree, folderKey),
              maxLength: 24,
              anchor: anchor,
              onAccept: function (text) {
                commitTree(window.JzoPrefs.renameFolder(wsState.sidebarTree, folderKey, text));
              }
            });
          }
        });
        items.push({
          label: "解散文件夹",
          hint: "不删插件",
          run: function () {
            commitTree(window.JzoPrefs.dissolveFolder(wsState.sidebarTree, folderKey));
            dockLine("文件夹已解散，组里的插件都回到了原位。", "prefs.folder");
          }
        });
      } else {
        var pluginId = keyPluginId(key);
        var plugin = findInstalled(pluginId);
        if (!plugin) return;
        items.push({ label: "新建文件夹", run: function () { newFolderFor(key, anchor); } });
        items.push({ label: "停用插件", run: function () { disablePlugin(plugin, anchor); } });
        items.push({ label: "重命名", run: function () { renamePlugin(plugin, anchor); } });
        var home = window.JzoPrefs ? window.JzoPrefs.folderKeyOf(wsState.sidebarTree, key) : "";
        if (home) {
          items.push({
            label: "移出文件夹",
            hint: window.JzoPrefs.folderName(wsState.sidebarTree, home),
            run: function () {
              commitTree(window.JzoPrefs.ungroupPlugin(wsState.sidebarTree, key));
            }
          });
        }
      }
      window.JzoMenu.open({
        x: event.clientX, y: event.clientY, anchor: anchor,
        label: "左栏条目操作", items: items
      });
    });
  }

  function wireDockMenu() {
    if (!dockLog || !window.JzoMenu) return;
    dockLog.addEventListener("contextmenu", function (event) {
      var item = event.target && event.target.closest ? event.target.closest(".ws-dock-item") : null;
      var lines = wsState.dockEntries.filter(entryVisible).map(function (row) { return row.line; });
      var items = [];
      if (item) {
        items.push({
          label: "复制本条",
          run: function () { copyPlainText(item.getAttribute("data-copy") || ""); }
        });
      }
      items.push({
        label: item ? "复制全部（当前视图）" : "复制全部（当前视图）",
        hint: lines.length + " 条",
        disabled: !lines.length,
        run: function () { copyPlainText(lines.join("\n")); }
      });
      event.preventDefault();
      // 军令逐字要求：这里绝不出现【清空】。清空只归头部那颗按钮。
      window.JzoMenu.open({
        x: event.clientX, y: event.clientY, anchor: item || dockLog,
        label: "输出日志区操作", items: items
      });
    });
  }



  function pluginSignatureOf(data, plugins) {
    if (data && typeof data.signature === "string" && data.signature) return data.signature;
    return plugins.map(function (p) { return p.id + "@" + p.version; }).join("|");
  }

  /**
   * 热插拔：/api/plugins 每次请求都重新扫描 plugins/，后端另回一份清单签名。
   * 页面只需定时比对签名，用户往 plugins/ 里解压一个新目录（或拖装成功）后，
   * 左栏与画布无需重启即可看到变化。运行中的 iframe 代码不热替换——规范 §4
   * 明确要求刷新页面才加载新代码，这里只负责“发现与接入”。
   */
  function loadPlugins(options) {
    var opts = options || {};
    return fetch("/api/plugins", { cache: "no-store" })
      .then(function (r) {
        return window.JzoHttp.readText(r, function (text, data) {
          if (!r.ok) throw window.JzoHttp.fromResponse(r, text, data, { url: "/api/plugins" });
          return data || {};
        });
      })
      .then(function (data) {
        var plugins = (data && data.plugins) || [];
        var signature = pluginSignatureOf(data, plugins);
        var changed = wsState.pluginSignature !== null && signature !== wsState.pluginSignature;
        var added = [];
        plugins.forEach(function (plugin) {
          if (!wsState.knownPluginIds[plugin.id]) added.push(plugin);
        });

        wsState.installedPlugins = plugins;
        // 左栏树来自这一份清单：先接上事实来源，再渲染。
        if (window.JzoPrefs) wsState.sidebarTree = window.JzoPrefs.readTree(data);
        applyPrefsLayer(data);
        if (wsState.activePlugin) {
          var still = null;
          for (var i = 0; i < plugins.length; i += 1) {
            if (plugins[i].id === wsState.activePlugin.id) { still = plugins[i]; break; }
          }
          if (still) {
            wsState.activePlugin = still;
            syncUiState(still);
            renderPluginPanel(still);
          } else {
            wsState.activePlugin = null;
            clearPluginPanel();
            setStage("工作台");
            markActiveEntry(null);
          }
        }
        renderPlugins(plugins);
        syncStageTree();
        // 右栏主权跟着同一份清单刷新：插件装/卸/停用、画布页签换主人都不必刷新页面
        syncContextSlot();
        if (window.JzoStage && typeof window.JzoStage.updatePlugin === "function") {
          plugins.forEach(function (plugin) { window.JzoStage.updatePlugin(plugin); });
        }
        // 能力路由字典与这份清单同源：每轮整表替换，停用/卸载的插件连命令一起退场。
        if (window.JzoStage && typeof window.JzoStage.setPluginCatalog === "function") {
          window.JzoStage.setPluginCatalog(plugins);
        }

        // 依赖不满足的插件已被后端置为 enabled=false：同一份签名只播报一次，
        // 老师能在对话区看见「为什么它没出现」，而不是以为装丢了。
        var blocked = (data && data.dependency_blocked) || [];
        var blockedSignature = blocked.map(function (row) {
          return (row.id || "") + ":" + (row.reason || "");
        }).join("|");
        if (opts.announce !== false && blocked.length &&
            blockedSignature !== wsState.dependencySignature) {
          addBubble("sys", "插件依赖不满足，已保持停用：" + blocked.map(function (row) {
            return "「" + (row.name || row.id) + "」（" + (row.reason || "缺少依赖") + "）";
          }).join("；"), { tone: "warn" });
        }
        wsState.dependencySignature = blockedSignature;

        if (opts.announce !== false && changed) {
          if (added.length) {
            addBubble("sys", "检测到新插件 " + added.map(function (p) {
              return "「" + (p.name || p.id) + "」";
            }).join("、") + "，已热接入左栏，无需重启。");
          } else {
            addBubble("sys", "插件清单已更新（覆盖安装或卸载）。左栏与页签已刷新。");
          }
        }

        wsState.pluginSignature = signature;
        wsState.knownPluginIds = {};
        plugins.forEach(function (plugin) { wsState.knownPluginIds[plugin.id] = true; });
        return plugins;
      });
  }

  function pollPlugins() {
    if (document.hidden) return;
    loadPlugins({ announce: true }).catch(function () { /* 轮询失败保持现状，下次再试 */ });
  }
  window.setInterval(pollPlugins, 5000);
  window.addEventListener("focus", pollPlugins);
  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) pollPlugins();
  });

    return {
      disablePlugin: disablePlugin,
      loadPlugins: loadPlugins,
      newFolderFor: newFolderFor,
      pluginSignatureOf: pluginSignatureOf,
      pollPlugins: pollPlugins,
      renamePlugin: renamePlugin,
      sidebarRowKey: sidebarRowKey,
      wireDockMenu: wireDockMenu,
      wireSidebarMenu: wireSidebarMenu,
    };
  }

  global.JzoWsCtxmenu = { create: create };
})(window);
