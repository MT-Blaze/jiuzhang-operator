/**
 * ui_ai_copilot.js —— 终极军令 任务一/任务三：API 配置中心 + 单题/批量 AI 识别。
 *
 * 一块可整块下架的 AI 能力：删掉本文件、index.html 里的一行 <script> 与两处弹窗、
 * 辅助栏两颗入口、ai_copilot.css，工作台即回到「只有录题与审核」的原样。
 *
 * 分工：
 *   辅助栏（sidebar.right）只放两颗入口——顶部【API 配置】与底部【批量 AI 识别全卷】；
 *   画布（stage.center）才拿得到题图、渲染行与双栏空间，弹窗与逐题动作全在这一帧。
 * 两帧之间只走既有主题 editor.batch_review（action: ai_config / ai_batch），不新增总线主题。
 *
 * 铁律：插件不碰 Key 原文的存取、不联网、不落本地存储；一律经宿主 ai.* 通道，
 * 回读只有掩码。API 出错只亮红点 + 底部【报错诊断】，绝不弹窗打断老师。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var state = coreState.state;
    var dom = deps.dom;
    var el = deps.el;
    var hostCall = deps.hostCall;
    var dock = deps.dock;
    var dockWarn = deps.dockWarn;
    var errorDetail = deps.errorDetail;
    var toast = deps.toast;
    var publish = deps.publish;
    var openModal = deps.openModal;
    var closeModal = deps.closeModal;
    var itemImage = deps.itemImage;
    var parsedOf = deps.parsedOf;
    var markDirty = deps.markDirty;
    var refreshRow = deps.refreshRow;
    var writeBackSourceText = deps.writeBackSourceText;

    // 宿主中继把识别请求放宽到 125 秒，插件这侧必须比它更耐心。
    var AI_TIMEOUT_MS = 135000;
    var CONFIG_TIMEOUT_MS = 60000;
    var FALLBACK_TASKS = [
      { key: "ocr", label: "视觉识别(OCR)" },
      { key: "solve", label: "解题" },
      { key: "meta", label: "元数据" },
      { key: "tikz", label: "TikZ" }
    ];

    var cluster = null;
    var editingId = "";
    var askChoice = null;      // 覆盖确认窗正在等的那次裁决
    var batchBusy = false;

    // ---------------------------------------------------------------- 通用

    function text(node) {
      return node ? String(node.value == null ? "" : node.value).trim() : "";
    }

    function setMsg(message, tone) {
      var node = document.getElementById("epAiConfigMsg");
      if (!node) return;
      node.textContent = String(message == null ? "" : message).slice(0, 300);
      node.setAttribute("data-tone", tone || "info");
    }

    function shortError(error) {
      var message = String((error && error.message) || "未知原因");
      return message.length > 120 ? message.slice(0, 120) + "…" : message;
    }

    function imagesOf(item) {
      var picture = itemImage ? itemImage(item) : null;
      return picture && picture.uri ? [picture.uri] : [];
    }

    /** 人工修改的判据：AI 上次落笔之后又被改过；从没跑过 AI 就看脏标记。 */
    function hasHumanEdits(item) {
      if (!item) return false;
      if (item.aiSource != null) return item.source !== item.aiSource;
      return item.dirty === true;
    }

    /** 方案 A：底座把结构化正文套好 exam-zh 骨架再交回来，插件整题换上，不自己拼环境。 */
    function applyResult(index, result) {
      var item = state.items[index];
      var source = String((result && result.source) || "");
      if (!item || !source.trim()) return false;
      item.source = source;
      item.aiSource = source;
      item.parsed = null;
      item.dirty = true;
      markDirty();
      // 换源要落进中栏 textarea：只重建渲染格，老师看到的源码还是旧的。
      if (writeBackSourceText) writeBackSourceText(item, index, "stem");
      refreshRow(index);
      return true;
    }

    function askOverwrite(message, onChoice) {
      if (!dom.aiOverwriteModalEl) { onChoice("cancel"); return; }
      if (dom.aiOverwriteModalEl.querySelector(".ep-modal-text")) {
        dom.aiOverwriteModalEl.querySelector(".ep-modal-text").textContent = message;
      }
      askChoice = onChoice;
      openModal(dom.aiOverwriteModalEl);
    }

    function settleAsk(choice) {
      var callback = askChoice;
      askChoice = null;
      closeModal(dom.aiOverwriteModalEl);
      if (callback) callback(choice);
    }

    // ---------------------------------------------------------------- 单题识别

    function callRecognize(index) {
      var item = state.items[index];
      var images = imagesOf(item);
      if (!images.length) {
        var missing = new Error("这一题没有题图可识别：先框选切题，或挂上原卷页图");
        missing.detail = "";
        return Promise.reject(missing);
      }
      var parsed = parsedOf(item);
      var source = (item.question && item.question.source) || {};
      return hostCall("ai.recognize", {
        images: images,
        context: {
          stem: String(parsed.stem || "").slice(0, 6000),
          question_no: String(source.question_no || "")
        },
        task: "ocr"
      }, AI_TIMEOUT_MS).then(function (result) {
        if (!result || result.ok !== true) {
          var failure = new Error((result && result.detail) || "模型没有回话");
          failure.detail = String((result && result.detail) || "");
          throw failure;
        }
        return result;
      });
    }

    function markBusy(button, busy) {
      if (!button) return;
      button.disabled = Boolean(busy);
      if (busy) button.setAttribute("aria-busy", "true");
      else button.removeAttribute("aria-busy");
    }

    function runSingle(index, button, force) {
      var item = state.items[index];
      if (!item) return;
      if (!force && hasHumanEdits(item)) {
        askOverwrite("第 " + (index + 1) + " 题检测到人工修改。AI 识别结果会整题替换当前正文。",
          function (choice) {
            // 已经确认过就不再问一遍：force 跳开脏标记复检。
            if (choice === "overwrite") runSingle(index, button, true);
          });
        return;
      }
      markBusy(button, true);
      callRecognize(index).then(function (result) {
        markBusy(button, false);
        if (button) button.removeAttribute("data-error");
        if (applyResult(index, result)) {
          toast("第 " + (index + 1) + " 题已按 AI 识别结果重写，还没保存", "ok");
        } else {
          dockWarn("第 " + (index + 1) + " 题 AI 识别没有产出正文，源码没动。");
        }
      }, function (error) {
        markBusy(button, false);
        if (button) {
          button.setAttribute("data-error", "true");
          button.setAttribute("title", shortError(error) + "（详见底部报错诊断）");
        }
        dockWarn("第 " + (index + 1) + " 题 AI 识别失败：" + shortError(error), errorDetail(error));
      });
    }

    // ---------------------------------------------------------------- 批量识别

    function report(payload) {
      publish("editor.batch_review", Object.assign({ action: "ai_batch", from: "canvas" }, payload));
    }

    function startBatch(targets, overwriteHuman) {
      batchBusy = true;
      var stats = { total: targets.length, applied: 0, skipped: 0, failed: 0 };
      var firstError = "";
      var position = 0;

      function step() {
        if (position >= targets.length) {
          batchBusy = false;
          report({
            phase: "done", total: stats.total, applied: stats.applied,
            skipped: stats.skipped, failed: stats.failed, message: firstError
          });
          dock("AI 批量识别完成：成功 " + stats.applied + " 题，跳过 " + stats.skipped
            + " 题，失败 " + stats.failed + " 题。", stats.failed ? "warn" : "info");
          if (firstError) dockWarn("AI 批量识别有题目失败，完整原因见报错诊断。", firstError);
          return;
        }
        var index = targets[position];
        position += 1;
        if (!overwriteHuman && hasHumanEdits(state.items[index])) {
          stats.skipped += 1;
          report({ phase: "progress", index: position, total: stats.total });
          step();
          return;
        }
        report({ phase: "progress", index: position, total: stats.total });
        callRecognize(index).then(function (result) {
          if (applyResult(index, result)) stats.applied += 1;
          else stats.failed += 1;
          step();
        }, function (error) {
          stats.failed += 1;
          if (!firstError) firstError = "第 " + (index + 1) + " 题：" + errorDetail(error);
          step();
        });
      }
      step();
    }

    function runBatch() {
      if (batchBusy) return;
      if (!state.items.length) {
        report({ phase: "done", total: 0, applied: 0, skipped: 0, failed: 0,
          message: "这一批还没有题目可识别" });
        return;
      }
      var targets = [];
      state.items.forEach(function (item, index) {
        if (imagesOf(item).length) targets.push(index);
      });
      if (!targets.length) {
        report({ phase: "done", total: 0, applied: 0, skipped: 0, failed: 0,
          message: "这一批没有题图可识别：先框选切题或挂上原卷页图" });
        dockWarn("批量 AI 识别没有可识别的题图。");
        return;
      }
      var human = targets.filter(function (index) { return hasHumanEdits(state.items[index]); });
      if (!human.length) { startBatch(targets, false); return; }
      askOverwrite("这批里有 " + human.length + " 道题检测到人工修改。要连同它们一起覆盖，还是跳过？",
        function (choice) {
          if (choice === "cancel") return;
          startBatch(targets, choice === "overwrite");
        });
    }

    // ---------------------------------------------------------------- 配置中心

    function taskList() {
      var list = cluster && Array.isArray(cluster.tasks) ? cluster.tasks : [];
      return list.length ? list : FALLBACK_TASKS;
    }

    function resetAccountForm() {
      editingId = "";
      var name = document.getElementById("epAiName");
      var base = document.getElementById("epAiBase");
      var key = document.getElementById("epAiKey");
      if (name) name.value = "";
      if (base) base.value = "";
      if (key) { key.value = ""; key.placeholder = "留空＝保留旧 Key"; }
    }

    function fillAccountForm(account) {
      editingId = String((account && account.id) || "");
      var name = document.getElementById("epAiName");
      var base = document.getElementById("epAiBase");
      var key = document.getElementById("epAiKey");
      if (name) name.value = String((account && account.name) || "");
      if (base) base.value = String((account && account.base_url) || "");
      if (key) { key.value = ""; key.placeholder = "留空＝保留旧 Key"; }
      setMsg("正在编辑「" + ((account && account.name) || "") + "」：Key 留空表示不改。", "info");
    }

    function renderPool() {
      var list = document.getElementById("epAiPoolList");
      if (!list) return;
      list.textContent = "";
      var accounts = (cluster && Array.isArray(cluster.accounts)) ? cluster.accounts : [];
      if (!accounts.length) {
        list.appendChild(el("p", "ep-ai-empty", "还没有账号。填下面的表单添加第一个。"));
        return;
      }
      accounts.forEach(function (account) {
        var row = el("div", "ep-ai-acc");
        row.setAttribute("data-id", String(account.id || ""));
        var head = el("div", "ep-ai-acc-head");
        head.appendChild(el("strong", "ep-ai-acc-name", String(account.name || "未命名")));
        var ready = el("span", "ep-ai-tag", account.configured === false ? "未配 Key" : "已配置");
        ready.setAttribute("data-ready", account.configured === false ? "false" : "true");
        head.appendChild(ready);
        row.appendChild(head);
        row.appendChild(el("p", "ep-ai-acc-meta", String(account.base_url || "")));
        row.appendChild(el("p", "ep-ai-acc-key",
          account.api_key_masked ? "Key " + account.api_key_masked : "Key 未设置"));
        var acts = el("div", "ep-actions ep-ai-acc-acts");
        var edit = el("button", "ep-btn ep-mini-btn", "编辑");
        edit.type = "button";
        edit.addEventListener("click", function () { fillAccountForm(account); });
        var del = el("button", "ep-btn ep-mini-btn ep-btn-danger", "删除");
        del.type = "button";
        var armed = false;
        var timer = 0;
        del.addEventListener("click", function () {
          if (!armed) {
            armed = true;
            del.textContent = "确认删除";
            timer = window.setTimeout(function () {
              armed = false;
              del.textContent = "删除";
            }, 3000);
            return;
          }
          window.clearTimeout(timer);
          removeAccount(String(account.id || ""));
        });
        acts.appendChild(edit);
        acts.appendChild(del);
        row.appendChild(acts);
        list.appendChild(row);
      });
    }

    function removeAccount(accountId) {
      if (!accountId) return;
      hostCall("ai.account_delete", { account_id: accountId }, CONFIG_TIMEOUT_MS)
        .then(function () {
          if (editingId === accountId) resetAccountForm();
          return loadCluster();
        }).then(function () {
          setMsg("账号已删除；它的指派与 .env 密钥一并清掉。", "ok");
        }, configFailed("删除账号失败"));
    }

    function fillModels(datalist, models) {
      if (!datalist) return;
      datalist.textContent = "";
      (Array.isArray(models) ? models : []).slice(0, 300).forEach(function (name) {
        var option = document.createElement("option");
        option.value = String(name || "");
        datalist.appendChild(option);
      });
    }

    function renderAssignments() {
      var list = document.getElementById("epAiAssignList");
      if (!list) return;
      list.textContent = "";
      var accounts = (cluster && Array.isArray(cluster.accounts)) ? cluster.accounts : [];
      var assignments = (cluster && cluster.assignments) || {};
      taskList().forEach(function (task) {
        var key = String(task.key || "");
        var label = String(task.label || key);
        var assignment = assignments[key] || {};
        var row = el("div", "ep-ai-task");
        row.setAttribute("data-task", key);
        var head = el("div", "ep-ai-job-head");
        head.appendChild(el("span", "ep-ai-job-label", label));
        var ready = el("span", "ep-ai-job-ready", assignment.ready ? "已就绪" : "未指派");
        ready.setAttribute("data-ready", assignment.ready ? "true" : "false");
        head.appendChild(ready);
        row.appendChild(head);

        var select = document.createElement("select");
        select.className = "ep-ai-select";
        select.setAttribute("aria-label", label + " · 账号");
        var placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = accounts.length ? "选择账号" : "先在左侧添加账号";
        select.appendChild(placeholder);
        accounts.forEach(function (account) {
          var option = document.createElement("option");
          option.value = String(account.id || "");
          option.textContent = String(account.name || account.id || "");
          select.appendChild(option);
        });
        select.value = String(assignment.account_id || "");
        row.appendChild(select);

        var datalist = document.createElement("datalist");
        datalist.id = "epAiModels-" + key;
        var model = document.createElement("input");
        model.className = "ep-ai-input";
        model.type = "text";
        model.maxLength = 128;
        model.value = String(assignment.model || "");
        model.setAttribute("list", datalist.id);
        model.setAttribute("placeholder", "模型名（下拉里没有就手输）");
        model.setAttribute("aria-label", label + " · 模型");
        row.appendChild(model);
        row.appendChild(datalist);

        var acts = el("div", "ep-actions ep-ai-job-acts");
        var pull = el("button", "ep-btn ep-mini-btn", "拉取模型");
        pull.type = "button";
        var save = el("button", "ep-btn ep-mini-btn ep-btn-primary", "保存指派");
        save.type = "button";
        acts.appendChild(pull);
        acts.appendChild(save);
        row.appendChild(acts);

        pull.addEventListener("click", function () {
          var accountId = String(select.value || "");
          if (!accountId) { setMsg("先给「" + label + "」选一个账号，再拉模型。", "warn"); return; }
          pull.setAttribute("aria-busy", "true");
          hostCall("ai.models", { account_id: accountId }, CONFIG_TIMEOUT_MS).then(function (result) {
            pull.removeAttribute("aria-busy");
            if (!result || result.ok === false) {
              pull.setAttribute("data-error", "true");
              setMsg("拉模型失败：" + ((result && result.detail) || "模型服务没有回声"), "error");
              dockWarn("拉取模型失败", (result && result.detail) || "");
              return;
            }
            pull.removeAttribute("data-error");
            fillModels(datalist, result.models);
            setMsg((result.host ? result.host + " · " : "") + "拉到 "
              + ((result.models || []).length) + " 个模型；下拉里没有就直接手输。", "ok");
          }, function (error) {
            pull.removeAttribute("aria-busy");
            pull.setAttribute("data-error", "true");
            setMsg("拉模型失败：" + shortError(error), "error");
            dockWarn("拉取模型失败", errorDetail(error));
          });
        });

        save.addEventListener("click", function () {
          var accountId = String(select.value || "");
          var modelName = String(model.value || "").trim();
          if (!accountId) { setMsg("先给「" + label + "」选一个账号。", "warn"); return; }
          if (!modelName) { setMsg("模型名不能为空；下拉里没有就手动输入。", "warn"); return; }
          hostCall("ai.assign", {
            task: key, account_id: accountId, model: modelName
          }, CONFIG_TIMEOUT_MS).then(function (result) {
            if (result && Array.isArray(result.tasks)) cluster = result;
            renderPool();
            renderAssignments();
            setMsg("已把「" + label + "」指派到 " + modelName + "。", "ok");
          }, configFailed("保存指派失败"));
        });

        list.appendChild(row);
      });
    }

    function configFailed(prefix) {
      return function (error) {
        setMsg(prefix + "：" + shortError(error), "error");
        dockWarn(prefix, errorDetail(error));
      };
    }

    function renderCluster() {
      renderPool();
      renderAssignments();
    }

    function loadCluster() {
      return hostCall("ai.center", {}, CONFIG_TIMEOUT_MS).then(function (result) {
        cluster = result && typeof result === "object" ? result : { accounts: [], assignments: {} };
        renderCluster();
        return cluster;
      });
    }

    function saveAccount() {
      var name = text(document.getElementById("epAiName"));
      var baseUrl = text(document.getElementById("epAiBase"));
      var apiKey = text(document.getElementById("epAiKey"));
      if (!name) { setMsg("账号名称不能为空。", "warn"); return; }
      if (!/^https?:\/\//i.test(baseUrl)) { setMsg("Base URL 必须是 http(s) 直链。", "warn"); return; }
      var payload = { name: name, base_url: baseUrl };
      if (editingId) payload.id = editingId;
      // Key 留空＝保留旧 Key：字段干脆不发，绝不用空串覆盖已存的密钥。
      if (apiKey) payload.api_key = apiKey;
      hostCall("ai.account_save", payload, CONFIG_TIMEOUT_MS).then(function () {
        return loadCluster();
      }).then(function () {
        resetAccountForm();
        setMsg("账号已保存；密钥只写在本机 .env，这里只看得到掩码。", "ok");
      }, configFailed("保存账号失败"));
    }

    function openConfig() {
      if (!dom.aiConfigModalEl) return;
      resetAccountForm();
      setMsg("正在读取密钥池…", "info");
      openModal(dom.aiConfigModalEl);
      loadCluster().then(function () {
        setMsg("", "info");
      }, configFailed("读取配置失败"));
    }

    // ---------------------------------------------------------------- 装配

    /** 只读条不许自己挂事件（契约），单题识别的点击统一由渲染容器委托。 */
    function wireMetaAi() {
      var body = dom.renderBodyEl;
      if (!body || body.getAttribute("data-ai-wired") === "1") return;
      body.setAttribute("data-ai-wired", "1");
      body.addEventListener("click", function (event) {
        var node = event.target;
        while (node && node !== body) {
          if (node.classList && node.classList.contains("ed-q-meta-ai")) {
            runSingle(Number(node.getAttribute("data-index")) || 0, node);
            return;
          }
          node = node.parentNode;
        }
      });
    }

    function wireCanvas() {
      wireMetaAi();
      var modal = dom.aiConfigModalEl;
      if (!modal) return;
      var close = document.getElementById("epAiConfigClose");
      if (close) close.addEventListener("click", function () { closeModal(modal); });
      var save = document.getElementById("epAiSaveAccount");
      if (save) save.addEventListener("click", saveAccount);
      var reset = document.getElementById("epAiResetAccount");
      if (reset) reset.addEventListener("click", resetAccountForm);
      var ok = document.getElementById("epAiOverwriteOk");
      if (ok) ok.addEventListener("click", function () { settleAsk("overwrite"); });
      var skip = document.getElementById("epAiOverwriteSkip");
      if (skip) skip.addEventListener("click", function () { settleAsk("skip"); });
      var cancel = document.getElementById("epAiOverwriteCancel");
      if (cancel) cancel.addEventListener("click", function () { settleAsk("cancel"); });
    }

    function wirePanel() {
      var config = dom.panelAiConfigEl;
      if (config) {
        config.addEventListener("click", function () {
          publish("editor.batch_review", { action: "ai_config", from: "panel" });
        });
      }
      var batch = dom.panelAiBatchEl;
      if (batch) {
        batch.addEventListener("click", function () {
          batch.removeAttribute("data-error");
          if (dom.panelAiBatchNoteEl) {
            dom.panelAiBatchNoteEl.textContent = "正在逐题识别…";
            dom.panelAiBatchNoteEl.setAttribute("data-tone", "busy");
          }
          publish("editor.batch_review", { action: "ai_batch", from: "panel" });
        });
      }
    }

    /** 画布把每一题的进度与结果回投辅助栏：话在那边说，红点也亮在那颗钮上。 */
    function onBatchReport(payload) {
      var note = dom.panelAiBatchNoteEl;
      var button = dom.panelAiBatchEl;
      var phase = String((payload && payload.phase) || "");
      if (phase === "progress") {
        if (note) {
          note.textContent = "AI 识别 " + (Number(payload.index) || 0) + " / "
            + (Number(payload.total) || 0) + " …";
          note.setAttribute("data-tone", "busy");
        }
        return;
      }
      if (phase !== "done") return;
      var failed = Number(payload.failed) || 0;
      if (note) {
        note.textContent = "批量识别完成：成功 " + (Number(payload.applied) || 0)
          + " · 跳过 " + (Number(payload.skipped) || 0) + " · 失败 " + failed;
        note.setAttribute("data-tone", failed ? "error" : "ok");
      }
      if (button) {
        if (failed) button.setAttribute("data-error", "true");
        else button.removeAttribute("data-error");
      }
      if (failed && payload.message) dockWarn("批量 AI 识别有题目失败。", String(payload.message));
    }

    return {
      applyResult: applyResult,
      hasHumanEdits: hasHumanEdits,
      onBatchReport: onBatchReport,
      openConfig: openConfig,
      runBatch: runBatch,
      runSingle: runSingle,
      wireCanvas: wireCanvas,
      wirePanel: wirePanel,
    };
  }

  global.JzoEditorAiCopilot = { create: create };
})(window);
