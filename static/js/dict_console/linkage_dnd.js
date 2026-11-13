/**
 * 知识点与考向树共享拖拽器：HTML5 拖拽 + Alt+方向键键盘排序两条路。
 * 列表项带 data-id 且 draggable；拖动中实时插位预览，松手（dragend）把
 * 当前 DOM 顺序交给 onOrder 落库。键盘路兼顾触屏与读屏（AGENTS §6）。
 * 整块下架：删本文件与各列的 DcDnd.attach 调用即可。
 */
(function () {
  "use strict";

  function closestItem(node, listEl) {
    while (node && node !== listEl) {
      if (node.nodeType === 1 && node.hasAttribute("data-id") && node.parentNode === listEl) return node;
      node = node.parentNode;
    }
    return null;
  }

  function currentIds(listEl) {
    return Array.prototype.map.call(
      listEl.querySelectorAll(":scope > [data-id]"),
      function (item) { return Number(item.getAttribute("data-id")); }
    );
  }

  function focusItem(item) {
    var target = item.querySelector("button") || item;
    if (typeof target.focus === "function") target.focus();
  }

  /**
   * attach(listEl, {onOrder})：onOrder(ids) 收到完整顺序清单，负责写库与回滚。
   * 列表重渲后监听仍在（事件委托在容器上），无需重复挂载。
   */
  function attach(listEl, options) {
    var dragged = null;

    listEl.addEventListener("dragstart", function (event) {
      var item = closestItem(event.target, listEl);
      if (!item) return;
      dragged = item;
      item.classList.add("dkl-dragging");
      if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = "move";
        try { event.dataTransfer.setData("text/plain", item.getAttribute("data-id")); } catch (error) { /* IE 残党 */ }
      }
    });

    listEl.addEventListener("dragover", function (event) {
      if (!dragged) return;
      event.preventDefault();
      if (event.dataTransfer) event.dataTransfer.dropEffect = "move";
      var target = closestItem(event.target, listEl);
      if (!target || target === dragged) return;
      var rect = target.getBoundingClientRect();
      var before = event.clientY - rect.top < rect.height / 2;
      listEl.insertBefore(dragged, before ? target : target.nextSibling);
    });

    listEl.addEventListener("drop", function (event) {
      if (dragged) event.preventDefault();
    });

    listEl.addEventListener("dragend", function () {
      if (!dragged) return;
      dragged.classList.remove("dkl-dragging");
      dragged = null;
      options.onOrder(currentIds(listEl));
    });

    listEl.addEventListener("keydown", function (event) {
      if (!event.altKey || (event.key !== "ArrowUp" && event.key !== "ArrowDown")) return;
      var item = closestItem(event.target, listEl);
      if (!item) return;
      event.preventDefault();
      var prev = item.previousElementSibling;
      var next = item.nextElementSibling;
      // 末位幽灵行不属于成员，不能被换到已排序条目之前。
      if (event.key === "ArrowUp" && prev && prev.hasAttribute("data-id")) {
        listEl.insertBefore(item, prev);
      }
      if (event.key === "ArrowDown" && next && next.hasAttribute("data-id")) {
        listEl.insertBefore(next, item);
      }
      focusItem(item);
      options.onOrder(currentIds(listEl));
    });
  }

  window.DcDnd = { attach: attach, currentIds: currentIds };
})();