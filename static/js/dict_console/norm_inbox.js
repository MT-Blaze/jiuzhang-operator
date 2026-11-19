/**
 * norm_inbox.js —— 记号标准字典·开集待审区（2.21.0 卡 §4）。
 *
 * 清洗写路遇到的不认识命令进 norm_corrections(pending)，在这里由老师裁决（人闸）：
 * 收编＝confirmed（须给目标代码，从此参与改写）；驳回＝rejected（黑名单，永不再问）。
 * 候选按命中次数倒序（接口已排好），原始代码与目标代码各渲染一份供对照，命中徽标显次数。
 * pending 一律不生效；久未命中由底座 sweep 沉底 archived，本区只展示 pending。
 * 公式经 JzoMath.render＋DOMParser 落节点，绝不拼 innerHTML。整块下架删本文件即可。
 */
(function () {
  "use strict";

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function busy(button, on) {
    if (!button) return;
    button.disabled = on;
    button.setAttribute("aria-busy", on ? "true" : "false");
  }

  function fail(title, error, anchor) {
    window.DcDialog.alert({
      title: title,
      message: error && error.message ? error.message : String(error),
      anchor: anchor
    });
  }

  /** 开集代码存的是命令名（不带反斜杠）；渲染与展示时补上，已是全码则不重复补。 */
  function texOf(code) {
    var text = String(code == null ? "" : code).trim();
    if (!text) return "";
    return text.charAt(0) === "\\" ? text : "\\" + text;
  }

  function bareName(code) {
    var text = String(code == null ? "" : code).trim();
    return text.charAt(0) === "\\" ? text.slice(1) : text;
  }

  function mathNode(tex, className) {
    var span = el("span", className || "dc-norm-math");
    var source = String(tex == null ? "" : tex);
    var html = window.JzoMath ? window.JzoMath.render(source, true) : "";
    var node = null;
    if (html) {
      try {
        node = new DOMParser().parseFromString(html, "text/html").body.firstChild;
      } catch (error) {
        node = null;
      }
    }
    if (node) span.appendChild(document.importNode(node, true));
    else span.textContent = source;
    return span;
  }

  function mount(host) {
    host.textContent = "";
    var head = el("div", "dc-norm-head");
    head.appendChild(el("h3", "dc-panel-title", "开集待审"));
    var badge = el("span", "dc-norm-inbox-badge", "待审 0");
    badge.setAttribute("aria-live", "polite");
    head.appendChild(badge);
    host.appendChild(head);
    host.appendChild(el("p", "dc-panel-hint",
      "清洗遇到的不认识命令在这里候审：收编须给目标代码（从此参与改写），驳回进黑名单永不再问。待审一律不生效。"));
    var countsLine = el("p", "dc-norm-counts");
    host.appendChild(countsLine);
    var listHost = el("div", "dc-norm-inbox-list");
    host.appendChild(listHost);

    function renderCounts(counts) {
      var c = counts || {};
      badge.textContent = "待审 " + (c.pending || 0);
      countsLine.textContent = "待审 " + (c.pending || 0) + " · 已收编 " + (c.confirmed || 0)
        + " · 已驳回 " + (c.rejected || 0) + " · 已沉底 " + (c.archived || 0);
    }

    function load() {
      listHost.textContent = "";
      var loading = el("p", "dc-panel-state", "正在读取开集候选…");
      loading.setAttribute("role", "status");
      listHost.appendChild(loading);
      window.DcClient.fetchJson("/api/norm/corrections?status=pending").then(function (data) {
        if (!host.isConnected) return;
        renderCounts(data.counts);
        listHost.textContent = "";
        var rows = data.corrections || [];
        if (!rows.length) {
          listHost.appendChild(el("p", "dc-panel-state", "暂无待审候选。"));
          return;
        }
        rows.forEach(function (row) { listHost.appendChild(inboxRow(row)); });
        if (window.JzoMath && window.JzoMath.onReady) {
          window.JzoMath.onReady(function () {
            if (!host.isConnected) return;
            listHost.textContent = "";
            rows.forEach(function (row) { listHost.appendChild(inboxRow(row)); });
          });
        }
      }).catch(function (error) {
        if (!host.isConnected) return;
        listHost.textContent = "";
        var box = el("p", "dc-panel-state dc-panel-error", "加载失败：" + error.message);
        box.setAttribute("role", "alert");
        listHost.appendChild(box);
        var retry = el("button", "dc-btn", "重试");
        retry.type = "button";
        retry.addEventListener("click", load);
        listHost.appendChild(retry);
      });
    }

    function decide(row, decision, targetCode, button) {
      busy(button, true);
      var payload = { raw_code: row.raw_code, decision: decision };
      if (targetCode) payload.target_code = targetCode;
      window.DcClient.writeJson("/api/norm/decide", payload).then(function () {
        load();
      }).catch(function (error) {
        busy(button, false);
        fail(decision === "confirmed" ? "收编失败" : "驳回失败", error, button);
      });
    }

    function inboxRow(row) {
      var block = el("section", "dc-norm-inbox-row");
      block.setAttribute("aria-label", "待审命令 " + texOf(row.raw_code));

      var top = el("div", "dc-norm-inbox-top");
      top.appendChild(el("code", "dc-norm-code", texOf(row.raw_code)));
      top.appendChild(el("span", "dc-norm-hit", "命中 " + (row.hit_count || 0) + " 次"));
      block.appendChild(top);

      var compare = el("div", "dc-norm-compare");
      var originalBox = el("div", "dc-norm-compare-cell");
      originalBox.appendChild(el("span", "dc-norm-compare-cap", "原始"));
      originalBox.appendChild(mathNode(texOf(row.raw_code)));
      compare.appendChild(originalBox);

      var suggestedBox = el("div", "dc-norm-compare-cell");
      suggestedBox.appendChild(el("span", "dc-norm-compare-cap", "收编后"));
      var preview = el("div", "dc-norm-preview");
      preview.appendChild(el("span", "dc-norm-muted", "填目标代码后预览"));
      suggestedBox.appendChild(preview);
      compare.appendChild(suggestedBox);
      block.appendChild(compare);

      var targetWrap = el("label", "dc-norm-target");
      targetWrap.appendChild(el("span", "dc-norm-target-cap", "目标代码"));
      var input = el("input", "dc-norm-target-input");
      input.type = "text";
      input.placeholder = "如 leqslant（不带反斜杠）";
      input.setAttribute("aria-label", "收编目标代码 " + texOf(row.raw_code));
      targetWrap.appendChild(input);
      block.appendChild(targetWrap);

      var confirmBtn = el("button", "dc-btn dc-btn-primary dc-norm-confirm", "收编");
      confirmBtn.type = "button";
      confirmBtn.disabled = true;
      var rejectBtn = el("button", "dc-btn dc-norm-reject", "驳回");
      rejectBtn.type = "button";

      input.addEventListener("input", function () {
        var name = bareName(input.value);
        confirmBtn.disabled = !name;
        preview.textContent = "";
        if (name) preview.appendChild(mathNode("\\" + name));
        else preview.appendChild(el("span", "dc-norm-muted", "填目标代码后预览"));
      });
      confirmBtn.addEventListener("click", function () {
        decide(row, "confirmed", bareName(input.value), confirmBtn);
      });
      rejectBtn.addEventListener("click", function () {
        window.DcDialog.open({
          title: "驳回进黑名单",
          message: "把「" + texOf(row.raw_code) + "」驳回？\n驳回后永不再问，也不参与改写。",
          confirmText: "驳回",
          anchor: rejectBtn,
          onConfirm: function () { decide(row, "rejected", "", rejectBtn); }
        });
      });

      var tools = el("div", "dc-norm-inbox-tools");
      tools.appendChild(confirmBtn);
      tools.appendChild(rejectBtn);
      block.appendChild(tools);
      return block;
    }

    load();
  }

  window.DcNormInbox = { mount: mount };
})();