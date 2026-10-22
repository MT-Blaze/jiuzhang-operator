(function () {
  "use strict";

  // 索引地址默认预填官方 Raw 直链（写在 HTML 的 value 里，用户可当场改掉）。
  // 底座仍不自动拉取：只有用户点【拉取清单】才会发起请求。
  var urlInput = document.getElementById("plIndexUrl");
  var form = document.getElementById("plIndexForm");
  var fetchBtn = document.getElementById("plFetchBtn");
  var statusBox = document.getElementById("plStatus");
  var resultHost = document.getElementById("plResults");
  var rejectedHost = document.getElementById("plRejected");
  var rejectedTitle = document.getElementById("pl-rejected-title");

  // 已安装插件的 id -> version，用于给卡片按钮标注「已安装/覆盖安装」
  var installedMap = {};

  var KIND_LABELS = {
    renderer: "渲染",
    importer: "导入",
    exporter: "导出",
    tool: "工具"
  };

  function setStatus(text, tone) {
    statusBox.textContent = text || "";
    statusBox.setAttribute("data-tone", tone || "info");
    statusBox.hidden = !text;
  }

  function setRejectedVisible(show) {
    // 没有条目被跳过时不挂一个空标题，免得看着像出了错却没内容
    rejectedTitle.hidden = !show;
    rejectedHost.hidden = !show;
  }

  function makePlaceholder(text) {
    var li = document.createElement("li");
    li.className = "pl-empty";
    li.appendChild(document.createTextNode(text));
    return li;
  }

  function clearResults() {
    while (resultHost.firstChild) resultHost.removeChild(resultHost.firstChild);
    while (rejectedHost.firstChild) rejectedHost.removeChild(rejectedHost.firstChild);
    setRejectedVisible(false);
  }

  function textNode(text) {
    return document.createTextNode(String(text == null ? "" : text));
  }

  function makeLink(url, label) {
    var a = document.createElement("a");
    a.className = "pl-link";
    a.href = url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.appendChild(textNode(label || url));
    return a;
  }

  function makeEntry(entry) {
    var li = document.createElement("li");
    li.className = "pl-entry";

    var head = document.createElement("div");
    head.className = "pl-entry-head";

    var title = document.createElement("h3");
    title.className = "pl-entry-title";
    title.appendChild(textNode(entry.name || entry.id));
    head.appendChild(title);

    var meta = document.createElement("p");
    meta.className = "pl-entry-meta";
    var bits = [];
    if (entry.kind && KIND_LABELS[entry.kind]) bits.push(KIND_LABELS[entry.kind]);
    bits.push("v" + (entry.version || "?"));
    bits.push(entry.id);
    if (installedMap[entry.id]) bits.push("本机已装 v" + installedMap[entry.id]);
    meta.appendChild(textNode(bits.join(" · ")));
    head.appendChild(meta);
    li.appendChild(head);

    if (entry.description) {
      var desc = document.createElement("p");
      desc.className = "pl-entry-desc";
      desc.appendChild(textNode(entry.description));
      li.appendChild(desc);
    }

    var actions = document.createElement("div");
    actions.className = "pl-entry-actions";
    actions.appendChild(makeInstallButton(entry));

    var zipLink = makeLink(entry.zip_url, "下载 zip 包");
    zipLink.className = "pl-link pl-link-ghost";
    actions.appendChild(zipLink);

    (entry.mirrors || []).forEach(function (mirror, index) {
      var link = makeLink(mirror, "镜像 " + (index + 1));
      link.className = "pl-link pl-link-ghost";
      actions.appendChild(link);
    });

    if (entry.homepage) {
      var home = makeLink(entry.homepage, "源码/说明页");
      home.className = "pl-link pl-link-ghost";
      actions.appendChild(home);
    }
    li.appendChild(actions);

    return li;
  }

  function renderIndex(data) {
    clearResults();

    (data.entries || []).forEach(function (entry) {
      resultHost.appendChild(makeEntry(entry));
    });

    if (!data.entries || !data.entries.length) {
      resultHost.appendChild(makePlaceholder("这份索引里没有可用条目。"));
    }

    (data.rejected || []).forEach(function (item) {
      var li = document.createElement("li");
      li.className = "pl-reject";
      var label = document.createElement("strong");
      label.appendChild(textNode("第 " + item.position + " 条被跳过："));
      li.appendChild(label);
      li.appendChild(textNode(item.reason));
      rejectedHost.appendChild(li);
    });
    setRejectedVisible(rejectedHost.firstChild !== null);
  }

  async function readToken() {
    var response = await fetch("/api/settings", { cache: "no-cache" });
    if (!response.ok) throw new Error("读取本机令牌失败（HTTP " + response.status + "）");
    var body = await response.json();
    var token = body && body.local_token ? String(body.local_token) : "";
    if (!token) throw new Error("本机未生成就绪令牌，请先启动服务后再试");
    return token;
  }

  async function refreshInstalledMap() {
    try {
      var response = await fetch("/api/plugins", { cache: "no-cache" });
      if (!response.ok) return;
      var body = await response.json();
      installedMap = {};
      (body.plugins || []).forEach(function (plugin) {
        installedMap[plugin.id] = plugin.version;
      });
    } catch (error) {
      // 已装状态只是标注用，拿不到就按「未安装」展示，不打断拉清单
    }
  }

  function markInstalled(btn, entry) {
    installedMap[entry.id] = entry.version;
    btn.textContent = "覆盖安装";
    btn.classList.add("pl-install-ghost");
    btn.setAttribute("data-installed", "true");
  }

  async function requestInstall(entry, replace) {
    var token = await readToken();
    var response = await fetch("/api/plugins/install-url", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-JZO-Token": token },
      body: JSON.stringify({ url: entry.zip_url, replace: replace })
    });
    var data = await response.json().catch(function () {
      return null;
    });
    if (!response.ok) {
      var detail = data && data.detail;
      var message =
        detail && typeof detail === "object" && detail.message
          ? detail.message
          : typeof detail === "string"
            ? detail
            : "HTTP " + response.status;
      var error = new Error(message);
      error.status = response.status;
      throw error;
    }
    return data;
  }

  async function installEntry(entry, btn) {
    var replace = btn.getAttribute("data-installed") === "true";
    btn.disabled = true;
    btn.setAttribute("aria-busy", "true");
    var idleLabel = btn.textContent;
    btn.textContent = "下载并安装中…";
    setStatus("正在从 " + entry.id + " 的直链下载 zip 并校验安装…", "info");

    try {
      var data = await requestInstall(entry, replace);
      markInstalled(btn, entry);
      setStatus(
        "已安装 " + data.plugin.name + " v" + data.plugin.version +
        "。底座发现接口即刻生效，无需重启。",
        "ok"
      );
    } catch (error) {
      var message = error && error.message ? error.message : String(error);
      if (error && error.status === 409 && !replace) {
        // 卡片状态可能过期：底座说已存在，就当场问用户要不要覆盖
        btn.textContent = idleLabel;
        btn.disabled = false;
        btn.setAttribute("aria-busy", "false");
        if (window.confirm("本机已安装 " + entry.id + "。覆盖为清单里的 v" + entry.version + "？")) {
          btn.setAttribute("data-installed", "true");
          await installEntry(entry, btn);
        } else {
          setStatus("已取消覆盖，本机原有插件保持不变。", "info");
        }
        return;
      }
      btn.textContent = idleLabel;
      setStatus("在线安装失败：" + message + "（可点卡片上的 zip 直链手动下载后拖进工作台安装）", "down");
    } finally {
      btn.disabled = false;
      btn.setAttribute("aria-busy", "false");
    }
  }

  function makeInstallButton(entry) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "q-button pl-install";
    var installedVersion = installedMap[entry.id];
    if (installedVersion) {
      btn.textContent = "覆盖安装";
      btn.classList.add("pl-install-ghost");
      btn.setAttribute("data-installed", "true");
      btn.title = "本机已装 v" + installedVersion + "，点击覆盖为清单里的 v" + entry.version;
    } else {
      btn.textContent = "在线安装";
    }
    btn.addEventListener("click", function () {
      installEntry(entry, btn);
    });
    return btn;
  }

  async function pullIndex(event) {
    if (event) event.preventDefault();
    var url = (urlInput.value || "").trim();
    if (!url) {
      setStatus("请先填入一个索引地址（默认已预填官方 Raw 直链）。", "warn");
      return;
    }

    clearResults();
    fetchBtn.disabled = true;
    fetchBtn.setAttribute("aria-busy", "true");
    setStatus("正在向该地址发起一次只读请求…", "info");

    try {
      await refreshInstalledMap();
      var token = await readToken();
      var response = await fetch("/api/plugins/index", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-JZO-Token": token },
        body: JSON.stringify({ url: url })
      });
      var data = await response.json().catch(function () {
        return null;
      });
      if (!response.ok) {
        var detail = data && data.detail;
        var message = typeof detail === "string" ? detail : "HTTP " + response.status;
        setStatus("没有取到列表：" + message, "down");
        resultHost.appendChild(makePlaceholder("本次没有取到任何条目。"));
        return;
      }

      renderIndex(data);
      var summary =
        "来自 " +
        (data.source_host || "该地址") +
        " · 可用 " +
        data.entry_count +
        " 条" +
        (data.rejected_count ? " · 跳过 " + data.rejected_count + " 条" : "");
      setStatus(summary, "ok");
    } catch (error) {
      setStatus("拉取失败：" + (error && error.message ? error.message : error), "down");
      resultHost.appendChild(makePlaceholder("本次没有取到任何条目。"));
    } finally {
      fetchBtn.disabled = false;
      fetchBtn.setAttribute("aria-busy", "false");
    }
  }

  if (form) form.addEventListener("submit", pullIndex);

  var demoBtn = document.getElementById("plDemoBtn");
  if (demoBtn) {
    demoBtn.addEventListener("click", function () {
      // 本机自带的示例清单：同源的 http 地址，请求出不了这台机器。
      urlInput.value = window.location.origin + "/plugins/index-example";
      urlInput.focus();
      setStatus("已填入本机示例清单地址。想拉真实清单请把它换成你信任的 http(s) 地址。", "info");
    });
  }

  // 首屏不留「可用条目」下面一个空白列表
  resultHost.appendChild(
    makePlaceholder("还没有拉取过任何地址。输入框已预填官方索引的 Raw 直链，点【拉取清单】即可列出可在线安装的插件；也可以换成你自己信任的地址。")
  );
})();
