/**
 * 宿主自绘对话框（军令 #16 模块一）：改名、新建文件夹这类「要打字」的确认。
 *
 * 为什么不用 window.prompt/confirm：
 * 浏览器的原生框样式不可控、在窄屏与沉浸态会跳出去，而且不能带上下文
 * （例如「把哪个插件放进新文件夹」）。这里用 focus trap + Esc + 焦点归位，
 * 满足 AGENTS §6 的可访问性底线。
 *
 * 只用 textContent 落文案，绝不拼 innerHTML（AGENTS §5）。
 */
(function () {
  "use strict";

  var active = null;

  function close(result) {
    if (!active) return;
    var box = active;
    active = null;
    document.removeEventListener("keydown", onKeydown, true);
    if (box.backdrop.parentNode) box.backdrop.parentNode.removeChild(box.backdrop);
    if (box.anchor && typeof box.anchor.focus === "function") box.anchor.focus();
    if (typeof box.done === "function") box.done(result);
  }

  function onKeydown(event) {
    if (!active) return;
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      close(null);
      return;
    }
    if (event.key !== "Tab") return;
    var focusables = active.field ? [active.field, active.ok, active.cancel] : [active.ok, active.cancel];
    var index = focusables.indexOf(document.activeElement);
    var step = event.shiftKey ? -1 : 1;
    var next = focusables[(index + step + focusables.length) % focusables.length];
    event.preventDefault();
    if (next) next.focus();
  }

  /**
   * @param {Object} spec {title, message, value, placeholder, confirmText, cancelText,
   *                       requireText, anchor, done(result)}
   *   result：null = 取消；{text} = 文本框确认；true = 无文本框确认。
   */
  function open(spec) {
    var options = spec || {};
    close(null);

    var backdrop = document.createElement("div");
    backdrop.className = "ws-dialog-backdrop";
    var box = document.createElement("div");
    box.className = "ws-dialog";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("aria-labelledby", "wsDialogTitle");

    var title = document.createElement("h2");
    title.className = "ws-dialog-title";
    title.id = "wsDialogTitle";
    title.textContent = String(options.title || "请确认");
    box.appendChild(title);

    if (options.message) {
      var lede = document.createElement("p");
      lede.className = "ws-dialog-lede";
      lede.textContent = String(options.message);
      box.appendChild(lede);
    }

    var field = null;
    if (options.value != null || options.placeholder) {
      field = document.createElement("input");
      field.className = "ws-dialog-field";
      field.type = "text";
      field.setAttribute("aria-label", String(options.fieldLabel || options.title || "名称"));
      field.maxLength = Number(options.maxLength) || 40;
      field.value = String(options.value || "");
      if (options.placeholder) field.placeholder = String(options.placeholder);
      box.appendChild(field);
    }

    var tools = document.createElement("div");
    tools.className = "ws-dialog-tools";
    var cancel = document.createElement("button");
    cancel.type = "button";
    cancel.className = "ws-btn ws-btn-sm";
    cancel.textContent = String(options.cancelText || "取消");
    var ok = document.createElement("button");
    ok.type = "button";
    ok.className = "ws-btn ws-btn-sm ws-btn-primary";
    ok.textContent = String(options.confirmText || "确定");
    tools.appendChild(cancel);
    tools.appendChild(ok);
    box.appendChild(tools);

    var error = document.createElement("p");
    error.className = "ws-dialog-error";
    error.setAttribute("role", "alert");
    error.hidden = true;
    box.appendChild(error);

    backdrop.appendChild(box);
    document.body.appendChild(backdrop);
    active = {
      backdrop: backdrop, box: box, field: field, ok: ok, cancel: cancel,
      anchor: options.anchor || null, done: options.done
    };

    function submit() {
      var text = field ? field.value.trim() : "";
      if (field && options.requireText !== false && !text) {
        error.textContent = String(options.emptyText || "名称不能为空。");
        error.hidden = false;
        field.focus();
        return;
      }
      close(field ? { text: text } : true);
    }

    ok.addEventListener("click", submit);
    cancel.addEventListener("click", function () { close(null); });
    backdrop.addEventListener("click", function (event) {
      if (event.target === backdrop) close(null);
    });
    if (field) {
      field.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
          event.preventDefault();
          submit();
        }
      });
      field.focus();
      if (typeof field.select === "function") field.select();
    } else {
      ok.focus();
    }
    document.addEventListener("keydown", onKeydown, true);
  }

  window.JzoDialogs = {
    open: open,
    isOpen: function () { return !!active; },
    /** 改名/新建文件夹用的文本框；done(text) 只在拿到非空文本时调用。 */
    text: function (spec) {
      var options = spec || {};
      var onAccept = options.onAccept;
      open({
        title: options.title, message: options.message, value: options.value,
        placeholder: options.placeholder, fieldLabel: options.fieldLabel,
        maxLength: options.maxLength, confirmText: options.confirmText,
        emptyText: options.emptyText, anchor: options.anchor,
        done: function (result) {
          if (result && typeof onAccept === "function") onAccept(result.text);
        }
      });
    },
    /** 二选一确认；done(true) 只在点【确定】时调用，onCancel 在取消/Esc/遮罩时调用。 */
    confirm: function (spec) {
      var options = spec || {};
      var onAccept = options.onAccept;
      open({
        title: options.title, message: options.message, value: null,
        confirmText: options.confirmText, cancelText: options.cancelText,
        anchor: options.anchor,
        done: function (result) {
          if (result === true) {
            if (typeof onAccept === "function") onAccept();
            return;
          }
          // 宿主侧的安全闸必须知道「用户没答应」：不回调就等于把调用方吊死。
          if (typeof options.onCancel === "function") options.onCancel();
        }
      });
    }
  };
})();
