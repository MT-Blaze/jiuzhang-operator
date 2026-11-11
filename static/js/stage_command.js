/**
 * stage_command.js —— stage.js 的「插件数据通道」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：底座 JS 单文件不超 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var BANK_VIEW_DEFAULT = deps.BANK_VIEW_DEFAULT;
    var PROTOCOL = deps.PROTOCOL;
    var RELAY_TIMEOUT_MS = deps.RELAY_TIMEOUT_MS;
    var activate = deps.activate;
    var dock = deps.dock;
    var fetchJson = deps.fetchJson;
    var findPluginTab = deps.findPluginTab;
    var notify = deps.notify;
    var openPlugin = deps.openPlugin;
    var plainObject = deps.plainObject;
    var request = deps.request;
    var stageState = deps.stageState;
    var textValue = deps.textValue;

  // ---------- 插件数据通道（Host API 转发） ----------
  // 插件不直连数据库、也不联网；只能申请下列方法，由宿主按当前页签的 plugin.id 查接口，
  // payload 里自报 plugin_id 一律不认。读接口开放；写操作由宿主代取一次性令牌。
  var RELAY_METHODS = [
    "bank.list", "bank.stats", "bank.get", "bank.random", "bank.create",
    "bank.active_list", "bank.active_stats",
    "bank.topics", "bank.topic_notes", "bank.review", "bank.update", "bank.delete",
    "bank.sources",
    "bank.engine_meta", "bank.engine_directions", "bank.engine_knowledge", "bank.engine_create",
    "bank.dashboard_stats", "bank.dashboard_heatmap",
    "basket.list", "basket.add", "basket.active_add", "basket.remove", "basket.clear",
    "asset.upload",
    // 切图要有真像素：插件在沙箱里，宿主原点的图片画进 Canvas 会污染画布，
    // toDataURL 直接抛 SecurityError。宿主把托管配图读成 data URL 递过去。
    "asset.read",
    // 军令 #24：中转站（待审核池）。批次列表、批次题目、存草稿、存入主库、
    // 彻底删除——录题端与主库之间那层物理隔离暂存，全走这五个口子。
    "pending.batch_list", "pending.list", "pending.save_draft",
    "pending.approve", "pending.delete", "pending.delete_batch",
    // 老师拖绿框微调后的题块坐标回写：只改页图清单，题目一个字节不动。
    "pending.set_pages",
    // 军令 #31：入库前的后台查重。只读，回主库里同题 / 高度相似题的**两侧完整文档**，
    // 插件拿去做左右渲染对比（对比渲染，不比源码）。
    "pending.duplicate",
    // 批次公共元数据：改一次，这一批所有题的 sources 立刻跟着改。
    "pending.set_meta", "pending.meta_history",
    // 3.5 一键剔除本批次重复题：先出一条清单（batch / bank 两组），老师勾完再按勾选集执行。
    "pending.batch_duplicates", "pending.purge_duplicates",
    // 军令 #32 · 第五步：重题池。列表 / 单条只读（渲染对比的原料），四个动作走写令牌。
    "pending.pool_list", "pending.pool_get", "pending.pool_act", "pending.pool_save",
    // 军令 #28：全域数据字典。读场景/学校/标签，写学校与标签（写走一次性令牌）。
    "meta.scenes", "meta.schools", "meta.tags",
    "meta.school_create", "meta.school_suggest", "meta.tag_remember",
    // 军令 #25：拖入/粘贴的文件进中转站。
    "ingest.files",
    // 本地 YOLO 模型仓库：查硬件/模型落地状态（只读），按需下载（老师点击才出网）。
    "layout.model_status", "layout.model_download",
    "draft.save", "draft.load",
    // 军令 #21：脏 LaTeX 清洗是确定性规则，不调模型也不碰题库；
    // 单独开一个通道，是为了让录题端与底座共用同一份清洗实现。
    "text.clean_latex",
    // 插件能用的口子只有这一排：改写、读清单、读工作区快照、装插件、设面板参数、开页签
    // 全部由宿主代办；数据库、写令牌与宿主 DOM 一道门都没开。常驻对话助手已下架。
    "agent.refine", "plugins.list", "workspace.state",
    "plugin.install_url", "ui.params.set", "editor.apply_patch",
    "stage.overlay", "stage.open_bank", "stage.open_editor", "dict.catalog", "dict.open",
    // 军令 #19：能力路由字典。任何插件都能查表与调度；目标未安装/未声明
    // 一律回明确错误，绝不悄悄落到别的插件上。
    "command.list", "command.execute",
    // AI 配置中心：密钥池只回掩码，Key 与写令牌都由宿主代持；拉模型与识别
    // 都是老师点按钮才出网，插件自己碰不到 Key 原文。
    "ai.center", "ai.account_save", "ai.account_delete",
    "ai.assign", "ai.models", "ai.recognize"
  ];
  // 智能体接口只对清单里声明了 ai:invoke 的插件开放：
  // 别的插件即使猜对方法名，也只会拿到 PERMISSION_DENIED。
  var AI_ONLY_METHODS = [
    "agent.refine", "plugin.install_url",
    "ui.params.set", "editor.apply_patch", "stage.open_bank", "stage.open_editor",
    "ai.center", "ai.account_save", "ai.account_delete",
    "ai.assign", "ai.models", "ai.recognize"
  ];
  // 助手要读的两种清单：实现写在 relayAgent 里，分发就必须走到 relayAgent。
  // 它们不在 AI_ONLY_METHODS 里（任何插件都可以读清单），所以得单独点名——
  // 漏点一次，请求就会一路掉到 relay 末尾的分支上（真机曾因此把题篮清空）。
  var AGENT_READ_METHODS = ["plugins.list", "workspace.state"];
  var AGENT_TIMEOUT_MS = 60000;      // 模型一轮回答可以慢，但不能无限等
  var CLEAN_TEXT_MAX = 20000;        // 与 /api/agent/clean_latex 的入参上限一致

  var bankProviderCall = null;

  /** 清单里声明了某项能力才算数（与权限判定同口径，插件自报一律不认）。 */
  function hasCapability(tab, capability) {
    var list = tab.plugin && tab.plugin.capabilities;
    return Array.isArray(list) && list.indexOf(capability) >= 0;
  }

  function loadBankView() {
    if (stageState.bankViewCall) return stageState.bankViewCall;
    stageState.bankViewCall = fetchJson("/api/plugins").then(function (data) {
      var views = ((data && data.plugins) || []).filter(function (plugin) {
        return plugin && plugin.enabled !== false && plugin.show_in_sidebar !== false
          && plugin.entry_url
          && Array.isArray(plugin.capabilities)
          && plugin.capabilities.indexOf("bank.view") >= 0;
      });
      var preferred = views.filter(function (plugin) {
        return plugin.id === BANK_VIEW_DEFAULT;
      })[0] || views[0];
      if (!preferred) stageState.bankViewCall = null;   // 没装上：下次跳转时重新查清单
      return preferred || null;
    }, function () {
      stageState.bankViewCall = null;
      return null;
    });
    return stageState.bankViewCall;
  }

  function bankProviderBase() {
    return "/api/bank/plugins/" + encodeURIComponent(stageState.bankProviderId);
  }

  function loadBankProvider() {
    if (!bankProviderCall) {
      bankProviderCall = fetchJson("/api/bank/provider").then(function (info) {
        var id = info && info.plugin_id;
        if (typeof id === "string" && id) stageState.bankProviderId = id;
        return info;
      }, function () { return null; });
    }
    return bankProviderCall;
  }
  loadBankProvider();   // 启动即取；插件要等用户点击才激活，届时已解析完
  var RELAY_WINDOW_MS = 10000;
  var RELAY_MAX_PER_WINDOW = 80;
  // 大纲节点 ID：tp_ + 层别码（bo/ch/se/kx）+ 8 位十六进制，定长 13（bank/schema.sql）
  var TOPIC_ID_RE = /^tp_(bo|ch|se|kx)[0-9a-f]{8}$/;
  // 能力路由字典（PLUGIN_SPEC §2.14）：命令 id 与 context 的大小上限、
  // 现开/现唤醒目标页签的等待、转发链上限（挡 A→B→A 的循环），
  // 以及调用安全加固的四道闸：结果体积、排队串行、pending 提示、自动开页上限。
  var COMMAND_ID_RE = /^[a-z0-9][a-z0-9_]*(?:[.-][a-z0-9_]+){2,7}$/;
  var COMMAND_CONTEXT_MAX = 16384;
  var COMMAND_READY_TIMEOUT_MS = 10000;
  var COMMAND_MAX_HOPS = 4;
  var COMMAND_RESULT_MAX = 65536;        // result 序列化后字节上限（64 KB）
  var COMMAND_PENDING_MS = 1000;         // 超过 1 秒未回，先给调用方一条 pending 通知
  var COMMAND_QUEUE_MAX = 8;             // 同一目标同时挂起的命令上限
  var COMMAND_AUTO_TAB_MAX = 5;          // 命令自动打开的画布页签上限
  var commandIndex = Object.create(null);    // 命令 id → 登记条目
  var pluginCatalog = Object.create(null);   // 插件 id → 清单条目（找目标 iframe 用）
  var commandQueues = Object.create(null);   // 目标 key → { tail, depth }（串行队列）

  /**
   * 用 /api/plugins 的整份清单重建字典：停用、卸载的插件连同它的命令一起退场。
   * 后端已按「同 id 先到先得」去过重，这里再挡一次是为了清单被别处改写时不串台。
   */
  function setPluginCatalog(plugins) {
    var nextIndex = Object.create(null);
    var nextPlugins = Object.create(null);
    (Array.isArray(plugins) ? plugins : []).forEach(function (plugin) {
      if (!plugin || typeof plugin.id !== "string" || !plugin.id) return;
      nextPlugins[plugin.id] = plugin;
      if (plugin.enabled === false) return;
      (Array.isArray(plugin.commands) ? plugin.commands : []).forEach(function (command) {
        if (!command || typeof command.id !== "string" || nextIndex[command.id]) return;
        nextIndex[command.id] = {
          id: command.id,
          title: typeof command.title === "string" ? command.title : command.id,
          plugin_id: plugin.id,
          plugin_name: plugin.name || plugin.id,
          requires_user: command.requires_user === true,
          // 军令 #20：参数与返回值说明是命令契约的一部分，查表的人要能直接看到。
          description: typeof command.description === "string" ? command.description : "",
          params_schema: plainObject(command.params_schema),
          returns: typeof command.returns === "string" ? command.returns : ""
        };
      });
    });
    commandIndex = nextIndex;
    pluginCatalog = nextPlugins;
  }

  function listCommands() {
    return Object.keys(commandIndex).sort().map(function (id) {
      var item = commandIndex[id];
      return {
        id: item.id,
        title: item.title,
        plugin_id: item.plugin_id,
        plugin_name: item.plugin_name,
        requires_user: item.requires_user === true,
        description: item.description,
        params_schema: item.params_schema,
        returns: item.returns
      };
    });
  }

  /** 目标插件可用的 iframe：活着的画布页签或右栏面板；休眠页签会交给调用方唤醒。 */
  function commandTarget(pluginId) {
    var tab = findPluginTab(pluginId);
    if (tab && tab.state === "live" && tab.frame && tab.ready) return tab;
    for (var i = 0; i < stageState.panels.length; i += 1) {
      if (stageState.panels[i].plugin && stageState.panels[i].plugin.id === pluginId && stageState.panels[i].frame) {
        return stageState.panels[i];
      }
    }
    return tab;
  }

  /** 等目标页签挂载并就绪；未就绪绝不硬发请求（postMessage 给空窗口会石沉大海）。 */
  function waitCommandReady(tab, timeoutMs) {
    return new Promise(function (resolve, reject) {
      var started = Date.now();
      function notReady(message) {
        var error = new Error(message);
        error.code = "NOT_READY";
        reject(error);
      }
      (function tick() {
        if (tab.state === "live" && tab.ready && tab.frame) { resolve(tab); return; }
        if (tab.state === "error") { notReady("目标插件加载失败"); return; }
        if (Date.now() - started > timeoutMs) {
          notReady("目标插件在 " + Math.round(timeoutMs / 1000) + " 秒内没有就绪");
          return;
        }
        window.setTimeout(tick, 200);
      })();
    });
  }

  function commandError(code, message) {
    var error = new Error(message);
    error.code = code;
    return error;
  }

  /** result 序列化后的字节数；-1 表示根本序列化不了（循环引用、BigInt 等）。 */
  function commandResultBytes(value) {
    var text;
    try {
      text = JSON.stringify(value === undefined ? {} : value);
    } catch (error) {
      return -1;
    }
    if (typeof text !== "string") return 0;
    if (typeof TextEncoder === "function") {
      try { return new TextEncoder().encode(text).length; } catch (error) { return text.length; }
    }
    return text.length;
  }

  /**
   * 同一目标串行执行：插件命令常写成「读—改—写」，并发插队会丢更新。
   * 队列按目标分箱，两个不同插件的命令互不排队。
   */
  function queueCommand(target, task) {
    var key = (target.kind || "tab") + ":"
      + (target.key || (target.plugin && target.plugin.id) || "unknown");
    var queue = commandQueues[key];
    if (!queue) {
      queue = { tail: Promise.resolve(), depth: 0 };
      commandQueues[key] = queue;
    }
    if (queue.depth >= COMMAND_QUEUE_MAX) {
      return Promise.reject(commandError("COMMAND_BUSY",
        "目标插件已有 " + COMMAND_QUEUE_MAX + " 条命令在排队，请稍后再试"));
    }
    queue.depth += 1;
    function release() {
      queue.depth -= 1;
      if (queue.depth <= 0 && commandQueues[key] === queue) delete commandQueues[key];
    }
    var result = queue.tail.then(function () { return task(); });
    queue.tail = result.then(release, release);   // 失败也要放行下一条
    return result;
  }

  /** 只数命令自动开出来的页签；老师自己点开的页签不占名额。 */
  function commandOpenedTabs() {
    return stageState.tabs.filter(function (tab) { return tab.openedByCommand === true; }).length;
  }

  /**
   * 高副作用命令（清单 requires_user）的当场确认。弹框脚本缺失时一律不放行：
   * 安全闸不能因为宿主少装一个脚本就静默失效。
   */
  function confirmCommand(caller, entry, decide) {
    if (!window.JzoDialogs || typeof window.JzoDialogs.confirm !== "function") {
      decide(false);
      return;
    }
    var callerName = (caller.plugin && (caller.plugin.name || caller.plugin.id)) || "调用方插件";
    window.JzoDialogs.confirm({
      title: "允许执行这条命令？",
      message: "「" + callerName + "」请求执行「" + entry.title + "」（" + entry.id + "），由「"
        + entry.plugin_name + "」处理。这条命令会改动数据或外部状态，请确认这是你要做的事。",
      confirmText: "允许执行",
      cancelText: "拒绝",
      anchor: document.activeElement && typeof document.activeElement.focus === "function"
        ? document.activeElement : null,
      onAccept: function () { decide(true); },
      onCancel: function () { decide(false); }
    });
  }

  /**
   * command.execute：查宿主内存字典 → 找到目标插件 → 经宿主 iframe 转发。
   * 插件之间没有直连通道：调用方只交命令 id 与 context，目标 id、实例与
   * 生命周期全部由宿主决定（与 system.open_editor 同一条规矩）。
   */
  function executeCommand(caller, payload, done, failWith) {
    var commandId = textValue(payload, "command_id", 120);
    if (!COMMAND_ID_RE.test(commandId)) {
      failWith("BAD_REQUEST", "command_id 缺失或形状不对（小写反向域名、至少三段）");
      return;
    }
    var context = plainObject(payload.context);
    var encoded = "";
    try { encoded = JSON.stringify(context); } catch (error) { encoded = "!"; }
    if (encoded.length > COMMAND_CONTEXT_MAX) {
      failWith("BAD_REQUEST", "context 超过 " + COMMAND_CONTEXT_MAX + " 字符上限");
      return;
    }
    var entry = commandIndex[commandId];
    if (!entry) {
      failWith("COMMAND_NOT_FOUND",
        "能力字典里没有命令「" + commandId + "」：目标插件未安装、已停用或没有声明它");
      return;
    }
    var plugin = pluginCatalog[entry.plugin_id];
    if (!plugin) {
      failWith("COMMAND_TARGET_MISSING",
        "命令「" + commandId + "」登记的插件 " + entry.plugin_id + " 不在当前清单里");
      return;
    }
    // trace 只截取形状、不信任内容：调用方自报的链路可以伪造，真正的环路阈值
    // 由宿主每一跳追加一层来收紧；限流（80 次/10 秒）是最后一道闸。
    var trace = Array.isArray(payload.trace) ? payload.trace.filter(function (item) {
      return typeof item === "string" && item.length > 0 && item.length <= 80;
    }).slice(0, COMMAND_MAX_HOPS) : [];
    if (trace.length >= COMMAND_MAX_HOPS) {
      failWith("COMMAND_LOOP",
        "命令转发已超过 " + COMMAND_MAX_HOPS + " 层，疑似循环调用，已中断");
      return;
    }

    if (entry.requires_user) {
      confirmCommand(caller, entry, function (allowed) {
        if (!allowed) {
          failWith("COMMAND_DENIED", "命令「" + commandId + "」需要用户当场确认，已取消执行");
          return;
        }
        dispatchCommand(caller, entry, plugin, commandId, context, trace, done, failWith);
      });
      return;
    }
    dispatchCommand(caller, entry, plugin, commandId, context, trace, done, failWith);
  }

  /** 真正的转发：开页/唤醒 → 按目标排队 → 发请求；pending 与结果体积都在这层。 */
  function dispatchCommand(caller, entry, plugin, commandId, context, trace, done, failWith) {
    if (plugin.headless === true) {
      // 无界面插件没有 iframe 可投递；它的数据命令由底座在 Host 侧执行（军令 #20）。
      failWith("COMMAND_HEADLESS",
        "「" + entry.plugin_name + "」是无界面插件，数据命令由底座直接执行，不经 iframe 转发");
      return;
    }
    var handle = commandTarget(plugin.id);
    var ready;
    if (!handle) {
      if (commandOpenedTabs() >= COMMAND_AUTO_TAB_MAX) {
        failWith("COMMAND_LIMIT", "命令自动打开的页签已达 " + COMMAND_AUTO_TAB_MAX
          + " 个上限，请先关掉一些页签再试");
        return;
      }
      handle = openPlugin(plugin);
      if (!handle) {
        failWith("COMMAND_TARGET_MISSING", "命令「" + commandId + "」的目标插件没有可加载的入口页");
        return;
      }
      handle.openedByCommand = true;
      dock("命令「" + entry.title + "」需要「" + entry.plugin_name + "」，已为它开一个画布页。",
        "stage.command.open");
      ready = waitCommandReady(handle, COMMAND_READY_TIMEOUT_MS);
    } else if (handle.kind === "panel") {
      ready = Promise.resolve(handle);
    } else if (handle.state === "live" && handle.ready) {
      ready = Promise.resolve(handle);
    } else {
      activate(handle.key);   // 休眠页签：唤醒后再发，避免请求打在空窗口上
      ready = waitCommandReady(handle, COMMAND_READY_TIMEOUT_MS);
    }

    // 排队与执行都可能慢：超过 1 秒就给调用方一条 pending 通知，请求本身继续等，
    // 最终仍以真实结果或错误收尾（通知不是失败回执）。
    var settled = false;
    var pendingTimer = window.setTimeout(function () {
      if (settled) return;
      notify(caller, "command.pending", {
        command_id: commandId,
        code: "COMMAND_PENDING",
        target_plugin_id: entry.plugin_id,
        message: "命令「" + entry.title + "」仍在「" + entry.plugin_name + "」排队或执行中"
      });
      dock("命令「" + entry.title + "」超过 1 秒未回，已向调用方发出排队提示。",
        "stage.command.pending");
    }, COMMAND_PENDING_MS);
    function settle() {
      if (settled) return false;
      settled = true;
      window.clearTimeout(pendingTimer);
      return true;
    }

    ready.then(function (target) {
      return queueCommand(target, function () {
        return request(target, "command.execute", {
          command_id: commandId,
          context: context,
          from: (caller.plugin && caller.plugin.id) || "",
          trace: trace.concat([entry.plugin_id])
        });
      });
    }).then(function (result) {
      if (!settle()) return;
      var bytes = commandResultBytes(result);
      if (bytes < 0) {
        failWith("COMMAND_RESULT_INVALID",
          "命令「" + commandId + "」的返回值无法序列化（可能含循环引用）", false);
        return;
      }
      if (bytes > COMMAND_RESULT_MAX) {
        failWith("COMMAND_RESULT_TOO_LARGE", "命令「" + commandId + "」的结果序列化后 "
          + bytes + " 字节，超过 " + COMMAND_RESULT_MAX + " 字节上限；请分页或改由宿主 API 拉取",
          false);
        return;
      }
      done({ command_id: commandId, plugin_id: entry.plugin_id, result: result });
    }, function (error) {
      if (!settle()) return;
      var code = error && error.code;
      var mapped = code === "NOT_READY" ? "COMMAND_NOT_READY"
        : (code === "COMMAND_BUSY" ? "COMMAND_BUSY" : "COMMAND_FAILED");
      failWith(mapped,
        "命令「" + commandId + "」执行失败：" + ((error && error.message) || "未知原因"), false);
    });
  }

  function replyHost(tab, message, ok, value) {
    if (!tab.frame || !tab.frame.contentWindow) return;
    var packet = { protocol: PROTOCOL, id: message.id, kind: "response", ok: ok };
    if (ok) {
      packet.result = value === undefined ? {} : value;
    } else {
      packet.error = {
        code: (value && value.code) || "HOST_ERROR",
        message: (value && value.message) || "宿主拒绝了请求",
        retryable: Boolean(value && value.retryable)
      };
      // 查重命中（409）要把主库那道题的 id 原样带回去：插件靠它弹「返回修改 / 强行覆盖」，
      // 少了这个字段，插件只能笼统地说「重复了」，老师没法裁决。
      if (value && value.existing_id) packet.error.existing_id = String(value.existing_id);
      if (value && value.duplicate === true) packet.error.duplicate = true;
      // 军令 #31：答案不同是**红字拦截**，不是普通重复。插件要靠这三个字段把
      // 「覆盖」「合并为解析二」两颗钮锁死，并原样亮出两边的答案。
      if (value && value.answer_mismatch === true) packet.error.answer_mismatch = true;
      if (value && value.existing_answer) {
        packet.error.existing_answer = String(value.existing_answer);
      }
      if (value && value.incoming_answer) {
        packet.error.incoming_answer = String(value.incoming_answer);
      }
      if (value && value.code) packet.error.detail_code = String(value.code);
    }
    try {
      tab.frame.contentWindow.postMessage(packet, "*");
    } catch (error) {
      // 帧已经被摘掉：回复无处可去，忽略
    }
  }

  /** 每页签限流，挡住插件里失控的循环把本机 SQLite 打满。 */
  function relayBudget(tab) {
    var now = Date.now();
    if (!tab.relayWindow || now - tab.relayWindow > RELAY_WINDOW_MS) {
      tab.relayWindow = now;
      tab.relayCount = 0;
    }
    tab.relayCount += 1;
    return tab.relayCount <= RELAY_MAX_PER_WINDOW;
  }

    return {
      AGENT_READ_METHODS: AGENT_READ_METHODS,
      AGENT_TIMEOUT_MS: AGENT_TIMEOUT_MS,
      AI_ONLY_METHODS: AI_ONLY_METHODS,
      CLEAN_TEXT_MAX: CLEAN_TEXT_MAX,
      COMMAND_AUTO_TAB_MAX: COMMAND_AUTO_TAB_MAX,
      COMMAND_CONTEXT_MAX: COMMAND_CONTEXT_MAX,
      COMMAND_ID_RE: COMMAND_ID_RE,
      COMMAND_MAX_HOPS: COMMAND_MAX_HOPS,
      COMMAND_PENDING_MS: COMMAND_PENDING_MS,
      COMMAND_QUEUE_MAX: COMMAND_QUEUE_MAX,
      COMMAND_READY_TIMEOUT_MS: COMMAND_READY_TIMEOUT_MS,
      COMMAND_RESULT_MAX: COMMAND_RESULT_MAX,
      RELAY_MAX_PER_WINDOW: RELAY_MAX_PER_WINDOW,
      RELAY_METHODS: RELAY_METHODS,
      RELAY_WINDOW_MS: RELAY_WINDOW_MS,
      TOPIC_ID_RE: TOPIC_ID_RE,
      bankProviderBase: bankProviderBase,
      bankProviderCall: bankProviderCall,
      commandError: commandError,
      commandIndex: commandIndex,
      commandOpenedTabs: commandOpenedTabs,
      commandQueues: commandQueues,
      commandResultBytes: commandResultBytes,
      commandTarget: commandTarget,
      confirmCommand: confirmCommand,
      dispatchCommand: dispatchCommand,
      executeCommand: executeCommand,
      hasCapability: hasCapability,
      listCommands: listCommands,
      loadBankProvider: loadBankProvider,
      loadBankView: loadBankView,
      pluginCatalog: pluginCatalog,
      queueCommand: queueCommand,
      relayBudget: relayBudget,
      replyHost: replyHost,
      setPluginCatalog: setPluginCatalog,
      waitCommandReady: waitCommandReady,
    };
  }

  global.JzoStageCommand = { create: create };
})(window);
