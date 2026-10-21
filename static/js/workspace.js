/**
 * 工作台：三栏布局 + 清单舞台 + 真实模型闭环
 */
(function () {
  "use strict";

  // --- State ---
  var currentView = "original"; // "original" | "split"
  var writeToken = null;
  var reviewItems = [];
  var lastOcrText = "";
  var providerList = [];

  // --- DOM refs ---
  var sidebar = document.getElementById("wsSidebar");
  var sidebarToggle = document.getElementById("wsToggleSidebar");
  var contextPanel = document.getElementById("wsContext");
  var contextToggle = document.getElementById("wsToggleContext");
  var chatForm = document.getElementById("wsChatForm");
  var promptInput = document.getElementById("wsPrompt");
  var reviewBody = document.getElementById("wsReviewBody");
  var toggleBtns = document.querySelectorAll(".ws-toggle-btn");
  var providerSelect = document.getElementById("wsProviderSelect");
  var providerStatus = document.getElementById("wsProviderStatus");

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

  // --- Write token fetch (一次性令牌，用后即焚) ---
  function ensureWriteToken() {
    if (writeToken) return Promise.resolve(writeToken);
    return fetch("/api/settings", { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (settings) {
        writeToken = settings.local_token || "";
        return writeToken;
      })
      .catch(function () {
        writeToken = "";
        return "";
      });
  }

  // --- Real API: send instruction → cards produced by the active provider ---
  function describeSource(response) {
    var data = response.data || {};
    if (response.mock) {
      return "Mock 降级（当前 Provider 未配置密钥）";
    }
    return "模型 " + (data.model || "未知") + " 产出";
  }

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

        var source = describeSource(response);

        var parsed;
        try {
          parsed = JSON.parse(content);
        } catch (e) {
          parsed = { action: "clarify", question: content };
        }

        // Render based on action type
        if (parsed.action === "split_paper") {
          var range = Array.isArray(parsed.page_range) ? parsed.page_range : [];
          var pageText = range.length === 2 ? "第" + range[0] + "-" + range[1] + "页" : "全卷";
          if (!lastOcrText) {
            return {
              items: [],
              message: "已识别拆题指令（" + pageText + "），但尚未导入原卷文本。" + source,
              isError: true,
            };
          }
          return callSplitApi(lastOcrText).then(function (result) {
            return {
              items: result.items,
              message: "已拆分 " + result.items.length + " 道题目（" + pageText + " · " + result.source + "）",
              isError: false,
            };
          });
        } else if (parsed.action === "tag_question") {
          return { items: [], message: "已标记题目：" + parsed.question_id + "（" + source + "）", isError: false };
        } else if (parsed.action === "export_paper") {
          return { items: [], message: "正在导出为 " + parsed.format + " 格式…（" + source + "）", isError: false };
        } else if (parsed.action === "clarify") {
          return { items: [], message: parsed.question || "请明确指令", isError: true };
        } else {
          return { items: [], message: "未识别的操作：" + (parsed.action || "未知"), isError: true };
        }
      });
  }

  // --- Confirm action (with one-time token): 入库模型产出的真实题面 ---
  var CARD_TYPES = ["single_choice", "multiple_choice", "fill_blank", "solution", "proof"];
  var CARD_DIFFICULTIES = ["basic", "medium", "hard", "novel"];

  function buildQuestionPayload(card) {
    var payload = {
      type: CARD_TYPES.indexOf(card.type) >= 0 ? card.type : "unknown",
      stem: card.stem,
      difficulty: CARD_DIFFICULTIES.indexOf(card.difficulty) >= 0 ? card.difficulty : "basic",
    };
    var options = normalizeOptions(card.options);
    if (options.length) payload.options = options;
    if (card.answer) payload.answer = buildAnswer(card, options);
    if (card.solution) payload.solution = card.solution;
    return payload;
  }

  function buildAnswer(card, options) {
    var raw = String(card.answer).trim();
    var isChoice = card.type === "single_choice" || card.type === "multiple_choice";
    var keys = options.map(function (item) {
      return item.key;
    });
    var letters = raw
      .toUpperCase()
      .split("")
      .filter(function (ch, idx, all) {
        return ch >= "A" && ch <= "H" && all.indexOf(ch) === idx;
      });
    if (isChoice && letters.length && keys.length && letters.every(function (k) { return keys.indexOf(k) >= 0; })) {
      return { kind: "choice", choice_keys: letters };
    }
    return { kind: "text", content: raw };
  }

  function confirmItem(card) {
    return ensureWriteToken().then(function (token) {
      if (!token) {
        throw new Error("No write token available");
      }

      return fetch("/api/questions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-JZO-Token": token,
        },
        body: JSON.stringify(buildQuestionPayload(card)),
      })
        .then(function (r) {
          if (!r.ok) {
            if (r.status === 401) {
              throw new Error("令牌已失效，再点一次【确认入库】即可（会自动换新令牌，无需刷新页面）");
            }
            return r.json().then(function (body) {
              var detail = body && body.detail;
              var message = typeof detail === "string" ? detail : (detail && detail.message) || "";
              var errors = (detail && detail.errors) || [];
              throw new Error(message || ("HTTP " + r.status) + (errors.length ? "：" + errors.join("；") : ""));
            });
          }
          return r.json();
        })
        .then(function (result) {
          return { ok: true, id: result.id };
        })
        // 一次性令牌在 require_write_token 校验通过的那一刻就已被服务端轮换，
        // 与业务成没成功无关：400（写法不合法）同样把令牌吃掉了。
        // 只在成功路径清缓存会让下一次写入必然 401，逼用户刷新页面。
        .finally(function () {
          writeToken = null;
        });
    });
  }

  // --- Render review list ---
  function sourceBadge(item) {
    if (!item.source) return "";
    var isMock = item.source.indexOf("Mock") >= 0;
    return (
      ' · <span class="ws-review-item-source' +
      (isMock ? " ws-source-mock" : "") +
      '">' +
      escapeHtml(item.source) +
      "</span>"
    );
  }

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
        sourceBadge(item) +
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
        sourceBadge(item) +
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
    var card = reviewItems.filter(function (item) {
      return item.id === itemId;
    })[0];
    if (!card) {
      showToast("清单里已找不到题目 " + itemId + "，请重新拆题", true);
      return;
    }
    btn.disabled = true;
    btn.textContent = "处理中…";
    confirmItem(card)
      .then(function (result) {
        btn.textContent = "已确认";
        btn.classList.add("ws-btn-primary");
        showToast("已入库，服务端 ID：" + result.id);
      })
      .catch(function (error) {
        btn.disabled = false;
        btn.textContent = "确认入库";
        showToast("确认失败：" + error.message, true);
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
        .then(function (result) {
          // 只在新结果真的带卡片时替换清单，clarify/报错不得清空已有卡片
          if (result.items && result.items.length) {
            reviewItems = result.items;
            renderReviewList();
          }
          promptInput.value = "";
          if (sendBtn) {
            sendBtn.disabled = false;
            sendBtn.textContent = "发送";
          }
          showToast(result.message, result.isError);
        })
        .catch(function (err) {
          if (sendBtn) {
            sendBtn.disabled = false;
            sendBtn.textContent = "发送";
          }
          showToast("指令执行失败：" + err.message, true);
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

  function formatOptions(options) {
    return normalizeOptions(options)
      .map(function (item) {
        return item.key + ". " + item.content;
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
        .then(function (result) {
          lastOcrText = text;
          reviewItems = result.items;
          renderReviewList();
          ocrModal.hidden = true;
          showToast("已拆分 " + result.items.length + " 道题目（" + result.source + "）");
        })
        .catch(function (err) {
          showToast("拆题失败：" + err.message, true);
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

        var source = describeSource(response);

        var questions;
        try {
          questions = JSON.parse(content);
        } catch (e) {
          throw new Error("Invalid JSON in split response");
        }

        if (!Array.isArray(questions)) {
          throw new Error("Expected array of questions");
        }

        return {
          source: source,
          items: questions.map(function (q, idx) {
            return normalizeCard(q, idx, source);
          }),
        };
      });
  }

  // --- Normalize one model card into the card shape this page renders ---
  function normalizeCard(raw, idx, source) {
    var card = {
      id: typeof raw.id === "string" && raw.id ? raw.id : "card_" + (idx + 1),
      type: raw.type || "unknown",
      stem: raw.stem || "",
      difficulty: raw.difficulty || "basic",
      source: source,
    };
    var options = normalizeOptions(raw.options);
    if (options.length) card.options = options;
    if (raw.answer) card.answer = raw.answer;
    if (raw.solution) card.solution = raw.solution;
    if (raw.status) card.status = raw.status;
    return card;
  }

  // 模型可能给数组、{A:"..."} 字典，或 [{key,content}]；统一成 [{key, content}]
  function normalizeOptions(options) {
    if (!options) return [];
    if (Array.isArray(options)) {
      return options.map(function (item, idx) {
        var key = "ABCDEFGH".charAt(idx) || String(idx);
        if (item && typeof item === "object") {
          return { key: String(item.key || key), content: String(item.content || item.text || "") };
        }
        return { key: key, content: String(item == null ? "" : item) };
      });
    }
    if (typeof options === "object") {
      return Object.keys(options).map(function (key) {
        return { key: String(key), content: String(options[key] == null ? "" : options[key]) };
      });
    }
    return [];
  }

  // --- Workspace Management ---
  var workspaceSelect = document.getElementById("wsWorkspaceSelect");
  var newWorkspaceBtn = document.getElementById("wsNewWorkspaceBtn");

  function loadWorkspaces() {
    return fetch("/api/workspaces")
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        populateWorkspaceSelector(data.workspaces || []);
        return data;
      });
  }

  function populateWorkspaceSelector(workspaces) {
    if (!workspaceSelect) return;

    workspaceSelect.innerHTML = "";

    workspaces.forEach(function (ws) {
      var option = document.createElement("option");
      option.value = ws.id;
      option.textContent = ws.name || ws.id;
      if (ws.is_active) {
        option.selected = true;
      }
      workspaceSelect.appendChild(option);
    });
  }

  function switchWorkspace(workspaceId) {
    return fetch("/api/workspaces/switch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_id: workspaceId }),
    })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        // Clear local state on workspace switch
        reviewItems = [];
        renderReviewList();

        // Refresh token for new workspace
        writeToken = null;
        loadSettings();

        showToast("已切换到工作区: " + (data.name || workspaceId));
        return data;
      });
  }

  function createWorkspace(name) {
    return fetch("/api/workspaces", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name }),
    })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        showToast("工作区创建成功: " + data.name);
        return loadWorkspaces().then(function () {
          // Auto-switch to new workspace
          if (workspaceSelect) {
            workspaceSelect.value = data.id;
          }
          return switchWorkspace(data.id);
        });
      });
  }

  function loadSettings() {
    return fetch("/api/settings")
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        if (data.local_token) {
          writeToken = data.local_token;
        }
      });
  }

  // Event listeners for workspace controls
  if (workspaceSelect) {
    workspaceSelect.addEventListener("change", function () {
      var workspaceId = workspaceSelect.value;
      if (workspaceId) {
        switchWorkspace(workspaceId).catch(function (err) {
          showToast("切换工作区失败: " + err.message, true);
          // Revert selector to previous value
          loadWorkspaces();
        });
      }
    });
  }

  if (newWorkspaceBtn) {
    newWorkspaceBtn.addEventListener("click", function () {
      var name = prompt("请输入新工作区名称：");
      if (name && name.trim()) {
        createWorkspace(name.trim()).catch(function (err) {
          showToast("创建工作区失败: " + err.message, true);
        });
      }
    });
  }

  // --- AI Provider 注册表：只展示「是否已配置 + 模型名 + 接口主机」，密钥不下发 ---
  function findActiveProvider() {
    for (var i = 0; i < providerList.length; i += 1) {
      if (providerList[i].active) return providerList[i];
    }
    return null;
  }

  function renderProviderStatus() {
    if (!providerStatus) return;
    var active = findActiveProvider();
    if (!active) {
      providerStatus.textContent = "未读取到 Provider 注册表";
      providerStatus.classList.add("ws-provider-mock");
      return;
    }
    if (!active.configured || active.mock) {
      providerStatus.textContent = "Mock 降级：「" + active.label + "」未配置 API Key";
      providerStatus.classList.add("ws-provider-mock");
      return;
    }
    providerStatus.textContent =
      "真实模型 · " + (active.model || "未填模型名") + (active.host ? " · " + active.host : "");
    providerStatus.classList.remove("ws-provider-mock");
  }

  function loadProviders() {
    return fetch("/api/providers", { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        providerList = data.providers || [];
        if (providerSelect) {
          providerSelect.innerHTML = "";
          providerList.forEach(function (p) {
            var option = document.createElement("option");
            option.value = p.name;
            option.textContent = p.label + (p.configured ? "" : "（未配置）");
            if (p.active) option.selected = true;
            providerSelect.appendChild(option);
          });
        }
        renderProviderStatus();
        return data;
      });
  }

  function switchProvider(name) {
    return ensureWriteToken()
      .then(function (token) {
        return fetch("/api/providers/active", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-JZO-Token": token,
          },
          body: JSON.stringify({ name: name }),
        });
      })
      .then(function (r) {
        if (!r.ok) {
          return r.json().then(function (body) {
            var detail = body && body.detail;
            throw new Error(
              (typeof detail === "string" ? detail : (detail && detail.message)) || "HTTP " + r.status
            );
          });
        }
        return r.json();
      })
      .then(function (data) {
        showToast(
          data.mock
            ? "已切到「" + data.active + "」：未配置密钥，走 Mock"
            : "已切到「" + data.active + "」：真实模型 " + data.model,
          data.mock
        );
        return loadProviders();
      })
      .finally(function () {
        writeToken = null;
      });
  }

  if (providerSelect) {
    providerSelect.addEventListener("change", function () {
      var name = providerSelect.value;
      if (!name) return;
      switchProvider(name).catch(function (err) {
        showToast("切换 Provider 失败：" + err.message, true);
        loadProviders().catch(function () {});
      });
    });
  }

  // Load initial workspace list
  loadWorkspaces().then(function () {
    loadSettings();
  }).catch(function (err) {
    console.error("Failed to load workspaces:", err);
  });

  loadProviders().catch(function (err) {
    console.error("Failed to load providers:", err);
    renderProviderStatus();
  });
})();
