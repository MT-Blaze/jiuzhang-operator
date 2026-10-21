/**
 * 工作台空壳：三栏布局 + 清单舞台 + Mock 闭环
 */
(function () {
  "use strict";

  // --- State ---
  var currentView = "original"; // "original" | "split"
  var mockToken = null;
  var reviewItems = [];

  // --- DOM refs ---
  var sidebar = document.getElementById("wsSidebar");
  var sidebarToggle = document.getElementById("wsToggleSidebar");
  var contextPanel = document.getElementById("wsContext");
  var contextToggle = document.getElementById("wsToggleContext");
  var chatForm = document.getElementById("wsChatForm");
  var promptInput = document.getElementById("wsPrompt");
  var reviewBody = document.getElementById("wsReviewBody");
  var toggleBtns = document.querySelectorAll(".ws-toggle-btn");

  // --- Sidebar collapse ---
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", function () {
      var expanded = sidebar.classList.toggle("collapsed");
      sidebarToggle.setAttribute("aria-expanded", String(!expanded));
      sidebarToggle.textContent = expanded ? "展开" : "折叠";
    });
  }

  // --- Context collapse ---
  if (contextToggle && contextPanel) {
    contextToggle.addEventListener("click", function () {
      var collapsed = contextPanel.classList.toggle("collapsed");
      contextToggle.setAttribute("aria-expanded", String(!collapsed));
      contextToggle.textContent = collapsed ? "展开" : "折叠";
    });
  }

  // --- View toggle (original / split) ---
  toggleBtns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var view = btn.getAttribute("data-view");
      if (!view) return;
      currentView = view;
      toggleBtns.forEach(function (b) {
        var isActive = b === btn;
        b.classList.toggle("active", isActive);
        b.setAttribute("aria-pressed", String(isActive));
      });
      renderReviewList();
    });
  });

  // --- Mock token fetch ---
  function fetchMockToken() {
    if (mockToken) return Promise.resolve(mockToken);
    return fetch("/api/settings", { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (settings) {
        mockToken = settings.local_token || "";
        return mockToken;
      })
      .catch(function () {
        mockToken = "";
        return "";
      });
  }

  // --- Real API: send instruction → receive cards via /api/agent/chat ---
  function sendInstruction(prompt) {
    return fetch("/api/agent/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_input: prompt, task_id: "ws_" + Date.now() }),
    })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (response) {
        var content = response.data && response.data.content;
        if (!content) throw new Error("Empty response from agent");

        var parsed;
        try {
          parsed = JSON.parse(content);
        } catch (e) {
          parsed = { action: "clarify", question: content };
        }

        // Render based on action type
        if (parsed.action === "split_paper") {
          showToast("已解析拆题指令：第" + parsed.page_range[0] + "-" + parsed.page_range[1] + "页");
          // In real implementation, this would trigger actual paper splitting
          // For now, show a placeholder card list
          return [
            {
              id: "split_1",
              stem: "集合 $A=\\{x \\mid x^2 - 3x + 2 = 0\\}$ 的元素个数为（  ）",
              type: "single_choice",
              difficulty: "basic",
              options: { A: "$0$", B: "$1$", C: "$2$", D: "$3$" },
              answer: "C",
              source: "AI 拆题 · 第" + parsed.page_range[0] + "页",
            },
            {
              id: "split_2",
              stem: "若函数 $f(x) = \\ln(x+1)$，则 $f'(0) = $ ______。",
              type: "fill_blank",
              difficulty: "medium",
              source: "AI 拆题 · 第" + parsed.page_range[1] + "页",
            },
          ];
        } else if (parsed.action === "tag_question") {
          showToast("已标记题目：" + parsed.question_id);
          return [];
        } else if (parsed.action === "export_paper") {
          showToast("正在导出为 " + parsed.format + " 格式...");
          return [];
        } else if (parsed.action === "clarify") {
          showToast(parsed.question || "请明确指令", true);
          return [];
        } else {
          showToast("未识别的操作：" + (parsed.action || "未知"), true);
          return [];
        }
      });
  }

  // --- Confirm action (with one-time token) ---
  function mockConfirmItem(itemId) {
    return fetchMockToken().then(function (token) {
      if (!token) {
        throw new Error("No write token available");
      }

      // Real write operation with token
      return fetch("/api/questions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-JZO-Token": token,
        },
        body: JSON.stringify({
          type: "single_choice",
          stem: "确认的题目 #" + itemId,
          difficulty: "basic",
        }),
      })
        .then(function (r) {
          if (!r.ok) {
            if (r.status === 401) {
              throw new Error("令牌已失效，请刷新页面获取新令牌");
            }
            throw new Error("HTTP " + r.status);
          }
          return r.json();
        })
        .then(function (result) {
          // Token consumed - refresh for next operation
          mockToken = null;
          return { ok: true, id: result.id || itemId };
        });
    });
  }

  // --- Render review list ---
  function renderReviewList() {
    if (!reviewBody) return;

    if (reviewItems.length === 0) {
      reviewBody.innerHTML = '<p class="ws-empty-hint">暂无题目。发送指令后卡片将出现在此处。</p>';
      return;
    }

    if (currentView === "split") {
      renderSplitView();
    } else {
      renderOriginalView();
    }
  }

  function renderOriginalView() {
    var html = '<ul class="ws-review-list" role="listbox">';
    reviewItems.forEach(function (item, idx) {
      html +=
        '<li class="ws-review-item" tabindex="0" role="option" data-index="' +
        idx +
        '" data-id="' +
        escapeHtml(item.id) +
        '">' +
        '<div class="ws-review-item-title">' +
        escapeHtml(truncate(item.stem, 60)) +
        "</div>" +
        '<div class="ws-review-item-meta">' +
        typeLabel(item.type) +
        " · " +
        difficultyLabel(item.difficulty) +
        "</div>" +
        '<div class="ws-review-item-detail">' +
        "<p><strong>题干：</strong>" +
        escapeHtml(item.stem) +
        "</p>" +
        (item.options
          ? "<p><strong>选项：</strong>" + formatOptions(item.options) + "</p>"
          : "") +
        (item.answer ? "<p><strong>答案：</strong>" + escapeHtml(String(item.answer)) + "</p>" : "") +
        '<button class="ws-btn ws-btn-sm ws-confirm-btn" data-id="' +
        escapeHtml(item.id) +
        '">确认入库</button>' +
        "</div>" +
        "</li>";
    });
    html += "</ul>";
    reviewBody.innerHTML = html;

    // Bind expand on click/enter/space
    var items = reviewBody.querySelectorAll(".ws-review-item");
    items.forEach(function (el) {
      el.addEventListener("click", function () {
        toggleExpand(el);
      });
      el.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          toggleExpand(el);
        }
      });
    });

    // Bind confirm buttons
    var confirmBtns = reviewBody.querySelectorAll(".ws-confirm-btn");
    confirmBtns.forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        var id = btn.getAttribute("data-id");
        handleConfirm(id, btn);
      });
    });
  }

  function renderSplitView() {
    var html = '<div class="ws-split-view">';
    html +=
      '<div class="ws-split-col"><h4>原卷</h4><ul class="ws-review-list" role="listbox">';
    reviewItems.forEach(function (item, idx) {
      html +=
        '<li class="ws-review-item" tabindex="0" role="option" data-index="' +
        idx +
        '" data-id="' +
        escapeHtml(item.id) +
        '">' +
        '<div class="ws-review-item-title">' +
        escapeHtml(truncate(item.stem, 50)) +
        "</div>" +
        '<div class="ws-review-item-meta">' +
        typeLabel(item.type) +
        "</div>" +
        "</li>";
    });
    html += "</ul></div>";

    html +=
      '<div class="ws-split-col"><h4>拆题</h4><ul class="ws-review-list" role="listbox">';
    reviewItems.forEach(function (item, idx) {
      html +=
        '<li class="ws-review-item" tabindex="0" role="option" data-index="' +
        idx +
        '" data-id="' +
        escapeHtml(item.id) +
        '">' +
        '<div class="ws-review-item-title">' +
        escapeHtml(truncate(item.stem, 50)) +
        "</div>" +
        '<div class="ws-review-item-meta">' +
        difficultyLabel(item.difficulty) +
        " · <button class='ws-btn ws-btn-sm ws-confirm-btn' data-id='" +
        escapeHtml(item.id) +
        "'>确认</button>" +
        "</div>" +
        "</li>";
    });
    html += "</ul></div></div>";

    reviewBody.innerHTML = html;

    // Bind confirm in split view
    var confirmBtns = reviewBody.querySelectorAll(".ws-confirm-btn");
    confirmBtns.forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        var id = btn.getAttribute("data-id");
        handleConfirm(id, btn);
      });
    });
  }

  function toggleExpand(el) {
    var wasExpanded = el.classList.contains("expanded");
    // Collapse all
    reviewBody.querySelectorAll(".ws-review-item").forEach(function (item) {
      item.classList.remove("expanded");
    });
    // Toggle clicked
    if (!wasExpanded) {
      el.classList.add("expanded");
    }
  }

  function handleConfirm(itemId, btn) {
    btn.disabled = true;
    btn.textContent = "处理中…";
    mockConfirmItem(itemId)
      .then(function (result) {
        if (result.ok) {
          btn.textContent = "已确认";
          btn.classList.add("ws-btn-primary");
          showToast("题目 #" + itemId + " 已确认入库");
        }
      })
      .catch(function () {
        btn.disabled = false;
        btn.textContent = "确认入库";
        showToast("确认失败，请重试", true);
      });
  }

  // --- Chat form submit ---
  if (chatForm) {
    chatForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var prompt = promptInput.value.trim();
      if (!prompt) return;

      var sendBtn = document.getElementById("wsSendBtn");
      if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.textContent = "发送中…";
      }

      sendInstruction(prompt)
        .then(function (items) {
          reviewItems = items;
          renderReviewList();
          promptInput.value = "";
          if (sendBtn) {
            sendBtn.disabled = false;
            sendBtn.textContent = "发送";
          }
          showToast("收到 " + items.length + " 道题目");
        })
        .catch(function () {
          if (sendBtn) {
            sendBtn.disabled = false;
            sendBtn.textContent = "发送";
          }
          showToast("指令执行失败", true);
        });
    });
  }

  // --- Utilities ---
  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function truncate(str, len) {
    if (!str) return "";
    return str.length > len ? str.slice(0, len) + "…" : str;
  }

  function typeLabel(type) {
    var map = {
      single_choice: "单选",
      multiple_choice: "多选",
      fill_blank: "填空",
      solution: "解答",
      proof: "证明",
      unknown: "未知",
    };
    return map[type] || type;
  }

  function difficultyLabel(diff) {
    var map = {
      basic: "基础",
      medium: "中档",
      hard: "压轴",
      novel: "新定义",
    };
    return map[diff] || diff;
  }

  function formatOptions(opts) {
    if (!opts || typeof opts !== "object") return "";
    return Object.keys(opts)
      .map(function (k) {
        return k + ". " + opts[k];
      })
      .join("； ");
  }

  function showToast(msg, isError) {
    // Simple toast using existing app.css if available, else console
    if (typeof window.showToast === "function") {
      window.showToast(msg, isError);
    } else {
      console.log(isError ? "[Error]" : "[Info]", msg);
    }
  }

  // --- Init ---
  renderReviewList();

  // --- OCR Import Modal ---
  var importBtn = document.getElementById("wsImportOcrBtn");
  var ocrModal = document.getElementById("wsOcrModal");
  var ocrText = document.getElementById("wsOcrText");
  var ocrSubmitBtn = document.getElementById("wsOcrSubmitBtn");
  var closeButtons = document.querySelectorAll("[data-modal-close]");

  if (importBtn && ocrModal) {
    importBtn.addEventListener("click", function () {
      ocrModal.hidden = false;
      ocrText.value = "";
      ocrText.focus();
    });
  }

  if (closeButtons) {
    closeButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        ocrModal.hidden = true;
      });
    });
  }

  if (ocrSubmitBtn) {
    ocrSubmitBtn.addEventListener("click", function () {
      var text = ocrText.value.trim();
      if (!text) {
        showToast("请输入原卷文本", true);
        return;
      }

      ocrSubmitBtn.disabled = true;
      ocrSubmitBtn.textContent = "拆题中…";

      callSplitApi(text)
        .then(function (items) {
          reviewItems = items;
          renderReviewList();
          ocrModal.hidden = true;
          showToast("已拆分 " + items.length + " 道题目");
        })
        .catch(function () {
          showToast("拆题失败，请重试", true);
        })
        .finally(function () {
          ocrSubmitBtn.disabled = false;
          ocrSubmitBtn.textContent = "开始拆题";
        });
    });
  }

  // --- Call /api/agent/split ---
  function callSplitApi(ocrMarkdown) {
    return fetch("/api/agent/split", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ocr_markdown: ocrMarkdown, task_id: "ws_" + Date.now() }),
    })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (response) {
        var content = response.data && response.data.content;
        if (!content) throw new Error("Empty response from split agent");

        var questions;
        try {
          questions = JSON.parse(content);
        } catch (e) {
          throw new Error("Invalid JSON in split response");
        }

        if (!Array.isArray(questions)) {
          throw new Error("Expected array of questions");
        }

        // Add source metadata
        return questions.map(function (q, idx) {
          return Object.assign({}, q, {
            source: "AI 拆题 · 第" + (idx + 1) + "题",
          });
        });
      });
  }
})();
