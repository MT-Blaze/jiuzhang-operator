/**
 * core_exam_source.js —— plugin.js 的「exam-zh 源码」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
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

  // 原卷题干常自带作答括号（全角/半角、中间有空格或没有都算）。
  // 只要题干里已经有一个空括号，就绝不再追加——否则出现「（ ）（  ）」。
  var EMPTY_BRACKET = /[（(][ \t\u3000]*[）)]/;
  // 旧版追加逻辑留下的连体空括号：并成一个，多出的那截直接收掉。
  var DUP_BRACKET = /([（(][ \t\u3000]*[）)])(?:[ \t]*[（(][ \t\u3000]*[）)])+/g;

  function ensureChoiceBracket(stem, multi) {
    var text = String(stem == null ? "" : stem).replace(/\s+$/, "");
    text = text.replace(DUP_BRACKET, "$1");
    if (multi && text.indexOf("（多选）") < 0) text += "（多选）";
    if (!EMPTY_BRACKET.test(text)) text += "（  ）";
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

  /**
   * 源码 → 回写池内的补丁：只交出题面四件（题型/题干/选项/答案/解析）。
   * 认不全就 ``ok=false``，由调用方决定「先别存」——绝不拿半截解析结果覆盖旧文档。
   * ``base.type`` 用于保留源码看不出来的证明题形态（problem 环境本身不分证明/解答）。
   */
  function sourceToPatch(text, base) {
    var parsed = parseExamSource(text);
    var blockers = (parsed.errors || []).filter(function (line) {
      return line.indexOf("\\fillin 方括号内容按提示处理") < 0;
    });
    if (blockers.length) return { ok: false, errors: blockers, patch: null };
    var type = parsed.type || String((base && base.type) || "solution");
    if (type === "solution" && base && base.type === "proof") type = "proof";
    var patch = { type: type, stem: parsed.stem, solution: parsed.analysis || "" };
    if (type === "single_choice" || type === "multiple_choice") {
      patch.options = parsed.choices.map(function (content, position) {
        return { key: "ABCDEFGH".charAt(position), content: String(content == null ? "" : content) };
      });
      var letters = String(parsed.answer || "").toUpperCase().replace(/[^A-H]/g, "").split("");
      var unique = [];
      letters.forEach(function (letter) {
        if (unique.indexOf(letter) < 0) unique.push(letter);
      });
      if (!unique.length) {
        return { ok: false, errors: ["答案没写选项字母"], patch: null };
      }
      if (type === "single_choice" && unique.length > 1) {
        return { ok: false, errors: ["单选只能有一个答案字母"], patch: null };
      }
      patch.answer = { kind: "choice", choice_keys: unique, final: unique.join("") };
    } else {
      patch.options = [];
      var value = String(parsed.answer == null ? "" : parsed.answer);
      patch.answer = {
        kind: type === "fill_blank" ? "expression" : "text",
        content: value,
        final: value
      };
    }
    return { ok: true, errors: [], patch: patch };
  }

  /**
   * 这里曾经有一份本地清洗规则（定界符归一 + CRLF），判据 1.6 把它收走了：
   * 规则表只准有一处，就是底座的 app/core/latex_style_dict.py。
   * 要洗源码一律发 hostCall("text.clean_latex", {mode: "exam_source"})，
   * 单题走 ui_ai.js 的 cleanViaHost（带预览），整批走 core_commands.js 的内部命令。
   */

    return {
      answerLetters: answerLetters,
      buildExamSource: buildExamSource,
      detectType: detectType,
      ensureChoiceBracket: ensureChoiceBracket,
      matchEnv: matchEnv,
      parseExamSource: parseExamSource,
      solutionBlock: solutionBlock,
      sourceToPatch: sourceToPatch,
      splitChoices: splitChoices,
    };
  }

  global.JzoEditorExamSource = { create: create };
})(window);
