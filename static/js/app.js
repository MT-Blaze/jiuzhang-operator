(function () {
  "use strict";

  var statusEl = document.getElementById("health");
  var labelEl = statusEl ? statusEl.querySelector(".status-label") : null;
  var versionEl = document.getElementById("version");
  var timeEl = document.getElementById("health-time");

  function setState(state, label) {
    if (statusEl) statusEl.dataset.state = state;
    if (labelEl) labelEl.textContent = label;
  }

  function formatTime(iso) {
    var date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "时间未知";
    return date.toLocaleString("zh-CN", { hour12: false });
  }

  async function checkHealth() {
    try {
      var response = await fetch("/healthz", {
        cache: "no-store",
        headers: { Accept: "application/json" }
      });
      if (!response.ok) throw new Error("HTTP " + response.status);

      var data = await response.json();
      if (versionEl && data.version) versionEl.textContent = "v" + data.version;
      if (timeEl) timeEl.textContent = "底座时间 " + formatTime(data.time);
      setState("ok", "底座在线");
    } catch (error) {
      setState("down", "底座离线");
      if (timeEl) timeEl.textContent = "无法连接 /healthz";
    }
  }

  checkHealth();
  window.setInterval(checkHealth, 30000);
})();
