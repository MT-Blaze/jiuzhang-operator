/**
 * 控制台自包含对话框：确认 / 告知两用。
 * 不用 window.confirm（样式不可控、窄屏跳出）；焦点陷阱 + Esc + 关闭后焦点归位，
 * 满足 AGENTS §6。文案只走 textContent，绝不拼 innerHTML。
 * 独立于工作台 JzoDialogs：控制台整块下架时不拖任何 ws-* 样式。
 */
(function () {
  "use strict";

  var active = null;

  function close(confirmed) {
    if (!active) return;
    var box = active;
    active = null;
    document.removeEventListener("keydown", onKeydown, true);
    if (box.backdrop.parentNode) box.backdrop.parentNode.removeChild(box.backdrop);
    if (box.anchor && typeof box.anchor.focus === "function") box.anchor.focus();
    if (confirmed && typeof box.onConfirm === "function") box.onConfirm();
    if (!confirmed && typeof box.onCancel === "function") box.onCancel();
  }

  function onKeydown(event) {
    if (!active) return;
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      close(false);
      return;
    }
    if (event.key !== "Tab") return;
    var items = active.focusables;
    var index = items.indexOf(document.activeElement);
    var step = event.shiftKey ? -1 : 1;
    var next = items[(index + step + items.length) % items.length];
    event.preventDefault();
    if (next) next.focus();
  }

  /**
   * spec: {title, message, confirmText, cancelText, alertOnly, anchor, onConfirm, onCancel}
   * alertOnly=true 时只有【知道了】，Esc 与遮罩等价于关闭。
   */
  function open(spec) {
    var options = spec || {};
    close(false);

    var backdrop = document.createElement("div");
    backdrop.className = "dc-dialog-backdrop";
    var box = document.createElement("div");
    box.className = "dc-dialog";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("aria-labelledby", "dcDialogTitle");

    var title = document.createElement("h2");
    title.className = "dc-dialog-title";
    title.id = "dcDialogTitle";
    title.textContent = String(options.title || "提示");
    box.appendChild(title);

    var message = document.createElement("p");
    message.className = "dc-dialog-message";
    message.textContent = String(options.message || "");
    box.appendChild(message);

    var tools = document.createElement("div");
    tools.className = "dc-dialog-tools";
    var focusables = [];
    var cancel = null;
    if (!options.alertOnly) {
      cancel = document.createElement("button");
      cancel.type = "button";
      cancel.className = "dc-btn";
      cancel.textContent = String(options.cancelText || "取消");
      tools.appendChild(cancel);
      focusables.push(cancel);
    }
    var ok = document.createElement("button");
    ok.type = "button";
    ok.className = "dc-btn dc-btn-primary";
    ok.textContent = String(options.confirmText || (options.alertOnly ? "知道了" : "确定"));
    tools.appendChild(ok);
    focusables.push(ok);
    box.appendChild(tools);

    backdrop.appendChild(box);
    document.body.appendChild(backdrop);
    active = {
      backdrop: backdrop, focusables: focusables,
      anchor: options.anchor || document.activeElement,
      onConfirm: options.onConfirm, onCancel: options.onCancel
    };

    ok.addEventListener("click", function () { close(true); });
    if (cancel) cancel.addEventListener("click", function () { close(false); });
    backdrop.addEventListener("click", function (event) {
      if (event.target === backdrop) close(false);
    });
    document.addEventListener("keydown", onKeydown, true);
    ok.focus();
  }

  window.DcDialog = {
    open: open,
    alert: function (spec) {
      var options = spec || {};
      options.alertOnly = true;
      open(options);
    },
    isOpen: function () { return !!active; }
  };
})();