/**
 * ui_model.js —— 本地 YOLO 模型的按需下载入口（可整块下架）。
 *
 * 模型不进插件包：选【YOLO】且本机没有模型时才弹窗，老师点哪一个才下载哪一个。
 * 下载由宿主持有写令牌发起，插件只轮询 Host API 的进度，再把百分比交给底栏日志。
 * 整块下架：删掉本文件、index.html 里的 #edModelModal 与那一行 script
 * 以及 panel_model.css，再把 ui_intake.js 的 modelGate 调用去掉即可。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var dock = deps.dock;
    var dockWarn = deps.dockWarn;
    var hostCall = deps.hostCall;
    var openModal = deps.openModal;
    var closeModal = deps.closeModal;
    var dom = deps.dom;
    var modalEl = dom.modelModalEl;
    var noteEl = dom.modelNoteEl;
    var hintEl = dom.modelHintEl;
    var progressEl = dom.modelProgressEl;
    var progressTextEl = dom.modelProgressTextEl;
    var barEl = dom.modelBarEl;
    var fullEl = dom.modelFullEl;
    var quantizedEl = dom.modelQuantizedEl;
    var cancelEl = dom.modelCancelEl;

    var pollTimer = null;
    var lastPercent = {};
    var lastDockAt = 0;
    var statusCache = null;

    function labelOf(kind, fallback) {
      var models = (statusCache && statusCache.models) || {};
      var entry = models[kind] || {};
      return String(entry.label || fallback || (kind === "full" ? "满血版" : "量化版"));
    }

    function sizeOf(kind, fallback) {
      var models = (statusCache && statusCache.models) || {};
      var entry = models[kind] || {};
      return String(entry.display_size || fallback || "");
    }

    function hasModel(status) {
      var models = (status && status.models) || {};
      return Object.keys(models).some(function (kind) {
        return Boolean(models[kind] && models[kind].present);
      });
    }

    function fetchStatus() {
      return hostCall("layout.model_status", {}, 15000).catch(function (error) {
        dockWarn("读取本地模型状态失败：" + ((error && error.message) || "未知原因"));
        return null;
      });
    }

    function paintPicker(status) {
      var hardware = (status && status.hardware) || {};
      var gpu = String(hardware.gpu || "");
      var hardwareNote = hardware.ready
        ? "本机可用：" + String(hardware.hardware_label || "CPU运行")
        : "本机缺少 onnxruntime，下载后仍需安装运行库才能启用本地推理。";
      if (noteEl) {
        noteEl.textContent = gpu
          ? "检测到您的设备支持显卡加速（" + hardwareNote + "），是否下载【满血版模型】以获得极致精度？（"
            + sizeOf("full", "约 75MB") + "）"
          : "未检测到可用的显卡加速（" + hardwareNote + "），建议下载【轻量量化版】在 CPU 上运行（"
            + sizeOf("quantized", "约 20MB") + "）。";
      }
      if (hintEl) {
        hintEl.textContent = "若网络慢或配置低，可下载【轻量量化版】（"
          + sizeOf("quantized", "约 20MB") + "）。模型只存本机，绝不进插件包。";
      }
      if (fullEl) {
        fullEl.textContent = "下载满血版（" + sizeOf("full", "约 75MB") + "）";
        fullEl.disabled = !(status && status.models && status.models.full);
      }
      if (quantizedEl) {
        quantizedEl.textContent = "下载轻量量化版（" + sizeOf("quantized", "约 20MB") + "）";
        quantizedEl.disabled = !(status && status.models && status.models.quantized);
      }
      setProgress(false);
    }

    function setProgress(visible, text, percent) {
      if (progressEl) progressEl.hidden = !visible;
      if (progressTextEl && text != null) progressTextEl.textContent = text;
      if (barEl) barEl.style.width = Math.max(0, Math.min(100, Number(percent) || 0)) + "%";
    }

    function setBusy(busy) {
      [fullEl, quantizedEl].forEach(function (button) {
        if (button) button.disabled = Boolean(busy);
      });
    }

    function openPicker(status) {
      statusCache = status;
      paintPicker(status);
      openModal(modalEl);
    }

    function progressLine(kind, download) {
      var label = labelOf(kind);
      var percent = Math.max(0, Math.min(99, Number(download && download.percent) || 0));
      if (download && Number(download.total) > 0) {
        return { text: "正在下载" + label + "模型: " + percent + "%...", percent: percent };
      }
      var received = Number((download && download.received) || 0) / 1048576;
      return { text: "正在下载" + label + "模型: 已接收 " + received.toFixed(1) + " MB...",
               percent: percent };
    }

    function stopPolling() {
      if (pollTimer) window.clearInterval(pollTimer);
      pollTimer = null;
    }

    function trackDownload() {
      if (pollTimer) return;
      pollTimer = window.setInterval(function () {
        hostCall("layout.model_status", {}, 15000).then(function (status) {
          var download = status && status.download;
          if (!download) { stopPolling(); return; }
          var kind = String(download.kind || "");
          var label = labelOf(kind);
          if (download.state === "downloading") {
            var line = progressLine(kind, download);
            var percent = line.percent;
            var now = Date.now();
            if (percent >= (lastPercent[kind] || 0) + 5 || now - lastDockAt >= 4000) {
              lastPercent[kind] = percent;
              lastDockAt = now;
              dock(line.text);
              setProgress(true, line.text, percent);
            }
            return;
          }
          stopPolling();
          setBusy(false);
          statusCache = status;
          if (download.state === "done") {
            var version = String(((status.models || {})[kind] || {}).version || "v1.0");
            setProgress(true, label + "模型已就绪（" + version + "）", 100);
            dock(label + "模型已就绪（" + version + "），可重新点【开始解析】。");
            if (modalEl && !modalEl.hidden) closeModal(modalEl);
            return;
          }
          setProgress(true, label + "模型下载失败", 0);
          dockWarn(label + "模型下载失败：" + String(download.message || "未知原因"));
        }, function (error) {
          stopPolling();
          setBusy(false);
          dockWarn("模型下载进度中断：" + ((error && error.message) || "未知原因"));
        });
      }, 2000);
    }

    function startDownload(kind) {
      setBusy(true);
      setProgress(true, kind === "full" ? "正在连接满血版镜像…" : "正在连接量化版镜像…", 0);
      hostCall("layout.model_download", { kind: kind }, 20000).then(function () {
        lastPercent[kind] = 0;
        lastDockAt = 0;
        // 后台静默下载：关掉弹窗，进度只走底栏【运行日志】。
        if (modalEl && !modalEl.hidden) closeModal(modalEl);
        dock("已开始下载" + labelOf(kind) + "模型（" + sizeOf(kind) + "），进度会显示在运行日志。");
        trackDownload();
      }, function (error) {
        setBusy(false);
        setProgress(false);
        dockWarn("启动" + labelOf(kind) + "模型下载失败："
          + ((error && error.message) || "未知原因"));
      });
    }

    /** 【开始解析】与切到 YOLO 时调用：有模型放行，没模型弹窗并拦下本次解析。 */
    function ensureLayoutModel(engine) {
      if (String(engine || "") !== "yolo") return Promise.resolve(true);
      return fetchStatus().then(function (status) {
        if (!status) return false;
        statusCache = status;
        if (hasModel(status)) return true;
        var download = status.download || {};
        if (download.state === "downloading") {
          dock("本地 YOLO 模型正在下载（" + (Number(download.percent) || 0) + "%），请稍候。");
          trackDownload();
          return false;
        }
        openPicker(status);
        return false;
      });
    }

    function wire() {
      if (fullEl) fullEl.addEventListener("click", function () { startDownload("full"); });
      if (quantizedEl) quantizedEl.addEventListener("click", function () { startDownload("quantized"); });
      if (cancelEl) cancelEl.addEventListener("click", function () {
        closeModal(modalEl);
        dock("已跳过本地模型下载；YOLO 不可用时自动交云端版面 API。");
      });
    }

    wire();
    return {
      ensureLayoutModel: ensureLayoutModel,
      wire: wire,
    };
  }

  global.JzoEditorModel = { create: create };
})(window);
