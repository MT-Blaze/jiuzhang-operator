/* 九章算子最小 Service Worker：让 Chrome / Edge 把本站视为可安装应用。

   缓存策略是「完全不缓存」：
   - activate 时清空所有 Cache Storage，旧版本 SW 留下的旧页面就此死透；
   - 同源导航 / 脚本 / 样式一律绕过 HTTP 缓存走网络，杜绝「F5 拿旧 JS」；
   - 其余请求不拦截，交给浏览器默认处理。 */
self.addEventListener("install", function () {
  self.skipWaiting();
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys()
      .then(function (keys) {
        return Promise.all(keys.map(function (key) { return caches.delete(key); }));
      })
      .then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (event) {
  var request = event.request;
  if (request.method !== "GET") return;
  var url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  var dest = request.destination;
  if (dest !== "document" && dest !== "script" && dest !== "style" && dest !== "worker") return;
  event.respondWith(
    fetch(request, { cache: "no-store" }).catch(function () {
      return new Response("底座正在重启，请稍候刷新。", {
        status: 503,
        headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" }
      });
    })
  );
});
