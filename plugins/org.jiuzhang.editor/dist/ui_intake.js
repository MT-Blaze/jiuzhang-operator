/**
 * ui_intake.js —— plugin.js 的「接收区」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var cropOpen = deps.cropOpen;
    var dock = deps.dock;
    var dockWarn = deps.dockWarn;
    var el = deps.el;
    var errorDetail = deps.errorDetail;
    var hostCall = deps.hostCall;
    var panelSay = deps.panelSay;
    var publish = deps.publish;
    var refreshBatches = deps.refreshBatches;
    var state = coreState.state;
    var basketEl = deps.dom.basketEl;
    var basketEmptyEl = deps.dom.basketEmptyEl;
    var basketFileEl = deps.dom.basketFileEl;
    var basketFootEl = deps.dom.basketFootEl;
    var basketGoEl = deps.dom.basketGoEl;
    var basketListEl = deps.dom.basketListEl;
    var root = deps.dom.root;

  // ---------- 接收区：拖入 / 粘贴 / 截屏 ----------

  // OCR 可能跑很久：宿主那条 HTTP 默认 20 秒就超时，这里给足时间。
  var INGEST_TIMEOUT_MS = 180000;
  // 四通道只影响**下一次**开始解析；已立起来的批次绝不重跑。
  var INGEST_CHANNELS = ["auto", "local_ai", "full_ocr", "mineru"];

  function currentChannel() {
    var picked = String(state.ingestChannel || "auto");
    return INGEST_CHANNELS.indexOf(picked) < 0 ? "auto" : picked;
  }

  function channelLabel(key) {
    return { auto: "自动", local_ai: "本地+AI", full_ocr: "全量OCR", mineru: "MinerU云端" }[key]
      || "自动";
  }

  function fileEntry(file, fallbackName) {
    return new Promise(function (resolve) {
      var name = String((file && file.name) || "") || String(fallbackName || "");
      if (!name) { resolve(null); return; }
      var reader = new FileReader();
      reader.onerror = function () { resolve(null); };
      reader.onload = function () {
        resolve({ name: name, data_url: String(reader.result || "") });
      };
      reader.readAsDataURL(file);
    });
  }


  /** 文件交给宿主建批次：识别与题库都在宿主那边，插件只递字节与通道。 */
  function ingestEntries(entries, channel) {
    var files = (entries || []).filter(function (entry) { return entry && entry.data_url; });
    if (!files.length) return Promise.resolve(null);
    return hostCall("ingest.files", {
      files: files,
      channel: channel || currentChannel()
    }, INGEST_TIMEOUT_MS).then(function (result) {
      var saved = Array.isArray(result && result.saved_ids) ? result.saved_ids.length : 0;
      var ids = Array.isArray(result && result.batch_ids)
        ? result.batch_ids
        : (result && result.batch_id ? [result.batch_id] : []);
      // 一个文件一个批次：拖 9 份就是 9 个批次，各认各的。
      var label = ids.length > 1
        ? ids.length + " 个批次（" + ids.join("、") + "）"
        : "批次 " + (ids[0] || "");
      // parsing=true：批次已经立起来了，识别在后台跑。
      if (result && result.parsing) {
        dock("已收下 " + files.length + " 份，分成 " + label + "，正在后台解析。");
        return result;
      }
      dock("已收下 " + files.length + " 个文件，认出 " + saved + " 道题，" + label + "。");
      return result;
    }).catch(function (error) {
      var text = (error && error.message) || "未知原因";
      panelSay("文件没收进来：" + text, "error", "failed");
      dockWarn("文件没收进来：" + text, errorDetail(error));
      return null;
    });
  }

  // 通道只记在这一次点击上：拖入与粘贴都只往筐里放，开始解析才带上它。
  var routeWatchTimer = null;

  function watchRoute(ids, channel) {
    if (!ids || !ids.length) return;
    if (routeWatchTimer) window.clearInterval(routeWatchTimer);
    var seen = {};
    var polls = 0;
    var maxPolls = channel === "mineru" ? 180 : 60;
    routeWatchTimer = window.setInterval(function () {
      polls += 1;
      hostCall("pending.batch_list", {}, 20000).then(function (result) {
        var cards = (result && Array.isArray(result.batches)) ? result.batches : [];
        var waiting = 0;
        cards.forEach(function (card) {
          var id = String((card && card.batch_id) || "");
          if (ids.indexOf(id) < 0) return;
          var route = (card && card.route) || {};
          var note = String(route.note || "");
          if (note && note !== seen[id]) {
            seen[id] = note;
            dock(note);
          }
          if (!route.done) waiting += 1;
        });
        if (!waiting || polls >= maxPolls) {
          window.clearInterval(routeWatchTimer);
          routeWatchTimer = null;
        }
      }, function () {
        if (polls >= maxPolls) {
          window.clearInterval(routeWatchTimer);
          routeWatchTimer = null;
        }
      });
    }, 5000);
  }

  function wireChannelButtons() {
    var group = document.getElementById("edRouteChannels");
    if (!group) return;
    var buttons = group.querySelectorAll("[data-channel]");
    function paint() {
      Array.prototype.forEach.call(buttons, function (button) {
        var on = String(button.getAttribute("data-channel")) === currentChannel();
        button.setAttribute("aria-pressed", on ? "true" : "false");
      });
    }
    Array.prototype.forEach.call(buttons, function (button) {
      button.addEventListener("click", function () {
        var key = String(button.getAttribute("data-channel") || "auto");
        state.ingestChannel = INGEST_CHANNELS.indexOf(key) < 0 ? "auto" : key;
        paint();
        dock("解析通道：" + channelLabel(state.ingestChannel)
          + "（只对下一次【开始解析】生效）");
      });
    });
    paint();
  }

  function hasFiles(event) {
    var transfer = event && event.dataTransfer;
    if (!transfer) return false;
    if (transfer.items && transfer.items.length) {
      for (var index = 0; index < transfer.items.length; index += 1) {
        if (transfer.items[index].kind === "file") return true;
      }
      return false;
    }
    return Boolean(transfer.files && transfer.files.length);
  }

  function isTypingTarget(target) {
    if (!target || !target.tagName) return false;
    var tag = String(target.tagName).toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select") return true;
    return Boolean(target.isContentEditable);
  }

  /**
   * 剪贴板里的图片：``items`` 与 ``files`` 两路都取，同一张只留一份。
   *
   * 只认 ``items`` 不够：有些环境贴图时 ``items`` 是空的，只有 ``files`` 里有货；
   * 两路都取，粘贴才不会时灵时不灵。
   */
  function clipboardImageFiles(event) {
    var data = event && event.clipboardData;
    if (!data) return [];
    var files = [];
    var seen = [];
    function push(file) {
      if (!file) return;
      var type = String(file.type || "").toLowerCase();
      if (type.indexOf("image/") !== 0) return;
      var name = String(file.name || "");
      var size = Number(file.size || 0);
      for (var i = 0; i < seen.length; i += 1) {
        if (seen[i].type === type && seen[i].name === name && seen[i].size === size) return;
      }
      seen.push({ type: type, name: name, size: size });
      files.push(file);
    }
    var items = data.items || [];
    for (var index = 0; index < items.length; index += 1) {
      if (items[index].kind !== "file") continue;
      var file = items[index].getAsFile();
      if (file) push(file);
    }
    var listed = data.files || [];
    for (var j = 0; j < listed.length; j += 1) push(listed[j]);
    return files;
  }

  /** 只有画布那只筐会亮收货高亮：辅助栏的虚线接收框已随「UI 极致瘦身令」下线。 */
  function markDrop(on) {
    if (basketEl) basketEl.classList.toggle("is-over", Boolean(on));
  }

  // ---------- 文件收集筐（军令 #27）----------
  // 收集筐是这一屏唯一的收件处：拖入、粘贴、点选都先落筐，
  // 底部的【开始解析】才是唯一的建批次入口——老师点它之前，底座不会多出一个批次。

  var basketSeq = 0;
  var basketBusy = false;
  // 单列列表里的小缩略图：44px 见方，左边一列图标、中间文件名、右边红 ×。
  var THUMB_SIDE = 44;

  /** 剪贴板里的图没有文件名时补一个：分拣只看后缀，名字不能空。 */
  function basketName(file) {
    var name = String((file && file.name) || "");
    if (name) return name;
    var type = String((file && file.type) || "").toLowerCase();
    if (type.indexOf("image/") === 0) {
      if (type.indexOf("jpeg") >= 0 || type.indexOf("jpg") >= 0) return "截图.jpg";
      if (type.indexOf("webp") >= 0) return "截图.webp";
      return "截图.png";
    }
    return "粘贴的文件";
  }

  /** 收一批文件进筐；``.zip`` 是插件包，走安装那条道，静默忽略。 */
  function basketAdd(fileList) {
    var files = Array.prototype.slice.call(fileList || []);
    var added = 0;
    files.forEach(function (file) {
      if (!file) return;
      var name = basketName(file);
      if (name.toLowerCase().slice(-4) === ".zip") return;
      var entry = {
        id: "b" + (basketSeq += 1),
        name: name,
        type: String(file.type || ""),
        size: Number(file.size || 0),
        file: file,
        bitmap: null,
        thumb: null
      };
      state.basket.push(entry);
      if (entry.type.indexOf("image/") === 0) decodeThumb(entry);
      added += 1;
    });
    if (added) {
      renderBasket();
      dock("收集筐里已有 " + state.basket.length + " 份文件，点【开始解析】才建批次。");
    }
    return added;
  }

  /**
   * 缩略图画在 canvas 上，不走 ``<img src=blob:...>``。
   *
   * 插件沙箱的 CSP 是 ``img-src 'self' <底座源>``：blob: 与 data: 的图片全被拦掉，
   * 屏幕上只会剩一只 200×200 的空框——看着像有缩略图，其实什么都没显示。
   * ``createImageBitmap`` 是插件自己把字节解成位图，不发请求、不受 CSP 管，
   * 画布上的像素是货真价实的题面。
   */
  function decodeThumb(entry) {
    if (!entry.file || typeof window.createImageBitmap !== "function") return;
    window.createImageBitmap(entry.file).then(function (bitmap) {
      entry.bitmap = bitmap;
      paintThumb(entry);
    }, function () {
      // 解不开（格式不支持）就只留文件名，不装作有预览
    });
  }

  function paintThumb(entry) {
    var node = entry.thumb;
    if (!node || !entry.bitmap) return;
    var width = entry.bitmap.width || 0;
    var height = entry.bitmap.height || 0;
    if (!width || !height) return;
    var ctx = node.getContext("2d");
    if (!ctx) return;
    var scale = Math.min(THUMB_SIDE / width, THUMB_SIDE / height);
    var drawW = Math.max(1, Math.round(width * scale));
    var drawH = Math.max(1, Math.round(height * scale));
    ctx.clearRect(0, 0, THUMB_SIDE, THUMB_SIDE);
    ctx.drawImage(entry.bitmap, (THUMB_SIDE - drawW) / 2, (THUMB_SIDE - drawH) / 2, drawW, drawH);
  }

  /** 文件类型角标：图片走缩略图，文档按后缀给一个短标签（PDF / DOCX / TEX …）。 */
  function fileBadge(name) {
    var text = String(name || "");
    var dot = text.lastIndexOf(".");
    var ext = dot < 0 ? "" : text.slice(dot + 1).toUpperCase();
    if (!ext) return "FILE";
    return ext.length > 5 ? ext.slice(0, 5) : ext;
  }

  function renderBasket() {
    if (!basketListEl) return;
    basketListEl.textContent = "";
    state.basket.forEach(function (entry) {
      var isImage = entry.type.indexOf("image/") === 0;
      var item = el("li", "ed-basket-item");
      item.setAttribute("data-kind", isImage ? "image" : "file");
      item.setAttribute("data-name", entry.name);
      if (isImage) {
        // 图就走 44px 缩略图：左边一眼认出是哪道题。
        var thumb = document.createElement("canvas");
        thumb.className = "ed-basket-thumb";
        thumb.width = THUMB_SIDE;
        thumb.height = THUMB_SIDE;
        thumb.setAttribute("data-thumb", "1");
        thumb.setAttribute("aria-label", "待解析图片预览：" + entry.name);
        item.appendChild(thumb);
        entry.thumb = thumb;
        paintThumb(entry);
      } else {
        // 文档给一张带后缀的图标，不装缩略图，也不留空框。
        var icon = el("span", "ed-basket-icon");
        icon.setAttribute("data-ext", fileBadge(entry.name));
        icon.setAttribute("aria-hidden", "true");
        icon.appendChild(el("span", "ed-basket-icon-ext", fileBadge(entry.name)));
        item.appendChild(icon);
      }
      // 中间文件名：再长也只占一行，超出自动省略，悬停看全名。
      var nameEl = el("span", "ed-basket-name", entry.name);
      nameEl.title = entry.name;
      item.appendChild(nameEl);
      var remove = el("button", "ed-basket-x", "×");
      remove.type = "button";
      remove.setAttribute("aria-label", "移除 " + entry.name);
      remove.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        basketRemove(entry.id);
      });
      item.appendChild(remove);
      basketListEl.appendChild(item);
    });
    if (basketEmptyEl) basketEmptyEl.hidden = state.basket.length > 0;
    if (basketFootEl) basketFootEl.hidden = state.basket.length === 0;
    if (basketGoEl && !basketBusy) {
      basketGoEl.textContent = "🚀 开始解析 (" + state.basket.length + " 个文件)";
    }
    if (basketEl) basketEl.setAttribute("data-count", String(state.basket.length));
  }

  function basketRemove(id) {
    var index = -1;
    for (var i = 0; i < state.basket.length; i += 1) {
      if (state.basket[i].id === id) { index = i; break; }
    }
    if (index < 0) return;
    var entry = state.basket.splice(index, 1)[0];
    if (entry.bitmap && typeof entry.bitmap.close === "function") entry.bitmap.close();
    renderBasket();
  }

  function basketClear() {
    state.basket.forEach(function (entry) {
      if (entry.bitmap && typeof entry.bitmap.close === "function") entry.bitmap.close();
    });
    state.basket = [];
    renderBasket();
  }

  function setBasketBusy(on) {
    if (!basketGoEl) return;
    basketGoEl.disabled = Boolean(on);
    if (on) {
      basketGoEl.setAttribute("aria-busy", "true");
      basketGoEl.textContent = "🚀 正在解析…";
    } else {
      basketGoEl.removeAttribute("aria-busy");
    }
  }

  /** 【开始解析】：筐里有多少交多少，宿主那边立批次、后台跑识别。 */
  function basketGo() {
    if (!state.basket.length || basketBusy) return Promise.resolve(null);
    basketBusy = true;
    setBasketBusy(true);
    var pickedChannel = currentChannel();
    return Promise.all(state.basket.map(function (entry) {
      // 剪贴板里的图未必带文件名，补上筐里显示的那个，解析才认得出它。
      return fileEntry(entry.file, entry.name);
    })).then(function (payloads) {
      return ingestEntries(payloads.filter(Boolean), pickedChannel);
    }).then(function (result) {
      if (result) {
        basketClear();
        refreshBatches();
        if (result.parsing) {
          // 页图在后台渲染：隔几拍再刷，纯图片批次的「原卷 N 页」会自己长出来。
          [1500, 4000, 8000, 15000].forEach(function (delay) {
            window.setTimeout(refreshBatches, delay);
          });
          var ids = Array.isArray(result.batch_ids)
            ? result.batch_ids
            : (result.batch_id ? [result.batch_id] : []);
          // MinerU 可能排队十几分钟：持续把路由进度写进底部日志，别让老师干等。
          watchRoute(ids.map(String), pickedChannel);
        }
      }
      basketBusy = false;
      setBasketBusy(false);
      renderBasket();
      return result;
    }, function (error) {
      basketBusy = false;
      setBasketBusy(false);
      renderBasket();
      dockWarn("开始解析失败：" + ((error && error.message) || "未知原因"), errorDetail(error));
      return null;
    });
  }

  /** 面板实例（在右栏那张 iframe 里）把文件交给宿主，由宿主转进画布的筐。 */
  function collectToCanvas(files) {
    var list = Array.prototype.slice.call(files || []);
    if (!list.length) return;
    publish("editor.collect_files", { files: list });
  }

  var intakeWired = false;

  /**
   * 接收区接线。
   *
   * 拖放与粘贴事件**不跨 iframe 边界**——宿主壳收不到插件框里发生的拖放，
   * 所以插件这一侧必须自己接住，再把字节转给宿主。
   *
   * 画布实例与辅助栏实例是两张 iframe：筐只住在画布里，
   * 面板那侧收到的文件一律转交宿主，由宿主送进画布的筐（插件两帧不直连）。
   */
  function wireIntake() {
    if (intakeWired) return;
    intakeWired = true;
    var inCanvas = state.slot === "stage.center";

    if (inCanvas && basketEl) {
      ["dragenter", "dragover"].forEach(function (type) {
        basketEl.addEventListener(type, function (event) {
          if (!hasFiles(event)) return;
          event.preventDefault();
          event.stopPropagation();
          if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
          markDrop(true);
        });
      });
      basketEl.addEventListener("dragleave", function (event) {
        event.preventDefault();
        markDrop(false);
      });
      basketEl.addEventListener("drop", function (event) {
        event.preventDefault();
        event.stopPropagation();
        markDrop(false);
        var files = event.dataTransfer && event.dataTransfer.files;
        if (files && files.length) basketAdd(files);
      });
      // 点框选文件：筐里的移除钮与【开始解析】不触发它
      basketEl.addEventListener("click", function (event) {
        var hit = event.target && event.target.closest
          ? event.target.closest(".ed-basket-x, .ed-basket-go") : null;
        if (hit) return;
        if (basketFileEl) basketFileEl.click();
      });
      basketEl.addEventListener("keydown", function (event) {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        if (basketFileEl) basketFileEl.click();
      });
    }
    if (inCanvas && basketFileEl) {
      basketFileEl.addEventListener("change", function () {
        var files = basketFileEl.files;
        if (files && files.length) basketAdd(files);
        basketFileEl.value = "";
      });
    }
    if (inCanvas && basketGoEl) {
      basketGoEl.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        basketGo();
      });
    }
    // 画布整屏都收：拖到筐旁边的空白处也算落进筐里
    if (inCanvas && root) {
      root.addEventListener("dragover", function (event) {
        if (!hasFiles(event)) return;
        event.preventDefault();
      });
      root.addEventListener("drop", function (event) {
        if (!hasFiles(event)) return;
        if (basketEl && basketEl.contains(event.target)) return;
        if (cropOpen()) return;   // 切图台正在等图，别把它当成新卷子
        event.preventDefault();
        var files = event.dataTransfer && event.dataTransfer.files;
        if (files && files.length) basketAdd(files);
      });
    }
    // Ctrl+V 粘贴截图 → 进筐，不直接建批次
    window.addEventListener("paste", function (event) {
      if (cropOpen()) return;   // 切图台正在等图，别把它当成新卷子
      if (isTypingTarget(event.target)) return;
      var files = clipboardImageFiles(event);
      if (!files.length) return;
      event.preventDefault();
      if (inCanvas) basketAdd(files);
      else collectToCanvas(files);
    });
    if (inCanvas) {
      wireChannelButtons();
      renderBasket();
    }
  }

    return {
      INGEST_TIMEOUT_MS: INGEST_TIMEOUT_MS,
      THUMB_SIDE: THUMB_SIDE,
      basketAdd: basketAdd,
      basketBusy: basketBusy,
      basketClear: basketClear,
      basketGo: basketGo,
      basketName: basketName,
      basketRemove: basketRemove,
      basketSeq: basketSeq,
      clipboardImageFiles: clipboardImageFiles,
      collectToCanvas: collectToCanvas,
      decodeThumb: decodeThumb,
      fileBadge: fileBadge,
      fileEntry: fileEntry,
      hasFiles: hasFiles,
      ingestEntries: ingestEntries,
      intakeWired: intakeWired,
      isTypingTarget: isTypingTarget,
      markDrop: markDrop,
      paintThumb: paintThumb,
      renderBasket: renderBasket,
      setBasketBusy: setBasketBusy,
      wireIntake: wireIntake,
    };
  }

  global.JzoEditorIntake = { create: create };
})(window);
