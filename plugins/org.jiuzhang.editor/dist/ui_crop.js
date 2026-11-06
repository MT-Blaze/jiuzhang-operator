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
    var splitFromCrop = deps.splitFromCrop;
    var stashOne = deps.stashOne;
    // 取图/解码/裁图/画布底层拆在同目录 ui_crop_io.js；本文件只管切图台状态机。
    var cropIo = global.JzoCropIo.create({ clampValue: clampValue, hostCall: hostCall });
    var cropFiles = cropIo.cropFiles;
    var cropPoint = cropIo.cropPoint;
    var cropRegionToDataUrl = cropIo.cropRegionToDataUrl;
    var dataUrlToBlob = cropIo.dataUrlToBlob;
    var decodePicture = cropIo.decodePicture;
    var drawCropCanvas = cropIo.drawCropCanvas;
    var loadPageBitmap = cropIo.loadPageBitmap;
    var stitchRegionsToDataUrl = cropIo.stitchRegionsToDataUrl;

  // ---------- 左栏切图：小口径放大镜 + 中心十字准星 ----------
  //
  // 镜窗直径只有 120px、镜内 1.2 倍：贴着光标偏移摆放，只够看清一两个公式符号，
  // 绝不挡住正在框的那一行字。镜心一根细红十字，告诉老师对准的是哪一处。
  // 左键松开，框选完成，镜子消失。
  //
  // 像素级精准的前提是画布干净：沙箱插件画不了宿主原点的图——画布会被污染，
  // toDataURL 直接抛 SecurityError。所以已有的配图走宿主 asset.read 递 data URL，
  // 老师现贴的图走 File：两条路拿到的都是不带污点的字节。
  var CROP_RADIUS = 60;      // 放大镜半径（CSS 像素）：直径 120px
  var CROP_ZOOM = 1.2;       // 镜内源像素倍率：小而清楚，不做满屏马赛克
  var CROP_MIN_SIDE = 4;     // 最小选区边长（CSS 像素）
  var crop = null;
  var lensCanvas = null;

  function cropAssetId() {
    return "img_crop_" + Math.random().toString(36).slice(2, 10);
  }

  /**
   * 切图台：左栏那一格变成一块画布，鼠标变十字，旁边跟一只放大镜。
   * ``autoSplit`` 用于纯图片卷的整卷页图：松开鼠标直接生成一道新题，不再问动作。
   */
  function openCrop(item, index, cell, autoSplit) {
    closeCrop();
    // closeCrop 会整屏重绘，格子节点换了新的：必须按序号重新找，别信调用方递进来的旧节点。
    cell = document.querySelector('.ed-img-cell[data-index="' + index + '"]') || cell;
    if (!cell) return;
    var session = {
      item: item,
      index: index,
      autoSplit: Boolean(autoSplit),
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
      hint: null,
      actions: null,
      pageNo: Number((item && item.pageImage && item.pageImage.page) || 0) || 1
    };
    crop = session;
    var hint = el("p", "ed-crop-hint", "正在取图…");
    session.hint = hint;
    cell.appendChild(hint);
    // 窗口级监听先绑上：图还没取回来的时候，粘贴与拖放也得能接住。
    window.addEventListener("mousemove", onCropMove, true);
    window.addEventListener("pointermove", onCropMove, true);
    window.addEventListener("mouseup", onCropUp, true);
    window.addEventListener("pointerup", onCropUp, true);
    window.addEventListener("pointercancel", onCropCancel, true);
    window.addEventListener("keydown", onCropKey, true);
    window.addEventListener("paste", onCropPaste, true);
    window.addEventListener("dragover", onCropDragOver, true);
    window.addEventListener("drop", onCropDrop, true);
    window.addEventListener("resize", onCropResize);
    var picture = itemImage(item);
    if (picture && picture.page) session.pageNo = Number(picture.page) || 1;
    var managed = picture && picture.uri.indexOf("/static/") === 0;
    if (!managed) {
      // 没有现成的托管图：等老师把卷子上的这一页贴进来或拖进来。
      mountCropSurface(session, null);
      return;
    }
    hostCall("asset.read", { uri: picture.uri }).then(function (result) {
      var blob = dataUrlToBlob(result && result.data_url, result && result.mime);
      return decodePicture(blob);
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
    window.removeEventListener("pointermove", onCropMove, true);
    window.removeEventListener("mouseup", onCropUp, true);
    window.removeEventListener("pointerup", onCropUp, true);
    window.removeEventListener("pointercancel", onCropCancel, true);
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
    if (session.actions && session.actions.parentNode) {
      session.actions.parentNode.removeChild(session.actions);
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
      // 指针与鼠标事件都接：指针事件负责触控与指针捕获，鼠标事件兜住老环境。
      // 两边都进来时只看第一次——session.dragging 已是 true 就直接忽略。
      var startDrag = function (event) {
        if (event.button !== 0 || !session.bitmap || session.dragging) return;
        event.preventDefault();
        hideCropActions(session);
        session.dragging = true;
        session.start = cropPoint(session, event.clientX, event.clientY);
        session.rect = null;
        if (canvas.setPointerCapture && event.pointerId != null) {
          try { canvas.setPointerCapture(event.pointerId); } catch (error) { /* 捕获失败也照常拖 */ }
        }
      };
      canvas.addEventListener("pointerdown", startDrag);
      canvas.addEventListener("mousedown", startDrag);
      // 松手后的 click 会冒泡到页图的「打开切图台」监听上：这里截断，
      // 否则切完一题立刻又开一个空台子，看起来就像「拖了没反应」。
      canvas.addEventListener("click", function (event) {
        event.stopPropagation();
      });
    }
    anchorCrop(session);
    ensureLens();
    session.lctx = lensCanvas.getContext("2d");
    resizeLens();
    session.hint.textContent = bitmap
      ? cropHint(session)
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
    // 只读绿框层让位给切图台：两套框叠在一起既看不清，也容易误认。
    var greens = frame.querySelector(".ed-green-layer");
    if (greens) greens.hidden = true;
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
    // 画布宽度必须与 <img width:100%> 一模一样，差几像素框选就会左右错位。
    // 量切图台所在的 .ed-img-frame，而不是量整栏再凭经验减 padding。
    var frame = canvas.parentNode && canvas.parentNode.classList
      && canvas.parentNode.classList.contains("ed-img-frame") ? canvas.parentNode : null;
    var body = document.getElementById("edImageBody");
    var frameWidth = frame && frame.clientWidth ? frame.clientWidth : 0;
    var maxWidth = Math.max(140, frameWidth || ((body ? body.clientWidth : 320) - 24));
    // 原图已经按 width:100% 铺满：小于栏宽的图同样放大到栏宽，画布跟着放，
    // 保证「看到的」与「裁到的」是同一块像素。
    var scale = session.width ? maxWidth / session.width : 1;
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
    if (session.actions && session.rect) positionActions(session);
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
    // 开平滑：2 倍取样下再关平滑就是马赛克。老师要看清公式，不是看像素格。
    ctx.imageSmoothingEnabled = true;
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
    // 指针离开画布就把镜子收掉：它只服务框选，不该飘到别的栏上挡字。
    if (px < box.left || px > box.right || py < box.top || py > box.bottom) return;
    var sx = (px - box.left) / session.scale;
    var sy = (py - box.top) / session.scale;
    // 镜子贴着指针右下偏移，撞到边就翻到另一侧；120px 的口径永远不压住光标下的字。
    var mx = px + radius + 18;
    var my = py + radius + 18;
    if (mx + radius > viewW - 8) mx = px - radius - 18;
    if (my + radius > viewH - 8) my = py - radius - 18;
    var half = radius / CROP_ZOOM;
    var ox = clampValue(sx - half, 0, Math.max(0, session.width - half * 2));
    var oy = clampValue(sy - half, 0, Math.max(0, session.height - half * 2));
    var sw = Math.max(1, Math.min(half * 2, session.width - ox));
    var sh = Math.max(1, Math.min(half * 2, session.height - oy));
    ctx.save();
    ctx.beginPath();
    ctx.arc(mx, my, radius, 0, Math.PI * 2);
    ctx.clip();
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(session.bitmap, ox, oy, sw, sh, mx - radius, my - radius, radius * 2, radius * 2);
    ctx.restore();
    ctx.strokeStyle = "rgba(255, 255, 255, 0.9)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(mx, my, radius, 0, Math.PI * 2);
    ctx.stroke();
    // 镜心准星：告诉老师放大的是哪一粒像素。
    ctx.strokeStyle = "rgba(255, 96, 96, 0.95)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(mx - 8, my + 0.5);
    ctx.lineTo(mx + 8, my + 0.5);
    ctx.moveTo(mx + 0.5, my - 8);
    ctx.lineTo(mx + 0.5, my + 8);
    ctx.stroke();
  }

  /**
   * 松开左键不等于切图：先把框留在图上，让老师选「配给本题」还是「切分新题」。
   * 无文本层的扫描卷就靠这一步把一页拆成十九道题。
   */
  function hideCropActions(session) {
    if (!session) return;
    if (session.actions && session.actions.parentNode) {
      session.actions.parentNode.removeChild(session.actions);
    }
    session.actions = null;
  }

  function positionActions(session) {
    var bar = session.actions;
    var rect = session.rect;
    if (!bar || !rect || !session.canvas) return;
    var width = bar.offsetWidth || 280;
    var height = bar.offsetHeight || 44;
    var top = rect.y + rect.h + 6;
    if (top + height > session.canvas.clientHeight) {
      top = Math.max(4, rect.y - height - 6);
    }
    var left = Math.max(4, Math.min(rect.x, (session.canvas.clientWidth || width) - width - 4));
    bar.style.top = Math.round(top) + "px";
    bar.style.left = Math.round(left) + "px";
  }

  function actionButton(label, primary, onClick) {
    var button = el("button", "ed-crop-action" + (primary ? " is-primary" : ""), label);
    button.type = "button";
    button.addEventListener("click", onClick);
    return button;
  }

  /** 中转站里、且还在一个批次里的格子才谈得上「切分新题」。 */
  function canSplitItem(item) {
    return Boolean(item && item.batchId && splitFromCrop && (item.pendingId || item.galleryPage));
  }

  /** 松开鼠标后的提示按真会给的动作说，别指着一颗不存在的按钮。 */
  function cropHint(session) {
    if (session.autoSplit) return "拖拽框选，松开鼠标即生成一道新题。Esc 取消。";
    if (canSplitItem(session.item)) {
      return "移动鼠标看像素，拖拽框选；松开后选【提取为本题配图】或【切分新题】。Esc 取消。";
    }
    return "移动鼠标看像素，拖拽框选；松开后点【提取为本题配图】。Esc 取消。";
  }

  function showCropActions(session) {
    hideCropActions(session);
    var rect = session && session.rect;
    var frame = session && session.canvas && session.canvas.parentNode;
    if (!rect || !frame) return;
    var bar = el("div", "ed-crop-actions");
    bar.setAttribute("role", "group");
    bar.setAttribute("aria-label", "框选之后要做什么");
    var canSplit = canSplitItem(session.item);
    var buttons = [actionButton("提取为本题配图", !canSplit, function () {
      finishCrop(session, "assign");
    })];
    if (canSplit) {
      buttons.push(actionButton("切分新题", true, function () {
        finishCrop(session, "split");
      }));
    }
    buttons.forEach(function (button) { bar.appendChild(button); });
    bar.appendChild(actionButton("取消", false, function () {
      session.rect = null;
      hideCropActions(session);
      drawCropCanvas(session);
      session.hint.textContent = "已取消这次框选，再拖一次。";
    }));
    frame.appendChild(bar);
    session.actions = bar;
    positionActions(session);
    var primary = bar.querySelector(".is-primary") || bar.firstChild;
    if (primary) primary.focus();
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
    // pointerup 与 mouseup 会先后各来一次：第一次就把 dragging 放下，第二次直接返回，
    // 保证「松手只切一刀」，也保证任何一条事件链丢了都还有另一条兜底。
    session.dragging = false;
    var rect = session.rect;
    if (!rect || rect.w < CROP_MIN_SIDE || rect.h < CROP_MIN_SIDE) {
      session.rect = null;
      drawCropCanvas(session);
      session.hint.textContent = "框太小了，再拖一次。";
      return;
    }
    if (session.autoSplit) {
      // 纯图片卷：松开即切，不再让老师点第二次。
      finishCrop(session, "split");
      return;
    }
    showCropActions(session);
  }

  function onCropCancel() {
    var session = crop;
    if (!session || !session.dragging) return;
    session.dragging = false;
    session.rect = null;
    session.hint.textContent = "这次拖拽被打断了，再拖一次。";
    drawCropCanvas(session);
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
      session.hint.textContent = cropHint(session);
    }, function (error) {
      session.hint.textContent = "这张图解不开（" + ((error && error.message) || "格式不支持") + "）。";
    });
  }

  /** 自动框确认切分：读页图 → 按坐标裁图 → 走与手动框选同一条切题通道。 */
  function splitPageRegion(item, region, info) {
    if (!splitFromCrop) return Promise.reject(new Error("切题通道没有接上"));
    if (!item || !item.batchId) return Promise.reject(new Error("当前页不在中转站批次里"));
    var picture = itemImage(item);
    if (!picture || !picture.uri) return Promise.reject(new Error("这一页的原卷图取不到"));
    return loadPageBitmap(picture.uri).then(function (bitmap) {
      var cropped = cropRegionToDataUrl(bitmap, region);
      if (!cropped) throw new Error("框选区域没有像素");
      var pageNo = Number(info && info.page) || Number(picture.page) || 1;
      return splitFromCrop(item, cropped.dataUrl, {
        width: cropped.width,
        height: cropped.height,
        page: pageNo
      });
    });
  }

  /** 跨页框确认切分：先把各页切片拼成一张题图，再走同一条切题通道。 */
  function splitSpanRegion(item, pieces) {
    if (!splitFromCrop) return Promise.reject(new Error("切题通道没有接上"));
    if (!item || !item.batchId) return Promise.reject(new Error("当前页不在中转站批次里"));
    if (!Array.isArray(pieces) || !pieces.length) {
      return Promise.reject(new Error("跨页框没有页面块"));
    }
    var picture = itemImage(item);
    var pageNo = Number(pieces[0] && pieces[0].pageNo)
      || Number(picture && picture.page) || 1;
    return stitchRegionsToDataUrl(pieces).then(function (stitched) {
      return splitFromCrop(item, stitched.dataUrl, {
        width: stitched.width,
        height: stitched.height,
        page: pageNo
      });
    });
  }

  /**
   * 已入池的绿框被老师拖过：按新坐标重切题图，原地更新那道待审题。
   * 读的必须是原卷页图（item.pageImage），不能走 itemImage——那会先拿到
   * 上一次切的题图，越调越糊。旧配图留在 pending_assets/，整批审完统一清。
   */
  function updatePageRegion(item, region, info) {
    if (!item || !item.pendingId) return Promise.reject(new Error("这一框没有对应的待审题"));
    if (!stashOne) return Promise.reject(new Error("存题通道没有接上"));
    var picture = item.pageImage;
    if (!picture || !picture.uri) return Promise.reject(new Error("这一页的原卷图取不到"));
    var pageNo = Number(info && info.page) || Number(picture.page) || 1;
    return loadPageBitmap(picture.uri).then(function (bitmap) {
      var cropped = cropRegionToDataUrl(bitmap, region);
      if (!cropped) throw new Error("框选区域没有像素");
      return applyStashedCrop(item, cropped, pageNo, "第 " + pageNo + " 页的框");
    });
  }

  /** 跨页绿框被拖过：重新拼一张题图，原地更新同一道待审题。 */
  function updateSpanRegion(item, pieces) {
    if (!item || !item.pendingId) return Promise.reject(new Error("这一框没有对应的待审题"));
    if (!stashOne) return Promise.reject(new Error("存题通道没有接上"));
    if (!Array.isArray(pieces) || !pieces.length) {
      return Promise.reject(new Error("跨页框没有页面块"));
    }
    var pageNo = Number(pieces[0] && pieces[0].pageNo)
      || Number(item.pageImage && item.pageImage.page) || 1;
    return stitchRegionsToDataUrl(pieces).then(function (stitched) {
      return applyStashedCrop(item, stitched, pageNo, "跨页题的框");
    });
  }

  /** 切图已经拿到手：换掉题图、存回中转站，单页与跨页共用这一段。 */
  function applyStashedCrop(item, cropped, pageNo, scope) {
    var assetId = cropAssetId();
    item.cropAsset = { id: assetId, data_url: cropped.dataUrl };
    item.question = item.question || {};
    // 只换这张自动切图，老师后来补的选项图 / 解析图一张都不丢。
    var previous = Array.isArray(item.question.images) ? item.question.images : null;
    var images = previous ? previous.slice() : [];
    var stemAt = -1;
    for (var index = 0; index < images.length; index += 1) {
      if (images[index] && images[index].role === "stem") { stemAt = index; break; }
    }
    if (stemAt < 0) { images.unshift(null); stemAt = 0; }
    images[stemAt] = { id: assetId, role: "stem", uri: "/static/uploads/" + assetId + ".png" };
    item.question.images = images;
    item.dirty = true;
    // 只换题图、不动正文：还没填题干也不该被拦下。
    return stashOne(item, metaFor(item, {}), true, true).then(function (outcome) {
      if (!outcome || !outcome.ok) {
        item.cropAsset = null;
        item.question.images = previous || [];
        throw new Error((outcome && outcome.message) || "题目没能存回中转站");
      }
      var saved = outcome.result && outcome.result.saved_assets && outcome.result.saved_assets[0];
      var asset = saved && saved.assets && saved.assets[0];
      if (asset && asset.uri && item.question.images[stemAt]) {
        item.question.images[stemAt].uri = asset.uri;
      }
      item.cropAsset = null;
      if (scheduleRender) scheduleRender();
      if (dock) {
        dock((scope || ("第 " + pageNo + " 页的框")) + "已微调，题图重切为 "
          + cropped.width + "×" + cropped.height + " 像素。");
      }
      return {
        uri: (asset && asset.uri) || "",
        width: cropped.width,
        height: cropped.height
      };
    });
  }

  /**
   * 老师选完动作才真正切：mode=assign 配给当前题，mode=split 另起一道待审题。
   * 截图像素按源图算，避免框选缩放后把题图裁小。
   */
  function finishCrop(session, mode) {
    var rect = session && session.rect;
    var scale = Number(session && session.scale);
    // 坐标换算一旦出 NaN，后端只会回一个看不懂的 400。这里当场拦下并说人话。
    if (!rect || !session.bitmap || !(scale > 0)
        || !isFinite(rect.x) || !isFinite(rect.y)
        || !isFinite(rect.w) || !isFinite(rect.h)) {
      if (session && session.hint) {
        session.hint.textContent = "这次框选的坐标没算出来，请再拖一次。";
      }
      session.dragging = false;
      return;
    }
    var sx = Math.round(rect.x / scale);
    var sy = Math.round(rect.y / scale);
    var sw = Math.max(CROP_MIN_SIDE, Math.round(rect.w / scale));
    var sh = Math.max(CROP_MIN_SIDE, Math.round(rect.h / scale));
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
    var pageNo = session.pageNo || 1;
    // 选完动作即收摊：放大镜与切图台当场撤掉，落库挪到后台慢慢办。
    closeCrop();
    if (mode === "split") {
      // 切分新题：这一块单独成一道待审题，题干留占位，老师接着在中间栏录入。
      if (!splitFromCrop) {
        dockWarn("切分新题不可用：录题工作台没有接上切题通道。");
        return;
      }
      splitFromCrop(item, dataUrl, { width: sw, height: sh, page: pageNo });
      return;
    }
    if (item.pendingId) {
      // 中转站里的题：字节随草稿一起进池子，配图落 pending_assets/，主库一个字节都不碰。
      item.cropAsset = { id: assetId, data_url: dataUrl };
      item.question.images = [{ id: assetId, role: "stem", uri: "/static/uploads/" + assetId + ".png" }];
      item.dirty = true;
      // 只补配图、不动题干：不能因为还没填答案就拒绝把图存进池子。
      stashOne(item, metaFor(item, {}), false, true).then(function (outcome) {
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
      cropRegionToDataUrl: cropRegionToDataUrl,
      dataUrlToBlob: dataUrlToBlob,
      loadPageBitmap: loadPageBitmap,
      splitPageRegion: splitPageRegion,
      splitSpanRegion: splitSpanRegion,
      updatePageRegion: updatePageRegion,
      updateSpanRegion: updateSpanRegion,
      drawCropCanvas: drawCropCanvas,
      drawLens: drawLens,
      ensureLens: ensureLens,
      finishCrop: finishCrop,
      layoutCrop: layoutCrop,
      lensCanvas: lensCanvas,
      mountCropSurface: mountCropSurface,
      onCropCancel: onCropCancel,
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
