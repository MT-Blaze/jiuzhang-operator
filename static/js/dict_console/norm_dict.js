/**
 * norm_dict.js —— 记号标准字典·闭集五列对照（2.21.0 卡 §4）。
 *
 * 整机库 data/latex_norm.db 住底座，本页是宿主（同源 DcClient），不经沙箱 relay。
 * 五列：①记号族 ②名称 ③各来源代码行＋标签筹码 ④逐行对齐 MathJax 渲染 ⑤默认单选。
 * 闭集内容出厂冻结，老师只写选择（choose）；恢复出厂＝选择回退（reset），出厂默认永不动。
 * 单轴过滤＝记号族筹码＋名称/代码搜索；开集待审区交 DcNormInbox 挂在下方第二块。
 * 公式经 JzoMath.render 取 SVG 串再用 DOMParser 落节点，绝不拼 innerHTML（控制台红线）。
 * 整块下架：删本文件、norm_inbox.js、dict_console_norm.css、catalog 的 notation 分类、
 * panels 的 norm-dict 分支与 dict_console.html 的 MathJax＋本族引用即可。
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

  /** TeX → 节点：JzoMath 渲染失败回空串时降级显示源码，绝不飘红、绝不 innerHTML。 */
  function mathNode(tex, display, className) {
    var span = el("span", className || (display ? "dc-norm-math-block" : "dc-norm-math"));
    var source = String(tex == null ? "" : tex);
    var html = window.JzoMath ? window.JzoMath.render(source, display) : "";
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

  function mount(host, ctx) {
    host.textContent = "";
    var state = { entries: [], families: [], family: "", q: "" };

    var head = el("div", "dc-norm-head");
    head.appendChild(el("h2", "dc-panel-title", "记号标准字典"));
    head.appendChild(el("span", "dc-norm-machine-badge", "整机生效"));
    host.appendChild(head);
    host.appendChild(el("p", "dc-panel-hint",
      "闭集出厂冻结，老师只选默认字形；恢复出厂＝回退出厂默认。整机库随整机备份，不随工作区漂移。"));

    var filterBar = el("div", "dc-norm-filter");
    filterBar.setAttribute("role", "group");
    filterBar.setAttribute("aria-label", "按记号族过滤");
    host.appendChild(filterBar);

    var search = el("input", "dc-norm-search");
    search.type = "search";
    search.placeholder = "搜索名称或代码…";
    search.setAttribute("aria-label", "搜索记号名称或代码");
    search.addEventListener("input", function () {
      state.q = search.value.trim().toLowerCase();
      renderList();
    });
    host.appendChild(search);

    var listHost = el("div", "dc-norm-list");
    listHost.setAttribute("aria-live", "polite");
    host.appendChild(listHost);

    var inboxHost = el("div", "dc-norm-inbox-block");
    host.appendChild(inboxHost);

    function renderChips() {
      filterBar.textContent = "";
      var keys = [""].concat(state.families);
      keys.forEach(function (family) {
        var chip = el("button", "dc-norm-chip", family || "全部");
        chip.type = "button";
        var on = state.family === family;
        chip.classList.toggle("is-on", on);
        chip.setAttribute("aria-pressed", on ? "true" : "false");
        chip.addEventListener("click", function () {
          state.family = family;
          renderChips();
          renderList();
        });
        filterBar.appendChild(chip);
      });
    }

    function matches(entry) {
      if (state.family && entry.category !== state.family) return false;
      if (!state.q) return true;
      if (String(entry.name).toLowerCase().indexOf(state.q) >= 0) return true;
      if (String(entry.entry_key).toLowerCase().indexOf(state.q) >= 0) return true;
      return (entry.variants || []).some(function (variant) {
        return String(variant.latex_code).toLowerCase().indexOf(state.q) >= 0;
      });
    }

    function renderList() {
      listHost.textContent = "";
      var shown = state.entries.filter(matches);
      if (!state.entries.length) {
        listHost.appendChild(el("p", "dc-panel-state",
          "闭集为空：底座启动时种子自举可能失败，请查看控制台日志或重启底座。"));
        return;
      }
      if (!shown.length) {
        listHost.appendChild(el("p", "dc-panel-state", "没有匹配的记号，换个族或关键词试试。"));
        return;
      }
      shown.forEach(function (entry) { listHost.appendChild(entryBlock(entry)); });
    }

    function syncDefault(entry, variantId, block) {
      entry.chosen_default_variant_id = variantId;
      entry.effective_default_variant_id = variantId || entry.factory_default_variant_id;
      var radios = block.querySelectorAll("input[type=radio]");
      Array.prototype.forEach.call(radios, function (radio) {
        radio.checked = Number(radio.value) === entry.effective_default_variant_id;
      });
      var resetBtn = block.querySelector(".dc-norm-reset");
      if (resetBtn) resetBtn.disabled = entry.chosen_default_variant_id == null;
      var stateLine = block.querySelector(".dc-norm-default-state");
      if (stateLine) {
        stateLine.textContent = entry.chosen_default_variant_id == null
          ? "当前：出厂默认" : "当前：老师已选默认";
      }
    }

    function choose(entry, variantId, radio, block) {
      busy(radio, true);
      window.DcClient.writeJson("/api/norm/choose",
        { entry_key: entry.entry_key, variant_id: variantId }).then(function () {
        syncDefault(entry, variantId, block);
      }).catch(function (error) {
        syncDefault(entry, entry.chosen_default_variant_id, block);
        fail("选择默认字形失败", error, radio);
      }).finally(function () { busy(radio, false); });
    }

    function reset(entry, button, block) {
      window.DcDialog.open({
        title: "恢复出厂默认",
        message: "把「" + entry.name + "」的默认字形回退到出厂默认？\n出厂内容本身不会被改动。",
        confirmText: "恢复出厂",
        anchor: button,
        onConfirm: function () {
          button.disabled = true;
          button.setAttribute("aria-busy", "true");
          window.DcClient.writeJson("/api/norm/reset", { entry_key: entry.entry_key })
            .then(function () { syncDefault(entry, null, block); })
            .catch(function (error) { button.disabled = false; fail("恢复出厂失败", error, button); })
            .finally(function () { button.setAttribute("aria-busy", "false"); });
        }
      });
    }

    function variantRow(entry, variant, block) {
      var row = el("div", "dc-norm-vrow");
      var codeCell = el("div", "dc-norm-vcode");
      codeCell.appendChild(el("code", "dc-norm-code", variant.latex_code));
      codeCell.appendChild(el("span", "dc-norm-label", variant.source_label));
      row.appendChild(codeCell);

      var renderCell = el("div", "dc-norm-vrender");
      if (variant.render_supported) {
        renderCell.appendChild(mathNode(variant.latex_code, true));
      } else {
        renderCell.appendChild(el("code", "dc-norm-code", variant.latex_code));
        renderCell.appendChild(el("span", "dc-norm-unsupported",
          variant.render_note || "此字形 MathJax 不支持渲染，已排除改写"));
      }
      row.appendChild(renderCell);

      var pickCell = el("div", "dc-norm-vpick");
      var radio = el("input", "dc-norm-radio");
      radio.type = "radio";
      radio.name = "dc-norm-default-" + entry.entry_key;
      radio.value = String(variant.id);
      radio.checked = variant.id === entry.effective_default_variant_id;
      radio.setAttribute("aria-label",
        entry.name + " 默认字形 " + variant.latex_code + "（" + variant.source_label + "）");
      radio.addEventListener("change", function () {
        if (radio.checked) choose(entry, variant.id, radio, block);
      });
      pickCell.appendChild(radio);
      row.appendChild(pickCell);
      return row;
    }

    function entryBlock(entry) {
      var block = el("section", "dc-norm-entry");
      block.setAttribute("aria-label", entry.name);

      var top = el("div", "dc-norm-entry-top");
      top.appendChild(el("span", "dc-norm-family", entry.category));
      var nameBox = el("div", "dc-norm-name-box");
      nameBox.appendChild(el("span", "dc-norm-name", entry.name));
      nameBox.appendChild(el("code", "dc-norm-key", entry.entry_key));
      top.appendChild(nameBox);
      var resetBtn = el("button", "dc-btn dc-norm-reset", "恢复出厂");
      resetBtn.type = "button";
      resetBtn.disabled = entry.chosen_default_variant_id == null;
      resetBtn.addEventListener("click", function () { reset(entry, resetBtn, block); });
      top.appendChild(resetBtn);
      block.appendChild(top);

      block.appendChild(el("p", "dc-norm-default-state",
        entry.chosen_default_variant_id == null ? "当前：出厂默认" : "当前：老师已选默认"));

      var cols = el("div", "dc-norm-vhead");
      cols.appendChild(el("span", "dc-norm-vcode", "代码 / 来源"));
      cols.appendChild(el("span", "dc-norm-vrender", "渲染"));
      cols.appendChild(el("span", "dc-norm-vpick", "默认"));
      block.appendChild(cols);

      (entry.variants || []).forEach(function (variant) {
        block.appendChild(variantRow(entry, variant, block));
      });
      return block;
    }

    var loading = el("p", "dc-panel-state", "正在读取记号标准字典…");
    loading.setAttribute("role", "status");
    listHost.appendChild(loading);

    window.DcClient.fetchJson("/api/norm/entries").then(function (data) {
      if (!host.isConnected) return;
      state.entries = data.entries || [];
      state.families = data.families || [];
      renderChips();
      renderList();
      if (window.JzoMath && window.JzoMath.onReady) {
        window.JzoMath.onReady(function () { if (host.isConnected) renderList(); });
      }
    }).catch(function (error) {
      if (!host.isConnected) return;
      listHost.textContent = "";
      var box = el("p", "dc-panel-state dc-panel-error", "加载失败：" + error.message);
      box.setAttribute("role", "alert");
      listHost.appendChild(box);
      var retry = el("button", "dc-btn", "重试");
      retry.type = "button";
      retry.addEventListener("click", function () { mount(host, ctx); });
      listHost.appendChild(retry);
    });

    if (window.DcNormInbox) window.DcNormInbox.mount(inboxHost);
  }

  window.DcNormDict = { mount: mount };
})();