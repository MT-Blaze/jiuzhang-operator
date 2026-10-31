/**
 * 录题工作台 v2（军令 #23）。
 *
 * 画布实例（stage.center）只有三栏：左原图 | 中全量 exam-zh 源码 | 右渲染。
 * 源码是唯一的录入面——一整段 \begin{question}…\end{solution}；
 * 题型、难度、来源这些元数据一律归辅助栏（sidebar.right，阶段 2），画布不放表单。
 *
 * 插件住在不透明源沙箱里：不联网、不碰浏览器本地存储、不碰宿主 DOM。
 * 读题只经宿主转发（bank.get），令牌由宿主代持；写库通道随阶段 2 的保存一起接入。
 * 布局偏好交宿主 draft.save / draft.load 代持。
 */
(function () {
  "use strict";

  var PROTOCOL = "jzo-plugin/1";
  var PLUGIN_ID = "org.jiuzhang.editor";
  var REQUEST_TIMEOUT_MS = 20000;
  var RENDER_DEBOUNCE_MS = 120;
  var LAYOUT_DRAFT_MS = 400;
  var SPLIT_W = 6;
  var PANE_MIN = 28;
  var DEV_NS = "org.jiuzhang.editor.dev";
  var DRAFT_LAYOUT_KEY = "editor:v2:layout";
  var OPTION_KEYS = "ABCDEFGH".split("");
  var COMMAND_QUESTION_ID_RE = /^q_[A-Za-z0-9_-]{1,78}$/;

  var root = document.getElementById("edRoot");
  var colsEl = document.getElementById("edCols");
  var imageBodyEl = document.getElementById("edImageBody");
  var sourceBodyEl = document.getElementById("edSourceBody");
  var renderBodyEl = document.getElementById("edRenderBody");
  var imageNameEl = document.getElementById("edImageName");
  var sourceHintEl = document.getElementById("edSourceHint");
  var metricsEl = document.getElementById("edMetrics");
  var progressEl = document.getElementById("edProgress");
  var formatEl = document.getElementById("edFormat");
  var dirtyEl = document.getElementById("edDirty");
  var toastEl = document.getElementById("edToast");

  var pending = new Map();
  var requestSeq = 0;
  var renderTimer = 0;
  var toastTimer = 0;
  var layoutTimer = 0;
  var mathCache = new Map();
  var katexCount = 0;
  var scrollLock = false;

  var state = {
    slot: "stage.center",
    items: [],
    active: 0,
    format: "latex",
    widths: { image: 260, source: 360 },
    dirty: false,
    layoutReady: false
  };

  // ---------- 宿主通信 ----------
  function hostCall(method, payload) {
    return new Promise(function (resolve, reject) {
      requestSeq += 1;
      var id = "edv2" + requestSeq + "-" + Date.now().toString(36);
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

  function publish(event, payload) {
    try {
      window.parent.postMessage({
        protocol: PROTOCOL, kind: "notification", event: event, payload: payload || {}
      }, "*");
    } catch (error) { /* 通知丢一帧不致命 */ }
  }

  function dock(text) {
    publish("region.dock", { text: String(text).slice(0, 200) });
  }

  function respond(target, id, ok, result, code, message) {
    var packet = { protocol: PROTOCOL, id: id, kind: "response", ok: ok };
    if (ok) packet.result = result || {};
    else packet.error = { code: code || "ERROR", message: message || "失败", retryable: false };
    try { target.postMessage(packet, "*"); } catch (error) { /* 宿主已走 */ }
  }

  function toast(text, tone) {
    if (!toastEl) return;
    toastEl.textContent = text;
    toastEl.setAttribute("data-tone", tone || "info");
    toastEl.setAttribute("data-show", "true");
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(function () {
      toastEl.setAttribute("data-show", "false");
    }, 2600);
  }

  // ---------- 富文本（文字 + LaTeX + 底座托管配图） ----------
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function clampValue(value, min, max) {
    if (max < min) return min;
    if (value < min) return min;
    if (value > max) return max;
    return value;
  }

  function mathNode(tex, display) {
    var span = el("span", display ? "ed-math-block" : "ed-math");
    var key = (display ? "D:" : "I:") + tex;
    var html = mathCache.get(key);
    if (html === undefined) {
      html = "";
      if (window.katex && typeof window.katex.renderToString === "function") {
        try {
          html = window.katex.renderToString(tex, {
            displayMode: display, throwOnError: false, strict: "ignore"
          });
        } catch (error) {
          html = "";
        }
      }
      mathCache.set(key, html);
    }
    if (html) {
      katexCount += 1;
      span.innerHTML = html;
    } else {
      span.textContent = (display ? "$$" : "$") + tex + (display ? "$$" : "$");
    }
    return span;
  }

  var INLINE_RE = /(\\includegraphics(?:\[[^\]]*\])?\{[^}]*\}|\\fillin(?:\[[^\]]*\])?|!\[[^\]]*\]\([^)]*\)|\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]|\$[^$\n]*?\$|\\\([\s\S]*?\\\)|\*\*[^*]+\*\*)/g;

  /** 只认底座托管路径与 asset:// 逻辑地址；远程 URL / data: / file: 一律当普通文本。 */
  function safeAssetUri(value) {
    var uri = String(value == null ? "" : value).trim();
    if (uri.indexOf("/static/uploads/") === 0) return uri;
    if (uri.indexOf("/static/icons/") === 0) return uri;
    if (uri.indexOf("/static/assets/") === 0) return uri;
    if (uri.indexOf("asset://") === 0 && uri.length > 8) return uri;
    return "";
  }

  function appendImageRef(parent, uri, alt, raw) {
    var path = safeAssetUri(uri);
    if (!path) {
      parent.appendChild(document.createTextNode(raw || String(uri == null ? "" : uri)));
      return;
    }
    if (path.indexOf("asset://") === 0) {
      parent.appendChild(el("span", "ed-opt-img", "（配图 " + path.slice(8) + "）"));
      return;
    }
    var img = document.createElement("img");
    img.className = "ed-inline-img";
    img.setAttribute("alt", alt || "题目配图");
    img.src = path;
    img.addEventListener("error", function () {
      if (img.parentNode) img.parentNode.replaceChild(el("span", "ed-opt-img", "（配图读取失败）"), img);
    });
    parent.appendChild(img);
  }

  /** 「\fillin 不带答案」是格式宪法：方括号里的内容只当老师留下的提示，绝不当答案渲染。 */
  function appendFillin(parent, token) {
    var hint = /\[([^\]]*)\]$/.exec(token);
    parent.appendChild(el("span", "ed-fillin", hint ? hint[1] : ""));
  }

  function appendRich(parent, text) {
    var source = String(text == null ? "" : text);
    var last = 0;
    var match;
    INLINE_RE.lastIndex = 0;
    while ((match = INLINE_RE.exec(source)) !== null) {
      if (match.index > last) parent.appendChild(document.createTextNode(source.slice(last, match.index)));
      var token = match[0];
      if (token.slice(0, 16) === "\\includegraphics") {
        var graphic = /\{([^}]*)\}$/.exec(token);
        appendImageRef(parent, graphic ? graphic[1] : "", "", token);
      } else if (token.slice(0, 7) === "\\fillin") {
        appendFillin(parent, token);
      } else if (token.slice(0, 2) === "![") {
        var markdown = /^!\[([^\]]*)\]\(([^)]*)\)$/.exec(token);
        appendImageRef(parent, markdown ? markdown[2] : "", markdown ? markdown[1] : "", token);
      } else if (token.slice(0, 2) === "$$" && token.slice(-2) === "$$") {
        parent.appendChild(mathNode(token.slice(2, -2), true));
      } else if (token.slice(0, 2) === "\\[" && token.slice(-2) === "\\]") {
        parent.appendChild(mathNode(token.slice(2, -2), true));
      } else if (token.slice(0, 2) === "\\(" && token.slice(-2) === "\\)") {
        parent.appendChild(mathNode(token.slice(2, -2), false));
      } else if (token.charAt(0) === "$" && token.charAt(token.length - 1) === "$") {
        parent.appendChild(mathNode(token.slice(1, -1), false));
      } else if (token.slice(0, 2) === "**" && token.slice(-2) === "**") {
        var strong = el("strong");
        appendRich(strong, token.slice(2, -2));
        parent.appendChild(strong);
      } else {
        parent.appendChild(document.createTextNode(token));
      }
      last = match.index + token.length;
    }
    if (last < source.length) parent.appendChild(document.createTextNode(source.slice(last)));
  }

  /** 把文本按独立公式切成「文字段 / 公式段」，文字段再按空行分段。 */
  function appendBody(parent, text) {
    var source = String(text == null ? "" : text).trim();
    if (!source) return;
    var displayRe = /(\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\])/g;
    var segments = source.split(displayRe);
    segments.forEach(function (segment, index) {
      if (!segment) return;
      if (index % 2 === 1) {
        parent.appendChild(mathNode(segment.slice(2, -2), true));
        return;
      }
      segment.split(/\n{2,}/).forEach(function (paragraph) {
        var clean = paragraph.replace(/\n/g, " ").trim();
        if (!clean) return;
        var p = el("p", "ed-line");
        appendRich(p, clean);
        parent.appendChild(p);
      });
    });
  }

  // ---------- exam-zh 源码：解析（渲染与格式二共用）+ 重组（阶段 2 直接复用这一份） ----------
  function matchEnv(text, name) {
    var begin = "\\begin{" + name + "}";
    var end = "\\end{" + name + "}";
    var start = text.indexOf(begin);
    if (start < 0) return null;
    var bodyAt = start + begin.length;
    var stop = text.indexOf(end, bodyAt);
    if (stop < 0) return null;
    return { start: start, end: stop + end.length, body: text.slice(bodyAt, stop) };
  }

  function splitChoices(body) {
    var found = matchEnv(body, "choices");
    if (!found) return { rest: body, items: [], found: false };
    var parts = found.body.split(/\\item\b/);
    var lead = parts.shift() || "";
    var items = [];
    if (lead.trim()) items.push(lead.trim());
    parts.forEach(function (part) { items.push(part.trim()); });
    return {
      rest: body.slice(0, found.start) + body.slice(found.end),
      items: items,
      found: true
    };
  }

  function detectType(parsed) {
    if (parsed.hasChoices) return parsed.multi ? "multiple_choice" : "single_choice";
    if (parsed.hasFillin) return "fill_blank";
    return "solution";
  }

  /** 一整段 exam-zh 源码 → 结构化（题干/选项/答案/解析）；认不出的逐项进 errors，绝不静默。 */
  function parseExamSource(text) {
    var src = String(text == null ? "" : text).replace(/\r\n/g, "\n");
    var result = {
      env: "", stem: "", choices: [], answer: "", analysis: "", stray: "",
      hasChoices: false, hasFillin: false, multi: false, type: "", errors: []
    };
    var question = matchEnv(src, "question");
    var problem = matchEnv(src, "problem");
    var solution = matchEnv(src, "solution");
    if (question && problem) result.errors.push("question 与 problem 环境只能二选一");
    result.env = question ? "question" : (problem ? "problem" : "");
    var stemHost = question || problem;
    if (!stemHost) result.errors.push("缺少 \\begin{question} 或 \\begin{problem}");

    var rest = stemHost ? stemHost.body : "";
    var innerSolution = matchEnv(rest, "solution");
    if (innerSolution) {
      // 有人把 solution 套进了题干环境里：环境不套环境，剥出来照常解析并留话。
      result.errors.push("solution 不应嵌在题干环境内");
      solution = innerSolution;
      rest = rest.slice(0, innerSolution.start) + rest.slice(innerSolution.end);
    }
    var choices = splitChoices(rest);
    result.hasChoices = choices.found;
    result.choices = choices.items;
    result.stem = (choices.rest || "").trim();
    result.hasFillin = /\\fillin\b/.test(result.stem);
    if (!result.stem) result.errors.push("题干为空");
    if (choices.found && choices.items.length < 2) result.errors.push("选项不足两项");
    result.multi = result.stem.indexOf("（多选）") >= 0 || result.stem.indexOf("(多选)") >= 0;

    result.stray = src.replace(/\\begin\{(question|problem|solution)\}[\s\S]*?\\end\{\1\}/g, "").trim();

    if (solution) {
      var body = String(solution.body || "").trim();
      var answerMatch = /^答案\s*[:：]\s*([^\n]*)([\s\S]*)$/.exec(body);
      if (answerMatch) {
        result.answer = (answerMatch[1] || "").trim();
        result.analysis = (answerMatch[2] || "").trim();
      } else if (body) {
        result.analysis = body;
        result.errors.push("solution 开头缺「答案：」");
      }
      if (/\\fillin\s*\[[^\]]*\]/.test(result.stem)) {
        result.errors.push("填空的 \\fillin 方括号内容按提示处理，答案仍取 solution");
      }
    } else {
      result.errors.push("缺少 \\begin{solution}");
    }

    result.type = stemHost ? detectType(result) : "";
    return result;
  }

  function ensureChoiceBracket(stem, multi) {
    var text = String(stem == null ? "" : stem).replace(/\s+$/, "");
    if (multi && text.indexOf("（多选）") < 0) text += "（多选）";
    var tail = text.slice(-6);
    if (tail.indexOf("（  ）") < 0 && tail.indexOf("(  )") < 0) text += "（  ）";
    return text;
  }

  function answerLetters(question) {
    var answer = (question && question.answer) || {};
    if (Array.isArray(answer.choice_keys) && answer.choice_keys.length) return answer.choice_keys.join("");
    if (typeof answer.final === "string" && answer.final) return answer.final;
    if (typeof answer.content === "string") return answer.content;
    return "";
  }

  function solutionBlock(question) {
    var head = "答案：" + answerLetters(question);
    var body = String((question && question.solution) == null ? "" : question.solution).trim();
    return body ? head + "\n" + body : head;
  }

  /** 结构化题目 → 格式一（军令 #23 的格式宪法；阶段 2 的自动重组复用这一个函数）。 */
  function buildExamSource(question) {
    var item = question || {};
    var type = String(item.type || "solution");
    var stem = String(item.stem == null ? "" : item.stem).trim();
    var out = "";
    if (type === "single_choice" || type === "multiple_choice") {
      var lines = (item.options || []).map(function (option) {
        return "  \\item " + String(option.content == null ? "" : option.content).trim();
      });
      out += "\\begin{question}\n" + ensureChoiceBracket(stem, type === "multiple_choice") + "\n"
        + "\\begin{choices}\n" + lines.join("\n") + "\n\\end{choices}\n\\end{question}\n\n";
    } else if (type === "fill_blank") {
      out += "\\begin{question}\n" + stem + "\n\\end{question}\n\n";
    } else {
      out += "\\begin{problem}\n" + stem + "\n\\end{problem}\n\n";
    }
    return out + "\\begin{solution}\n" + solutionBlock(item) + "\n\\end{solution}\n";
  }

  /** 本地规则清洗：只归一公式定界符，绝不动 exam-zh 环境骨架。 */
  function cleanExamSource(text) {
    var src = String(text == null ? "" : text);
    var touched = 0;
    var next = src.replace(/\\\[([\s\S]*?)\\\]/g, function (all, inner) {
      touched += 1;
      return "$$" + inner.trim() + "$$";
    }).replace(/\\\(([\s\S]*?)\\\)/g, function (all, inner) {
      touched += 1;
      return "$" + inner.trim() + "$";
    });
    if (next.indexOf("\r\n") >= 0) {
      touched += 1;
      next = next.replace(/\r\n/g, "\n");
    }
    return { text: next, touched: touched };
  }

  // ---------- 假数据（与 dev/fixtures.json 同一份；沙箱 CSP connect-src none，只能内嵌） ----------
  //# FIXTURES-BEGIN
  var DEV_FIXTURES = [
  {
    "schema_version": "2.0",
    "id": "q_fx000001",
    "type": "single_choice",
    "stem": "已知函数 $f(x)=x^2+1$，求其最小值（  ）",
    "difficulty": "L1",
    "options": [
      {
        "key": "A",
        "content": "$0$",
        "image_ids": []
      },
      {
        "key": "B",
        "content": "$1$",
        "image_ids": []
      },
      {
        "key": "C",
        "content": "$2$",
        "image_ids": []
      },
      {
        "key": "D",
        "content": "$3$",
        "image_ids": []
      }
    ],
    "answer": {
      "kind": "choice",
      "choice_keys": [
        "B"
      ],
      "final": "B"
    },
    "solution": "解析：配方得 $f(x)=(x-1)^2+1$，故最小值为 $1$。",
    "grade": "高一",
    "tags": [
      "二次函数",
      "配方法"
    ],
    "taxonomy": {
      "textbook": "人教A版·必修第一册",
      "chapter": "2. 一元二次函数",
      "section": "2.1 方程与不等式",
      "topic_ids": []
    },
    "source": {
      "paper_title": "军令 #23 假数据卷",
      "question_no": "1",
      "year": 2024,
      "exam_type": "一模",
      "school": "九章中学",
      "region": "本地"
    },
    "images": [],
    "extensions": {
      "org.jiuzhang.editor.dev": {
        "source_latex": "\\begin{question}\n已知函数 $f(x)=x^2+1$，求其最小值（  ）\n\\begin{choices}\n  \\item $0$\n  \\item $1$\n  \\item $2$\n  \\item $3$\n\\end{choices}\n\\end{question}\n\n\\begin{solution}\n答案：B\n解析：配方得 $f(x)=(x-1)^2+1$，故最小值为 $1$。\n\\end{solution}\n",
        "image_uri": "/static/icons/icon-192.png",
        "image_pages": [
          1
        ],
        "confidence": 0.93,
        "cross_page": false,
        "long_solution": false
      }
    },
    "meta": {
      "created_at": "2026-10-31T08:00:00+08:00",
      "updated_at": "2026-10-31T08:00:00+08:00",
      "revision": 1,
      "status": "draft"
    }
  }
];
  //# FIXTURES-END

  function devBlock(question) {
    var ext = question && question.extensions ? question.extensions[DEV_NS] : null;
    return ext && typeof ext === "object" ? ext : {};
  }

  function makeItem(question, source) {
    return {
      question: question,
      source: source,
      dev: devBlock(question),
      savedId: null,
      dirty: false,
      status: "pending"
    };
  }

  function loadFixtures() {
    state.items = DEV_FIXTURES.map(function (question) {
      var block = devBlock(question);
      var source = (typeof block.source_latex === "string" && block.source_latex)
        ? block.source_latex : buildExamSource(question);
      return makeItem(question, source);
    });
    state.active = 0;
  }

  // ---------- 载入真题（三端分离入口：题库点「去编辑」/ AI 命令） ----------
  function loadForEdit(questionId, from) {
    var id = String(questionId || "");
    if (!COMMAND_QUESTION_ID_RE.test(id)) return Promise.resolve(null);
    return hostCall("bank.get", { id: id }).then(function (document) {
      if (!document || !document.stem) return null;
      var item = makeItem(document, buildExamSource(document));
      item.savedId = document.id || id;
      item.status = "stored";
      state.items = [item];
      state.active = 0;
      state.dirty = false;
      scheduleRender();
      dock("录题工作台已把题目 " + id + " 序列化成 exam-zh 源码"
        + (from ? "（来自 " + from + "）" : "") + "。");
      return item;
    }).catch(function (error) {
      toast("载入题目失败：" + error.message, "error");
      dock("载入题目 " + id + " 失败：" + error.message);
      return null;
    });
  }

  // ---------- 三栏渲染 ----------
  function renderImageCell(item, index) {
    var cell = el("div", "ed-img-cell");
    cell.setAttribute("role", "listitem");
    var uri = safeAssetUri(item.dev && item.dev.image_uri);
    if (uri) {
      var frame = el("div", "ed-img-frame");
      var img = document.createElement("img");
      img.src = uri;
      img.alt = "第 " + (index + 1) + " 题原图";
      img.addEventListener("error", function () {
        if (img.parentNode) {
          img.parentNode.replaceChild(el("p", "ed-img-missing", "原图读取失败"), img);
        }
      });
      frame.appendChild(img);
      var box = el("div", "ed-img-box");
      box.setAttribute("data-box", "stem");
      frame.appendChild(box);
      cell.appendChild(frame);
    } else {
      cell.appendChild(el("p", "ed-img-missing", "本题没有原图（假数据只留占位）。"));
    }
    var paper = (item.question && item.question.source && item.question.source.paper_title) || "无来源卷";
    cell.appendChild(el("p", "ed-img-caption", "第 " + (index + 1) + " 题 · " + paper));
    return cell;
  }

  function renderSourceCell(item, index) {
    var cell = el("div", "ed-src-cell");
    cell.appendChild(el("span", "ed-src-tag", "第 " + (index + 1) + " 题 · exam-zh 全量源码"));
    var area = document.createElement("textarea");
    area.className = "ed-src-area";
    area.setAttribute("aria-label", "第 " + (index + 1) + " 题 LaTeX 源码");
    area.setAttribute("spellcheck", "false");
    area.readOnly = true;            // 阶段 1 只读；阶段 2 打开编辑并接双格式
    area.value = item.source;
    area.setAttribute("data-index", String(index));
    cell.appendChild(area);
    return cell;
  }

  function renderQuestionBlock(item, index) {
    var parsed = parseExamSource(item.source);
    var block = el("div", "ed-q-block");
    block.setAttribute("data-index", String(index));
    block.setAttribute("data-type", parsed.type);
    block.setAttribute("data-errors", String(parsed.errors.length));

    if (parsed.errors.length) {
      block.appendChild(el("p", "ed-opt-img", "源码尚未认全：" + parsed.errors.join("；")));
    }
    var stem = el("p", "ed-q-stem");
    stem.appendChild(el("span", "ed-num", (index + 1) + "."));
    appendRich(stem, parsed.stem || item.source);
    block.appendChild(stem);

    if (parsed.hasChoices) {
      var list = el("ul", "ed-choices");
      parsed.choices.forEach(function (content, position) {
        var key = OPTION_KEYS[position] || String(position + 1);
        var li = el("li");
        var badge = el("span", "ed-choice-key", key + ".");
        if (parsed.answer && parsed.answer.toUpperCase().indexOf(key) >= 0) {
          badge.className += " is-answer";
        }
        li.appendChild(badge);
        var text = el("span", "ed-choice-text");
        appendRich(text, content);
        li.appendChild(text);
        list.appendChild(li);
      });
      block.appendChild(list);
    }
    if (parsed.answer) block.appendChild(el("p", "ed-q-answer", "答案：" + parsed.answer));
    if (parsed.analysis) {
      var analysis = el("div", "ed-q-analysis");
      appendBody(analysis, parsed.analysis);
      block.appendChild(analysis);
    }
    if (parsed.stray) block.appendChild(el("pre", "ed-raw", parsed.stray));
    return block;
  }

  function growTextarea(node) {
    node.style.height = "auto";
    node.style.height = Math.max(node.scrollHeight, 60) + "px";
  }

  /** 行高取三栏较高者：三栏共用一条滚动，短栏余下的高度正是那层极淡底色。 */
  function alignRows() {
    var max = 0;
    for (var index = 0; index < state.items.length; index += 1) {
      var cells = [imageBodyEl.children[index], sourceBodyEl.children[index], renderBodyEl.children[index]];
      var rowH = 0;
      cells.forEach(function (cell) {
        if (cell && cell.offsetHeight > rowH) rowH = cell.offsetHeight;
      });
      cells.forEach(function (cell) {
        if (cell) cell.style.minHeight = rowH + "px";
      });
      if (index === 0) max = rowH;
    }
    Array.prototype.forEach.call(sourceBodyEl.querySelectorAll(".ed-src-area"), growTextarea);
    return max;
  }

  function markDirty() {
    state.dirty = state.items.some(function (each) { return each.dirty; });
    if (dirtyEl) {
      dirtyEl.setAttribute("data-dirty", state.dirty ? "true" : "false");
      dirtyEl.textContent = state.dirty ? "有未保存改动" : "未改动";
    }
  }

  function renderAll() {
    if (!root || root.hidden || !state.items.length) return;
    var started = Date.now();
    katexCount = 0;
    imageBodyEl.textContent = "";
    sourceBodyEl.textContent = "";
    renderBodyEl.textContent = "";
    var errorTotal = 0;
    state.items.forEach(function (item, index) {
      imageBodyEl.appendChild(renderImageCell(item, index));
      sourceBodyEl.appendChild(renderSourceCell(item, index));
      var block = renderQuestionBlock(item, index);
      errorTotal += Number(block.getAttribute("data-errors") || 0);
      renderBodyEl.appendChild(block);
    });
    var rowH = alignRows();
    var elapsed = Date.now() - started;

    var first = state.items[state.active] || state.items[0];
    var progressText = "第 " + (state.active + 1) + " / " + state.items.length + " 题";
    if (progressEl) {
      progressEl.textContent = progressText;
      progressEl.setAttribute("data-active", String(state.active + 1));
      progressEl.setAttribute("data-total", String(state.items.length));
    }
    if (formatEl) formatEl.setAttribute("data-format", state.format);
    if (metricsEl) {
      metricsEl.textContent = progressText + " · 渲染 " + elapsed + "ms";
      metricsEl.setAttribute("data-render-ms", String(elapsed));
      metricsEl.setAttribute("data-katex", String(katexCount));
      metricsEl.setAttribute("data-blocks", String(state.items.length));
      metricsEl.setAttribute("data-errors", String(errorTotal));
      metricsEl.setAttribute("data-question-id", (first && (first.savedId || first.question.id)) || "");
      metricsEl.setAttribute("data-row-h", String(rowH));
      metricsEl.setAttribute("data-pane-w", String(colsEl ? colsEl.clientWidth : 0));
    }
    if (imageNameEl) imageNameEl.textContent = (first && first.dev && first.dev.image_uri) || "未载入";
    markDirty();
  }

  function scheduleRender() {
    window.clearTimeout(renderTimer);
    renderTimer = window.setTimeout(renderAll, RENDER_DEBOUNCE_MS);
  }

  // ---------- 三栏拖宽（不能归零，只留极窄缝） ----------
  function applyWidths() {
    var total = colsEl ? colsEl.clientWidth : 0;
    if (total <= 0) return;
    var image = clampValue(state.widths.image, PANE_MIN, Math.max(PANE_MIN, total - PANE_MIN * 2 - SPLIT_W * 2));
    var source = clampValue(state.widths.source, PANE_MIN,
      Math.max(PANE_MIN, total - image - PANE_MIN - SPLIT_W * 2));
    state.widths.image = image;
    state.widths.source = source;
    colsEl.style.setProperty("--w-image", image + "px");
    colsEl.style.setProperty("--w-source", source + "px");
    if (metricsEl) metricsEl.setAttribute("data-pane-w", String(total));
  }

  function saveLayout() {
    hostCall("draft.save", { key: DRAFT_LAYOUT_KEY, value: { widths: state.widths } })
      .catch(function () { /* 布局偏好存不下就算了，不打扰老师 */ });
  }

  function queueLayoutSave() {
    window.clearTimeout(layoutTimer);
    layoutTimer = window.setTimeout(saveLayout, LAYOUT_DRAFT_MS);
  }

  function bindSplit(node, which) {
    if (!node) return;
    var drag = null;
    node.addEventListener("pointerdown", function (event) {
      drag = { x: event.clientX, image: state.widths.image, source: state.widths.source };
      node.setAttribute("data-drag", "true");
      if (node.setPointerCapture) node.setPointerCapture(event.pointerId);
      event.preventDefault();
    });
    node.addEventListener("pointermove", function (event) {
      if (!drag) return;
      var delta = event.clientX - drag.x;
      if (which === "image") state.widths.image = drag.image + delta;
      else state.widths.source = drag.source + delta;
      applyWidths();
    });
    function stop(event) {
      if (!drag) return;
      drag = null;
      node.removeAttribute("data-drag");
      if (node.releasePointerCapture && event && event.pointerId != null) {
        try { node.releasePointerCapture(event.pointerId); } catch (error) { /* 已经松开了 */ }
      }
      queueLayoutSave();
      scheduleRender();
    }
    node.addEventListener("pointerup", stop);
    node.addEventListener("pointercancel", stop);
    node.addEventListener("keydown", function (event) {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      var step = event.shiftKey ? 8 : 24;
      var delta = event.key === "ArrowLeft" ? -step : step;
      if (which === "image") state.widths.image += delta;
      else state.widths.source += delta;
      applyWidths();
      queueLayoutSave();
      scheduleRender();
      event.preventDefault();
    });
  }

  function syncScroll(from) {
    if (scrollLock) return;
    scrollLock = true;
    [imageBodyEl, sourceBodyEl, renderBodyEl].forEach(function (node) {
      if (node && node !== from) node.scrollTop = from.scrollTop;
    });
    window.requestAnimationFrame(function () { scrollLock = false; });
  }

  // ---------- 能力路由字典（军令 #20 的四条命令，v2 继续沿用同一批 id） ----------
  function commandReject(source, message, code, text) {
    respond(source, message.id, false, null, code, text);
  }

  function handleCommandExecute(source, message) {
    var payload = message.payload || {};
    var commandId = typeof payload.command_id === "string" ? payload.command_id : "";
    var context = payload.context && typeof payload.context === "object" ? payload.context : {};

    if (commandId === "org.jiuzhang.action.input.open_question") {
      var unknown = Object.keys(context).filter(function (key) { return key !== "question_id"; });
      if (unknown.length) {
        return commandReject(source, message, "BAD_PARAMS", "不认识的参数：" + unknown.join("、"));
      }
      if (typeof context.question_id !== "string" || !COMMAND_QUESTION_ID_RE.test(context.question_id)) {
        return commandReject(source, message, "BAD_PARAMS", "question_id 必须是合法的题目 id（q_ 开头）");
      }
      loadForEdit(context.question_id, "command").then(function (loaded) {
        if (!loaded) {
          commandReject(source, message, "COMMAND_FAILED", "没能载入题目 " + context.question_id);
          return;
        }
        respond(source, message.id, true, { question_id: context.question_id, editing: true });
      });
      return;
    }

    if (commandId === "org.jiuzhang.action.process.clean_latex") {
      if (Object.keys(context).length) {
        return commandReject(source, message, "BAD_PARAMS", "清洗命令不接受参数");
      }
      var touched = 0;
      state.items.forEach(function (item) {
        var cleaned = cleanExamSource(item.source);
        if (cleaned.touched) {
          item.source = cleaned.text;
          item.dirty = true;
          touched += cleaned.touched;
        }
      });
      scheduleRender();
      return respond(source, message.id, true, { touched: touched });
    }

    if (commandId === "org.jiuzhang.action.input.save_question") {
      return commandReject(source, message, "COMMAND_FAILED",
        "军令 #23 阶段 1 只做三栏骨架，保存入库在阶段 2 接入");
    }
    if (commandId === "org.jiuzhang.action.process.create_variant") {
      return commandReject(source, message, "COMMAND_FAILED",
        "军令 #23 阶段 1 只做三栏骨架，派生变式随阶段 2 的保存一起接入");
    }
    commandReject(source, message, "UNKNOWN_COMMAND", "未声明的方法：" + commandId);
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
      if (message.event === "system.open_editor") {
        var wanted = (message.payload && message.payload.question_id) || "";
        var origin = (message.payload && message.payload.from) || "";
        if (wanted) loadForEdit(wanted, origin);
        return;
      }
      if (message.event === "editor.apply_patch") {
        toast("AI 回填将在军令 #23 阶段 3（档 1 帮改）接入，本次未改动源码", "info");
        return;
      }
      if (message.event === "ui.params.changed") {
        return;   // 辅助栏参数由阶段 2 接管，画布此阶段不响应
      }
      return;
    }

    if (message.kind !== "request") return;

    if (message.method === "plugin.activate") {
      state.slot = (message.payload && message.payload.slot) || "stage.center";
      if (state.slot !== "stage.center") {
        // 右栏那一个帧是辅助栏实例，阶段 2 才铺表单；先认领插槽，不留白屏。
        return respond(event.source, message.id, true, { ready: true, plugin_id: PLUGIN_ID });
      }
      root.hidden = false;
      loadFixtures();
      applyWidths();
      renderAll();
      if (sourceHintEl) sourceHintEl.textContent = "只读 · 阶段 1";
      hostCall("draft.load", { key: DRAFT_LAYOUT_KEY }).then(function (result) {
        var value = result && result.value;
        if (value && value.widths) {
          state.widths.image = Number(value.widths.image) || state.widths.image;
          state.widths.source = Number(value.widths.source) || state.widths.source;
          applyWidths();
        }
        state.layoutReady = true;
      }).catch(function () { state.layoutReady = true; });
      return respond(event.source, message.id, true, { ready: true, plugin_id: PLUGIN_ID });
    }
    if (message.method === "plugin.deactivate") {
      root.hidden = true;
      return respond(event.source, message.id, true, { ready: false });
    }
    if (message.method === "command.execute") {
      return handleCommandExecute(event.source, message);
    }
    respond(event.source, message.id, false, null, "UNSUPPORTED_METHOD",
      "未实现的方法：" + String(message.method));
  });

  // ---------- 启动 ----------
  function bind() {
    bindSplit(document.getElementById("edSplitImage"), "image");
    bindSplit(document.getElementById("edSplitSource"), "source");
    [imageBodyEl, sourceBodyEl, renderBodyEl].forEach(function (node) {
      if (node) node.addEventListener("scroll", function () { syncScroll(node); });
    });
    if (window.ResizeObserver && colsEl) {
      var observer = new window.ResizeObserver(function () {
        applyWidths();
        scheduleRender();
      });
      observer.observe(colsEl);
    }
    window.addEventListener("beforeunload", function () {
      if (layoutTimer) {
        window.clearTimeout(layoutTimer);
        saveLayout();
      }
    });
  }

  bind();

  // 真机探针用的调试面：只把解析/重组结果交给 Playwright 复核，不参与业务分支。
  window.__jzoEditorV2 = {
    version: "2.0.0-stage1",
    parseExamSource: parseExamSource,
    buildExamSource: buildExamSource,
    cleanExamSource: cleanExamSource,
    fixtures: DEV_FIXTURES,
    state: state,
    renderAll: renderAll
  };
})();
