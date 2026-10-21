(function () {
  "use strict";

  // 底座不预置任何索引地址：url 只有一个来源——用户在这页亲手填进来。
  var urlInput = document.getElementById("plIndexUrl");
  var form = document.getElementById("plIndexForm");
  var fetchBtn = document.getElementById("plFetchBtn");
  var statusBox = document.getElementById("plStatus");
  var resultHost = document.getElementById("plResults");
  var rejectedHost = document.getElementById("plRejected");
  var rejectedTitle = document.getElementById("pl-rejected-title");

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
    actions.appendChild(makeLink(entry.zip_url, "下载 zip 包"));

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

  async function pullIndex(event) {
    if (event) event.preventDefault();
    var url = (urlInput.value || "").trim();
    if (!url) {
      setStatus("请先填入一个索引地址。本底座不会替你准备任何地址。", "warn");
      return;
    }

    clearResults();
    fetchBtn.disabled = true;
    fetchBtn.setAttribute("aria-busy", "true");
    setStatus("正在向该地址发起一次只读请求…", "info");

    try {
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
    makePlaceholder("还没有拉取过任何地址。填入地址并点【拉取列表】后，条目会出现在这里。")
  );
})();
