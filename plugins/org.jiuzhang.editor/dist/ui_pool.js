/**
 * ui_pool.js —— 重题池**自己的那一屏**（军令 #32 · 第五步，判据 5.1）。
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）
 *
 * 为什么再开一屏：#31 的查重对比是一只浮层，它压在审核三栏上，老师看完得关掉、
 * 再翻回批次列表找下一条——重题池攒了三五十条时，这条路每一步都是浪费。
 * 现在池子有自己的画布（画布第三种模式 `pool`），与审核三栏物理分开：
 * 左边主库原题、右边池内这一条，两边都是**渲染**结果，不比源码、不显示源码栏。
 *
 * 这一屏**一颗按钮都不放**（军令 #23 铁律：画布里只许有题目内容）。
 * 档位、四个动作、锁死说明、返回审核全住右侧辅助栏（ui_pool_panel.js），
 * 开合与选中的条目由辅助栏经宿主投过来（`editor.pool_review`）。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var PLUGIN_ID = coreState.PLUGIN_ID;
    var publish = deps.publish;
    var state = coreState.state;
    var renderDoc = deps.renderDoc;
    var setMode = deps.setMode;
    var canvasEl = deps.dom.poolCanvasEl;
    var incomingEl = deps.dom.poolIncomingEl;
    var mainEl = deps.dom.poolMainEl;
    var noteEl = deps.dom.poolNoteEl;
    var root = deps.dom.root;
    var warnEl = deps.dom.poolWarnEl;

    var currentId = "";

    /** 红灯只在这屏亮（判据 5.2）：样式已按 data-mode="pool" 收口，这里只管开关。 */
    function paintLamp(on) {
      if (!root) return;
      if (on) root.setAttribute("data-dup", "on");
      else root.removeAttribute("data-dup");
    }

    /** 抬头那一行：只说「在看哪一条、像到什么程度」，措辞用底座的 label。 */
    function noteText(entry) {
      var bits = [];
      var label = String(entry.label || "");
      var percent = Number(entry.percent) || 0;
      bits.push(label ? label + "（" + percent + "%）" : "像的程度 " + percent + "%");
      if (entry.main_id) bits.push("主库 " + entry.main_id);
      if (entry.item_id) bits.push("池内 " + entry.item_id);
      if (entry.batch_id) bits.push("批次 #" + entry.batch_id);
      if (entry.source_name) bits.push(entry.source_name);
      return "重题池 · " + bits.join(" · ") + " · 左右都是渲染结果，裁决在右侧辅助栏。";
    }

    /** 答案明确不同与「主库那道已不在」：两句都只报事实，动作在辅助栏锁。 */
    function warnText(entry) {
      var answer = entry.answer && typeof entry.answer === "object" ? entry.answer : {};
      if (answer.mismatch) {
        return "两边答案不同（主库：" + (answer.main || "没写") + " ／ 这条："
          + (answer.incoming || "没写") + "）。合并元数据与新增解析已被锁死，只能选「不重复」或「删除」。";
      }
      if (entry.existing_missing || !entry.main_id) {
        return "主库那道原题已经不在了：这一条没有可并的目标，只能选「不重复」存进主库，或「删除」。";
      }
      return "";
    }

    /** 辅助栏选中了某一条：把两侧渲染画出来，并切到池子那一屏。 */
    function show(entry) {
      if (!entry || typeof entry !== "object") return;
      currentId = String(entry.pool_id || "");
      setMode("pool");
      if (noteEl) noteEl.textContent = noteText(entry);
      if (renderDoc) {
        renderDoc(mainEl, entry.existing);
        renderDoc(incomingEl, entry.incoming);
      }
      var warn = warnText(entry);
      if (warnEl) {
        warnEl.textContent = warn;
        warnEl.hidden = !warn;
      }
      // 左右两栏的标题按实际身份改写：没有主库原题时右边那句「池内这一条」还是对的，
      // 左边得说「主库原题（已不在）」。
      var heads = canvasEl ? canvasEl.querySelectorAll(".ed-dup-head") : [];
      if (heads.length >= 2 && (entry.existing_missing || !entry.main_id)) {
        heads[0].textContent = "主库原题（已不在）";
      } else if (heads.length >= 2) {
        heads[0].textContent = "主库原题";
      }
      paintLamp(true);
    }

    /**
     * 收盘：灯熄、清空两侧，回到老师来时的地方。
     *
     * 画布还留着这一批的题就回三栏审核；题都审完（或压根没开批次）才回批次列表——
     * 这条判断只认 state.items，不去问后端要数，免得来回跳屏时多一次无谓请求。
     *
     * `notifyPanel` 默认带上：画布这边是**被**辅助栏叫开的，也是被它叫回的吗？
     * 不一定——老师可能按 Esc 自己退。谁先起的头，另一方就得知道，否则辅助栏还
     * 把这条当「已选中」亮着。辅助栏自己发的收窗不再回话（notifyPanel=false）。
     */
    function clear(reason, notifyPanel) {
      currentId = "";
      paintLamp(false);
      if (noteEl) noteEl.textContent = "";
      if (warnEl) {
        warnEl.textContent = "";
        warnEl.hidden = true;
      }
      if (mainEl) mainEl.textContent = "";
      if (incomingEl) incomingEl.textContent = "";
      if (state.mode !== "pool") return;
      setMode(state.items.length ? "review" : "list");
      if (notifyPanel !== false && publish) {
        publish("editor.pool_review", {
          pluginId: PLUGIN_ID, from: "canvas", phase: "closed",
          reason: String(reason || "user_close")
        });
      }
    }

    /** Esc：关这一屏。浮层没有可圈的焦点（它一颗控件都没有），键盘总得能退出。 */
    document.addEventListener("keydown", function (event) {
      if (event.key !== "Escape") return;
      if (state.slot !== "stage.center" || state.mode !== "pool") return;
      event.preventDefault();
      clear("user_esc");
    });

    function isOpen() {
      return Boolean(currentId);
    }

    return {
      clear: clear,
      currentId: function () { return currentId; },
      isOpen: isOpen,
      show: show,
    };
  }

  global.JzoEditorPool = { create: create };
})(window);
