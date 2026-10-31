(function () {
  "use strict";

  // 注册根作用域 Service Worker，让浏览器提供「安装为应用」入口。
  // 注册失败不影响使用：普通浏览器标签页仍然是完整功能。
  if (!("serviceWorker" in navigator) || location.protocol === "file:") return;

  window.addEventListener("load", function () {
    // updateViaCache: "none" 让浏览器每次都对 sw.js 回源；SW 自身也不缓存任何响应，
    // 并在 activate 时清空旧 Cache Storage，杜绝「F5 拿旧页面、Ctrl+F5 才好」。
    navigator.serviceWorker.register("/sw.js", { updateViaCache: "none" }).catch(function () {});
  });
})();
