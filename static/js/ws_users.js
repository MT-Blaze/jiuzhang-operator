/**
 * ws_users.js —— 左栏「切换用户」（2026-11-05）。
 *
 * 用户 == 工作区：切换/新建都走 /api/workspaces，后端写指针后重启底座。
 * 这里只负责用户清单、切换确认与重启遮罩；数据隔离（题库/密钥/插件）由后端目录结构保证。
 * 整块功能可独立下架：删除本文件、ws_users.css 与 workspace.html 里的三处标记即可。
 */
(function () {
  "use strict";

  var cardBtn = document.getElementById("wsUserSwitchBtn");
  var nameEl = document.getElementById("wsUserName");
  var modal = document.getElementById("wsUserModal");
  var modalClose = document.getElementById("wsUserModalClose");
  var listEl = document.getElementById("wsUserList");
  var statusEl = document.getElementById("wsUserStatus");
  var form = document.getElementById("wsUserCreateForm");
  var nameInput = document.getElementById("wsUserNewName");
  var createBtn = document.getElementById("wsUserCreateBtn");
  var overlay = document.getElementById("wsRestartOverlay");
  var overlayBox = document.getElementById("wsRestartBox");
  var overlayText = document.getElementById("wsRestartText");
  var overlayHint = document.getElementById("wsRestartHint");
  var reloadBtn = document.getElementById("wsRestartReloadBtn");

  if (!cardBtn || !modal || !listEl) return;

  var busy = false;
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

  function loadUsers() {
    return requestJson("/api/workspaces", "GET").then(function (data) {
      var list = (data && data.workspaces) || [];
      var current = (data && data.current) || "";
      var active = null;
      list.forEach(function (ws) { if (ws.id === current) active = ws; });
      if (nameEl) nameEl.textContent = active ? (active.name || active.id) : "默认工作区";
      renderList(list, current);
      return data;
    });
  }

  function renderList(list, current) {
    listEl.textContent = "";
    if (!list.length) {
      listEl.appendChild(el("li", "ws-user-empty", "尚未登记任何用户"));
      return;
    }
    list.forEach(function (ws) {
      var li = el("li", "ws-user-item");
      li.setAttribute("data-active", ws.is_active || ws.id === current ? "1" : "0");
      var main = el("div", "ws-user-item-main");
      main.appendChild(el("strong", "ws-user-item-name", ws.name || ws.id));
      main.appendChild(el("span", "ws-user-item-meta",
        Number(ws.question_count || 0) + " 题" + (ws.id === current ? " · 当前用户" : "")));
      li.appendChild(main);
      if (ws.id !== current) {
        var go = el("button", "ws-btn ws-btn-sm", "切换到此用户");
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
    setStatus("正在读取用户清单…", "info");
    loadUsers()
      .then(function () { setStatus("", "info"); })
      .catch(function (error) { setStatus("读取用户失败：" + error.message, "down"); });
    if (nameInput) nameInput.value = "";
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

  function runSwitch(request, waitText) {
    if (busy) return;
    busy = true;
    if (createBtn) {
      createBtn.disabled = true;
      createBtn.setAttribute("aria-busy", "true");
    }
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
      busy = false;
      if (createBtn) {
        createBtn.disabled = false;
        createBtn.setAttribute("aria-busy", "false");
      }
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

  function createUser(event) {
    if (event) event.preventDefault();
    if (busy) return;
    var name = String((nameInput && nameInput.value) || "").trim();
    if (!name) {
      setStatus("请先填写新用户名称。", "warn");
      if (nameInput) nameInput.focus();
      return;
    }
    runSwitch(function () {
      return requestJson("/api/workspaces", "POST", { name: name, textbook_id: "" });
    }, "正在新建空用户「" + name + "」并重启底座，请稍候…");
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

  cardBtn.addEventListener("click", openModal);
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
  if (form) form.addEventListener("submit", createUser);
  if (reloadBtn) reloadBtn.addEventListener("click", function () {
    hideOverlay();
    reloadPage();
  });

  loadUsers().catch(function () {
    if (nameEl) nameEl.textContent = "默认工作区";
  });
})();
