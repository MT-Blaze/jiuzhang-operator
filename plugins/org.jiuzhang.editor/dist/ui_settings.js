/**
 * ui_settings.js —— 录题偏好（可整块下架）。
 *
 * 把 AI 提示词、预设难度、自动暂存三件高频业务参数摆在右侧辅助栏里，
 * 老师录题时顺手就调，不用退回设置控制台。整块移除只需删：
 * 本文件、panel_biz.css、index.html 里的 #epBizSec、plugin.js 里两处 settings 依赖。
 *
 * 偏好经宿主 draft.save / draft.load 代持（键 editor:v2:prefs），插件不碰浏览器
 * 本地存储；两帧之间只走宿主总线 editor.settings —— 面板改、画布收，不直连。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var hostCall = deps.hostCall;
    var publish = deps.publish;

    var DRAFT_KEY = "editor:v2:prefs";
    var DIFFICULTY_VALUES = coreState.DIFFICULTY_VALUES;
    var DIFFICULTY_LABELS = coreState.DIFFICULTY_LABELS;
    var DEFAULTS = { ai_prompt: true, autosave: true, default_difficulty: "" };

    var values = Object.assign({}, DEFAULTS);
    var listeners = [];
    var mounted = false;

    var secEl = document.getElementById("epBizSec");
    var aiEl = document.getElementById("epBizAi");
    var difficultyEl = document.getElementById("epBizDifficulty");
    var autosaveEl = document.getElementById("epBizAutosave");
    var aiSecEl = document.getElementById("epAiSec");

    /** 只收合法值：草稿写坏就回默认，绝不让一个坏字段把三个开关一起带崩。 */
    function sanitize(raw) {
      var out = Object.assign({}, DEFAULTS);
      if (!raw || typeof raw !== "object") return out;
      if (typeof raw.ai_prompt === "boolean") out.ai_prompt = raw.ai_prompt;
      if (typeof raw.autosave === "boolean") out.autosave = raw.autosave;
      if (typeof raw.default_difficulty === "string"
        && (raw.default_difficulty === "" || DIFFICULTY_VALUES.indexOf(raw.default_difficulty) >= 0)) {
        out.default_difficulty = raw.default_difficulty;
      }
      return out;
    }

    function emit() {
      listeners.forEach(function (fn) { fn(values); });
    }

    /** 把当前值落到 DOM 上：两帧都跑一遍，画布那帧只关心 autosave。 */
    function applyLocal() {
      if (aiSecEl) aiSecEl.hidden = values.ai_prompt === false;
      if (aiEl) aiEl.checked = values.ai_prompt !== false;
      if (autosaveEl) autosaveEl.checked = values.autosave !== false;
      if (difficultyEl) difficultyEl.value = values.default_difficulty;
      emit();
    }

    function save() {
      hostCall("draft.save", { key: DRAFT_KEY, value: values }).catch(function () {
        // 草稿代持失败只影响下次启动的默认值，不拦老师当场调参。
      });
    }

    /** 面板改值：先本地生效，再交宿主存草稿，并广播给画布那一帧。 */
    function update(patch) {
      values = sanitize(Object.assign({}, values, patch));
      applyLocal();
      save();
      publish("editor.settings", { from: "panel", settings: values });
    }

    /** 画布收到面板的广播：只消费，不再回播，避免两帧互相回声。 */
    function applyRemote(raw) {
      var payload = (raw && raw.settings) || raw || {};
      values = sanitize(payload);
      applyLocal();
    }

    function fillDifficulty() {
      if (!difficultyEl) return;
      difficultyEl.textContent = "";
      var follow = document.createElement("option");
      follow.value = "";
      follow.textContent = "跟随识别";
      difficultyEl.appendChild(follow);
      DIFFICULTY_VALUES.forEach(function (code) {
        var option = document.createElement("option");
        option.value = code;
        option.textContent = DIFFICULTY_LABELS[code] || code;
        difficultyEl.appendChild(option);
      });
      difficultyEl.value = values.default_difficulty;
    }

    /** 只由辅助栏那帧的 activatePanel 调用：画布那一帧的 DOM 没人看，不挂监听。 */
    function mount() {
      if (!secEl) return;
      fillDifficulty();
      if (!mounted) {
        mounted = true;
        if (aiEl) {
          aiEl.addEventListener("change", function () {
            update({ ai_prompt: aiEl.checked });
          });
        }
        if (difficultyEl) {
          difficultyEl.addEventListener("change", function () {
            update({ default_difficulty: difficultyEl.value });
          });
        }
        if (autosaveEl) {
          autosaveEl.addEventListener("change", function () {
            update({ autosave: autosaveEl.checked });
          });
        }
      }
      secEl.hidden = false;
      applyLocal();
    }

    function onChange(fn) {
      if (typeof fn === "function") listeners.push(fn);
    }

    function aiPromptOn() { return values.ai_prompt !== false; }
    function autosaveOn() { return values.autosave !== false; }
    function presetDifficulty() { return values.default_difficulty; }

    // 开机先向宿主取本工作区的偏好；取不到就按默认值跑，不挡任何录题动作。
    hostCall("draft.load", { key: DRAFT_KEY }).then(function (result) {
      values = sanitize(result && result.value);
      applyLocal();
    }).catch(function () { applyLocal(); });

    return {
      DRAFT_KEY: DRAFT_KEY,
      DEFAULTS: DEFAULTS,
      applyLocal: applyLocal,
      applyRemote: applyRemote,
      aiPromptOn: aiPromptOn,
      autosaveOn: autosaveOn,
      mount: mount,
      onChange: onChange,
      presetDifficulty: presetDifficulty,
      update: update,
      values: function () { return Object.assign({}, values); },
    };
  }

  global.JzoEditorSettings = { create: create };
})(window);
