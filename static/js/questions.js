(function () {
  "use strict";

  var PROTOCOL = "jzo-plugin/1";
  var SLOT = "question.card";
  var RENDER_TIMEOUT_MS = 3000;
  var ACTIVATE_TIMEOUT_MS = 3000;
  var MAX_CONSECUTIVE_FAILURES = 3;

  var TYPE_LABELS = {
    single_choice: "单选",
    multiple_choice: "多选",
    fill_blank: "填空",
    solution: "解答",
    proof: "证明",
    unknown: "待定"
  };

  var DIFFICULTY_LABELS = {
    basic: "基础",
    medium: "中档",
    hard: "压轴",
    novel: "新定义"
  };

  var DROP_TAGS = {
    SCRIPT: true,
    STYLE: true,
    IFRAME: true,
    OBJECT: true,
    EMBED: true,
    FORM: true,
    INPUT: true,
    LINK: true,
    META: true,
    TEMPLATE: true,
    NOSCRIPT: true,
    SVG: true,
    MATH: true
  };

  var ALLOWED_TAGS = Object.create(null);
  [
    "ARTICLE", "SECTION", "DIV", "P", "SPAN", "OL", "UL", "LI",
    "STRONG", "EM", "B", "I", "CODE", "PRE", "BR", "SUP", "SUB",
    "H2", "H3", "H4", "HEADER", "FOOTER", "DL", "DT", "DD",
    "TABLE", "THEAD", "TBODY", "TR", "TH", "TD"
  ].forEach(function (tag) { ALLOWED_TAGS[tag] = true; });

  var ALLOWED_ATTRS = {
    "class": true,
    "title": true,
    "data-jzo-plugin": true,
    "aria-hidden": true,
    "colspan": true,
    "rowspan": true
  };

  var state = {
    page: 1,
    pageSize: 10,
    query: "",
    type: "",
    total: 0,
    totalPages: 1,
    requestSeq: 0,
    plugin: null,
    iframe: null,
    active: false,
    failures: 0,
    pending: new Map()
  };

  var el = {};

  function cacheElements() {
    el.search = document.getElementById("qSearch");
    el.type = document.getElementById("qType");
    el.pageSize = document.getElementById("qPageSize");
    el.refresh = document.getElementById("qRefresh");
    el.rendererNote = document.getElementById("rendererNote");
    el.resultRegion = document.getElementById("qResultRegion");
    el.state = document.getElementById("qState");
    el.list = document.getElementById("qList");
    el.prev = document.getElementById("prevPage");
    el.next = document.getElementById("nextPage");
    el.pageInfo = document.getElementById("pageInfo");
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function labelOf(map, key) {
    return Object.prototype.hasOwnProperty.call(map, key) ? map[key] : "未知";
  }

  function makeId() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return window.crypto.randomUUID();
    }
    return "r_" + Date.now().toString(36) + "_" + Math.random().toString(36).slice(2, 10);
  }

  async function apiJson(path) {
    var response = await fetch(path, {
      cache: "no-store",
      headers: { Accept: "application/json" }
    });
    var text = await response.text();
    var data = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch (error) {
        data = null;
      }
    }
    if (!response.ok) {
      var detail = data && data.detail;
      var message = typeof detail === "string"
        ? detail
        : (detail && detail.message) || ("HTTP " + response.status);
      throw new Error(message);
    }
    return data;
  }

  function themeSpec() {
    var dark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    return { mode: dark ? "dark" : "light", accent: "#a63b2b" };
  }

  function setRendererNote(message, tone) {
    if (!el.rendererNote) return;
    el.rendererNote.textContent = message;
    if (tone) {
      el.rendererNote.dataset.tone = tone;
    } else {
      delete el.rendererNote.dataset.tone;
    }
  }

  function setStateMessage(message, tone) {
    if (!el.state) return;
    if (!message) {
      el.state.hidden = true;
      el.state.textContent = "";
      return;
    }
    el.state.hidden = false;
    el.state.textContent = message;
    el.state.dataset.tone = tone || "info";
  }

  function setBusy(busy) {
    if (el.resultRegion) el.resultRegion.setAttribute("aria-busy", busy ? "true" : "false");
    if (el.refresh) el.refresh.disabled = busy;
  }

  function updatePager(data) {
    if (el.pageInfo) {
      el.pageInfo.textContent = "第 " + data.page + " / " + data.total_pages + " 页 · 共 " + data.total + " 题";
    }
    if (el.prev) el.prev.disabled = data.page <= 1;
    if (el.next) el.next.disabled = data.page >= data.total_pages;
  }

  function buildListUrl() {
    var params = new URLSearchParams();
    params.set("page", String(state.page));
    params.set("page_size", String(state.pageSize));
    if (state.query) params.set("q", state.query);
    if (state.type) params.set("type", state.type);
    return "/api/questions?" + params.toString();
  }

  function sanitizeNode(node) {
    var child = node.firstChild;
    while (child) {
      var next = child.nextSibling;

      if (child.nodeType === 3) {
        child = next;
        continue;
      }

      if (child.nodeType !== 1) {
        node.removeChild(child);
        child = next;
        continue;
      }

      var tag = child.tagName;
      if (DROP_TAGS[tag]) {
        node.removeChild(child);
        child = next;
        continue;
      }

      if (!ALLOWED_TAGS[tag]) {
        sanitizeNode(child);
        while (child.firstChild) {
          node.insertBefore(child.firstChild, child);
        }
        node.removeChild(child);
        child = next;
        continue;
      }

      var attributes = Array.prototype.slice.call(child.attributes);
      attributes.forEach(function (attribute) {
        if (!ALLOWED_ATTRS[attribute.name.toLowerCase()]) {
          child.removeAttribute(attribute.name);
        }
      });

      if (child.hasAttribute("class")) {
        var classValue = child.getAttribute("class").trim();
        if (classValue && !/^[A-Za-z0-9_\-\s]+$/.test(classValue)) {
          child.removeAttribute("class");
        }
      }

      sanitizeNode(child);
      child = next;
    }
  }

  function sanitizeFragment(html) {
    if (typeof html !== "string" || !html || html.length > 200000) return "";
    var parsed = new DOMParser().parseFromString(
      '<div id="jzo-sanitize-root">' + html + "</div>",
      "text/html"
    );
    var root = parsed.getElementById("jzo-sanitize-root");
    if (!root) return "";
    sanitizeNode(root);
    return root.innerHTML;
  }

  function isScopedCss(css, pluginId) {
    if (typeof css !== "string" || !css || css.length > 200000) return false;

    var withoutComments = css.replace(/\/\*[\s\S]*?\*\//g, "");
    var lower = withoutComments.toLowerCase();
    if (lower.indexOf("@import") >= 0) return false;
    if (lower.indexOf("position:fixed") >= 0 || lower.indexOf("position: fixed") >= 0) return false;
    if (/url\s*\(\s*['"]?https?:/.test(lower)) return false;

    var scope = '[data-jzo-plugin="' + pluginId + '"]';
    var buffer = "";
    var depth = 0;

    for (var index = 0; index < withoutComments.length; index += 1) {
      var char = withoutComments.charAt(index);
      if (char === "{") {
        var prelude = buffer.trim();
        if (prelude.charAt(0) !== "@" && prelude.indexOf(scope) === -1) {
          return false;
        }
        buffer = "";
        depth += 1;
        continue;
      }
      if (char === "}") {
        depth = Math.max(0, depth - 1);
        buffer = "";
        continue;
      }
      if (char === ";") {
        buffer = "";
        continue;
      }
      buffer += char;
    }

    return depth === 0;
  }

  async function injectPluginCss(plugin) {
    if (!plugin.css_url) return;
    try {
      var response = await fetch(plugin.css_url, { cache: "no-cache" });
      if (!response.ok) return;
      var css = await response.text();
      if (!isScopedCss(css, plugin.id)) {
        setRendererNote("插件样式未通过作用域校验，已忽略；题卡使用底座样式。", "warn");
        return;
      }
      var style = document.createElement("style");
      style.dataset.jzoPlugin = plugin.id;
      style.textContent = css;
      document.head.appendChild(style);
    } catch (error) {
      setRendererNote("插件样式加载失败，题卡使用底座样式。", "warn");
    }
  }

  function createPluginFrame(plugin) {
    return new Promise(function (resolve, reject) {
      var iframe = document.createElement("iframe");
      iframe.className = "plugin-runtime";
      iframe.setAttribute("sandbox", "allow-scripts");
      iframe.setAttribute("aria-hidden", "true");
      iframe.setAttribute("title", "插件运行时：" + plugin.name);
      iframe.tabIndex = -1;

      var done = false;
      var timer = window.setTimeout(function () {
        if (done) return;
        done = true;
        reject(new Error("插件页面加载超时"));
      }, ACTIVATE_TIMEOUT_MS);

      iframe.addEventListener("load", function () {
        if (done) return;
        done = true;
        window.clearTimeout(timer);
        resolve(iframe);
      }, { once: true });

      iframe.src = plugin.entry_url;
      document.body.appendChild(iframe);
    });
  }

  function rejectPending(reason) {
    state.pending.forEach(function (entry) {
      window.clearTimeout(entry.timer);
      entry.reject(new Error(reason));
    });
    state.pending.clear();
  }

  function stopPlugin(reason) {
    state.active = false;
    rejectPending(reason);
    if (state.iframe && state.iframe.parentNode) {
      state.iframe.parentNode.removeChild(state.iframe);
    }
    state.iframe = null;
  }

  function request(method, payload, timeoutMs) {
    return new Promise(function (resolve, reject) {
      if (!state.iframe || !state.iframe.contentWindow) {
        reject(new Error("插件运行时不可用"));
        return;
      }
      var id = makeId();
      var timer = window.setTimeout(function () {
        state.pending.delete(id);
        reject(new Error("插件响应超时"));
      }, timeoutMs || RENDER_TIMEOUT_MS);

      state.pending.set(id, { resolve: resolve, reject: reject, timer: timer });
      state.iframe.contentWindow.postMessage({
        protocol: PROTOCOL,
        id: id,
        kind: "request",
        method: method,
        payload: payload || {}
      }, "*");
    });
  }

  function onPluginMessage(event) {
    if (!state.iframe || event.source !== state.iframe.contentWindow) return;
    var message = event.data;
    if (!message || message.protocol !== PROTOCOL || message.kind !== "response") return;
    if (typeof message.id !== "string") return;

    var pending = state.pending.get(message.id);
    if (!pending) return;
    state.pending.delete(message.id);
    window.clearTimeout(pending.timer);

    if (message.ok) {
      pending.resolve(message.result || {});
    } else {
      var detail = message.error && message.error.message;
      pending.reject(new Error(detail || "插件渲染失败"));
    }
  }

  async function mountPlugin() {
    var discovery = await apiJson("/api/plugins");
    var renderers = (discovery.plugins || []).filter(function (plugin) {
      return plugin.kind === "renderer" && plugin.slots.indexOf(SLOT) !== -1;
    });

    if (renderers.length === 0) {
      state.active = false;
      setRendererNote("未发现 question.card 渲染插件，使用底座降级渲染。", "warn");
      return;
    }

    state.plugin = renderers[0];
    await injectPluginCss(state.plugin);

    var iframe = await createPluginFrame(state.plugin);
    state.iframe = iframe;
    await request("plugin.activate", {
      plugin_id: state.plugin.id,
      api_version: state.plugin.api_version,
      locale: "zh-CN",
      theme: themeSpec()
    }, ACTIVATE_TIMEOUT_MS);

    state.active = true;
    state.failures = 0;
    setRendererNote("由插件「" + state.plugin.name + "」渲染题卡 · " + state.plugin.id);
  }

  function fallbackCard(question, reason) {
    var item = document.createElement("li");
    item.className = "qcard";
    item.dataset.questionId = question.id;

    var article = document.createElement("article");
    article.className = "fallback-card";

    var meta = document.createElement("p");
    meta.className = "fallback-meta";
    meta.textContent = labelOf(TYPE_LABELS, question.type) + " · " +
      labelOf(DIFFICULTY_LABELS, question.difficulty) + " · " + question.id;

    var stem = document.createElement("p");
    stem.className = "fallback-stem";
    stem.textContent = question.stem || "";

    var note = document.createElement("p");
    note.className = "fallback-note";
    note.textContent = "底座降级渲染" + (reason ? "：" + reason : "");

    article.appendChild(meta);
    article.appendChild(stem);
    article.appendChild(note);
    item.appendChild(article);
    return item;
  }

  async function renderQuestion(question) {
    if (!state.active) {
      return fallbackCard(question, "插件未激活");
    }

    try {
      var result = await request("question.render", {
        question: question,
        slot: SLOT,
        view: "card",
        theme: themeSpec(),
        locale: "zh-CN",
        render_mode: "math-source",
        assets: {}
      }, RENDER_TIMEOUT_MS);

      var html = sanitizeFragment(result && result.html);
      if (!html) {
        throw new Error("插件返回了空内容");
      }

      state.failures = 0;
      var item = document.createElement("li");
      item.className = "qcard";
      item.dataset.questionId = question.id;
      item.innerHTML = html;
      return item;
    } catch (error) {
      state.failures += 1;
      if (state.failures >= MAX_CONSECUTIVE_FAILURES) {
        stopPlugin("插件连续渲染失败，已在当前会话停用。");
        setRendererNote("插件连续失败已被停用，后续使用底座降级渲染。", "warn");
      }
      return fallbackCard(question, error.message);
    }
  }

  function replaceList(nodes) {
    if (!el.list) return;
    while (el.list.firstChild) el.list.removeChild(el.list.firstChild);
    nodes.forEach(function (node) { el.list.appendChild(node); });
  }

  async function loadPage(page) {
    state.page = Math.max(1, page);
    var seq = state.requestSeq + 1;
    state.requestSeq = seq;
    setBusy(true);
    setStateMessage("正在读取题库…", "info");

    try {
      var data = await apiJson(buildListUrl());
      if (seq !== state.requestSeq) return;

      state.total = data.total;
      state.totalPages = data.total_pages;
      updatePager(data);

      if (!data.items || data.items.length === 0) {
        replaceList([]);
        setStateMessage(
          state.query || state.type
            ? "没有符合筛选条件的题目。"
            : "题库还是空的。可通过 POST /api/questions 装入第一道题。",
          "info"
        );
        return;
      }

      var nodes = await Promise.all(data.items.map(renderQuestion));
      if (seq !== state.requestSeq) return;

      replaceList(nodes);
      setStateMessage("");
    } catch (error) {
      if (seq !== state.requestSeq) return;
      replaceList([]);
      setStateMessage("题库加载失败：" + error.message, "error");
    } finally {
      if (seq === state.requestSeq) setBusy(false);
    }
  }

  function debounce(callback, wait) {
    var timer = null;
    return function () {
      var args = arguments;
      window.clearTimeout(timer);
      timer = window.setTimeout(function () {
        callback.apply(null, args);
      }, wait);
    };
  }

  function bindEvents() {
    if (el.search) {
      el.search.addEventListener("input", debounce(function () {
        state.query = el.search.value.trim();
        loadPage(1);
      }, 320));
    }

    if (el.type) {
      el.type.addEventListener("change", function () {
        state.type = el.type.value;
        loadPage(1);
      });
    }

    if (el.pageSize) {
      el.pageSize.addEventListener("change", function () {
        state.pageSize = Number(el.pageSize.value) || 10;
        loadPage(1);
      });
    }

    if (el.refresh) {
      el.refresh.addEventListener("click", function () { loadPage(state.page); });
    }

    if (el.prev) {
      el.prev.addEventListener("click", function () {
        if (state.page > 1) loadPage(state.page - 1);
      });
    }

    if (el.next) {
      el.next.addEventListener("click", function () {
        if (state.page < state.totalPages) loadPage(state.page + 1);
      });
    }
  }

  async function boot() {
    cacheElements();
    bindEvents();
    window.addEventListener("message", onPluginMessage);

    try {
      await mountPlugin();
    } catch (error) {
      stopPlugin("插件宿主未就绪");
      setRendererNote("插件宿主未就绪：" + error.message + "；使用底座降级渲染。", "warn");
    }

    await loadPage(1);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
