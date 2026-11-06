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

    /** 只读绿框层：坐标来自 page.regions 的原图像素，只给老师看位置，不吃任何鼠标。 */
    function renderGreenLayer(page) {
      var width = Number(page && page.width) || 0;
      var height = Number(page && page.height) || 0;
      var regions = (page && Array.isArray(page.regions)) ? page.regions : [];
      if (!width || !height || !regions.length) return null;
      var layer = el("div", "ed-green-layer");
      regions.forEach(function (region, regionIndex) {
        var w = Number(region && region.w) || 0;
        var h = Number(region && region.h) || 0;
        if (!(w > 0) || !(h > 0)) return;
        var number = Number(region.no) || regionIndex + 1;
        var box = el("div", "ed-green-box");
        box.setAttribute("data-no", String(number));
        if (region.pending_id) box.setAttribute("data-pending-id", String(region.pending_id));
        box.style.left = ((Number(region.x) || 0) / width * 100) + "%";
        box.style.top = ((Number(region.y) || 0) / height * 100) + "%";
        box.style.width = (w / width * 100) + "%";
        box.style.height = (h / height * 100) + "%";
        box.appendChild(el("span", "ed-green-no", String(number)));
        layer.appendChild(box);
      });
      return layer;
    }

    function renderPageSlide(page, index) {
      var pageNo = Number(page && page.page) || index + 1;
      var cell = el("div", "ed-img-cell ed-page-cell");
      cell.setAttribute("role", "listitem");
      cell.setAttribute("data-index", String(index));
      cell.setAttribute("data-page-index", String(index));
      // 页与页之间只留一道极细虚线 + 页码：整卷像一条连续长纸带。
      if (index > 0) {
        var sep = el("div", "ed-page-sep");
        sep.appendChild(el("span", "ed-page-sep-text", "原卷第 " + pageNo + " 页"));
        cell.appendChild(sep);
      }
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
      var greens = renderGreenLayer(page);
      if (greens) frame.appendChild(greens);
      // 切图台自己的画布/动作条会冒泡到这里：放行，别一松鼠标就重开一次。
      frame.addEventListener("click", function (event) {
        if (!event.target.closest(
            ".ed-crop-canvas, .ed-crop-actions, .ed-crop-hint, .ed-img-tools")) {
          openPageCrop(page, index, cell);
        }
      });
      // 入口浮在页角：页与页之间除了那道虚线，不再插任何按钮。
      var tools = el("div", "ed-img-tools");
      var cropBtn = el("button", "ed-img-crop-btn", "框选切题");
      cropBtn.type = "button";
      cropBtn.setAttribute("aria-label", "原卷第 " + pageNo + " 页框选切题");
      cropBtn.addEventListener("click", function (event) {
        event.stopPropagation();
        openPageCrop(page, index, cell);
      });
      tools.appendChild(cropBtn);
      frame.appendChild(tools);
      cell.appendChild(frame);
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
