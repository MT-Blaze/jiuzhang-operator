/* 九章算子最小 Service Worker：让 Chrome / Edge 把本站视为可安装应用。
   只做网络透传，不缓存任何响应，避免「装完应用还在看旧页面」。 */
self.addEventListener("install", function () {
  self.skipWaiting();
});

self.addEventListener("activate", function (event) {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", function () {});
