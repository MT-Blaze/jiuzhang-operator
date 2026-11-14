/**
 * ws_users.js —— 左栏底部栏：工作区胶囊 + 三合一工作区弹窗（2026-11-13）。
 *
 * 用户 == 工作区：切换/新建都走 /api/workspaces，后端写指针后重启底座。
 * 这里只负责用户清单、切换确认与重启遮罩；数据隔离（题库/密钥/插件）由后端目录结构保证。
 * 整块功能可独立下架：删除本文件、ws_users.css 与 workspace.html 里的三处标记即可。
 */
(function () {
  "use strict";

  var workspaceBtn = document.getElementById("wsWorkspaceBtn");
  var nameEl = document.getElementById("wsWorkspaceName");
  var avatarEl = document.getElementById("wsWorkspaceAvatar");
  var modal = document.getElementById("wsWorkspaceModal");
  var modalClose = document.getElementById("wsWorkspaceModalClose");
  var listEl = document.getElementById("wsWorkspaceList");
  var statusEl = document.getElementById("wsWorkspaceStatus");
  var createForm = document.getElementById("wsWorkspaceCreateForm");
  var nameInput = document.getElementById("wsWorkspaceNewName");
  var createBtn = document.getElementById("wsWorkspaceCreateBtn");
  var renameForm = document.getElementById("wsWorkspaceRenameForm");
  var renameInput = document.getElementById("wsWorkspaceRenameName");
  var renameBtn = document.getElementById("wsWorkspaceRenameBtn");
  var overlay = document.getElementById("wsRestartOverlay");
  var overlayBox = document.getElementById("wsRestartBox");
  var overlayText = document.getElementById("wsRestartText");
  var overlayHint = document.getElementById("wsRestartHint");
  var reloadBtn = document.getElementById("wsRestartReloadBtn");

  if (!workspaceBtn || !modal || !listEl) return;

  var busy = false;
  var currentId = "default";
  var currentName = "默认工作区";
  var prevFocus = null;
  var pollTimer = null;
  var POLL_MS = 600;
  var TIMEOUT_MS = 120000;

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function setStatus(text, tone) {
    if (!statusEl) return;
    statusEl.textContent = text || "";
    statusEl.setAttribute("data-tone", tone || "info");
    statusEl.hidden = !text;
  }

  function initialOf(name) {
    var text = String(name || "").trim();
    return text ? text.slice(0, 1).toUpperCase() : "工";
  }

  function paintWorkspace(ws) {
    var id = String((ws && (ws.id || ws.workspace_id)) || currentId || "default");
    var label = String((ws && ws.name) || (id === "default" ? "默认工作区" : id));
    currentId = id;
    currentName = label;
    if (nameEl) {
      nameEl.textContent = label;
      nameEl.title = label;
    }
    if (avatarEl) avatarEl.textContent = initialOf(label);
    if (renameInput && document.activeElement !== renameInput) renameInput.value = label;
    if (workspaceBtn) workspaceBtn.title = "当前工作区：" + label;
  }

  function reloadPage() {
    var target = window;
    try {
      if (window.top && window.top !== window.self) target = window.top;
    } catch (error) {
      target = window;
    }
    target.location.reload();
  }

  function requestJson(path, method, body) {
    var headers = { Accept: "application/json" };
    if (body) headers["Content-Type"] = "application/json";
    var tokenStep = method === "GET" ? Promise.resolve("") : readToken();
    return tokenStep.then(function (token) {
      if (token) headers["X-JZO-Token"] = token;
      return fetch(path, {
        method: method,
        headers: headers,
        body: body ? JSON.stringify(body) : undefined,
        cache: "no-store",
      });
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (data) {
        if (!response.ok) {
          var detail = data && (data.detail || data.message);
          throw new Error(typeof detail === "string" && detail ? detail : "HTTP " + response.status);
        }
        return data;
      });
    });
  }

  function readToken() {
    return fetch("/api/settings", { cache: "no-store" })
      .then(function (response) { return response.ok ? response.json() : null; })
      .then(function (body) { return body && body.local_token ? String(body.local_token) : ""; })
      .catch(function () { return ""; });
  }

  function loadWorkspaces() {
    return requestJson("/api/workspaces", "GET").then(function (data) {
      var list = (data && data.workspaces) || [];
      var current = (data && data.current) || "default";
      var active = null;
      list.forEach(function (ws) { if (ws.id === current) active = ws; });
      paintWorkspace(active || { id: current, name: current === "default" ? "默认工作区" : current });
      renderList(list, current);
      return data;
    });
  }

  function renderList(list, current) {
    listEl.textContent = "";
    if (!list.length) {
      listEl.appendChild(el("li", "ws-switch-empty", "尚未登记任何工作区"));
      return;
    }
    list.forEach(function (ws) {
      var active = ws.is_active || ws.id === current;
      var li = el("li", "ws-switch-item");
      li.setAttribute("data-active", active ? "1" : "0");
      var main = el("div", "ws-switch-item-main");
      main.appendChild(el("strong", "ws-switch-item-name", ws.name || ws.id));
      main.appendChild(el("span", "ws-switch-item-meta",
        Number(ws.question_count || 0) + " 题" + (active ? " · 当前工作区" : "")));
      li.appendChild(main);
      if (!active) {
        var go = el("button", "ws-btn ws-btn-sm", "切换");
        go.type = "button";
        go.addEventListener("click", function () { switchTo(ws); });
        li.appendChild(go);
      }
      listEl.appendChild(li);
    });
  }

  function openModal() {
    if (busy) return;
    prevFocus = document.activeElement;
    modal.hidden = false;
    modal.setAttribute("aria-hidden", "false");
    setStatus("正在读取工作区清单…", "info");
    if (nameInput) nameInput.value = "";
    loadWorkspaces()
      .then(function () { setStatus("", "info"); })
      .catch(function (error) { setStatus("读取工作区失败：" + error.message, "down"); });
    if (modalClose) modalClose.focus();
  }

  function closeModal(focusBack) {
    modal.hidden = true;
    modal.setAttribute("aria-hidden", "true");
    if (focusBack && prevFocus && prevFocus.focus) prevFocus.focus();
    prevFocus = null;
    setStatus("", "info");
  }

  function showOverlay(text) {
    if (!overlay) return;
    if (overlayText) overlayText.textContent = text || "正在重启底座，请稍候…";
    if (overlayHint) {
      overlayHint.textContent = "底座恢复后本页会自动刷新，请别关闭或手动刷新窗口。";
      overlayHint.hidden = false;
    }
    if (reloadBtn) reloadBtn.hidden = true;
    overlay.hidden = false;
    overlay.setAttribute("aria-hidden", "false");
    if (overlayBox && overlayBox.focus) overlayBox.focus();
  }

  function hideOverlay() {
    if (pollTimer) {
      clearTimeout(pollTimer);
      pollTimer = null;
    }
    if (!overlay) return;
    overlay.hidden = true;
    overlay.setAttribute("aria-hidden", "true");
  }

  function overlayFailed(text) {
    if (overlayText) overlayText.textContent = text;
    if (overlayHint) overlayHint.textContent = "确认底座已在运行后，可点下方按钮手动刷新。";
    if (reloadBtn) {
      reloadBtn.hidden = false;
      if (reloadBtn.focus) reloadBtn.focus();
    }
  }

  function readBootId() {
    return fetch("/healthz", { cache: "no-store" })
      .then(function (response) { return response.ok ? response.json() : null; })
      .then(function (data) { return data && data.boot_id ? String(data.boot_id) : ""; })
      .catch(function () { return ""; });
  }

  function waitForRestart(oldBootId) {
    var deadline = Date.now() + TIMEOUT_MS;
    var sawDown = false;
    function tick() {
      pollTimer = null;
      if (Date.now() > deadline) {
        overlayFailed("重启等待超时：两分钟内没有看到新进程上线。");
        return;
      }
      fetch("/healthz", { cache: "no-store" })
        .then(function (response) {
          if (!response.ok) throw new Error("HTTP " + response.status);
          return response.json();
        })
        .then(function (data) {
          var id = data && data.boot_id ? String(data.boot_id) : "";
          // 只有「身份证换过了」才算恢复；拿不到旧 id 时要求先看到一次断线。
          var alive = oldBootId ? Boolean(id) && id !== oldBootId : sawDown && Boolean(id);
          if (!alive) {
            pollTimer = setTimeout(tick, POLL_MS);
            return;
          }
          reloadPage();
        })
        .catch(function () {
          sawDown = true;
          pollTimer = setTimeout(tick, POLL_MS);
        });
    }
    if (pollTimer) clearTimeout(pollTimer);
    tick();
  }

  function setBusy(value) {
    busy = value;
    [createBtn, renameBtn].forEach(function (btn) {
      if (!btn) return;
      btn.disabled = value;
      btn.setAttribute("aria-busy", value ? "true" : "false");
    });
  }

  function runSwitch(request, waitText) {
    if (busy) return;
    setBusy(true);
    closeModal(false);
    showOverlay(waitText);
    readBootId().then(function (oldBootId) {
      return request().then(
        function (result) { return { bootId: oldBootId, result: result, error: null }; },
        function (error) { return { bootId: oldBootId, result: null, error: error }; }
      );
    }).then(function (outcome) {
      if (outcome.error) {
        // 请求死在重启那一瞬不能判死刑：指针已写、脚本已生成，继续等新进程起来。
        var network = outcome.error && outcome.error.name === "TypeError";
        if (!outcome.bootId || !network) throw outcome.error;
        waitForRestart(outcome.bootId);
        return;
      }
      var result = outcome.result || {};
      if (!result.restarting) {
        hideOverlay();
        reloadPage();
        return;
      }
      waitForRestart(String(result.boot_id || outcome.bootId || ""));
    }).catch(function (error) {
      hideOverlay();
      setBusy(false);
      modal.hidden = false;
      modal.setAttribute("aria-hidden", "false");
      setStatus("操作失败：" + error.message, "down");
    });
  }

  function switchTo(ws) {
    if (busy || !ws) return;
    runSwitch(function () {
      return requestJson("/api/workspaces/switch", "POST", { workspace_id: ws.id });
    }, "正在切换到「" + (ws.name || ws.id) + "」并重启底座，请稍候…");
  }

  function createWorkspace(event) {
    if (event) event.preventDefault();
    if (busy) return;
    var name = String((nameInput && nameInput.value) || "").trim();
    if (!name) {
      setStatus("请先填写新工作区名称。", "warn");
      if (nameInput) nameInput.focus();
      return;
    }
    runSwitch(function () {
      return requestJson("/api/workspaces", "POST", { name: name, textbook_id: "" });
    }, "正在新建工作区「" + name + "」并重启底座，请稍候…");
  }

  function renameWorkspace(event) {
    if (event) event.preventDefault();
    if (busy) return;
    var name = String((renameInput && renameInput.value) || "").trim();
    if (!name) {
      setStatus("请先填写新名称。", "warn");
      if (renameInput) renameInput.focus();
      return;
    }
    if (name === currentName) {
      setStatus("名称没有变化。", "warn");
      return;
    }
    setBusy(true);
    setStatus("正在保存名称…", "info");
    requestJson("/api/workspaces/rename", "POST", { workspace_id: currentId, name: name })
      .then(function (data) {
        paintWorkspace({ id: currentId, name: (data && data.name) || name });
        setStatus("已重命名为「" + currentName + "」。", "ok");
        return loadWorkspaces();
      })
      .catch(function (error) { setStatus("重命名失败：" + error.message, "down"); })
      .then(function () { setBusy(false); });
  }

  function trapFocus(event) {
    if (event.key !== "Tab") return;
    var nodes = Array.prototype.filter.call(
      modal.querySelectorAll("button, input, a[href]"),
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

  workspaceBtn.addEventListener("click", openModal);
  if (modalClose) modalClose.addEventListener("click", function () { closeModal(true); });
  modal.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      event.preventDefault();
      closeModal(true);
      return;
    }
    trapFocus(event);
  });
  modal.addEventListener("click", function (event) {
    if (event.target === modal) closeModal(true);
  });
  if (createForm) createForm.addEventListener("submit", createWorkspace);
  if (renameForm) renameForm.addEventListener("submit", renameWorkspace);
  if (reloadBtn) reloadBtn.addEventListener("click", function () {
    hideOverlay();
    reloadPage();
  });

  loadWorkspaces().catch(function () {
    if (nameEl) nameEl.textContent = "默认工作区";
    if (avatarEl) avatarEl.textContent = "默";
  });
})();
