/**
 * ui_dup_compare.js —— 查重三栏变身（军令·查重三栏）。
 *
 * 只在画布帧跑：审核三栏里的原图栏左移淡出并收起，中间工作台变成
 * 「新题源码（可编辑） | 新题渲染 | 原题渲染」，第三栏从右侧滑出。
 * 一切失败都在这里兜底并交给底座报错诊断，绝不把界面僵在半路。
 *
 * 渲染冻结：中间新题渲染区的 `#edRenderBody` 与 `#edCmpIncoming` 只建一次，
 * 换下一道题时只在既有节点里换内容，不重建容器、不换壳。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var state = coreState.state;
    var el = deps.el;
    var renderDoc = deps.renderDoc;
    var buildExamSource = deps.buildExamSource;
    var setMode = deps.setMode;
    var renderAll = deps.renderAll;
    var publish = deps.publish;
    var dockWarn = deps.dockWarn;
    var errorDetail = deps.errorDetail;
    var dom = deps.dom;
    var colsEl = dom.colsEl;
    var imagePaneEl = dom.imagePaneEl;
    var splitImageEl = dom.splitImageEl;
    var sourceBodyEl = dom.sourceBodyEl;
    var renderBodyEl = dom.renderBodyEl;
    var originalPaneEl = dom.originalPaneEl;
    var originalBodyEl = dom.originalBodyEl;
    var originalIdentEl = dom.originalIdentEl;
    var cmpSourceLabelEl = dom.cmpSourceLabelEl;
    var renderHeadLabelEl = dom.renderHeadLabelEl;

    var openFlag = false;
    var incomingHost = null;
    var originalHost = null;
    var sourceArea = null;
    var currentId = "";
    var hideTimer = 0;
    var reduced = false;
    try {
      reduced = Boolean(window.matchMedia
        && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
    } catch (error) {
      reduced = false;
    }

    /** 整段替换内容而不是重建容器：先离屏装好，再一次性换进去。 */
    function paintDoc(host, doc) {
      if (!host) return;
      var staging = document.createElement("div");
      try {
        renderDoc(staging, doc || {});
      } catch (error) {
        staging.textContent = "这一侧的内容没画出来：" + ((error && error.message) || "未知原因");
        dockWarn("查重渲染失败：" + ((error && error.message) || "未知原因"), errorDetail(error));
      }
      var fragment = document.createDocumentFragment();
      while (staging.firstChild) fragment.appendChild(staging.firstChild);
      if (host.replaceChildren) host.replaceChildren(fragment);
      else {
        host.textContent = "";
        host.appendChild(fragment);
      }
    }

    function ensureIncomingHost() {
      if (incomingHost && renderBodyEl && renderBodyEl.contains(incomingHost)) return incomingHost;
      incomingHost = el("div", "ed-cmp-doc");
      incomingHost.id = "edCmpIncoming";
      incomingHost.setAttribute("data-cmp-persist", "1");
      if (renderBodyEl) {
        renderBodyEl.textContent = "";
        renderBodyEl.appendChild(incomingHost);
      }
      return incomingHost;
    }

    function ensureOriginalHost() {
      if (originalHost && originalBodyEl && originalBodyEl.contains(originalHost)) return originalHost;
      originalHost = el("div", "ed-cmp-doc");
      originalHost.id = "edCmpOriginal";
      originalHost.setAttribute("data-cmp-persist", "1");
      if (originalBodyEl) {
        originalBodyEl.textContent = "";
        originalBodyEl.appendChild(originalHost);
      }
      return originalHost;
    }

    function ensureSourceArea() {
      if (sourceArea && sourceBodyEl && sourceBodyEl.contains(sourceArea)) return sourceArea;
      sourceArea = document.createElement("textarea");
      sourceArea.className = "ed-cmp-source";
      sourceArea.id = "edCmpSource";
      sourceArea.spellcheck = false;
      sourceArea.setAttribute("aria-label", "新题源码，可直接编辑");
      sourceArea.addEventListener("input", function () {
        sourceArea.setAttribute("data-dirty", "true");
      });
      if (sourceBodyEl) {
        sourceBodyEl.textContent = "";
        sourceBodyEl.appendChild(sourceArea);
      }
      return sourceArea;
    }

    function paintChrome(entry) {
      if (originalIdentEl) {
        originalIdentEl.textContent = entry.main_id
          ? ("主库 " + entry.main_id) : "主库原题（已不在）";
      }
      if (cmpSourceLabelEl) cmpSourceLabelEl.hidden = false;
      if (renderHeadLabelEl) renderHeadLabelEl.textContent = "新题渲染";
      if (originalPaneEl) originalPaneEl.hidden = false;
    }

    function paint(entry) {
      if (!entry || typeof entry !== "object") return;
      currentId = String(entry.pool_id || "");
      paintChrome(entry);
      var area = ensureSourceArea();
      var source = "";
      try {
        source = buildExamSource ? buildExamSource(entry.incoming || {}) : "";
      } catch (error) {
        source = "";
      }
      if (area.value !== source) {
        area.value = source;
        area.setAttribute("data-dirty", "false");
      }
      paintDoc(ensureIncomingHost(), entry.incoming || {});
      paintDoc(ensureOriginalHost(), entry.existing || {});
      setMode("compare");
      if (colsEl) colsEl.setAttribute("data-compare", "true");
    }

    function open(entry) {
      try {
        if (!entry) return;
        var first = !openFlag;
        openFlag = true;
        window.clearTimeout(hideTimer);
        if (colsEl) colsEl.setAttribute("data-compare-anim", "on");
        if (imagePaneEl) imagePaneEl.hidden = false;
        if (splitImageEl) splitImageEl.hidden = false;
        paint(entry);
        hideTimer = window.setTimeout(function () {
          if (!openFlag) return;
          if (imagePaneEl) imagePaneEl.hidden = true;
          if (splitImageEl) splitImageEl.hidden = true;
        }, reduced || !first ? 0 : 280);
      } catch (error) {
        dockWarn("查重对比没打开：" + ((error && error.message) || "未知原因"), errorDetail(error));
      }
    }

    function update(entry) {
      if (!openFlag) {
        open(entry);
        return;
      }
      try {
        paint(entry);
      } catch (error) {
        dockWarn("下一道没切过来：" + ((error && error.message) || "未知原因"), errorDetail(error));
      }
    }

    function close(options) {
      var opts = options || {};
      if (!openFlag) return;
      openFlag = false;
      currentId = "";
      window.clearTimeout(hideTimer);
      try {
        if (imagePaneEl) imagePaneEl.hidden = false;
        if (splitImageEl) splitImageEl.hidden = false;
        if (colsEl) {
          colsEl.removeAttribute("data-compare-anim");
          colsEl.removeAttribute("data-compare");
        }
        if (cmpSourceLabelEl) cmpSourceLabelEl.hidden = true;
        if (renderHeadLabelEl) renderHeadLabelEl.textContent = "渲染";
        hideTimer = window.setTimeout(function () {
          if (originalPaneEl) originalPaneEl.hidden = true;
        }, reduced ? 0 : 300);
        setMode(state.items.length ? "review" : "list");
        if (renderAll) renderAll();
      } catch (error) {
        dockWarn("退出查重对比失败：" + ((error && error.message) || "未知原因"), errorDetail(error));
      }
      if (opts.notify !== false && publish) {
        publish("editor.dup_compare", {
          pluginId: coreState.PLUGIN_ID, from: "canvas", phase: "closed",
          reason: String(opts.reason || "user_close")
        });
      }
    }

    document.addEventListener("keydown", function (event) {
      if (event.key !== "Escape" || state.mode !== "compare") return;
      event.preventDefault();
      close({ reason: "user_esc" });
    });

    return {
      close: close,
      currentId: function () { return currentId; },
      isOpen: function () { return openFlag; },
      open: open,
      update: update,
    };
  }

  global.JzoEditorDupCompare = { create: create };
})(window);
