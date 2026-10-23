/**
 * 专题讲义插件（org.jiuzhang.lecture）。
 *
 * 一份讲义由三块组成：知识点 / 方法 / 易错点。题篮里的题先按考向归堆，
 * 「从题篮生成骨架」把每个考向铺进三块；老师直接在块里写 Markdown + LaTeX，
 * 每条正文下方同步给原生预览（标题、列表、公式都是真 DOM，不是源码回显）。
 *
 * 边界：题目只经 Host API 的 basket.list 读取；草稿交给宿主代持（draft.save/load），
 * 插件不碰浏览器本地存储、不联网、不读宿主 DOM。打印时只出正文，编辑控件全部隐去。
 */
(function () {
  "use strict";

  var PROTOCOL = "jzo-plugin/1";
  var PLUGIN_ID = "org.jiuzhang.lecture";
  var DRAFT_KEY = "lecture";
  var REQUEST_TIMEOUT_MS = 20000;
  var REBUILD_WINDOW_MS = 4000;
  var ENTRY_MAX_CHARS = 8000;
  var TOPIC_LIMIT = 10;

  var BLOCKS = [
    {
      key: "knowledge",
      label: "知识点",
      placeholder: "例：\n## 等差数列通项\n- 定义：$a_{n+1}-a_n=d$\n- 通项：$a_n=a_1+(n-1)d$"
    },
    {
      key: "methods",
      label: "方法",
      placeholder: "例：\n## 求通项的通用路径\n1. 先判类型（等差 / 等比 / 递推）\n2. 选公式或构造辅助数列\n3. 代回检验首项"
    },
    {
      key: "pitfalls",
      label: "易错点",
      placeholder: "例：\n- 等比数列求和忘记讨论 $q=1$\n- 换元后没有回代定义域"
    }
  ];

  var INLINE_RE = /(\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\)|\$[^$\n]+?\$|\*\*[^*\n]+\*\*)/g;

  var root = document.getElementById("lcRoot");
  var titleInput = document.getElementById("lcTitle");
  var docTitle = document.getElementById("lcDocTitle");
  var docMeta = document.getElementById("lcDocMeta");
  var statusEl = document.getElementById("lcStatus");
  var sourceList = document.getElementById("lcSourceList");
  var sourceEmpty = document.getElementById("lcSourceEmpty");
  var sourceCount = document.getElementById("lcSourceCount");
  var emptyHint = document.getElementById("lcEmptyHint");

  var entriesHosts = {};
  var countEls = {};
  BLOCKS.forEach(function (block) {
    entriesHosts[block.key] = document.querySelector('[data-entries="' + block.key + '"]');
    countEls[block.key] = document.querySelector('[data-count="' + block.key + '"]');
  });

  var requestSeq = 0;
  var pending = new Map();
  var saveTimer = 0;
  var statusTimer = 0;
  var rebuildAt = 0;
  var loadToken = 0;
  var booted = false;
  var mathCache = new Map();

  var state = {
    title: "九章算子 · 专题讲义",
    sources: [],
    blocks: { knowledge: [], methods: [], pitfalls: [] }
  };

  // ---------- 宿主通信 ----------
  function hostCall(method, payload) {
    return new Promise(function (resolve, reject) {
      requestSeq += 1;
      var id = "l" + requestSeq + "_" + Date.now().toString(36);
      var timer = window.setTimeout(function () {
        pending.delete(id);
        reject(new Error("宿主响应超时（" + Math.round(REQUEST_TIMEOUT_MS / 1000) + "s）"));
      }, REQUEST_TIMEOUT_MS);
      pending.set(id, {
        resolve: function (result) { window.clearTimeout(timer); resolve(result); },
        reject: function (error) { window.clearTimeout(timer); reject(error); }
      });
      try {
        window.parent.postMessage({
          protocol: PROTOCOL, id: id, kind: "request", method: method, payload: payload || {}
        }, "*");
      } catch (error) {
        pending.delete(id);
        window.clearTimeout(timer);
        reject(error);
      }
    });
  }

  function respond(source, id, ok, result, code, message) {
    var packet = { protocol: PROTOCOL, id: id, kind: "response", ok: ok };
    if (ok) {
      packet.result = result === undefined ? {} : result;
    } else {
      packet.error = { code: code || "PLUGIN_ERROR", message: message || "插件拒绝了请求" };
    }
    try {
      source.postMessage(packet, "*");
    } catch (error) {
      // 宿主帧已销毁
    }
  }

  function dock(text) {
    try {
      window.parent.postMessage({
        protocol: PROTOCOL, kind: "notification", event: "region.dock",
        payload: { text: String(text).slice(0, 200) }
      }, "*");
    } catch (error) {
      // 通知丢一帧不致命
    }
  }

  function status(text, warn) {
    statusEl.textContent = text || "";
    statusEl.style.color = warn ? "#8a4b2f" : "";
    window.clearTimeout(statusTimer);
    if (text) {
      statusTimer = window.setTimeout(function () { statusEl.textContent = ""; }, 6000);
    }
  }

  function clockLabel() {
    var now = new Date();
    return [now.getHours(), now.getMinutes(), now.getSeconds()].map(function (value) {
      return value < 10 ? "0" + value : String(value);
    }).join(":");
  }

  // ---------- 安全富文本 ----------
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function mathNode(tex, display) {
    var span = el("span", display ? "lc-math-block" : "lc-math");
    var key = (display ? "D:" : "I:") + tex;
    var html = mathCache.get(key);
    if (html === undefined) {
      html = "";
      if (window.katex && typeof window.katex.renderToString === "function") {
        try {
          html = window.katex.renderToString(tex, {
            displayMode: Boolean(display),
            throwOnError: false,
            trust: false,
            strict: "ignore"
          });
        } catch (error) {
          html = "";
        }
      }
      mathCache.set(key, html);
    }
    if (html) span.innerHTML = html;
    else span.textContent = (display ? "$$" : "$") + tex + (display ? "$$" : "$");
    return span;
  }

  function appendInline(target, text) {
    var last = 0;
    var match;
    INLINE_RE.lastIndex = 0;
    while ((match = INLINE_RE.exec(text)) !== null) {
      if (match.index > last) {
        target.appendChild(document.createTextNode(text.slice(last, match.index)));
      }
      var token = match[0];
      if (token.slice(0, 2) === "$$" || token.slice(0, 2) === "\\[") {
        target.appendChild(mathNode(token.slice(2, -2), true));
      } else if (token.slice(0, 2) === "\\(") {
        target.appendChild(mathNode(token.slice(2, -2), false));
      } else if (token.charAt(0) === "$") {
        target.appendChild(mathNode(token.slice(1, -1), false));
      } else {
        var strong = document.createElement("strong");
        strong.textContent = token.slice(2, -2);
        target.appendChild(strong);
      }
      last = INLINE_RE.lastIndex;
    }
    if (last < text.length) {
      target.appendChild(document.createTextNode(text.slice(last)));
    }
  }

  /** Markdown 子集 → 真 DOM：标题、有序/无序列表、普通段落，行内公式逐段渲染。 */
  function renderRich(target, source) {
    target.textContent = "";
    var text = String(source == null ? "" : source).replace(/\r\n?/g, "\n").trim();
    if (!text) return;
    var list = null;
    text.split("\n").forEach(function (raw) {
      var line = raw.trim();
      if (!line) {
        list = null;
        return;
      }
      var heading = line.match(/^(#{1,3})\s+(.*)$/);
      if (heading) {
        list = null;
        var level = Math.min(4, heading[1].length + 1);
        var node = el("h" + level, "lc-h");
        appendInline(node, heading[2]);
        target.appendChild(node);
        return;
      }
      var bullet = line.match(/^[-*]\s+(.*)$/);
      var numbered = line.match(/^\d+[.、]\s+(.*)$/);
      if (bullet || numbered) {
        var tag = bullet ? "ul" : "ol";
        if (!list || list.tagName.toLowerCase() !== tag) {
          list = el(tag, "lc-list");
          target.appendChild(list);
        }
        var item = el("li");
        appendInline(item, (bullet || numbered)[1]);
        list.appendChild(item);
        return;
      }
      list = null;
      var paragraph = el("p", "lc-p");
      appendInline(paragraph, line);
      target.appendChild(paragraph);
    });
  }

  function excerpt(text, max) {
    var flat = String(text == null ? "" : text).replace(/\s+/g, " ").trim();
    return flat.length > max ? flat.slice(0, max) + "…" : flat;
  }

  // ---------- 三块正文 ----------
  function blockDef(key) {
    for (var i = 0; i < BLOCKS.length; i += 1) {
      if (BLOCKS[i].key === key) return BLOCKS[i];
    }
    return BLOCKS[0];
  }

  function totalEntries() {
    return BLOCKS.reduce(function (sum, block) {
      return sum + state.blocks[block.key].length;
    }, 0);
  }

  function updateCounts() {
    BLOCKS.forEach(function (block) {
      if (countEls[block.key]) countEls[block.key].textContent = String(state.blocks[block.key].length);
    });
    emptyHint.hidden = totalEntries() > 0;
  }

  function renderBlock(key) {
    var host = entriesHosts[key];
    if (!host) return;
    var def = blockDef(key);
    host.textContent = "";
    state.blocks[key].forEach(function (text, index) {
      var entry = el("article", "lc-entry");
      entry.setAttribute("data-index", String(index + 1));

      var area = document.createElement("textarea");
      area.rows = 4;
      area.value = text;
      area.placeholder = def.placeholder;
      area.setAttribute("aria-label", def.label + "第 " + (index + 1) + " 条");
      area.addEventListener("input", function () {
        state.blocks[key][index] = area.value;
        renderRich(entry.querySelector(".lc-preview"), area.value);
        updateCounts();
        scheduleSave();
      });

      var remove = el("button", "lc-remove", "×");
      remove.type = "button";
      remove.title = "删除这一条";
      remove.setAttribute("aria-label", "删除" + def.label + "第 " + (index + 1) + " 条");
      remove.addEventListener("click", function () {
        state.blocks[key].splice(index, 1);
        renderBlock(key);
        updateCounts();
        scheduleSave();
        status("已删除一条" + def.label);
      });

      var preview = el("div", "lc-preview");
      preview.setAttribute("aria-live", "polite");
      renderRich(preview, text);

      entry.appendChild(area);
      entry.appendChild(remove);
      entry.appendChild(preview);
      host.appendChild(entry);
    });
  }

  function renderBlocks() {
    BLOCKS.forEach(function (block) { renderBlock(block.key); });
    updateCounts();
  }

  function addEntry(key) {
    state.blocks[key].push("");
    renderBlock(key);
    updateCounts();
    var host = entriesHosts[key];
    var last = host ? host.lastElementChild : null;
    var area = last ? last.querySelector("textarea") : null;
    if (area) area.focus();
    scheduleSave();
  }

  document.querySelectorAll(".lc-add").forEach(function (button) {
    button.addEventListener("click", function () {
      addEntry(button.getAttribute("data-add"));
    });
  });

  // ---------- 题源 ----------
  function renderSources() {
    sourceList.textContent = "";
    sourceCount.textContent = String(state.sources.length);
    sourceEmpty.hidden = state.sources.length > 0;
    state.sources.forEach(function (item, index) {
      var question = item && item.question ? item.question : item;
      if (!question || typeof question !== "object") return;
      var node = el("li", "lc-source");
      node.appendChild(el("span", "lc-source-no", String(index + 1)));
      var body = el("div", "lc-source-body");
      body.appendChild(el("p", "lc-source-stem", excerpt(question.stem || "（无题干）", 96)));
      var taxonomy = question.taxonomy || {};
      var tags = [taxonomy.chapter, taxonomy.section, taxonomy.topic].filter(Boolean).join(" · ");
      body.appendChild(el("p", "lc-source-tags", tags || "未归类"));
      node.appendChild(body);
      sourceList.appendChild(node);
    });
    updateDocMeta();
  }

  function updateDocMeta() {
    var parts = ["题源 " + state.sources.length + " 道"];
    if (!state.sources.length) parts.push("可手写");
    var now = new Date();
    parts.push(now.getFullYear() + "-" + String(now.getMonth() + 1).padStart(2, "0") + "-" +
      String(now.getDate()).padStart(2, "0"));
    docMeta.textContent = parts.join(" · ");
  }

  function loadBasket() {
    var token = ++loadToken;
    return hostCall("basket.list", { expand: true }).then(function (result) {
      if (token !== loadToken) return state.sources;
      state.sources = Array.isArray(result.items) ? result.items : [];
      renderSources();
      return state.sources;
    }, function (error) {
      if (token !== loadToken) return state.sources;
      state.sources = [];
      renderSources();
      status("题篮读取失败：" + error.message, true);
      return state.sources;
    });
  }

  // ---------- 骨架 ----------
  function buildSkeleton() {
    if (!state.sources.length) {
      status("题篮是空的，先加几道同类题再生成骨架", true);
      return 0;
    }
    var groups = [];
    var index = new Map();
    state.sources.forEach(function (item) {
      var question = item && item.question ? item.question : item;
      if (!question || typeof question !== "object") return;
      var taxonomy = question.taxonomy || {};
      var label = taxonomy.topic || taxonomy.section || taxonomy.chapter || "未归类考点";
      var scope = [taxonomy.chapter, taxonomy.section].filter(Boolean).join(" · ");
      if (!index.has(label)) {
        var bucket = { label: label, scope: scope, count: 0 };
        index.set(label, bucket);
        groups.push(bucket);
      }
      index.get(label).count += 1;
    });
    groups.sort(function (a, b) { return b.count - a.count; });
    var topics = groups.slice(0, TOPIC_LIMIT);

    state.blocks = { knowledge: [], methods: [], pitfalls: [] };
    topics.forEach(function (topic) {
      var scope = topic.scope ? "（" + topic.scope + "）" : "";
      state.blocks.knowledge.push(
        "## " + topic.label + "\n题源 " + topic.count + " 道" + scope + "。\n- 核心定义：\n- 关键公式："
      );
      state.blocks.methods.push(
        "## " + topic.label + " 的通用路径\n1. 识别特征：\n2. 选择方法：\n3. 规范书写："
      );
      state.blocks.pitfalls.push("## " + topic.label + " 的易错点\n- ");
    });
    renderBlocks();
    updateDocMeta();
    scheduleSave();
    status("已按 " + topics.length + " 个考向生成骨架");
    dock("讲义骨架已生成：" + topics.length + " 个考向，题源 " + state.sources.length + " 道。");
    return topics.length;
  }

  // ---------- 草稿 ----------
  function snapshot() {
    return {
      title: state.title,
      blocks: state.blocks,
      saved_at: Date.now()
    };
  }

  function applyState(raw) {
    if (!raw || typeof raw !== "object") return false;
    var blocks = raw.blocks && typeof raw.blocks === "object" ? raw.blocks : null;
    if (!blocks) return false;
    if (typeof raw.title === "string" && raw.title.trim()) {
      state.title = raw.title.trim().slice(0, 48);
    }
    titleInput.value = state.title;
    docTitle.textContent = state.title;
    BLOCKS.forEach(function (block) {
      var list = Array.isArray(blocks[block.key]) ? blocks[block.key] : [];
      state.blocks[block.key] = list
        .filter(function (text) { return typeof text === "string"; })
        .map(function (text) { return text.slice(0, ENTRY_MAX_CHARS); });
    });
    renderBlocks();
    updateDocMeta();
    return true;
  }

  function saveDraft(auto) {
    return hostCall("draft.save", { key: DRAFT_KEY, value: snapshot() }).then(function (result) {
      if (result && result.ok === false) {
        status("草稿未保存：" + (result.reason || "宿主拒绝"), true);
        return false;
      }
      status((auto ? "已自动保存 " : "草稿已保存 ") + clockLabel());
      return true;
    }, function (error) {
      status("草稿保存失败：" + error.message, true);
      return false;
    });
  }

  function scheduleSave() {
    window.clearTimeout(saveTimer);
    saveTimer = window.setTimeout(function () { saveDraft(true); }, 1500);
  }

  function loadDraft(manual) {
    return hostCall("draft.load", { key: DRAFT_KEY }).then(function (result) {
      if (!result || result.ok === false) {
        status("草稿读取失败：" + ((result && result.reason) || "宿主拒绝"), true);
        return false;
      }
      if (!result.value) {
        status("还没有保存过的草稿", true);
        return false;
      }
      var restored = applyState(result.value);
      if (restored) status("草稿已载入");
      else status("草稿内容不完整，已忽略", true);
      return restored;
    }, function (error) {
      status("草稿读取失败：" + error.message, true);
      return false;
    });
  }

  // ---------- 交互 ----------
  titleInput.addEventListener("input", function () {
    state.title = String(titleInput.value || "").trim().slice(0, 48) || "九章算子 · 专题讲义";
    docTitle.textContent = state.title;
    scheduleSave();
  });

  document.getElementById("lcSave").addEventListener("click", function () { saveDraft(false); });
  document.getElementById("lcLoad").addEventListener("click", function () { loadDraft(true); });
  document.getElementById("lcPrint").addEventListener("click", function () { window.print(); });

  document.getElementById("lcSkeleton").addEventListener("click", function () {
    if (totalEntries() > 0 && Date.now() - rebuildAt > REBUILD_WINDOW_MS) {
      rebuildAt = Date.now();
      status("再点一次「从题篮生成骨架」将覆盖现有内容", true);
      return;
    }
    rebuildAt = 0;
    buildSkeleton();
  });

  window.addEventListener("beforeprint", function () { renderBlocks(); });

  // ---------- 启动 ----------
  function boot() {
    hostCall("draft.load", { key: DRAFT_KEY }).then(function (result) {
      var restored = Boolean(result && result.ok !== false && result.value && applyState(result.value));
      loadBasket().then(function (sources) {
        if (restored) {
          status("已恢复上次草稿");
          return;
        }
        if (sources.length) buildSkeleton();
        else {
          renderBlocks();
          status("题篮为空，可直接手写或点「＋ 添加」");
        }
      });
    }, function () {
      loadBasket().then(function (sources) {
        if (sources.length) buildSkeleton();
        else renderBlocks();
      });
    });
  }

  // ---------- 协议 ----------
  window.addEventListener("message", function (event) {
    var message = event.data;
    if (!message || message.protocol !== PROTOCOL) return;

    if (message.kind === "response" && pending.has(message.id)) {
      var waiter = pending.get(message.id);
      pending.delete(message.id);
      if (message.ok) waiter.resolve(message.result || {});
      else waiter.reject(new Error((message.error && message.error.message) || "宿主返回失败"));
      return;
    }

    if (message.kind === "notification") {
      if (message.event === "basket.changed") {
        loadBasket().then(function () {
          status("题篮已更新，需要重建骨架时点【从题篮生成骨架】");
        });
      }
      return;
    }

    if (message.kind !== "request") return;

    if (message.method === "plugin.activate") {
      root.hidden = false;
      respond(event.source, message.id, true, { ready: true, plugin_id: PLUGIN_ID });
      if (booted) loadBasket();
      else {
        booted = true;
        boot();
      }
      return;
    }
    if (message.method === "plugin.deactivate") {
      root.hidden = true;
      respond(event.source, message.id, true, { ready: false });
      return;
    }
    respond(event.source, message.id, false, null, "UNSUPPORTED_METHOD", "未实现的方法：" + message.method);
  });
})();
