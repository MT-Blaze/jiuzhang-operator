/**
 * st_provider.js —— settings.js 的「模型配置」小节抽出来的独立模块
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

  // ============ 模型配置：Provider 列表 / 切换 / 保存 / 测连通 ============
  var pvSelect = document.getElementById("pvSelect");
  var pvTarget = document.getElementById("pvTarget");
  var pvBaseUrl = document.getElementById("pvBaseUrl");
  var pvApiKey = document.getElementById("pvApiKey");
  var pvModel = document.getElementById("pvModel");
  var pvSwitchBtn = document.getElementById("pvSwitchBtn");
  var pvSaveBtn = document.getElementById("pvSaveBtn");
  var pvTestBtn = document.getElementById("pvTestBtn");
  var pvResult = document.getElementById("pvResult");
  var pvProfiles = [];

  function pvCurrent() {
    var name = pvSelect && pvSelect.value ? pvSelect.value : "";
    for (var i = 0; i < pvProfiles.length; i += 1) {
      if (pvProfiles[i].name === name) return pvProfiles[i];
    }
    return null;
  }

  function pvRenderTarget() {
    if (!pvTarget) return;
    var profile = pvCurrent();
    if (!profile) {
      pvTarget.textContent = "未选择 Provider";
      pvTarget.setAttribute("data-state", "off");
      return;
    }
    pvTarget.textContent = profile.label + " · " + (profile.active ? "当前使用" : "未启用") +
      " · " + (profile.configured ? "已配置密钥" : "未配置（走 Mock）") +
      (profile.host ? " · " + profile.host : "") +
      (profile.model ? " · " + profile.model : "");
    pvTarget.setAttribute("data-state", profile.configured ? "on" : "off");
    if (pvBaseUrl && !pvBaseUrl.value) {
      pvBaseUrl.placeholder = profile.host
        ? "当前接口主机：" + profile.host + "（留空则不改）"
        : "https://api.example.com/v1";
    }
    if (pvModel && !pvModel.value) pvModel.value = profile.model || "";
  }

  function pvNotifyHost() {
    // 宿主顶栏的模型胶囊是只读状态；配置变了就提醒它重新拉一次 /api/providers。
    try {
      if (window.parent && window.parent !== window.self) {
        window.parent.postMessage({ jzo: "providers.changed" }, window.location.origin);
      }
    } catch (error) { /* 独立打开时没有宿主，忽略 */ }
  }

  function pvLoad() {
    return fetch("/api/providers", { cache: "no-store" })
      .then(function (response) {
        return readJson(response, "/api/providers", "GET");
      })
      .then(function (data) {
        pvProfiles = (data && data.providers) || [];
        if (pvSelect) {
          pvSelect.textContent = "";
          pvProfiles.forEach(function (p) {
            var option = el("option");
            option.value = p.name;
            option.textContent = p.label + (p.configured ? "" : "（未配置）");
            if (p.active) option.selected = true;
            pvSelect.appendChild(option);
          });
        }
        pvRenderTarget();
      })
      .catch(function (error) { mgSet(pvResult, "读取 Provider 注册表失败：" + error.message, "down"); });
  }

  function pvCollect() {
    var profile = pvCurrent();
    if (!profile) return null;
    var payload = { name: profile.name };
    var dirty = false;
    if (pvBaseUrl && pvBaseUrl.value.trim()) { payload.base_url = pvBaseUrl.value.trim(); dirty = true; }
    if (pvApiKey && pvApiKey.value.trim()) { payload.api_key = pvApiKey.value.trim(); dirty = true; }
    if (pvModel && pvModel.value.trim()) { payload.model = pvModel.value.trim(); dirty = true; }
    return dirty ? payload : false;
  }

  function pvSave() {
    var payload = pvCollect();
    if (!payload) return Promise.resolve(false);
    return apiCall("/api/providers/config", "POST", payload).then(function () {
      if (pvApiKey) pvApiKey.value = "";
      if (pvBaseUrl) pvBaseUrl.value = "";
      return pvLoad().then(function () { return true; });
    });
  }

  function pvBusy(btn, on, label) {
    if (!btn) return;
    btn.disabled = on;
    btn.setAttribute("aria-busy", on ? "true" : "false");
    if (label) btn.textContent = label;
  }

  if (pvSelect) pvSelect.addEventListener("change", pvRenderTarget);

  if (pvSwitchBtn) pvSwitchBtn.addEventListener("click", function () {
    var profile = pvCurrent();
    if (!profile) { mgSet(pvResult, "请先选择一个 Provider。", "warn"); return; }
    pvBusy(pvSwitchBtn, true);
    mgSet(pvResult, "正在切换…", "info");
    pvSave().catch(function () { return false; }).then(function () {
      return apiCall("/api/providers/active", "POST", { name: profile.name });
    }).then(function (result) {
      mgSet(pvResult, result.mock
        ? "已切到「" + result.active + "」：未配置密钥，走 Mock 回显。"
        : "已切到「" + result.active + "」：真实模型 " + result.model + "。", "ok");
      return pvLoad().then(pvNotifyHost);
    }).catch(function (error) {
      mgSet(pvResult, "切换失败：" + error.message, "down");
    }).finally(function () { pvBusy(pvSwitchBtn, false); });
  });

  if (pvSaveBtn) pvSaveBtn.addEventListener("click", function () {
    pvBusy(pvSaveBtn, true);
    pvSave().then(function (saved) {
      mgSet(pvResult, saved
        ? "配置已保存并热生效（密钥只落在本机 .env，永不回显）。"
        : "表单没有改动，无需保存。", saved ? "ok" : "info");
      if (saved) pvNotifyHost();
    }).catch(function (error) {
      mgSet(pvResult, "保存失败：" + error.message, "down");
    }).finally(function () { pvBusy(pvSaveBtn, false); });
  });

  if (pvTestBtn) pvTestBtn.addEventListener("click", function () {
    var profile = pvCurrent();
    if (!profile) { mgSet(pvResult, "请先选择一个 Provider。", "warn"); return; }
    pvBusy(pvTestBtn, true);
    mgSet(pvResult, "正在保存未提交的改动，随后向接口发一次只读 GET /models…", "info");
    pvSave().catch(function () { return false; }).then(function () {
      return apiCall("/api/providers/test", "POST", { name: profile.name });
    }).then(function (body) {
      mgSet(pvResult, (body.ok ? "连通正常 · " : "不通 · ") + (body.detail || ""),
        body.ok ? "ok" : "down");
      return pvLoad().then(pvNotifyHost);
    }).catch(function (error) {
      mgSet(pvResult, "测试失败：" + error.message, "down");
    }).finally(function () { pvBusy(pvTestBtn, false); });
  });

  pvLoad();

    return {
      pvApiKey: pvApiKey,
      pvBaseUrl: pvBaseUrl,
      pvBusy: pvBusy,
      pvCollect: pvCollect,
      pvCurrent: pvCurrent,
      pvLoad: pvLoad,
      pvModel: pvModel,
      pvNotifyHost: pvNotifyHost,
      pvProfiles: pvProfiles,
      pvRenderTarget: pvRenderTarget,
      pvResult: pvResult,
      pvSave: pvSave,
      pvSaveBtn: pvSaveBtn,
      pvSelect: pvSelect,
      pvSwitchBtn: pvSwitchBtn,
      pvTarget: pvTarget,
      pvTestBtn: pvTestBtn,
    };
  }

  global.JzoStProvider = { create: create };
})(window);
