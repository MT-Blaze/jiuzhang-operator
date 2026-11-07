/**
 * st_plugins.js —— settings.js 的「插件管理与控制」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：底座 JS 单文件不超 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var readJson = deps.readJson;
    var readToken = deps.readToken;
    var runWorkspaceRequest = deps.runWorkspaceRequest;

  // ============ 插件管理与控制 ============
  var mgList = document.getElementById("mgList");
  var mgStatus = document.getElementById("mgStatus");
  var mgRefresh = document.getElementById("mgRefresh");
  var cmdRegistryBody = document.getElementById("cmdRegistryBody");
  var cmdRegistryEmpty = document.getElementById("cmdRegistryEmpty");
  var cmdRegistryIssues = document.getElementById("cmdRegistryIssues");
  var cmdRejectedTitle = document.getElementById("cmdRejectedTitle");
  var importFile = document.getElementById("dbImportFile");
  var importBtn = document.getElementById("dbImportBtn");
  var importName = document.getElementById("importWsName");
  var importStatus = document.getElementById("importStatus");
  var modal = document.getElementById("uninstallModal");
  var modalText = document.getElementById("uninstallText");
  var modalKeep = document.getElementById("uninstallKeep");
  var modalDanger = document.getElementById("uninstallDanger");
  var modalProvider = document.getElementById("uninstallProvider");
  var modalConfirm = document.getElementById("uninstallConfirm");
  var modalCancel = document.getElementById("uninstallCancel");
  var uninstallTarget = null;
  var installedBody = { plugins: [], sidebar: [] };
  var prefsReloadBusy = false;
  var uninstallPrevFocus = null;

  /** 题库引擎（声明 bank.provider）：数据是老师真题本体，卸载不许碰库。 */
  function isProviderPlugin(plugin) {
    return !!(plugin && Array.isArray(plugin.capabilities) &&
      plugin.capabilities.indexOf("bank.provider") >= 0);
  }

  function mgSet(box, text, tone) {
    if (!box) return;
    box.textContent = text || "";
    box.setAttribute("data-tone", tone || "info");
    box.hidden = !text;
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function apiCall(path, method, body, options) {
    // GET 默认不带令牌；但更新续更待办那条 GET 是带令牌的路由，须显式要求。
    var needsToken = method !== "GET" || Boolean(options && options.token);
    var steps = needsToken ? readToken() : Promise.resolve();
    return steps.then(function (token) {
      var headers = { Accept: "application/json" };
      if (token) headers["X-JZO-Token"] = token;
      if (body) headers["Content-Type"] = "application/json";
      return fetch(path, { method: method, headers: headers, body: body ? JSON.stringify(body) : undefined })
        .then(function (response) {
          return readJson(response, path, method, body);
        });
    });
  }

  /**
   * 「已启用」的顺序与左栏导航 100% 对齐——两边读的是同一棵后端树（/api/plugins 的 sidebar），
   * 这里只把它摊平，不再自己排一遍第二顺序，否则「对齐」只能靠运气。
   */
  function flattenTree(tree) {
    var keys = [];
    (tree || []).forEach(function (item) {
      if (item.kind === "folder") {
        item.children.forEach(function (child) { keys.push(child); });
      } else keys.push(item.id);
    });
    return keys;
  }

  function enabledFirst(plugins, tree) {
    var byKey = {};
    var rest = [];
    (plugins || []).forEach(function (plugin) {
      if (plugin.enabled === false) return;
      byKey["plugin:" + plugin.id] = plugin;
      rest.push(plugin);
    });
    var ordered = [];
    flattenTree(tree).forEach(function (key) {
      if (byKey[key]) { ordered.push(byKey[key]); delete byKey[key]; }
    });
    // 树上还没有的（刚装完还没拖过）接在末尾，保持清单原序，绝不插队到已排好的段里
    rest.forEach(function (plugin) {
      if (ordered.indexOf(plugin) < 0) ordered.push(plugin);
    });
    return ordered;
  }

  /** 「已停用」按停用时间先后排；本机没记下时间的排最后，文案如实写「未知」。 */
  function disabledByTime(plugins) {
    var rows = (plugins || []).filter(function (plugin) { return plugin.enabled === false; });
    rows.sort(function (a, b) {
      var ta = Date.parse(a.disabled_at || "") || Number.MAX_SAFE_INTEGER;
      var tb = Date.parse(b.disabled_at || "") || Number.MAX_SAFE_INTEGER;
      return ta - tb;
    });
    return rows;
  }

  function renderInstalled(plugins, body) {
    if (!mgList) return;
    // 相对时间只在渲染这一瞬算一次：不挂定时器、不后台刷新（军令逐字要求）。
    var now = new Date();
    var tree = window.JzoPrefs ? window.JzoPrefs.readTree(body) : [];
    var ordered = enabledFirst(plugins, tree).concat(disabledByTime(plugins));
    mgList.textContent = "";
    if (!ordered.length) {
      mgList.appendChild(el("li", "mg-empty", "尚未安装任何插件"));
      return;
    }
    ordered.forEach(function (plugin) {
      var off = plugin.enabled === false;
      var blocked = plugin.dependency_blocked === true;
      var li = el("li", "mg-card");
      li.setAttribute("data-id", plugin.id);
      if (off) li.setAttribute("data-state", "disabled");

      var head = el("div", "mg-card-head");
      // 大字只属于老师给它的叫法；没起昵称时 displayName 回落官方原名
      head.appendChild(el("span", "mg-card-name",
        window.JzoPrefs ? window.JzoPrefs.displayName(plugin) : (plugin.name || plugin.id)));
      var status = el("span", "mg-card-state", blocked ? "依赖不满足" : (off ? "已停用" : "已启用"));
      status.setAttribute("data-state", off ? "off" : "on");
      head.appendChild(status);
      li.appendChild(head);

      // 依赖缺失/被停用：说清缺谁、为什么没亮，绝不让老师面对一个空壳界面。
      if (blocked && plugin.dependency_error) {
        li.appendChild(el("p", "mg-card-deps", plugin.dependency_error));
      }

      // 小字才是官方原名与版本——昵称再花哨也不掩盖它装的是哪一个包
      li.appendChild(el("p", "mg-card-official",
        "官方原名：" + (plugin.name || plugin.id) + " · v" + (plugin.version || "?")));
      li.appendChild(el("p", "mg-card-desc", plugin.description || ""));
      var sub = "id：" + plugin.id + " · 类型：" + (plugin.kind || "?");
      if (off) {
        sub += " · 停用时间：" + (window.JzoPrefs
          ? (window.JzoPrefs.relTime(plugin.disabled_at, now) || "本机未记录（早于本版本停用）")
          : (plugin.disabled_at || "本机未记录"));
      }
      li.appendChild(el("p", "mg-card-sub", sub));

      var tools = el("div", "mg-card-tools");
      var toggle = el("button", "q-button mg-toggle");
      toggle.type = "button";
      toggle.textContent = off ? "启用" : "停用";
      // 依赖不满足时单点「启用」只会写进本机偏好，发现阶段仍会把它按住；
      // 干脆禁用按钮并指向真正的解法——先装/启用依赖插件。
      toggle.disabled = blocked;
      if (blocked) toggle.title = "先安装或启用它依赖的插件：" + (plugin.missing_requires || []).join("、");
      toggle.addEventListener("click", function () {
        setEnabled(plugin, off);
      });
      tools.appendChild(toggle);

      var nickname = el("button", "q-button mg-rename");
      nickname.type = "button";
      nickname.textContent = "改昵称";
      nickname.addEventListener("click", function () { renameFromCard(plugin); });
      tools.appendChild(nickname);

      if (plugin.show_in_sidebar === false) {
        tools.appendChild(el("span", "mg-tag", "不占左栏"));
      }

      if (plugin.uninstallable === false) {
        // 免死金牌：清单写死不可卸载，面板不给按钮；后端 DELETE 同样按 409 拒绝。
        tools.appendChild(el("span", "mg-tag", "受保护·不可卸载"));
      } else {
        var remove = el("button", "q-button q-button-danger mg-uninstall");
        remove.type = "button";
        remove.textContent = "卸载";
        remove.addEventListener("click", function () { openUninstall(plugin); });
        tools.appendChild(remove);
      }

      // 卡片尾部小标签：它在哪一组。这里只给改昵称，不设任何回退官方名的按钮。
      var homeKey = window.JzoPrefs
        ? window.JzoPrefs.folderKeyOf(tree, "plugin:" + plugin.id) : "";
      tools.appendChild(el("span", "mg-tag mg-tag-folder",
        homeKey ? "组：" + window.JzoPrefs.folderName(tree, homeKey) : "未分组"));
      li.appendChild(tools);

      mgList.appendChild(li);
    });
  }

  /** 命令能力字典：只读对照表，数据来自 /api/plugins 的 commands（与 command.list 同源）。 */
  function renderCommandRegistry(body) {
    if (!cmdRegistryBody) return;
    var commands = body && Array.isArray(body.commands) ? body.commands : [];
    var rejected = body && Array.isArray(body.commands_rejected) ? body.commands_rejected : [];
    cmdRegistryBody.textContent = "";
    commands.forEach(function (command) {
      var row = el("tr", "");
      row.appendChild(el("td", "mg-cmd-id", command.id || ""));
      row.appendChild(el("td", "", command.title || command.id || ""));
      row.appendChild(el("td", "", command.plugin_name || command.plugin_id || ""));
      row.appendChild(el("td", "mg-cmd-desc", command.description || command.returns || ""));
      row.appendChild(el("td", "mg-cmd-flag",
        command.requires_user ? "需确认" : "直接执行"));
      cmdRegistryBody.appendChild(row);
    });
    if (cmdRegistryEmpty) cmdRegistryEmpty.hidden = commands.length > 0;
    if (cmdRegistryIssues) {
      cmdRegistryIssues.textContent = "";
      rejected.forEach(function (issue) {
        var id = issue && issue.id ? "「" + issue.id + "」" : "";
        cmdRegistryIssues.appendChild(el("li", "",
          "插件 " + ((issue && issue.plugin_id) || "?") + " 声明的 " + id + " 已丢弃："
          + ((issue && issue.reason) || "未说明原因")));
      });
      cmdRegistryIssues.hidden = rejected.length === 0;
    }
    if (cmdRejectedTitle) cmdRejectedTitle.hidden = rejected.length === 0;
  }

  function renameFromCard(plugin) {
    var current = String(plugin.nickname || "");
    var next = window.prompt(
      "给「" + (plugin.name || plugin.id) + "」起个只在你这台机器上生效的昵称（留空则回到官方原名）：",
      current);
    if (next == null) return;
    setNickname(plugin, next.trim());
  }

  function setNickname(plugin, nickname) {
    mgSet(mgStatus, "正在改昵称…", "info");
    apiCall("/api/plugins/" + encodeURIComponent(plugin.id) + "/nickname", "POST", { nickname: nickname })
      .then(function () {
        mgSet(mgStatus, nickname ? "已改叫「" + nickname + "」。" : "已回到官方原名。", "ok");
        tellWorkspacePrefs();
        return loadInstalled();
      })
      .catch(function (error) { mgSet(mgStatus, "改昵称失败：" + error.message, "down"); });
  }

  /** 控制台改完偏好，工作台左栏要当场跟上，不等下一次轮询。 */
  function tellWorkspacePrefs() {
    if (window.parent && window.parent !== window) {
      window.parent.postMessage({ jzo: "prefs.changed" }, window.location.origin);
    }
  }

  // 反方向同理：在工作台左栏拖了组、改了昵称或停用了插件，
  // 内嵌在画布页签里的这份卡片必须跟着重读，不能各说各话。
  window.addEventListener("message", function (event) {
    if (event.origin !== window.location.origin) return;
    var data = event.data;
    if (data && data.jzo === "prefs.changed" && !prefsReloadBusy) {
      prefsReloadBusy = true;
      loadInstalled().then(function () { prefsReloadBusy = false; },
        function () { prefsReloadBusy = false; });
    }
  });

  // ============ 已安装插件清单 ============
  function loadInstalled() {
    return fetch("/api/plugins", { cache: "no-store" })
      .then(function (response) {
        return readJson(response, "/api/plugins", "GET");
      })
      .then(function (data) {
        installedBody = data || {};
        renderInstalled(installedBody.plugins || [], installedBody);
        renderCommandRegistry(installedBody);
      })
      .catch(function (error) { mgSet(mgStatus, "读取插件列表失败：" + error.message, "down"); });
  }

  function setEnabled(plugin, enabled) {
    mgSet(mgStatus, "正在" + (enabled ? "启用" : "停用") + " " + (plugin.name || plugin.id) + "…", "info");
    apiCall("/api/plugins/" + encodeURIComponent(plugin.id) + "/enabled", "POST", { enabled: enabled })
      .then(function () {
        mgSet(mgStatus, (enabled ? "已启用：" : "已停用：") +
          (window.JzoPrefs ? window.JzoPrefs.displayName(plugin) : (plugin.name || plugin.id)) +
          (enabled ? "，工作台左栏刷新后可见。" : "，代码与数据原地保留，随时可再启用。"), "ok");
        tellWorkspacePrefs();
        loadInstalled();
      })
      .catch(function (error) { mgSet(mgStatus, "操作失败：" + error.message, "down"); });
  }

  function openUninstall(plugin) {
    if (plugin && plugin.uninstallable === false) {
      mgSet(mgStatus, "「" + (plugin.name || plugin.id)
        + "」是题库引擎，受保护不可卸载；如需停用请用「停用」按钮。", "info");
      return;
    }
    uninstallTarget = plugin;
    uninstallPrevFocus = document.activeElement;
    var guarded = isProviderPlugin(plugin);
    if (modalText) modalText.textContent = "确定卸载「" + (plugin.name || plugin.id) + "」？";
    if (modalKeep) {
      modalKeep.checked = true;
      // 置灰而不是隐藏：隐藏会让人以为这是个能勾却没勾上的选项
      modalKeep.disabled = guarded;
      if (guarded && modalKeep.parentNode) modalKeep.parentNode.setAttribute("aria-disabled", "true");
      if (!guarded && modalKeep.parentNode) modalKeep.parentNode.removeAttribute("aria-disabled");
    }
    if (modalDanger) modalDanger.hidden = true;
    if (modalProvider) modalProvider.hidden = !guarded;
    if (modal) {
      modal.hidden = false;
      modal.setAttribute("aria-hidden", "false");
      if (guarded && modalCancel) modalCancel.focus();
      else if (modalKeep) modalKeep.focus();
    }
  }

  function closeUninstall() {
    if (modal) {
      modal.hidden = true;
      modal.setAttribute("aria-hidden", "true");
    }
    uninstallTarget = null;
    if (uninstallPrevFocus && uninstallPrevFocus.focus) uninstallPrevFocus.focus();
    uninstallPrevFocus = null;
  }

  function confirmUninstall() {
    if (!uninstallTarget) return;
    var plugin = uninstallTarget;
    // 题库引擎双保险：DOM 被改坏了也照样按「保留数据」发请求
    var keep = isProviderPlugin(plugin) || (modalKeep ? modalKeep.checked : true);
    closeUninstall();
    mgSet(mgStatus, "正在卸载 " + (plugin.name || plugin.id) + "…", "info");
    apiCall("/api/plugins/" + encodeURIComponent(plugin.id) + "?keep_data=" + (keep ? "true" : "false"), "DELETE")
      .then(function (result) {
        var removed = (result && result.removed_data && result.removed_data.length) || 0;
        var outcome;
        if (result && result.provider_guarded) {
          outcome = "（题库引擎已被保护，数据将原地保留）。";
        } else if (keep) {
          outcome = "（保留了本地数据）。";
        } else {
          outcome = "（已连同 " + removed + " 个本地数据库一并物理删除）。";
        }
        mgSet(mgStatus, "已卸载 " + (plugin.name || plugin.id) + outcome, "ok");
        loadInstalled();
      })
      .catch(function (error) { mgSet(mgStatus, "卸载失败：" + error.message, "down"); });
  }

  function fileToBase64(file) {
    return new Promise(function (resolve, reject) {
      var reader = new FileReader();
      reader.onload = function () {
        var text = String(reader.result || "");
        resolve(text.slice(text.indexOf(",") + 1));   // 去掉 data:;base64, 前缀
      };
      reader.onerror = function () { reject(new Error("读取文件失败")); };
      reader.readAsDataURL(file);
    });
  }

  function importDatabase() {
    if (!importFile) return;
    var name = importName ? String(importName.value || "").trim() : "";
    if (!name) { mgSet(importStatus, "请先填写新工作区名称。", "warn"); if (importName) importName.focus(); return; }
    importFile.click();
  }

  function handleImportFile(file) {
    if (!file) return;
    if (!/\.db$/i.test(file.name || "")) { mgSet(importStatus, "请选择 .db 数据库文件。", "warn"); return; }
    if (file.size > 64 * 1024 * 1024) { mgSet(importStatus, "题库文件超过 64 MB 上限。", "warn"); return; }
    mgSet(importStatus, "正在校验并挂载 " + file.name + "…", "info");
    fileToBase64(file).then(function (b64) {
      var name = importName ? String(importName.value || "").trim() : "";
      // 导入即切换，切库必须重启：交给同一套遮罩 + /healthz 轮询，不假装修好了。
      runWorkspaceRequest(function () {
        return apiCall("/api/workspaces/import", "POST", { name: name, db_base64: b64 });
      }, "正在挂载「" + name + "」为新工作区并重启底座，请稍候…", "导入失败");
      if (importName) importName.value = "";
    }).catch(function (error) {
      mgSet(importStatus, "导入失败：" + (error && error.message ? error.message : error), "down");
    });
  }

  if (mgRefresh) mgRefresh.addEventListener("click", loadInstalled);
  if (modalConfirm) modalConfirm.addEventListener("click", confirmUninstall);
  if (modalCancel) modalCancel.addEventListener("click", closeUninstall);
  if (modalKeep) modalKeep.addEventListener("change", function () {
    if (modalDanger) modalDanger.hidden = modalKeep.checked;
  });
  if (modal) modal.addEventListener("keydown", function (event) {
    if (event.key === "Escape") { event.preventDefault(); closeUninstall(); }
  });
  if (importBtn) importBtn.addEventListener("click", importDatabase);
  if (importFile) importFile.addEventListener("change", function () {
    var file = importFile.files && importFile.files[0];
    importFile.value = "";
    handleImportFile(file);
  });

    return {
      apiCall: apiCall,
      closeUninstall: closeUninstall,
      cmdRegistryBody: cmdRegistryBody,
      cmdRegistryEmpty: cmdRegistryEmpty,
      cmdRegistryIssues: cmdRegistryIssues,
      cmdRejectedTitle: cmdRejectedTitle,
      confirmUninstall: confirmUninstall,
      disabledByTime: disabledByTime,
      el: el,
      enabledFirst: enabledFirst,
      fileToBase64: fileToBase64,
      flattenTree: flattenTree,
      handleImportFile: handleImportFile,
      importBtn: importBtn,
      importDatabase: importDatabase,
      importFile: importFile,
      importName: importName,
      importStatus: importStatus,
      installedBody: installedBody,
      isProviderPlugin: isProviderPlugin,
      loadInstalled: loadInstalled,
      mgList: mgList,
      mgRefresh: mgRefresh,
      mgSet: mgSet,
      mgStatus: mgStatus,
      modal: modal,
      modalCancel: modalCancel,
      modalConfirm: modalConfirm,
      modalDanger: modalDanger,
      modalKeep: modalKeep,
      modalProvider: modalProvider,
      modalText: modalText,
      openUninstall: openUninstall,
      prefsReloadBusy: prefsReloadBusy,
      renameFromCard: renameFromCard,
      renderCommandRegistry: renderCommandRegistry,
      renderInstalled: renderInstalled,
      setEnabled: setEnabled,
      setNickname: setNickname,
      tellWorkspacePrefs: tellWorkspacePrefs,
      uninstallPrevFocus: uninstallPrevFocus,
      uninstallTarget: uninstallTarget,
    };
  }

  global.JzoStPlugins = { create: create };
})(window);
