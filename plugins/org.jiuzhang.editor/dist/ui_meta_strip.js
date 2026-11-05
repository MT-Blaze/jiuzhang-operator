/**
 * ui_meta_strip.js —— 渲染栏每题顶部的只读信息条（待审进度 + 原卷题号 / 题型 / 分值 / 难度）。
 *
 * 这是一块可以整块下架的展示能力：删掉本文件、index.html 里的一行 <script>、
 * ui_columns.js 里的一行调用与 layout_canvas.css 的 .ed-q-meta 段，渲染栏即回原样。
 * 只读展示，不挂任何点击/键盘事件；要改元数据请去右侧辅助栏。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var el = deps.el;
    var DIFFICULTY_LABELS = deps.difficultyLabels || {};
    var TYPE_LABELS = deps.typeLabels || {};

    // 单题 AI 入口（终极军令 任务三）：识别与解析两颗钮挂在只读条最右侧，
    // 动作由 ui_ai_copilot 统一委托。不传回调就整组不画——只读条仍可整块下架。
    function aiButtons(index) {
      var onAiIdentify = deps.onAiIdentify;
      if (typeof onAiIdentify !== "function") return null;
      var wrap = el("span", "ed-q-meta-ais");
      [
        ["ocr", "✨ AI 识别本题", "识别结果整题替换当前正文，并静默存入待审池；有人工修改时会先问"],
        ["solve", "✨ 解析本题", "只补答案与解析，题干与选项原样保留；完成后静默存入待审池"]
      ].forEach(function (spec) {
        var button = el("button", "ed-q-meta-ai", spec[1]);
        button.type = "button";
        button.setAttribute("data-index", String(index));
        button.setAttribute("data-mode", spec[0]);
        button.setAttribute("aria-label", spec[1].replace("✨ ", "") + " · 第 " + (index + 1) + " 题");
        button.setAttribute("title", spec[2]);
        wrap.appendChild(button);
      });
      // 只读条本身不挂任何事件：点击由渲染容器统一委托给 ui_ai_copilot。
      return wrap;
    }

    function scoreText(raw) {
      var text = String(raw == null ? "" : raw).trim();
      if (!text) return "分值未设";
      return /分$/.test(text) ? text : text + "分";
    }

    /** 题号只认原卷：从私有元数据 source.question_no 读，没写就不硬编一个序号。 */
    function questionNo(item, data) {
      var meta = data || {};
      var source = (item && item.question && item.question.source) || {};
      var raw = meta.question_no != null && String(meta.question_no).trim()
        ? meta.question_no : source.question_no;
      return String(raw == null ? "" : raw).trim();
    }

    /** 顶部第一格：池内进度 + 原卷题号，例如 ``5 / 19 (原卷第13题)``。 */
    function progressText(item, index, data, total) {
      var count = Number(total) || 0;
      var head = (index + 1) + " / " + (count > 0 ? count : "?");
      var no = questionNo(item, data);
      return no ? head + " (原卷第" + no + "题)" : head;
    }

    function render(item, index, parsed, meta, total) {
      var data = meta || {};
      var type = String(data.type || (parsed && parsed.type) || "");
      var difficulty = String(data.difficulty || "");
      var strip = el("p", "ed-q-meta");
      strip.setAttribute("role", "note");
      strip.setAttribute("aria-label", "题目信息（只读）");
      strip.setAttribute("title", "只读信息；要修改请到右侧辅助栏");
      [
        progressText(item, index, data, total),
        TYPE_LABELS[type] || "题型待定",
        scoreText(data.score),
        DIFFICULTY_LABELS[difficulty] || "难度未设"
      ].forEach(function (text) {
        strip.appendChild(el("span", "ed-q-meta-item", text));
      });
      var buttons = aiButtons(index);
      if (buttons) strip.appendChild(buttons);
      return strip;
    }

    return { render: render };
  }

  global.JzoEditorMetaStrip = { create: create };
})(window);
