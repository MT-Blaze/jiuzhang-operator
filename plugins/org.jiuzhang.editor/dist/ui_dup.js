/**
 * ui_dup.js —— 查重拦截的**画布侧**对比浮层（军令 #31）。
 *
 * 为什么长在画布而不是辅助栏：辅助栏那帧按军令 #23 绝不放渲染预览，而这一窗要比的
 * 恰恰是**渲染**结果——同一句话两种 LaTeX 打法（`\leq` 与 `\le`）、选项字母顺序不同，
 * 只有渲染出来才看得出是不是同一道题。画布本来就带着 KaTeX 与富文本渲染器，
 * 对比浮层放这里既不越界，也不必另造一套渲染。
 *
 * **这一层只画不裁**：浮层里一颗按钮都没有（军令 #23：画布里只许有题目内容），
 * 三个裁决动作住在右侧辅助栏的段三。老师一边看这里的渲染对比，一边在那边拍板；
 * 辅助栏把「打开 / 关闭」经宿主投过来（`editor.dup_review`），本模块照办。
 * 判据全在底座（`pending_dedupe`），插件一个字节都不自己造。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var appendBody = deps.appendBody;
    var appendRich = deps.appendRich;
    var el = deps.el;
    var root = deps.dom.root;
    var modalEl = deps.dom.dupReviewEl;
    var mineEl = deps.dom.dupMineEl;
    var theirsEl = deps.dom.dupTheirEl;
    var noteEl = deps.dom.dupNoteEl;
    var blockEl = deps.dom.dupBlockEl;

    /** 画布边缘的红呼吸灯：命中即亮，裁决完或换题即熄。 */
    function paintLamp(on) {
      if (!root) return;
      if (on) root.setAttribute("data-dup", "on");
      else root.removeAttribute("data-dup");
    }

    /** 答案对象 → 一行可读文本；没写答案就回空串，绝不当成「答案不同」。 */
    function answerText(answer) {
      if (!answer || typeof answer !== "object") return "";
      var keys = answer.choice_keys;
      if (Array.isArray(keys) && keys.length) {
        return keys.map(function (key) { return String(key); }).join("");
      }
      if (answer.content != null && String(answer.content).trim()) return String(answer.content);
      if (answer.final != null && String(answer.final).trim()) return String(answer.final);
      return "";
    }

    /** 把一份标准题目文档渲染进容器：题干、选项、答案。**不显示源码**。 */
    function renderDoc(target, doc) {
      if (!target) return;
      target.textContent = "";
      var body = doc && typeof doc === "object" ? doc : {};
      var stem = body.stem == null ? "" : String(body.stem);
      if (stem.trim()) {
        appendBody(target, stem);
      } else {
        target.appendChild(el("p", "ed-dup-empty", "（这一侧没有题干）"));
      }
      var options = Array.isArray(body.options) ? body.options : [];
      options.forEach(function (option) {
        var line = el("p", "ed-dup-option");
        var key = option && option.key != null ? String(option.key) : "";
        line.appendChild(el("span", "ed-dup-key", key ? key + ". " : "· "));
        appendRich(line, option && option.content != null ? String(option.content) : "");
        target.appendChild(line);
      });
      var answer = answerText(body.answer);
      var foot = el("p", "ed-dup-answer");
      foot.appendChild(el("span", "ed-dup-answer-key", "答案 "));
      if (answer) appendRich(foot, answer);
      else foot.appendChild(document.createTextNode("（这一侧没写答案）"));
      target.appendChild(foot);
    }

    /** 浮层里那句「两边答案不同」的红字：由辅助栏把拦截结论传进来。 */
    function paintBlock(blocked) {
      if (!blockEl) return;
      if (blocked) {
        blockEl.textContent = "两边答案不同：覆盖会拿这边的答案盖掉那边的，"
          + "合并会把两套互相矛盾的解法并进同一道题。请放弃存入，回池子里核对答案。";
        blockEl.hidden = false;
      } else {
        blockEl.textContent = "";
        blockEl.hidden = true;
      }
    }

    function noteText(report) {
      if (!report) return "";
      var existingId = String(report.existing_id || "");
      if (report.level === "identical") {
        return "主库里已经有同一道题（" + existingId + "）。左右是渲染结果，"
          + "可以覆盖、合并为解析二，或放弃存入。";
      }
      var percent = Math.round((Number(report.similarity) || 0) * 100);
      return "主库里有一道高度相似的题（" + existingId + "，相似度 " + percent
        + "%）。请对比两侧渲染结果再决定。";
    }

    /** 辅助栏要求开窗：画两侧渲染、点灯、显示。 */
    function show(payload) {
      var report = payload && payload.report ? payload.report : payload;
      if (!report || typeof report !== "object") return;
      renderDoc(mineEl, report.incoming);
      renderDoc(theirsEl, report.existing);
      if (noteEl) {
        noteEl.textContent = report.existing_id
          ? noteText(report)
          : "主库里那道题已经不在了，这一条可以直接存入。";
      }
      paintBlock(Boolean(report.blocked) || (Boolean(report.answer) && report.answer.same === false));
      paintLamp(true);
      if (modalEl) modalEl.hidden = false;
    }

    /**
     * 只点灯、不开窗：后台查重一命中就把红灯亮起来（老师还没点任何按钮）。
     * 红字与裁决动作在辅助栏；画布这一盏灯只负责在余光里报「这道题主库里有」。
     */
    function notice(payload) {
      var report = payload && payload.report ? payload.report : payload;
      if (!report || typeof report !== "object") return;
      paintLamp(true);
      paintBlock(Boolean(report.blocked) || (Boolean(report.answer) && report.answer.same === false));
    }

    /** 收盘：熄灯、关窗、清空两侧。辅助栏裁决完或换题时调。 */
    function clear() {
      paintLamp(false);
      paintBlock(false);
      if (noteEl) noteEl.textContent = "";
      if (modalEl) modalEl.hidden = true;
      if (mineEl) mineEl.textContent = "";
      if (theirsEl) theirsEl.textContent = "";
    }

    /** 只更新拦截口径（辅助栏写完被后端拦下时用），不重画整窗。 */
    function markBlocked(blocked) {
      paintBlock(Boolean(blocked));
      if (blocked) paintLamp(true);
    }

    /** Esc 关窗：浮层不设焦点陷阱（它没有可操作控件），但键盘总得能关掉它。 */
    document.addEventListener("keydown", function (event) {
      if (!modalEl || modalEl.hidden) return;
      if (event.key !== "Escape") return;
      event.preventDefault();
      clear();
    });

    return {
      clear: clear,
      markBlocked: markBlocked,
      notice: notice,
      renderDoc: renderDoc,
      show: show,
    };
  }

  global.JzoEditorDup = { create: create };
})(window);
