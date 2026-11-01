/**
 * st_workspace.js —— settings.js 的「工作区」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：底座 JS 单文件不超 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var apiCall = deps.apiCall;
    var el = deps.el;
    var mgSet = deps.mgSet;
    var readJson = deps.readJson;

  // ============ 工作区：列出 / 切换 / 新建（含教材版本） ============
  var wsListEl = document.getElementById("stWsList");
  var wsStatus = document.getElementById("stWsStatus");
  var wsNameInput = document.getElementById("stWsName");
  var wsTextbookSelect = document.getElementById("stWsTextbook");
  var wsCreateBtn = document.getElementById("stWsCreateBtn");
  var wsTextbookRefresh = document.getElementById("stWsTextbookRefresh");
  var wsDeleteModal = document.getElementById("wsDeleteModal");
  var wsDeleteModalText = document.getElementById("wsDeleteModalText");
  var wsDeleteInput = document.getElementById("wsDeleteConfirmInput");
  var wsDeleteCancel = document.getElementById("wsDeleteCancel");
  var wsDeleteConfirm = document.getElementById("wsDeleteConfirm");
  var wsDeleteTarget = null;
  var wsDeletePrevFocus = null;
  var wsDeleteBusy = false;
  var textbookById = {};
  var textbookItems = [];
  var activeTextbookId = "";
  var wsBusy = false;
  var wsSwitchModal = document.getElementById("wsSwitchModal");
  var wsSwitchTarget = document.getElementById("wsSwitchTarget");
  var wsSwitchCancel = document.getElementById("wsSwitchCancel");
  var wsSwitchConfirm = document.getElementById("wsSwitchConfirm");
  var wsSwitchTargetWs = null;
  var wsSwitchPrevFocus = null;
  var restartOverlay = document.getElementById("wsRestartOverlay");
  var restartBox = restartOverlay ? restartOverlay.querySelector(".st-restart-box") : null;
  var restartText = document.getElementById("wsRestartText");
  var restartHint = document.getElementById("wsRestartHint");
  var restartReloadBtn = document.getElementById("wsRestartReloadBtn");
  var restartTimer = null;

  // 独立访问 /settings 时刷新自己；被画布页签内嵌时刷新宿主，页签与左栏一起对齐新库。
  function reloadHostPage() {
    var target = window;
    try {
      if (window.top && window.top !== window.self) target = window.top;
    } catch (error) {
      target = window;
    }
    target.location.reload();
  }

  function renderWorkspaces(data) {
    if (!wsListEl) return;
    wsListEl.textContent = "";
    var list = (data && data.workspaces) || [];
    if (!list.length) {
      wsListEl.appendChild(el("li", "st-ws-empty", "尚未登记任何工作区"));
      return;
    }
    list.forEach(function (ws) {
      var li = el("li", "st-ws-item");
      li.setAttribute("data-active", ws.is_active ? "1" : "0");
      li.appendChild(el("span", "st-ws-name", ws.name || ws.id));
      var fallbackName = ws.is_active && activeTextbookId && textbookById[activeTextbookId]
        ? "跟随默认版本（当前：" + textbookById[activeTextbookId] + "）"
        : "跟随默认版本";
      var tb = ws.textbook_id ? (textbookById[ws.textbook_id] || ws.textbook_id) : fallbackName;
      li.appendChild(el("span", "st-ws-meta",
        (ws.is_active ? "当前 · " : "") + Number(ws.question_count || 0) + " 题 · 教材：" + tb));
      var actions = el("div", "st-ws-actions");
      if (textbookItems.length || ws.textbook_id) {
        var picker = el("label", "st-ws-pick");
        picker.appendChild(el("span", "st-ws-pick-label", "教材版本"));
        var pick = el("select", "st-ws-textbook-inline");
        pick.setAttribute("aria-label", "教材版本：" + (ws.name || ws.id));
        var follow = el("option");
        follow.value = "";
        follow.textContent = "跟随默认";
        pick.appendChild(follow);
        textbookItems.forEach(function (item) {
          var option = el("option");
          option.value = item.id;
          option.textContent = item.name + (item.is_default ? "（默认）" : "");
          pick.appendChild(option);
        });
        if (ws.textbook_id && !textbookById[ws.textbook_id]) {
          var stale = el("option");
          stale.value = ws.textbook_id;
          stale.textContent = ws.textbook_id + "（当前库未登记）";
          stale.disabled = true;
          pick.appendChild(stale);
        }
        pick.value = ws.textbook_id || "";
        pick.addEventListener("change", function () {
          setWorkspaceTextbook(ws, pick.value, pick);
        });
        picker.appendChild(pick);
        actions.appendChild(picker);
      }
      if (!ws.is_active) {
        var go = el("button", "q-button", "切换");
        go.type = "button";
        go.addEventListener("click", function () { switchWorkspace(ws); });
        actions.appendChild(go);
      }
      if (!ws.is_active && ws.id !== "default") {
        var remove = el("button", "q-button q-button-danger", "删除");
        remove.type = "button";
        remove.setAttribute("aria-label", "删除工作区：" + (ws.name || ws.id));
        remove.addEventListener("click", function (event) {
          event.preventDefault();
          openWsDelete(ws);
        });
        actions.appendChild(remove);
      }
      li.appendChild(actions);
      wsListEl.appendChild(li);
    });
  }

  function loadWorkspaces() {
    return fetch("/api/workspaces", { cache: "no-store" })
      .then(function (response) {
        return readJson(response, "/api/workspaces", "GET");
      })
      .then(renderWorkspaces)
      .catch(function (error) { mgSet(wsStatus, "读取工作区失败：" + error.message, "down"); });
  }

  function switchWorkspace(ws) {
    openWsSwitch(ws);
  }

  // ============ 切库重启：确认弹窗 → 全屏遮罩 → 轮询 /healthz 等新 boot_id ============
  // 严禁假死装像：遮罩只在后端真的调度了重启时出现；看不到新 boot_id 就如实报超时，
  // 并把「手动刷新」这条路交给用户，绝不用 setTimeout 演一场恢复。
  // 轮询用自我续期的 setTimeout，不用窗口级周期定时器：控制台页有一条锁死规则
  // （tests.test_console_plugin_panel.RelativeTimeTest）禁周期性墙钟定时器，
  // 而这条轮询是用户当场点确认才起的、恢复即止的一次性等待，语义完全一致。
  var RESTART_POLL_MS = 600;
  var RESTART_TIMEOUT_MS = 120000;

  function showRestartWait(text) {
    if (!restartOverlay) return;
    if (restartText) restartText.textContent = text || "正在重启底座，请稍候…";
    if (restartHint) {
      restartHint.textContent = "底座恢复后本页会自动刷新，请别关闭或手动刷新窗口。";
      restartHint.hidden = false;
    }
    if (restartBox) restartBox.removeAttribute("data-tone");
    if (restartReloadBtn) restartReloadBtn.hidden = true;
    restartOverlay.hidden = false;
    restartOverlay.setAttribute("aria-hidden", "false");
    if (restartBox && restartBox.focus) restartBox.focus();
  }

  function hideRestartWait() {
    if (restartTimer) {
      clearTimeout(restartTimer);
      restartTimer = null;
    }
    if (!restartOverlay) return;
    restartOverlay.hidden = true;
    restartOverlay.setAttribute("aria-hidden", "true");
  }

  function restartFailed(text) {
    if (restartText) restartText.textContent = text;
    if (restartHint) restartHint.textContent = "确认底座已在运行后，可点下方按钮手动刷新。";
    if (restartBox) restartBox.setAttribute("data-tone", "down");
    if (restartReloadBtn) {
      restartReloadBtn.hidden = false;
      if (restartReloadBtn.focus) restartReloadBtn.focus();
    }
  }

  function readBootId() {
    return fetch("/healthz", { cache: "no-store" })
      .then(function (response) { return response.ok ? response.json() : null; })
      .then(function (data) { return data && data.boot_id ? String(data.boot_id) : ""; })
      .catch(function () { return ""; });
  }

  function isNetworkError(error) {
    // fetch 连不上（进程正好退出）抛 TypeError；后端明确回错误才是普通 Error。
    return Boolean(error) && error.name === "TypeError";
  }

  function waitForRestart(oldBootId) {
    var deadline = Date.now() + RESTART_TIMEOUT_MS;
    var sawDown = false;
    function stop() {
      if (restartTimer) {
        clearTimeout(restartTimer);
        restartTimer = null;
      }
    }
    function tick() {
      restartTimer = null;
      if (Date.now() > deadline) {
        restartFailed("重启等待超时：两分钟内没有看到新进程上线。");
        mgSet(wsStatus, "重启等待超时，工作区指针已写入；底座起来后刷新本页即见新库。", "warn");
        return;
      }
      fetch("/healthz", { cache: "no-store" })
        .then(function (response) {
          if (!response.ok) throw new Error("HTTP " + response.status);
          return response.json();
        })
        .then(function (data) {
          var id = data && data.boot_id ? String(data.boot_id) : "";
          // 只有「身份证换过了」才算恢复；旧进程临死前的 200 不作数。
          // 拿不到旧 id 时（极少数）退而求其次：必须先看到一次连不上，再看到有进程应答。
          var alive = oldBootId ? Boolean(id) && id !== oldBootId : sawDown && Boolean(id);
          if (!alive) {
            restartTimer = setTimeout(tick, RESTART_POLL_MS);
            return;
          }
          if (restartText) restartText.textContent = "底座已重启，正在加载新工作区…";
          reloadHostPage();
        })
        .catch(function () {
          sawDown = true;
          restartTimer = setTimeout(tick, RESTART_POLL_MS);
        });
    }
    stop();
    tick();
  }

  function runWorkspaceRequest(request, waitText, failLabel) {
    wsBusy = true;
    if (wsCreateBtn) {
      wsCreateBtn.disabled = true;
      wsCreateBtn.setAttribute("aria-busy", "true");
    }
    showRestartWait(waitText);
    return readBootId().then(function (oldBootId) {
      return request().then(
        function (result) { return { bootId: oldBootId, result: result, error: null }; },
        function (error) { return { bootId: oldBootId, result: null, error: error }; }
      );
    }).then(function (outcome) {
      if (outcome.error) {
        // 请求死在重启那一瞬不能判死刑：指针已写、脚本已生成，继续等新进程起来。
        if (!outcome.bootId || !isNetworkError(outcome.error)) throw outcome.error;
        waitForRestart(outcome.bootId);
        return;
      }
      var result = outcome.result || {};
      if (!result.restarting) {
        // 受控环境（JZO_RESTART_DISABLED=1）根本没有重启：直接重载，不演等待。
        hideRestartWait();
        reloadHostPage();
        return;
      }
      waitForRestart(String(result.boot_id || outcome.bootId || ""));
    }).catch(function (error) {
      hideRestartWait();
      wsBusy = false;
      if (wsCreateBtn) {
        wsCreateBtn.disabled = false;
        wsCreateBtn.setAttribute("aria-busy", "false");
      }
      mgSet(wsStatus, failLabel + "：" + error.message, "down");
    });
  }

  function openWsSwitch(ws) {
    if (!wsSwitchModal || wsBusy) return;
    wsSwitchTargetWs = ws;
    if (wsSwitchTarget) wsSwitchTarget.textContent = "目标工作区：" + (ws.name || ws.id);
    wsSwitchPrevFocus = document.activeElement;
    wsSwitchModal.hidden = false;
    wsSwitchModal.setAttribute("aria-hidden", "false");
    if (wsSwitchConfirm) wsSwitchConfirm.focus();
  }

  function closeWsSwitch(focusBack) {
    if (wsSwitchModal) {
      wsSwitchModal.hidden = true;
      wsSwitchModal.setAttribute("aria-hidden", "true");
    }
    if (focusBack && wsSwitchPrevFocus && wsSwitchPrevFocus.focus) wsSwitchPrevFocus.focus();
    wsSwitchPrevFocus = null;
    wsSwitchTargetWs = null;
  }

  function confirmWsSwitch() {
    var ws = wsSwitchTargetWs;
    if (!ws || wsBusy) return;
    closeWsSwitch(false);
    runWorkspaceRequest(function () {
      return apiCall("/api/workspaces/switch", "POST", { workspace_id: ws.id });
    }, "正在重启底座，请稍候…", "切换失败");
  }

  function trapWsSwitchFocus(event) {
    if (!wsSwitchModal || event.key !== "Tab") return;
    var nodes = Array.prototype.filter.call(
      wsSwitchModal.querySelectorAll("button, input, select, textarea, a[href]"),
      function (node) { return !node.disabled && node.offsetParent !== null; }
    );
    if (!nodes.length) return;
    var first = nodes[0];
    var last = nodes[nodes.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  // 已有工作区也能就地换教材版本：只改工作区档案里的偏好字段，不碰题库数据。
  // 改的是当前活跃工作区时刷新宿主，让大纲树、题库浏览与录题页一起按新版本重建。
  function setWorkspaceTextbook(ws, textbookId, selectEl) {
    if (wsBusy) {
      if (selectEl) selectEl.value = ws.textbook_id || "";
      return;
    }
    wsBusy = true;
    if (selectEl) selectEl.disabled = true;
    mgSet(wsStatus, "正在为「" + (ws.name || ws.id) + "」保存教材版本…", "info");
    apiCall("/api/workspaces/textbook", "POST", {
      workspace_id: ws.id,
      textbook_id: textbookId,
    })
      .then(function () {
        if (ws.is_active) {
          reloadHostPage();
          return null;
        }
        wsBusy = false;
        return loadWorkspaces();
      })
      .catch(function (error) {
        wsBusy = false;
        if (selectEl) {
          selectEl.disabled = false;
          selectEl.value = ws.textbook_id || "";
        }
        mgSet(wsStatus, "教材版本保存失败：" + error.message, "down");
      });
  }

  function openWsDelete(ws) {
    if (!wsDeleteModal || wsDeleteBusy) return;
    wsDeleteTarget = ws;
    if (wsDeleteModalText) {
      wsDeleteModalText.textContent =
        "即将删除「" + (ws.name || ws.id) + "」：该工作区的库、边车、上传图片与配置将整体移入系统回收站。" +
        "这不是永久删除，但工作区会立即从列表消失；需要时可从回收站还原。";
    }
    if (wsDeleteInput) wsDeleteInput.value = "";
    if (wsDeleteConfirm) wsDeleteConfirm.disabled = true;
    wsDeletePrevFocus = document.activeElement;
    wsDeleteModal.hidden = false;
    wsDeleteModal.setAttribute("aria-hidden", "false");
    if (wsDeleteInput) wsDeleteInput.focus();
  }

  function closeWsDelete(focusBack) {
    if (wsDeleteModal) {
      wsDeleteModal.hidden = true;
      wsDeleteModal.setAttribute("aria-hidden", "true");
    }
    if (focusBack && wsDeletePrevFocus && wsDeletePrevFocus.focus) wsDeletePrevFocus.focus();
    wsDeletePrevFocus = null;
    wsDeleteTarget = null;
  }

  function confirmWsDelete() {
    if (wsDeleteBusy || !wsDeleteTarget) return;
    if (!wsDeleteInput || wsDeleteInput.value !== "确认删除") return;
    var ws = wsDeleteTarget;
    wsDeleteBusy = true;
    if (wsDeleteConfirm) wsDeleteConfirm.disabled = true;
    closeWsDelete(false);
    mgSet(wsStatus, "正在把「" + (ws.name || ws.id) + "」移入系统回收站…", "info");
    apiCall("/api/workspaces/" + encodeURIComponent(ws.id), "DELETE", { confirm: "确认删除" })
      .then(function (result) {
        mgSet(wsStatus, "已移入系统回收站：" + (ws.name || ws.id) +
          "（审计已写入 " + ((result && result.audit) || "data/deletion_audit.json") + "）", "ok");
        return loadWorkspaces();
      })
      .catch(function (error) { mgSet(wsStatus, "删除失败，未移入回收站：" + error.message, "down"); })
      .finally(function () { wsDeleteBusy = false; });
  }

  function trapWsDeleteFocus(event) {
    if (!wsDeleteModal || event.key !== "Tab") return;
    var nodes = Array.prototype.filter.call(
      wsDeleteModal.querySelectorAll("button, input, select, textarea, a[href]"),
      function (node) { return !node.disabled && node.offsetParent !== null; }
    );
    if (!nodes.length) return;
    var first = nodes[0];
    var last = nodes[nodes.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function loadTextbooks() {
    if (!wsTextbookSelect) return Promise.resolve();
    wsTextbookSelect.textContent = "";
    var fallback = el("option");
    fallback.value = "";
    fallback.textContent = "跟随默认版本";
    wsTextbookSelect.appendChild(fallback);
    return fetch("/api/bank/textbooks", { cache: "no-store" })
      .then(function (response) {
        return readJson(response, "/api/bank/textbooks", "GET");
      })
      .then(function (data) {
        var items = (data && data.items) || [];
        textbookById = {};
        textbookItems = items;
        activeTextbookId = String((data && data.active_textbook_id) || "");
        if (!items.length) {
          var none = el("option");
          none.value = "";
          none.textContent = "当前题库未登记教材版本";
          none.disabled = true;
          wsTextbookSelect.appendChild(none);
          mgSet(wsStatus, "当前题库没有 textbooks 登记表（老库未升级）；新建工作区仍可用，版本待大纲导入后再选。", "warn");
          return;
        }
        items.forEach(function (item) {
          textbookById[item.id] = item.name;
          var option = el("option");
          option.value = item.id;
          option.textContent = item.name + (item.is_default ? "（默认）" : "") +
            (item.publisher ? " · " + item.publisher : "");
          wsTextbookSelect.appendChild(option);
        });
      })
      .catch(function (error) { mgSet(wsStatus, "读取教材版本清单失败：" + error.message, "down"); });
  }

  function createWorkspace() {
    if (wsBusy || !wsNameInput) return;
    var name = String(wsNameInput.value || "").trim();
    if (!name) { mgSet(wsStatus, "请先填写工作区名称。", "warn"); wsNameInput.focus(); return; }
    var textbookId = wsTextbookSelect ? String(wsTextbookSelect.value || "") : "";
    // 教材版本随新建一次性登记：重启已经开始，再补一刀 /textbook 会撞在进程退出上。
    runWorkspaceRequest(function () {
      return apiCall("/api/workspaces", "POST", { name: name, textbook_id: textbookId });
    }, "正在新建工作区「" + name + "」并重启底座，请稍候…", "新建失败");
  }

  if (wsCreateBtn) wsCreateBtn.addEventListener("click", createWorkspace);
  if (wsTextbookRefresh) wsTextbookRefresh.addEventListener("click", function () {
    loadTextbooks().then(loadWorkspaces);
  });
  if (wsDeleteInput) wsDeleteInput.addEventListener("input", function () {
    if (wsDeleteConfirm) wsDeleteConfirm.disabled = wsDeleteInput.value !== "确认删除";
  });
  if (wsDeleteConfirm) wsDeleteConfirm.addEventListener("click", confirmWsDelete);
  if (wsDeleteCancel) wsDeleteCancel.addEventListener("click", function () {
    closeWsDelete(true);
    mgSet(wsStatus, "已取消删除，工作区未变动。", "info");
  });
  if (wsDeleteModal) wsDeleteModal.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      event.preventDefault();
      closeWsDelete(true);
      mgSet(wsStatus, "已取消删除，工作区未变动。", "info");
      return;
    }
    trapWsDeleteFocus(event);
  });
  if (wsSwitchConfirm) wsSwitchConfirm.addEventListener("click", confirmWsSwitch);
  if (wsSwitchCancel) wsSwitchCancel.addEventListener("click", function () {
    closeWsSwitch(true);
    mgSet(wsStatus, "已取消切换，工作区未变动。", "info");
  });
  if (wsSwitchModal) wsSwitchModal.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      event.preventDefault();
      closeWsSwitch(true);
      mgSet(wsStatus, "已取消切换，工作区未变动。", "info");
      return;
    }
    trapWsSwitchFocus(event);
  });
  if (restartReloadBtn) restartReloadBtn.addEventListener("click", function () {
    hideRestartWait();
    reloadHostPage();
  });

    return {
      RESTART_POLL_MS: RESTART_POLL_MS,
      RESTART_TIMEOUT_MS: RESTART_TIMEOUT_MS,
      activeTextbookId: activeTextbookId,
      closeWsDelete: closeWsDelete,
      closeWsSwitch: closeWsSwitch,
      confirmWsDelete: confirmWsDelete,
      confirmWsSwitch: confirmWsSwitch,
      createWorkspace: createWorkspace,
      hideRestartWait: hideRestartWait,
      isNetworkError: isNetworkError,
      loadTextbooks: loadTextbooks,
      loadWorkspaces: loadWorkspaces,
      openWsDelete: openWsDelete,
      openWsSwitch: openWsSwitch,
      readBootId: readBootId,
      reloadHostPage: reloadHostPage,
      renderWorkspaces: renderWorkspaces,
      restartBox: restartBox,
      restartFailed: restartFailed,
      restartHint: restartHint,
      restartOverlay: restartOverlay,
      restartReloadBtn: restartReloadBtn,
      restartText: restartText,
      restartTimer: restartTimer,
      runWorkspaceRequest: runWorkspaceRequest,
      setWorkspaceTextbook: setWorkspaceTextbook,
      showRestartWait: showRestartWait,
      switchWorkspace: switchWorkspace,
      textbookById: textbookById,
      textbookItems: textbookItems,
      trapWsDeleteFocus: trapWsDeleteFocus,
      trapWsSwitchFocus: trapWsSwitchFocus,
      waitForRestart: waitForRestart,
      wsBusy: wsBusy,
      wsCreateBtn: wsCreateBtn,
      wsDeleteBusy: wsDeleteBusy,
      wsDeleteCancel: wsDeleteCancel,
      wsDeleteConfirm: wsDeleteConfirm,
      wsDeleteInput: wsDeleteInput,
      wsDeleteModal: wsDeleteModal,
      wsDeleteModalText: wsDeleteModalText,
      wsDeletePrevFocus: wsDeletePrevFocus,
      wsDeleteTarget: wsDeleteTarget,
      wsListEl: wsListEl,
      wsNameInput: wsNameInput,
      wsStatus: wsStatus,
      wsSwitchCancel: wsSwitchCancel,
      wsSwitchConfirm: wsSwitchConfirm,
      wsSwitchModal: wsSwitchModal,
      wsSwitchPrevFocus: wsSwitchPrevFocus,
      wsSwitchTarget: wsSwitchTarget,
      wsSwitchTargetWs: wsSwitchTargetWs,
      wsTextbookRefresh: wsTextbookRefresh,
      wsTextbookSelect: wsTextbookSelect,
    };
  }

  global.JzoStWorkspace = { create: create };
})(window);
