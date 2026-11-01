/**
 * stage_draft.js —— stage.js 的「草稿托管」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：底座 JS 单文件不超 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
  // ---------- 草稿托管（宿主代持 localStorage，按工作区分箱） ----------
  // 沙箱 iframe 是不透明源（只给 allow-scripts，不同源），插件里访问
  // localStorage 会直接抛 SecurityError——「关 Tab 不丢草稿」这件事只能由同源的宿主来做。
  // 插件通过 draft.save / draft.load 两个 RPC 把表单态交给宿主，宿主按「工作区 + plugin.id」分箱：
  // 切库重启后各区只看自己那箱，A 区没录完的题不会串进 B 区，切回来时还在。
  // 这里绝不碰后端题库：草稿是浏览器本地易失态，不进库、不出网。
  var DRAFT_NS = "jzo.draft.";
  var DRAFT_KEY_RE = /^[A-Za-z0-9_.:-]{1,80}$/;
  var DRAFT_MAX_CHARS = 200000;
  var DRAFT_TTL_MS = 14 * 24 * 60 * 60 * 1000;   // 两周没来取的草稿算陈旧，随写随清
  var DRAFT_BOX_MAX = 60;                        // 每箱最多 60 槽，超了丢最旧的
  var DRAFT_WS_RE = /^[A-Za-z0-9_-]{1,40}$/;
  // 分箱槽位的工作区段只有两种来源：default 与底座生成、一律带 ws_ 前缀的 id（app/api/workspaces.py）；
  // 插件 id 是反向域名，首段恒为 org/com/net 之类，永不会长这样。判「是否已分箱」必须用这个形状——
  // 只看「有没有点」会在 B 区开机时把 A 区已分箱的草稿当旧槽搬走。
  var DRAFT_BOXED_HEAD_RE = /^(default|ws_[A-Za-z0-9_-]{4,})\./;
  var draftWorkspace = "";                       // 当前工作区 id；没拿到之前一槽都不碰
  var draftBoxReady = null;

  function draftPrefix(workspaceId) {
    return DRAFT_NS + workspaceId + ".";
  }

  function draftSlot(pluginId, key) {
    return draftPrefix(draftWorkspace) + pluginId + "." + key;
  }

  function draftBoxUnknown() {
    return { ok: false, reason: "工作区身份未就绪，草稿箱未开放" };
  }

  function draftEachSlot(workspaceId, visit) {
    var prefix = draftPrefix(workspaceId);
    var slots = [];
    for (var i = 0; i < window.localStorage.length; i += 1) {
      var slot = window.localStorage.key(i);
      if (slot && slot.indexOf(prefix) === 0) slots.push(slot);
    }
    slots.forEach(visit);
    return slots.length;
  }

  /** 槽位信封 {saved_at, value}；分箱之前的裸值按「无时间戳」收编，下次写入自动补信封。 */
  function draftUnwrap(text) {
    var parsed = JSON.parse(text);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)
      && typeof parsed.saved_at === "number" && "value" in parsed) return parsed;
    return { saved_at: 0, value: parsed };
  }

  /** 清掉本箱里过期与超量的槽位；返回删除数。saved_at 为 0 的旧槽排在最先丢。 */
  function sweepDraftBox() {
    if (!draftWorkspace) return 0;
    var now = Date.now();
    var alive = [];
    var removed = 0;
    draftEachSlot(draftWorkspace, function (slot) {
      var stamp = 0;
      try {
        var text = window.localStorage.getItem(slot);
        if (!text) return;
        stamp = draftUnwrap(text).saved_at;
      } catch (error) {
        window.localStorage.removeItem(slot);
        removed += 1;
        return;
      }
      if (stamp && now - stamp > DRAFT_TTL_MS) {
        window.localStorage.removeItem(slot);
        removed += 1;
        return;
      }
      alive.push({ slot: slot, saved_at: stamp });
    });
    if (alive.length <= DRAFT_BOX_MAX) return removed;
    alive.sort(function (a, b) { return a.saved_at - b.saved_at; });
    var drop = alive.length - DRAFT_BOX_MAX;
    for (var i = 0; i < drop; i += 1) {
      window.localStorage.removeItem(alive[i].slot);
      removed += 1;
    }
    return removed;
  }

  /** 老命名空间 jzo.draft.<插件 id>.<键> 里没有工作区段；带工作区段的槽位一律不碰，别区的不许搬进本区。 */
  function migrateLegacyDrafts(workspaceId) {
    var target = draftPrefix(workspaceId);
    var slots = [];
    for (var i = 0; i < window.localStorage.length; i += 1) {
      var slot = window.localStorage.key(i);
      if (!slot || slot.indexOf(DRAFT_NS) !== 0 || slot.indexOf(target) === 0) continue;
      if (DRAFT_BOXED_HEAD_RE.test(slot.slice(DRAFT_NS.length))) continue;
      if (slot.slice(DRAFT_NS.length).indexOf(".") < 0) continue;
      slots.push(slot);
    }
    slots.forEach(function (slot) {
      var next = target + slot.slice(DRAFT_NS.length);
      var text = window.localStorage.getItem(slot);
      if (text && !window.localStorage.getItem(next)) window.localStorage.setItem(next, text);
      window.localStorage.removeItem(slot);
    });
    return slots.length;
  }

  /** 向底座问一次「我现在住在哪个工作区」；问不到就宁可不开箱，也绝不把草稿挂到别的区上。 */
  function resolveDraftBox() {
    if (draftBoxReady) return draftBoxReady;
    draftBoxReady = fetch("/api/settings", { cache: "no-store" })
      .then(function (response) { return response.ok ? response.json() : null; })
      .then(function (data) {
        var id = data && typeof data.workspace_id === "string" ? data.workspace_id : "";
        if (!DRAFT_WS_RE.test(id)) return "";
        draftWorkspace = id;
        try {
          migrateLegacyDrafts(id);
          sweepDraftBox();
        } catch (error) {
          // 搬家/清扫失败只影响陈旧槽位回收，不拦老师当场存草稿。
        }
        return id;
      })
      .catch(function () { return ""; });
    return draftBoxReady;
  }

  resolveDraftBox();   // 页签挂载前先把箱子落到哪个区问清楚，插件第一次 draft.load 就不用等

  /** 宿主代存草稿：value 为 null 即清除。返回是否成功（配额满/非法键/未分箱都如实报失败）。 */
  function saveDraft(pluginId, key, value) {
    if (!DRAFT_KEY_RE.test(key)) return { ok: false, reason: "草稿键不合法" };
    if (!draftWorkspace) return draftBoxUnknown();
    var slot = draftSlot(pluginId, key);
    try {
      if (value === null || value === undefined) {
        window.localStorage.removeItem(slot);
        return { ok: true, cleared: true };
      }
      var envelope = { saved_at: Date.now(), value: value };
      var text = JSON.stringify(envelope);
      if (text.length > DRAFT_MAX_CHARS) return { ok: false, reason: "草稿过大，未保存" };
      window.localStorage.setItem(slot, text);
      sweepDraftBox();
      return { ok: true, saved_at: envelope.saved_at };
    } catch (error) {
      return { ok: false, reason: String(error && error.name || "存储失败") };
    }
  }

  function loadDraft(pluginId, key) {
    if (!DRAFT_KEY_RE.test(key)) return { ok: false, reason: "草稿键不合法" };
    if (!draftWorkspace) return draftBoxUnknown();
    try {
      var text = window.localStorage.getItem(draftSlot(pluginId, key));
      return { ok: true, value: text ? draftUnwrap(text).value : null };
    } catch (error) {
      return { ok: false, reason: String(error && error.name || "读取失败") };
    }
  }

    return {
      DRAFT_BOXED_HEAD_RE: DRAFT_BOXED_HEAD_RE,
      DRAFT_BOX_MAX: DRAFT_BOX_MAX,
      DRAFT_KEY_RE: DRAFT_KEY_RE,
      DRAFT_MAX_CHARS: DRAFT_MAX_CHARS,
      DRAFT_NS: DRAFT_NS,
      DRAFT_TTL_MS: DRAFT_TTL_MS,
      DRAFT_WS_RE: DRAFT_WS_RE,
      draftBoxReady: draftBoxReady,
      draftBoxUnknown: draftBoxUnknown,
      draftEachSlot: draftEachSlot,
      draftPrefix: draftPrefix,
      draftSlot: draftSlot,
      draftUnwrap: draftUnwrap,
      draftWorkspace: draftWorkspace,
      loadDraft: loadDraft,
      migrateLegacyDrafts: migrateLegacyDrafts,
      resolveDraftBox: resolveDraftBox,
      saveDraft: saveDraft,
      sweepDraftBox: sweepDraftBox,
    };
  }

  global.JzoStageDraft = { create: create };
})(window);
