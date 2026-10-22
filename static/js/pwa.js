(function () {
  "use strict";

  // 注册根作用域 Service Worker，让浏览器提供「安装为应用」入口。
  // 注册失败不影响使用：普通浏览器标签页仍然是完整功能。
  if (!("serviceWorker" in navigator) || location.protocol === "file:") return;

  window.addEventListener("load", function () {
    navigator.serviceWorker.register("/sw.js").catch(function () {});
  });
})();
