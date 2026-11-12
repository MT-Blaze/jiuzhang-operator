/**
 * ui_answer_editor.js —— 辅助栏第三层的「答案 / 解析」两只可编辑框。
 *
 * 不是整段源码，也不是渲染预览：只认 solution 环境里的答案行与解析正文。
 * 改动经宿主 editor.apply_patch 广播给画布，由画布改源码、再回发 stage.selection；
 * 两条框都在失焦或停顿后回填，老师边打字不会被回显抢走光标。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var panel = coreState.panel;
    var hostCall = deps.hostCall;
    var parseExamSource = deps.parseExamSource;
    var patchIdFor = deps.patchIdFor;
    var answerEl = deps.dom.panelAnswerInputEl;
    var analysisEl = deps.dom.panelAnalysisInputEl;
    var noteEl = deps.dom.panelAnswerNoteEl;
    var timer = 0;
    var suppress = false;
    var lastKey = "";
    var lastSent = { answer: "", solution: "" };

    function say(text) {
      if (noteEl) noteEl.textContent = text;
    }

    function currentSource() {
      return panel.selection ? String(panel.selection.source || "") : "";
    }

    /** 只画，不发：选区回显、换题、清空都走这里。 */
    function render() {
      if (!answerEl || !analysisEl) return;
      var key = panel.selection ? String(panel.selection.key || "") : "";
      var focused = document.activeElement === answerEl || document.activeElement === analysisEl;
      // 老师正在这两只框里打字：回显让位，等失焦后的下一次选区再对账。
      if (focused && key === lastKey) return;
      var parsed = currentSource() ? parseExamSource(currentSource()) : null;
      suppress = true;
      answerEl.value = parsed ? String(parsed.answer || "") : "";
      analysisEl.value = parsed ? String(parsed.analysis || "") : "";
      answerEl.disabled = !key;
      analysisEl.disabled = !key;
      suppress = false;
      if (key !== lastKey) {
        lastKey = key;
        lastSent = { answer: "", solution: "" };
      }
      if (!key) say("选中一道题后才能改答案与解析。");
      else if (!parsed || !parsed.hasSolution) say("源码里还没有 solution 环境，保存时会自动补一段。");
      else say("改完自动回填画布，未入库");
    }

    function clear() {
      window.clearTimeout(timer);
      lastKey = "";
      lastSent = { answer: "", solution: "" };
      if (answerEl) {
        answerEl.value = "";
        answerEl.disabled = true;
      }
      if (analysisEl) {
        analysisEl.value = "";
        analysisEl.disabled = true;
      }
      say("选中一道题后才能改答案与解析。");
    }

    function sendField(field) {
      if (suppress || !panel.selection) return;
      var node = field === "answer" ? answerEl : analysisEl;
      if (!node) return;
      var value = String(node.value || "").trim();
      if (!value) {
        say(field === "answer" ? "答案为空，未回填。" : "解析为空，未回填。");
        return;
      }
      var key = String(panel.selection.key || "");
      if (lastSent[field] === value) return;
      hostCall("editor.apply_patch", {
        id: patchIdFor(key),
        field: field,
        value: value
      }).then(function (result) {
        if (!result || !result.ok) return;
        lastSent[field] = value;
        say((field === "answer" ? "答案" : "解析") + "已回填画布，未入库");
      }, function (error) {
        say((field === "answer" ? "答案" : "解析") + "回填失败："
          + ((error && error.message) || "宿主没回应"));
      });
    }

    function queue(field) {
      window.clearTimeout(timer);
      timer = window.setTimeout(function () { sendField(field); }, 600);
    }

    function wire() {
      [["answer", answerEl], ["solution", analysisEl]].forEach(function (pair) {
        var node = pair[1];
        if (!node) return;
        node.addEventListener("input", function () { queue(pair[0]); });
        node.addEventListener("change", function () {
          window.clearTimeout(timer);
          sendField(pair[0]);
        });
      });
    }

    return { clear: clear, render: render, wire: wire };
  }

  global.JzoEditorAnswerEditor = { create: create };
})(window);
