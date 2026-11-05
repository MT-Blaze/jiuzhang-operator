/**
 * ui_page_boxes.js —— 原卷页上的自动切分框（绿虚线）与人工微调。
 *
 * 底座在页图条目上带 ``width / height / regions``：``regions`` 是文本层抽出的
 * 每道题像素坐标。解析完成时后端已经把每个框裁好、连同空壳题排进待审池，
 * ``region.pending_id`` 就是那道题在池子里的编号。
 *
 * 这里只负责两件事：
 *   1. 把框画出来，题号常显——一页十几道题也不许认错行；
 *   2. 老师拖框微调后，把新坐标回写批次页图，并重切这道题的题图。
 * 新题入池仍走 ui_crop 的 ``splitPageRegion`` → ``splitFromCrop``，
 * 与手动框选同一条通道。
 *
 * 框没有把整页盖死：层本身 pointer-events:none，只有每个绿框可交互，
 * 框外的点击仍会冒泡到页面的「手动框选切题」入口。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var el = deps.el;
    var dockWarn = deps.dockWarn;
    var hostCall = deps.hostCall;
    var splitPageRegion = deps.splitPageRegion;
    var updatePageRegion = deps.updatePageRegion;
    var coreState = deps.coreState;

    var MIN_SIDE = 24;          // 微调后的最小选区（页面图像素）
    var doneByBatch = {};       // 批次 → 「页:框」集合；重绘后仍是已切状态
    var currentBatch = "";
    var commitTimers = {};      // 「页:框」→ 防抖计时器：拖完再裁，不每动一像素裁一次

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

    /** 这个框对应的待审题：已自动入池的框靠它找回归属，找不到就当普通框。 */
    function pendingItemOf(region) {
      var pendingId = String((region && region.pending_id) || "");
      if (!pendingId) return null;
      var items = (coreState && coreState.state && coreState.state.items) || [];
      for (var index = 0; index < items.length; index += 1) {
        if (String(items[index].pendingId || "") === pendingId) return items[index];
      }
      return null;
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
      // 后端解析完就把框裁成题排进了待审池：这种框显示「已入池」，
      // 但拖拽照样放行——老师发现切偏了，拖一下就能重切那一道题。
      var pooled = Boolean(pendingItemOf(region));
      var pageNo = Number(page && page.page) || pageIndex + 1;
      box.setAttribute("data-no", String(number));
      box.setAttribute("data-page-index", String(pageIndex));
      box.setAttribute("data-region-index", String(regionIndex));
      box.setAttribute("role", "group");
      box.setAttribute("tabindex", "0");
      box.setAttribute("aria-label", pooled
        ? "第 " + number + " 题自动切分框：已入待审池，拖拽可微调并重切"
        : "第 " + number + " 题自动切分框：拖拽移动，拖角微调，回车确认切分");
      if (region.label) box.title = region.label;
      if (finished) box.setAttribute("data-done", "on");
      if (pooled) box.setAttribute("data-pending", "on");
      syncBoxStyle(box, region, pageWidth, pageHeight);

      // 题号常显：一页十几道题、框只有二三十像素高时，标签藏起来就等于没有。
      box.appendChild(el("span", "ed-auto-box-no", String(number)));
      var button = el("button", "ed-auto-box-split",
        pooled ? "已入池" : (finished ? "已切" : "确认切分"));
      button.type = "button";
      if (pooled) button.classList.add("is-pooled");
      button.disabled = pooled || finished;
      if (pooled) button.title = "这道题已排进中间，拖框微调后会自动重切";
      box.appendChild(button);

      ["nw", "n", "ne", "e", "se", "s", "sw", "w"].forEach(function (handle) {
        var node = el("span", "ed-auto-handle");
        node.setAttribute("data-handle", handle);
        node.setAttribute("aria-hidden", "true");
        box.appendChild(node);
      });

      function afterAdjust() {
        if (pooled) queueCommit(pageIndex, regionIndex, region, pageNo);
      }

      bindDrag(box, button, region, pageWidth, pageHeight, layer, afterAdjust);
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
        afterAdjust();
      });
      return box;
    }

    /** 拖完不立刻回写：停手 650ms 才落一次坐标与重切，拖动过程里一次请求都不发。 */
    function queueCommit(pageIndex, regionIndex, region, pageNo) {
      var key = regionKey(pageIndex, regionIndex);
      if (commitTimers[key]) window.clearTimeout(commitTimers[key]);
      commitTimers[key] = window.setTimeout(function () {
        delete commitTimers[key];
        commitRegion(pageIndex, regionIndex, region, pageNo);
      }, 650);
    }

    function markBox(pageIndex, regionIndex, attribute, value) {
      var box = document.querySelector('.ed-auto-box[data-page-index="' + pageIndex
        + '"][data-region-index="' + regionIndex + '"]');
      if (!box) return;
      if (value) box.setAttribute(attribute, value);
      else box.removeAttribute(attribute);
    }

    /**
     * 框被挪过：坐标回写批次页图，同时把这道待审题重切一张题图。
     * 坐标先落库——哪怕重切失败，老师下次打开看到的位置也是对的。
     */
    function commitRegion(pageIndex, regionIndex, region, pageNo) {
      var state = coreState && coreState.state ? coreState.state : {};
      var batchId = String(state.batchId || "");
      var pending = pendingItemOf(region);
      markBox(pageIndex, regionIndex, "data-saving", "on");
      var saving = batchId && hostCall
        ? hostCall("pending.set_pages", { batch_id: batchId, page_images: state.pageImages })
        : Promise.resolve(null);
      var recrop = pending && updatePageRegion
        ? updatePageRegion(pending, region, { page: pageNo })
        : Promise.resolve(null);
      Promise.all([saving, recrop]).then(function () {
        markBox(pageIndex, regionIndex, "data-saving", "");
        markBox(pageIndex, regionIndex, "data-region-saved", "on");
        if (dockWarn && !pending) {
          // 没找到对应题目时只回了坐标：提示一句，别让老师以为题图也换了。
          dockWarn("这一框已保存新位置；它没有对应的待审题，题图未重切。");
        }
      }, function (error) {
        markBox(pageIndex, regionIndex, "data-saving", "");
        if (dockWarn) {
          dockWarn("微调没能存住：" + ((error && error.message) || "未知原因"));
        }
      });
    }

    /** 拖动：框体=移动，手柄=改对应边；用页面图像素记坐标，缩放后也不漂。 */
    function bindDrag(box, button, region, pageWidth, pageHeight, layer, afterAdjust) {
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
          return;
        }
        // 拖完才回写：已入池的框重切题图，没入池的框什么也不做。
        if (afterAdjust) afterAdjust();
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
        // 缩略图上的题块常常只有几像素高：八向手柄的命中区会把框体盖死，
        // 拖动就变成「改上边」。这种框只留框体拖动，改边交给键盘。
        Array.prototype.forEach.call(layer.children, function (node) {
          if (node.getBoundingClientRect().height < 36) node.classList.add("is-thin");
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
