/**
 * ui_meta_combo.js —— 公共元数据的「无箭头模糊搜索」输入框（军令：砸掉原生下拉）。
 *
 * 只认宿主给的一份候选：打字才弹悬浮 ul，点中才填值并记住字典 ID；
 * 字典里没有的词，离开输入框时要么清空、要么爆红报错，绝不留一个说不清来路的词。
 * 组件不碰业务，回调都在 create(options) 里交给 ui_std_name。
 */
(function (global) {
  "use strict";

  var SEQ = 0;
  var MAX_MATCHES = 12;

  function text(value) { return String(value == null ? "" : value); }

  function norm(value) {
    return text(value).toLowerCase().replace(/\s+/g, "");
  }

  function create(options) {
    var input = options && options.input;
    if (!input) return null;
    var strict = options.strict !== false;
    var allowFree = Boolean(options.allowFreeText);
    // 考试主体同时吃历史值与学校远程结果：两边同名的，学校那条优先（才认得出学校）。
    var preferRemote = Boolean(options.preferRemote);
    var seq = ++SEQ;
    var items = [];
    var remoteItems = [];
    var matches = [];
    var active = -1;
    var bound = null;
    var open = false;
    var query = "";
    var remoteTimer = 0;
    var remoteSeq = 0;
    var invalidTimer = 0;

    var menu = document.createElement("ul");
    menu.className = "ep-pick-menu";
    menu.id = "epPickMenu" + seq;
    menu.setAttribute("role", "listbox");
    menu.hidden = true;
    document.body.appendChild(menu);

    input.classList.add("ep-pick");
    input.setAttribute("autocomplete", "off");
    input.setAttribute("role", "combobox");
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-expanded", "false");
    input.setAttribute("aria-controls", menu.id);

    function close() {
      open = false;
      active = -1;
      menu.hidden = true;
      menu.textContent = "";
      input.setAttribute("aria-expanded", "false");
      input.removeAttribute("aria-activedescendant");
    }

    function position() {
      var rect = input.getBoundingClientRect();
      var height = Math.min(224, window.innerHeight - 16);
      var below = window.innerHeight - rect.bottom;
      var top = below >= 160 ? rect.bottom + 4 : Math.max(8, rect.top - Math.min(height, 220) - 4);
      menu.style.left = Math.round(rect.left) + "px";
      menu.style.top = Math.round(top) + "px";
      menu.style.width = Math.round(Math.max(rect.width, 168)) + "px";
    }

    function show() {
      if (!query) { close(); return; }
      open = true;
      menu.hidden = false;
      input.setAttribute("aria-expanded", "true");
      position();
    }

    function allItems() {
      var seen = {};
      var out = [];
      var pool = preferRemote ? remoteItems.concat(items) : items.concat(remoteItems);
      pool.forEach(function (item) {
        if (!item) return;
        // 同名只留一条：历史主体与学校字典经常同名，留错了就认不出「主体是学校」。
        var key = norm(item.name) || ("id:" + text(item.id));
        if (!key || seen[key]) return;
        seen[key] = true;
        out.push(item);
      });
      return out;
    }

    function scoreOf(item, needle) {
      var name = norm(item.name);
      if (!name) return 0;
      if (name === needle) return 4;
      if (name.indexOf(needle) === 0) return 3;
      if (name.indexOf(needle) >= 0) return 2;
      var aliases = Array.isArray(item.aliases) ? item.aliases : [];
      for (var i = 0; i < aliases.length; i += 1) {
        var alias = norm(aliases[i]);
        if (alias && (alias === needle || alias.indexOf(needle) >= 0)) return 1;
      }
      return 0;
    }

    function findExact(value) {
      var needle = norm(value);
      if (!needle) return null;
      var pool = allItems();
      for (var i = 0; i < pool.length; i += 1) {
        if (norm(pool[i].name) === needle) return pool[i];
        var aliases = Array.isArray(pool[i].aliases) ? pool[i].aliases : [];
        for (var j = 0; j < aliases.length; j += 1) {
          if (norm(aliases[j]) === needle) return pool[i];
        }
      }
      return null;
    }

    function mergeInto(target, source) {
      if (!Array.isArray(source)) return;
      source.forEach(function (item) {
        if (item && text(item.name)) target.push(item);
      });
    }

    function render() {
      var needle = norm(query);
      if (!needle) { close(); return; }
      var scored = [];
      allItems().forEach(function (item) {
        var score = scoreOf(item, needle);
        if (score > 0) scored.push({ item: item, score: score });
      });
      scored.sort(function (a, b) {
        if (b.score !== a.score) return b.score - a.score;
        if (a.item.name.length !== b.item.name.length) {
          return a.item.name.length - b.item.name.length;
        }
        return a.item.name.localeCompare(b.item.name, "zh");
      });
      matches = scored.slice(0, MAX_MATCHES).map(function (row) { return row.item; });
      active = matches.length ? 0 : -1;
      menu.textContent = "";
      if (!matches.length) {
        var empty = document.createElement("li");
        empty.className = "ep-pick-empty";
        empty.textContent = options.emptyText || ("字典里没有「" + query + "」");
        menu.appendChild(empty);
      } else {
        matches.forEach(function (item, index) {
          var row = document.createElement("li");
          row.className = "ep-pick-item";
          row.id = menu.id + "-" + index;
          row.setAttribute("role", "option");
          row.setAttribute("data-active", index === active ? "true" : "false");
          var name = document.createElement("span");
          name.className = "ep-pick-name";
          name.textContent = item.name;
          row.appendChild(name);
          if (item.hint) {
            var hint = document.createElement("span");
            hint.className = "ep-pick-hint";
            hint.textContent = item.hint;
            row.appendChild(hint);
          }
          row.addEventListener("mousedown", function (event) {
            event.preventDefault();
            pick(item);
          });
          menu.appendChild(row);
        });
        var current = matches[active];
        if (current) input.setAttribute("aria-activedescendant", menu.id + "-" + active);
      }
      show();
    }

    function move(step) {
      if (!matches.length) return;
      active = (active + step + matches.length) % matches.length;
      var rows = menu.querySelectorAll(".ep-pick-item");
      for (var i = 0; i < rows.length; i += 1) {
        rows[i].setAttribute("data-active", i === active ? "true" : "false");
      }
      if (rows[active]) {
        input.setAttribute("aria-activedescendant", rows[active].id);
        if (rows[active].scrollIntoView) rows[active].scrollIntoView({ block: "nearest" });
      }
    }

    function clearInvalid() {
      window.clearTimeout(invalidTimer);
      input.classList.remove("is-invalid");
      input.removeAttribute("aria-invalid");
      input.removeAttribute("data-pick-error");
    }

    function flagInvalid(message) {
      input.classList.add("is-invalid");
      input.setAttribute("aria-invalid", "true");
      input.setAttribute("data-pick-error", message || "字典里没有这一项");
      input.title = message || "字典里没有这一项，请从候选里选";
      window.clearTimeout(invalidTimer);
      invalidTimer = window.setTimeout(function () {
        if (String(input.value || "").trim()) {
          // 留着红标：老师没改之前，错误一直看得见。
          return;
        }
        clearInvalid();
      }, 1800);
    }

    function notify() {
      if (typeof options.onChange === "function") options.onChange();
    }

    function pick(item) {
      input.value = text(item.name);
      bound = item;
      clearInvalid();
      close();
      input.focus();
      if (typeof options.onPick === "function") options.onPick(item);
      if (typeof options.onAccept === "function") options.onAccept(item, text(item.name));
      notify();
    }

    /** 离开输入框才判词：打得半截不打断，松手那一刻才要一个确定的字典项。 */
    function validate() {
      var raw = text(input.value).trim();
      if (!raw) {
        bound = null;
        clearInvalid();
        notify();
        return;
      }
      var exact = findExact(raw);
      if (exact) {
        bound = exact;
        if (text(exact.name) !== raw) input.value = text(exact.name);
        clearInvalid();
        if (typeof options.onAccept === "function") options.onAccept(exact, raw);
        notify();
        return;
      }
      if (allowFree) {
        bound = null;
        flagInvalid("字典里没有「" + raw + "」，确认后按手填主体记住");
        notify();
        return;
      }
      input.value = "";
      bound = null;
      if (strict) flagInvalid("字典里没有「" + raw + "」，已清空");
      notify();
    }

    function requestRemote(value) {
      if (typeof options.remote !== "function" || !value) return;
      window.clearTimeout(remoteTimer);
      var token = ++remoteSeq;
      remoteTimer = window.setTimeout(function () {
        options.remote(value, function (rows) {
          if (token !== remoteSeq) return;
          remoteItems = [];
          mergeInto(remoteItems, rows);
          if (open) render();
        });
      }, 160);
    }

    input.addEventListener("input", function () {
      query = text(input.value).trim();
      bound = null;
      clearInvalid();
      if (!query) { close(); return; }
      render();
      requestRemote(query);
    });

    input.addEventListener("keydown", function (event) {
      var key = String(event.key || "");
      if (key === "ArrowDown") {
        event.preventDefault();
        if (!open) render();
        else move(1);
        return;
      }
      if (key === "ArrowUp") {
        event.preventDefault();
        if (open) move(-1);
        return;
      }
      if (key === "Enter") {
        if (!open || !matches.length) return;
        event.preventDefault();
        pick(matches[active] || matches[0]);
        return;
      }
      if (key === "Escape") {
        if (open) {
          event.preventDefault();
          close();
        }
      }
    });

    input.addEventListener("blur", function () {
      window.setTimeout(function () {
        close();
        validate();
      }, 0);
    });

    window.addEventListener("resize", function () {
      if (open) position();
    });
    window.addEventListener("scroll", function () {
      if (open) close();
    }, true);

    return {
      input: input,
      menu: menu,
      setItems: function (next) { items = Array.isArray(next) ? next.slice() : []; },
      setValue: function (name, id) {
        input.value = text(name);
        var hit = findExact(name);
        if (id == null) {
          bound = hit;
        } else if (hit && text(hit.id) === text(id)) {
          bound = hit;
        } else {
          bound = { id: text(id), name: text(name) };
        }
        clearInvalid();
      },
      getValue: function () { return text(input.value).trim(); },
      getItem: function () { return bound || findExact(input.value); },
      refresh: function () { if (open) render(); },
      clear: function () {
        input.value = "";
        bound = null;
        clearInvalid();
        close();
      },
      clearInvalid: clearInvalid,
      close: close,
      validate: validate
    };
  }

  global.JzoEditorMetaCombo = { create: create };
})(window);
