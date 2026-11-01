/**
 * core_ai_fields.js —— plugin.js 的「只动题干段」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var DEV_NS = coreState.DEV_NS;
    var FIELD_MAX = coreState.FIELD_MAX;

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

    return {
      devBlock: devBlock,
      envSpan: envSpan,
      fieldAtOffset: fieldAtOffset,
      fieldLabel: fieldLabel,
      fieldRanges: fieldRanges,
      itemKey: itemKey,
      keyFromPatchId: keyFromPatchId,
      makeItem: makeItem,
      patchIdFor: patchIdFor,
      replaceField: replaceField,
    };
  }

  global.JzoEditorAiFields = { create: create };
})(window);
