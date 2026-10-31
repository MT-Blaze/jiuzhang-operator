/**
 * 录题工作台 v2（军令 #23）。
 *
 * 画布实例（stage.center）只有三栏：左原图 | 中全量 exam-zh 源码 | 右渲染。
 * 源码是唯一的录入面——一整段 \begin{question}…\end{solution}；
 * 题型、难度、来源、考向与审核动作一律在辅助栏（sidebar.right）。
 *
 * 同一个插件的两个沙箱帧拿不到彼此的 DOM，只走底座开好的四条合法通道：
 *   画布 → 辅助栏：发布 stage.selection（当前题的源码、进度与元数据默认值）；
 *   辅助栏 → 画布：ui.params.set（格式一 / 格式二），由宿主广播 ui.params.changed；
 *   两帧共享：draft.save / draft.load 交宿主代持的工作清单与元数据草稿；
 *   写库：辅助栏经宿主 bank.create / bank.update 落库，成功回音 system.question_updated。
 *
 * 插件住在不透明源沙箱里：不联网、不碰浏览器本地存储、不碰宿主 DOM，令牌永远在宿主手里。
 */
(function () {
  "use strict";

  var PROTOCOL = "jzo-plugin/1";
  var PLUGIN_ID = "org.jiuzhang.editor";
  var REQUEST_TIMEOUT_MS = 20000;
  // 宿主给模型的额度是 60s（stage.js 的 AGENT_TIMEOUT_MS），插件按 20s 等会把慢回答误报成失败
  var AI_REQUEST_TIMEOUT_MS = 65000;
  var RENDER_DEBOUNCE_MS = 120;
  var LAYOUT_DRAFT_MS = 400;
  var WORKLIST_DRAFT_MS = 600;
  var SELECTION_MS = 160;
  var PANEL_DRAFT_RETRY_MS = 900;
  var RECEIPT_RETRY_MS = 350;
  var RECEIPT_RETRY_MAX = 4;
  var SPLIT_W = 6;
  var PANE_MIN = 28;
  var DEV_NS = "org.jiuzhang.editor.dev";
  var DRAFT_LAYOUT_KEY = "editor:v2:layout";
  var DRAFT_WORKLIST_KEY = "editor:v2:worklist";
  var DRAFT_META_KEY = "editor:v2:meta";
  var DRAFT_RECEIPT_KEY = "editor:v2:receipts";
  var OPTION_KEYS = "ABCDEFGH".split("");
  var COMMAND_QUESTION_ID_RE = /^q_[A-Za-z0-9_-]{1,78}$/;
  var TOPIC_ID_RE = /^tp_(bo|ch|se|kx)[0-9a-f]{8}$/;
  var TYPE_VALUES = ["single_choice", "multiple_choice", "fill_blank", "solution"];
  var TYPE_LABELS = {
    single_choice: "单选题", multiple_choice: "多选题",
    fill_blank: "填空题", solution: "解答题"
  };
  var DIFFICULTY_VALUES = ["L1", "L2", "L3", "L4"];
  var FORMATS = { latex: true, boxed: true };
  var AI_STATE_LABELS = {
    idle: "未发起", sending: "等模型回话", cleaning: "清洗中",
    ready: "待老师裁决", error: "改写失败"
  };
  var STEM_MAX = 50000;
  var FIELD_MAX = 20000;
  var TOPIC_LIMIT = 8;
  var TAG_LIMIT = 32;
  // 宿主 stage.js 对 instruction 的截断额度就是 400，面板先按同一个数拦，别让老师的长指令被悄悄切尾
  var AI_ASK_MAX = 400;

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
  var savedEl = document.getElementById("edSaved");
  var poolEl = document.getElementById("edPool");
  var batchNoteEl = document.getElementById("edBatchNote");
  var saveAllEl = document.getElementById("edSaveAll");
  var poolStashEl = document.getElementById("edPoolStash");

  var panelRoot = document.getElementById("epRoot");
  var panelProgressEl = document.getElementById("epProgress");
  var panelStatusEl = document.getElementById("epStatus");
  var panelConfidenceEl = document.getElementById("epConfidence");
  var panelFormatLatexEl = document.getElementById("epFormatLatex");
  var panelFormatBoxedEl = document.getElementById("epFormatBoxed");
  var panelTypeEl = document.getElementById("epType");
  var panelTypeNoteEl = document.getElementById("epTypeNote");
  var panelDifficultyEl = document.getElementById("epDifficulty");
  var panelGradeEl = document.getElementById("epGrade");
  var panelPaperEl = document.getElementById("epPaper");
  var panelQuestionNoEl = document.getElementById("epQuestionNo");
  var panelExamTypeEl = document.getElementById("epExamType");
  var panelYearEl = document.getElementById("epYear");
  var panelTagsEl = document.getElementById("epTags");
  var panelMountedEl = document.getElementById("epMounted");
  var panelTreeEl = document.getElementById("epTopicTree");
  var panelTopicErrorEl = document.getElementById("epTopicError");
  var panelSaveEl = document.getElementById("epSave");
  var panelVariantEl = document.getElementById("epVariant");
  var panelMessageEl = document.getElementById("epMessage");
  var panelMetricsEl = document.getElementById("epMetrics");
  var panelAiFieldEl = document.getElementById("epAiField");
  var panelAiAskEl = document.getElementById("epAiAsk");
  var panelAiSendEl = document.getElementById("epAiSend");
  var panelAiCleanEl = document.getElementById("epAiClean");
  var panelAiStateEl = document.getElementById("epAiState");
  var panelAiNoteEl = document.getElementById("epAiNote");
  var panelAiPreviewEl = document.getElementById("epAiPreview");
  var panelAiApplyEl = document.getElementById("epAiApply");
  var panelAiDiscardEl = document.getElementById("epAiDiscard");

  var pending = new Map();
  var requestSeq = 0;
  var renderTimer = 0;
  var toastTimer = 0;
  var layoutTimer = 0;
  var worklistTimer = 0;
  var selectionTimer = 0;
  var metaTimer = 0;
  var mathCache = new Map();
  var katexCount = 0;
  var scrollLock = false;
  var scrollRestore = false;
  var lastErrorTotal = 0;

  var state = {
    slot: "stage.center",
    items: [],
    active: 0,
    format: "latex",
    widths: { image: 260, source: 360 },
    dirty: false,
    layoutReady: false,
    worklistReady: false,
    batchSaving: false
  };

  var panel = {
    ready: false,
    selection: null,
    source: "",
    meta: {},
    uiRevisions: null,
    receipts: [],
    format: "latex",
    topics: { roots: null, children: {}, open: {}, loading: {} },
    saving: false,
    ai: { state: "idle", field: "", key: "", value: "", note: "", mock: false, busy: false }
  };

  // ---------- 宿主通信 ----------
  function hostCall(method, payload, timeoutMs) {
    return new Promise(function (resolve, reject) {
      requestSeq += 1;
      var id = "edv2" + requestSeq + "-" + Date.now().toString(36);
      var limit = Number(timeoutMs) > 0 ? Number(timeoutMs) : REQUEST_TIMEOUT_MS;
      var timer = window.setTimeout(function () {
        pending.delete(id);
        reject(new Error("宿主响应超时（" + Math.round(limit / 1000) + "s）"));
      }, limit);
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

  /** 宿主错误码必须原样带出来：409 撞号、422 不符合 Schema 与「没权限」是三种话。 */
  function hostError(raw) {
    var error = new Error((raw && raw.message) || "宿主返回失败");
    error.code = String((raw && raw.code) || "HOST_ERROR");
    error.retryable = Boolean(raw && raw.retryable);
    return error;
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

  /** 辅助栏的落地话术：状态区常驻，不用老师盯着画布的一闪而过的提示。 */
  function panelSay(text, tone, state) {
    if (!panelMessageEl) return;
    panelMessageEl.textContent = text;
    panelMessageEl.setAttribute("data-tone", tone || "info");
    panelMessageEl.setAttribute("data-save-state", state || "idle");
  }

  function trunc(value, limit) {
    var text = String(value == null ? "" : value);
    return text.length > limit ? text.slice(0, limit) : text;
  }

  function nowIso() {
    var date = new Date();
    var pad = function (n) { return (n < 10 ? "0" : "") + n; };
    var offset = -date.getTimezoneOffset();
    var sign = offset >= 0 ? "+" : "-";
    var hours = pad(Math.floor(Math.abs(offset) / 60));
    var minutes = pad(Math.abs(offset) % 60);
    return date.getFullYear() + "-" + pad(date.getMonth() + 1) + "-" + pad(date.getDate())
      + "T" + pad(date.getHours()) + ":" + pad(date.getMinutes()) + ":" + pad(date.getSeconds())
      + sign + hours + ":" + minutes;
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
      hasChoices: false, hasFillin: false, hasSolution: false, multi: false, type: "", errors: []
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

    result.hasSolution = Boolean(solution);
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

  // ---------- AI 帮改（档 1）：只动题干段/解析段的正文，环境骨架一律不碰 ----------
  /** matchEnv 的偏移版：回填要知道「段落在整段源码的第几个字」，光有正文不够。 */
  function envSpan(text, name, from) {
    var begin = "\\begin{" + name + "}";
    var endTag = "\\end{" + name + "}";
    var start = text.indexOf(begin, Number(from) || 0);
    if (start < 0) return null;
    var bodyAt = start + begin.length;
    var stop = text.indexOf(endTag, bodyAt);
    if (stop < 0) return null;
    return { beginAt: start, bodyAt: bodyAt, bodyEnd: stop, endAt: stop + endTag.length };
  }

  /**
   * 题干段 = 题干环境正文里、choices 之前的那一段；
   * 解析段 = solution 正文里、「答案：」首行之后的那一段。
   * 这两段就是 AI 与清洗的全部活动范围—— choices 与答案行由格式宪法锁死。
   */
  function fieldRanges(src) {
    var text = String(src == null ? "" : src).replace(/\r\n/g, "\n");
    var stem = envSpan(text, "question") || envSpan(text, "problem");
    var solution = envSpan(text, "solution");
    var out = { stem: null, solution: null };
    if (stem) {
      var choices = envSpan(text, "choices", stem.bodyAt);
      var stemEnd = choices && choices.beginAt < stem.bodyEnd ? choices.beginAt : stem.bodyEnd;
      out.stem = { start: stem.bodyAt, end: stemEnd };
    }
    if (solution) {
      var body = text.slice(solution.bodyAt, solution.bodyEnd);
      var answerLine = /^[ \t]*答案\s*[:：][^\n]*\n?/.exec(body);
      out.solution = {
        start: solution.bodyAt + (answerLine ? answerLine[0].length : 0),
        end: solution.bodyEnd
      };
    }
    return out;
  }

  function fieldLabel(field) { return field === "solution" ? "解析" : "题干"; }

  /** 光标/选区落在哪一段：choices、答案行与环境名之外一律不算可改字段，如实回 null。 */
  function fieldAtOffset(src, offset) {
    var ranges = fieldRanges(src);
    var position = Math.max(0, Number(offset) || 0);
    if (ranges.solution && position >= ranges.solution.start && position <= ranges.solution.end) {
      return "solution";
    }
    if (ranges.stem && position >= ranges.stem.start && position <= ranges.stem.end) {
      return "stem";
    }
    return "";
  }

  function replaceField(src, field, value) {
    var text = String(src == null ? "" : src);
    var range = fieldRanges(text)[field === "solution" ? "solution" : "stem"];
    if (!range) {
      return { ok: false, message: "源码里找不到" + fieldLabel(field) + "段：先在格式一补上对应环境" };
    }
    if (String(value == null ? "" : value).length > FIELD_MAX) {
      return { ok: false, message: fieldLabel(field) + "改写超出 " + FIELD_MAX + " 字上限，未回填" };
    }
    var body = String(value == null ? "" : value).trim();
    return { ok: true, text: text.slice(0, range.start) + "\n" + body + "\n" + text.slice(range.end) };
  }

  /** 目标题的键要编进回填请求 id 里：宿主的 editor.apply_patch 只带 {id, field, value}。 */
  function patchIdFor(key) {
    return ("ai1-" + String(key == null ? "" : key).replace(/[^A-Za-z0-9_-]/g, "-")).slice(0, 80);
  }

  function keyFromPatchId(id) {
    return String(id == null ? "" : id).indexOf("ai1-") === 0 ? String(id).slice(4) : "";
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
  },
  {
    "schema_version": "2.0",
    "id": "q_fx000002",
    "type": "multiple_choice",
    "stem": "已知集合 $A=\\{x\\mid x^2-3x+2=0\\}$，则下列元素属于 $A$ 的是（多选）（  ）",
    "difficulty": "L1",
    "options": [
      {
        "key": "A",
        "content": "$1$",
        "image_ids": []
      },
      {
        "key": "B",
        "content": "$2$",
        "image_ids": []
      },
      {
        "key": "C",
        "content": "$3$",
        "image_ids": []
      },
      {
        "key": "D",
        "content": "$4$",
        "image_ids": []
      }
    ],
    "answer": {
      "kind": "choice",
      "choice_keys": [
        "A",
        "B"
      ],
      "final": "AB"
    },
    "solution": "解析：由 $x^2-3x+2=(x-1)(x-2)=0$ 得 $x=1$ 或 $x=2$，故 $A=\\{1,2\\}$。",
    "grade": "高一",
    "tags": [
      "集合",
      "一元二次方程"
    ],
    "taxonomy": {
      "textbook": "人教A版·必修第一册",
      "chapter": "1. 集合与常用逻辑用语",
      "section": "1.1 集合的概念",
      "topic_ids": []
    },
    "source": {
      "paper_title": "军令 #23 假数据卷",
      "question_no": "2",
      "year": 2024,
      "exam_type": "一模",
      "school": "九章中学",
      "region": "本地"
    },
    "images": [],
    "extensions": {
      "org.jiuzhang.editor.dev": {
        "source_latex": "\\begin{question}\n已知集合 $A=\\{x\\mid x^2-3x+2=0\\}$，则下列元素属于 $A$ 的是（多选）（  ）\n\\begin{choices}\n  \\item $1$\n  \\item $2$\n  \\item $3$\n  \\item $4$\n\\end{choices}\n\\end{question}\n\n\\begin{solution}\n答案：AB\n解析：由 $x^2-3x+2=(x-1)(x-2)=0$ 得 $x=1$ 或 $x=2$，故 $A=\\{1,2\\}$。\n\\end{solution}\n",
        "image_uri": "/static/icons/icon-192.png",
        "image_pages": [
          1
        ],
        "confidence": 0.88,
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
  },
  {
    "schema_version": "2.0",
    "id": "q_fx000003",
    "type": "fill_blank",
    "stem": "已知 $a>0$，则 $a+\\dfrac{1}{a}$ 的最小值为\\fillin",
    "difficulty": "L2",
    "answer": {
      "kind": "expression",
      "content": "$2$",
      "final": "$2$"
    },
    "solution": "解析：由均值不等式 $a+\\dfrac{1}{a}\\ge 2\\sqrt{a\\cdot\\dfrac{1}{a}}=2$，当且仅当 $a=1$ 时取等。",
    "grade": "高一",
    "tags": [
      "均值不等式",
      "最值"
    ],
    "taxonomy": {
      "textbook": "人教A版·必修第一册",
      "chapter": "2. 一元二次函数",
      "section": "2.2 基本不等式",
      "topic_ids": []
    },
    "source": {
      "paper_title": "军令 #23 假数据卷",
      "question_no": "7",
      "year": 2024,
      "exam_type": "一模",
      "school": "九章中学",
      "region": "本地"
    },
    "images": [],
    "extensions": {
      "org.jiuzhang.editor.dev": {
        "source_latex": "\\begin{question}\n已知 $a>0$，则 $a+\\dfrac{1}{a}$ 的最小值为\\fillin\n\\end{question}\n\n\\begin{solution}\n答案：$2$\n解析：由均值不等式 $a+\\dfrac{1}{a}\\ge 2\\sqrt{a\\cdot\\dfrac{1}{a}}=2$，当且仅当 $a=1$ 时取等。\n\\end{solution}\n",
        "image_uri": "/static/icons/icon-192.png",
        "image_pages": [
          1
        ],
        "confidence": 0.76,
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
  },
  {
    "schema_version": "2.0",
    "id": "q_fx000004",
    "type": "solution",
    "stem": "已知等差数列 $\\{a_n\\}$ 的前 $n$ 项和为 $S_n$，若 $a_1=1$，$a_4=7$，求 $S_5$。",
    "difficulty": "L3",
    "answer": {
      "kind": "expression",
      "content": "$S_5=25$",
      "final": "$S_5=25$"
    },
    "solution": "解析：由 $a_4=a_1+3d=7$ 得 $d=2$。\n\n于是 $S_5=5a_1+\\dfrac{5\\times 4}{2}d=5+20=25$。\n\n$$S_5=\\dfrac{5(a_1+a_5)}{2}=25$$",
    "grade": "高二",
    "tags": [
      "等差数列",
      "前n项和"
    ],
    "taxonomy": {
      "textbook": "人教A版·选择性必修第二册",
      "chapter": "4. 数列",
      "section": "4.2 等差数列",
      "topic_ids": []
    },
    "source": {
      "paper_title": "军令 #23 假数据卷",
      "question_no": "17",
      "year": 2024,
      "exam_type": "一模",
      "school": "九章中学",
      "region": "本地"
    },
    "images": [],
    "extensions": {
      "org.jiuzhang.editor.dev": {
        "source_latex": "\\begin{problem}\n已知等差数列 $\\{a_n\\}$ 的前 $n$ 项和为 $S_n$，若 $a_1=1$，$a_4=7$，求 $S_5$。\n\\end{problem}\n\n\\begin{solution}\n答案：$S_5=25$\n解析：由 $a_4=a_1+3d=7$ 得 $d=2$。\n\n于是 $S_5=5a_1+\\dfrac{5\\times 4}{2}d=5+20=25$。\n\n$$S_5=\\dfrac{5(a_1+a_5)}{2}=25$$\n\\end{solution}\n",
        "image_uri": "/static/icons/icon-512.png",
        "image_pages": [
          3
        ],
        "confidence": 0.61,
        "cross_page": true,
        "long_solution": true
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

  function itemKey(question, index) {
    var id = question && question.id ? String(question.id) : "";
    return id || "idx:" + index;
  }

  function makeItem(question, source, index) {
    return {
      question: question,
      source: source,
      dev: devBlock(question),
      key: itemKey(question, index || 0),
      savedId: null,
      dirty: false,
      status: "pending",
      parsed: null
    };
  }

  function loadFixtures() {
    state.items = DEV_FIXTURES.map(function (question, index) {
      var block = devBlock(question);
      var source = (typeof block.source_latex === "string" && block.source_latex)
        ? block.source_latex : buildExamSource(question);
      return makeItem(question, source, index);
    });
    state.active = 0;
  }

  // ---------- 载入真题（三端分离入口：题库点「去编辑」/ AI 命令） ----------
  function loadForEdit(questionId, from) {
    var id = String(questionId || "");
    if (!COMMAND_QUESTION_ID_RE.test(id)) return Promise.resolve(null);
    return hostCall("bank.get", { id: id }).then(function (document) {
      if (!document || !document.stem) return null;
      var item = makeItem(document, buildExamSource(document), 0);
      item.savedId = document.id || id;
      item.status = "stored";
      state.items = [item];
      state.active = 0;
      state.dirty = false;
      scheduleRender();
      publishSelectionSoon();
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
    cell.setAttribute("data-index", String(index));
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
    var jump = el("button", "ed-img-jump", "跳到第 " + (index + 1) + " 题");
    jump.type = "button";
    jump.setAttribute("data-index", String(index));
    jump.setAttribute("aria-label", "跳到第 " + (index + 1) + " 题 · " + paper);
    jump.addEventListener("click", function () { jumpTo(index); });
    cell.appendChild(jump);
    cell.appendChild(el("p", "ed-img-caption", "第 " + (index + 1) + " 题 · " + paper));
    return cell;
  }

  /** 格式一：一整段 exam-zh 源码，可编辑——它是唯一的录入面。 */
  function renderSourceCell(item, index) {
    if (state.format === "boxed") return renderBoxedCell(item, index);
    var cell = el("div", "ed-src-cell");
    cell.setAttribute("data-index", String(index));
    cell.appendChild(el("span", "ed-src-tag", "第 " + (index + 1) + " 题 · exam-zh 全量源码"));
    var area = document.createElement("textarea");
    area.className = "ed-src-area";
    area.setAttribute("aria-label", "第 " + (index + 1) + " 题 LaTeX 源码");
    area.setAttribute("spellcheck", "false");
    area.setAttribute("data-index", String(index));
    area.setAttribute("data-field", "source");
    area.value = item.source;
    area.addEventListener("input", function () {
      onSourceInput(index, area.value);
    });
    // 选区也要上桥：AI 帮改靠光标落在哪一段来认字段，只发源码不够
    ["click", "keyup", "select"].forEach(function (type) {
      area.addEventListener(type, publishSelectionSoon);
    });
    cell.appendChild(area);
    return cell;
  }

  /** 格式二的底线：环境骨架不完整或有游离文本时，绝不自动重组——先如实说明。 */
  function boxedBlockReason(parsed) {
    if (parsed.stray) return "源码里有环境外的内容，请先在格式一清掉再拆框";
    if (!parsed.env) return "缺 \\begin{question} 或 \\begin{problem}，拆不出框";
    if (!parsed.hasSolution) return "缺 \\begin{solution}，答案与解析没有归属";
    if (parsed.hasChoices && parsed.choices.length < 2) return "选项不足两项";
    return "";
  }

  function boxFieldCell(cell, index, label, envName, value, field, pos, multiline) {
    var wrap = el("div", "ed-box");
    var head = el("div", "ed-box-head");
    head.appendChild(el("span", "ed-box-env", envName));
    head.appendChild(el("span", "ed-box-field", label));
    wrap.appendChild(head);
    var node = document.createElement(multiline ? "textarea" : "input");
    node.className = multiline ? "ed-box-area ed-box-textarea" : "ed-box-area ed-box-input";
    node.setAttribute("data-index", String(index));
    node.setAttribute("data-field", field);
    if (pos != null) node.setAttribute("data-pos", String(pos));
    node.setAttribute("aria-label", label + "（" + envName + " 内容，只能改内容）");
    node.setAttribute("spellcheck", "false");
    if (!multiline) node.setAttribute("type", "text");
    node.value = value;
    node.addEventListener("input", function () {
      onBoxInput(index, field, pos, node.value);
    });
    if (field === "stem" || field === "solution") {
      ["click", "keyup", "select"].forEach(function (type) {
        node.addEventListener(type, publishSelectionSoon);
      });
    }
    wrap.appendChild(node);
    cell.appendChild(wrap);
    return node;
  }

  /** 格式二：框里只有内容，\begin{…} 骨架是写死的标签，摸不到也改不了。 */
  function renderBoxedCell(item, index) {
    var cell = el("div", "ed-boxed");
    cell.setAttribute("data-index", String(index));
    var parsed = parsedOf(item);
    cell.appendChild(el("span", "ed-src-tag", "第 " + (index + 1) + " 题 · 格式二（改完自动重组格式一）"));
    var reason = boxedBlockReason(parsed);
    if (reason) {
      cell.appendChild(el("p", "ed-boxed-blocked", "格式二暂不可用：" + reason));
      var area = document.createElement("textarea");
      area.className = "ed-src-area";
      area.setAttribute("aria-label", "第 " + (index + 1) + " 题 LaTeX 源码");
      area.setAttribute("spellcheck", "false");
      area.setAttribute("data-index", String(index));
      area.setAttribute("data-field", "source");
      area.value = item.source;
      area.addEventListener("input", function () {
        onSourceInput(index, area.value);
      });
      cell.appendChild(area);
      return cell;
    }
    boxFieldCell(cell, index, "题干", "\\begin{" + parsed.env + "}", parsed.stem, "stem", null, true);
    if (parsed.hasChoices) {
      parsed.choices.forEach(function (content, position) {
        boxFieldCell(cell, index, "选项 " + (OPTION_KEYS[position] || position + 1),
          "\\item", content, "choice", position, true);
      });
    }
    boxFieldCell(cell, index, "答案", "\\begin{solution} 首行", parsed.answer, "answer", null, false);
    boxFieldCell(cell, index, "解析", "\\begin{solution} 内", parsed.analysis, "analysis", null, true);
    return cell;
  }

  /** 框里的内容 → 结构化题目；环境骨架由 buildExamSource 重新给出，不接受外部改写。 */
  function boxesToQuestion(parsed, stem, choices, answer, analysis) {
    var type = parsed.type;
    var question = {
      type: type,
      stem: typeof stem === "string" ? stem : parsed.stem,
      options: [],
      solution: typeof analysis === "string" ? analysis : parsed.analysis
    };
    var list = Array.isArray(choices) ? choices : parsed.choices;
    var text = typeof answer === "string" ? answer : parsed.answer;
    if (type === "single_choice" || type === "multiple_choice") {
      question.options = list.map(function (content, position) {
        return { key: OPTION_KEYS[position] || "A", content: String(content == null ? "" : content) };
      });
      var letters = String(text || "").toUpperCase().replace(/[^A-H]/g, "");
      var unique = [];
      for (var i = 0; i < letters.length; i += 1) {
        if (unique.indexOf(letters.charAt(i)) < 0) unique.push(letters.charAt(i));
      }
      if (type === "single_choice") unique = unique.slice(0, 1);
      question.answer = { kind: "choice", choice_keys: unique, final: unique.join("") };
    } else {
      var value = String(text || "");
      question.answer = {
        kind: type === "fill_blank" ? "expression" : "text",
        content: value,
        final: value
      };
    }
    return question;
  }

  function onSourceInput(index, value) {
    var item = state.items[index];
    if (!item || item.source === value) return;
    item.source = value;
    item.parsed = null;
    item.dirty = true;
    refreshRow(index);
  }

  function onBoxInput(index, field, pos, value) {
    var item = state.items[index];
    if (!item) return;
    var parsed = item.parsed || parseExamSource(item.source);
    item.parsed = parsed;
    var patch = parsed.patch || {
      stem: parsed.stem, choices: parsed.choices.slice(), answer: parsed.answer, analysis: parsed.analysis
    };
    if (field === "choice") {
      var list = patch.choices.slice();
      list[pos] = value;
      patch.choices = list;
    } else if (field === "stem") {
      patch.stem = value;
    } else if (field === "answer") {
      patch.answer = value;
    } else if (field === "analysis") {
      patch.analysis = value;
    } else {
      return;
    }
    parsed.patch = patch;
    var next = buildExamSource(boxesToQuestion(parsed, patch.stem, patch.choices, patch.answer, patch.analysis));
    if (next === item.source) return;
    item.source = next;
    item.parsed = null;
    item.dirty = true;
    refreshRow(index);
  }

  function parsedOf(item) {
    if (!item.parsed) item.parsed = parseExamSource(item.source);
    return item.parsed;
  }

  function renderQuestionBlock(item, index) {
    var parsed = parsedOf(item);
    var block = el("div", "ed-q-block");
    block.setAttribute("data-index", String(index));
    block.setAttribute("data-type", parsed.type);
    block.setAttribute("data-errors", String(parsed.errors.length));
    item.errorCount = parsed.errors.length;

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
    Array.prototype.forEach.call(
      sourceBodyEl.querySelectorAll(".ed-src-area, .ed-box-textarea"), growTextarea);
    return max;
  }

  function markDirty() {
    state.dirty = state.items.some(function (each) { return each.dirty; });
    if (dirtyEl) {
      dirtyEl.setAttribute("data-dirty", state.dirty ? "true" : "false");
      dirtyEl.textContent = state.dirty ? "有未保存改动" : "未改动";
    }
  }

  function captureFocus() {
    var node = document.activeElement;
    if (!node || !node.getAttribute || node.getAttribute("data-field") == null) return null;
    return {
      index: node.getAttribute("data-index"),
      field: node.getAttribute("data-field"),
      pos: node.getAttribute("data-pos"),
      start: node.selectionStart,
      end: node.selectionEnd
    };
  }

  function restoreFocus(info) {
    if (!info || !sourceBodyEl) return;
    var selector = '[data-field="' + info.field + '"][data-index="' + info.index + '"]';
    if (info.pos != null) selector += '[data-pos="' + info.pos + '"]';
    var node = sourceBodyEl.querySelector(selector);
    if (!node) return;
    node.focus();
    if (info.start != null) {
      try { node.setSelectionRange(info.start, info.end); } catch (error) { /* input 不一定支持 */ }
    }
  }

  function updateStatusbar(elapsed, rowH) {
    var first = state.items[state.active] || state.items[0];
    var progressText = "第 " + (state.active + 1) + " / " + state.items.length + " 题";
    if (progressEl) {
      progressEl.textContent = progressText;
      progressEl.setAttribute("data-active", String(state.active + 1));
      progressEl.setAttribute("data-total", String(state.items.length));
    }
    if (formatEl) formatEl.setAttribute("data-format", state.format);
    var errorTotal = 0;
    state.items.forEach(function (item) { errorTotal += Number(item.errorCount || 0); });
    if (metricsEl) {
      metricsEl.textContent = progressText + " · 渲染 " + elapsed + "ms";
      metricsEl.setAttribute("data-render-ms", String(elapsed));
      metricsEl.setAttribute("data-katex", String(katexCount));
      metricsEl.setAttribute("data-blocks", String(state.items.length));
      metricsEl.setAttribute("data-errors", String(errorTotal));
      metricsEl.setAttribute("data-question-id", (first && (first.savedId || first.question.id)) || "");
      metricsEl.setAttribute("data-row-h", String(rowH || 0));
      metricsEl.setAttribute("data-pane-w", String(colsEl ? colsEl.clientWidth : 0));
    }
    if (imageNameEl) imageNameEl.textContent = (first && first.dev && first.dev.image_uri) || "未载入";
    markDirty();
    markActiveRow();
    renderPool();
  }

  /**
   * 换了当前题但没重新渲染：只回灌进度与状态位。
   * render-ms 读回上一次实测值——滚一下不许冒充刚渲染过，也不许写成 0。
   */
  function syncActiveBits() {
    var elapsed = Number(metricsEl && metricsEl.getAttribute("data-render-ms"));
    var rowH = Number(metricsEl && metricsEl.getAttribute("data-row-h"));
    updateStatusbar(isNaN(elapsed) ? 0 : elapsed, isNaN(rowH) ? 0 : rowH);
  }

  function renderAll() {
    if (!root || root.hidden || !state.items.length) return;
    var focus = captureFocus();
    var scrolls = [imageBodyEl, sourceBodyEl, renderBodyEl].map(function (node) {
      return node ? node.scrollTop : 0;
    });
    var started = Date.now();
    katexCount = 0;
    imageBodyEl.textContent = "";
    sourceBodyEl.textContent = "";
    renderBodyEl.textContent = "";
    state.items.forEach(function (item, index) {
      imageBodyEl.appendChild(renderImageCell(item, index));
      sourceBodyEl.appendChild(renderSourceCell(item, index));
      renderBodyEl.appendChild(renderQuestionBlock(item, index));
    });
    var rowH = alignRows();
    restoreFocus(focus);
    // 清空重建会把滚动线抹回顶部：批量界面里老师的阅读位置必须原地保住
    scrollRestore = true;
    [imageBodyEl, sourceBodyEl, renderBodyEl].forEach(function (node, position) {
      if (node) node.scrollTop = scrolls[position] || 0;
    });
    window.requestAnimationFrame(function () { scrollRestore = false; });
    updateStatusbar(Date.now() - started, rowH);
  }

  /**
   * 只重建改动那一题的渲染行：源码框继续持有焦点与光标，老师边打字边看到排版结果。
   * 整屏重排留给挂载、格式切换与拖宽——那时焦点本来就不在框里。
   */
  function refreshRow(index) {
    if (!root || root.hidden) return;
    var item = state.items[index];
    if (!item) return;
    var holder = renderBodyEl.children[index];
    if (!holder) {
      scheduleRender();
    } else {
      var started = Date.now();
      var block = renderQuestionBlock(item, index);
      renderBodyEl.replaceChild(block, holder);
      var rowH = alignRows();
      updateStatusbar(Date.now() - started, rowH);
    }
    publishSelectionSoon();
    queueWorklistSave();
  }

  function scheduleRender() {
    window.clearTimeout(renderTimer);
    renderTimer = window.setTimeout(renderAll, RENDER_DEBOUNCE_MS);
  }

  /** 把回填后的源码写回中栏：格式一改 textarea 的值并把光标停在段末，格式二整格重建（框本就从源码拆出来）。 */
  function writeBackSourceText(item, index, field) {
    var area = state.format === "boxed" ? null
      : sourceBodyEl.querySelector('.ed-src-area[data-index="' + index + '"]');
    if (!area) {
      renderAll();
      return;
    }
    area.value = item.source;
    growTextarea(area);
    var range = fieldRanges(item.source)[field === "solution" ? "solution" : "stem"];
    if (range && document.activeElement === area) {
      // 光标停在改写段末尾：老师接着看结果，不必自己找位置
      area.setSelectionRange(range.end, range.end);
    }
  }

  /**
   * 辅助栏点了【采用】才有这条通知。只替换题干段/解析段的正文，
   * 目标题认不出来、段找不到、内容超长都如实拒绝——绝不用半截改写覆盖老师的源码。
   */
  function applyAiPatch(payload) {
    var raw = payload && payload.raw ? payload.raw : payload;
    var field = raw && (raw.field === "solution" || raw.field === "stem") ? raw.field : "";
    var value = String((raw && raw.value) || "");
    if (!field || !value.trim()) {
      toast("AI 回填缺字段或内容为空，源码没动", "error");
      return false;
    }
    var item = state.items[state.active];
    if (!item) {
      toast("画布当前没有题目可回填", "error");
      return false;
    }
    var wanted = keyFromPatchId(raw.id);
    if (wanted && wanted !== String(item.key).replace(/[^A-Za-z0-9_-]/g, "-")) {
      toast("AI 回填的目标不是当前题，源码没动", "error");
      return false;
    }
    var outcome = replaceField(item.source, field, value);
    if (!outcome.ok) {
      toast(outcome.message, "error");
      return false;
    }
    item.source = outcome.text;
    item.dirty = true;
    markDirty();
    writeBackSourceText(item, state.active, field);
    refreshRow(state.active);
    toast("已采用 AI 改写的" + fieldLabel(field) + "，还没保存", "ok");
    return true;
  }

  // ---------- 当前题上桥（画布 → 辅助栏：唯一的合法通道是 stage.selection） ----------
  /** 元数据默认值：从真题结构里摘出辅助栏表单要预填的那一小组字段。 */
  function defaultsOf(item) {
    var question = item.question || {};
    var source = question.source || {};
    var taxonomy = question.taxonomy || {};
    return {
      type: TYPE_VALUES.indexOf(question.type) >= 0 ? question.type : "",
      difficulty: DIFFICULTY_VALUES.indexOf(question.difficulty) >= 0 ? question.difficulty : "L1",
      grade: trunc(question.grade, 20),
      tags: (question.tags || []).slice(0, TAG_LIMIT).join(","),
      paper_title: trunc(source.paper_title, 120),
      question_no: trunc(source.question_no, 20),
      exam_type: trunc(source.exam_type, 64),
      year: source.year == null ? "" : String(source.year),
      textbook: trunc(taxonomy.textbook, 64),
      chapter: trunc(taxonomy.chapter, 64),
      section: trunc(taxonomy.section, 64)
    };
  }

  /**
   * 老师当前题里的光标位置 → AI 能改哪个字段。
   * 格式一按源码偏移判定（choices 与「答案：」行都判不出字段，档 1 只吃题干/解析）；
   * 格式二直接看框的语义字段，框头环境名本来就锁死，不必再算偏移。
   */
  function caretOfActive() {
    var item = state.items[state.active];
    if (!item) return null;
    var node = document.activeElement;
    if (!node || !node.getAttribute || !("selectionStart" in node)) return null;
    if (node.getAttribute("data-index") !== String(state.active)) return null;
    var boxField = node.getAttribute("data-field");
    var start = Number(node.selectionStart) || 0;
    var end = Number(node.selectionEnd) || 0;
    var picked = String(node.value || "").slice(Math.min(start, end), Math.max(start, end));
    var field = "";
    if (boxField === "source") field = fieldAtOffset(item.source, end || start);
    else if (boxField === "stem" || boxField === "solution") field = boxField;
    return {
      field: field,
      has_selection: end > start,
      text: trunc(picked, 160)
    };
  }

  function selectionPayload() {
    var item = state.items[state.active];
    if (!item) return null;
    var parsed = parsedOf(item);
    var question = item.question || {};
    return {
      index: state.active,
      total: state.items.length,
      key: item.key,
      question_id: item.savedId || question.id || "",
      saved_id: item.savedId || "",
      status: item.status,
      dirty: Boolean(item.dirty),
      format: state.format,
      source: trunc(item.source, FIELD_MAX),
      caret: caretOfActive(),
      errors: parsed.errors.slice(0, 8),
      ai_type: parsed.type,
      confidence: typeof item.dev.confidence === "number" ? item.dev.confidence : null,
      defaults: defaultsOf(item),
      images: (question.images || []).slice(0, 32),
      extensions: keepExtensions(question.extensions)
    };
  }

  /** 假数据提示只活在开发帧里，绝不该跟到真题库的 extensions 里。 */
  function keepExtensions(raw) {
    var out = {};
    Object.keys(raw && typeof raw === "object" ? raw : {}).forEach(function (key) {
      if (key === DEV_NS) return;
      out[key] = raw[key];
    });
    return out;
  }

  function publishSelection() {
    var payload = selectionPayload();
    if (!payload) return;
    publish("stage.selection", payload);
  }

  function publishSelectionSoon() {
    window.clearTimeout(selectionTimer);
    selectionTimer = window.setTimeout(publishSelection, SELECTION_MS);
  }

  function worklistValue() {
    return {
      active: state.active,
      items: state.items.map(function (item) {
        return {
          key: item.key,
          id: item.question && item.question.id ? item.question.id : "",
          saved_id: item.savedId || "",
          status: item.status,
          dirty: Boolean(item.dirty),
          source: trunc(item.source, FIELD_MAX),
          // 辅助栏可能在画布发布选区之前就已挂载：把默认值一并存进宿主代持的草稿，
          // 面板读草稿就能自己补出这张表单，不必等一条永远不会重放的通知。
          defaults: defaultsOf(item),
          confidence: typeof item.dev.confidence === "number" ? item.dev.confidence : null,
          errors: parsedOf(item).errors.slice(0, 8)
        };
      })
    };
  }

  function saveWorklist() {
    if (!state.items.length) return;
    hostCall("draft.save", { key: DRAFT_WORKLIST_KEY, value: worklistValue() })
      .catch(function () { /* 草稿存不下就算了，不打扰老师 */ });
  }

  function queueWorklistSave() {
    window.clearTimeout(worklistTimer);
    worklistTimer = window.setTimeout(saveWorklist, WORKLIST_DRAFT_MS);
  }

  /** 辅助栏挂载时补的是同一份宿主代持草稿；画布重开页签也靠它对回未保存的源码。 */
  function restoreWorklist() {
    return hostCall("draft.load", { key: DRAFT_WORKLIST_KEY }).then(function (result) {
      var value = result && result.value;
      if (!value || !Array.isArray(value.items)) return;
      var touched = false;
      value.items.forEach(function (saved) {
        if (!saved || typeof saved !== "object") return;
        for (var index = 0; index < state.items.length; index += 1) {
          var item = state.items[index];
          if (item.key !== saved.key) continue;
          if (typeof saved.source === "string" && saved.source && saved.source !== item.source) {
            item.source = saved.source;
            item.parsed = null;
            touched = true;
          }
          item.dirty = Boolean(saved.dirty);
          item.status = saved.status === "stored" ? "stored" : "pending";
          item.savedId = typeof saved.saved_id === "string" ? saved.saved_id : null;
          break;
        }
      });
      var wanted = Number(value.active);
      if (wanted >= 0 && wanted < state.items.length) state.active = wanted;
      if (touched) scheduleRender();
    }).catch(function () { /* 读不到草稿就从假数据重来 */ });
  }

  // ---------- 格式一 / 格式二（切换请求来自辅助栏，经宿主 ui.params 落地） ----------
  function setFormat(next) {
    var value = FORMATS[next] ? next : "latex";
    if (value === state.format) return;
    state.format = value;
    if (sourceHintEl) {
      sourceHintEl.textContent = value === "boxed"
        ? "格式二 · 框里只有内容，环境骨架改不动"
        : "格式一 · 整段源码直接编辑";
    }
    renderAll();
    publishSelection();
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

  // ---------- 批量滚动：滚到哪一题，当前题就跟到哪一题 ----------
  /** 只认正在编辑的框：焦点落在第几题的源码/框里，那一题就是当前题，滚动不许来抢。 */
  function editingRowIndex() {
    var node = document.activeElement;
    if (!node || !node.getAttribute) return -1;
    if (node.tagName !== "TEXTAREA" && node.tagName !== "INPUT") return -1;
    var raw = node.getAttribute("data-index");
    if (raw == null) return -1;
    var index = Number(raw);
    return isNaN(index) || index < 0 ? -1 : index;
  }

  /** 当前题 = 视口里露出最多的那一行：只按「顶边越过滚动线」会在滚到底时漏掉最后一题。 */
  function activeFromScroll(top) {
    var body = renderBodyEl || sourceBodyEl || imageBodyEl;
    if (!body) return state.active;
    var bottom = top + Math.max(body.clientHeight || 0, 1);
    var best = state.active;
    var bestArea = -1;
    for (var position = 0; position < body.children.length; position += 1) {
      var cell = body.children[position];
      var visible = Math.min(cell.offsetTop + cell.offsetHeight, bottom) - Math.max(cell.offsetTop, top);
      if (visible > bestArea) {
        bestArea = visible;
        best = position;
      }
    }
    return clampValue(best, 0, Math.max(state.items.length - 1, 0));
  }

  /** 三栏同时高亮当前题：状态不只靠颜色（AGENTS §6），顶部进度条与左栏按钮文案一起说明。 */
  function markActiveRow() {
    [imageBodyEl, sourceBodyEl, renderBodyEl].forEach(function (body) {
      if (!body) return;
      Array.prototype.forEach.call(body.children, function (cell, index) {
        if (!cell.classList) return;
        cell.classList.toggle("is-active", index === state.active);
      });
    });
    Array.prototype.forEach.call(imageBodyEl ? imageBodyEl.querySelectorAll(".ed-img-jump") : [],
      function (node) {
        var index = Number(node.getAttribute("data-index"));
        var on = index === state.active;
        node.setAttribute("aria-current", on ? "true" : "false");
      });
  }

  function jumpTo(index) {
    var target = clampValue(Number(index) || 0, 0, Math.max(state.items.length - 1, 0));
    state.active = target;
    [imageBodyEl, sourceBodyEl, renderBodyEl].forEach(function (body) {
      var cell = body && body.children[target];
      if (body && cell) body.scrollTop = Math.max(cell.offsetTop - 12, 0);
    });
    syncActiveBits();
    publishSelectionSoon();
    queueWorklistSave();
  }

  function followActive(from) {
    if (!state.items.length || editingRowIndex() >= 0) return;
    var next = activeFromScroll(from ? from.scrollTop : 0);
    if (next === state.active) return;
    state.active = next;
    syncActiveBits();
    publishSelectionSoon();
    queueWorklistSave();
  }

  function syncScroll(from) {
    if (scrollRestore) return;
    if (scrollLock) return;
    scrollLock = true;
    [imageBodyEl, sourceBodyEl, renderBodyEl].forEach(function (node) {
      if (node && node !== from) node.scrollTop = from.scrollTop;
    });
    followActive(from);
    window.requestAnimationFrame(function () { scrollLock = false; });
  }

  // ---------- 落库（辅助栏发起；命令面走同一份实现，绝不让两处各写一套） ----------
  function splitTags(text) {
    var seen = [];
    String(text == null ? "" : text).split(/[，,、;；\n]/).forEach(function (raw) {
      var tag = raw.trim().slice(0, 32);
      if (tag && seen.indexOf(tag) < 0) seen.push(tag);
    });
    return seen.slice(0, TAG_LIMIT);
  }

  function lettersFrom(text, type) {
    var letters = String(text == null ? "" : text).toUpperCase().replace(/[^A-H]/g, "");
    var unique = [];
    for (var index = 0; index < letters.length; index += 1) {
      if (unique.indexOf(letters.charAt(index)) < 0) unique.push(letters.charAt(index));
    }
    return type === "single_choice" ? unique.slice(0, 1) : unique.slice(0, 8);
  }

  /** 元数据只认宿主代持的草稿；两帧谁先写都无所谓，读的时候都是同一份。 */
  function metaFor(item, override) {
    var stored = panel.meta[item.key] || {};
    var meta = {};
    Object.keys(stored).forEach(function (key) { meta[key] = stored[key]; });
    if (override) Object.keys(override).forEach(function (key) { meta[key] = override[key]; });
    return meta;
  }

  function questionFromParsed(item, parsed, meta) {
    var question = item.question || {};
    var type = TYPE_VALUES.indexOf(meta.type) >= 0 ? meta.type : parsed.type;
    var doc = {
      schema_version: "2.0",
      type: type,
      stem: parsed.stem
    };
    var isChoice = type === "single_choice" || type === "multiple_choice";
    if (isChoice) {
      doc.options = parsed.choices.map(function (content, position) {
        return { key: OPTION_KEYS[position] || "A", content: String(content == null ? "" : content) };
      });
    }
    var letters = lettersFrom(parsed.answer, type);
    if (isChoice) {
      doc.answer = { kind: "choice", choice_keys: letters, final: letters.join("") };
    } else {
      var value = String(parsed.answer == null ? "" : parsed.answer);
      doc.answer = { kind: type === "fill_blank" ? "expression" : "text", content: value, final: value };
    }
    if (parsed.analysis) doc.solution = parsed.analysis;
    doc.difficulty = DIFFICULTY_VALUES.indexOf(meta.difficulty) >= 0 ? meta.difficulty : "L1";
    if (meta.grade) doc.grade = String(meta.grade).trim().slice(0, 20);
    var tags = splitTags(meta.tags);
    if (tags.length) doc.tags = tags;
    var taxonomy = {};
    ["textbook", "chapter", "section"].forEach(function (field) {
      var text = String(meta[field] == null ? "" : meta[field]).trim();
      if (text) taxonomy[field] = text.slice(0, 64);
    });
    var topicIds = (meta.topic_ids || []).filter(function (id) { return TOPIC_ID_RE.test(String(id)); }).slice(0, TOPIC_LIMIT);
    if (topicIds.length) taxonomy.topic_ids = topicIds;
    if (Object.keys(taxonomy).length) doc.taxonomy = taxonomy;
    var source = {};
    if (meta.paper_title) source.paper_title = String(meta.paper_title).trim().slice(0, 120);
    if (meta.question_no) source.question_no = String(meta.question_no).trim().slice(0, 20);
    if (meta.exam_type) source.exam_type = String(meta.exam_type).trim().slice(0, 64);
    var year = Number(meta.year);
    if (year >= 1900 && year <= 2100) source.year = Math.floor(year);
    if (question.source && question.source.region) source.region = String(question.source.region).slice(0, 64);
    if (question.source && question.source.school) source.school = String(question.source.school).slice(0, 64);
    if (Object.keys(source).length) doc.source = source;
    if (Array.isArray(question.images) && question.images.length) doc.images = question.images.slice(0, 32);
    var extras = keepExtensions(question.extensions);
    // 底座新增题目的写路径只从 extensions 认年级（core-bank.grade → org.jiuzhang.editor → legacy），
    // 契约根字段 grade 在 create 通道里没人读——沿用 v1 录题插件的键双写一次，否则年级落库即丢。
    if (doc.grade) {
      var editorExt = extras["org.jiuzhang.editor"] || {};
      editorExt.grade = doc.grade;
      extras["org.jiuzhang.editor"] = editorExt;
    }
    if (Object.keys(extras).length) doc.extensions = extras;
    return doc;
  }

  /** 保存前的最小校验：先把源码认全，再逐条对照契约的硬边界，问题一律用老师看得懂的话说。 */
  function validateForSave(doc, parsed, meta) {
    var problems = [];
    parsed.errors.forEach(function (text) { problems.push("源码：" + text); });
    if (!doc.stem) problems.push("题干不能为空");
    if (doc.stem.length > STEM_MAX) problems.push("题干过长（上限 " + STEM_MAX + " 字）");
    if (TYPE_VALUES.indexOf(doc.type) < 0) {
      problems.push("题库只收单选、多选、填空、解答四类题型，当前判为「" + (doc.type || "未知") + "」");
    }
    var isChoice = doc.type === "single_choice" || doc.type === "multiple_choice";
    if (isChoice) {
      if (!doc.options || doc.options.length < 2) problems.push("选择题至少要两个选项");
      var keys = (doc.options || []).map(function (option) { return option.key; });
      var letters = (doc.answer && doc.answer.choice_keys) || [];
      if (!letters.length) problems.push("请填写答案字母（例：B 或 AC）");
      letters.forEach(function (letter) {
        if (keys.indexOf(letter) < 0) problems.push("答案 " + letter + " 没有对应选项");
      });
      if (doc.type === "single_choice" && letters.length !== 1) problems.push("单选题答案只能有一个字母");
      if (doc.type === "multiple_choice" && letters.length < 2) problems.push("多选题答案至少两个字母");
    } else if (!(doc.answer && doc.answer.content)) {
      problems.push("请填写答案");
    }
    var rawYear = String(meta.year == null ? "" : meta.year).trim();
    if (rawYear && !doc.source) problems.push("年份要写 1900–2100 的四位数");
    if (doc.taxonomy && doc.taxonomy.topic_ids && doc.taxonomy.topic_ids.length > TOPIC_LIMIT) {
      problems.push("考向最多挂 " + TOPIC_LIMIT + " 个");
    }
    return problems;
  }

  function saveItem(item, meta, mode) {
    var parsed = parseExamSource(item.source);
    var doc = questionFromParsed(item, parsed, meta || {});
    var problems = validateForSave(doc, parsed, meta || {});
    if (problems.length) {
      return Promise.reject({ code: "LOCAL_INVALID", message: problems.join("；"), retryable: false });
    }
    var updating = mode !== "variant" && item.savedId && item.status === "stored";
    var payload = { question: doc };
    if (updating) payload.id = item.savedId;
    // 不带 sources：契约的「没给就保持原样」保住一题多卷的其余原卷，
    // 阶段 2 的辅助栏只有一张原卷输入，不能拿它去覆盖老师挂好的整组来源。
    var method = updating ? "bank.update" : "bank.create";
    return hostCall(method, payload).then(function (result) {
      var id = (result && result.id) || (updating ? item.savedId : "");
      if (mode !== "variant") {
        item.savedId = id;
        item.status = "stored";
        item.dirty = false;
        if (state.slot === "stage.center") {
          markDirty();
          queueWorklistSave();
        }
        pushReceipt({ key: item.key, id: id, action: updating ? "update" : "create", mode: mode });
        showSaved(id, updating);
      } else {
        pushReceipt({ key: item.key, id: id, action: "create", mode: "variant" });
        dock("录题工作台另存了派生变式：" + id + "（原题未动）");
        // 变式号必须留在状态位上：话术区随后会被画布回投的选区盖掉，只靠文本没法复查
        if (panelMetricsEl) panelMetricsEl.setAttribute("data-variant-id", id || "");
        panelSay("已另存为新题 " + id + "，原题仍是 " + (item.savedId || "未入库的那一题") + "。", "ok", "saved");
      }
      return { question_id: id, created: !updating, parent_id: item.savedId || "" };
    });
  }

  /** 入库后的回显：画布只报题号，辅助栏把状态徽章、按钮与详情话术一起改到位。 */
  function showSaved(id, updating) {
    if (state.slot === "stage.center") {
      if (savedEl) {
        savedEl.hidden = false;
        savedEl.textContent = "已入库 " + id;
        savedEl.setAttribute("data-id", id || "");
      }
      if (metricsEl) metricsEl.setAttribute("data-saved-id", id || "");
      dock("录题工作台把" + (updating ? "修改后的" : "新的") + "题目写进了题库：" + id);
      return;
    }
    if (panelStatusEl) {
      panelStatusEl.textContent = "● 已入库";
      panelStatusEl.setAttribute("data-status", "stored");
    }
    if (panelMetricsEl) {
      panelMetricsEl.setAttribute("data-saved-id", id || "");
      panelMetricsEl.setAttribute("data-save-state", updating ? "updated" : "created");
    }
    panelSay((updating ? "已更新题目 " : "已入库新题 ") + id + "。", "ok", updating ? "updated" : "created");
  }

  function loadMetaDraft() {
    return hostCall("draft.load", { key: DRAFT_META_KEY }).then(function (result) {
      var value = result && result.value;
      if (value && typeof value === "object") panel.meta = value;
      return panel.meta;
    }).catch(function () { return {}; });
  }

  function saveMetaDraft() {
    hostCall("draft.save", { key: DRAFT_META_KEY, value: panel.meta })
      .catch(function () { /* 存不下就算了 */ });
  }

  function queueMetaSave() {
    window.clearTimeout(metaTimer);
    metaTimer = window.setTimeout(saveMetaDraft, 250);
  }

  /** 画布侧的命令面保存：元数据从宿主代持的草稿里读，与辅助栏用的是同一份。 */
  function saveViaCommand(mode) {
    var item = state.items[state.active];
    if (!item) return Promise.reject(new Error("画布里没有当前题目"));
    return loadMetaDraft().then(function () {
      return saveItem(item, metaFor(item, {}), mode);
    });
  }

  // ---------- 批量条：脏题计数、待入库池界面与【保存全部】 ----------
  function dirtyList() {
    var out = [];
    state.items.forEach(function (item, index) {
      if (item.dirty) out.push({ item: item, index: index });
    });
    return out;
  }

  function poolCounts() {
    var fresh = 0, stored = 0, dirty = 0, errored = 0;
    state.items.forEach(function (item) {
      if (item.status === "stored") stored += 1;
      else fresh += 1;
      if (item.dirty) dirty += 1;
      if (Number(item.errorCount || 0) > 0) errored += 1;
    });
    return { fresh: fresh, stored: stored, dirty: dirty, errored: errored };
  }

  function batchNote(text, phase) {
    if (!batchNoteEl) return;
    batchNoteEl.textContent = text;
    batchNoteEl.setAttribute("data-batch", phase || "idle");
  }

  /** 待入库池现在只是台账：池的存储层随下一军令接入，所以按钮出厂锁死、话术写明白。 */
  function renderPool() {
    var counts = poolCounts();
    if (poolEl) {
      poolEl.textContent = "待入库 " + counts.fresh + " · 已入库 " + counts.stored
        + " · 脏 " + counts.dirty + " · 未认全 " + counts.errored;
      poolEl.setAttribute("data-new", String(counts.fresh));
      poolEl.setAttribute("data-stored", String(counts.stored));
      poolEl.setAttribute("data-dirty", String(counts.dirty));
      poolEl.setAttribute("data-errored", String(counts.errored));
    }
    if (saveAllEl) {
      var blocked = state.batchSaving || counts.dirty === 0;
      saveAllEl.disabled = blocked;
      if (state.batchSaving) saveAllEl.setAttribute("aria-busy", "true");
      else saveAllEl.removeAttribute("aria-busy");
      saveAllEl.setAttribute("aria-disabled", blocked ? "true" : "false");
      saveAllEl.title = counts.dirty === 0
        ? "没有脏题：底部只提交改动过的题"
        : "逐题串行提交 " + counts.dirty + " 道脏题（已入库走更新，未入库走新建）";
    }
    if (poolStashEl) {
      poolStashEl.disabled = true;
      poolStashEl.setAttribute("aria-disabled", "true");
    }
  }

  /**
   * 【保存全部】只提交脏题：没改过的一题也不写库。
   * 逐题串行而不是并发——宿主对写库有频率闸门，一次全发只会换来一排 RATE_LIMITED 的假失败。
   */
  function saveAllDirty() {
    if (state.batchSaving) return Promise.resolve(null);
    var targets = dirtyList();
    if (!targets.length) {
      batchNote("没有脏题可提交——底部只提交改动过的题，未改动的不动。", "empty");
      return Promise.resolve(null);
    }
    state.batchSaving = true;
    renderPool();
    batchNote("正在提交 " + targets.length + " 道脏题…", "running");
    return loadMetaDraft().then(function () {
      return targets.reduce(function (chain, target) {
        return chain.then(function (acc) {
          return saveItem(target.item, metaFor(target.item, {}), "save").then(function (result) {
            acc.saved.push(result.question_id || "");
          }, function (error) {
            acc.failed.push("第 " + (target.index + 1) + " 题：" + explainHostError(error));
          }).then(function () {
            // 每一棒都得把台账交回下一棒，否则第二题开始 acc 就是 undefined，整串批量会假死。
            return acc;
          });
        });
      }, Promise.resolve({ saved: [], failed: [] }));
    }).then(function (acc) {
      state.batchSaving = false;
      var untouched = state.items.length - acc.saved.length - acc.failed.length;
      var text = "提交 " + (acc.saved.length + acc.failed.length) + " 道脏题：入库 "
        + acc.saved.length + "、失败 " + acc.failed.length + "；未改动的 " + untouched
        + " 道一题也没写。";
      if (acc.failed.length) text += " 失败明细：" + acc.failed.join("；");
      batchNote(text, acc.failed.length ? "partial" : "done");
      dock("录题工作台批量提交：" + acc.saved.length + " 题入库、" + acc.failed.length + " 题失败。");
      syncActiveBits();
      publishSelectionSoon();
      queueWorklistSave();
      return acc;
    }, function (error) {
      state.batchSaving = false;
      batchNote("批量提交没走通：" + ((error && error.message) || "未知失败") + "，已提交的部分不追回。",
        "failed");
      renderPool();
      return null;
    });
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
      if (Object.keys(context).length) {
        return commandReject(source, message, "BAD_PARAMS", "保存命令不接受参数");
      }
      saveViaCommand("save").then(function (result) {
        respond(source, message.id, true, result);
      }, function (error) {
        commandReject(source, message, error && error.code === "LOCAL_INVALID" ? "BAD_REQUEST" : "COMMAND_FAILED",
          (error && error.message) || "保存失败");
      });
      return;
    }
    if (commandId === "org.jiuzhang.action.process.create_variant") {
      if (Object.keys(context).length) {
        return commandReject(source, message, "BAD_PARAMS", "派生变式命令不接受参数");
      }
      saveViaCommand("variant").then(function (result) {
        respond(source, message.id, true, result);
      }, function (error) {
        commandReject(source, message, error && error.code === "LOCAL_INVALID" ? "BAD_REQUEST" : "COMMAND_FAILED",
          (error && error.message) || "另存失败");
      });
      return;
    }
    commandReject(source, message, "UNKNOWN_COMMAND", "未声明的方法：" + commandId);
  }

  // ---------- 两帧对账：格式参数（面板→画布）与入库回执（面板→画布） ----------
  function onUiParams(payload) {
    var values = payload && payload.values;
    if (!payload || payload.pluginId !== PLUGIN_ID || !values) return;
    if (payload.revisions && typeof payload.revisions === "object") {
      panel.uiRevisions = JSON.parse(JSON.stringify(payload.revisions));
    }
    if (state.slot === "stage.center") {
      if (values.format && values.format !== state.format) setFormat(values.format);
      return;
    }
    if (values.format) setFormatButtons(values.format);
  }

  /**
   * 辅助栏落库后留一张回执，画布收到 system.question_updated 时按回执认领：
   * 「新建」和「派生变式」在事件里长得一模一样，只有回执能分清是哪一题变成了哪道题。
   */
  function pushReceipt(receipt) {
    var list = Array.isArray(panel.receipts) ? panel.receipts : [];
    list.push({
      key: receipt.key, id: receipt.id, action: receipt.action,
      mode: receipt.mode, at: nowIso()
    });
    panel.receipts = list.slice(-20);
    hostCall("draft.save", { key: DRAFT_RECEIPT_KEY, value: { items: panel.receipts } })
      .catch(function () { /* 回执丢了，画布顶多少刷一次状态 */ });
  }

  function consumeReceipts(payload, attempt) {
    var id = payload && payload.id ? String(payload.id) : "";
    if (!id) return;
    var tries = Number(attempt) || 0;
    hostCall("draft.load", { key: DRAFT_RECEIPT_KEY }).then(function (result) {
      var value = result && result.value;
      var list = value && Array.isArray(value.items) ? value.items : [];
      var matched = null;
      var rest = [];
      list.forEach(function (item) {
        if (!matched && item && String(item.id) === id) matched = item;
        else rest.push(item);
      });
      if (!matched) {
        // 宿主是先广播事件、后把应答送回辅助栏，回执落草稿比事件晚一跳；读不到就重试
        if (tries < RECEIPT_RETRY_MAX) {
          setTimeout(function () { consumeReceipts(payload, tries + 1); }, RECEIPT_RETRY_MS);
        }
        return;
      }
      panel.receipts = rest;
      hostCall("draft.save", { key: DRAFT_RECEIPT_KEY, value: { items: rest } }).catch(function () {});
      var target = null;
      state.items.forEach(function (item) {
        if (item.key === matched.key) target = item;
      });
      if (!target) target = state.items[state.active];
      if (!target || matched.mode === "variant") {
        dock("派生变式已入库：" + id + "（当前题没动）");
        return;
      }
      target.savedId = id;
      target.status = "stored";
      target.dirty = false;
      if (target.question) target.question.id = id;
      renderAll();
      saveWorklist();
      publishSelection();
      // 画布与辅助栏是两个 iframe，面板那句「已入库」画布看不见；
      // 认领回执时由画布自己把题号回显到顶栏，老师不用来回翻帧。
      showSaved(id, matched.action === "update");
    }).catch(function () { /* 读不到回执就不动，等老师再点一次保存 */ });
  }

  // ---------- 辅助栏实例（sidebar.right）：元数据 + 审核动作 + 格式切换 ----------
  function fillSelect(node, values, labels) {
    if (!node) return;
    node.textContent = "";
    values.forEach(function (value) {
      var option = document.createElement("option");
      option.value = value;
      option.textContent = labels[value] || value;
      node.appendChild(option);
    });
  }

  function panelItem() {
    var sel = panel.selection;
    if (!sel) return null;
    return {
      key: String(sel.key || "idx:" + Number(sel.index || 0)),
      savedId: sel.saved_id || "",
      status: sel.status === "stored" ? "stored" : "pending",
      source: String(sel.source || panel.source || ""),
      question: {
        id: sel.question_id || "",
        images: Array.isArray(sel.images) ? sel.images : [],
        extensions: sel.extensions && typeof sel.extensions === "object" ? sel.extensions : {}
      }
    };
  }

  function defaultEntry(sel) {
    var d = (sel && sel.defaults) || {};
    return {
      type: d.type || "",
      difficulty: d.difficulty || "L1",
      grade: d.grade || "",
      textbook: d.textbook || "",
      chapter: d.chapter || "",
      section: d.section || "",
      paper_title: d.paper_title || "",
      question_no: d.question_no || "",
      exam_type: d.exam_type || "",
      year: d.year || "",
      tags: d.tags || "",
      topic_ids: [],
      topic_names: {}
    };
  }

  function entryFor(sel) {
    var key = String(sel.key || "idx:" + Number(sel.index || 0));
    if (!panel.meta[key]) panel.meta[key] = defaultEntry(sel);
    return panel.meta[key];
  }

  function readForm() {
    var entry = {};
    Object.keys(panel.currentEntry || {}).forEach(function (key) { entry[key] = panel.currentEntry[key]; });
    if (panelTypeEl) entry.type = panelTypeEl.value;
    if (panelDifficultyEl) entry.difficulty = panelDifficultyEl.value;
    if (panelGradeEl) entry.grade = panelGradeEl.value;
    if (panelPaperEl) entry.paper_title = panelPaperEl.value;
    if (panelQuestionNoEl) entry.question_no = panelQuestionNoEl.value;
    if (panelExamTypeEl) entry.exam_type = panelExamTypeEl.value;
    if (panelYearEl) entry.year = panelYearEl.value;
    if (panelTagsEl) entry.tags = panelTagsEl.value;
    return entry;
  }

  function bindFormChanges() {
    [panelTypeEl, panelDifficultyEl, panelGradeEl, panelPaperEl, panelQuestionNoEl,
      panelExamTypeEl, panelYearEl, panelTagsEl].forEach(function (node) {
      if (!node) return;
      node.addEventListener("input", onFormChange);
      node.addEventListener("change", onFormChange);
    });
  }

  /** 表单是元数据的编辑面：每次改动都立刻并回草稿，别让保存读到半旧的版本。 */
  function onFormChange() {
    if (!panel.selection) return;
    panel.currentEntry = readForm();
    panel.meta[panel.selection.key] = panel.currentEntry;
    panel.selection.dirty = true;
    queueMetaSave();
    renderTypeNote();
    renderPanelMetrics();
  }

  function renderTypeNote() {
    if (!panelTypeNoteEl || !panel.selection) return;
    var aiType = panel.selection.ai_type;
    var chosen = panelTypeEl ? panelTypeEl.value : "";
    if (!aiType) {
      panelTypeNoteEl.textContent = "源码还没认全，题型先按人工选择。";
      panelTypeNoteEl.setAttribute("data-from", "manual");
      return;
    }
    if (chosen && chosen !== aiType) {
      panelTypeNoteEl.textContent = "源码判为「" + (TYPE_LABELS[aiType] || aiType) + "」，你改成了「"
        + (TYPE_LABELS[chosen] || chosen) + "」——保存以你的选择为准。";
      panelTypeNoteEl.setAttribute("data-from", "manual");
      return;
    }
    panelTypeNoteEl.textContent = "题型由源码自动判断（" + (TYPE_LABELS[aiType] || aiType) + "），可人工改。";
    panelTypeNoteEl.setAttribute("data-from", "ai");
  }

  function applySelection(sel) {
    if (!sel || typeof sel !== "object") return;
    var previous = panel.selection;
    if (previous && previous.key && previous.key !== sel.key) {
      // 换题前把老师正在填的这一半按旧题的键存回草稿，别让表单跟着题号一起漂
      panel.meta[previous.key] = Object.assign(panel.meta[previous.key] || defaultEntry(previous), readForm());
      queueMetaSave();
      // 预览中的改写属于上一道题：换题即失效，不许糊到新题上
      if (panel.ai.key && panel.ai.key !== sel.key && panel.ai.state !== "sending" && panel.ai.state !== "cleaning") {
        aiClear("换题了：上一题的改写已作废。");
      }
    }
    panel.selection = sel;
    panel.source = String(sel.source || "");
    var entry = entryFor(sel);
    if (panel.currentEntry !== entry) {
      panel.currentEntry = entry;
    }
    var merged = entry;
    if (panelProgressEl) {
      panelProgressEl.textContent = "第 " + (Number(sel.index || 0) + 1) + " / " + (sel.total || 1) + " 题";
      panelProgressEl.setAttribute("data-active", String(Number(sel.index || 0) + 1));
      panelProgressEl.setAttribute("data-total", String(sel.total || 1));
    }
    if (panelStatusEl) {
      var stored = sel.status === "stored";
      panelStatusEl.textContent = stored ? "● 已入库" : "● 待审核";
      panelStatusEl.setAttribute("data-status", stored ? "stored" : "pending");
      panelStatusEl.setAttribute("data-dirty", sel.dirty ? "true" : "false");
    }
    if (panelConfidenceEl) {
      var confidence = typeof sel.confidence === "number" ? Math.round(sel.confidence * 100) : null;
      panelConfidenceEl.textContent = confidence == null ? "置信度 —（假数据占位）" : "置信度 " + confidence + "%（假数据占位）";
      panelConfidenceEl.setAttribute("data-confidence", confidence == null ? "" : String(confidence));
    }
    if (panelTypeEl) panelTypeEl.value = merged.type || sel.ai_type || "single_choice";
    if (panelDifficultyEl) panelDifficultyEl.value = merged.difficulty || "L1";
    if (panelGradeEl) panelGradeEl.value = merged.grade || "";
    if (panelPaperEl) panelPaperEl.value = merged.paper_title || "";
    if (panelQuestionNoEl) panelQuestionNoEl.value = merged.question_no || "";
    if (panelExamTypeEl) panelExamTypeEl.value = merged.exam_type || "";
    if (panelYearEl) panelYearEl.value = merged.year || "";
    if (panelTagsEl) panelTagsEl.value = merged.tags || "";
    setFormatButtons(sel.format || panel.format);
    renderTypeNote();
    renderMounted();
    renderPanelMetrics();
    renderAi();
    if (panelSelectionError()) {
      panelSay(panelSelectionError(), "error", "invalid");
    } else if (panel.ai.state === "ready" && panel.ai.key === sel.key) {
      // 刚把改写发给画布，那句「保存才入库」不能被选区回显盖掉——否则老师会以为已经入库了
    } else if (panelSaveEl && panelSaveEl.getAttribute("aria-busy") !== "true") {
      panelSay("当前第 " + (Number(sel.index || 0) + 1) + " 题" + (sel.dirty ? "有未保存改动" : "未改动") + "。",
        "info", sel.dirty ? "dirty" : "idle");
    }
  }

  function panelSelectionError() {
    var sel = panel.selection;
    if (!sel || !sel.errors || !sel.errors.length) return "";
    return "源码还没认全：" + sel.errors.slice(0, 4).join("；");
  }

  function renderPanelMetrics() {
    if (!panelMetricsEl || !panel.selection) return;
    var sel = panel.selection;
    panelMetricsEl.setAttribute("data-question-id", sel.question_id || "");
    panelMetricsEl.setAttribute("data-saved-id", sel.saved_id || "");
    panelMetricsEl.setAttribute("data-type", panelTypeEl ? panelTypeEl.value : "");
    panelMetricsEl.setAttribute("data-difficulty", panelDifficultyEl ? panelDifficultyEl.value : "");
    panelMetricsEl.setAttribute("data-format", panel.format);
    panelMetricsEl.setAttribute("data-dirty", sel.dirty ? "true" : "false");
    var entry = panel.currentEntry || {};
    panelMetricsEl.setAttribute("data-topics", String((entry.topic_ids || []).length));
    panelMetricsEl.textContent = "键 " + (sel.key || "") + " · 已挂考向 " + (entry.topic_ids || []).length
      + " · 标签 " + splitTags(entry.tags).length;
  }

  function setFormatButtons(format) {
    panel.format = FORMATS[format] ? format : "latex";
    [panelFormatLatexEl, panelFormatBoxedEl].forEach(function (node) {
      if (!node) return;
      var on = node.getAttribute("data-format") === panel.format;
      node.classList.toggle("is-on", on);
      node.setAttribute("aria-pressed", on ? "true" : "false");
    });
    if (panelMetricsEl) panelMetricsEl.setAttribute("data-format", panel.format);
  }

  /**
   * 格式切换走 ui.params.set：宿主只认清单里声明过的 select 键，
   * 并且「人在本轮手改过」的字段一律跳过——AI/面板永远赢不过人的手。
   */
  function switchFormat(next) {
    if (!FORMATS[next] || next === panel.format) return;
    var snapshot = panel.uiRevisions ? JSON.parse(JSON.stringify(panel.uiRevisions)) : {};
    hostCall("ui.params.set", {
      params: { format: next },
      snapshot: snapshot,
      plugin_id: PLUGIN_ID
    }).then(function (outcome) {
      var skipped = outcome && Array.isArray(outcome.skipped) ? outcome.skipped : [];
      if (skipped.length) {
        panelSay("格式切换被跳过：" + skipped.map(function (item) {
          return (item.label || "参数") + "（" + item.reason + "）";
        }).join("；") + "。", "warn", "skipped");
        return;
      }
      setFormatButtons(next);
    }).catch(function (error) {
      panelSay("格式切换没送到画布：" + explainHostError(error), "error", "failed");
    });
  }

  function explainHostError(error) {
    var code = String((error && error.code) || "");
    var text = (error && error.message) || "未知失败";
    if (code === "FORBIDDEN") return "清单没申请这道权限（FORBIDDEN），本次未写入题库";
    if (code === "PERMISSION_DENIED") return "宿主不认这份清单的权限（PERMISSION_DENIED）：" + text;
    if (code === "RATE_LIMITED") return "请求太密（每 10 秒有上限），稍等再点一次";
    if (code === "NOT_READY") return "宿主还没就绪（NOT_READY）：" + text;
    if (code === "HOST_409") return "题库里已经有同一道题（409 撞号）：请改点【另存为新题】，或先处理旧题";
    if (code === "HOST_422") return "题目不符合题库 Schema（422）：" + text;
    if (code === "HOST_404") return "要改的那道题在题库里找不到了（404）";
    if (code.indexOf("HOST_") === 0) return "底座写库失败（" + code + "）：" + text;
    if (code === "LOCAL_INVALID") return text;
    return text;
  }

  function onPanelSave(mode) {
    var item = panelItem();
    if (!item) {
      panelSay("辅助栏还没收到当前题的源码，等画布发一次选区。", "warn", "idle");
      return;
    }
    if (panel.saving) return;
    var entry = readForm();
    panel.currentEntry = entry;
    panel.meta[item.key] = entry;
    panelSay("正在写入题库…", "info", "saving");
    if (panelSaveEl) {
      panelSaveEl.disabled = true;
      panelSaveEl.setAttribute("aria-busy", "true");
    }
    panel.saving = true;
    saveItem(item, entry, mode).then(function (result) {
      panel.selection.status = mode === "variant" ? panel.selection.status : "stored";
      panel.selection.saved_id = mode === "variant" ? panel.selection.saved_id : result.question_id;
      panel.selection.dirty = mode === "variant" ? panel.selection.dirty : false;
      queueMetaSave();
      renderPanelMetrics();
      renderTypeNote();
      if (mode === "variant") {
        panelSay("已另存为新题 " + result.question_id + "，原题没动。", "ok", "created");
      }
    }, function (error) {
      panelSay(explainHostError(error), "error", error && error.code === "LOCAL_INVALID" ? "invalid" : "failed");
      dock("录题辅助栏保存失败：" + ((error && error.message) || "未知原因"));
    }).then(function () {
      panel.saving = false;
      if (panelSaveEl) {
        panelSaveEl.disabled = false;
        panelSaveEl.removeAttribute("aria-busy");
      }
    });
  }

  // ---------- 辅助栏 AI 帮改（档 1）：预览归面板，替换归老师那一下点击 ----------
  function setEpEnabled(node, enabled) {
    if (!node) return;
    if (enabled) {
      node.disabled = false;
      node.removeAttribute("aria-disabled");
    } else {
      node.disabled = true;
      node.setAttribute("aria-disabled", "true");
    }
  }

  function aiClear(note) {
    panel.ai = { state: "idle", field: "", key: "", value: "", note: note || "", mock: false, busy: false };
    renderAi();
  }

  /**
   * 面板 AI 区唯一的出口：可用性与话术全部从 panel.ai + 当前选区算出来。
   * 预览正文只走 textContent——模型回什么都不许被当成 DOM 结构解析（AGENTS §5）。
   */
  function renderAi() {
    var caret = (panel.selection && panel.selection.caret) || null;
    var field = caret && caret.field ? caret.field : "";
    if (panelAiFieldEl) {
      var hint;
      if (!panel.selection) hint = "辅助栏还没收到当前题的源码。";
      else if (!field) hint = "把光标放进题干段或解析段，AI 才知道要改哪一段——选项与「答案：」行由格式宪法锁死，改不到。";
      else hint = "改写字段：" + fieldLabel(field)
        + (caret.has_selection ? "（已选中 " + String(caret.text || "").length + " 字，改写整段）" : "（改写整段）");
      panelAiFieldEl.textContent = hint;
      panelAiFieldEl.setAttribute("data-ai-field", field);
    }
    if (panelAiStateEl) {
      panelAiStateEl.textContent = AI_STATE_LABELS[panel.ai.state] || panel.ai.state;
      panelAiStateEl.setAttribute("data-ai-state", panel.ai.state);
    }
    if (panelAiNoteEl) {
      panelAiNoteEl.textContent = panel.ai.note;
      panelAiNoteEl.setAttribute("data-ai-mock", panel.ai.mock ? "true" : "");
    }
    if (panelAiPreviewEl) {
      panelAiPreviewEl.textContent = panel.ai.value
        || "改写结果会出现在这里，点【采用】才会替换画布源码。";
      panelAiPreviewEl.setAttribute("data-ai-field", panel.ai.field);
      panelAiPreviewEl.setAttribute("data-ai-value", panel.ai.value ? "ready" : "empty");
    }
    var ask = panelAiAskEl ? String(panelAiAskEl.value || "").trim() : "";
    var idle = !panel.ai.busy;
    setEpEnabled(panelAiSendEl, Boolean(field && ask) && panel.ai.state !== "cleaning" && idle);
    setEpEnabled(panelAiCleanEl, Boolean(panel.selection) && panel.ai.state !== "sending" && idle);
    // 【采用】只在「待老师裁决」时亮：模型一回答完就自动覆盖老师源码，是档 1 的红线
    setEpEnabled(panelAiApplyEl, panel.ai.state === "ready" && Boolean(panel.ai.field && panel.ai.value) && idle);
    setEpEnabled(panelAiDiscardEl, panel.ai.state !== "idle" && panel.ai.state !== "sending" && idle);
    [panelAiSendEl, panelAiCleanEl, panelAiApplyEl].forEach(function (node) {
      if (!node) return;
      if (panel.ai.busy) node.setAttribute("aria-busy", "true");
      else node.removeAttribute("aria-busy");
    });
  }

  /**
   * 交给模型的上下文只取契约里看得见的正文与难度，绝不带 extensions、题号以外的身份、更不带令牌——
   * 底座 build_refine_user_message 也只做同样的取舍，两头都别把私有数据喂出去。
   */
  function refineContext(source, field, original) {
    var parsed = parseExamSource(String(source || ""));
    var entry = panel.currentEntry || {};
    var question = {
      type: entry.type || parsed.type || "",
      difficulty: entry.difficulty || "L1",
      stem: parsed.stem || "",
      answer: parsed.answer || "",
      solution: parsed.analysis || "",
      options: parsed.choices.map(function (content, position) {
        return { key: OPTION_KEYS[position] || "A", content: String(content == null ? "" : content) };
      })
    };
    question[field] = original;
    return question;
  }

  function segmentOf(source, field) {
    var range = fieldRanges(source)[field === "solution" ? "solution" : "stem"];
    if (!range) return "";
    return String(source || "").slice(range.start, range.end).trim();
  }

  function onAiSend() {
    var item = panelItem();
    var caret = (panel.selection && panel.selection.caret) || null;
    if (!item || !caret || !caret.field) {
      panelSay("先把光标放进题干段或解析段，AI 才知道改哪一段。", "warn", "idle");
      return;
    }
    if (panel.ai.busy) return;
    var ask = panelAiAskEl ? String(panelAiAskEl.value || "").trim() : "";
    if (!ask) {
      panelSay("指令是空的：说一句要怎么改，再点发送。", "warn", "idle");
      return;
    }
    var original = segmentOf(item.source, caret.field);
    if (!original) {
      panelSay("源码里找不到" + fieldLabel(caret.field) + "段的正文：切到格式一补上环境骨架再试。", "error", "invalid");
      return;
    }
    panel.ai = {
      state: "sending", field: caret.field, key: item.key, value: "", note: "", mock: false, busy: true
    };
    renderAi();
    panelSay("改写请求已发出，最长等 " + Math.round(AI_REQUEST_TIMEOUT_MS / 1000) + " 秒…", "info", "sending");
    hostCall("agent.refine", {
      instruction: ask.slice(0, AI_ASK_MAX),
      question: refineContext(item.source, caret.field, original),
      field: caret.field,
      task_id: patchIdFor(item.key).slice(0, 60)
    }, AI_REQUEST_TIMEOUT_MS).then(function (result) {
      panel.ai.busy = false;
      var value = String((result && result.value) || "").trim();
      if (!result || result.ok === false || !value) {
        panel.ai.state = "error";
        panel.ai.note = "模型没给回可采用的正文"
          + ((result && result.note) ? "：" + trunc(result.note, 120) : "；没配 Provider 时底座只会原样回显。");
        renderAi();
        panelSay("改写失败，画布源码没动。", "error", "failed");
        return;
      }
      panel.ai.state = "ready";
      panel.ai.field = result.field === "solution" ? "solution" : caret.field;
      panel.ai.value = trunc(value, FIELD_MAX);
      // 宿主摊平时把 mock 标记丢了：原文与新文逐字相同，就是回显而不是改写，别装作模型改过
      panel.ai.mock = panel.ai.value === original;
      panel.ai.note = panel.ai.mock
        ? "内容与原文逐字相同，多半是回显（本机还没配 Provider）。"
        : trunc(result.note || "", 120);
      renderAi();
      panelSay("改写结果已就绪，看过预览再点【采用】。", "ok", "ready");
    }, function (error) {
      panel.ai.busy = false;
      panel.ai.state = "error";
      panel.ai.note = explainHostError(error);
      renderAi();
      panelSay("改写请求没走通：" + explainHostError(error), "error", "failed");
    });
  }

  /** 采用：面板只发请求，替换由画布执行；两步之间不许把「已发出」说成「已改好」。 */
  function onAiApply() {
    if (panel.ai.state !== "ready" || !panel.ai.field || !panel.ai.value) return;
    var item = panelItem();
    if (!item) {
      panelSay("辅助栏没收到当前题了，回画布点一下那道题再采用。", "warn", "idle");
      return;
    }
    if (item.key !== panel.ai.key) {
      panelSay("当前题已经换成「" + item.key + "」，这份改写属于「" + panel.ai.key + "」，没有回填。", "error", "failed");
      return;
    }
    panel.ai.busy = true;
    renderAi();
    hostCall("editor.apply_patch", {
      id: patchIdFor(panel.ai.key), field: panel.ai.field, value: panel.ai.value
    }).then(function () {
      panel.ai.busy = false;
      panelSay("改写已发给画布的" + fieldLabel(panel.ai.field) + "段——替换结果看中栏提示，保存才入库。", "info", "sent");
    }, function (error) {
      panel.ai.busy = false;
      renderAi();
      panelSay("回填请求没送到画布：" + explainHostError(error), "error", "failed");
    });
  }

  function onAiDiscard() {
    var ask = panelAiAskEl ? panelAiAskEl.value : "";
    panel.ai = { state: "idle", field: "", key: "", value: "", note: "已放弃这次改写。", mock: false, busy: false };
    renderAi();
    if (panelAiAskEl) panelAiAskEl.value = ask;
    panelSay("已放弃这次改写，画布源码没动。", "info", "idle");
  }

  /** 题干段与解析段并发清洗，Promise.all 全成功才逐段回填；任一失败就一个字都不动。 */
  function cleanViaHost() {
    var item = panelItem();
    if (!item) {
      panelSay("辅助栏还没收到当前题的源码，等画布发一次选区。", "warn", "idle");
      return;
    }
    if (panel.ai.busy) return;
    var jobs = ["stem", "solution"].reduce(function (acc, field) {
      var body = segmentOf(item.source, field);
      if (body) acc.push({ field: field, text: body });
      return acc;
    }, []);
    if (!jobs.length) {
      panelSay("源码里没有可清洗的题干段或解析段。", "warn", "idle");
      return;
    }
    panel.ai = { state: "cleaning", field: "", key: item.key, value: "", note: "", mock: false, busy: true };
    renderAi();
    Promise.all(jobs.map(function (job) {
      return hostCall("text.clean_latex", { text: job.text });
    })).then(function (results) {
      var patches = jobs.map(function (job, index) {
        var result = results[index] || {};
        return {
          field: job.field,
          text: String(result.text || "").trim(),
          changed: Boolean(result.changed),
          ok: result.ok !== false && String(result.text || "").trim().length > 0
        };
      });
      var unusable = patches.filter(function (patch) { return !patch.ok; });
      if (unusable.length) {
        panel.ai.busy = false;
        panel.ai.state = "error";
        panel.ai.note = "有段落没清洗出正文（" + unusable.map(function (p) { return fieldLabel(p.field); }).join("、") + "），源码保持原样。";
        renderAi();
        panelSay("清洗中止，画布源码没动。", "error", "failed");
        return;
      }
      var changedCount = patches.filter(function (patch) { return patch.changed; }).length;
      var chain = Promise.resolve();
      patches.forEach(function (patch) {
        chain = chain.then(function () {
          return hostCall("editor.apply_patch", {
            id: patchIdFor(item.key), field: patch.field, value: patch.text
          });
        });
      });
      return chain.then(function () { return changedCount; });
    }).then(function (changedCount) {
      panel.ai.busy = false;
      panel.ai.state = "idle";
      panel.ai.note = changedCount ? "已清洗 " + changedCount + " 段，画布源码待保存。" : "两段都符合规范，没有改动。";
      renderAi();
      panelSay(panel.ai.note, "ok", "cleaned");
    }, function (error) {
      panel.ai.busy = false;
      panel.ai.state = "error";
      panel.ai.note = "清洗失败：" + explainHostError(error) + "，源码保持原样。";
      renderAi();
      panelSay("清洗失败，画布源码没动。", "error", "failed");
    });
  }

  // ---------- 考向（bank.topics 懒展开，可挂多个、可摘） ----------
  function topicNode(node, depth) {
    var row = el("div", "ep-topic-row");
    row.style.paddingLeft = (depth * 12) + "px";
    var expander = el("button", "ep-topic-expander", node.has_children ? "▸" : "·");
    expander.type = "button";
    expander.setAttribute("aria-label", (node.has_children ? "展开 " : "没有下级：") + node.name);
    if (!node.has_children) expander.disabled = true;
    var label = el("button", "ep-topic-name", node.name);
    label.type = "button";
    label.title = "题量 " + node.question_count + "；点一下挂到本题";
    row.appendChild(expander);
    row.appendChild(label);
    var kids = el("div", "ep-topic-kids");
    kids.hidden = true;
    row.appendChild(kids);
    expander.addEventListener("click", function () {
      var open = !kids.hidden;
      kids.hidden = open;
      expander.textContent = open ? "▸" : "▾";
      row.setAttribute("data-open", open ? "false" : "true");
      if (!open && !kids.childNodes.length) loadChildren(node, kids, depth + 1);
    });
    label.addEventListener("click", function () { toggleTopic(node); });
    return row;
  }

  function loadChildren(node, holder, depth) {
    hostCall("bank.topics", { parent_id: node.id }).then(function (result) {
      var items = (result && result.items) || [];
      if (!items.length) {
        holder.appendChild(el("p", "ep-note", "这一层没有下级节点。"));
        return;
      }
      items.forEach(function (child) { holder.appendChild(topicNode(child, depth)); });
    }, function (error) {
      holder.appendChild(el("p", "ep-note", "读考向失败：" + explainHostError(error)));
    });
  }

  function loadTopicRoots() {
    if (!panelTreeEl || panel.topics.roots) return;
    panelTreeEl.textContent = "";
    panelTreeEl.appendChild(el("p", "ep-note", "正在读大纲…"));
    hostCall("bank.topics", {}).then(function (result) {
      var items = (result && result.items) || [];
      panel.topics.roots = items;
      panelTreeEl.textContent = "";
      if (!items.length) {
        panelTreeEl.appendChild(el("p", "ep-note", "当前题库还没有大纲节点。"));
        return;
      }
      items.forEach(function (node) { panelTreeEl.appendChild(topicNode(node, 0)); });
      if (panelTopicErrorEl) panelTopicErrorEl.hidden = true;
    }, function (error) {
      panelTreeEl.textContent = "";
      if (panelTopicErrorEl) {
        panelTopicErrorEl.hidden = false;
        panelTopicErrorEl.textContent = "考向读不出来：" + explainHostError(error) + "（不影响保存）";
      }
    });
  }

  function toggleTopic(node) {
    var entry = panel.currentEntry || (panel.currentEntry = {});
    var ids = (entry.topic_ids || []).slice();
    var names = entry.topic_names || {};
    var position = ids.indexOf(node.id);
    if (position >= 0) {
      ids.splice(position, 1);
      delete names[node.id];
    } else if (ids.length >= TOPIC_LIMIT) {
      panelSay("考向最多挂 " + TOPIC_LIMIT + " 个，先摘掉一个。", "warn", "idle");
      return;
    } else {
      ids.push(node.id);
      names[node.id] = node.name;
    }
    entry.topic_ids = ids;
    entry.topic_names = names;
    panel.currentEntry = entry;
    if (panel.selection) {
      panel.meta[panel.selection.key] = entry;
      panel.selection.dirty = true;
    }
    queueMetaSave();
    renderMounted();
    renderPanelMetrics();
  }

  function renderMounted() {
    if (!panelMountedEl) return;
    var entry = panel.currentEntry || {};
    var ids = entry.topic_ids || [];
    var names = entry.topic_names || {};
    panelMountedEl.textContent = "";
    if (!ids.length) {
      panelMountedEl.appendChild(el("span", "ep-note", "还没挂考向"));
      return;
    }
    ids.forEach(function (id) {
      var chip = el("span", "ep-chip");
      chip.setAttribute("data-topic", id);
      chip.appendChild(el("span", "ep-chip-name", names[id] || id));
      var removeBtn = el("button", "ep-chip-x", "摘");
      removeBtn.type = "button";
      removeBtn.setAttribute("aria-label", "摘除考向 " + (names[id] || id));
      removeBtn.addEventListener("click", function () {
        toggleTopic({ id: id, name: names[id] || id });
      });
      chip.appendChild(removeBtn);
      panelMountedEl.appendChild(chip);
    });
  }

  /** 从宿主代持的工作清单草稿里重建辅助栏选区——两个帧同时挂载，通知不一定赶得上。 */
  function applyDraftSelection(value) {
    if (panel.selection) return;
    var items = value && Array.isArray(value.items) ? value.items : [];
    var active = value ? Number(value.active) || 0 : 0;
    var saved = items[active] || items[0] || null;
    if (!saved) return;
    var source = String(saved.source || "");
    panel.source = source;
    applySelection({
      index: active, total: items.length, key: saved.key,
      question_id: saved.id || saved.saved_id || "", saved_id: saved.saved_id || "",
      status: saved.status, dirty: Boolean(saved.dirty), format: panel.format,
      source: source, errors: saved.errors || [], ai_type: parseExamSource(source).type,
      confidence: typeof saved.confidence === "number" ? saved.confidence : null,
      defaults: saved.defaults || {}, images: [], extensions: {}
    });
  }

  function activatePanel() {
    if (!panelRoot) return;
    panelRoot.hidden = false;
    fillSelect(panelTypeEl, TYPE_VALUES, TYPE_LABELS);
    fillSelect(panelDifficultyEl, DIFFICULTY_VALUES, {
      L1: "L1 基础", L2: "L2 中档", L3: "L3 难", L4: "L4 压轴"
    });
    bindFormChanges();
    if (panelFormatLatexEl) {
      panelFormatLatexEl.addEventListener("click", function () { switchFormat("latex"); });
    }
    if (panelFormatBoxedEl) {
      panelFormatBoxedEl.addEventListener("click", function () { switchFormat("boxed"); });
    }
    if (panelSaveEl) panelSaveEl.addEventListener("click", function () { onPanelSave("save"); });
    if (panelVariantEl) panelVariantEl.addEventListener("click", function () { onPanelSave("variant"); });
    if (panelAiAskEl) panelAiAskEl.addEventListener("input", renderAi);
    if (panelAiSendEl) panelAiSendEl.addEventListener("click", onAiSend);
    if (panelAiCleanEl) panelAiCleanEl.addEventListener("click", cleanViaHost);
    if (panelAiApplyEl) panelAiApplyEl.addEventListener("click", onAiApply);
    if (panelAiDiscardEl) panelAiDiscardEl.addEventListener("click", onAiDiscard);
    renderAi();
    setFormatButtons("latex");
    loadMetaDraft().then(function () {
      return hostCall("draft.load", { key: DRAFT_WORKLIST_KEY });
    }).then(function (result) {
      applyDraftSelection(result && result.value);
      loadTopicRoots();
      if (!panel.selection) {
        // 画布可能比面板慢一步才把草稿写回来：补读一次，别让右栏晾成空壳
        window.setTimeout(function () {
          if (panel.selection) return;
          hostCall("draft.load", { key: DRAFT_WORKLIST_KEY }).then(function (retry) {
            applyDraftSelection(retry && retry.value);
          }, function () { /* 还是读不到就等画布下一次发布 */ });
        }, PANEL_DRAFT_RETRY_MS);
      }
    }).catch(function () { loadTopicRoots(); });
    panel.ready = true;
  }

  // ---------- 协议 ----------
  window.addEventListener("message", function (event) {
    var message = event.data;
    if (!message || message.protocol !== PROTOCOL) return;

    if (message.kind === "response" && pending.has(message.id)) {
      var waiter = pending.get(message.id);
      pending.delete(message.id);
      if (message.ok) waiter.resolve(message.result || {});
      else waiter.reject(hostError(message.error));
      return;
    }

    if (message.kind === "notification") {
      if (message.event === "system.open_editor") {
        if (state.slot !== "stage.center") return;
        var wanted = (message.payload && message.payload.question_id) || "";
        var origin = (message.payload && message.payload.from) || "";
        if (wanted) loadForEdit(wanted, origin);
        return;
      }
      if (message.event === "editor.apply_patch") {
        // 面板自己发的回填会广播回所有帧：只有画布动手改源码，面板一律静默
        if (state.slot === "stage.center") applyAiPatch(message.payload);
        return;
      }
      if (message.event === "ui.params.changed") {
        onUiParams(message.payload);
        return;
      }
      if (message.event === "stage.selection") {
        // 宿主只把选区投给面板帧（画布自己就是来源，回灌只会形成回声）
        if (state.slot !== "stage.center") {
          applySelection((message.payload && message.payload.raw) || {});
        }
        return;
      }
      if (message.event === "system.question_updated") {
        if (state.slot === "stage.center") consumeReceipts(message.payload);
        return;
      }
      return;
    }

    if (message.kind !== "request") return;

    if (message.method === "plugin.activate") {
      state.slot = (message.payload && message.payload.slot) || "stage.center";
      if (state.slot !== "stage.center") {
        activatePanel();
        return respond(event.source, message.id, true, { ready: true, plugin_id: PLUGIN_ID, slot: state.slot });
      }
      root.hidden = false;
      loadFixtures();
      applyWidths();
      renderAll();
      if (sourceHintEl) sourceHintEl.textContent = "格式一 · 整段源码直接编辑";
      restoreWorklist().then(function () {
        renderAll();
        saveWorklist();
        publishSelection();
      });
      hostCall("draft.load", { key: DRAFT_LAYOUT_KEY }).then(function (result) {
        var value = result && result.value;
        if (value && value.widths) {
          state.widths.image = Number(value.widths.image) || state.widths.image;
          state.widths.source = Number(value.widths.source) || state.widths.source;
          applyWidths();
        }
        state.layoutReady = true;
      }).catch(function () { state.layoutReady = true; });
      return respond(event.source, message.id, true, { ready: true, plugin_id: PLUGIN_ID, slot: state.slot });
    }
    if (message.method === "plugin.deactivate") {
      if (state.slot === "stage.center") {
        root.hidden = true;
        if (worklistTimer) { window.clearTimeout(worklistTimer); saveWorklist(); }
        if (selectionTimer) window.clearTimeout(selectionTimer);
      } else {
        panelRoot.hidden = true;
        if (metaTimer) { window.clearTimeout(metaTimer); saveMetaDraft(); }
      }
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
    if (saveAllEl) saveAllEl.addEventListener("click", function () { saveAllDirty(); });
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
      if (worklistTimer) {
        window.clearTimeout(worklistTimer);
        saveWorklist();
      }
      if (metaTimer) {
        window.clearTimeout(metaTimer);
        saveMetaDraft();
      }
    });
  }

  bind();

  // 真机探针用的调试面：只把解析/重组结果交给 Playwright 复核，不参与业务分支。
  window.__jzoEditorV2 = {
    version: "2.0.0-stage4",
    parseExamSource: parseExamSource,
    buildExamSource: buildExamSource,
    cleanExamSource: cleanExamSource,
    boxesToQuestion: boxesToQuestion,
    questionFromParsed: questionFromParsed,
    validateForSave: validateForSave,
    fixtures: DEV_FIXTURES,
    state: state,
    panel: panel,
    renderAll: renderAll,
    refreshRow: refreshRow,
    setFormat: setFormat,
    saveItem: saveItem,
    applySelection: applySelection,
    selectionPayload: selectionPayload,
    jumpTo: jumpTo,
    poolCounts: poolCounts,
    saveAllDirty: saveAllDirty
  };
})();
