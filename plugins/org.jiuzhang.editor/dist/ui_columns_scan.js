/**
 * ui_columns_scan.js —— 纯图片卷的左栏整卷页图（像 PDF 阅读器一样往下滚）
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 只画「一页一张图」的左栏；题行、源码/渲染两栏仍在 ui_columns.js。
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰别的 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var state = deps.state;
    var safeAssetUri = deps.safeAssetUri;
    var el = deps.el;
    var toast = deps.toast;
    var openCrop = deps.openCrop;
    var renderPageBoxes = deps.renderPageBoxes;
    var imageBodyEl = deps.imageBodyEl;

    /** 一页原卷 → 切图台认的那张「格子」：框选后直接切出新题，不配给任何已有题。 */
    function pageCropItem(page, index) {
      return {
        pageImage: {
          uri: safeAssetUri(page && page.uri) || "",
          page: Number(page && page.page) || index + 1
        },
        batchId: String(state.batchId || ""),
        galleryPage: true,
        question: {}
      };
    }

    function openPageCrop(page, index, cell) {
      if (!safeAssetUri(page && page.uri)) {
        toast("这一页的原卷图取不到，切不了题。", "error");
        return;
      }
      // autoSplit：松开鼠标直接生成新题，老师不必再点一次。
      openCrop(pageCropItem(page, index), index, cell, true);
    }

    function renderPageSlide(page, index) {
      var pageNo = Number(page && page.page) || index + 1;
      var cell = el("div", "ed-img-cell ed-page-cell");
      cell.setAttribute("role", "listitem");
      cell.setAttribute("data-index", String(index));
      cell.setAttribute("data-page-index", String(index));
      var frame = el("div", "ed-img-frame ed-img-page");
      var img = document.createElement("img");
      img.src = safeAssetUri(page && page.uri) || "";
      img.alt = "原卷第 " + pageNo + " 页";
      img.addEventListener("error", function () {
        if (img.parentNode) {
          img.parentNode.replaceChild(el("p", "ed-img-missing", "原卷页读取失败"), img);
        }
      });
      frame.appendChild(img);
      var box = el("div", "ed-img-box");
      box.setAttribute("data-box", "stem");
      frame.appendChild(box);
      var boxCount = renderPageBoxes ? renderPageBoxes(page, index, frame, pageCropItem(page, index)) : 0;
      // 切图台自己的画布/动作条会冒泡到这里：放行，别一松鼠标就重开一次。
      frame.addEventListener("click", function (event) {
        if (!event.target.closest(".ed-crop-canvas, .ed-crop-actions, .ed-crop-hint, .ed-auto-box, .ed-page-boxes")) openPageCrop(page, index, cell);
      });
      cell.appendChild(frame);
      var tools = el("div", "ed-img-tools");
      var cropBtn = el("button", "ed-img-crop-btn", "框选切题");
      cropBtn.type = "button";
      cropBtn.setAttribute("aria-label", "原卷第 " + pageNo + " 页框选切题");
      cropBtn.addEventListener("click", function (event) {
        event.stopPropagation();
        openPageCrop(page, index, cell);
      });
      tools.appendChild(cropBtn);
      cell.appendChild(tools);
      var regions = (page && Array.isArray(page.regions)) ? page.regions : [];
      var pooledCount = regions.filter(function (region) {
        return Boolean(region && region.pending_id);
      }).length;
      var caption = "原卷第 " + pageNo + " 页 · 拖框即生成新题";
      if (pooledCount) {
        caption = "原卷第 " + pageNo + " 页 · 已自动切出 " + pooledCount
          + " 道题排进中间，拖绿框可微调";
      } else if (boxCount) {
        caption = "原卷第 " + pageNo + " 页 · 已自动框出 " + boxCount
          + " 道题，悬停绿框确认或微调";
      }
      cell.appendChild(el("p", "ed-img-caption", caption));
      return cell;
    }

    function emptyColumnNote(text) {
      return el("p", "ed-column-empty", text);
    }

    function renderScanGallery() {
      var pages = Array.isArray(state.pageImages) ? state.pageImages : [];
      pages.forEach(function (page, index) {
        imageBodyEl.appendChild(renderPageSlide(page, index));
      });
      if (!pages.length) {
        imageBodyEl.appendChild(emptyColumnNote(
          "这一批没有可用的原卷页图：请重新拖入文件，或删除这个批次。"));
      }
    }

    return {
      emptyColumnNote: emptyColumnNote,
      openPageCrop: openPageCrop,
      pageCropItem: pageCropItem,
      renderPageSlide: renderPageSlide,
      renderScanGallery: renderScanGallery
    };
  }

  global.JzoColumnsScan = { create: create };
})(window);
