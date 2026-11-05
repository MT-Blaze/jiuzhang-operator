/**
 * ui_crop_io.js —— 切图台的「取图 / 解码 / 裁图 / 画布」底层
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 只处理字节与画布，不认切图台的状态机：会话、事件、动作条仍在 ui_crop.js。
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰别的 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var clampValue = deps.clampValue;
    var hostCall = deps.hostCall;
    // 原卷页解码一次就够：一页上要接连确认十九个框，不能每点一次都重解几 MB 的 PNG。
    var pageBitmaps = {};
    var PAGE_BITMAP_LIMIT = 4;

    /** data URL → Blob。插件侧禁用 fetch（契约红线），只能用 atob 造字节。 */
    function dataUrlToBlob(dataUrl, mime) {
      var text = String(dataUrl || "");
      var comma = text.indexOf(",");
      var payload = comma >= 0 ? text.slice(comma + 1) : "";
      var binary = window.atob(payload);
      var bytes = new Uint8Array(binary.length);
      for (var index = 0; index < binary.length; index += 1) {
        bytes[index] = binary.charCodeAt(index);
      }
      return new Blob([bytes], { type: mime || "image/png" });
    }

    /**
     * Blob → 能画上 canvas 的图。
     * 只走 createImageBitmap：沙箱 CSP 不放 blob:/data:，`<img>` 那条路走不通；
     * 需要解码的图一律是底座托管的 PNG/JPEG/WebP，没有 SVG。
     */
    function decodePicture(blob) {
      if (typeof window.createImageBitmap !== "function") {
        return Promise.reject(new Error("当前环境不支持图片解码"));
      }
      return window.createImageBitmap(blob);
    }

    function cropFiles(event) {
      var data = event && event.clipboardData;
      if (!data) return [];
      var files = [];
      var items = data.items || [];
      for (var index = 0; index < items.length; index += 1) {
        if (items[index].kind !== "file") continue;
        var file = items[index].getAsFile();
        if (file && String(file.type || "").indexOf("image/") === 0) files.push(file);
      }
      var listed = data.files || [];
      for (var j = 0; j < listed.length; j += 1) {
        var each = listed[j];
        if (each && String(each.type || "").indexOf("image/") === 0) files.push(each);
      }
      return files;
    }

    function drawCropCanvas(session) {
      var ctx = session.ctx;
      var canvas = session.canvas;
      if (!ctx || !canvas) return;
      var dpr = session.dpr || 1;
      var displayW = canvas.width / dpr;
      var displayH = canvas.height / dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, displayW, displayH);
      if (!session.bitmap) return;
      ctx.drawImage(session.bitmap, 0, 0, displayW, displayH);
      var rect = session.rect;
      if (!rect) return;
      // 框外压暗、框内提亮，四周再描一圈 2px 绿线：半透明选框一眼可见。
      ctx.fillStyle = "rgba(6, 8, 12, 0.38)";
      ctx.fillRect(0, 0, displayW, displayH);
      ctx.fillStyle = "rgba(255, 255, 255, 0.14)";
      ctx.fillRect(rect.x, rect.y, rect.w, rect.h);
      ctx.strokeStyle = "#2f6b4f";
      ctx.lineWidth = 2;
      ctx.strokeRect(rect.x + 1, rect.y + 1, Math.max(0, rect.w - 2), Math.max(0, rect.h - 2));
    }

    function cropPoint(session, clientX, clientY) {
      var box = session.canvas.getBoundingClientRect();
      return {
        x: clampValue(clientX - box.left, 0, box.width),
        y: clampValue(clientY - box.top, 0, box.height)
      };
    }

    /** 原卷页位图按 uri 缓存：一页要接连确认十几道题，不能每次都重解几 MB 的 PNG。 */
    function loadPageBitmap(uri) {
      if (pageBitmaps[uri]) return pageBitmaps[uri];
      var pending = hostCall("asset.read", { uri: uri }).then(function (result) {
        if (!result || !result.data_url) throw new Error("这张原卷图读不出来");
        return decodePicture(dataUrlToBlob(result.data_url, result.mime));
      });
      pageBitmaps[uri] = pending;
      pending.then(null, function () { delete pageBitmaps[uri]; });
      var keys = Object.keys(pageBitmaps);
      if (keys.length > PAGE_BITMAP_LIMIT) {
        keys.slice(0, keys.length - PAGE_BITMAP_LIMIT).forEach(function (stale) {
          if (stale === uri) return;
          pageBitmaps[stale].then(function (bitmap) {
            if (bitmap && typeof bitmap.close === "function") bitmap.close();
          }, function () { /* 没解成功的本来就没有位图要关 */ });
          delete pageBitmaps[stale];
        });
      }
      return pending;
    }

    /** 按页面图像素坐标裁一块 PNG：自动切分框的【确认切分】走这里。 */
    function cropRegionToDataUrl(bitmap, region) {
      var width = Number(bitmap.width) || 0;
      var height = Number(bitmap.height) || 0;
      var sx = Math.round(Number(region && region.x) || 0);
      var sy = Math.round(Number(region && region.y) || 0);
      var sw = Math.round(Number(region && region.w) || 0);
      var sh = Math.round(Number(region && region.h) || 0);
      if (!(width > 0 && height > 0) || !(sw > 0 && sh > 0)) return null;
      sx = clampValue(sx, 0, Math.max(0, width - 1));
      sy = clampValue(sy, 0, Math.max(0, height - 1));
      sw = clampValue(sw, 1, width - sx);
      sh = clampValue(sh, 1, height - sy);
      var out = document.createElement("canvas");
      out.width = sw;
      out.height = sh;
      var octx = out.getContext("2d");
      octx.imageSmoothingEnabled = false;
      octx.drawImage(bitmap, sx, sy, sw, sh, 0, 0, sw, sh);
      return { dataUrl: out.toDataURL("image/png"), width: sw, height: sh };
    }

    return {
      PAGE_BITMAP_LIMIT: PAGE_BITMAP_LIMIT,
      cropFiles: cropFiles,
      cropPoint: cropPoint,
      cropRegionToDataUrl: cropRegionToDataUrl,
      dataUrlToBlob: dataUrlToBlob,
      decodePicture: decodePicture,
      drawCropCanvas: drawCropCanvas,
      loadPageBitmap: loadPageBitmap
    };
  }

  global.JzoCropIo = { create: create };
})(window);
