/**
 * 宿主右键菜单（军令 #16 模块一）。
 *
 * 规矩：
 * - 只在底座自己的区域开菜单（左栏插件行、文件夹行、底栏输出区）；
 *   中间画布的右键交给插件自己决定，底座一律不拦。
 * - 菜单是原生 DOM + textContent 拼的，不拼 innerHTML（AGENTS §5）。
 * - 键盘可达：Esc 关、↑↓ 走、Enter/Space 执行、焦点关闭后还给发起元素（AGENTS §6）。
 */
(function () {
  "use strict";

  var openMenu = null;

  function closeMenu(restoreFocus) {
    if (!openMenu) return;
    var owner = openMenu;
    openMenu = null;
    document.removeEventListener("keydown", onKeydown, true);
    window.removeEventListener("blur", onBlur);
    document.removeEventListener("pointerdown", onOutside, true);
    if (owner.el.parentNode) owner.el.parentNode.removeChild(owner.el);
    if (restoreFocus !== false && owner.anchor && typeof owner.anchor.focus === "function") {
      owner.anchor.focus();
    }
  }

  function onKeydown(event) {
    if (!openMenu) return;
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      closeMenu();
      return;
    }
    var buttons = openMenu.buttons;
    var index = buttons.indexOf(document.activeElement);
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (!buttons.length) return;
      var step = event.key === "ArrowDown" ? 1 : -1;
      var next = index < 0 ? (step > 0 ? 0 : buttons.length - 1)
        : (index + step + buttons.length) % buttons.length;
      buttons[next].focus();
      return;
    }
    if (index < 0 && (event.key === "Enter" || event.key === " ")) {
      event.preventDefault();
      if (buttons.length) buttons[0].focus();
    }
  }

  function onBlur() {
    closeMenu(false);
  }

  function onOutside(event) {
    if (openMenu && !openMenu.el.contains(event.target)) closeMenu(false);
  }

  function place(el, x, y) {
    el.style.left = "0px";
    el.style.top = "0px";
    var box = el.getBoundingClientRect();
    var maxX = Math.max(8, window.innerWidth - box.width - 8);
    var maxY = Math.max(8, window.innerHeight - box.height - 8);
    el.style.left = Math.min(Math.max(8, x), maxX) + "px";
    el.style.top = Math.min(Math.max(8, y), maxY) + "px";
  }

  /**
   * 打开一个菜单。
   * @param {Object} spec {x, y, anchor, items:[{label, run, disabled, checked}]}
   */
  function open(spec) {
    var options = spec || {};
    var items = Array.isArray(options.items) ? options.items : [];
    closeMenu(false);
    if (!items.length) return;

    var menu = document.createElement("div");
    menu.className = "ws-menu";
    menu.setAttribute("role", "menu");
    menu.setAttribute("aria-label", options.label || "操作");
    var buttons = [];
    items.forEach(function (item) {
      if (item && item.separator) {
        var line = document.createElement("div");
        line.className = "ws-menu-sep";
        line.setAttribute("role", "separator");
        menu.appendChild(line);
        return;
      }
      var button = document.createElement("button");
      button.type = "button";
      button.className = "ws-menu-item";
      button.setAttribute("role", "menuitem");
      button.textContent = String(item.label || "");
      if (item.disabled) {
        button.disabled = true;
        button.setAttribute("aria-disabled", "true");
      } else {
        buttons.push(button);
      }
      if (typeof item.hint === "string" && item.hint) {
        var hint = document.createElement("span");
        hint.className = "ws-menu-hint";
        hint.textContent = item.hint;
        button.appendChild(hint);
      }
      button.addEventListener("click", function () {
        var run = item.run;
        closeMenu();
        if (typeof run === "function") run();
      });
      menu.appendChild(button);
    });

    document.body.appendChild(menu);
    place(menu, Number(options.x) || 0, Number(options.y) || 0);
    openMenu = { el: menu, buttons: buttons, anchor: options.anchor || null };
    document.addEventListener("keydown", onKeydown, true);
    window.addEventListener("blur", onBlur);
    document.addEventListener("pointerdown", onOutside, true);
    if (buttons.length) buttons[0].focus();
    else menu.focus && menu.focus();
  }

  function isOpen() {
    return !!openMenu;
  }

  window.JzoMenu = { open: open, close: function () { closeMenu(); }, isOpen: isOpen };
})();
