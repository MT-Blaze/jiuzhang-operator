/**
 * 录入入口（宿主壳）：拖入的文件、粘贴的截图、屏幕截取。
 *
 * 为什么落在宿主而不是插件里：拖拽与粘贴事件**不跨 iframe 边界**，插件沙箱里的
 * iframe 收不到工作台上的拖放；写令牌也只在宿主手里（AGENTS §2 铁律二、§5 安全）。
 * 于是插件把字节交给宿主，宿主代发——口径只有一处：
 * `POST /api/ingest/files` → 中转站里新建一批待审题。
 *
 * 分拣只看后缀（app/core/ingest.py）：文本类轻量解析、PDF 尽力抽文本层、
 * 图片走 OCR；`.zip` 静默忽略——插件安装包走的是另一条道，不进中转站也不提示。
 *
 * 截屏：浏览器没有系统级截屏 API（本项目没有桌面壳，见 docs/tauri-assessment.md），
 * 这里借 getDisplayMedia 取屏幕或窗口画面，在视口上盖一层变暗的实时画面，
 * 鼠标旁跟一个圆形放大镜（中心带十字准星，放大时关掉平滑，像素看得见），
 * 左键松开即截。被拒时由宿主自己画一个确认框：请用户亲手点一下——
 * 那一刻宿主文档才拿到用户手势，浏览器才肯开屏。
 */
