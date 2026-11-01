/**
 * 录题工作台 v3（军令 #24：批次系统与待审核池）。
 *
 * 画布实例（stage.center）有两屏：
 *   首屏是批次列表——一行一个批次，点任意一行进入审核；
 *   二屏是三栏审核界面——左原图 | 中全量 exam-zh 源码 | 右渲染，抬头写着当前批次号。
 * 辅助栏实例（sidebar.right）是审核台：元数据表单 + AI 帮改 + 审核动作。
 *
 * 题目先落在中转站（待审核池），老师审完才由【存入主库】落进主库。
 * 中转站与主库物理隔离，插件不碰数据库、不碰令牌，写库一律经宿主。
 *
 * 同一个插件的两个沙箱帧拿不到彼此的 DOM，只走底座开好的合法通道：
 *   画布 → 辅助栏：发布 stage.selection（当前题的源码、进度与元数据默认值）；
 *   辅助栏 → 画布：ui.params.set（format / swap / view），由宿主广播 ui.params.changed；
 *   两帧共享：draft.save / draft.load 交宿主代持的工作清单与元数据草稿；
 *   中转站：pending.batch_list / list / save_draft / approve / delete 五条 Host API；
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
  var GHOST_SCROLL_MS = 900;
  var PANEL_DRAFT_RETRY_MS = 900;
  var RECEIPT_RETRY_MS = 350;
  var RECEIPT_RETRY_MAX = 4;
  var SPLIT_W = 6;
  var PANE_MIN = 28;
  // 三栏宽度按「比例」记账，不按像素：画布宽度一变（折叠辅助栏、拖窗口），
  // 三栏必须按同一比例缩放，而不是把弹性那一栏（渲染）单独挤没。
  var DEFAULT_IMAGE_RATIO = 0.2;
  var DEFAULT_SOURCE_RATIO = 0.34;
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
  // 源码在两帧之间要整段搬运（辅助栏的批量保存靠它重建题目对象）：
  // 砍到 20000 字会把长解析的尾巴悄悄切掉，题库里就少一截。
  var SOURCE_MAX = 60000;
  var TOPIC_LIMIT = 8;
  var TAG_LIMIT = 32;
  // 呼吸灯：鼠标在画布某题上停够 200ms 才亮，免得一路扫过去满屏闪。
  var LAMP_DELAY_MS = 200;
  // 幽灵胶囊：停在上面 150ms 自己活过来并接上光标，老师不用点。
  var GHOST_DELAY_MS = 150;
  // 宿主 stage.js 对 instruction 的截断额度就是 400，面板先按同一个数拦，别让老师的长指令被悄悄切尾
  var AI_ASK_MAX = 400;
  // 防呆：界面三分钟没人碰，就静默把当前题存回中转池。
  // 用 setInterval 巡时间差，而不是一条 setTimeout 链——后者在页面冻结时会被浏览器压后，
  // 假时钟也推不动它；巡时间差这条，真实时钟一走满就一定触发。
  var IDLE_MS = 3 * 60 * 1000;
  var IDLE_TICK_MS = 5000;

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
  var batchesEl = document.getElementById("edBatches");
  var batchListEl = document.getElementById("edBatchList");
  var batchesEmptyEl = document.getElementById("edBatchesEmpty");
  var batchNoEl = document.getElementById("edBatchNo");
  var batchStatEl = document.getElementById("edBatchStat");
  // 文件收集筐（军令 #27）：拖入、粘贴、点选都先落这里，【开始解析】才建批次。
  var basketEl = document.getElementById("edBasket");
  var basketFileEl = document.getElementById("edBasketFile");
  var basketEmptyEl = document.getElementById("edBasketEmpty");
  var basketListEl = document.getElementById("edBasketList");
  var basketFootEl = document.getElementById("edBasketFoot");
  var basketGoEl = document.getElementById("edBasketGo");

  var panelRoot = document.getElementById("epRoot");
  var panelScrollEl = document.getElementById("epScroll");
  var panelProgressEl = document.getElementById("epProgress");
  var panelStatusEl = document.getElementById("epStatus");
  var panelConfidenceEl = document.getElementById("epConfidence");
  var panelTypeEl = document.getElementById("epType");
  var panelTypeNoteEl = document.getElementById("epTypeNote");
  var panelDifficultyEl = document.getElementById("epDifficulty");
  var panelGradeEl = document.getElementById("epGrade");
  var panelPaperEl = document.getElementById("epPaper");
  var panelQuestionNoEl = document.getElementById("epQuestionNo");
  var panelExamTypeEl = document.getElementById("epExamType");
  var panelYearEl = document.getElementById("epYear");
  var panelScoreEl = document.getElementById("epScore");
  var panelHeadNoEl = document.getElementById("epHeadNo");
  var panelTagsEl = document.getElementById("epTags");
  var panelTagListEl = document.getElementById("epTagList");
  var panelMountedEl = document.getElementById("epMounted");
  var panelMetaSecEl = document.getElementById("epMetaSec");
  var panelMetaFoldEl = document.getElementById("epMetaFold");
  var panelMetaSummaryEl = document.getElementById("epMetaSummary");
  var panelGhostTagMenuEl = document.getElementById("epGhostTagMenu");
  var panelGhostTopicMenuEl = document.getElementById("epGhostTopicMenu");
  var panelTreeEl = document.getElementById("epTopicTree");
  var panelTopicErrorEl = document.getElementById("epTopicError");
  var panelApproveEl = document.getElementById("epApprove");
  var panelStashEl = document.getElementById("epStash");
  var panelDeleteEl = document.getElementById("epDelete");
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
  var panelFmtLatexEl = document.getElementById("epFmtLatex");
  var panelFmtBoxedEl = document.getElementById("epFmtBoxed");
  var panelSwapEl = document.getElementById("epSwap");
  var panelBackListEl = document.getElementById("epBackList");
  var panelViewNoteEl = document.getElementById("epViewNote");
  var dupModalEl = document.getElementById("epDupModal");
  var dupTextEl = document.getElementById("epDupText");
  var dupBackEl = document.getElementById("epDupBack");
  var dupForceEl = document.getElementById("epDupForce");
  var delModalEl = document.getElementById("epDelModal");
  var delCancelEl = document.getElementById("epDelCancel");
  var delOkEl = document.getElementById("epDelOk");

  // 批次公共元数据（辅助栏顶部）：六个可填字段 + 字典学校 + 可手改的标准名。
  var panelSrcNameEl = document.getElementById("epSrcName");
  var panelStdNameEl = document.getElementById("epStdName");
  var panelStdFlashEl = document.getElementById("epStdFlash");
  var panelStdHintEl = document.getElementById("epStdHint");
  var panelIntakeEl = document.getElementById("epIntake");
  var panelMetaYearEl = document.getElementById("epMetaYear");
  var panelMetaRegionEl = document.getElementById("epMetaRegion");
  var panelMetaBodyEl = document.getElementById("epMetaBody");
  var panelMetaSceneEl = document.getElementById("epMetaScene");
  var panelMetaExamTypeEl = document.getElementById("epMetaExamType");
  var panelMetaSubjectEl = document.getElementById("epMetaSubject");
  var panelMetaSchoolsEl = document.getElementById("epMetaSchools");
  var panelSchoolListEl = document.getElementById("epSchoolList");
  var panelSchoolInputEl = document.getElementById("epSchoolInput");
  var panelSchoolMenuEl = document.getElementById("epSchoolMenu");
  var panelSchoolConfirmEl = document.getElementById("epSchoolConfirm");
  var panelSchoolConfirmTextEl = document.getElementById("epSchoolConfirmText");
  var panelSchoolFullNameEl = document.getElementById("epSchoolFullName");
  var panelSchoolConfirmOkEl = document.getElementById("epSchoolConfirmOk");
  var panelSchoolConfirmCancelEl = document.getElementById("epSchoolConfirmCancel");
  var panelSchoolErrorEl = document.getElementById("epSchoolError");
  var panelTagMenuEl = document.getElementById("epTagMenu");
  var panelRegionListEl = document.getElementById("epMetaRegionList");
  var panelBodyListEl = document.getElementById("epMetaBodyList");
  var panelSubjectListEl = document.getElementById("epMetaSubjectList");

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
  // 互换钮被点击时会先把焦点从源码框夺走：记住最后一只有 data-field 的编辑框，换完把光标送回去
  var lastFieldNode = null;

  var state = {
    slot: "stage.center",
    // 两屏：list 是批次列表（首屏），review 是三栏审核（二屏）。
    mode: "list",
    items: [],
    active: 0,
    batches: [],
    batchId: "",
    format: "latex",
    swap: false,
    widths: { image: DEFAULT_IMAGE_RATIO, source: DEFAULT_SOURCE_RATIO },
    dirty: false,
    layoutReady: false,
    worklistReady: false,
    // 收集筐里还没解析的文件（军令 #27）：拖入、粘贴、点选都先进这里。
    basket: []
  };

  var panel = {
    ready: false,
    selection: null,
    source: "",
    meta: {},
    uiRevisions: null,
    receipts: [],
    format: "latex",
    swap: false,
    topics: { roots: null, children: {}, open: {}, loading: {} },
    saving: false,
    // 弹窗正在处置的那道题（查重 / 彻底删除共用）
    pending: null,
    ai: { state: "idle", field: "", key: "", value: "", note: "", mock: false, busy: false },
    // 批次公共元数据：当前批次、这一批的公共字段、明细学校名单、历史值。
    batchId: "",
    batchCard: null,
    batchMeta: {},
    // 明细学校只存字典记录（id + 全称 + 简称），题目里也只认 school_id。
    schools: [],
    // 老师刚建档、还没进回执快照的学校：回执晚到时不能把它抹掉。
    schoolAdded: {},
    // 老师亲手摘掉的学校：旧回执也不能把它请回来。
    schoolDropped: {},
    // 这套本地记账跟着哪一批走，换批就作废。
    schoolBatchId: "",
    schoolOptions: [],
    schoolQuery: "",
    schoolPending: null,
    // 11 个主场景由底座给，插件不写死一份名单。
    scenes: [],
    tagOptions: [],
    groups: {},
    history: {},
    lastBody: "",
    metaSyncing: false,
    // 标准名双向联动：手改即 manual，元数据再动立刻回 auto。
    stdManual: false,
    // 考向节点 id → 名称：模糊搜索要给人看的路径，bank.topics 只给 id 链。
    topicNames: {},
    // 父节点 id → 它那一层的子节点名：查一次路径就把整层名字收下来，不重复问。
    topicChildren: {},
    // 同一层正在飞的路：并发的路径解析共用一个请求，别把宿主问炸。
    topicPending: {}
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
    // 查重：底座把主库那道题的 id 与 duplicate 标记一并带回来，弹窗才画得出「返回修改 / 强行覆盖」。
    error.existingId = String((raw && raw.existing_id) || "");
    error.duplicate = Boolean(raw && raw.duplicate);
    // 报错诊断与字典拦截都靠这几个字段：完整现场 + 结构化的冲突信息。
    error.detail = String((raw && raw.detail) || "");
    error.status = Number(raw && raw.status) || 0;
    error.detailCode = String((raw && raw.detail_code) || "");
    error.existingFullName = String((raw && raw.existing_full_name) || "");
    return error;
  }

  function publish(event, payload) {
    try {
      window.parent.postMessage({
        protocol: PROTOCOL, kind: "notification", event: event, payload: payload || {}
      }, "*");
    } catch (error) { /* 通知丢一帧不致命 */ }
  }

  /** 往底部日志写一行。level 由宿主白名单把关：note（灰字流水）、warn（警告）、info。 */
  function dock(text, level, topic, detail) {
    publish("region.dock", {
      text: String(text == null ? "" : text).slice(0, 400),
      level: level || "info",
      topic: topic || "",
      // 报错诊断要完整现场：宿主中继失败时把请求行、状态、Response 全文一并交出去。
      detail: String(detail == null ? "" : detail).slice(0, 20000)
    });
  }

  function errorDetail(error) {
    if (!error) return "";
    if (typeof error.detail === "string" && error.detail) return error.detail;
    var lines = [];
    if (error.status) lines.push("HTTP " + error.status + (error.statusText ? " " + error.statusText : ""));
    if (error.message) lines.push(String(error.message));
    return lines.join("\n");
  }

  /**
   * 警告只进底部日志，绝不在画布上弹红窗——
   * 后台切题时识别错得再离谱也照切不误，老师看到的只是一行提示，不是一块拦路的窗。
   */
  function dockWarn(text, detail) {
    dock("⚠ " + String(text == null ? "" : text).slice(0, 360), "warn", "editor.warn", detail);
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
    // 中转站里的配图挂在 pending_assets/，审核台看的就是它。
    if (uri.indexOf("/static/pending/") === 0) return uri;
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

  // ---------- exam-zh 源码：解析（渲染与卡片共用）+ 重组（阶段 2 直接复用这一份） ----------
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

  /** 结构化题目 → 源码（军令 #23 的格式宪法；阶段 2 的自动重组复用这一个函数）。 */
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
      return { ok: false, message: "源码里找不到" + fieldLabel(field) + "段：先在源码补上对应环境" };
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
    "schema_version": "2.1",
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
    "schema_version": "2.1",
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
    "schema_version": "2.1",
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
    "schema_version": "2.1",
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
      // 中转站编号（p_ 开头）与所属批次：审核动作全靠这两个号说话。
      pendingId: "",
      batchId: "",
      assets: [],
      dirty: false,
      status: "pending",
      parsed: null
    };
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
      state.batchId = "";
      // 题库点「去编辑」是从批次列表外直接跳进二屏：先把三栏露出来。
      setMode("review");
      renderAll();
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

  // ---------- 审核台（军令 #24）：首屏批次列表，二屏三栏审核 ----------
  var WEEKDAYS = "日一二三四五六";

  /** 批次录入时间 → 「2024-10-31-星期四-15:30」。写的是原卷的本地时间，不做时区换算。 */
  function batchStamp(createdAt) {
    var text = String(createdAt == null ? "" : createdAt);
    var hit = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(text);
    if (!hit) return text.slice(0, 16) || "时间未知";
    var day = new Date(Number(hit[1]), Number(hit[2]) - 1, Number(hit[3]));
    return hit[1] + "-" + hit[2] + "-" + hit[3] + "-星期" + WEEKDAYS.charAt(day.getDay())
      + "-" + hit[4] + ":" + hit[5];
  }

  function currentBatch() {
    var id = String(state.batchId || "");
    var found = null;
    state.batches.forEach(function (card) {
      if (String(card.batch_id || "") === id) found = card;
    });
    return found;
  }

  /**
   * 首屏：批次列表。一行一个批次，左边时间与编号，右边「未审：n / N」。
   * 数字用绿色；未审数为 0 的批次整行变灰、沉到最底下，并且点不动——只能看。
   */
  function renderBatchList() {
    if (!batchListEl) return;
    batchListEl.textContent = "";
    var cards = state.batches.slice();
    cards.sort(function (left, right) {
      var leftDone = Number(left.pending_count) === 0 ? 1 : 0;
      var rightDone = Number(right.pending_count) === 0 ? 1 : 0;
      if (leftDone !== rightDone) return leftDone - rightDone;
      return String(right.created_at || "").localeCompare(String(left.created_at || ""));
    });
    cards.forEach(function (card) {
      var pending = Number(card.pending_count) || 0;
      var total = Number(card.total) || 0;
      var done = pending === 0;
      var row = el("button", "ed-batch-row");
      row.type = "button";
      row.setAttribute("data-batch", String(card.batch_id || ""));
      row.setAttribute("data-done", done ? "true" : "false");
      if (done) {
        row.disabled = true;
        row.setAttribute("aria-disabled", "true");
        row.setAttribute("aria-label", "批次 " + card.batch_id + " 已审完，未审 0 / " + total + "，只看不能进");
      } else {
        row.setAttribute("aria-label", "批次 " + card.batch_id + "，未审 " + pending + " / " + total + "，点开审核");
        row.addEventListener("click", function () { openBatch(card.batch_id); });
      }
      row.appendChild(el("span", "ed-batch-left",
        batchStamp(card.created_at) + "-批次编号 #" + card.batch_id));
      var right = el("span", "ed-batch-right");
      right.appendChild(el("span", "ed-batch-label", "未审："));
      right.appendChild(el("span", "ed-batch-num", String(pending)));
      right.appendChild(el("span", "ed-batch-sep", " / "));
      right.appendChild(el("span", "ed-batch-num", String(total)));
      if (done) right.appendChild(el("span", "ed-batch-check", "✅"));
      row.appendChild(right);
      batchListEl.appendChild(row);
    });
    if (batchesEmptyEl) batchesEmptyEl.hidden = cards.length > 0;
  }

  /** 二屏抬头：当前批次号与这一批还剩几道没审。 */
  function renderBatchBar() {
    if (batchNoEl) batchNoEl.textContent = "批次 #" + (state.batchId || "—");
    if (batchStatEl) {
      var card = currentBatch();
      var pending = state.items.length;
      var total = card ? Number(card.total) || 0 : pending;
      batchStatEl.textContent = "未审 " + pending + " / " + total;
      batchStatEl.setAttribute("data-pending", String(pending));
      batchStatEl.setAttribute("data-total", String(total));
    }
  }

  function setMode(mode) {
    state.mode = mode === "review" ? "review" : "list";
    if (root) root.setAttribute("data-mode", state.mode);
    if (batchesEl) batchesEl.hidden = state.mode !== "list";
    if (colsEl) colsEl.hidden = state.mode !== "review";
  }

  /** 重新拉一遍批次卡片：未审数、总数与「审完变灰」都以底座那边的账为准。 */
  function refreshBatches() {
    return hostCall("pending.batch_list", {}).then(function (result) {
      var cards = (result && Array.isArray(result.batches)) ? result.batches : [];
      state.batches = cards;
      renderBatchList();
      renderBatchBar();
      var card = currentBatch();
      if (state.mode === "review" && card && Number(card.pending_count) === 0 && !state.items.length) {
        backToList("这一批已审完，卡片变灰沉到列表最底下。");
      }
      // 首屏要把最新的批次卡片推给辅助栏：它据此显示原文件名、标准名与公共元数据。
      if (state.mode === "list") publishSelection();
      return cards;
    }).catch(function (error) {
      dockWarn("批次列表没拉下来：" + ((error && error.message) || "未知原因"), errorDetail(error));
      return [];
    });
  }

  /** 头一次开审核台：中转站是空的，就把识别结果整批入池，批次列表才有东西可点。 */
  function seedBatch() {
    var questions = DEV_FIXTURES.map(function (doc) {
      return { question: doc };
    });
    return hostCall("pending.save_draft", {
      questions: questions,
      origin: "editor.recognize"
    }).then(function (result) {
      dock("识别结果已入池：" + (result.batch_id || "") + "（" + questions.length + " 题）。");
      return result;
    }, function (error) {
      dockWarn("识别结果入池失败：" + ((error && error.message) || "未知原因"), errorDetail(error));
      return null;
    });
  }

  /** 画布视图（review / list）也走宿主参数通道：辅助栏那颗【← 返回列表】才有路。 */
  function publishView(view) {
    hostCall("ui.params.set", {
      params: { view: view === "list" ? "list" : "review" },
      snapshot: panel.uiRevisions || {},
      plugin_id: PLUGIN_ID
    }).catch(function () { /* 参数通道没通，画布自己的落点不受影响 */ });
  }

  /** 点开一个批次：中转站里那一批的待审题直接铺进三栏。 */
  function openBatch(batchId) {
    var id = String(batchId || "");
    if (!id) return Promise.resolve(null);
    return hostCall("pending.list", { batch_id: id }).then(function (result) {
      var rows = (result && Array.isArray(result.items)) ? result.items : [];
      state.batchId = id;
      state.items = rows.map(function (row, index) {
        var doc = (row && row.question) || {};
        var item = makeItem(doc, buildExamSource(doc), index);
        item.pendingId = String((row && row.id) || "");
        item.batchId = String((row && row.batch_id) || id);
        item.assets = Array.isArray(row.assets) ? row.assets : [];
        item.status = "pending";
        return item;
      });
      state.active = 0;
      state.dirty = false;
      setMode("review");
      publishView("review");
      renderBatchBar();
      renderAll();
      publishSelection();
      noteActivity();
      // 识别错得再离谱也照切不误：只在底部日志留一行警告，绝不在画布上弹红窗。
      var broken = state.items.filter(function (item) { return parsedOf(item).errors.length > 0; });
      if (broken.length) {
        dockWarn("批次 " + id + " 里有 " + broken.length + " 题识别有出入，已照原样切进来。");
      }
      return state.items;
    }).catch(function (error) {
      dockWarn("批次 " + id + " 切不进来：" + ((error && error.message) || "未知原因"), errorDetail(error));
      return null;
    });
  }

  /** 回批次列表。走之前把改过的题静默存回中转池，别让老师的改动随界面一起没了。 */
  function backToList(note, fromHost) {
    var leaving = state.mode === "review";
    setMode("list");
    if (leaving) stashBeforeLeave();
    // 辅助栏点的那一下已经走过宿主广播，画布不必把同样的意思再发一遍。
    if (!fromHost) publishView("list");
    refreshBatches();
    if (note) dock(note);
  }

  /**
   * 一道题存回中转池：带 pending_id 就是原地更新，池子里不会多出一道重影。
   * silent=true 时不打扰老师（自动保存与离开前兜底走这条）。
   */
  function stashOne(item, meta, silent) {
    var parsed = parseExamSource(item.source);
    var doc = questionFromParsed(item, parsed, meta || {});
    var problems = validateForSave(doc, parsed, meta || {});
    if (problems.length) {
      var reason = problems.slice(0, 3).join("；");
      if (!silent) panelSay("这一题还存不进去：" + reason, "warn", "invalid");
      return Promise.resolve({ ok: false, message: reason });
    }
    var payload = { questions: [{ pending_id: item.pendingId || "", question: doc }] };
    // 刚切出来的图：字节随草稿一起进池子，落 pending_assets/，主库一个字节都不碰。
    if (item.cropAsset && item.cropAsset.data_url) {
      payload.questions[0].assets = [{
        id: String(item.cropAsset.id || ""),
        data_url: String(item.cropAsset.data_url || "")
      }];
    }
    if (item.batchId) payload.batch_id = item.batchId;
    return hostCall("pending.save_draft", payload).then(function (result) {
      item.dirty = false;
      if (!item.pendingId && result && Array.isArray(result.saved_ids) && result.saved_ids[0]) {
        item.pendingId = String(result.saved_ids[0]);
        item.batchId = String(result.batch_id || item.batchId || "");
      }
      if (!silent) {
        panelSay("已存为待办（池子编号 " + (item.pendingId || "—") + "）。", "ok", "stashed");
        dock("一道题已存进中转站（待审核池）。");
      }
      return { ok: true, result: result };
    }, function (error) {
      var text = (error && error.message) || "未知原因";
      if (!silent) {
        panelSay("存为待办失败：" + text, "error", "failed");
        dockWarn("存为待办失败：" + text, errorDetail(error));
      }
      return { ok: false, message: text, detail: errorDetail(error) };
    });
  }

  /** 离开审核界面之前，把改过的题静默存回中转池。 */
  function stashBeforeLeave() {
    var targets = state.items.filter(function (item) { return item.pendingId && item.dirty; });
    if (!targets.length) return Promise.resolve(null);
    return loadMetaDraft().then(function () {
      return targets.reduce(function (chain, target) {
        return chain.then(function () {
          return stashOne(target, metaFor(target, {}), true);
        });
      }, Promise.resolve(null));
    }).catch(function () { return null; });
  }

  // ---------- 防呆：三分钟没人碰就静默存回中转池 ----------
  var lastActivityAt = Date.now();
  var idleTimer = 0;
  var idleBusy = false;

  function noteActivity() {
    lastActivityAt = Date.now();
  }

  function startIdleWatch() {
    if (idleTimer) return;
    idleTimer = window.setInterval(function () {
      if (state.slot !== "stage.center" || state.mode !== "review" || idleBusy) return;
      if (!state.items.length) return;
      if (Date.now() - lastActivityAt < IDLE_MS) return;
      autoSaveIdle();
    }, IDLE_TICK_MS);
  }

  /** 长时间无操作 → 静默存回中转池，只在底部日志留一行灰字，绝不弹窗抢老师。 */
  function autoSaveIdle() {
    var item = state.items[state.active];
    if (!item || !item.pendingId) return;
    idleBusy = true;
    loadMetaDraft().then(function () {
      return stashOne(item, metaFor(item, {}), true);
    }).then(function (outcome) {
      idleBusy = false;
      lastActivityAt = Date.now();
      if (outcome && outcome.ok) {
        dock("检测到长时间无操作，已自动存入待审核池。", "note");
      } else {
        dockWarn("自动存入待审核池没成功：" + ((outcome && outcome.message) || "未知原因"),
          (outcome && outcome.detail) || "");
      }
    }, function () {
      idleBusy = false;
    });
  }

  /** 关闭或刷新页面时的兜底：不等草稿往返，直接把当前题存回中转池。 */
  function stashOnUnload() {
    var item = state.items[state.active];
    if (!item || !item.pendingId) return;
    var meta = metaFor(item, {});
    var parsed = parseExamSource(item.source);
    var doc = questionFromParsed(item, parsed, meta);
    if (validateForSave(doc, parsed, meta).length) return;
    var payload = { questions: [{ pending_id: item.pendingId, question: doc }] };
    if (item.batchId) payload.batch_id = item.batchId;
    hostCall("pending.save_draft", payload).catch(function () { /* 页面已经在关了 */ });
  }

  /** 中转站动了：入库与删除会把题从池子里带走，画布得把那几道撤下来；暂存只是改内容，不撤。 */
  function onPendingUpdated(payload) {
    var action = String((payload && payload.action) || "");
    var ids = (payload && Array.isArray(payload.pending_ids)) ? payload.pending_ids : [];
    if ((action === "approve" || action === "delete") && ids.length) {
      var before = state.items.length;
      state.items = state.items.filter(function (item) {
        return ids.indexOf(String(item.pendingId)) < 0;
      });
      if (state.items.length !== before) {
        if (state.active >= state.items.length) state.active = Math.max(0, state.items.length - 1);
        renderBatchBar();
        renderAll();
        publishSelection();
      }
    }
    refreshBatches();
  }

  // ---------- 批次公共元数据（辅助栏顶部） ----------

  /** 标准名：年份-地区-主体-场景-类型-学科。空段不占位；底座也用同一口径重算，客户端说了不算。 */
  function standardNameOf(meta) {
    var m = meta || {};
    var parts = [
      m.year == null || m.year === "" ? "" : String(m.year),
      String(m.region || ""),
      String(m.body || ""),
      String(m.scene_type || ""),
      String(m.exam_type || ""),
      String(m.subject || "")
    ];
    return parts.filter(function (part) { return part; }).join("-").slice(0, 120);
  }

  function fillDataList(node, values) {
    if (!node) return;
    node.textContent = "";
    (values || []).forEach(function (value) {
      var text = String(value || "");
      if (!text) return;
      var option = document.createElement("option");
      option.value = text;
      node.appendChild(option);
    });
  }

  /** 历史值：地区 / 主体 / 学科各一份联想，另有主体 → 明细学校的对应。 */
  function loadMetaHistory() {
    return hostCall("pending.meta_history", {}).then(function (result) {
      panel.history = (result && result.history) || {};
      panel.groups = (result && result.groups) || {};
      fillDataList(panelRegionListEl, panel.history.region);
      fillDataList(panelBodyListEl, panel.history.body);
      fillDataList(panelSubjectListEl, panel.history.subject);
      return panel.history;
    }).catch(function () {
      return null;
    });
  }

  // ---------- 场景表：11 个主场景，底座说了算 ----------

  function renderSceneOptions() {
    if (!panelMetaSceneEl) return;
    var current = String(panelMetaSceneEl.value || (panel.batchMeta || {}).scene_type || "");
    panelMetaSceneEl.textContent = "";
    var blank = document.createElement("option");
    blank.value = "";
    blank.textContent = "未分类";
    panelMetaSceneEl.appendChild(blank);
    panel.scenes.forEach(function (name) {
      var option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      panelMetaSceneEl.appendChild(option);
    });
    if (current && panel.scenes.indexOf(current) < 0) {
      var extra = document.createElement("option");
      extra.value = current;
      extra.textContent = current;
      panelMetaSceneEl.appendChild(extra);
    }
    panelMetaSceneEl.value = current;
  }

  function loadScenes() {
    if (panel.scenes.length) return Promise.resolve(panel.scenes);
    return hostCall("meta.scenes", {}).then(function (result) {
      var rows = (result && Array.isArray(result.scenes)) ? result.scenes : [];
      panel.scenes = rows.map(function (row) { return String((row && row.name) || ""); })
        .filter(Boolean);
      renderSceneOptions();
      return panel.scenes;
    }).catch(function (error) {
      dockWarn("场景表没拉下来：" + ((error && error.message) || "未知原因"), errorDetail(error));
      return [];
    });
  }

  // ---------- 学校字典：题目只存 school_id，校名一律回字典查 ----------

  function setSchoolError(text) {
    if (panelSchoolErrorEl) {
      var message = String(text || "");
      panelSchoolErrorEl.textContent = message;
      panelSchoolErrorEl.hidden = !message;
    }
    if (panelSchoolInputEl) {
      // 简称撞车时输入框当场爆红：CSS 只认 aria-invalid 与 .is-invalid 两种记号。
      panelSchoolInputEl.setAttribute("aria-invalid", text ? "true" : "false");
      panelSchoolInputEl.classList.toggle("is-invalid", Boolean(text));
    }
  }

  function schoolChip(record) {
    var shortName = String(record.short_name || record.full_name || "");
    var chip = el("span", "ep-school");
    chip.setAttribute("data-school-id", String(record.id || ""));
    chip.setAttribute("title", String(record.full_name || shortName));
    chip.appendChild(el("span", "ep-school-name", shortName));
    var remove = el("button", "ep-school-x", "×");
    remove.type = "button";
    remove.setAttribute("aria-label", "去掉 " + shortName);
    remove.addEventListener("click", function () {
      panel.schools = panel.schools.filter(function (item) {
        return String(item.id || "") !== String(record.id || "");
      });
      // 老师亲手摘掉的，旧回执不许把它请回来。
      panel.schoolDropped[String(record.id || "")] = true;
      delete panel.schoolAdded[String(record.id || "")];
      renderSchools();
      queueMetaSync();
    });
    chip.appendChild(remove);
    return chip;
  }

  /** 明细学校胶囊：主体填了才冒出来；点 × 去掉一所。 */
  function renderSchools() {
    if (!panelMetaSchoolsEl || !panelSchoolListEl) return;
    var body = panelMetaBodyEl ? String(panelMetaBodyEl.value || "").trim() : "";
    panelMetaSchoolsEl.hidden = !body;
    panelSchoolListEl.textContent = "";
    panel.schools.forEach(function (record) {
      panelSchoolListEl.appendChild(schoolChip(record || {}));
    });
  }

  function hideSchoolMenu() {
    if (panelSchoolMenuEl) panelSchoolMenuEl.hidden = true;
    if (panelSchoolInputEl) panelSchoolInputEl.setAttribute("aria-expanded", "false");
  }

  function menuItem(text, hint) {
    var item = el("button", "ep-menu-item");
    item.type = "button";
    item.setAttribute("role", "option");
    item.appendChild(el("span", "ep-menu-text", text));
    if (hint) item.appendChild(el("span", "ep-menu-hint", hint));
    return item;
  }

  function renderSchoolMenu(matches, query) {
    if (!panelSchoolMenuEl) return;
    panelSchoolMenuEl.textContent = "";
    var added = {};
    panel.schools.forEach(function (item) { added[String(item.id || "")] = true; });
    var visible = (matches || []).filter(function (record) {
      return record && record.id && !added[String(record.id)];
    });
    visible.forEach(function (record) {
      var shortName = String(record.short_name || record.full_name || "");
      var item = menuItem(shortName, String(record.full_name || ""));
      item.setAttribute("data-school-id", String(record.id));
      item.addEventListener("mousedown", function (event) {
        // mousedown 而不是 click：input 失焦会先把菜单收掉，click 就永远等不到。
        event.preventDefault();
        addSchoolRecord(record);
        if (panelSchoolInputEl) panelSchoolInputEl.value = "";
        hideSchoolMenu();
        setSchoolError("");
      });
      panelSchoolMenuEl.appendChild(item);
    });
    if (query) {
      var create = menuItem("＋ 新建学校「" + query + "」", "AI 补全全称后确认");
      create.setAttribute("data-school-create", query);
      create.addEventListener("mousedown", function (event) {
        event.preventDefault();
        hideSchoolMenu();
        requestSchoolSuggest(query);
      });
      panelSchoolMenuEl.appendChild(create);
    }
    panelSchoolMenuEl.hidden = !panelSchoolMenuEl.children.length;
    if (panelSchoolInputEl) {
      panelSchoolInputEl.setAttribute("aria-expanded", panelSchoolMenuEl.hidden ? "false" : "true");
    }
  }

  function searchSchools(query) {
    return hostCall("meta.schools", { q: String(query || ""), limit: 8 }).then(function (result) {
      var rows = (result && Array.isArray(result.schools)) ? result.schools : [];
      panel.schoolOptions = rows;
      renderSchoolMenu(rows, String(query || "").trim());
      return rows;
    }).catch(function (error) {
      hideSchoolMenu();
      dockWarn("学校字典没查成：" + ((error && error.message) || "未知原因"), errorDetail(error));
      return [];
    });
  }

  function addSchoolRecord(record) {
    if (!record || !record.id) return;
    var id = String(record.id);
    var exists = panel.schools.some(function (item) { return String(item.id || "") === id; });
    if (exists) {
      panelSay("「" + String(record.short_name || record.full_name) + "」已经在明细里了。",
        "warn", "invalid");
      return;
    }
    if (panel.schools.length >= 24) {
      panelSay("明细学校最多 24 所。", "warn", "invalid");
      return;
    }
    panel.schools.push({
      id: id,
      full_name: String(record.full_name || ""),
      short_name: String(record.short_name || record.full_name || "")
    });
    // 本地先记一笔：这所在还没进回执快照，晚到的旧回执不许把它抹掉。
    panel.schoolAdded[id] = true;
    delete panel.schoolDropped[id];
    setSchoolError("");
    renderSchools();
    queueMetaSync();
  }

  function requestSchoolSuggest(shortName) {
    var text = String(shortName || "").trim();
    if (!text) return;
    panel.schoolPending = { short_name: text };
    if (panelSchoolConfirmEl) panelSchoolConfirmEl.hidden = false;
    if (panelSchoolConfirmTextEl) {
      panelSchoolConfirmTextEl.textContent = "字典里没有「" + text + "」，正在让 AI 补全全称…";
    }
    if (panelSchoolFullNameEl) panelSchoolFullNameEl.value = "";
    if (panelSchoolConfirmOkEl) panelSchoolConfirmOkEl.disabled = true;
    var region = panelMetaRegionEl ? String(panelMetaRegionEl.value || "").trim() : "";
    hostCall("meta.school_suggest", { short_name: text, region: region }).then(function (result) {
      var full = String((result && result.full_name) || "");
      if (panelSchoolFullNameEl) panelSchoolFullNameEl.value = full;
      if (panelSchoolConfirmTextEl) {
        panelSchoolConfirmTextEl.textContent = full
          ? "AI 建议全称「" + full + "」，确认无误就建档；不对就手改。"
          : "AI 没补出全称，请手填后确认。";
      }
      if (panelSchoolConfirmOkEl) panelSchoolConfirmOkEl.disabled = false;
    }, function (error) {
      if (panelSchoolConfirmTextEl) {
        panelSchoolConfirmTextEl.textContent = "AI 补全没成功（"
          + ((error && error.message) || "未知原因") + "），请手填全称后确认。";
      }
      if (panelSchoolConfirmOkEl) panelSchoolConfirmOkEl.disabled = false;
      dockWarn("学校全称补全没成功：" + ((error && error.message) || "未知原因"),
        errorDetail(error));
    });
  }

  function cancelSchoolConfirm() {
    panel.schoolPending = null;
    if (panelSchoolConfirmEl) panelSchoolConfirmEl.hidden = true;
    if (panelSchoolFullNameEl) panelSchoolFullNameEl.value = "";
    setSchoolError("");
  }

  function confirmSchoolCreate() {
    var pendingSchool = panel.schoolPending;
    if (!pendingSchool) return;
    var fullName = panelSchoolFullNameEl ? String(panelSchoolFullNameEl.value || "").trim() : "";
    if (!fullName) {
      setSchoolError("请先填学校全称，确认后才建档。");
      if (panelSchoolFullNameEl) panelSchoolFullNameEl.focus();
      return;
    }
    if (panelSchoolConfirmOkEl) panelSchoolConfirmOkEl.disabled = true;
    hostCall("meta.school_create", {
      full_name: fullName,
      short_name: String(pendingSchool.short_name || "")
    }).then(function (result) {
      var record = (result && result.school) || {};
      if (panelSchoolConfirmOkEl) panelSchoolConfirmOkEl.disabled = false;
      if (!record.id) return;
      cancelSchoolConfirm();
      addSchoolRecord(record);
      if (panelSchoolInputEl) panelSchoolInputEl.value = "";
      hideSchoolMenu();
      dock("学校已建档：" + String(record.full_name || "") + "（" + String(record.short_name || "") + "）。");
    }, function (error) {
      if (panelSchoolConfirmOkEl) panelSchoolConfirmOkEl.disabled = false;
      // 简称撞车按底座的原话回显：❌ 简称冲突，已被【哈尔滨师范大学附属中学】占用
      setSchoolError((error && error.message) || "学校建档没成功");
      dockWarn("学校建档没成功：" + ((error && error.message) || "未知原因"),
        errorDetail(error));
    });
  }

  function onSchoolEnter() {
    var query = panelSchoolInputEl ? String(panelSchoolInputEl.value || "").trim() : "";
    if (!query) return;
    var exact = (panel.schoolOptions || []).filter(function (record) {
      return String(record.short_name || "") === query || String(record.full_name || "") === query;
    })[0];
    if (exact) {
      addSchoolRecord(exact);
      panelSchoolInputEl.value = "";
      hideSchoolMenu();
      setSchoolError("");
      return;
    }
    hideSchoolMenu();
    requestSchoolSuggest(query);
  }

  // ---------- 交叉标签：按场景权重排序，模糊匹配，回车即记 ----------

  function hideTagMenu() {
    if (panelTagMenuEl) panelTagMenuEl.hidden = true;
    if (panelMetaExamTypeEl) panelMetaExamTypeEl.setAttribute("aria-expanded", "false");
  }

  function renderTagMenu(items) {
    if (!panelTagMenuEl) return;
    panelTagMenuEl.textContent = "";
    panel.tagOptions = (items || []).slice();
    panel.tagOptions.forEach(function (tag) {
      var item = menuItem(String(tag.name || ""),
        tag.scene_weight ? "本场景常用" : "");
      item.setAttribute("data-tag", String(tag.name || ""));
      item.addEventListener("mousedown", function (event) {
        event.preventDefault();
        pickTag(String(tag.name || ""));
      });
      panelTagMenuEl.appendChild(item);
    });
    panelTagMenuEl.hidden = !panelTagMenuEl.children.length;
    if (panelMetaExamTypeEl) {
      panelMetaExamTypeEl.setAttribute("aria-expanded", panelTagMenuEl.hidden ? "false" : "true");
    }
  }

  // 候选菜单的回执序号：晚到的旧回执不许盖掉刚画出来的新菜单。
  var tagMenuSeq = 0;

  function loadTags(query) {
    var scene = panelMetaSceneEl ? String(panelMetaSceneEl.value || "") : "";
    var seq = tagMenuSeq + 1;
    tagMenuSeq = seq;
    return hostCall("meta.tags", { scene: scene, q: String(query || ""), limit: 8 })
      .then(function (result) {
        if (seq !== tagMenuSeq) return [];
        var rows = (result && Array.isArray(result.tags)) ? result.tags : [];
        renderTagMenu(rows);
        return rows;
      }).catch(function (error) {
        if (seq !== tagMenuSeq) return [];
        hideTagMenu();
        dockWarn("交叉标签没拉下来：" + ((error && error.message) || "未知原因"),
          errorDetail(error));
        return [];
      });
  }

  function pickTag(name) {
    var text = String(name || "").trim();
    if (!text) return;
    if (panelMetaExamTypeEl) panelMetaExamTypeEl.value = text;
    hideTagMenu();
    queueMetaSync();
  }

  function onTagEnter() {
    var text = panelMetaExamTypeEl ? String(panelMetaExamTypeEl.value || "").trim() : "";
    if (!text) return;
    var known = (panel.tagOptions || []).some(function (tag) {
      return String(tag.name || "") === text;
    });
    if (known) {
      hideTagMenu();
      queueMetaSync();
      return;
    }
    var scene = panelMetaSceneEl ? String(panelMetaSceneEl.value || "") : "";
    hostCall("meta.tag_remember", { name: text, scene: scene }).then(function () {
      hideTagMenu();
      dock("新标签「" + text + "」已记进本地标签库，下次打字就会弹出来。", "note");
      queueMetaSync();
    }, function (error) {
      hideTagMenu();
      dockWarn("标签没记进本地库：" + ((error && error.message) || "未知原因"),
        errorDetail(error));
      queueMetaSync();
    });
  }

  // ---------- 标准名：自动拼接 + 手改暂停 + 元数据再动即恢复 ----------

  var stdFlashTimer = 0;

  function setStdMode(manual) {
    panel.stdManual = Boolean(manual);
    var mode = panel.stdManual ? "manual" : "auto";
    if (panelStdNameEl) panelStdNameEl.setAttribute("data-mode", mode);
    if (panelStdHintEl) {
      panelStdHintEl.setAttribute("data-mode", mode);
      panelStdHintEl.textContent = panel.stdManual
        ? "已暂停自动拼接；再动任意元数据即恢复自动重拼。"
        : "自动拼接；手改后暂停联动，再改元数据即恢复。";
    }
  }

  function flashStd() {
    if (!panelStdFlashEl) return;
    panelStdFlashEl.textContent = "已更新";
    panelStdFlashEl.setAttribute("data-show", "true");
    window.clearTimeout(stdFlashTimer);
    stdFlashTimer = window.setTimeout(function () {
      panelStdFlashEl.setAttribute("data-show", "false");
    }, 1400);
  }

  function stdLiveName() {
    var meta = panel.batchMeta || {};
    return standardNameOf({
      year: panelMetaYearEl ? panelMetaYearEl.value : meta.year,
      region: panelMetaRegionEl ? panelMetaRegionEl.value : meta.region,
      body: panelMetaBodyEl ? panelMetaBodyEl.value : meta.body,
      scene_type: panelMetaSceneEl ? panelMetaSceneEl.value : meta.scene_type,
      exam_type: panelMetaExamTypeEl ? panelMetaExamTypeEl.value : meta.exam_type,
      subject: panelMetaSubjectEl ? panelMetaSubjectEl.value : meta.subject
    });
  }

  /** 顶部两行：灰字是原文件名，黑字的标准名跟着元数据实时重拼，手改后停下。 */
  function renderTopLines(options) {
    var card = panel.batchCard || {};
    var meta = panel.batchMeta || {};
    if (panelSrcNameEl) {
      var name = String(card.source_name || "");
      panelSrcNameEl.textContent = name || "还没有批次";
      panelSrcNameEl.setAttribute("data-name", name);
    }
    if (panelStdNameEl) {
      if (!panel.stdManual) {
        // 自动拼接模式：老师一眼就看见这一批将被叫成什么。
        var standard = stdLiveName();
        panelStdNameEl.value = standard;
        panelStdNameEl.setAttribute("data-standard", standard);
      } else if (!panelStdNameEl.value) {
        panelStdNameEl.value = String(meta.standard_name || stdLiveName());
      }
      panelStdNameEl.setAttribute("data-mode", panel.stdManual ? "manual" : "auto");
    }
    renderFoldSummary();
    if (options && options.flash) flashStd();
  }

  /** 底座回执里的标准名与模式是最终事实：以它对齐一次，别让本地猜。 */
  function applyStdFromMeta(flash) {
    var meta = panel.batchMeta || {};
    setStdMode(String(meta.name_mode || "auto") === "manual");
    if (panelStdNameEl) {
      var name = String(meta.standard_name || stdLiveName());
      if (!panel.stdManual || !panelStdNameEl.value) panelStdNameEl.value = name;
      panelStdNameEl.setAttribute("data-standard", name);
    }
    if (flash) flashStd();
  }

  /**
   * 回执只当加法：老师刚建档的学校还没进快照，晚到的旧回执不许把它抹掉；
   * 老师亲手摘掉的也不许被旧回执请回来。
   */
  function mergeSchools(details) {
    var rows = [];
    var known = {};
    (details || []).forEach(function (item) {
      var id = String((item && item.id) || "");
      if (!id || panel.schoolDropped[id]) return;
      known[id] = true;
      rows.push({
        id: id,
        full_name: String((item && item.full_name) || ""),
        short_name: String((item && (item.short_name || item.full_name)) || "")
      });
    });
    panel.schools.forEach(function (item) {
      var id = String(item.id || "");
      if (!id || known[id] || !panel.schoolAdded[id]) return;
      known[id] = true;
      rows.push({
        id: id,
        full_name: String(item.full_name || ""),
        short_name: String(item.short_name || item.full_name || "")
      });
    });
    return rows;
  }

  function renderBatchMeta() {
    var meta = panel.batchMeta || {};
    // 换批就换一套本地记账：上一批的加与减跟这一批无关。
    if (String(panel.batchId || "") !== String(panel.schoolBatchId || "")) {
      panel.schoolBatchId = String(panel.batchId || "");
      panel.schoolAdded = {};
      panel.schoolDropped = {};
    }
    if (panelMetaYearEl) panelMetaYearEl.value = meta.year == null ? "" : String(meta.year);
    if (panelMetaRegionEl) panelMetaRegionEl.value = String(meta.region || "");
    if (panelMetaBodyEl) panelMetaBodyEl.value = String(meta.body || "");
    if (panelMetaExamTypeEl) panelMetaExamTypeEl.value = String(meta.exam_type || "");
    if (panelMetaSubjectEl) panelMetaSubjectEl.value = String(meta.subject || "");
    renderSceneOptions();
    if (panelMetaSceneEl) panelMetaSceneEl.value = String(meta.scene_type || "");
    var details = Array.isArray(meta.school_details) ? meta.school_details : [];
    panel.schools = mergeSchools(details);
    panel.lastBody = String(meta.body || "");
    setStdMode(String(meta.name_mode || "auto") === "manual");
    renderSchools();
    renderTopLines();
    applyStdFromMeta(false);
    syncSourceFields();
  }

  /**
   * 同步回来的只刷「看得见的部分」，**不碰老师正在打的字**——
   * 上一笔同步的回执晚到时，照抄回执会把老师新打的字抹掉。
   */
  function renderMetaView() {
    var meta = panel.batchMeta || {};
    if (Array.isArray(meta.school_details)) {
      panel.schools = mergeSchools(meta.school_details);
    }
    if (panelMetaSceneEl && String(panelMetaSceneEl.value || "") !== String(meta.scene_type || "")) {
      panelMetaSceneEl.value = String(meta.scene_type || "");
    }
    renderSchools();
    renderTopLines();
    applyStdFromMeta(true);
    syncSourceFields();
  }

  var metaSyncTimer = 0;

  /** 改一个公共字段 → 整批同步。攒 400ms 再发，免得连打五个字段发五回。 */
  function queueMetaSync() {
    window.clearTimeout(metaSyncTimer);
    metaSyncTimer = window.setTimeout(applyMetaSync, 400);
  }

  function applyMetaSync() {
    if (!panel.batchId) return Promise.resolve(null);
    var payload = {
      batch_id: panel.batchId,
      year: panelMetaYearEl ? String(panelMetaYearEl.value || "").trim() : "",
      region: panelMetaRegionEl ? String(panelMetaRegionEl.value || "").trim() : "",
      body: panelMetaBodyEl ? String(panelMetaBodyEl.value || "").trim() : "",
      scene_type: panelMetaSceneEl ? String(panelMetaSceneEl.value || "").trim() : "",
      exam_type: panelMetaExamTypeEl ? String(panelMetaExamTypeEl.value || "").trim() : "",
      subject: panelMetaSubjectEl ? String(panelMetaSubjectEl.value || "").trim() : "",
      // 题目只认字典 ID：名字一个字节都不往题目里写。
      school_ids: panel.schools.map(function (item) { return String(item.id || ""); })
        .filter(Boolean),
      name_mode: panel.stdManual ? "manual" : "auto",
      standard_name: panelStdNameEl ? String(panelStdNameEl.value || "").trim() : ""
    };
    panel.metaSyncing = true;
    return hostCall("pending.set_meta", payload).then(function (result) {
      panel.metaSyncing = false;
      panel.batchMeta = (result && result.meta) || payload;
      panel.batchCard = (result && result.batch) || panel.batchCard;
      renderMetaView();
      var synced = Number(result && result.synced) || 0;
      var patched = Number(result && result.patched) || 0;
      var skipped = Number(result && result.skipped) || 0;
      var warnings = (result && Array.isArray(result.warnings)) ? result.warnings : [];
      warnings.slice(0, 3).forEach(function (text) { dockWarn(text); });
      panelSay("公共元数据已同步：" + synced + " 道题"
        + (patched ? "，主库补写 " + patched + " 道" : "")
        + (skipped ? "，" + skipped + " 道没同步上" : "") + "。",
        skipped ? "warn" : "ok", "meta");
      return result;
    }).catch(function (error) {
      panel.metaSyncing = false;
      var text = (error && error.message) || "未知原因";
      panelSay("公共元数据没同步上：" + text, "error", "failed");
      dockWarn("公共元数据没同步上：" + text, errorDetail(error));
      return null;
    });
  }

  /** 主体换了一个：历史里记过同一主体的，按字典把学校 ID 自动带出来。 */
  function hydrateGroupSchools(names) {
    var wanted = (names || []).map(function (name) { return String(name || "").trim(); })
      .filter(Boolean);
    if (!wanted.length) return Promise.resolve(null);
    return wanted.reduce(function (chain, name) {
      return chain.then(function () {
        return hostCall("meta.schools", { q: name, limit: 5 }).then(function (result) {
          var rows = (result && Array.isArray(result.schools)) ? result.schools : [];
          var hit = rows.filter(function (record) {
            return String(record.short_name || "") === name || String(record.full_name || "") === name;
          })[0];
          if (hit) addSchoolRecord(hit);
          return null;
        }, function () { return null; });
      });
    }, Promise.resolve(null)).then(function () {
      renderSchools();
      return null;
    });
  }

  function onMetaFieldChange() {
    var body = panelMetaBodyEl ? String(panelMetaBodyEl.value || "").trim() : "";
    if (body !== panel.lastBody) {
      panel.lastBody = body;
      var known = panel.groups ? panel.groups[body] : null;
      if (known && known.length) hydrateGroupSchools(known);
    }
    // 元数据一动，手改过的标准名立刻交回自动拼接（军令 #28 双向联动）。
    if (panel.stdManual) setStdMode(false);
    renderSchools();
    renderTopLines({ flash: true });
    queueMetaSync();
  }

  function onSceneChange() {
    if (panel.stdManual) setStdMode(false);
    renderTopLines({ flash: true });
    // 场景一换，交叉标签的排序与候选立刻跟着换。
    loadTags(panelMetaExamTypeEl ? String(panelMetaExamTypeEl.value || "").trim() : "");
    queueMetaSync();
  }

  /** 老师手改标准名：自动拼接当场暂停，改完这一段就以手改为准。 */
  function onStdInput() {
    setStdMode(true);
    window.clearTimeout(metaSyncTimer);
    metaSyncTimer = window.setTimeout(applyMetaSync, 600);
  }

  /** 取这一批的公共元数据：批次卡片里就带着 meta。 */
  function loadBatchMeta(batchId) {
    var id = String(batchId || "");
    panel.batchId = id;
    if (!id) {
      panel.batchCard = null;
      panel.batchMeta = {};
      panel.schools = [];
      renderBatchMeta();
      return Promise.resolve(null);
    }
    return hostCall("pending.batch_list", {}).then(function (result) {
      var cards = (result && Array.isArray(result.batches)) ? result.batches : [];
      var card = null;
      for (var index = 0; index < cards.length; index += 1) {
        if (String(cards[index].batch_id || "") === id) { card = cards[index]; break; }
      }
      if (!card) return null;
      panel.batchCard = card;
      panel.batchMeta = (card.meta && typeof card.meta === "object") ? card.meta : {};
      renderBatchMeta();
      return card;
    }).catch(function () {
      return null;
    });
  }

  /** 换批次：把公共元数据面板切到这一批。 */
  function syncBatchContext(batchId) {
    var id = String(batchId || "");
    if (id === panel.batchId && panel.batchCard) return Promise.resolve(null);
    return loadBatchMeta(id);
  }

  // ---------- 接收区：拖入 / 粘贴 / 截屏 ----------

  // OCR 可能跑很久：宿主那条 HTTP 默认 20 秒就超时，这里给足时间。
  var INGEST_TIMEOUT_MS = 180000;

  function fileEntry(file, fallbackName) {
    return new Promise(function (resolve) {
      var name = String((file && file.name) || "") || String(fallbackName || "");
      if (!name) { resolve(null); return; }
      var reader = new FileReader();
      reader.onerror = function () { resolve(null); };
      reader.onload = function () {
        resolve({ name: name, data_url: String(reader.result || "") });
      };
      reader.readAsDataURL(file);
    });
  }


  /** 文件交给宿主建批次：识别与题库都在宿主那边，插件只递字节。 */
  function ingestEntries(entries) {
    var files = (entries || []).filter(function (entry) { return entry && entry.data_url; });
    if (!files.length) return Promise.resolve(null);
    return hostCall("ingest.files", { files: files }, INGEST_TIMEOUT_MS).then(function (result) {
      var saved = Array.isArray(result && result.saved_ids) ? result.saved_ids.length : 0;
      var ids = Array.isArray(result && result.batch_ids)
        ? result.batch_ids
        : (result && result.batch_id ? [result.batch_id] : []);
      // 一个文件一个批次：拖 9 份就是 9 个批次，各认各的。
      var label = ids.length > 1
        ? ids.length + " 个批次（" + ids.join("、") + "）"
        : "批次 " + (ids[0] || "");
      // parsing=true：批次已经立起来了，识别在后台跑。
      if (result && result.parsing) {
        dock("已收下 " + files.length + " 份，分成 " + label + "，正在后台解析。");
        return result;
      }
      dock("已收下 " + files.length + " 个文件，认出 " + saved + " 道题，" + label + "。");
      return result;
    }).catch(function (error) {
      var text = (error && error.message) || "未知原因";
      panelSay("文件没收进来：" + text, "error", "failed");
      dockWarn("文件没收进来：" + text, errorDetail(error));
      return null;
    });
  }

  function hasFiles(event) {
    var transfer = event && event.dataTransfer;
    if (!transfer) return false;
    if (transfer.items && transfer.items.length) {
      for (var index = 0; index < transfer.items.length; index += 1) {
        if (transfer.items[index].kind === "file") return true;
      }
      return false;
    }
    return Boolean(transfer.files && transfer.files.length);
  }

  function isTypingTarget(target) {
    if (!target || !target.tagName) return false;
    var tag = String(target.tagName).toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select") return true;
    return Boolean(target.isContentEditable);
  }

  /**
   * 剪贴板里的图片：``items`` 与 ``files`` 两路都取，同一张只留一份。
   *
   * 只认 ``items`` 不够：有些环境贴图时 ``items`` 是空的，只有 ``files`` 里有货；
   * 两路都取，粘贴才不会时灵时不灵。
   */
  function clipboardImageFiles(event) {
    var data = event && event.clipboardData;
    if (!data) return [];
    var files = [];
    var seen = [];
    function push(file) {
      if (!file) return;
      var type = String(file.type || "").toLowerCase();
      if (type.indexOf("image/") !== 0) return;
      var name = String(file.name || "");
      var size = Number(file.size || 0);
      for (var i = 0; i < seen.length; i += 1) {
        if (seen[i].type === type && seen[i].name === name && seen[i].size === size) return;
      }
      seen.push({ type: type, name: name, size: size });
      files.push(file);
    }
    var items = data.items || [];
    for (var index = 0; index < items.length; index += 1) {
      if (items[index].kind !== "file") continue;
      var file = items[index].getAsFile();
      if (file) push(file);
    }
    var listed = data.files || [];
    for (var j = 0; j < listed.length; j += 1) push(listed[j]);
    return files;
  }

  function markDrop(on) {
    if (basketEl) basketEl.classList.toggle("is-over", Boolean(on));
    if (panelIntakeEl) panelIntakeEl.classList.toggle("is-over", Boolean(on));
  }

  // ---------- 文件收集筐（军令 #27）----------
  // 收集筐是这一屏唯一的收件处：拖入、粘贴、点选都先落筐，
  // 底部的【开始解析】才是唯一的建批次入口——老师点它之前，底座不会多出一个批次。

  var basketSeq = 0;
  var basketBusy = false;
  // 单列列表里的小缩略图：44px 见方，左边一列图标、中间文件名、右边红 ×。
  var THUMB_SIDE = 44;

  /** 剪贴板里的图没有文件名时补一个：分拣只看后缀，名字不能空。 */
  function basketName(file) {
    var name = String((file && file.name) || "");
    if (name) return name;
    var type = String((file && file.type) || "").toLowerCase();
    if (type.indexOf("image/") === 0) {
      if (type.indexOf("jpeg") >= 0 || type.indexOf("jpg") >= 0) return "截图.jpg";
      if (type.indexOf("webp") >= 0) return "截图.webp";
      return "截图.png";
    }
    return "粘贴的文件";
  }

  /** 收一批文件进筐；``.zip`` 是插件包，走安装那条道，静默忽略。 */
  function basketAdd(fileList) {
    var files = Array.prototype.slice.call(fileList || []);
    var added = 0;
    files.forEach(function (file) {
      if (!file) return;
      var name = basketName(file);
      if (name.toLowerCase().slice(-4) === ".zip") return;
      var entry = {
        id: "b" + (basketSeq += 1),
        name: name,
        type: String(file.type || ""),
        size: Number(file.size || 0),
        file: file,
        bitmap: null,
        thumb: null
      };
      state.basket.push(entry);
      if (entry.type.indexOf("image/") === 0) decodeThumb(entry);
      added += 1;
    });
    if (added) {
      renderBasket();
      dock("收集筐里已有 " + state.basket.length + " 份文件，点【开始解析】才建批次。");
    }
    return added;
  }

  /**
   * 缩略图画在 canvas 上，不走 ``<img src=blob:...>``。
   *
   * 插件沙箱的 CSP 是 ``img-src 'self' <底座源>``：blob: 与 data: 的图片全被拦掉，
   * 屏幕上只会剩一只 200×200 的空框——看着像有缩略图，其实什么都没显示。
   * ``createImageBitmap`` 是插件自己把字节解成位图，不发请求、不受 CSP 管，
   * 画布上的像素是货真价实的题面。
   */
  function decodeThumb(entry) {
    if (!entry.file || typeof window.createImageBitmap !== "function") return;
    window.createImageBitmap(entry.file).then(function (bitmap) {
      entry.bitmap = bitmap;
      paintThumb(entry);
    }, function () {
      // 解不开（格式不支持）就只留文件名，不装作有预览
    });
  }

  function paintThumb(entry) {
    var node = entry.thumb;
    if (!node || !entry.bitmap) return;
    var width = entry.bitmap.width || 0;
    var height = entry.bitmap.height || 0;
    if (!width || !height) return;
    var ctx = node.getContext("2d");
    if (!ctx) return;
    var scale = Math.min(THUMB_SIDE / width, THUMB_SIDE / height);
    var drawW = Math.max(1, Math.round(width * scale));
    var drawH = Math.max(1, Math.round(height * scale));
    ctx.clearRect(0, 0, THUMB_SIDE, THUMB_SIDE);
    ctx.drawImage(entry.bitmap, (THUMB_SIDE - drawW) / 2, (THUMB_SIDE - drawH) / 2, drawW, drawH);
  }

  /** 文件类型角标：图片走缩略图，文档按后缀给一个短标签（PDF / DOCX / TEX …）。 */
  function fileBadge(name) {
    var text = String(name || "");
    var dot = text.lastIndexOf(".");
    var ext = dot < 0 ? "" : text.slice(dot + 1).toUpperCase();
    if (!ext) return "FILE";
    return ext.length > 5 ? ext.slice(0, 5) : ext;
  }

  function renderBasket() {
    if (!basketListEl) return;
    basketListEl.textContent = "";
    state.basket.forEach(function (entry) {
      var isImage = entry.type.indexOf("image/") === 0;
      var item = el("li", "ed-basket-item");
      item.setAttribute("data-kind", isImage ? "image" : "file");
      item.setAttribute("data-name", entry.name);
      if (isImage) {
        // 图就走 44px 缩略图：左边一眼认出是哪道题。
        var thumb = document.createElement("canvas");
        thumb.className = "ed-basket-thumb";
        thumb.width = THUMB_SIDE;
        thumb.height = THUMB_SIDE;
        thumb.setAttribute("data-thumb", "1");
        thumb.setAttribute("aria-label", "待解析图片预览：" + entry.name);
        item.appendChild(thumb);
        entry.thumb = thumb;
        paintThumb(entry);
      } else {
        // 文档给一张带后缀的图标，不装缩略图，也不留空框。
        var icon = el("span", "ed-basket-icon");
        icon.setAttribute("data-ext", fileBadge(entry.name));
        icon.setAttribute("aria-hidden", "true");
        icon.appendChild(el("span", "ed-basket-icon-ext", fileBadge(entry.name)));
        item.appendChild(icon);
      }
      // 中间文件名：再长也只占一行，超出自动省略，悬停看全名。
      var nameEl = el("span", "ed-basket-name", entry.name);
      nameEl.title = entry.name;
      item.appendChild(nameEl);
      var remove = el("button", "ed-basket-x", "×");
      remove.type = "button";
      remove.setAttribute("aria-label", "移除 " + entry.name);
      remove.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        basketRemove(entry.id);
      });
      item.appendChild(remove);
      basketListEl.appendChild(item);
    });
    if (basketEmptyEl) basketEmptyEl.hidden = state.basket.length > 0;
    if (basketFootEl) basketFootEl.hidden = state.basket.length === 0;
    if (basketGoEl && !basketBusy) {
      basketGoEl.textContent = "🚀 开始解析 (" + state.basket.length + " 个文件)";
    }
    if (basketEl) basketEl.setAttribute("data-count", String(state.basket.length));
  }

  function basketRemove(id) {
    var index = -1;
    for (var i = 0; i < state.basket.length; i += 1) {
      if (state.basket[i].id === id) { index = i; break; }
    }
    if (index < 0) return;
    var entry = state.basket.splice(index, 1)[0];
    if (entry.bitmap && typeof entry.bitmap.close === "function") entry.bitmap.close();
    renderBasket();
  }

  function basketClear() {
    state.basket.forEach(function (entry) {
      if (entry.bitmap && typeof entry.bitmap.close === "function") entry.bitmap.close();
    });
    state.basket = [];
    renderBasket();
  }

  function setBasketBusy(on) {
    if (!basketGoEl) return;
    basketGoEl.disabled = Boolean(on);
    if (on) {
      basketGoEl.setAttribute("aria-busy", "true");
      basketGoEl.textContent = "🚀 正在解析…";
    } else {
      basketGoEl.removeAttribute("aria-busy");
    }
  }

  /** 【开始解析】：筐里有多少交多少，宿主那边立批次、后台跑识别。 */
  function basketGo() {
    if (!state.basket.length || basketBusy) return Promise.resolve(null);
    basketBusy = true;
    setBasketBusy(true);
    return Promise.all(state.basket.map(function (entry) {
      // 剪贴板里的图未必带文件名，补上筐里显示的那个，解析才认得出它。
      return fileEntry(entry.file, entry.name);
    })).then(function (payloads) {
      return ingestEntries(payloads.filter(Boolean));
    }).then(function (result) {
      if (result) {
        basketClear();
        refreshBatches();
      }
      basketBusy = false;
      setBasketBusy(false);
      renderBasket();
      return result;
    }, function (error) {
      basketBusy = false;
      setBasketBusy(false);
      renderBasket();
      dockWarn("开始解析失败：" + ((error && error.message) || "未知原因"), errorDetail(error));
      return null;
    });
  }

  /** 面板实例（在右栏那张 iframe 里）把文件交给宿主，由宿主转进画布的筐。 */
  function collectToCanvas(files) {
    var list = Array.prototype.slice.call(files || []);
    if (!list.length) return;
    publish("editor.collect_files", { files: list });
  }

  var intakeWired = false;

  /**
   * 接收区接线。
   *
   * 拖放与粘贴事件**不跨 iframe 边界**——宿主壳收不到插件框里发生的拖放，
   * 所以插件这一侧必须自己接住，再把字节转给宿主。
   *
   * 画布实例与辅助栏实例是两张 iframe：筐只住在画布里，
   * 面板那侧收到的文件一律转交宿主，由宿主送进画布的筐（插件两帧不直连）。
   */
  function wireIntake() {
    if (intakeWired) return;
    intakeWired = true;
    var inCanvas = state.slot === "stage.center";

    if (inCanvas && basketEl) {
      ["dragenter", "dragover"].forEach(function (type) {
        basketEl.addEventListener(type, function (event) {
          if (!hasFiles(event)) return;
          event.preventDefault();
          event.stopPropagation();
          if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
          markDrop(true);
        });
      });
      basketEl.addEventListener("dragleave", function (event) {
        event.preventDefault();
        markDrop(false);
      });
      basketEl.addEventListener("drop", function (event) {
        event.preventDefault();
        event.stopPropagation();
        markDrop(false);
        var files = event.dataTransfer && event.dataTransfer.files;
        if (files && files.length) basketAdd(files);
      });
      // 点框选文件：筐里的移除钮与【开始解析】不触发它
      basketEl.addEventListener("click", function (event) {
        var hit = event.target && event.target.closest
          ? event.target.closest(".ed-basket-x, .ed-basket-go") : null;
        if (hit) return;
        if (basketFileEl) basketFileEl.click();
      });
      basketEl.addEventListener("keydown", function (event) {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        if (basketFileEl) basketFileEl.click();
      });
    }
    if (inCanvas && basketFileEl) {
      basketFileEl.addEventListener("change", function () {
        var files = basketFileEl.files;
        if (files && files.length) basketAdd(files);
        basketFileEl.value = "";
      });
    }
    if (inCanvas && basketGoEl) {
      basketGoEl.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        basketGo();
      });
    }
    // 画布整屏都收：拖到筐旁边的空白处也算落进筐里
    if (inCanvas && root) {
      root.addEventListener("dragover", function (event) {
        if (!hasFiles(event)) return;
        event.preventDefault();
      });
      root.addEventListener("drop", function (event) {
        if (!hasFiles(event)) return;
        if (basketEl && basketEl.contains(event.target)) return;
        if (crop) return;   // 切图台正在等图，别把它当成新卷子
        event.preventDefault();
        var files = event.dataTransfer && event.dataTransfer.files;
        if (files && files.length) basketAdd(files);
      });
    }
    // Ctrl+V 粘贴截图 → 进筐，不直接建批次
    window.addEventListener("paste", function (event) {
      if (crop) return;   // 切图台正在等图，别把它当成新卷子
      if (isTypingTarget(event.target)) return;
      var files = clipboardImageFiles(event);
      if (!files.length) return;
      event.preventDefault();
      if (inCanvas) basketAdd(files);
      else collectToCanvas(files);
    });
    // 辅助栏的接收区（在右栏那张 iframe 里）：文件转交宿主，再送进画布的筐。
    // 只在面板实例里接：画布实例那边的 #epIntake 是收着的，绑了也是死代码。
    if (!inCanvas && panelIntakeEl) {
      ["dragenter", "dragover"].forEach(function (type) {
        panelIntakeEl.addEventListener(type, function (event) {
          if (!hasFiles(event)) return;
          event.preventDefault();
          event.stopPropagation();
          if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
          markDrop(true);
        });
      });
      panelIntakeEl.addEventListener("dragleave", function (event) {
        event.preventDefault();
        markDrop(false);
      });
      panelIntakeEl.addEventListener("drop", function (event) {
        event.preventDefault();
        event.stopPropagation();
        markDrop(false);
        var files = event.dataTransfer && event.dataTransfer.files;
        if (files && files.length) collectToCanvas(files);
      });
    }
    if (inCanvas) renderBasket();
  }

  // ---------- 三栏渲染 ----------

  /** 这一题自己的配图：真题看 images，假数据才退到 dev 里的占位图。 */
  function itemImage(item) {
    var images = (item.question && Array.isArray(item.question.images)) ? item.question.images : [];
    for (var index = 0; index < images.length; index += 1) {
      var uri = safeAssetUri(images[index] && images[index].uri);
      if (uri) return { uri: uri, id: String((images[index] && images[index].id) || "") };
    }
    var demo = safeAssetUri(item.dev && item.dev.image_uri);
    return demo ? { uri: demo, id: "" } : null;
  }

  function renderImageCell(item, index) {
    var cell = el("div", "ed-img-cell");
    cell.setAttribute("role", "listitem");
    cell.setAttribute("data-index", String(index));
    var picture = itemImage(item);
    var frame = el("div", "ed-img-frame");
    if (picture) {
      var img = document.createElement("img");
      img.src = picture.uri;
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
    } else {
      frame.appendChild(el("p", "ed-img-missing", "本题没有配图。框选取图可以把卷子上的这一题裁下来。"));
    }
    cell.appendChild(frame);
    // 切图台入口：点开就是一只跟着鼠标的放大镜，拖拽框选，左键松开切完。
    var tools = el("div", "ed-img-tools");
    var cropBtn = el("button", "ed-img-crop-btn", picture ? "重新框选" : "框选取图");
    cropBtn.type = "button";
    cropBtn.setAttribute("data-index", String(index));
    cropBtn.setAttribute("aria-label",
      (picture ? "重新框选第 " : "框选取图第 ") + (index + 1) + " 题的配图");
    cropBtn.addEventListener("click", function () { openCrop(item, index); });
    tools.appendChild(cropBtn);
    cell.appendChild(tools);
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

  // ---------- 左栏切图：圆形放大镜 + 中心十字准星 ----------
  //
  // 放大镜是从宿主壳那套截屏交互里原样搬过来的：半径 104、8 倍、关平滑看像素，
  // 镜心一根红十字。只是它不再跟着屏幕走，而是跟着老师在左栏那张图上的鼠标走；
  // 左键松开，框选完成，镜子消失。
  //
  // 像素级精准的前提是画布干净：沙箱插件画不了宿主原点的图——画布会被污染，
  // toDataURL 直接抛 SecurityError。所以已有的配图走宿主 asset.read 递 data URL，
  // 老师现贴的图走 File：两条路拿到的都是不带污点的字节。
  var CROP_RADIUS = 104;     // 放大镜半径（CSS 像素）
  var CROP_ZOOM = 8;         // 放大倍数
  var CROP_MIN_SIDE = 4;     // 最小选区边长（CSS 像素）
  var crop = null;
  var lensCanvas = null;

  function cropAssetId() {
    return "img_crop_" + Math.random().toString(36).slice(2, 10);
  }

  /** data URL → Blob。插件侧禁用 fetch（契约红线），只能用 atob 造字节。 */
  function dataUrlToBlob(dataUrl, mime) {
    var text = String(dataUrl || "");
    var comma = text.indexOf(",");
    var payload = comma >= 0 ? text.slice(comma + 1) : "";
    var binary = window.atob(payload);
    var bytes = new Uint8Array(binary.length);
    for (var index = 0; index < binary.length; index += 1) {
      bytes[index] = binary.charCodeAt(index);
    }
    return new Blob([bytes], { type: mime || "image/png" });
  }

  function cropFiles(event) {
    var data = event && event.clipboardData;
    if (!data) return [];
    var files = [];
    var items = data.items || [];
    for (var index = 0; index < items.length; index += 1) {
      if (items[index].kind !== "file") continue;
      var file = items[index].getAsFile();
      if (file && String(file.type || "").indexOf("image/") === 0) files.push(file);
    }
    var listed = data.files || [];
    for (var j = 0; j < listed.length; j += 1) {
      var each = listed[j];
      if (each && String(each.type || "").indexOf("image/") === 0) files.push(each);
    }
    return files;
  }

  /** 切图台：左栏那一格变成一块画布，鼠标变十字，旁边跟一只放大镜。 */
  function openCrop(item, index) {
    closeCrop();
    // closeCrop 会整屏重绘，格子节点换了新的：这里按序号重新找，别拿旧的。
    var cell = document.querySelector('.ed-img-cell[data-index="' + index + '"]');
    if (!cell) return;
    var session = {
      item: item,
      index: index,
      cell: cell,
      bitmap: null,
      width: 0,
      height: 0,
      scale: 1,
      dpr: 1,
      rect: null,
      dragging: false,
      start: null,
      pointer: { x: 0, y: 0 },
      canvas: null,
      ctx: null,
      lens: null,
      lctx: null,
      hint: null
    };
    crop = session;
    var hint = el("p", "ed-crop-hint", "正在取图…");
    session.hint = hint;
    cell.appendChild(hint);
    // 窗口级监听先绑上：图还没取回来的时候，粘贴与拖放也得能接住。
    window.addEventListener("mousemove", onCropMove, true);
    window.addEventListener("mouseup", onCropUp, true);
    window.addEventListener("keydown", onCropKey, true);
    window.addEventListener("paste", onCropPaste, true);
    window.addEventListener("dragover", onCropDragOver, true);
    window.addEventListener("drop", onCropDrop, true);
    window.addEventListener("resize", onCropResize);
    var picture = itemImage(item);
    var managed = picture && picture.uri.indexOf("/static/") === 0;
    if (!managed) {
      // 没有现成的托管图：等老师把卷子上的这一页贴进来或拖进来。
      mountCropSurface(session, null);
      return;
    }
    hostCall("asset.read", { uri: picture.uri }).then(function (result) {
      var blob = dataUrlToBlob(result && result.data_url, result && result.mime);
      return window.createImageBitmap(blob);
    }).then(function (bitmap) {
      mountCropSurface(session, bitmap);
    }, function (error) {
      hint.textContent = "这张图取不出来（" + ((error && error.message) || "未知原因") + "）。";
    });
  }

  /** 收摊：放大镜撤掉，画布撤掉，这一格回到普通态。 */
  function closeCrop() {
    if (!crop) return;
    var session = crop;
    crop = null;
    window.removeEventListener("mousemove", onCropMove, true);
    window.removeEventListener("mouseup", onCropUp, true);
    window.removeEventListener("keydown", onCropKey, true);
    window.removeEventListener("paste", onCropPaste, true);
    window.removeEventListener("dragover", onCropDragOver, true);
    window.removeEventListener("drop", onCropDrop, true);
    window.removeEventListener("resize", onCropResize);
    if (session.canvas && session.canvas.parentNode) {
      session.canvas.parentNode.removeChild(session.canvas);
    }
    if (session.hint && session.hint.parentNode) {
      session.hint.parentNode.removeChild(session.hint);
    }
    if (lensCanvas) {
      if (lensCanvas.parentNode) lensCanvas.parentNode.removeChild(lensCanvas);
      lensCanvas = null;
    }
    if (session.bitmap && typeof session.bitmap.close === "function") {
      session.bitmap.close();
    }
    renderAll();
  }

  function mountCropSurface(session, bitmap) {
    if (bitmap) {
      if (session.bitmap && typeof session.bitmap.close === "function") session.bitmap.close();
      session.bitmap = bitmap;
      session.width = bitmap.width;
      session.height = bitmap.height;
    }
    if (!session.canvas) {
      var canvas = document.createElement("canvas");
      canvas.className = "ed-crop-canvas";
      canvas.setAttribute("aria-label", "切图台：拖拽框选，左键松开切图");
      session.canvas = canvas;
      session.ctx = canvas.getContext("2d");
      canvas.addEventListener("mousedown", function (event) {
        if (event.button !== 0 || !session.bitmap) return;
        event.preventDefault();
        session.dragging = true;
        session.start = cropPoint(session, event.clientX, event.clientY);
        session.rect = null;
      });
    }
    anchorCrop(session);
    ensureLens();
    session.lctx = lensCanvas.getContext("2d");
    resizeLens();
    session.hint.textContent = bitmap
      ? "移动鼠标看像素，拖拽框选，左键松开切图；Esc 取消。"
      : "把卷子上的这一页 Ctrl+V 贴进来（或拖进来），再拖拽框选。";
  }

  /**
   * 切图台要跟着格子走。
   *
   * 画布上有个 ResizeObserver：切图台一挂上去，格子高度变了，它就排一次整屏重绘，
   * 重绘把格子换成了新的——切图台若还攥着旧格子，画布就掉进了一个没人看得见的
   * 树里（症状：镜子在，格子上的画布不见了）。所以每次重绘后都要把画布与提示
   * 搬回当前这一格。
   *
   * 搬的动作必须和重绘在同一个任务里做完：ResizeObserver 只在帧末比一次尺寸，
   * 中间塌下去又撑回来的那一下它根本看不见——也就不会自己绕成死循环。
   */
  function anchorCrop(session) {
    if (!session) return;
    var cell = document.querySelector('.ed-img-cell[data-index="' + session.index + '"]');
    if (!cell) return;
    var frame = cell.querySelector(".ed-img-frame");
    if (!frame) return;
    var img = frame.querySelector("img");
    if (img) img.hidden = true;
    var box = frame.querySelector(".ed-img-box");
    if (box) box.hidden = true;
    if (session.canvas && session.canvas.parentNode !== frame) {
      if (session.canvas.parentNode) session.canvas.parentNode.removeChild(session.canvas);
      frame.insertBefore(session.canvas, frame.firstChild);
    }
    if (session.hint && session.hint.parentNode !== cell) {
      if (session.hint.parentNode) session.hint.parentNode.removeChild(session.hint);
      cell.appendChild(session.hint);
    }
    session.cell = cell;
    layoutCrop(session);
  }

  function layoutCrop(session) {
    var canvas = session.canvas;
    if (!canvas) return;
    var body = document.getElementById("edImageBody");
    var maxWidth = Math.max(140, (body ? body.clientWidth : 320) - 24);
    var scale = session.width ? Math.min(1, maxWidth / session.width) : 1;
    session.scale = scale;
    // 图还没贴进来时给一块看得见的空台子，不然画布只有 1×1 像素，像坏了。
    var displayW = session.width ? Math.max(1, Math.round(session.width * scale))
                                 : Math.min(maxWidth, 360);
    var displayH = session.height ? Math.max(1, Math.round(session.height * scale))
                                   : Math.round(displayW * 0.62);
    var dpr = Math.min(2, window.devicePixelRatio || 1);
    session.dpr = dpr;
    // 尺寸没变就别再动 canvas.width：改了会重置 2D 上下文，画布高度也会抖一下，
    // 抖一下就撞上 ResizeObserver → 整屏重绘 → 再抖一下。
    var pixelW = Math.round(displayW * dpr);
    var pixelH = Math.round(displayH * dpr);
    if (canvas.width !== pixelW || canvas.height !== pixelH) {
      canvas.width = pixelW;
      canvas.height = pixelH;
    }
    canvas.style.width = displayW + "px";
    canvas.style.height = displayH + "px";
    drawCropCanvas(session);
  }

  function drawCropCanvas(session) {
    var ctx = session.ctx;
    var canvas = session.canvas;
    if (!ctx || !canvas) return;
    var dpr = session.dpr || 1;
    var displayW = canvas.width / dpr;
    var displayH = canvas.height / dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, displayW, displayH);
    if (!session.bitmap) return;
    ctx.drawImage(session.bitmap, 0, 0, displayW, displayH);
    var rect = session.rect;
    if (!rect) return;
    ctx.fillStyle = "rgba(6, 8, 12, 0.42)";
    ctx.fillRect(0, 0, displayW, displayH);
    ctx.fillStyle = "rgba(255, 255, 255, 0.08)";
    ctx.fillRect(rect.x, rect.y, rect.w, rect.h);
    ctx.strokeStyle = "#2f6b4f";
    ctx.lineWidth = 1;
    ctx.strokeRect(rect.x + 0.5, rect.y + 0.5, rect.w, rect.h);
  }

  /** 放大镜层：整屏一块画布，镜子跟着鼠标走，镜心一根红十字。 */
  function ensureLens() {
    if (lensCanvas) return lensCanvas;
    lensCanvas = document.createElement("canvas");
    lensCanvas.className = "ed-crop-lens";
    lensCanvas.setAttribute("aria-hidden", "true");
    document.body.appendChild(lensCanvas);
    resizeLens();
    return lensCanvas;
  }

  function resizeLens() {
    if (!lensCanvas) return;
    var dpr = Math.min(2, window.devicePixelRatio || 1);
    lensCanvas.width = Math.max(1, Math.floor(window.innerWidth * dpr));
    lensCanvas.height = Math.max(1, Math.floor(window.innerHeight * dpr));
    lensCanvas.style.width = window.innerWidth + "px";
    lensCanvas.style.height = window.innerHeight + "px";
    var ctx = lensCanvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.imageSmoothingEnabled = false;
    if (crop) crop.lctx = ctx;
  }

  function drawLens(session) {
    var ctx = session.lctx;
    if (!ctx) return;
    var viewW = window.innerWidth;
    var viewH = window.innerHeight;
    ctx.setTransform(session.dpr || 1, 0, 0, session.dpr || 1, 0, 0);
    ctx.clearRect(0, 0, viewW, viewH);
    if (!session.bitmap || !session.canvas) return;
    var radius = CROP_RADIUS;
    var px = session.pointer.x;
    var py = session.pointer.y;
    var box = session.canvas.getBoundingClientRect();
    var sx = (px - box.left) / session.scale;
    var sy = (py - box.top) / session.scale;
    // 镜子默认在鼠标右下边，撞到边就翻到另一侧。
    var mx = px + radius + 28;
    var my = py + radius + 28;
    if (mx + radius > viewW - 8) mx = px - radius - 28;
    if (my + radius > viewH - 8) my = py - radius - 28;
    var half = radius / CROP_ZOOM;
    var ox = clampValue(sx - half, 0, Math.max(0, session.width - half * 2));
    var oy = clampValue(sy - half, 0, Math.max(0, session.height - half * 2));
    var sw = Math.max(1, Math.min(half * 2, session.width - ox));
    var sh = Math.max(1, Math.min(half * 2, session.height - oy));
    ctx.save();
    ctx.beginPath();
    ctx.arc(mx, my, radius, 0, Math.PI * 2);
    ctx.clip();
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(session.bitmap, ox, oy, sw, sh, mx - radius, my - radius, radius * 2, radius * 2);
    ctx.restore();
    ctx.strokeStyle = "rgba(255, 255, 255, 0.92)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(mx, my, radius, 0, Math.PI * 2);
    ctx.stroke();
    // 镜心准星：告诉老师放大的是哪一粒像素。
    ctx.strokeStyle = "rgba(255, 96, 96, 0.95)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(mx - 12, my + 0.5);
    ctx.lineTo(mx + 12, my + 0.5);
    ctx.moveTo(mx + 0.5, my - 12);
    ctx.lineTo(mx + 0.5, my + 12);
    ctx.stroke();
  }

  function cropPoint(session, clientX, clientY) {
    var box = session.canvas.getBoundingClientRect();
    return {
      x: clampValue(clientX - box.left, 0, box.width),
      y: clampValue(clientY - box.top, 0, box.height)
    };
  }

  function onCropResize() {
    var session = crop;
    if (!session) return;
    layoutCrop(session);
    resizeLens();
    drawLens(session);
  }

  function onCropMove(event) {
    var session = crop;
    if (!session) return;
    session.pointer.x = event.clientX;
    session.pointer.y = event.clientY;
    if (session.dragging && session.bitmap) {
      var point = cropPoint(session, event.clientX, event.clientY);
      session.rect = {
        x: Math.min(session.start.x, point.x),
        y: Math.min(session.start.y, point.y),
        w: Math.abs(point.x - session.start.x),
        h: Math.abs(point.y - session.start.y)
      };
      drawCropCanvas(session);
    }
    drawLens(session);
  }

  function onCropUp(event) {
    var session = crop;
    if (!session || !session.dragging) return;
    if (event.button !== 0) return;
    session.dragging = false;
    var rect = session.rect;
    if (!rect || rect.w < CROP_MIN_SIDE || rect.h < CROP_MIN_SIDE) {
      session.rect = null;
      drawCropCanvas(session);
      session.hint.textContent = "框太小了，再拖一次。";
      return;
    }
    finishCrop(session);
  }

  function onCropKey(event) {
    if (!crop) return;
    if (event.key !== "Escape") return;
    event.preventDefault();
    closeCrop();
  }

  function onCropPaste(event) {
    var session = crop;
    if (!session) return;
    var files = cropFiles(event);
    if (!files.length) return;
    event.preventDefault();
    event.stopPropagation();
    adoptCropFile(session, files[0]);
  }

  function onCropDragOver(event) {
    if (!crop) return;
    event.preventDefault();
  }

  function onCropDrop(event) {
    var session = crop;
    if (!session) return;
    var files = (event.dataTransfer && event.dataTransfer.files) || [];
    if (!files.length) return;
    event.preventDefault();
    event.stopPropagation();
    for (var index = 0; index < files.length; index += 1) {
      if (String(files[index].type || "").indexOf("image/") === 0) {
        adoptCropFile(session, files[index]);
        return;
      }
    }
  }

  /** 贴/拖进来的图直接顶替当前那张——老师要「重新框选」时常常是换一张新的。 */
  function adoptCropFile(session, file) {
    session.hint.textContent = "正在解码这张图…";
    window.createImageBitmap(file).then(function (bitmap) {
      if (!crop || crop !== session) {
        if (typeof bitmap.close === "function") bitmap.close();
        return;
      }
      if (session.bitmap && typeof session.bitmap.close === "function") session.bitmap.close();
      session.bitmap = bitmap;
      session.width = bitmap.width;
      session.height = bitmap.height;
      layoutCrop(session);
      session.hint.textContent = "移动鼠标看像素，拖拽框选，左键松开切图；Esc 取消。";
    }, function (error) {
      session.hint.textContent = "这张图解不开（" + ((error && error.message) || "格式不支持") + "）。";
    });
  }

  /** 松手：按源像素切一块，交给底座落盘，再把题面里的配图换过去。 */
  function finishCrop(session) {
    var rect = session.rect;
    var sx = Math.round(rect.x / session.scale);
    var sy = Math.round(rect.y / session.scale);
    var sw = Math.max(CROP_MIN_SIDE, Math.round(rect.w / session.scale));
    var sh = Math.max(CROP_MIN_SIDE, Math.round(rect.h / session.scale));
    sx = clampValue(sx, 0, Math.max(0, session.width - 1));
    sy = clampValue(sy, 0, Math.max(0, session.height - 1));
    sw = clampValue(sw, 1, session.width - sx);
    sh = clampValue(sh, 1, session.height - sy);
    var out = document.createElement("canvas");
    out.width = sw;
    out.height = sh;
    var octx = out.getContext("2d");
    octx.imageSmoothingEnabled = false;
    octx.drawImage(session.bitmap, sx, sy, sw, sh, 0, 0, sw, sh);
    var dataUrl;
    try {
      dataUrl = out.toDataURL("image/png");
    } catch (error) {
      closeCrop();
      dockWarn("切图失败：画布被污染，取不到像素。");
      return;
    }
    var item = session.item;
    var assetId = cropAssetId();
    // 松手即收摊：放大镜与切图台当场撤掉，落库挪到后台慢慢办。
    // 军令原话是「直到左键松开，框选完成，放大镜消失」——镜子不能在等回执的
    // 那两秒里还杵在屏幕上。
    closeCrop();
    if (item.pendingId) {
      // 中转站里的题：字节随草稿一起进池子，配图落 pending_assets/，主库一个字节都不碰。
      item.cropAsset = { id: assetId, data_url: dataUrl };
      item.question.images = [{ id: assetId, role: "stem", uri: "/static/uploads/" + assetId + ".png" }];
      item.dirty = true;
      stashOne(item, metaFor(item, {}), false).then(function (outcome) {
        if (!outcome || !outcome.ok) {
          dockWarn("切图没能存进中转站：" + ((outcome && outcome.message) || "未知原因"),
            (outcome && outcome.detail) || "");
          return;
        }
        var saved = outcome.result && outcome.result.saved_assets && outcome.result.saved_assets[0];
        var asset = saved && saved.assets && saved.assets[0];
        if (asset && asset.uri && item.question.images && item.question.images[0]) {
          item.question.images[0].uri = asset.uri;
        }
        // 字节已经进池子了：清掉，免得下一次保存又写一份重复的配图。
        item.cropAsset = null;
        scheduleRender();
        dock("切图已存进中转站（" + sw + "×" + sh + " 像素）。");
      });
      return;
    }
    // 题库里的题：先让底座把字节收进 uploads/，再把题面里的 uri 换过去。
    hostCall("asset.upload", { data_url: dataUrl }).then(function (result) {
      item.question.images = [{ id: result.id, role: "stem", uri: result.uri }];
      item.dirty = true;
      scheduleRender();
      dock("切图已存进题库（" + sw + "×" + sh + " 像素）。");
    }, function (error) {
      dockWarn("切图没存住：" + ((error && error.message) || "未知原因"), errorDetail(error));
    });
  }

  /** 源码：一整段 exam-zh 源码，可编辑——它是唯一的录入面。 */
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

  /** 卡片的底线：环境骨架不完整或有游离文本时，绝不自动重组——先如实说明。 */
  function boxedBlockReason(parsed) {
    if (parsed.stray) return "源码里有环境外的内容，请先在源码清掉再拆框";
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

  /** 卡片：框里只有内容，\begin{…} 骨架是写死的标签，摸不到也改不了。 */
  function renderBoxedCell(item, index) {
    var cell = el("div", "ed-boxed");
    cell.setAttribute("data-index", String(index));
    var parsed = parsedOf(item);
    cell.appendChild(el("span", "ed-src-tag", "第 " + (index + 1) + " 题 · 卡片（改完自动重组源码）"));
    var reason = boxedBlockReason(parsed);
    if (reason) {
      cell.appendChild(el("p", "ed-boxed-blocked", "卡片暂不可用：" + reason));
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

  /**
   * 行高取三栏较高者：三栏共用一条滚动，短栏余下的高度正是那层极淡底色。
   *
   * 顺序是这件事的全部：文本框必须先长到内容高度，再量行高。
   * 反过来（先量后长）的话，源码栏会在量完之后继续长高一截，
   * 三栏之间的虚线当场错位——老师点一下「源码/卡片」就看见。
   * 所以这里长—量两轮：第一轮让框就位，第二轮按最终高度重新对齐。
   *
   * 量高必须用 getBoundingClientRect 的小数高度：offsetHeight 会把 300.4px 截成 300，
   * 而框框视图里的内容高往往带小数，于是每一行的源码格都比另两栏高出一丝，
   * 虚线一行一行往下飘——这正是「点一下卡片就歪」的真相。
   */
  function alignRows() {
    var max = 0;
    for (var pass = 0; pass < 2; pass += 1) {
      Array.prototype.forEach.call(
        sourceBodyEl.querySelectorAll(".ed-src-area, .ed-box-textarea"), growTextarea);
      max = 0;
      for (var index = 0; index < state.items.length; index += 1) {
        var cells = [imageBodyEl.children[index], sourceBodyEl.children[index], renderBodyEl.children[index]];
        var rowH = 0;
        cells.forEach(function (cell) {
          if (!cell) return;
          var height = cell.getBoundingClientRect().height;
          if (height > rowH) rowH = height;
        });
        cells.forEach(function (cell) {
          if (cell) cell.style.minHeight = rowH + "px";
        });
        if (index === 0) max = rowH;
      }
    }
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
    if (formatEl) {
      formatEl.setAttribute("data-format", state.format);
      formatEl.textContent = state.format === "boxed" ? "卡片" : "源码";
    }
    setFormatButtons(state.format);
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
    // 切图台先归位再量行高：量的时候它得在格子里，否则量出来的行高偏小，
    // 归位后格子又长高一截，那一截会再勾一次 ResizeObserver，绕成死循环。
    anchorCrop(crop);
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

  /** 把回填后的源码写回中栏：源码改 textarea 的值并把光标停在段末，卡片整格重建（框本就从源码拆出来）。 */
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
    var extensions = question.extensions && typeof question.extensions === "object"
      ? question.extensions : {};
    var editorExt = extensions["org.jiuzhang.editor"] && typeof extensions["org.jiuzhang.editor"] === "object"
      ? extensions["org.jiuzhang.editor"] : {};
    return {
      type: TYPE_VALUES.indexOf(question.type) >= 0 ? question.type : "",
      difficulty: DIFFICULTY_VALUES.indexOf(question.difficulty) >= 0 ? question.difficulty : "L1",
      grade: trunc(question.grade, 20),
      tags: (question.tags || []).slice(0, TAG_LIMIT).join(","),
      score: trunc(editorExt.score, 8),
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
   * 源码按源码偏移判定（choices 与「答案：」行都判不出字段，档 1 只吃题干/解析）；
   * 卡片直接看框的语义字段，框头环境名本来就锁死，不必再算偏移。
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
    // 首屏是批次列表：没有题可发，但辅助栏仍要知道有哪些批次、当前是哪一个，
    // 才能把公共元数据与标准名摆出来。
    if (state.mode === "list") return listPayload();
    if (!item) return null;
    var parsed = parsedOf(item);
    var question = item.question || {};
    return {
      index: state.active,
      total: state.items.length,
      key: item.key,
      question_id: item.savedId || question.id || "",
      saved_id: item.savedId || "",
      // 中转站的两把号：审核动作（存入主库 / 存为待办 / 彻底删除）全靠它们。
      pending_id: item.pendingId || "",
      batch_id: item.batchId || state.batchId || "",
      mode: state.mode,
      status: item.status,
      dirty: Boolean(item.dirty),
      format: state.format,
      swap: Boolean(state.swap),
      source: trunc(item.source, SOURCE_MAX),
      caret: caretOfActive(),
      errors: parsed.errors.slice(0, 8),
      ai_type: parsed.type,
      confidence: typeof item.dev.confidence === "number" ? item.dev.confidence : null,
      defaults: defaultsOf(item),
      // 待入库池的台账随选区一起走：辅助栏要自己知道「一共几题、几题脏」才敢让那颗钮亮起来。
      pool: poolCounts(),
      images: (question.images || []).slice(0, 32),
      extensions: keepExtensions(question.extensions),
      origin: question.source && typeof question.source === "object"
        ? { region: question.source.region || "", school: question.source.school || "" }
        : null
    };
  }

  /** 批次列表语境：辅助栏据此显示原文件名、标准名与公共元数据面板。 */
  function listPayload() {
    return {
      mode: "list",
      index: 0,
      total: state.items.length,
      key: "",
      question_id: "",
      saved_id: "",
      pending_id: "",
      batch_id: state.batchId || "",
      status: "pending",
      dirty: false,
      format: state.format,
      swap: Boolean(state.swap),
      source: "",
      caret: null,
      errors: [],
      ai_type: "",
      confidence: null,
      defaults: {},
      pool: poolCounts(),
      images: [],
      extensions: {},
      origin: null,
      batches: state.batches.map(function (card) {
        return {
          batch_id: String(card.batch_id || ""),
          source_name: String(card.source_name || ""),
          label: String(card.label || ""),
          pending_count: Number(card.pending_count) || 0,
          total: Number(card.total) || 0,
          meta: card.meta && typeof card.meta === "object" ? card.meta : {}
        };
      })
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
    // 选区一发布，工作清单草稿就得跟着落盘：批量保存那颗钮住在辅助栏，
    // 面板侧只能读这份草稿重建题目。草稿若还停在 600ms 前的旧版，
    // 老师刚改的那一题就会漏交，还不自知。
    saveWorklist();
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
        var question = item.question || {};
        return {
          key: item.key,
          id: question.id ? question.id : "",
          saved_id: item.savedId || "",
          pending_id: item.pendingId || "",
          batch_id: item.batchId || state.batchId || "",
          status: item.status,
          dirty: Boolean(item.dirty),
          source: trunc(item.source, SOURCE_MAX),
          // 辅助栏可能在画布发布选区之前就已挂载：把默认值一并存进宿主代持的草稿，
          // 面板读草稿就能自己补出这张表单，不必等一条永远不会重放的通知。
          defaults: defaultsOf(item),
          confidence: typeof item.dev.confidence === "number" ? item.dev.confidence : null,
          errors: parsedOf(item).errors.slice(0, 8),
          // 批量保存搬进辅助栏后，面板侧要靠这份台账把题目原样重建出来：
          // 少了图片、扩展与原卷字段，更新一题就会把这些悄悄抹掉。
          images: (question.images || []).slice(0, 32),
          extensions: keepExtensions(question.extensions),
          origin: question.source && typeof question.source === "object"
            ? { region: question.source.region || "", school: question.source.school || "" }
            : null
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

  // ---------- 源码 / 卡片（开关住辅助栏；画布是视图主人，宿主 ui.params 做跨帧对账） ----------
  function setFormatButtons(format) {
    var value = FORMATS[format] ? format : "latex";
    panel.format = value;
    [panelFmtLatexEl, panelFmtBoxedEl].forEach(function (node) {
      if (!node) return;
      var on = node.getAttribute("data-format") === value;
      node.classList.toggle("is-on", on);
      node.setAttribute("aria-pressed", on ? "true" : "false");
    });
    if (panelViewNoteEl) {
      panelViewNoteEl.textContent = value === "boxed"
        ? "卡片：框里只有内容，环境骨架改不动。"
        : "源码：整段源码直接编辑。两者只是同一份源码的两种编辑面。";
    }
    if (panelMetricsEl) panelMetricsEl.setAttribute("data-format", value);
  }

  function setFormat(next) {
    var value = FORMATS[next] ? next : "latex";
    if (value === state.format) return;
    state.format = value;
    if (sourceHintEl) {
      sourceHintEl.textContent = value === "boxed"
        ? "卡片 · 框里只有内容，环境骨架改不动"
        : "源码 · 整段源码直接编辑";
    }
    setFormatButtons(value);
    renderAll();
    publishSelection();
  }

  /**
   * 辅助栏点格式：按钮先亮，再请宿主把参数广播给画布帧。
   * 面板拿不到画布的 DOM，真正切视图只发生在画布收到 ui.params.changed 之后。
   */
  function chooseFormatFromPanel(next) {
    if (!FORMATS[next]) return;
    setFormatButtons(next);
    hostCall("ui.params.set", {
      params: { format: next },
      snapshot: panel.uiRevisions || {},
      plugin_id: PLUGIN_ID
    }).catch(function () {
      if (panel.selection) setFormatButtons(panel.selection.format || "latex");
    });
  }

  // ---------- 源码 / 渲染左右互换（只改视觉顺序，DOM 不挪） ----------
  function setSwapButton(on) {
    panel.swap = Boolean(on);
    if (!panelSwapEl) return;
    var label = panel.swap ? "⇄ 换回" : "⇄ 互换";
    panelSwapEl.setAttribute("aria-pressed", panel.swap ? "true" : "false");
    panelSwapEl.setAttribute("aria-label", label + "（源码与渲染左右位置）");
    panelSwapEl.setAttribute("title", label + "（源码与渲染左右位置）");
    panelSwapEl.textContent = label;
  }

  function applySwap(next, persist) {
    state.swap = Boolean(next);
    if (colsEl) colsEl.setAttribute("data-swap", state.swap ? "true" : "false");
    setSwapButton(state.swap);
    if (persist) queueLayoutSave();
  }

  /** 辅助栏点互换：同样只把意图交给宿主，画布收到广播后才换位并回投选区。 */
  function toggleSwapFromPanel() {
    var next = !panel.swap;
    setSwapButton(next);
    hostCall("ui.params.set", {
      params: { swap: next ? "true" : "false" },
      snapshot: panel.uiRevisions || {},
      plugin_id: PLUGIN_ID
    }).catch(function () {
      if (panel.selection) setSwapButton(Boolean(panel.selection.swap));
    });
  }

  /** 辅助栏点【← 返回列表】：意图交给宿主，画布收到广播后才回列表。 */
  function backToListFromPanel() {
    hostCall("ui.params.set", {
      params: { view: "list" },
      snapshot: panel.uiRevisions || {},
      plugin_id: PLUGIN_ID
    }).catch(function () { /* 参数通道没通就留在三栏，绝不擅自改本帧 DOM */ });
  }

  /**
   * 互换的只有视觉位置：源码框与渲染块还是原来那两个 DOM 节点，
   * 值、选区、撤销栈与滚动进度都不会离开元素，所以只需在换序后补一次行高对齐。
   */
  function toggleSwap() {
    var focus = lastFieldNode && document.contains(lastFieldNode) ? lastFieldNode : null;
    var caret = null;
    if (focus) {
      try { caret = [focus.selectionStart, focus.selectionEnd]; } catch (error) { caret = null; }
    }
    var scrolls = [sourceBodyEl, renderBodyEl].map(function (node) {
      return node ? node.scrollTop : 0;
    });
    applySwap(!state.swap, true);
    alignRows();
    [sourceBodyEl, renderBodyEl].forEach(function (node, position) {
      if (node) node.scrollTop = scrolls[position];
    });
    // 点按钮会把焦点从源码框拿走：换完把光标送回原处，老师接着打字
    if (focus && document.activeElement !== focus) {
      try { focus.focus({ preventScroll: true }); } catch (error) { focus.focus(); }
      if (caret) {
        try { focus.setSelectionRange(caret[0], caret[1]); } catch (error) { /* input 不一定支持 */ }
      }
    }
    window.requestAnimationFrame(function () {
      alignRows();
      [sourceBodyEl, renderBodyEl].forEach(function (node, position) {
        if (node) node.scrollTop = scrolls[position];
      });
    });
  }

  // ---------- 三栏拖宽（比例记账，像素只在下鼠标那一刻出现） ----------
  /** 夹比例：留一份极窄缝，其余全给弹性栏。 */
  function clampRatio(value, fallback) {
    var number = Number(value);
    if (!isFinite(number) || number <= 0) return fallback;
    return Math.min(0.9, Math.max(0.02, number));
  }

  /** 当前画布的可用宽度：总宽与「中右两栏合起来」的那一段。 */
  function paneMetrics() {
    var total = colsEl ? colsEl.clientWidth : 0;
    var image = state.widths.image * total;
    var workbench = total - image - SPLIT_W;
    if (workbench < PANE_MIN * 2) workbench = PANE_MIN * 2;
    return { total: total, workbench: workbench };
  }

  /**
   * 把比例写进 CSS 变量：原图栏按总宽算比例，源码栏按中右两栏合起来的宽度算比例。
   * 画布变窄时两个比例都不动，三栏一起等比缩放。
   */
  function applyWidths() {
    var metrics = paneMetrics();
    if (metrics.total <= 0) return;
    state.widths.image = clampRatio(state.widths.image, DEFAULT_IMAGE_RATIO);
    state.widths.source = clampRatio(state.widths.source, DEFAULT_SOURCE_RATIO);
    colsEl.style.setProperty("--w-image", (state.widths.image * 100).toFixed(3) + "%");
    colsEl.style.setProperty("--w-source", (state.widths.source * 100).toFixed(3) + "%");
    if (metricsEl) metricsEl.setAttribute("data-pane-w", String(metrics.total));
  }

  /**
   * 老草稿记的是像素（260/360 那一版）：读回来时按当时的画布宽换算成比例，
   * 免得老布局一恢复就把原图栏撑成整幅画布。
   */
  function normalizeWidths(value) {
    var metrics = paneMetrics();
    var raw = (value && typeof value === "object") ? value : {};
    var image = Number(raw.image);
    var source = Number(raw.source);
    if (isFinite(image) && image > 1) {
      image = metrics.total > 0 ? image / metrics.total : DEFAULT_IMAGE_RATIO;
    }
    if (isFinite(source) && source > 1) {
      source = metrics.workbench > 0 ? source / metrics.workbench : DEFAULT_SOURCE_RATIO;
    }
    state.widths.image = clampRatio(image, DEFAULT_IMAGE_RATIO);
    state.widths.source = clampRatio(source, DEFAULT_SOURCE_RATIO);
  }

  function saveLayout() {
    hostCall("draft.save", {
      key: DRAFT_LAYOUT_KEY,
      value: { widths: state.widths, swap: state.swap }
    }).catch(function () { /* 布局偏好存不下就算了，不打扰老师 */ });
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
      var metrics = paneMetrics();
      // 像素位移立刻换算成比例位移：拖到哪儿都是「占画布的几分之几」
      if (which === "image") {
        state.widths.image = drag.image + (metrics.total > 0 ? delta / metrics.total : 0);
      } else {
        state.widths.source = drag.source + (metrics.workbench > 0 ? delta / metrics.workbench : 0);
      }
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
      // 焦点在里面的互换钮上时，方向键归按钮（不许把回车/方向键顺手变成拖栏）
      if (event.target !== node) return;
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      var step = event.shiftKey ? 8 : 24;
      var delta = event.key === "ArrowLeft" ? -step : step;
      var metrics = paneMetrics();
      if (which === "image") {
        state.widths.image += metrics.total > 0 ? delta / metrics.total : 0;
      } else {
        state.widths.source += metrics.workbench > 0 ? delta / metrics.workbench : 0;
      }
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
    // 草稿里没有这一题时，用题目自己的默认值打底：自动存草稿是「静默」的动作，
    // 绝不能顺手把年级、标签、来源抹掉——老师没碰过表单不等于他不要这些。
    var fallback = defaultEntry({ defaults: defaultsOf(item) });
    Object.keys(fallback).forEach(function (key) { meta[key] = fallback[key]; });
    var taxonomy = (item.question || {}).taxonomy || {};
    meta.topic_ids = Array.isArray(taxonomy.topic_ids)
      ? taxonomy.topic_ids.slice(0, TOPIC_LIMIT) : [];
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
    var editorExt = extras["org.jiuzhang.editor"] || {};
    if (doc.grade) editorExt.grade = doc.grade;
    // 分值同样没有契约字段：只存进插件自己的扩展里，题目正文一个字都不多。
    var scoreText = String(meta.score == null ? "" : meta.score).trim().slice(0, 8);
    if (scoreText) editorExt.score = scoreText;
    if (Object.keys(editorExt).length) extras["org.jiuzhang.editor"] = editorExt;
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

  // ---------- 台账：辅助栏底边那一行只报数，审核动作在上面那三颗钮里，这里不再带按钮。 ----------
  /** 画布侧的真身：整份工作清单都在这儿，池的账只能从这里算。 */
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

  /** 面板侧的账：随选区一起从画布过来，画布没开口子之前一律报零。 */
  function panelPoolCounts() {
    var pool = panel.selection && panel.selection.pool;
    if (!pool || typeof pool !== "object") return { fresh: 0, stored: 0, dirty: 0, errored: 0 };
    return {
      fresh: Number(pool.fresh) || 0, stored: Number(pool.stored) || 0,
      dirty: Number(pool.dirty) || 0, errored: Number(pool.errored) || 0
    };
  }

  function batchNote(text, phase) {
    if (!batchNoteEl) return;
    batchNoteEl.textContent = text;
    // 辅助栏窄，话术只许单行省略（契约如此）；完整文案挂 title，悬停能看全。
    batchNoteEl.title = text;
    batchNoteEl.setAttribute("data-batch", phase || "idle");
  }

  /** 台账：辅助栏底边那一行只报数，审核动作在上面那三颗钮里，这里不再带按钮。 */
  function renderPool() {
    var counts = state.slot === "stage.center" ? poolCounts() : panelPoolCounts();
    if (poolEl) {
      // 军令 #29：底段只留一行灰字「待入库：N · 已入库：M」；脏与缺件只在真发生时补上，
      // 平时这一行始终是两段，窄栏里也不会被挤成三行。
      var parts = ["待入库：" + counts.fresh, "已入库：" + counts.stored];
      if (counts.dirty) parts.push("未保存：" + counts.dirty);
      if (counts.errored) parts.push("缺件：" + counts.errored);
      poolEl.textContent = parts.join(" · ");
      poolEl.setAttribute("data-new", String(counts.fresh));
      poolEl.setAttribute("data-stored", String(counts.stored));
      poolEl.setAttribute("data-dirty", String(counts.dirty));
      poolEl.setAttribute("data-errored", String(counts.errored));
    }
  }

  // ---------- 审核三钮：存入主库 / 存为待办 / 彻底删除 ----------
  /** 当前题 → 契约里的题目文档（源码解析 + 表单元数据），顺带把该说的话说了。 */
  function documentFor(item, meta) {
    var parsed = parseExamSource(item.source);
    var doc = questionFromParsed(item, parsed, meta || {});
    return { doc: doc, parsed: parsed, problems: validateForSave(doc, parsed, meta || {}) };
  }

  function approveBusy(busy) {
    if (!panelApproveEl) return;
    panelApproveEl.disabled = busy;
    panelApproveEl.setAttribute("aria-busy", busy ? "true" : "false");
    panelApproveEl.setAttribute("aria-disabled", busy ? "true" : "false");
  }

  /**
   * 【存入主库】：中转站里的题由底座落进主库，p_ 号段换成 q_ 号段，配图搬进 uploads。
   * 主库已有同题时底座回 409，原样抛给弹窗——底座只如实报出「哪一道、差在哪儿」，
   * 覆盖与否由老师拍板，插件不替老师做主。
   */
  function onApprove(force) {
    var item = panelItem();
    if (!item) {
      panelSay("辅助栏还没收到当前题的源码，等画布发一次选区。", "warn", "idle");
      return;
    }
    if (panel.saving) return;
    var entry = readForm();
    panel.currentEntry = entry;
    panel.meta[item.key] = entry;
    if (!item.pendingId) {
      // 题库里的题直接改：走 bank.update，不经过中转站。
      panel.saving = true;
      approveBusy(true);
      panelSay("正在写入题库…", "info", "saving");
      saveItem(item, entry, "save").then(function (result) {
        panel.selection.status = "stored";
        panel.selection.dirty = false;
        panelSay("已更新题目 " + result.question_id + "。", "ok", "updated");
      }, function (error) {
        panelSay(explainHostError(error), "error", "failed");
        dockWarn("存入主库失败：" + ((error && error.message) || "未知原因"), errorDetail(error));
      }).then(function () {
        panel.saving = false;
        approveBusy(false);
      });
      return;
    }
    panel.saving = true;
    approveBusy(true);
    panelSay("正在存入主库…", "info", "saving");
    batchNote("正在存入主库…", "running");
    hostCall("pending.approve", { pending_id: item.pendingId, force: force === true })
      .then(function (result) {
        panel.saving = false;
        approveBusy(false);
        closeModal(dupModalEl);
        panel.selection.status = "stored";
        panel.selection.dirty = false;
        panelSay("已存入主库：" + (result.question_id || "") + "。", "ok", "created");
        batchNote("已存入主库（" + (result.question_id || "") + "）。", "done");
        dock("中转站里的一道题已存入主库：" + (result.question_id || ""));
      }, function (error) {
        panel.saving = false;
        approveBusy(false);
        if (error && error.duplicate) {
          batchNote("主库已有该题，等老师拍板。", "partial");
          openDupModal(item, error);
          return;
        }
        panelSay(explainHostError(error), "error", "failed");
        batchNote("存入主库失败：" + ((error && error.message) || "未知原因"), "failed");
        dockWarn("存入主库失败：" + ((error && error.message) || "未知原因"), errorDetail(error));
      });
  }

  /** 【存为待办】：把这一题写回中转池。带 pending_id 就是原地更新，池子里不会多出一道重影。 */
  function onStash() {
    var item = panelItem();
    if (!item) {
      panelSay("辅助栏还没收到当前题的源码，等画布发一次选区。", "warn", "idle");
      return;
    }
    if (panel.saving) return;
    var entry = readForm();
    panel.currentEntry = entry;
    panel.meta[item.key] = entry;
    var built = documentFor(item, entry);
    if (built.problems.length) {
      panelSay("这一题还存不进去：" + built.problems.slice(0, 3).join("；"), "warn", "invalid");
      return;
    }
    var payload = { questions: [{ pending_id: item.pendingId || "", question: built.doc }] };
    if (item.batchId) payload.batch_id = item.batchId;
    panel.saving = true;
    panelSay("正在存进中转站…", "info", "saving");
    batchNote("正在存进中转站…", "running");
    hostCall("pending.save_draft", payload).then(function (result) {
      panel.saving = false;
      var ids = (result && Array.isArray(result.saved_ids)) ? result.saved_ids : [];
      panelSay("已存为待办（池子编号 " + (item.pendingId || ids[0] || "—") + "）。", "ok", "stashed");
      batchNote("已存为待办（池子编号 " + (item.pendingId || ids[0] || "—") + "）。", "done");
      dock("一道题已存进中转站（待审核池）。");
    }, function (error) {
      panel.saving = false;
      panelSay("存为待办失败：" + ((error && error.message) || "未知原因"), "error", "failed");
      batchNote("存为待办失败。", "failed");
      dockWarn("存为待办失败：" + ((error && error.message) || "未知原因"), errorDetail(error));
    });
  }

  /** 【彻底删除】：这一道题连同它的配图从中转站消失，主库一个字节都不碰。 */
  function onDelete() {
    var item = panelItem();
    if (!item || !item.pendingId) {
      panelSay("这一题不在待审核池里，池子删不了它——题库里的题请回题库删。", "warn", "idle");
      return;
    }
    panel.pending = item;
    openModal(delModalEl);
  }

  function onDeleteConfirm() {
    var item = panel.pending;
    closeModal(delModalEl);
    if (!item) return;
    hostCall("pending.delete", { pending_id: item.pendingId }).then(function () {
      panelSay("这一题已从中转站彻底删除。", "ok", "deleted");
      batchNote("这一题已从中转站彻底删除。", "done");
      dock("一道题已从中转站彻底删除。");
    }, function (error) {
      panelSay("删不掉：" + ((error && error.message) || "未知原因"), "error", "failed");
      batchNote("彻底删除失败。", "failed");
      dockWarn("彻底删除失败：" + ((error && error.message) || "未知原因"), errorDetail(error));
    });
  }

  // ---------- 弹窗：查重与彻底删除共用一套开合规矩（焦点圈住、Esc 可关、关掉还焦） ----------
  var modalRestoreFocus = null;

  function openModalNode() {
    if (dupModalEl && !dupModalEl.hidden) return dupModalEl;
    if (delModalEl && !delModalEl.hidden) return delModalEl;
    return null;
  }

  function openModal(node) {
    if (!node) return;
    modalRestoreFocus = document.activeElement;
    node.hidden = false;
    var first = node.querySelector("button");
    if (first && typeof first.focus === "function") first.focus();
  }

  function closeModal(node) {
    if (!node || node.hidden) return;
    node.hidden = true;
    if (modalRestoreFocus && typeof modalRestoreFocus.focus === "function") {
      modalRestoreFocus.focus();
    }
    modalRestoreFocus = null;
  }

  /** 查重命中：弹窗给两颗钮——返回修改 / 强行覆盖。 */
  function openDupModal(item, error) {
    if (!dupModalEl) return;
    panel.pending = item;
    if (dupTextEl) {
      dupTextEl.textContent = "主库里已经有同一道题（"
        + ((error && error.existingId) || "已有记录")
        + "）。可以返回修改，也可以强行覆盖主库那一条。";
    }
    openModal(dupModalEl);
  }

  document.addEventListener("keydown", function (event) {
    var node = openModalNode();
    if (!node) return;
    if (event.key === "Escape") {
      event.preventDefault();
      closeModal(node);
      return;
    }
    if (event.key !== "Tab") return;
    var focusable = node.querySelectorAll("button");
    if (!focusable.length) return;
    var first = focusable[0];
    var last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });

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

  // ---------- 两帧对账：辅助栏设的视图参数（面板→画布）与入库回执（面板→画布） ----------
  function onUiParams(payload) {
    var values = payload && payload.values;
    if (!payload || payload.pluginId !== PLUGIN_ID || !values) return;
    if (payload.revisions && typeof payload.revisions === "object") {
      panel.uiRevisions = JSON.parse(JSON.stringify(payload.revisions));
    }
    if (state.slot === "stage.center") {
      if (values.format && values.format !== state.format) setFormat(values.format);
      if (values.swap != null) {
        var wantSwap = values.swap === true || values.swap === "true";
        if (wantSwap !== state.swap) {
          applySwap(wantSwap, true);
          alignRows();
          publishSelection();
        }
      }
      // 辅助栏那颗【← 返回列表】：画布收到广播才真回列表，且不再回发一遍。
      if (values.view === "list" && state.mode === "review") backToList("已回到批次列表。", true);
      return;
    }
    if (values.format) setFormatButtons(values.format);
    if (values.swap != null) setSwapButton(values.swap === true || values.swap === "true");
  }

  /**
   * 辅助栏落库后留一张回执，画布收到 system.question_updated 时按回执认领：
   * 「新建」和「派生变式」在事件里长得一模一样，只有回执能分清是哪一题变成了哪道题。
   */
  /**
   * 回执箱是两只帧共用的一只：面板投票，画布认领。
   * 认领方不许改写箱子——它一写，就会把对面刚投进来的新票抹掉，
   * 批量提交时那一票就永远等不到，题目在画布上会一直挂着「未入库」。
   * 所以只写方（pushReceipt）先读后写，认领方只读。
   */
  function pushReceipt(receipt) {
    hostCall("draft.load", { key: DRAFT_RECEIPT_KEY }).then(function (result) {
      var value = result && result.value;
      var list = value && Array.isArray(value.items) ? value.items.slice() : [];
      list.push({
        key: receipt.key, id: receipt.id, action: receipt.action,
        mode: receipt.mode, at: nowIso()
      });
      panel.receipts = list.slice(-20);
      return hostCall("draft.save", { key: DRAFT_RECEIPT_KEY, value: { items: panel.receipts } });
    }).catch(function () { /* 回执丢了，画布顶多少刷一次状态 */ });
  }

  function consumeReceipts(payload, attempt) {
    var id = payload && payload.id ? String(payload.id) : "";
    if (!id) return;
    var tries = Number(attempt) || 0;
    hostCall("draft.load", { key: DRAFT_RECEIPT_KEY }).then(function (result) {
      var value = result && result.value;
      var list = value && Array.isArray(value.items) ? value.items : [];
      var matched = null;
      list.forEach(function (item) {
        if (!matched && item && String(item.id) === id) matched = item;
      });
      if (!matched) {
        // 宿主是先广播事件、后把应答送回辅助栏，回执落草稿比事件晚一跳；读不到就重试
        if (tries < RECEIPT_RETRY_MAX) {
          setTimeout(function () { consumeReceipts(payload, tries + 1); }, RECEIPT_RETRY_MS);
        }
        return;
      }
      panel.receipts = list.slice(-20);
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
      // 认领回执时由画布把题号回显到读屏状态位，老师不用来回翻帧。
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
      pendingId: sel.pending_id || "",
      batchId: sel.batch_id || "",
      status: sel.status === "stored" ? "stored" : "pending",
      source: String(sel.source || panel.source || ""),
      question: {
        id: sel.question_id || "",
        images: Array.isArray(sel.images) ? sel.images : [],
        extensions: sel.extensions && typeof sel.extensions === "object" ? sel.extensions : {},
        source: sel.origin && typeof sel.origin === "object" ? sel.origin : null
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
      score: d.score || "",
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
    if (panelScoreEl) entry.score = panelScoreEl.value;
    return entry;
  }

  function bindFormChanges() {
    [panelTypeEl, panelDifficultyEl, panelGradeEl, panelPaperEl, panelQuestionNoEl,
      panelExamTypeEl, panelYearEl, panelScoreEl].forEach(function (node) {
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

  /**
   * 这一批有了标准名，题级的「原卷名 / 年份 / 类型」就变成只读镜像——
   * 标准名是那五个公共字段拼出来的，手改它等于把整批的公共元数据改乱。
   */
  function syncSourceFields() {
    var meta = panel.batchMeta || {};
    var standard = String(meta.standard_name || standardNameOf(meta));
    var locked = Boolean(standard);
    if (panelPaperEl) {
      if (locked) panelPaperEl.value = standard;
      panelPaperEl.readOnly = locked;
      panelPaperEl.setAttribute("data-locked", locked ? "true" : "false");
    }
    if (panelYearEl) {
      if (locked && meta.year != null) panelYearEl.value = String(meta.year);
      panelYearEl.readOnly = locked;
      panelYearEl.setAttribute("data-locked", locked ? "true" : "false");
    }
    if (panelExamTypeEl) {
      if (locked && meta.exam_type) panelExamTypeEl.value = String(meta.exam_type);
      panelExamTypeEl.readOnly = locked;
      panelExamTypeEl.setAttribute("data-locked", locked ? "true" : "false");
    }
  }

  /** 首屏是批次列表：只切换批次语境，绝不碰那道题还没填完的表单。 */
  function applyListSelection(sel) {
    panel.selection = null;
    panel.currentEntry = null;
    var cards = Array.isArray(sel.batches) ? sel.batches : [];
    var wanted = String(sel.batch_id || "");
    var current = null;
    for (var index = 0; index < cards.length; index += 1) {
      if (String(cards[index].batch_id || "") === wanted) { current = cards[index]; break; }
    }
    if (!current && cards.length) current = cards[0];
    panel.batchCard = current;
    panel.batchMeta = current && current.meta && typeof current.meta === "object"
      ? current.meta
      : {};
    panel.batchId = current ? String(current.batch_id || "") : "";
    renderBatchMeta();
    if (panelProgressEl) {
      panelProgressEl.textContent = "批次列表";
      panelProgressEl.setAttribute("data-active", "0");
      panelProgressEl.setAttribute("data-total", String(cards.length));
    }
    if (panelStatusEl) {
      panelStatusEl.textContent = "● 待审核";
      panelStatusEl.setAttribute("data-status", "pending");
      panelStatusEl.setAttribute("data-dirty", "false");
    }
    renderPool();
    if (!panel.metaSyncing) {
      panelSay(cards.length
        ? "点批次列表里的任意一行进入审核。"
        : "中转站里还没有批次：把卷子拖进来，或 Ctrl+V 粘贴截图。",
        "info", "idle");
    }
  }

  function applySelection(sel) {
    if (!sel || typeof sel !== "object") return;
    // 首屏是批次列表：这里只认批次，不动那道题还没填的表单。
    if (sel.mode === "list") {
      applyListSelection(sel);
      return;
    }
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
    if (panelScoreEl) panelScoreEl.value = merged.score || "";
    if (panelHeadNoEl) panelHeadNoEl.textContent = "第 " + (Number(sel.index || 0) + 1) + " 题";
    syncSourceFields();
    // 换批次要把公共元数据面板切过去；面板回来后再把题级的只读镜像对齐一次。
    syncBatchContext(sel.batch_id).then(function () { syncSourceFields(); });
    renderTags();
    setFormatButtons(sel.format || panel.format);
    setSwapButton(Boolean(sel.swap));
    renderTypeNote();
    renderMounted();
    renderPanelMetrics();
    renderAi();
    renderPool();
    if (panelSelectionError()) {
      panelSay(panelSelectionError(), "error", "invalid");
    } else if (panel.ai.state === "ready" && panel.ai.key === sel.key) {
      // 刚把改写发给画布，那句「保存才入库」不能被选区回显盖掉——否则老师会以为已经入库了
    } else if (!panel.saving) {
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
      panelSay("源码里找不到" + fieldLabel(caret.field) + "段的正文：切到源码补上环境骨架再试。", "error", "invalid");
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

  // ---------- 幽灵胶囊（军令 #29 / #30）：标签与考向共用一套 ----------
  // 空壳、候选、高亮与已经挂上的胶囊都在 dist/ui_capsule.js 里；
  // 这里只把元素、宿主通道与要回写的地方交进去。
  var capsule = window.JzoEditorCapsule.create({
    el: el,
    hostCall: hostCall,
    tagList: panelTagListEl,
    mountedList: panelMountedEl,
    tagMenu: panelGhostTagMenuEl,
    topicMenu: panelGhostTopicMenuEl,
    tagsValue: function () { return panelTagsEl ? panelTagsEl.value : ""; },
    entry: function () { return panel.currentEntry || {}; },
    topicStore: panel,
    scene: function () { return panelMetaSceneEl ? String(panelMetaSceneEl.value || "") : ""; },
    commitTags: function (tags) { commitTags(tags); },
    toggleTopic: function (topic) { toggleTopic(topic); },
    splitTags: splitTags,
    delay: GHOST_DELAY_MS
  });

  function renderTags() { capsule.renderTags(); }

  function renderMounted() { capsule.renderMounted(); }

  function wireGhostCell(kind) { capsule.wireCell(kind); }

  function commitTags(tags) {
    if (!panelTagsEl) return;
    var list = [];
    (tags || []).forEach(function (tag) {
      var one = String(tag == null ? "" : tag).trim().slice(0, 32);
      if (one && list.indexOf(one) < 0) list.push(one);
    });
    panelTagsEl.value = list.slice(0, TAG_LIMIT).join(",");
    renderTags();
    onFormChange();
  }

  /** 从宿主代持的工作清单草稿里重建辅助栏选区——两个帧同时挂载，通知不一定赶得上。 */
  function applyDraftSelection(value) {
    if (panel.selection) return;
    var items = value && Array.isArray(value.items) ? value.items : [];
    var active = value ? Number(value.active) || 0 : 0;
    var saved = items[active] || items[0] || null;
    if (!saved) return;
    var source = String(saved.source || "");
    var pool = { fresh: 0, stored: 0, dirty: 0, errored: 0 };
    items.forEach(function (each) {
      if (each.status === "stored") pool.stored += 1;
      else pool.fresh += 1;
      if (each.dirty) pool.dirty += 1;
      if (each.errors && each.errors.length) pool.errored += 1;
    });
    panel.source = source;
    applySelection({
      index: active, total: items.length, key: saved.key,
      question_id: saved.id || saved.saved_id || "", saved_id: saved.saved_id || "",
      pending_id: saved.pending_id || "", batch_id: saved.batch_id || "",
      mode: "review",
      status: saved.status, dirty: Boolean(saved.dirty), format: panel.format,
      swap: panel.swap, source: source, errors: saved.errors || [],
      ai_type: parseExamSource(source).type,
      confidence: typeof saved.confidence === "number" ? saved.confidence : null,
      defaults: saved.defaults || {}, pool: pool,
      images: Array.isArray(saved.images) ? saved.images : [],
      extensions: saved.extensions && typeof saved.extensions === "object" ? saved.extensions : {},
      origin: saved.origin && typeof saved.origin === "object" ? saved.origin : null
    });
  }

  /** 中转站动了：辅助栏要知道——批次卡片与公共元数据都可能变了。 */
  function onPanelPendingUpdated(payload) {
    var action = String((payload && payload.action) || "");
    if (action === "ingest") {
      loadMetaHistory();
      panelSay("新批次已建，去批次列表里审。", "info", "idle");
      return;
    }
    if (action === "meta") {
      // 底座刚把公共元数据同步过，重新读一遍这一批的账
      loadBatchMeta(panel.batchId);
      return;
    }
    if (action === "approve" || action === "delete" || action === "save_draft") {
      loadBatchMeta(panel.batchId);
    }
  }

  // ---------- 双侧呼吸灯与批次折叠（军令 #29 / #30） ----------
  // 两个 iframe 之间不直连（AGENTS §2）：画布把「鼠标停在哪一题」「画布在滚动」
  // 经宿主总线报给辅助栏，辅助栏据此亮边缘、收批次公共元数据。
  // 灯与折叠的状态和渲染都在 dist/ui_breath.js，这里只把元素、总线与延时交进去。
  var breath = window.JzoBreath.create({
    rows: [imageBodyEl, sourceBodyEl, renderBodyEl],
    panelRoot: panelRoot,
    panelMetaSecEl: panelMetaSecEl,
    panelMetaFoldEl: panelMetaFoldEl,
    panelMetaSummaryEl: panelMetaSummaryEl,
    publish: publish,
    delay: LAMP_DELAY_MS
  });

  function wireLamp() { breath.wireLamp(); }

  function onCanvasState(payload) { breath.onCanvasState(payload); }

  function signalCanvasScroll() { breath.signalCanvasScroll(); }

  function collapseMetaSection() { breath.collapseMetaSection(); }

  function expandMetaSection() { breath.expandMetaSection(); }

  /** 收起来时那一行矮标题要报点什么：标准名最有用，没有就报场景。 */
  function renderFoldSummary() {
    if (!panelMetaSummaryEl) return;
    var std = panelStdNameEl ? String(panelStdNameEl.value || "").trim() : "";
    var scene = panelMetaSceneEl ? String(panelMetaSceneEl.value || "").trim() : "";
    breath.renderFoldSummary(std || scene || "—");
  }

  function activatePanel() {
    if (!panelRoot) return;
    panelRoot.hidden = false;
    fillSelect(panelTypeEl, TYPE_VALUES, TYPE_LABELS);
    fillSelect(panelDifficultyEl, DIFFICULTY_VALUES, {
      L1: "L1 基础", L2: "L2 中档", L3: "L3 难", L4: "L4 压轴"
    });
    bindFormChanges();
    renderTags();
    renderMounted();
    wireGhostCell("tag");
    wireGhostCell("topic");
    // 批次公共元数据：画布一滚动就收成一行矮标题；鼠标停在标题上才展开，
    // 移开鼠标不收起——老师正在填的字段不许被自动折叠抢走。
    if (panelMetaFoldEl) {
      panelMetaFoldEl.addEventListener("mouseenter", expandMetaSection);
      panelMetaFoldEl.addEventListener("click", function () {
        var open = panelMetaSecEl && panelMetaSecEl.getAttribute("data-fold") === "open";
        if (open) collapseMetaSection();
        else expandMetaSection();
      });
    }
    [panelFmtLatexEl, panelFmtBoxedEl].forEach(function (node) {
      if (!node) return;
      node.addEventListener("click", function () {
        chooseFormatFromPanel(node.getAttribute("data-format"));
      });
    });
    if (panelSwapEl) panelSwapEl.addEventListener("click", toggleSwapFromPanel);
    if (panelBackListEl) panelBackListEl.addEventListener("click", backToListFromPanel);
    if (panelApproveEl) panelApproveEl.addEventListener("click", function () { onApprove(false); });
    if (panelStashEl) panelStashEl.addEventListener("click", onStash);
    if (panelDeleteEl) panelDeleteEl.addEventListener("click", onDelete);
    if (dupBackEl) dupBackEl.addEventListener("click", function () { closeModal(dupModalEl); });
    if (dupForceEl) dupForceEl.addEventListener("click", function () {
      closeModal(dupModalEl);
      onApprove(true);
    });
    if (delCancelEl) delCancelEl.addEventListener("click", function () { closeModal(delModalEl); });
    if (delOkEl) delOkEl.addEventListener("click", onDeleteConfirm);
    if (panelAiAskEl) panelAiAskEl.addEventListener("input", renderAi);
    if (panelAiSendEl) panelAiSendEl.addEventListener("click", onAiSend);
    if (panelAiCleanEl) panelAiCleanEl.addEventListener("click", cleanViaHost);
    if (panelAiApplyEl) panelAiApplyEl.addEventListener("click", onAiApply);
    if (panelAiDiscardEl) panelAiDiscardEl.addEventListener("click", onAiDiscard);
    // 批次公共元数据：改一次，这一批所有题立刻跟着改
    [panelMetaYearEl, panelMetaRegionEl, panelMetaBodyEl, panelMetaSubjectEl].forEach(function (node) {
      if (!node) return;
      node.addEventListener("input", onMetaFieldChange);
      node.addEventListener("change", onMetaFieldChange);
    });
    if (panelMetaSceneEl) panelMetaSceneEl.addEventListener("change", onSceneChange);
    // 学校输入框：搜字典 → 选中即加；查不到就走 AI 补全 → 老师确认 → 建档。
    if (panelSchoolInputEl) {
      panelSchoolInputEl.addEventListener("input", function () {
        setSchoolError("");
        var query = String(panelSchoolInputEl.value || "").trim();
        if (!query) { hideSchoolMenu(); return; }
        searchSchools(query);
      });
      panelSchoolInputEl.addEventListener("focus", function () {
        var query = String(panelSchoolInputEl.value || "").trim();
        if (query) searchSchools(query);
      });
      panelSchoolInputEl.addEventListener("keydown", function (event) {
        if (String(event.key || "") !== "Enter") return;
        event.preventDefault();
        onSchoolEnter();
      });
      panelSchoolInputEl.addEventListener("blur", function () {
        window.setTimeout(hideSchoolMenu, 120);
      });
    }
    if (panelSchoolConfirmOkEl) panelSchoolConfirmOkEl.addEventListener("click", confirmSchoolCreate);
    if (panelSchoolConfirmCancelEl) {
      panelSchoolConfirmCancelEl.addEventListener("click", cancelSchoolConfirm);
    }
    // 交叉标签：场景决定候选排序；打一个字就模糊查；回车把新标签记进本地库。
    if (panelMetaExamTypeEl) {
      panelMetaExamTypeEl.addEventListener("input", function () {
        loadTags(String(panelMetaExamTypeEl.value || "").trim());
        if (panel.stdManual) setStdMode(false);
        renderTopLines({ flash: true });
      });
      panelMetaExamTypeEl.addEventListener("focus", function () {
        loadTags(String(panelMetaExamTypeEl.value || "").trim());
      });
      panelMetaExamTypeEl.addEventListener("keydown", function (event) {
        if (String(event.key || "") !== "Enter") return;
        event.preventDefault();
        onTagEnter();
      });
      panelMetaExamTypeEl.addEventListener("change", onMetaFieldChange);
      panelMetaExamTypeEl.addEventListener("blur", function () {
        window.setTimeout(hideTagMenu, 120);
      });
    }
    if (panelStdNameEl) {
      panelStdNameEl.addEventListener("input", onStdInput);
      panelStdNameEl.addEventListener("change", onStdInput);
    }
    wireIntake();
    loadScenes();
    loadMetaHistory();
    renderBatchMeta();
    renderAi();
    setFormatButtons("latex");
    setSwapButton(false);
    wireGhost(panelScrollEl || panelRoot);
    wireGhost(document.getElementById("epTree"));
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
      if (message.event === "editor.canvas_state") {
        // 画布的悬停与滚动：宿主只把它投给面板帧，面板据此亮边缘、收批次元数据
        if (state.slot === "stage.center") return;
        onCanvasState(message.payload || {});
        return;
      }
      if (message.event === "system.question_updated") {
        if (state.slot === "stage.center") consumeReceipts(message.payload);
        return;
      }
      if (message.event === "system.pending_updated") {
        // 中转站动了：入库与删除要把题从画布上撤下来，暂存只改内容不撤。
        if (state.slot === "stage.center") onPendingUpdated(message.payload);
        else onPanelPendingUpdated(message.payload);
        return;
      }
      if (message.event === "editor.collect_files") {
        // 宿主壳或辅助栏那边接到的文件，转进画布的收集筐：
        // 只有画布收，面板再收一遍就成了两份。
        if (state.slot !== "stage.center") return;
        var incoming = (message.payload && message.payload.files) || [];
        if (Array.isArray(incoming) && incoming.length) basketAdd(incoming);
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
      setMode("list");
      applyWidths();
      renderAll();
      wireIntake();
      if (sourceHintEl) sourceHintEl.textContent = "源码 · 整段源码直接编辑";
      startIdleWatch();
      // 首屏就是批次列表：中转站还空着就先把这批识别结果入池，好让老师有东西可点。
      refreshBatches().then(function (cards) {
        if (cards.length) return null;
        return seedBatch().then(function () { return refreshBatches(); });
      });
      restoreWorklist().then(function () {
        renderAll();
        saveWorklist();
        publishSelection();
      });
      hostCall("draft.load", { key: DRAFT_LAYOUT_KEY }).then(function (result) {
        var value = result && result.value;
        if (value && value.widths) normalizeWidths(value.widths);
        if (value && typeof value.swap === "boolean") applySwap(value.swap, false);
        applyWidths();
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
  /** 幽灵滚动条：只在真滚动时让滚动条浮出来，停手就淡回去（纯样式行为，不参与业务）。 */
  function wireGhost(node) {
    if (!node) return;
    var timer = 0;
    node.addEventListener("scroll", function () {
      node.classList.add("is-scrolling");
      window.clearTimeout(timer);
      timer = window.setTimeout(function () { node.classList.remove("is-scrolling"); }, GHOST_SCROLL_MS);
    }, { passive: true });
  }

  function bind() {
    bindSplit(document.getElementById("edSplitImage"), "image");
    bindSplit(document.getElementById("edSplitSource"), "source");
    document.addEventListener("focusin", function (event) {
      var node = event.target;
      if (node && node.getAttribute && node.getAttribute("data-field") != null) lastFieldNode = node;
    });
    applySwap(state.swap, false);
    setFormatButtons(state.format);
    [imageBodyEl, sourceBodyEl, renderBodyEl].forEach(function (node) {
      if (!node) return;
      wireGhost(node);
      node.addEventListener("scroll", function () {
        syncScroll(node);
        if (state.slot === "stage.center") signalCanvasScroll();
      });
    });
    wireLamp();
    // 三分钟没人碰就静默存回中转池：任何一次动手都算「有人在」，这里只做记账。
    ["pointerdown", "keydown", "wheel", "input"].forEach(function (type) {
      window.addEventListener(type, noteActivity, { passive: true, capture: true });
    });
    if (window.ResizeObserver && colsEl) {
      var observer = new window.ResizeObserver(function () {
        applyWidths();
        scheduleRender();
      });
      observer.observe(colsEl);
    }
    window.addEventListener("beforeunload", function () {
      stashOnUnload();
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
    version: "3.0.0-batch",
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
    applySwap: applySwap,
    toggleSwap: toggleSwap,
    saveItem: saveItem,
    applySelection: applySelection,
    selectionPayload: selectionPayload,
    jumpTo: jumpTo,
    poolCounts: poolCounts,
    // 审核台：批次列表、点入审核、存草稿、存回中转池
    refreshBatches: refreshBatches,
    renderBatchList: renderBatchList,
    openBatch: openBatch,
    backToList: backToList,
    backToListFromPanel: backToListFromPanel,
    publishView: publishView,
    setMode: setMode,
    stashOne: stashOne,
    onApprove: onApprove,
    onStash: onStash,
    onDelete: onDelete,
    autoSaveIdle: autoSaveIdle,
    noteActivity: noteActivity,
    // 批次公共元数据与接收区
    standardNameOf: standardNameOf,
    renderBatchMeta: renderBatchMeta,
    loadBatchMeta: loadBatchMeta,
    loadMetaHistory: loadMetaHistory,
    applyMetaSync: applyMetaSync,
    queueMetaSync: queueMetaSync,
    onMetaFieldChange: onMetaFieldChange,
    // 数据字典（军令 #28）：学校检索/建档、场景与交叉标签。
    addSchoolRecord: addSchoolRecord,
    searchSchools: searchSchools,
    confirmSchoolCreate: confirmSchoolCreate,
    requestSchoolSuggest: requestSchoolSuggest,
    loadTags: loadTags,
    pickTag: pickTag,
    onTagEnter: onTagEnter,
    loadScenes: loadScenes,
    // 标准名双向联动：自动/手动模式与「已更新」闪烁。
    stdLiveName: stdLiveName,
    setStdMode: setStdMode,
    flashStd: flashStd,
    ingestEntries: ingestEntries,
    // 收集筐（军令 #27）：探针要能看筐里有什么、能把文件塞进去。
    basket: function () {
      return state.basket.map(function (entry) {
        return { id: entry.id, name: entry.name, type: entry.type, size: entry.size, url: entry.url };
      });
    },
    basketAdd: basketAdd,
    basketRemove: basketRemove,
    basketGo: basketGo,
    // 探针要把假时钟拨快，三分钟那道闸门才认得出「没人操作」
    idleThreshold: function () { return IDLE_MS; },
    tickIdle: function () {
      lastActivityAt = Date.now() - IDLE_MS - 1000;
    }
  };
})();
