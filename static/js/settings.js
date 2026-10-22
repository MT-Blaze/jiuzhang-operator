/**
 * 设置与控制：手动安装 zip。
 *
 * 在线索引的拉取/安装逻辑仍由 plugins.js 负责（同一套表单 id），本文件只补
 * 「手动安装」：文件选择 + 拖拽区 + 状态回显。
 * 边界与工作台拖装一致：只收 .zip、上限 50 MB、写接口带本机令牌、409 需显式
 * 确认覆盖，失败不留半个文件。所有插件名只走 textContent。
 */
(function () {
  "use strict";

  var dropZone = document.getElementById("stDropZone");
  var fileInput = document.getElementById("stZipFile");
  var pickBtn = document.getElementById("stPickZip");
  var statusBox = document.getElementById("stInstallStatus");
  var busy = false;

  function setStatus(text, tone) {
    if (!statusBox) return;
    statusBox.textContent = text || "";
    statusBox.setAttribute("data-tone", tone || "info");
    statusBox.hidden = !text;
  }

  function readToken() {
    return fetch("/api/settings", { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) throw new Error("读取本机令牌失败（HTTP " + response.status + "）");
        return response.json();
      })
      .then(function (body) {
        var token = body && body.local_token ? String(body.local_token) : "";
        if (!token) throw new Error("本机未生成就绪令牌，请先启动服务后再试");
        return token;
      });
  }

  function readErrorDetail(response, body) {
    var detail = body && body.detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail.message === "string") return detail.message;
    return "HTTP " + response.status;
  }

  function firstZip(fileList) {
    for (var i = 0; i < (fileList || []).length; i += 1) {
      if (/\.zip$/i.test(fileList[i].name || "")) return fileList[i];
    }
    return null;
  }

  function hasFiles(event) {
    var types = (event.dataTransfer && event.dataTransfer.types) || [];
    return Array.prototype.indexOf.call(types, "Files") !== -1;
  }

  function setDragging(on) {
    if (dropZone) dropZone.classList.toggle("is-dragover", Boolean(on));
  }

  function installZip(file, replace) {
    if (!file) return Promise.resolve();
    if (!/\.zip$/i.test(file.name || "")) {
      setStatus("只接受标准 .zip 插件包（解压即用）。", "warn");
      return Promise.resolve();
    }
    if (file.size > 50 * 1024 * 1024) {
      setStatus("zip 包超过 50 MB 上限。", "warn");
      return Promise.resolve();
    }

    busy = true;
    if (pickBtn) {
      pickBtn.disabled = true;
      pickBtn.setAttribute("aria-busy", "true");
    }
    setStatus("正在校验并安装 " + file.name + " …", "info");

    return readToken()
      .then(function (token) {
        return fetch("/api/plugins/install" + (replace ? "?replace=true" : ""), {
          method: "POST",
          headers: { "Content-Type": "application/zip", "X-JZO-Token": token },
          body: file,
        });
      })
      .then(function (response) {
        return response.json().catch(function () { return null; }).then(function (body) {
          if (response.status === 409 && !replace) {
            var question = readErrorDetail(response, body) + " 覆盖升级会先删除旧目录，继续吗？";
            if (window.confirm(question)) return installZip(file, true);
            setStatus("已取消覆盖，本机原有插件保持不变。", "info");
            return null;
          }
          if (!response.ok) throw new Error(readErrorDetail(response, body));
          var plugin = (body && body.plugin) || {};
          setStatus(
            "已安装 " + (plugin.name || plugin.id) + " v" + (plugin.version || "?") +
            "。工作台左栏与对话工具即刻生效，无需重启。",
            "ok"
          );
          return body;
        });
      })
      .catch(function (error) {
        setStatus("安装失败：" + (error && error.message ? error.message : error), "down");
      })
      .finally(function () {
        busy = false;
        if (pickBtn) {
          pickBtn.disabled = false;
          pickBtn.setAttribute("aria-busy", "false");
        }
      });
  }

  function openPicker() {
    if (busy || !fileInput) return;
    fileInput.click();
  }

  if (pickBtn) pickBtn.addEventListener("click", openPicker);

  if (fileInput) {
    fileInput.addEventListener("change", function () {
      var file = fileInput.files && fileInput.files[0];
      fileInput.value = "";
      if (file) installZip(file, false);
    });
  }

  if (dropZone) {
    dropZone.addEventListener("click", openPicker);
    dropZone.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openPicker();
      }
    });
    dropZone.addEventListener("dragenter", function (event) {
      if (!hasFiles(event)) return;
      event.preventDefault();
      setDragging(true);
    });
    dropZone.addEventListener("dragover", function (event) {
      if (!hasFiles(event)) return;
      event.preventDefault();
      if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
      setDragging(true);
    });
    dropZone.addEventListener("dragleave", function () {
      setDragging(false);
    });
    dropZone.addEventListener("drop", function (event) {
      event.preventDefault();
      event.stopPropagation();
      setDragging(false);
      var file = firstZip(event.dataTransfer && event.dataTransfer.files);
      if (!file) {
        setStatus("没看到 .zip 文件：插件包必须是标准 zip。", "warn");
        return;
      }
      installZip(file, false);
    });
  }

  // 拖到框外时也别让浏览器把 zip 当页面打开；只提示该往哪拖。
  window.addEventListener("dragover", function (event) {
    if (hasFiles(event)) event.preventDefault();
  });
  window.addEventListener("drop", function (event) {
    if (!hasFiles(event)) return;
    event.preventDefault();
    setDragging(false);
    if (dropZone && dropZone.contains(event.target)) return;
    setStatus("请把 .zip 拖到虚线框内，或点【选择 zip 文件】。", "warn");
  });
})();
