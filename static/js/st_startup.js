/**
 * st_startup.js —— settings.js 的「系统设置」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：底座 JS 单文件不超 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var apiCall = deps.apiCall;
    var mgSet = deps.mgSet;

  // ============ 系统设置：启动行为 ============
  // 数据源是后端 /api/startup 回的 candidates——即「所有已启用插件」，
  // 前端不再自己拼一遍口径，免得两处判断漂移。
  var startupSelect = document.getElementById("startupTarget");
  var startupSaveBtn = document.getElementById("startupSaveBtn");
  var startupReloadBtn = document.getElementById("startupReloadBtn");
  var startupStatus = document.getElementById("startupStatus");
  var startupNow = document.getElementById("startupNow");

  function startupOption(value, text) {
    var option = document.createElement("option");
    option.value = value;
    option.textContent = text;
    return option;
  }

  function renderStartup(body) {
    if (!startupSelect) return;
    var target = String((body && body.target) || "");
    var defaultTarget = String((body && body.default_target) || "");
    startupSelect.textContent = "";
    var candidates = (body && body.candidates) || [];
    candidates.forEach(function (item) {
      var label = (item.name || item.id) + "（v" + (item.version || "?") + "）";
      if (defaultTarget && "plugin:" + item.id === defaultTarget) label += " · 默认启动页";
      if (item.show_in_sidebar === false) label += " · 不占左栏";
      startupSelect.appendChild(startupOption("plugin:" + item.id, label));
    });
    var known = candidates.some(function (item) {
      return "plugin:" + item.id === target;
    });
    if (target && !known) {
      // 配置里那个插件已被卸载/停用：如实列出原值，不假装它还在
      startupSelect.appendChild(startupOption(target, target.slice("plugin:".length) + "（已卸载或已停用）"));
    }
    startupSelect.value = target;
    var reason = String((body && body.fallback_reason) || "");
    if (startupNow) {
      if (reason) {
        startupNow.textContent = "当前配置：" + target + " —— " + reason + "。配置已原地保留，插件装回或启用后自动恢复。";
      } else if (body && body.configured === false) {
        startupNow.textContent = "当前生效：" + ((body && body.plugin_name) || "留白")
          + "（默认启动页，你还没选过）。";
      } else if (!target) {
        startupNow.textContent = "当前生效：画布留白。";
      } else {
        startupNow.textContent = "当前生效：" + ((body && body.plugin_name) || target) + "。下次打开软件直接落在这里。";
      }
      startupNow.hidden = false;
    }
  }

  function loadStartup() {
    if (!startupSelect) return Promise.resolve();
    return apiCall("/api/startup", "GET")
      .then(renderStartup)
      .catch(function (error) { mgSet(startupStatus, "读取启动行为失败：" + error.message, "down"); });
  }

  if (startupSaveBtn) startupSaveBtn.addEventListener("click", function () {
    var value = startupSelect ? startupSelect.value : "";
    startupSaveBtn.disabled = true;
    startupSaveBtn.setAttribute("aria-busy", "true");
    mgSet(startupStatus, "正在保存启动行为…", "info");
    apiCall("/api/startup", "POST", { target: value })
      .then(function (body) {
        renderStartup(body);
        mgSet(startupStatus, "已保存：下次打开软件将进入「" +
          (body.plugin_name || body.effective || "留白") + "」。", "ok");
      })
      .catch(function (error) { mgSet(startupStatus, "保存失败：" + error.message, "down"); })
      .finally(function () {
        startupSaveBtn.disabled = false;
        startupSaveBtn.removeAttribute("aria-busy");
      });
  });

  if (startupReloadBtn) startupReloadBtn.addEventListener("click", function () {
    mgSet(startupStatus, "正在重新读取…", "info");
    loadStartup().then(function () { mgSet(startupStatus, "已按磁盘上的配置刷新。", "ok"); });
  });

    return {
      loadStartup: loadStartup,
      renderStartup: renderStartup,
      startupNow: startupNow,
      startupOption: startupOption,
      startupReloadBtn: startupReloadBtn,
      startupSaveBtn: startupSaveBtn,
      startupSelect: startupSelect,
      startupStatus: startupStatus,
    };
  }

  global.JzoStStartup = { create: create };
})(window);
