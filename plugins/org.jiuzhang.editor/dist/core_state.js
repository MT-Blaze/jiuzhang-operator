/**
 * core_state.js —— 录题工作台的常量表与三个共享盒子（pending / state / panel）。
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）
 *
 * 这里只有「值」，没有行为：额度、键名、下拉选项都集中在这一份，
 * 别的模块领 coreState 一个命名空间就够，不再逐个领常量别名。
 * state / panel / pending 是同一份引用，两帧各自改的是自己那一侧。
 */
(function (global) {
  "use strict";

  function create() {
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

  var pending = new Map();

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
    // 清洗预览：只存内存，逐段等老师点【采用】才回填；画布不在时整块降级只报摘要。
    clean: null,
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
    // 学校建档三件套：AI 补全好了没（ready）、请求发出去没（busy）、入库按钮在忙没（approveBusy）。
    schoolConfirmReady: false,
    schoolConfirmBusy: false,
    approveBusy: false,
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

    return {
      AI_ASK_MAX: AI_ASK_MAX,
      AI_REQUEST_TIMEOUT_MS: AI_REQUEST_TIMEOUT_MS,
      AI_STATE_LABELS: AI_STATE_LABELS,
      COMMAND_QUESTION_ID_RE: COMMAND_QUESTION_ID_RE,
      DEFAULT_IMAGE_RATIO: DEFAULT_IMAGE_RATIO,
      DEFAULT_SOURCE_RATIO: DEFAULT_SOURCE_RATIO,
      DEV_NS: DEV_NS,
      DIFFICULTY_VALUES: DIFFICULTY_VALUES,
      DRAFT_LAYOUT_KEY: DRAFT_LAYOUT_KEY,
      DRAFT_META_KEY: DRAFT_META_KEY,
      DRAFT_RECEIPT_KEY: DRAFT_RECEIPT_KEY,
      DRAFT_WORKLIST_KEY: DRAFT_WORKLIST_KEY,
      FIELD_MAX: FIELD_MAX,
      FORMATS: FORMATS,
      GHOST_DELAY_MS: GHOST_DELAY_MS,
      GHOST_SCROLL_MS: GHOST_SCROLL_MS,
      IDLE_MS: IDLE_MS,
      IDLE_TICK_MS: IDLE_TICK_MS,
      LAMP_DELAY_MS: LAMP_DELAY_MS,
      LAYOUT_DRAFT_MS: LAYOUT_DRAFT_MS,
      OPTION_KEYS: OPTION_KEYS,
      PANEL_DRAFT_RETRY_MS: PANEL_DRAFT_RETRY_MS,
      PANE_MIN: PANE_MIN,
      PLUGIN_ID: PLUGIN_ID,
      PROTOCOL: PROTOCOL,
      RECEIPT_RETRY_MAX: RECEIPT_RETRY_MAX,
      RECEIPT_RETRY_MS: RECEIPT_RETRY_MS,
      RENDER_DEBOUNCE_MS: RENDER_DEBOUNCE_MS,
      REQUEST_TIMEOUT_MS: REQUEST_TIMEOUT_MS,
      SELECTION_MS: SELECTION_MS,
      SOURCE_MAX: SOURCE_MAX,
      SPLIT_W: SPLIT_W,
      STEM_MAX: STEM_MAX,
      TAG_LIMIT: TAG_LIMIT,
      TOPIC_ID_RE: TOPIC_ID_RE,
      TOPIC_LIMIT: TOPIC_LIMIT,
      TYPE_LABELS: TYPE_LABELS,
      TYPE_VALUES: TYPE_VALUES,
      WORKLIST_DRAFT_MS: WORKLIST_DRAFT_MS,
      panel: panel,
      pending: pending,
      state: state,
    };
  }

  global.JzoEditorCoreState = { create: create };
})(window);
