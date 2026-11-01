/**
 * st_update.js —— settings.js 的「双轨更新」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：底座 JS 单文件不超 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var apiCall = deps.apiCall;
    var el = deps.el;
    var loadInstalled = deps.loadInstalled;
    var mgSet = deps.mgSet;

  // ============ 双轨更新：插件热更新 + 底座自更新（PLUGIN_SPEC §1.7） ============
  // 出网铁律：下面每一个请求都只由当场的一次点击发起，没有任何定时器与轮询。
  var upCheckBtn = document.getElementById("upCheckBtn");
  var upAllBtn = document.getElementById("upAllBtn");
  var upStatus = document.getElementById("upStatus");
  var upListTitle = document.getElementById("upListTitle");
  var upList = document.getElementById("upList");
  var upHost = document.getElementById("upHost");
  var upHostText = document.getElementById("upHostText");
  var upHostBtn = document.getElementById("upHostBtn");
  var upLog = document.getElementById("upLog");
  var upProgress = document.getElementById("upProgress");
  var upIndexUrl = document.getElementById("plIndexUrl");
  var upRows = [];
  var upHostRow = null;
  var upHostArmed = false;
  var UP_LOG_MAX = 200;
  var UP_NOTICE_KEY = "jzo.updateNotice";

  function upStamp() {
    var now = new Date();
    function pad(value) { return value < 10 ? "0" + value : String(value); }
    return pad(now.getHours()) + ":" + pad(now.getMinutes()) + ":" + pad(now.getSeconds());
  }

  function upLine(text, tone) {
    if (!upLog) return;
    var li = el("li", "up-log-line");
    li.setAttribute("data-tone", tone || "info");
    li.appendChild(el("span", "up-log-time", upStamp()));
    li.appendChild(el("span", "up-log-text", text));
    upLog.appendChild(li);
    while (upLog.children.length > UP_LOG_MAX) upLog.removeChild(upLog.firstChild);
    upLog.scrollTop = upLog.scrollHeight;
  }

  function upBusy(on, label) {
    if (on) {
      [upCheckBtn, upAllBtn].forEach(function (button) {
        if (!button) return;
        button.disabled = true;
        button.setAttribute("aria-busy", "true");
      });
      upProgressSet(true, label);
      mgSet(upStatus, label || "正在处理…", "info");
      return;
    }
    [upCheckBtn, upAllBtn].forEach(function (button) {
      if (!button) return;
      button.removeAttribute("aria-busy");
    });
    if (upCheckBtn) upCheckBtn.disabled = false;
    if (upAllBtn) {
      upAllBtn.disabled = !upRows.some(function (row) { return row.state === "update_available"; });
    }
    upProgressSet(false);
  }

  // 后端没有细粒度进度事件：只诚实展示「不确定进度」，不伪造百分比。
  function upProgressSet(on, label) {
    if (!upProgress) return;
    upProgress.hidden = !on;
    upProgress.setAttribute("aria-busy", on ? "true" : "false");
    upProgress.setAttribute("aria-valuetext", on ? (label || "正在处理…") : "空闲");
  }

  // 检查/更新完成后把待办数同步给宿主：工作台左栏据此亮「有 N 项更新」文字徽标，
  // 不靠颜色单独传达状态（AGENTS §6）。只写本机，不发任何网络请求。
  function publishUpdateNotice(count) {
    var value = Number(count) || 0;
    try {
      if (value > 0) {
        localStorage.setItem(UP_NOTICE_KEY, JSON.stringify({ count: value, at: Date.now() }));
      } else {
        localStorage.removeItem(UP_NOTICE_KEY);
      }
    } catch (error) { /* 隐私模式禁用本地存储时只影响徽标，不影响更新流程 */ }
    try {
      if (window.parent && window.parent !== window) {
        window.parent.postMessage({ jzo: "updates.available", count: value }, window.location.origin);
      }
    } catch (error) { /* 宿主已关闭：忽略 */ }
  }

  function syncUpdateNotice() {
    var pending = upRows.filter(function (row) { return row.state === "update_available"; }).length;
    var host = upHostRow && upHostRow.update_available && upHostRow.available ? 1 : 0;
    publishUpdateNotice(pending + host);
  }

  var UP_STATE_LABEL = {
    up_to_date: "已是最新",
    update_available: "可更新",
    incompatible: "需先更新底座",
    not_in_index: "索引未收录",
    bad_entry: "条目有问题"
  };

  function renderUpdateRows() {
    if (!upList) return;
    upList.textContent = "";
    if (upListTitle) upListTitle.hidden = !upRows.length;
    if (!upRows.length) return;
    upRows.forEach(function (row) {
      var li = el("li", "mg-card up-card");
      li.setAttribute("data-id", row.id);
      li.setAttribute("data-state", row.state);

      var head = el("div", "mg-card-head");
      head.appendChild(el("span", "mg-card-name", row.name || row.id));
      head.appendChild(el("span", "mg-card-version",
        "v" + (row.local_version || "?") + (row.remote_version ? " → v" + row.remote_version : "")));
      var badge = el("span", "mg-card-state", UP_STATE_LABEL[row.state] || row.state);
      badge.setAttribute("data-state", row.state === "update_available" ? "on" : "off");
      head.appendChild(badge);
      li.appendChild(head);

      if (row.reason) li.appendChild(el("p", "mg-card-desc", row.reason));
      li.appendChild(el("p", "mg-card-sub", "id：" + row.id));

      var tools = el("div", "mg-card-tools");
      if (row.state === "update_available") {
        var apply = el("button", "q-button q-button-danger up-apply");
        apply.type = "button";
        apply.textContent = "更新";
        apply.addEventListener("click", function () { applyOne(row, apply); });
        tools.appendChild(apply);
      } else if (row.state === "incompatible") {
        var blocked = el("button", "q-button up-apply");
        blocked.type = "button";
        blocked.textContent = "需先更新底座";
        blocked.disabled = true;
        blocked.title = row.reason || "";
        tools.appendChild(blocked);
      }
      li.appendChild(tools);
      upList.appendChild(li);
    });
  }

  function renderHostRow() {
    if (!upHost || !upHostText || !upHostBtn) return;
    upHost.hidden = !upHostRow;
    upHostArmed = false;
    if (!upHostRow) return;
    var available = upHostRow.update_available && upHostRow.available;
    upHostText.textContent = available
      ? ("发现底座新版本 " + upHostRow.available + "（当前 " + upHostRow.current + "）" +
         (upHostRow.notes ? "：" + upHostRow.notes : ""))
      : ("底座当前 " + (upHostRow.current || "?") + "，" + (upHostRow.reason || "无需更新") + "。");
    upHostBtn.disabled = !available;
    upHostBtn.textContent = "更新并重启";
  }

  function upCheck() {
    var url = upIndexUrl && upIndexUrl.value ? upIndexUrl.value.trim() : "";
    upBusy(true, url ? "正在按索引地址检查更新…" : "正在用本机索引缓存检查更新…");
    upLine(url ? "检查更新：拉取索引 " + url : "检查更新：使用本机索引缓存（未出网）");
    apiCall("/api/plugins/update/check", "POST", url ? { url: url, allow_mirrors: true } : {})
      .then(function (body) {
        upRows = (body && body.plugins) || [];
        upHostRow = (body && body.host) || null;
        renderUpdateRows();
        renderHostRow();
        syncUpdateNotice();
        var summary = (body && body.summary) || {};
        upLine("检查完成：共 " + (summary.checked || 0) + " 个插件，可更新 " +
          (summary.update_available || 0) + " 个，需先更新底座 " + (summary.incompatible || 0) +
          " 个，已是最新 " + (summary.up_to_date || 0) + " 个。", "ok");
        if (body && body.index_source === "cache") upLine("索引来自本机缓存（未出网）。");
        upBusy(false);
        mgSet(upStatus, "检查完成。", "ok");
      })
      .catch(function (error) {
        upBusy(false);
        upLine("检查失败：" + error.message, "down");
        mgSet(upStatus, "检查更新失败：" + error.message, "down");
      });
  }

  function afterUpdated(updated) {
    loadInstalled();
    // 通知宿主工作台：刷新左栏插件状态，并让正占据画布的那个插件重新水合。
    try {
      window.parent.postMessage({ jzo: "plugins.updated", updated: updated || [] }, window.location.origin);
    } catch (error) {
      upLine("已更新，但通知工作台失败：" + error.message, "warn");
    }
  }

  function logOutcome(body) {
    ((body && body.updated) || []).forEach(function (row) {
      var kept = (row.preserved || []).length;
      upLine("已更新 " + row.id + "：" + (row.from || "?") + " → " + row.to +
        (kept ? "（保住本机文件 " + kept + " 个）" : ""), "ok");
    });
    ((body && body.failed) || []).forEach(function (row) {
      upLine("更新失败 " + row.id + "：" + row.reason, "down");
    });
    ((body && body.skipped) || []).forEach(function (row) {
      upLine("已跳过 " + row.id + "：" + (row.reason || row.state || ""), "warn");
    });
  }

  function applyOne(row, button) {
    if (button) { button.disabled = true; button.setAttribute("aria-busy", "true"); }
    upBusy(true, "正在更新 " + (row.name || row.id) + " …");
    upLine("开始更新 " + row.id + "：" + row.local_version + " → " + row.remote_version);
    apiCall("/api/plugins/update/apply", "POST", { ids: [row.id] })
      .then(function (body) {
        logOutcome(body);
        upBusy(false);
        if (button) button.removeAttribute("aria-busy");
        afterUpdated((body && body.updated) || []);
        mgSet(upStatus, "更新流程结束，详见下方日志。", "ok");
        upCheckSilently();
      })
      .catch(function (error) {
        upBusy(false);
        if (button) { button.disabled = false; button.removeAttribute("aria-busy"); }
        upLine("更新失败：" + error.message, "down");
        mgSet(upStatus, "更新失败：" + error.message, "down");
      });
  }

  function applyAll() {
    upBusy(true, "正在一键更新全部插件（单次批量，跑完即止）…");
    upLine("一键更新全部插件：本次范围内的条目逐个下载并热更。");
    apiCall("/api/plugins/update/apply", "POST", { all: true })
      .then(function (body) {
        logOutcome(body);
        upBusy(false);
        afterUpdated((body && body.updated) || []);
        mgSet(upStatus, "一键更新结束，详见下方日志。", "ok");
        upCheckSilently();
      })
      .catch(function (error) {
        upBusy(false);
        upLine("一键更新失败：" + error.message, "down");
        mgSet(upStatus, "一键更新失败：" + error.message, "down");
      });
  }

  function upCheckSilently() {
    // 更新完就地重算一次状态表：只用本机缓存，不再出网。
    apiCall("/api/plugins/update/check", "POST", {})
      .then(function (body) {
        upRows = (body && body.plugins) || [];
        upHostRow = (body && body.host) || upHostRow;
        renderUpdateRows();
        renderHostRow();
        syncUpdateNotice();
        upBusy(false);
      })
      .catch(function () { upBusy(false); });
  }

  function waitThenReload(triesLeft) {
    // 底座重启期间页面必然断线；这里的重试只为「重启完成后自动回到界面」，
    // 是用户那一次点击的收尾动作，不是后台轮询。
    if (triesLeft <= 0) {
      mgSet(upStatus, "底座重启超时，请手动刷新页面。", "down");
      upLine("等待底座重启超时，请手动刷新。", "down");
      return;
    }
    window.setTimeout(function () {
      fetch("/healthz", { cache: "no-store" })
        .then(function (response) {
          if (!response.ok) throw new Error("HTTP " + response.status);
          window.location.reload();
        })
        .catch(function () { waitThenReload(triesLeft - 1); });
    }, 2000);
  }

  function hostApply() {
    if (!upHostArmed) {
      // 第一下只下载 + 校验 + 生成一次性脚本，绝不动正在运行的底座。
      upHostBtn.disabled = true;
      upHostBtn.setAttribute("aria-busy", "true");
      upProgressSet(true, "正在下载并校验底座新版本…");
      upLine("正在下载并校验底座新版本（尚未覆盖任何文件）…");
      apiCall("/api/plugins/update/host-apply", "POST", {})
        .then(function (body) {
          upHostBtn.removeAttribute("aria-busy");
          upProgressSet(false);
          upLine("底座新版本已下载并校验：" + body.current + " → " + body.version +
            "；一次性脚本已生成。", "ok");
          if (body.launchable === false) {
            upLine("当前是开发工作树，底座拒绝自动覆盖重启；脚本在 " + body.script_path +
              "，需要时手工执行。", "warn");
            upHostBtn.disabled = true;
            upHostArmed = false;
            upHostBtn.textContent = "开发工作树不自动重启";
            return;
          }
          upHostArmed = true;
          upHostBtn.disabled = false;
          upHostBtn.textContent = "确认：覆盖并重启";
          mgSet(upStatus, "再点一次【确认：覆盖并重启】才会结束当前进程并覆盖程序文件（data/ 全程受保护）。", "warn");
        })
        .catch(function (error) {
          upHostBtn.removeAttribute("aria-busy");
          upProgressSet(false);
          upHostBtn.disabled = false;
          upLine("底座更新失败：" + error.message, "down");
          mgSet(upStatus, "底座更新失败：" + error.message, "down");
        });
      return;
    }
    upHostBtn.disabled = true;
    upHostBtn.setAttribute("aria-busy", "true");
    upLine("正在交接给一次性脚本：稍后底座会自行退出、覆盖程序文件并重启…");
    apiCall("/api/plugins/update/host-apply", "POST", { launch: true })
      .then(function (body) {
        upLine("已交接。底座将在 " + (body.restart_in_ms || 0) + " 毫秒后退出，" +
          "覆盖过程保护 data/、.venv/、.git/ 等目录，完成后自动重启。", "ok");
        mgSet(upStatus, "底座正在重启，页面稍后会自动恢复。", "warn");
        waitThenReload(30);
      })
      .catch(function (error) {
        upHostBtn.removeAttribute("aria-busy");
        upHostBtn.disabled = false;
        upLine("重启交接失败：" + error.message, "down");
        mgSet(upStatus, "重启交接失败：" + error.message, "down");
      });
  }

  function loadPending() {
    apiCall("/api/plugins/update/pending", "GET", null, { token: true })
      .then(function (body) {
        var pending = (body && body.pending) || [];
        if (pending.length) {
          upLine("本机有 " + pending.length + " 个插件待补齐（上一轮更新因底座重启中断）：" +
            pending.map(function (row) { return row.id; }).join("、"), "warn");
        }
        var last = (body && body.last_resume) || null;
        if (last && last.ran && last.had_pending) {
          (last.resumed || []).forEach(function (row) {
            upLine("启动续更完成：" + row.id + " " + (row.from || "?") + " → " + row.to, "ok");
          });
          (last.failed || []).forEach(function (row) {
            upLine("启动续更失败：" + row.id + "（" + row.reason + "）", "down");
          });
        }
      })
      .catch(function () { /* 待办读不到不影响其他面板，静默 */ });
  }

  if (upCheckBtn) upCheckBtn.addEventListener("click", upCheck);
  if (upAllBtn) upAllBtn.addEventListener("click", applyAll);
  if (upHostBtn) upHostBtn.addEventListener("click", hostApply);
  loadPending();

    return {
      UP_LOG_MAX: UP_LOG_MAX,
      UP_NOTICE_KEY: UP_NOTICE_KEY,
      UP_STATE_LABEL: UP_STATE_LABEL,
      afterUpdated: afterUpdated,
      applyAll: applyAll,
      applyOne: applyOne,
      hostApply: hostApply,
      loadPending: loadPending,
      logOutcome: logOutcome,
      publishUpdateNotice: publishUpdateNotice,
      renderHostRow: renderHostRow,
      renderUpdateRows: renderUpdateRows,
      syncUpdateNotice: syncUpdateNotice,
      upAllBtn: upAllBtn,
      upBusy: upBusy,
      upCheck: upCheck,
      upCheckBtn: upCheckBtn,
      upCheckSilently: upCheckSilently,
      upHost: upHost,
      upHostArmed: upHostArmed,
      upHostBtn: upHostBtn,
      upHostRow: upHostRow,
      upHostText: upHostText,
      upIndexUrl: upIndexUrl,
      upLine: upLine,
      upList: upList,
      upListTitle: upListTitle,
      upLog: upLog,
      upProgress: upProgress,
      upProgressSet: upProgressSet,
      upRows: upRows,
      upStamp: upStamp,
      upStatus: upStatus,
      waitThenReload: waitThenReload,
    };
  }

  global.JzoStUpdate = { create: create };
})(window);
