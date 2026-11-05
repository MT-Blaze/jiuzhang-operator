/**
 * ui_page_boxes.js —— 原卷页上的自动切分框（绿虚线）与人工微调。
 *
 * 底座在页图条目上带 ``width / height / regions``：``regions`` 是文本层抽出的
 * 每道题像素坐标。这里只负责画框和让老师拖拽微调；真正裁图与建新题仍走
 * ui_crop 的 ``splitPageRegion`` → ``splitFromCrop``，与手动框选同一条通道。
 *
 * 框没有把整页盖死：层本身 pointer-events:none，只有每个绿框可交互，
 * 框外的点击仍会冒泡到页面的「手动框选切题」入口。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var el = deps.el;
    var dockWarn = deps.dockWarn;
    var splitPageRegion = deps.splitPageRegion;
    var coreState = deps.coreState;

    var MIN_SIDE = 24;          // 微调后的最小选区（页面图像素）
    var doneByBatch = {};       // 批次 → 「页:框」集合；重绘后仍是已切状态
    var currentBatch = "";

    function clamp(value, low, high) {
      return Math.min(Math.max(value, low), high);
    }

    function percent(value, total) {
      return (Number(value) / Number(total) * 100) + "%";
    }

    function regionKey(pageIndex, regionIndex) {
      return String(pageIndex) + ":" + String(regionIndex);
    }

    function doneOfBatch() {
      var batchId = String(coreState.state.batchId || "");
      if (batchId !== currentBatch) {
        currentBatch = batchId;
        doneByBatch = {};
      }
      return doneByBatch;
    }

    function syncBoxStyle(box, region, pageWidth, pageHeight) {
      box.style.left = percent(region.x, pageWidth);
      box.style.top = percent(region.y, pageHeight);
      box.style.width = percent(region.w, pageWidth);
      box.style.height = percent(region.h, pageHeight);
    }

    function applyRegion(box, region, pageWidth, pageHeight) {
      region.x = Math.round(clamp(region.x, 0, pageWidth - MIN_SIDE));
      region.y = Math.round(clamp(region.y, 0, pageHeight - MIN_SIDE));
      region.w = Math.round(clamp(region.w, MIN_SIDE, pageWidth - region.x));
      region.h = Math.round(clamp(region.h, MIN_SIDE, pageHeight - region.y));
      syncBoxStyle(box, region, pageWidth, pageHeight);
    }

    /** 把一个绿框钉到页图坐标上：拖框移动、拖八向手柄改边、回车确认切分。 */
    function buildBox(page, pageIndex, region, regionIndex, item, pageWidth, pageHeight,
                      done, layer) {
      var number = Number(region.no) || regionIndex + 1;
      var box = el("div", "ed-auto-box");
      var key = regionKey(pageIndex, regionIndex);
      var finished = Boolean(done[key]);
      box.setAttribute("data-no", String(number));
      box.setAttribute("data-page-index", String(pageIndex));
      box.setAttribute("data-region-index", String(regionIndex));
      box.setAttribute("role", "group");
      box.setAttribute("tabindex", "0");
      box.setAttribute("aria-label",
        "第 " + number + " 题自动切分框：拖拽移动，拖角微调，回车确认切分");
      if (region.label) box.title = region.label;
      if (finished) box.setAttribute("data-done", "on");
      syncBoxStyle(box, region, pageWidth, pageHeight);

      box.appendChild(el("span", "ed-auto-box-tag", "第 " + number + " 题"));
      var button = el("button", "ed-auto-box-split", finished ? "已切" : "确认切分");
      button.type = "button";
      button.disabled = finished;
      box.appendChild(button);

      ["nw", "n", "ne", "e", "se", "s", "sw", "w"].forEach(function (handle) {
        var node = el("span", "ed-auto-handle");
        node.setAttribute("data-handle", handle);
        node.setAttribute("aria-hidden", "true");
        box.appendChild(node);
      });

      bindDrag(box, button, region, pageWidth, pageHeight, layer);
      bindConfirm(box, button, page, pageIndex, region, regionIndex, item, done);

      box.addEventListener("click", function (event) {
        // 框自己的点击不能冒泡成「在页面上再开一个手动切图台」。
        event.stopPropagation();
      });
      box.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          if (!button.disabled) button.click();
          return;
        }
        var step = event.shiftKey ? 16 : 4;
        var dx = 0;
        var dy = 0;
        if (event.key === "ArrowLeft") dx = -step;
        else if (event.key === "ArrowRight") dx = step;
        else if (event.key === "ArrowUp") dy = -step;
        else if (event.key === "ArrowDown") dy = step;
        else return;
        event.preventDefault();
        event.stopPropagation();
        if (event.shiftKey) {
          region.w += dx;
          region.h += dy;
        } else {
          region.x += dx;
          region.y += dy;
        }
        applyRegion(box, region, pageWidth, pageHeight);
      });
      return box;
    }

    /** 拖动：框体=移动，手柄=改对应边；用页面图像素记坐标，缩放后也不漂。 */
    function bindDrag(box, button, region, pageWidth, pageHeight, layer) {
      var drag = null;

      function start(event, mode, handle) {
        if (event.button !== 0) return;
        event.preventDefault();
        event.stopPropagation();
        var rect = layer.getBoundingClientRect();
        if (!rect.width || !rect.height) return;
        drag = {
          mode: mode,
          handle: handle || "",
          startX: event.clientX,
          startY: event.clientY,
          region: { x: region.x, y: region.y, w: region.w, h: region.h },
          scaleX: pageWidth / rect.width,
          scaleY: pageHeight / rect.height,
          moved: false
        };
        if (box.setPointerCapture && event.pointerId != null) {
          try { box.setPointerCapture(event.pointerId); } catch (error) { /* 捕获失败也照常拖 */ }
        }
        box.classList.add("is-dragging");
        window.addEventListener("pointermove", onMove, true);
        window.addEventListener("pointerup", onUp, true);
        window.addEventListener("pointercancel", onUp, true);
      }

      function onMove(event) {
        if (!drag) return;
        event.preventDefault();
        var dx = (event.clientX - drag.startX) * drag.scaleX;
        var dy = (event.clientY - drag.startY) * drag.scaleY;
        if (Math.abs(dx) > 1 || Math.abs(dy) > 1) drag.moved = true;
        var base = drag.region;
        var left = base.x;
        var top = base.y;
        var right = base.x + base.w;
        var bottom = base.y + base.h;
        if (drag.mode === "move") {
          left = clamp(base.x + dx, 0, pageWidth - base.w);
          top = clamp(base.y + dy, 0, pageHeight - base.h);
        } else {
          var handle = drag.handle;
          if (handle.indexOf("w") >= 0) left = clamp(base.x + dx, 0, right - MIN_SIDE);
          if (handle.indexOf("e") >= 0) right = clamp(base.x + base.w + dx, left + MIN_SIDE, pageWidth);
          if (handle.indexOf("n") >= 0) top = clamp(base.y + dy, 0, bottom - MIN_SIDE);
          if (handle.indexOf("s") >= 0) bottom = clamp(base.y + base.h + dy, top + MIN_SIDE, pageHeight);
        }
        region.x = left;
        region.y = top;
        region.w = right - left;
        region.h = bottom - top;
        applyRegion(box, region, pageWidth, pageHeight);
      }

      function onUp(event) {
        if (!drag) return;
        var moved = drag.moved;
        drag = null;
        box.classList.remove("is-dragging");
        if (box.releasePointerCapture && event.pointerId != null) {
          try { box.releasePointerCapture(event.pointerId); } catch (error) { /* 已释放 */ }
        }
        window.removeEventListener("pointermove", onMove, true);
        window.removeEventListener("pointerup", onUp, true);
        window.removeEventListener("pointercancel", onUp, true);
        if (!moved) {
          box.classList.add("is-selected");
          button.focus();
        }
      }

      box.addEventListener("pointerdown", function (event) {
        if (event.target.closest(".ed-auto-box-split, .ed-auto-handle")) return;
        if (box.getAttribute("data-done") === "on") return;
        start(event, "move", "");
      });
      Array.prototype.forEach.call(box.querySelectorAll(".ed-auto-handle"), function (node) {
        node.addEventListener("pointerdown", function (event) {
          if (box.getAttribute("data-done") === "on") return;
          start(event, "resize", node.getAttribute("data-handle") || "");
        });
      });
    }

    /** 确认切分：先记「已切」再落库；重绘后新 DOM 仍按 done 标记显示已切。 */
    function bindConfirm(box, button, page, pageIndex, region, regionIndex, item, done) {
      button.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        if (button.disabled) return;
        var key = regionKey(pageIndex, regionIndex);
        var pageNo = Number(page && page.page) || pageIndex + 1;
        done[key] = true;
        box.setAttribute("data-done", "on");
        button.disabled = true;
        button.textContent = "切分中…";
        box.classList.add("is-splitting");

        function reset(message) {
          delete done[key];
          box.removeAttribute("data-done");
          box.classList.remove("is-splitting");
          button.disabled = false;
          button.textContent = "确认切分";
          if (message && dockWarn) dockWarn(message);
        }

        Promise.resolve(splitPageRegion(item, region, { page: pageNo, no: region.no }))
          .then(function (created) {
            box.classList.remove("is-splitting");
            if (!created) {
              // splitFromCrop 已经用 dockWarn 说明了原因，这里只把按钮放回去。
              reset("");
              return;
            }
            box.classList.add("is-done");
            button.textContent = "已切";
          }, function (error) {
            reset("确认切分没成功：" + ((error && error.message) || "未知原因"));
          });
      });
    }

    /**
     * 一页原图 → 绿框层。返回这一页实际画出的框数；没有区域就返回 0，
     * 页面照旧可以点「框选切题」手动画。
     */
    function renderPageBoxes(page, pageIndex, frame, item) {
      var regions = (page && Array.isArray(page.regions)) ? page.regions : [];
      if (!regions.length || !frame) return 0;
      var pageWidth = Number(page.width) || 0;
      var pageHeight = Number(page.height) || 0;
      var picture = frame.querySelector("img");

      function mount(width, height) {
        if (!(width > 0) || !(height > 0)) return 0;
        var stale = frame.querySelector(".ed-page-boxes");
        if (stale && stale.parentNode) stale.parentNode.removeChild(stale);
        var layer = el("div", "ed-page-boxes");
        layer.setAttribute("role", "group");
        layer.setAttribute("aria-label",
          "原卷第 " + (Number(page.page) || pageIndex + 1) + " 页自动切分框");
        var done = doneOfBatch();
        regions.forEach(function (region, regionIndex) {
          layer.appendChild(buildBox(page, pageIndex, region, regionIndex, item,
            width, height, done, layer));
        });
        frame.appendChild(layer);
        // 每页十几道题时，单个框可能只有二十来像素高：标签压上去会遮住上一题。
        // 量高必须等这一格挂进文档：renderPageSlide 此刻还没把格子交给左栏，
        // 当场量到的全是 0，标签会被误判成全藏掉。
        requestAnimationFrame(function () {
          if (!layer.parentNode) return;
          Array.prototype.forEach.call(layer.children, function (box) {
            box.classList.toggle("is-tiny", box.getBoundingClientRect().height < 30);
          });
        });
        return regions.length;
      }

      if (pageWidth > 0 && pageHeight > 0) return mount(pageWidth, pageHeight);
      // 老批次没带尺寸：等图片自己报出原始像素再画，绝不拿栏宽瞎换算。
      if (picture && picture.naturalWidth && picture.naturalHeight) {
        return mount(picture.naturalWidth, picture.naturalHeight);
      }
      if (picture) {
        picture.addEventListener("load", function () {
          mount(picture.naturalWidth, picture.naturalHeight);
        }, { once: true });
      }
      return regions.length;
    }

    return {
      MIN_SIDE: MIN_SIDE,
      renderPageBoxes: renderPageBoxes,
    };
  }

  global.JzoEditorPageBoxes = { create: create };
})(window);
