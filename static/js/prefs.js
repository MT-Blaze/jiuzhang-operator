/**
 * 主机偏好的前端读端（军令 #16）。
 *
 * 唯一事实来源永远在后端（data/plugin_state.json，由 /api/plugins 投影下发）；
 * 本文件只做两件事：把下发的树/绑定读成视图用得顺的形状，以及按 GitHub 口径
 * 把时间戳写成「3 天前」——只在渲染那一瞬间算一次，绝不后台实时跳字。
 *
 * 浏览器 localStorage 不再是顺序的落点：清缓存、换浏览器、换机器都不该让老师
 * 排好的左栏一夜回到默认序（v0.9.0 之前确实存在，本模块带一次性迁移）。
 */
(function () {
  "use strict";

  var LEGACY_ORDER_KEY = "jzo.sidebar.order";
  var MIGRATED_KEY = "jzo.sidebar.migrated";

  function asText(value, limit) {
    var text = String(value == null ? "" : value).replace(/\s+/g, " ").trim();
    return text.slice(0, limit || 64);
  }

  /**
   * GitHub 式相对时间。基准时刻由调用方在「点开面板那一瞬」拍一次传进来，
   * 同一批卡片因此共用同一个「现在」，不会渲染到一半跳字。
   */
  function relTime(iso, now) {
    var text = String(iso || "").trim();
    if (!text) return "";
    var then = Date.parse(text);
    if (isNaN(then)) return "";
    var base = now instanceof Date ? now.getTime() : Number(now) || Date.now();
    var seconds = Math.floor((base - then) / 1000);
    if (seconds < 45) return "刚刚";
    var units = [["年", 31536000], ["月", 2592000], ["周", 604800],
      ["天", 86400], ["小时", 3600], ["分钟", 60]];
    for (var i = 0; i < units.length; i += 1) {
      if (seconds >= units[i][1]) return Math.round(seconds / units[i][1]) + " " + units[i][0] + "前";
    }
    return "刚刚";
  }

  function isPluginKey(key) {
    return typeof key === "string" && key.indexOf("plugin:") === 0;
  }

  function isFolderKey(key) {
    return typeof key === "string" && key.indexOf("folder:") === 0;
  }

  function pluginIdOf(key) {
    return isPluginKey(key) ? key.slice(7) : "";
  }

  function newFolderKey() {
    return "folder:" + Date.now().toString(36) + Math.floor(Math.random() * 1e4).toString(36);
  }

  /** 后端下发的树（已含「没排过序的新插件追加在末尾」），形状不对就当没排过。 */
  function readTree(body) {
    var raw = body && Array.isArray(body.sidebar) ? body.sidebar : [];
    var tree = [];
    raw.forEach(function (item) {
      if (!item || typeof item !== "object") return;
      if (item.kind === "folder" && isFolderKey(item.id)) {
        tree.push({
          kind: "folder",
          id: String(item.id),
          name: asText(item.name, 24) || "未命名文件夹",
          children: (Array.isArray(item.children) ? item.children : []).filter(isPluginKey)
        });
      } else if (item.kind === "plugin" && isPluginKey(item.id)) {
        tree.push({ kind: "plugin", id: String(item.id) });
      }
    });
    return tree;
  }

  function treeKeys(tree) {
    var keys = [];
    (tree || []).forEach(function (item) {
      if (item.kind === "folder") {
        keys.push(item.id);
        item.children.forEach(function (child) { keys.push(child); });
      } else keys.push(item.id);
    });
    return keys;
  }

  /** 树上有没有任何「人排过的痕迹」：有文件夹、或顺序与插件清单不同，都算排过。 */
  function treeIsCustomized(tree, plugins) {
    if (!(tree || []).length) return false;
    if (tree.some(function (item) { return item.kind === "folder"; })) return true;
    var listed = (plugins || []).map(function (plugin) { return "plugin:" + plugin.id; });
    var flat = treeKeys(tree).filter(isPluginKey);
    if (flat.length !== listed.length) return false;
    for (var i = 0; i < flat.length; i += 1) {
      if (flat.indexOf(listed[i]) < 0) return false;   // 树上有不在盘的插件：算排过
      if (flat[i] !== listed[i]) return true;          // 顺序不同：排过
    }
    return false;
  }

  /** 把 v0.9.0 之前存在浏览器里的拖拽顺序搬成一颗扁平树（只搬一次）。 */
  function legacyTree() {
    var keys;
    try {
      var parsed = JSON.parse(window.localStorage.getItem(LEGACY_ORDER_KEY) || "[]");
      keys = Array.isArray(parsed) ? parsed.filter(isPluginKey) : [];
    } catch (error) {
      return [];
    }
    if (!keys.length) return [];
    try {
      if (window.localStorage.getItem(MIGRATED_KEY)) return [];
    } catch (error) { /* 读不到迁移标记就再试一次，写树本身是幂等的 */ }
    return keys.map(function (key) { return { kind: "plugin", id: key }; });
  }

  function markLegacyMigrated() {
    try {
      window.localStorage.setItem(MIGRATED_KEY, "1");
    } catch (error) { /* 记不住标记只意味着下次可能再问一次，不影响结果 */ }
  }

  function pluginRows(body) {
    return body && Array.isArray(body.plugins) ? body.plugins : [];
  }

  function findPlugin(body, pluginId) {
    var rows = pluginRows(body);
    for (var i = 0; i < rows.length; i += 1) {
      if (rows[i] && rows[i].id === pluginId) return rows[i];
    }
    return null;
  }

  // ============ 组合键归一（与后端 plugin_state.canonical_combo 同一口径） ============
  // 后端是唯一事实来源（写非法值一律 400）；前端做同一份判断只为当场反馈，
  // 让设置页的输入框不必等一次网络往返才知道自己写歪了。
  var MODIFIER_ORDER = ["Ctrl", "Alt", "Shift", "Meta"];
  var MODIFIER_ALIASES = {
    CTRL: "Ctrl", CONTROL: "Ctrl",
    ALT: "Alt", OPTION: "Alt",
    SHIFT: "Shift",
    META: "Meta", CMD: "Meta", COMMAND: "Meta", SUPER: "Meta", WIN: "Meta"
  };
  var KEY_ALIASES = {
    ESCAPE: "Esc", ESC: "Esc",
    SPACE: "Space", SPACEBAR: "Space",
    TAB: "Tab", ENTER: "Enter", RETURN: "Enter",
    HOME: "Home", END: "End",
    DELETE: "Delete", DEL: "Delete", BACKSPACE: "Backspace",
    ARROWUP: "ArrowUp", ARROWDOWN: "ArrowDown",
    ARROWLEFT: "ArrowLeft", ARROWRIGHT: "ArrowRight",
    PAGEUP: "PageUp", PGUP: "PageUp",
    PAGEDOWN: "PageDown", PGDN: "PageDown",
    PLUS: "+"
  };
  var FUNCTION_KEY = /^F(?:[1-9]|1[0-2])$/i;
  var COMBO = new RegExp(
    "^(?:(?:Ctrl|Alt|Shift|Meta)\\+){1,3}" +
    "(?:[A-Z0-9]|F[1-9]|F1[0-2]|Enter|Esc|Space|Tab|Home|End|Delete|Backspace" +
    "|Arrow(?:Up|Down|Left|Right)|PageUp|PageDown|[-+\\[\\];',./=\\\\])$"
  );

  function canonicalCombo(raw) {
    var text = String(raw == null ? "" : raw).trim();
    if (!text) return "";
    // "Ctrl++"（加号本身是主键）写作 ++：先换成哨兵再拆，免得拆出一个空段
    var parts = text.replace("++", "+PLUS+").split("+").map(function (piece) {
      return piece.trim();
    });
    if (parts.length && !parts[parts.length - 1]) parts.pop();
    if (parts.some(function (piece) { return !piece; })) return "";
    var modifiers = [];
    var key = "";
    for (var index = 0; index < parts.length; index += 1) {
      var piece = parts[index];
      var alias = MODIFIER_ALIASES[piece.toUpperCase()];
      if (alias && index < parts.length - 1) {
        if (modifiers.indexOf(alias) < 0) modifiers.push(alias);
        continue;
      }
      var named = KEY_ALIASES[piece.toUpperCase()];
      if (named) key = named;
      else if (FUNCTION_KEY.test(piece)) key = "F" + piece.slice(1);
      else if (piece.length === 1) key = piece.toUpperCase();
      else key = piece.charAt(0).toUpperCase() + piece.slice(1).toLowerCase();
      break;
    }
    if (!key || !modifiers.length) return "";
    var ordered = MODIFIER_ORDER.filter(function (mod) {
      return modifiers.indexOf(mod) >= 0;
    }).join("+");
    var combo = ordered + "+" + key;
    return COMBO.test(combo) ? combo : "";
  }

  /** KeyboardEvent → 规范形组合键；不带修饰键的裸键回空串（那是输入框和控件的地盘）。 */
  function comboFromEvent(event) {
    if (!event) return "";
    var modifiers = [];
    if (event.ctrlKey) modifiers.push("Ctrl");
    if (event.altKey) modifiers.push("Alt");
    if (event.shiftKey) modifiers.push("Shift");
    if (event.metaKey) modifiers.push("Meta");
    if (!modifiers.length) return "";
    var raw = String(event.key || "");
    if (!raw || raw === "Unidentified") return "";
    if (raw.length === 1 && raw !== " ") raw = raw.toUpperCase();
    if (raw === " ") raw = "Space";
    var key = canonicalCombo("Ctrl+" + raw).slice(5);
    if (!key) return "";
    return modifiers.join("+") + "+" + key;
  }

  /** 卡片/条目上的显示名：老师起的昵称优先，没起过就用官方原名（军令 #16 模块二）。 */
  function displayName(plugin) {
    return asText(plugin && plugin.nickname, 40) ||
      asText(plugin && plugin.name, 64) ||
      asText(plugin && plugin.id, 80) || "未命名插件";
  }

  function folderName(tree, folderKey) {
    var rows = tree || [];
    for (var i = 0; i < rows.length; i += 1) {
      if (rows[i].kind === "folder" && rows[i].id === folderKey) return rows[i].name;
    }
    return "";
  }

  /** 插件在树里所属的文件夹 key（没有就空串）。 */
  function folderKeyOf(tree, pluginKey) {
    var rows = tree || [];
    for (var i = 0; i < rows.length; i += 1) {
      if (rows[i].kind === "folder" && rows[i].children.indexOf(pluginKey) >= 0) return rows[i].id;
    }
    return "";
  }

  function cloneTree(tree) {
    return (tree || []).map(function (item) {
      return {
        kind: item.kind, id: item.id, name: item.name,
        children: (item.children || []).slice()
      };
    });
  }

  function indexOfKey(rows, key) {
    for (var i = 0; i < rows.length; i += 1) {
      if (rows[i].id === key) return i;
      if (rows[i].kind === "folder" && rows[i].children.indexOf(key) >= 0) return i;
    }
    return -1;
  }

  /** 从树里摘掉一个条目（插件或整个文件夹），返回被摘掉的东西与其原位置。 */
  function extract(rows, key) {
    var at = -1;
    var extracted = null;
    var insideFolder = false;
    rows.forEach(function (item, i) {
      if (item.kind === "plugin" && item.id === key) { at = i; extracted = item; }
      else if (item.kind === "folder") {
        var childAt = item.children.indexOf(key);
        if (childAt >= 0) {
          at = i;
          insideFolder = true;
          extracted = { kind: "plugin", id: key };
          item.children.splice(childAt, 1);
        } else if (item.id === key) {
          at = i;
          extracted = item;
        }
      }
    });
    if (at < 0) return { rows: rows, extracted: null, at: -1, insideFolder: insideFolder };
    if (!insideFolder) rows.splice(at, 1);
    // 文件夹被掏空就整个消失，不留一个空壳占位
    rows.forEach(function (item, i) {
      if (item.kind === "folder" && !item.children.length) rows.splice(i, 1);
    });
    return { rows: rows, extracted: extracted, at: at, insideFolder: insideFolder };
  }

  /**
   * 拖拽/右键改组的唯一算法：把 key 挪到 anchor 的前/后，或塞进 anchor 那个文件夹。
   * @param {Array} tree 当前树
   * @param {string} key plugin:<id> 或 folder:<id>
   * @param {Object} target {mode:"before"|"after"|"into", anchor:条目 key}
   */
  function moveEntry(tree, key, target) {
    var rows = cloneTree(tree);
    var holder = extract(rows, key);
    if (!holder.extracted) return cloneTree(tree);
    var mode = target && target.mode;
    var anchor = target && target.anchor;
    if (!anchor || mode === "top") {
      rows.unshift(holder.extracted);
      return rows;
    }
    var at = indexOfKey(rows, anchor);
    if (at < 0) { rows.push(holder.extracted); return rows; }
    var anchorRow = rows[at];
    // 文件夹不套文件夹：拖「文件夹」进「文件夹」按放在它后面处理
    if (holder.extracted.kind === "folder" && mode === "into") mode = "after";
    if (mode === "into" && anchorRow.kind === "folder") {
      anchorRow.children.push(holder.extracted.id);
      return rows;
    }
    if (anchorRow.kind === "folder" && anchorRow.id !== anchor) {
      // anchor 在文件夹里：同级插入，只许插在它旁边（文件夹内序）
      var childAt = anchorRow.children.indexOf(anchor);
      if (holder.extracted.kind === "plugin") {
        anchorRow.children.splice(mode === "after" ? childAt + 1 : childAt, 0, holder.extracted.id);
      } else {
        rows.splice(mode === "after" ? at + 1 : at, 0, holder.extracted);
      }
      return rows;
    }
    if (anchorRow.kind === "plugin") {
      var parent = null;
      rows.forEach(function (item) {
        if (item.kind === "folder" && item.children.indexOf(anchor) >= 0) parent = item;
      });
      if (parent && holder.extracted.kind === "plugin") {
        var index = parent.children.indexOf(anchor);
        parent.children.splice(mode === "after" ? index + 1 : index, 0, holder.extracted.id);
        return rows;
      }
      var topAt = indexOfKey(rows, anchor);
      rows.splice(mode === "after" ? topAt + 1 : topAt, 0, holder.extracted);
      return rows;
    }
    rows.splice(mode === "after" ? at + 1 : at, 0, holder.extracted);
    return rows;
  }

  /** 在 anchor 插件的位置就地建一个文件夹，并把该插件收进去。 */
  function createFolderAt(tree, anchorPluginKey, name) {
    var rows = (tree || []).map(function (item) {
      return { kind: item.kind, id: item.id, name: item.name, children: (item.children || []).slice() };
    });
    var folder = {
      kind: "folder", id: newFolderKey(),
      name: asText(name, 24) || "未命名文件夹",
      children: []
    };
    var at = -1;
    rows.forEach(function (item, i) {
      if (item.kind === "plugin" && item.id === anchorPluginKey) at = i;
      else if (item.kind === "folder") {
        var childAt = item.children.indexOf(anchorPluginKey);
        if (childAt >= 0) {
          item.children.splice(childAt, 1);
          folder.children.push(anchorPluginKey);
          at = i;
        }
      }
    });
    if (at < 0) {
      folder.children.push(anchorPluginKey);
      rows.push(folder);
      return rows;
    }
    if (!folder.children.length) folder.children.push(anchorPluginKey);
    rows.splice(at, 0, folder);
    return rows;
  }

  /** 把插件从文件夹里拿出来，放回顶层（紧跟在那个文件夹后面）。 */
  function ungroupPlugin(tree, pluginKey) {
    var rows = (tree || []).map(function (item) {
      return { kind: item.kind, id: item.id, name: item.name, children: (item.children || []).slice() };
    });
    var homeAt = -1;
    rows.forEach(function (item, i) {
      if (item.kind !== "folder") return;
      var at = item.children.indexOf(pluginKey);
      if (at >= 0) {
        item.children.splice(at, 1);
        homeAt = i;
      }
    });
    if (homeAt < 0) return rows;
    var home = rows[homeAt];
    if (!home.children.length) rows.splice(homeAt, 1);
    rows.splice(homeAt + 1, 0, { kind: "plugin", id: pluginKey });
    return rows;
  }

  /** 解散文件夹：里面的插件按原顺序回到该文件夹的位置上。 */
  function dissolveFolder(tree, folderKey) {
    var rows = [];
    (tree || []).forEach(function (item) {
      if (item.kind === "folder" && item.id === folderKey) {
        item.children.forEach(function (child) { rows.push({ kind: "plugin", id: child }); });
        return;
      }
      rows.push({ kind: item.kind, id: item.id, name: item.name, children: (item.children || []).slice() });
    });
    return rows;
  }

  function renameFolder(tree, folderKey, name) {
    return (tree || []).map(function (item) {
      if (item.kind !== "folder" || item.id !== folderKey) return item;
      return {
        kind: "folder", id: item.id,
        name: asText(name, 24) || item.name,
        children: (item.children || []).slice()
      };
    });
  }

  window.JzoPrefs = {
    relTime: relTime,
    asText: asText,
    canonicalCombo: canonicalCombo,
    comboFromEvent: comboFromEvent,
    displayName: displayName,
    isPluginKey: isPluginKey,
    isFolderKey: isFolderKey,
    pluginIdOf: pluginIdOf,
    readTree: readTree,
    treeKeys: treeKeys,
    treeIsCustomized: treeIsCustomized,
    legacyTree: legacyTree,
    markLegacyMigrated: markLegacyMigrated,
    pluginRows: pluginRows,
    findPlugin: findPlugin,
    folderName: folderName,
    folderKeyOf: folderKeyOf,
    newFolderKey: newFolderKey,
    moveEntry: moveEntry,
    createFolderAt: createFolderAt,
    ungroupPlugin: ungroupPlugin,
    dissolveFolder: dissolveFolder,
    renameFolder: renameFolder
  };
})();
