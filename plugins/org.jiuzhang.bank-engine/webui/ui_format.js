/**
 * 题库视图的通用格式化：标签翻译、原卷行、迁移标记、分页器与答案口径。
 *
 * 列表、详情与待审视图共用；这里不含任何取数逻辑。
 */
(function (global) {
  "use strict";

  function create() {
    function el(tag, className, text) {
      var node = document.createElement(tag);
      if (className) node.className = className;
      if (text != null) node.textContent = text;
      return node;
    }

    // 契约 2.0 只发 L1–L4；旧键留着只为渲染历史缓存里的题卡
    function difficultyLabel(value) {
      return {
        L1: "基础", L2: "中档", L3: "难", L4: "压轴",
        basic: "基础", medium: "中档", hard: "难", novel: "压轴"
      }[value] || value;
    }

    function typeLabel(value) {
      return {
        single_choice: "单选", multiple_choice: "多选", fill_blank: "填空",
        solution: "解答", proof: "证明", unknown: "待定"
      }[value] || value;
    }

    function sourceLine(question) {
      var source = question.source || {};
      return [source.paper_title, source.question_no ? "原卷 " + source.question_no + " 题" : ""]
        .filter(Boolean).join(" · ");
    }

    function migrationFlags(question) {
      var entry = (question.extensions || {})["org.jiuzhang.core-bank.migration"];
      var flags = entry && entry.flags;
      return Array.isArray(flags) ? flags : [];
    }

    // 列表视图与待审视图的分页器是同一个形状（上一页—页码—下一页），只差数据源与翻页动作。
    function mountPager(page, pages, total, onGo) {
      var pager = el("div", "cb-pager");
      var prev = el("button", "cb-btn", "上一页");
      prev.type = "button";
      prev.disabled = page <= 1;
      prev.addEventListener("click", function () { if (page > 1) onGo(page - 1); });
      var next = el("button", "cb-btn", "下一页");
      next.type = "button";
      next.disabled = page >= pages;
      next.addEventListener("click", function () { if (page < pages) onGo(page + 1); });
      pager.appendChild(prev);
      pager.appendChild(el("span", null, "第 " + page + " / " + pages + " 页 · 共 " + total + " 题"));
      pager.appendChild(next);
      return pager;
    }

    // 答案口径只有一处真相：选项题报选项键、其余报正文，两者都没有就是「待补」。
    function answerText(question) {
      var answer = question.answer;
      if (answer && answer.kind === "choice") return (answer.choice_keys || []).join("、");
      if (answer && answer.content) return String(answer.content);
      return "";
    }

    return {
      el: el,
      difficultyLabel: difficultyLabel,
      typeLabel: typeLabel,
      sourceLine: sourceLine,
      migrationFlags: migrationFlags,
      mountPager: mountPager,
      answerText: answerText
    };
  }

  global.JzoBankFormat = { create: create };
})(window);