(function () {
  "use strict";

  var INGEST_URL = "/api/ingest/files";
  var MAX_FILES = 20;
  var MAX_FILE_BYTES = 32 * 1024 * 1024;
  var MAGNIFY_RADIUS = 104;   // 放大镜半径（CSS 像素）
  var MAGNIFY_ZOOM = 8;       // 放大倍数
  var CROP_WIDTH = 1100;      // 截下来的那一块的宽（视频像素）
  var CROP_HEIGHT = 760;

  var capturing = false;
  var writeQueue = Promise.resolve();

  // ---------- 通用小工具 ----------

  function dock(text, tone) {
    if (!window.JzoBus || typeof window.JzoBus.emit !== "function") return;
    window.JzoBus.emit("region.dock", {
      text: String(text || "").slice(0, 300),
      topic: tone === "warn" ? "host.warn" : "host.notice"
    });
  }

  function suffixOf(name) {
    var text = String(name || "");
    var dot = text.lastIndexOf(".");
    return dot < 0 ? "" : text.slice(dot).toLowerCase();
  }

  function isZip(name) {
    return suffixOf(name) === ".zip";
  }

  function pad2(value) {
    return (value < 10 ? "0" : "") + value;
  }

  function shotName() {
    var now = new Date();
    return "截图-" + now.getFullYear() + pad2(now.getMonth() + 1) + pad2(now.getDate())
      + "-" + pad2(now.getHours()) + pad2(now.getMinutes()) + pad2(now.getSeconds()) + ".png";
  }

  function readAsDataUrl(file) {
    return new Promise(function (resolve, reject) {
      var reader = new FileReader();
      reader.onload = function () { resolve(String(reader.result || "")); };
      reader.onerror = function () {
        reject(new Error("读取文件失败：" + (file && file.name ? file.name : "未命名")));
      };
      reader.readAsDataURL(file);
    });
  }

  function dataUrlToFile(dataUrl, name) {
    var parts = String(dataUrl || "").split(",");
    var mime = (String(parts[0] || "").match(/data:([^;]+)/) || [])[1] || "image/png";
    var binary = atob(parts[1] || "");
    var bytes = new Uint8Array(binary.length);
    for (var i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    return new File([bytes], name || shotName(), { type: mime });
  }

  // ---------- 写通道：一次性令牌永远在宿主侧 ----------

  function postJson(url, body) {
    return fetch("/api/settings", { cache: "no-store" })
      .then(function (response) { return response.json(); })
      .then(function (data) {
        var token = data && data.local_token;
        if (!token) throw new Error("拿不到本地写操作令牌");
        return fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-JZO-Token": token },
          body: JSON.stringify(body)
        });
      })
      .then(function (response) {
        return response.text().then(function (text) {
          var data = null;
          try { data = text ? JSON.parse(text) : {}; } catch (error) { data = null; }
          if (!response.ok) {
            var detail = data && data.detail;
            var message = typeof detail === "string" ? detail
              : (detail && detail.message) || ("宿主接口返回 HTTP " + response.status);
            throw new Error(message);
          }
          return data || {};
        });
      });
  }

  /** 写操作排队：令牌用后即焚，两个写同时打出去必有一个被拒。 */
  function serialize(task) {
    var next = writeQueue.then(task, task);
    writeQueue = next.then(function () {}, function () {});
    return next;
  }

  function announce(result) {
    var batchId = String((result && result.batch_id) || "");
    var saved = Array.isArray(result && result.saved_ids) ? result.saved_ids.length : 0;
    var warnings = Array.isArray(result && result.warnings) ? result.warnings : [];
    if (batchId) {
      window.JzoBus.emit("system.pending_updated", {
        action: "ingest",
        pending_ids: (result.saved_ids || []).map(function (id) { return String(id); }),
        batch_id: batchId,
        pluginId: ""
      });
    }
    if (saved) {
      dock("已入池 " + saved + " 道题（批次 " + batchId + "），去批次列表里审。");
    } else if (warnings.length) {
      dock("没有认出题目：" + warnings[0], "warn");
    } else {
      dock("这次没能从文件里认出题目。", "warn");
    }
    warnings.forEach(function (text) { dock(String(text), "warn"); });
  }

  /**
   * 入库一批文件条目（``{name, data_url}``）。
   * 插件转发与宿主自己拖进来的文件走同一个函数，队列与令牌口径只有一处。
   */
  function ingestEntries(entries, options) {
    var opts = options || {};
    var prepared = [];
    var oversized = 0;
    for (var i = 0; i < (entries || []).length; i += 1) {
      var entry = entries[i] || {};
      var name = String(entry.name || "").slice(0, 120);
      var dataUrl = typeof entry.data_url === "string" ? entry.data_url : "";
      if (!name || !dataUrl) continue;
      if (dataUrl.length > 48 * 1024 * 1024) { oversized += 1; continue; }
      prepared.push({ name: name, data_url: dataUrl });
      if (prepared.length >= MAX_FILES) break;
    }
    if (!prepared.length) {
      return Promise.resolve({ skipped: true, warnings: oversized ? ["文件超过 32 MB 上限。"] : [] });
    }
    return serialize(function () {
      return postJson(INGEST_URL, { files: prepared });
    }).then(function (result) {
      if (opts.silent !== true) announce(result);
      return result;
    });
  }

  /** 宿主自己拿到的 File 对象 → 入库。``.zip`` 静默忽略：不提示、不建批次。 */
  function ingestFiles(fileList, options) {
    var opts = options || {};
    var files = Array.prototype.slice.call(fileList || []);
    var docs = [];
    var ignored = 0;
    var oversized = 0;
    for (var i = 0; i < files.length; i += 1) {
      var file = files[i];
      if (!file) continue;
      if (isZip(file.name)) { ignored += 1; continue; }
      if (file.size > MAX_FILE_BYTES) { oversized += 1; continue; }
      docs.push(file);
    }
    if (!docs.length) {
      if (oversized && opts.silent !== true) dock("文件超过 32 MB 上限，没收。", "warn");
      return Promise.resolve({ skipped: true, ignored: ignored });
    }
    if (docs.length > MAX_FILES) {
      docs = docs.slice(0, MAX_FILES);
      if (opts.silent !== true) dock("一次最多收 " + MAX_FILES + " 个文件，多出来的没收。", "warn");
    }
    return Promise.all(docs.map(function (file) {
      return readAsDataUrl(file).then(function (dataUrl) {
        return { name: file.name || "未命名文件", data_url: dataUrl };
      });
    })).then(function (entries) {
      return ingestEntries(entries, opts);
    });
  }

  // ---------- 屏幕截取 ----------

  function requestDisplay() {
    if (!navigator.mediaDevices || typeof navigator.mediaDevices.getDisplayMedia !== "function") {
      return Promise.reject(new Error(
        "这个浏览器/这个地址不支持屏幕截取（缺 getDisplayMedia），请改用 Ctrl+V 粘贴截图"));
    }
    return navigator.mediaDevices.getDisplayMedia({
      video: { frameRate: { ideal: 12, max: 30 } },
      audio: false
    });
  }

  /** 宿主自绘确认框：请用户亲手点一下，宿主文档才拿得到用户手势。 */
  function askForGesture(onCancel) {
    return new Promise(function (resolve, reject) {
      if (!window.JzoDialogs || typeof window.JzoDialogs.confirm !== "function") {
        reject(new Error("浏览器要你亲手点一下才能截屏，请改用 Ctrl+V 粘贴截图"));
        return;
      }
      window.JzoDialogs.confirm({
        title: "开始截屏",
        message: "浏览器要求截屏由你亲手点一下发起。点【开始截屏】后，选中要截的窗口或屏幕，"
          + "移动鼠标看放大镜，左键松开即截；不想截就点【取消】，改用 Ctrl+V 粘贴截图。",
        confirmText: "开始截屏",
        cancelText: "取消",
        onAccept: function () { resolve(true); },
        onCancel: function () {
          reject(new Error("已取消截屏。想截屏可以直接 Ctrl+V 粘贴截图。"));
        }
      });
    });
  }

  function runCapture(stream) {
    return new Promise(function (resolve, reject) {
      var video = document.createElement("video");
      video.muted = true;
      video.setAttribute("playsinline", "");
      video.setAttribute("aria-hidden", "true");
      video.srcObject = stream;

      var layer = document.createElement("div");
      layer.className = "jzo-cap-layer";
      var canvas = document.createElement("canvas");
      canvas.className = "jzo-cap-canvas";
      var hint = document.createElement("div");
      hint.className = "jzo-cap-hint";
      hint.textContent = "移动鼠标看像素 · 左键松开截取 · Esc 取消";
      layer.appendChild(canvas);
      layer.appendChild(hint);

      // 上下文先建好、平滑先关掉，再挂进 DOM：
      // 画布一旦进了文档，谁先调 getContext 谁就拿到这个上下文——
      // 让别人抢在前面建出一个默认开着平滑的上下文，像素就被插值糊掉了。
      var ctx = canvas.getContext("2d");
      ctx.imageSmoothingEnabled = false;
      var source = document.createElement("canvas");
      var sctx = source.getContext("2d");
      sctx.imageSmoothingEnabled = false;
      document.body.appendChild(layer);

      var pointer = { x: Math.round(window.innerWidth / 2), y: Math.round(window.innerHeight / 2) };
      var frame = 0;
      var done = false;

      function stopTracks() {
        if (stream && typeof stream.getTracks === "function") {
          stream.getTracks().forEach(function (track) {
            try { track.stop(); } catch (error) { /* 轨道已经停了，无所谓 */ }
          });
        }
      }

      function cleanup() {
        if (done) return;
        done = true;
        if (frame) window.cancelAnimationFrame(frame);
        layer.removeEventListener("mousemove", onMove);
        layer.removeEventListener("mouseup", onUp);
        layer.removeEventListener("mousedown", onDown);
        layer.removeEventListener("contextmenu", onContext);
        window.removeEventListener("keydown", onKey, true);
        window.removeEventListener("resize", resize);
        if (layer.parentNode) layer.parentNode.removeChild(layer);
        video.srcObject = null;
        stopTracks();
        capturing = false;
      }

      function resize() {
        var dpr = Math.min(2, window.devicePixelRatio || 1);
        canvas.width = Math.max(1, Math.floor(window.innerWidth * dpr));
        canvas.height = Math.max(1, Math.floor(window.innerHeight * dpr));
        canvas.style.width = window.innerWidth + "px";
        canvas.style.height = window.innerHeight + "px";
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        // 改画布尺寸会把上下文重置回默认状态，平滑也跟着被打开——
        // 每改一次尺寸就得再关一次，放大镜才看得见像素而不是插值色。
        ctx.imageSmoothingEnabled = false;
      }

      function onMove(event) {
        pointer.x = event.clientX;
        pointer.y = event.clientY;
      }

      function onDown(event) {
        // 只认左键；按下即锁住坐标，防止松开时鼠标已经挪走。
        if (event.button !== 0) return;
        event.preventDefault();
      }

      function onContext(event) {
        event.preventDefault();
      }

      function onUp(event) {
        if (event.button !== 0) return;
        event.preventDefault();
        var crop = cropRect();
        if (!crop) {
          cleanup();
          resolve({ cancelled: true });
          return;
        }
        var out = document.createElement("canvas");
        out.width = Math.max(1, Math.round(crop.width));
        out.height = Math.max(1, Math.round(crop.height));
        var octx = out.getContext("2d");
        octx.imageSmoothingEnabled = false;
        octx.drawImage(source, crop.x, crop.y, crop.width, crop.height, 0, 0, out.width, out.height);
        var dataUrl = out.toDataURL("image/png");
        cleanup();
        resolve({ data_url: dataUrl, width: out.width, height: out.height });
      }

      function onKey(event) {
        if (event.key !== "Escape") return;
        event.preventDefault();
        cleanup();
        resolve({ cancelled: true });
      }

      /** 光标周围那一块：从原始画面里裁，不带暗层与放大镜。 */
      function cropRect() {
        var vw = video.videoWidth;
        var vh = video.videoHeight;
        if (!vw || !vh) return null;
        var scale = Math.max(window.innerWidth / vw, window.innerHeight / vh);
        var ox = (window.innerWidth - vw * scale) / 2;
        var oy = (window.innerHeight - vh * scale) / 2;
        var vx = (pointer.x - ox) / scale;
        var vy = (pointer.y - oy) / scale;
        var width = Math.min(CROP_WIDTH, vw);
        var height = Math.min(CROP_HEIGHT, vh);
        var x = Math.max(0, Math.min(vw - width, vx - width / 2));
        var y = Math.max(0, Math.min(vh - height, vy - height / 2));
        return { x: x, y: y, width: width, height: height };
      }

      function draw() {
        if (done) return;
        frame = window.requestAnimationFrame(draw);
        var vw = video.videoWidth;
        var vh = video.videoHeight;
        if (!vw || !vh) return;
        if (source.width !== vw || source.height !== vh) {
          source.width = vw;
          source.height = vh;
        }
        sctx.imageSmoothingEnabled = false;
        sctx.drawImage(video, 0, 0, vw, vh);

        var viewW = window.innerWidth;
        var viewH = window.innerHeight;
        var scale = Math.max(viewW / vw, viewH / vh);
        var dw = vw * scale;
        var dh = vh * scale;
        var ox = (viewW - dw) / 2;
        var oy = (viewH - dh) / 2;

        ctx.clearRect(0, 0, viewW, viewH);
        ctx.drawImage(source, ox, oy, dw, dh);
        // 全屏变暗：看得见屏幕，但压得住，好找要截的那一处
        ctx.fillStyle = "rgba(6, 8, 12, 0.58)";
        ctx.fillRect(0, 0, viewW, viewH);

        // 鼠标变成十字：系统指针藏起来，自己画一根
        ctx.strokeStyle = "rgba(255, 255, 255, 0.9)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(pointer.x - 16, pointer.y + 0.5);
        ctx.lineTo(pointer.x + 16, pointer.y + 0.5);
        ctx.moveTo(pointer.x + 0.5, pointer.y - 16);
        ctx.lineTo(pointer.x + 0.5, pointer.y + 16);
        ctx.stroke();

        // 圆形放大镜：跟着鼠标走，关掉平滑看像素
        var radius = MAGNIFY_RADIUS;
        var mx = pointer.x + radius + 28;
        var my = pointer.y + radius + 28;
        if (mx + radius > viewW - 8) mx = pointer.x - radius - 28;
        if (my + radius > viewH - 8) my = pointer.y - radius - 28;
        var half = radius / MAGNIFY_ZOOM;
        var sx = (pointer.x - ox) / scale - half;
        var sy = (pointer.y - oy) / scale - half;
        var sw = half * 2;
        var sh = half * 2;
        ctx.save();
        ctx.beginPath();
        ctx.arc(mx, my, radius, 0, Math.PI * 2);
        ctx.clip();
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(source, sx, sy, sw, sh, mx - radius, my - radius, radius * 2, radius * 2);
        ctx.restore();
        ctx.strokeStyle = "rgba(255, 255, 255, 0.92)";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(mx, my, radius, 0, Math.PI * 2);
        ctx.stroke();
        // 放大镜中心的十字准星
        ctx.strokeStyle = "rgba(255, 96, 96, 0.95)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(mx - 12, my + 0.5);
        ctx.lineTo(mx + 12, my + 0.5);
        ctx.moveTo(mx + 0.5, my - 12);
        ctx.lineTo(mx + 0.5, my + 12);
        ctx.stroke();
      }

      resize();
      window.addEventListener("resize", resize);
      layer.addEventListener("mousemove", onMove);
      layer.addEventListener("mousedown", onDown);
      layer.addEventListener("mouseup", onUp);
      layer.addEventListener("contextmenu", onContext);
      window.addEventListener("keydown", onKey, true);
      capturing = true;
      video.play().catch(function () { /* 自动播放被拒也不影响：有画面才画，没画面就等着 */ });
      frame = window.requestAnimationFrame(draw);
    });
  }

  function captureScreen() {
    if (capturing) return Promise.resolve({ cancelled: true, busy: true });
    return requestDisplay().then(function (stream) {
      return runCapture(stream);
    }, function (error) {
      // 拿不到画面，多半是浏览器要用户手势；请用户亲手点一下再试。
      return askForGesture().then(function () {
        return requestDisplay();
      }).then(function (stream) {
        return runCapture(stream);
      }, function (second) {
        var reason = second && second.message ? second.message
          : (error && error.message ? error.message : "浏览器没给屏幕画面");
        throw new Error(reason);
      });
    });
  }

  // ---------- 宿主自己的两个入口 ----------

  function imageFilesFromClipboard(event) {
    var items = (event.clipboardData && event.clipboardData.items) || [];
    var files = [];
    for (var i = 0; i < items.length; i += 1) {
      if (items[i].kind !== "file") continue;
      if (String(items[i].type || "").indexOf("image/") !== 0) continue;
      var file = items[i].getAsFile();
      if (file) files.push(file);
    }
    return files;
  }

  function isTypingTarget(target) {
    if (!target || !target.tagName) return false;
    var tag = String(target.tagName).toUpperCase();
    return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable === true;
  }

  window.addEventListener("paste", function (event) {
    if (isTypingTarget(event.target)) return;
    var files = imageFilesFromClipboard(event);
    if (!files.length) return;
    event.preventDefault();
    ingestFiles(files, { source: "paste" });
  });

  window.addEventListener("keydown", function (event) {
    if (!event.altKey || event.ctrlKey || event.metaKey) return;
    if (String(event.key || "").toLowerCase() !== "s") return;
    if (isTypingTarget(event.target)) return;
    event.preventDefault();
    captureScreen().then(function (result) {
      if (!result || !result.data_url) return null;
      return ingestFiles([dataUrlToFile(result.data_url, shotName())], { source: "capture" });
    }).catch(function (error) {
      dock("截屏没成功：" + (error && error.message ? error.message : "未知原因"), "warn");
    });
  });

  window.JzoIntake = {
    ingestFiles: ingestFiles,
    ingestEntries: ingestEntries,
    captureScreen: captureScreen,
    isCapturing: function () { return capturing; },
    shotName: shotName,
    dataUrlToFile: dataUrlToFile,
    // 写队列是全局唯一的：stage.js 的写操作也走这一条，两边才不会互相烧掉对方的令牌。
    serialize: serialize
  };
})();
