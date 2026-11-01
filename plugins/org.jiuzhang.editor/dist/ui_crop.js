/**
 * ui_crop.js —— plugin.js 的「1132」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var clampValue = deps.clampValue;
    var dock = deps.dock;
    var dockWarn = deps.dockWarn;
    var el = deps.el;
    var errorDetail = deps.errorDetail;
    var hostCall = deps.hostCall;
    var itemImage = deps.itemImage;
    var metaFor = deps.metaFor;
    var renderAll = deps.renderAll;
    var scheduleRender = deps.scheduleRender;
    var stashOne = deps.stashOne;

  // ---------- 左栏切图：圆形放大镜 + 中心十字准星 ----------
  //
  // 放大镜是从宿主壳那套截屏交互里原样搬过来的：半径 104、8 倍、关平滑看像素，
  // 镜心一根红十字。只是它不再跟着屏幕走，而是跟着老师在左栏那张图上的鼠标走；
  // 左键松开，框选完成，镜子消失。
  //
  // 像素级精准的前提是画布干净：沙箱插件画不了宿主原点的图——画布会被污染，
  // toDataURL 直接抛 SecurityError。所以已有的配图走宿主 asset.read 递 data URL，
  // 老师现贴的图走 File：两条路拿到的都是不带污点的字节。
  var CROP_RADIUS = 104;     // 放大镜半径（CSS 像素）
  var CROP_ZOOM = 8;         // 放大倍数
  var CROP_MIN_SIDE = 4;     // 最小选区边长（CSS 像素）
  var crop = null;
  var lensCanvas = null;

  function cropAssetId() {
    return "img_crop_" + Math.random().toString(36).slice(2, 10);
  }

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

  /** 切图台：左栏那一格变成一块画布，鼠标变十字，旁边跟一只放大镜。 */
  function openCrop(item, index) {
    closeCrop();
    // closeCrop 会整屏重绘，格子节点换了新的：这里按序号重新找，别拿旧的。
    var cell = document.querySelector('.ed-img-cell[data-index="' + index + '"]');
    if (!cell) return;
    var session = {
      item: item,
      index: index,
      cell: cell,
      bitmap: null,
      width: 0,
      height: 0,
      scale: 1,
      dpr: 1,
      rect: null,
      dragging: false,
      start: null,
      pointer: { x: 0, y: 0 },
      canvas: null,
      ctx: null,
      lens: null,
      lctx: null,
      hint: null
    };
    crop = session;
    var hint = el("p", "ed-crop-hint", "正在取图…");
    session.hint = hint;
    cell.appendChild(hint);
    // 窗口级监听先绑上：图还没取回来的时候，粘贴与拖放也得能接住。
    window.addEventListener("mousemove", onCropMove, true);
    window.addEventListener("mouseup", onCropUp, true);
    window.addEventListener("keydown", onCropKey, true);
    window.addEventListener("paste", onCropPaste, true);
    window.addEventListener("dragover", onCropDragOver, true);
    window.addEventListener("drop", onCropDrop, true);
    window.addEventListener("resize", onCropResize);
    var picture = itemImage(item);
    var managed = picture && picture.uri.indexOf("/static/") === 0;
    if (!managed) {
      // 没有现成的托管图：等老师把卷子上的这一页贴进来或拖进来。
      mountCropSurface(session, null);
      return;
    }
    hostCall("asset.read", { uri: picture.uri }).then(function (result) {
      var blob = dataUrlToBlob(result && result.data_url, result && result.mime);
      return window.createImageBitmap(blob);
    }).then(function (bitmap) {
      mountCropSurface(session, bitmap);
    }, function (error) {
      hint.textContent = "这张图取不出来（" + ((error && error.message) || "未知原因") + "）。";
    });
  }

  /** 收摊：放大镜撤掉，画布撤掉，这一格回到普通态。 */
  function closeCrop() {
    if (!crop) return;
    var session = crop;
    crop = null;
    window.removeEventListener("mousemove", onCropMove, true);
    window.removeEventListener("mouseup", onCropUp, true);
    window.removeEventListener("keydown", onCropKey, true);
    window.removeEventListener("paste", onCropPaste, true);
    window.removeEventListener("dragover", onCropDragOver, true);
    window.removeEventListener("drop", onCropDrop, true);
    window.removeEventListener("resize", onCropResize);
    if (session.canvas && session.canvas.parentNode) {
      session.canvas.parentNode.removeChild(session.canvas);
    }
    if (session.hint && session.hint.parentNode) {
      session.hint.parentNode.removeChild(session.hint);
    }
    if (lensCanvas) {
      if (lensCanvas.parentNode) lensCanvas.parentNode.removeChild(lensCanvas);
      lensCanvas = null;
    }
    if (session.bitmap && typeof session.bitmap.close === "function") {
      session.bitmap.close();
    }
    renderAll();
  }

  function mountCropSurface(session, bitmap) {
    if (bitmap) {
      if (session.bitmap && typeof session.bitmap.close === "function") session.bitmap.close();
      session.bitmap = bitmap;
      session.width = bitmap.width;
      session.height = bitmap.height;
    }
    if (!session.canvas) {
      var canvas = document.createElement("canvas");
      canvas.className = "ed-crop-canvas";
      canvas.setAttribute("aria-label", "切图台：拖拽框选，左键松开切图");
      session.canvas = canvas;
      session.ctx = canvas.getContext("2d");
      canvas.addEventListener("mousedown", function (event) {
        if (event.button !== 0 || !session.bitmap) return;
        event.preventDefault();
        session.dragging = true;
        session.start = cropPoint(session, event.clientX, event.clientY);
        session.rect = null;
      });
    }
    anchorCrop(session);
    ensureLens();
    session.lctx = lensCanvas.getContext("2d");
    resizeLens();
    session.hint.textContent = bitmap
      ? "移动鼠标看像素，拖拽框选，左键松开切图；Esc 取消。"
      : "把卷子上的这一页 Ctrl+V 贴进来（或拖进来），再拖拽框选。";
  }

  /**
   * 切图台要跟着格子走。
   *
   * 画布上有个 ResizeObserver：切图台一挂上去，格子高度变了，它就排一次整屏重绘，
   * 重绘把格子换成了新的——切图台若还攥着旧格子，画布就掉进了一个没人看得见的
   * 树里（症状：镜子在，格子上的画布不见了）。所以每次重绘后都要把画布与提示
   * 搬回当前这一格。
   *
   * 搬的动作必须和重绘在同一个任务里做完：ResizeObserver 只在帧末比一次尺寸，
   * 中间塌下去又撑回来的那一下它根本看不见——也就不会自己绕成死循环。
   */
  function anchorCrop(session) {
    if (!session) return;
    var cell = document.querySelector('.ed-img-cell[data-index="' + session.index + '"]');
    if (!cell) return;
    var frame = cell.querySelector(".ed-img-frame");
    if (!frame) return;
    var img = frame.querySelector("img");
    if (img) img.hidden = true;
    var box = frame.querySelector(".ed-img-box");
    if (box) box.hidden = true;
    if (session.canvas && session.canvas.parentNode !== frame) {
      if (session.canvas.parentNode) session.canvas.parentNode.removeChild(session.canvas);
      frame.insertBefore(session.canvas, frame.firstChild);
    }
    if (session.hint && session.hint.parentNode !== cell) {
      if (session.hint.parentNode) session.hint.parentNode.removeChild(session.hint);
      cell.appendChild(session.hint);
    }
    session.cell = cell;
    layoutCrop(session);
  }

  function layoutCrop(session) {
    var canvas = session.canvas;
    if (!canvas) return;
    var body = document.getElementById("edImageBody");
    var maxWidth = Math.max(140, (body ? body.clientWidth : 320) - 24);
    var scale = session.width ? Math.min(1, maxWidth / session.width) : 1;
    session.scale = scale;
    // 图还没贴进来时给一块看得见的空台子，不然画布只有 1×1 像素，像坏了。
    var displayW = session.width ? Math.max(1, Math.round(session.width * scale))
                                 : Math.min(maxWidth, 360);
    var displayH = session.height ? Math.max(1, Math.round(session.height * scale))
                                   : Math.round(displayW * 0.62);
    var dpr = Math.min(2, window.devicePixelRatio || 1);
    session.dpr = dpr;
    // 尺寸没变就别再动 canvas.width：改了会重置 2D 上下文，画布高度也会抖一下，
    // 抖一下就撞上 ResizeObserver → 整屏重绘 → 再抖一下。
    var pixelW = Math.round(displayW * dpr);
    var pixelH = Math.round(displayH * dpr);
    if (canvas.width !== pixelW || canvas.height !== pixelH) {
      canvas.width = pixelW;
      canvas.height = pixelH;
    }
    canvas.style.width = displayW + "px";
    canvas.style.height = displayH + "px";
    drawCropCanvas(session);
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
    ctx.fillStyle = "rgba(6, 8, 12, 0.42)";
    ctx.fillRect(0, 0, displayW, displayH);
    ctx.fillStyle = "rgba(255, 255, 255, 0.08)";
    ctx.fillRect(rect.x, rect.y, rect.w, rect.h);
    ctx.strokeStyle = "#2f6b4f";
    ctx.lineWidth = 1;
    ctx.strokeRect(rect.x + 0.5, rect.y + 0.5, rect.w, rect.h);
  }

  /** 放大镜层：整屏一块画布，镜子跟着鼠标走，镜心一根红十字。 */
  function ensureLens() {
    if (lensCanvas) return lensCanvas;
    lensCanvas = document.createElement("canvas");
    lensCanvas.className = "ed-crop-lens";
    lensCanvas.setAttribute("aria-hidden", "true");
    document.body.appendChild(lensCanvas);
    resizeLens();
    return lensCanvas;
  }

  function resizeLens() {
    if (!lensCanvas) return;
    var dpr = Math.min(2, window.devicePixelRatio || 1);
    lensCanvas.width = Math.max(1, Math.floor(window.innerWidth * dpr));
    lensCanvas.height = Math.max(1, Math.floor(window.innerHeight * dpr));
    lensCanvas.style.width = window.innerWidth + "px";
    lensCanvas.style.height = window.innerHeight + "px";
    var ctx = lensCanvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.imageSmoothingEnabled = false;
    if (crop) crop.lctx = ctx;
  }

  function drawLens(session) {
    var ctx = session.lctx;
    if (!ctx) return;
    var viewW = window.innerWidth;
    var viewH = window.innerHeight;
    ctx.setTransform(session.dpr || 1, 0, 0, session.dpr || 1, 0, 0);
    ctx.clearRect(0, 0, viewW, viewH);
    if (!session.bitmap || !session.canvas) return;
    var radius = CROP_RADIUS;
    var px = session.pointer.x;
    var py = session.pointer.y;
    var box = session.canvas.getBoundingClientRect();
    var sx = (px - box.left) / session.scale;
    var sy = (py - box.top) / session.scale;
    // 镜子默认在鼠标右下边，撞到边就翻到另一侧。
    var mx = px + radius + 28;
    var my = py + radius + 28;
    if (mx + radius > viewW - 8) mx = px - radius - 28;
    if (my + radius > viewH - 8) my = py - radius - 28;
    var half = radius / CROP_ZOOM;
    var ox = clampValue(sx - half, 0, Math.max(0, session.width - half * 2));
    var oy = clampValue(sy - half, 0, Math.max(0, session.height - half * 2));
    var sw = Math.max(1, Math.min(half * 2, session.width - ox));
    var sh = Math.max(1, Math.min(half * 2, session.height - oy));
    ctx.save();
    ctx.beginPath();
    ctx.arc(mx, my, radius, 0, Math.PI * 2);
    ctx.clip();
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(session.bitmap, ox, oy, sw, sh, mx - radius, my - radius, radius * 2, radius * 2);
    ctx.restore();
    ctx.strokeStyle = "rgba(255, 255, 255, 0.92)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(mx, my, radius, 0, Math.PI * 2);
    ctx.stroke();
    // 镜心准星：告诉老师放大的是哪一粒像素。
    ctx.strokeStyle = "rgba(255, 96, 96, 0.95)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(mx - 12, my + 0.5);
    ctx.lineTo(mx + 12, my + 0.5);
    ctx.moveTo(mx + 0.5, my - 12);
    ctx.lineTo(mx + 0.5, my + 12);
    ctx.stroke();
  }

  function cropPoint(session, clientX, clientY) {
    var box = session.canvas.getBoundingClientRect();
    return {
      x: clampValue(clientX - box.left, 0, box.width),
      y: clampValue(clientY - box.top, 0, box.height)
    };
  }

  function onCropResize() {
    var session = crop;
    if (!session) return;
    layoutCrop(session);
    resizeLens();
    drawLens(session);
  }

  function onCropMove(event) {
    var session = crop;
    if (!session) return;
    session.pointer.x = event.clientX;
    session.pointer.y = event.clientY;
    if (session.dragging && session.bitmap) {
      var point = cropPoint(session, event.clientX, event.clientY);
      session.rect = {
        x: Math.min(session.start.x, point.x),
        y: Math.min(session.start.y, point.y),
        w: Math.abs(point.x - session.start.x),
        h: Math.abs(point.y - session.start.y)
      };
      drawCropCanvas(session);
    }
    drawLens(session);
  }

  function onCropUp(event) {
    var session = crop;
    if (!session || !session.dragging) return;
    if (event.button !== 0) return;
    session.dragging = false;
    var rect = session.rect;
    if (!rect || rect.w < CROP_MIN_SIDE || rect.h < CROP_MIN_SIDE) {
      session.rect = null;
      drawCropCanvas(session);
      session.hint.textContent = "框太小了，再拖一次。";
      return;
    }
    finishCrop(session);
  }

  function onCropKey(event) {
    if (!crop) return;
    if (event.key !== "Escape") return;
    event.preventDefault();
    closeCrop();
  }

  function onCropPaste(event) {
    var session = crop;
    if (!session) return;
    var files = cropFiles(event);
    if (!files.length) return;
    event.preventDefault();
    event.stopPropagation();
    adoptCropFile(session, files[0]);
  }

  function onCropDragOver(event) {
    if (!crop) return;
    event.preventDefault();
  }

  function onCropDrop(event) {
    var session = crop;
    if (!session) return;
    var files = (event.dataTransfer && event.dataTransfer.files) || [];
    if (!files.length) return;
    event.preventDefault();
    event.stopPropagation();
    for (var index = 0; index < files.length; index += 1) {
      if (String(files[index].type || "").indexOf("image/") === 0) {
        adoptCropFile(session, files[index]);
        return;
      }
    }
  }

  /** 贴/拖进来的图直接顶替当前那张——老师要「重新框选」时常常是换一张新的。 */
  function adoptCropFile(session, file) {
    session.hint.textContent = "正在解码这张图…";
    window.createImageBitmap(file).then(function (bitmap) {
      if (!crop || crop !== session) {
        if (typeof bitmap.close === "function") bitmap.close();
        return;
      }
      if (session.bitmap && typeof session.bitmap.close === "function") session.bitmap.close();
      session.bitmap = bitmap;
      session.width = bitmap.width;
      session.height = bitmap.height;
      layoutCrop(session);
      session.hint.textContent = "移动鼠标看像素，拖拽框选，左键松开切图；Esc 取消。";
    }, function (error) {
      session.hint.textContent = "这张图解不开（" + ((error && error.message) || "格式不支持") + "）。";
    });
  }

  /** 松手：按源像素切一块，交给底座落盘，再把题面里的配图换过去。 */
  function finishCrop(session) {
    var rect = session.rect;
    var sx = Math.round(rect.x / session.scale);
    var sy = Math.round(rect.y / session.scale);
    var sw = Math.max(CROP_MIN_SIDE, Math.round(rect.w / session.scale));
    var sh = Math.max(CROP_MIN_SIDE, Math.round(rect.h / session.scale));
    sx = clampValue(sx, 0, Math.max(0, session.width - 1));
    sy = clampValue(sy, 0, Math.max(0, session.height - 1));
    sw = clampValue(sw, 1, session.width - sx);
    sh = clampValue(sh, 1, session.height - sy);
    var out = document.createElement("canvas");
    out.width = sw;
    out.height = sh;
    var octx = out.getContext("2d");
    octx.imageSmoothingEnabled = false;
    octx.drawImage(session.bitmap, sx, sy, sw, sh, 0, 0, sw, sh);
    var dataUrl;
    try {
      dataUrl = out.toDataURL("image/png");
    } catch (error) {
      closeCrop();
      dockWarn("切图失败：画布被污染，取不到像素。");
      return;
    }
    var item = session.item;
    var assetId = cropAssetId();
    // 松手即收摊：放大镜与切图台当场撤掉，落库挪到后台慢慢办。
    // 军令原话是「直到左键松开，框选完成，放大镜消失」——镜子不能在等回执的
    // 那两秒里还杵在屏幕上。
    closeCrop();
    if (item.pendingId) {
      // 中转站里的题：字节随草稿一起进池子，配图落 pending_assets/，主库一个字节都不碰。
      item.cropAsset = { id: assetId, data_url: dataUrl };
      item.question.images = [{ id: assetId, role: "stem", uri: "/static/uploads/" + assetId + ".png" }];
      item.dirty = true;
      stashOne(item, metaFor(item, {}), false).then(function (outcome) {
        if (!outcome || !outcome.ok) {
          dockWarn("切图没能存进中转站：" + ((outcome && outcome.message) || "未知原因"),
            (outcome && outcome.detail) || "");
          return;
        }
        var saved = outcome.result && outcome.result.saved_assets && outcome.result.saved_assets[0];
        var asset = saved && saved.assets && saved.assets[0];
        if (asset && asset.uri && item.question.images && item.question.images[0]) {
          item.question.images[0].uri = asset.uri;
        }
        // 字节已经进池子了：清掉，免得下一次保存又写一份重复的配图。
        item.cropAsset = null;
        scheduleRender();
        dock("切图已存进中转站（" + sw + "×" + sh + " 像素）。");
      });
      return;
    }
    // 题库里的题：先让底座把字节收进 uploads/，再把题面里的 uri 换过去。
    hostCall("asset.upload", { data_url: dataUrl }).then(function (result) {
      item.question.images = [{ id: result.id, role: "stem", uri: result.uri }];
      item.dirty = true;
      scheduleRender();
      dock("切图已存进题库（" + sw + "×" + sh + " 像素）。");
    }, function (error) {
      dockWarn("切图没存住：" + ((error && error.message) || "未知原因"), errorDetail(error));
    });
  }

    return {
      CROP_MIN_SIDE: CROP_MIN_SIDE,
      CROP_RADIUS: CROP_RADIUS,
      CROP_ZOOM: CROP_ZOOM,
      adoptCropFile: adoptCropFile,
      // 重绘后把切图台搬回当前格子；session 是本模块的私产，绝不按值交出去。
      reanchor: function () { anchorCrop(crop); },
      closeCrop: closeCrop,
      // 切图台开没开：外面只问这一句，不许按值把 session 拿走。
      isOpen: function () { return Boolean(crop); },
      cropAssetId: cropAssetId,
      cropFiles: cropFiles,
      cropPoint: cropPoint,
      dataUrlToBlob: dataUrlToBlob,
      drawCropCanvas: drawCropCanvas,
      drawLens: drawLens,
      ensureLens: ensureLens,
      finishCrop: finishCrop,
      layoutCrop: layoutCrop,
      lensCanvas: lensCanvas,
      mountCropSurface: mountCropSurface,
      onCropDragOver: onCropDragOver,
      onCropDrop: onCropDrop,
      onCropKey: onCropKey,
      onCropMove: onCropMove,
      onCropPaste: onCropPaste,
      onCropResize: onCropResize,
      onCropUp: onCropUp,
      openCrop: openCrop,
      resizeLens: resizeLens,
    };
  }

  global.JzoEditorCrop = { create: create };
})(window);
