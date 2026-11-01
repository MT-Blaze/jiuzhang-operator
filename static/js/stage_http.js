/**
 * stage_http.js —— stage.js 的「339」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：底座 JS 单文件不超 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var RELAY_TIMEOUT_MS = deps.RELAY_TIMEOUT_MS;

  function textValue(payload, key, max) {
    var value = payload[key];
    if (typeof value !== "string") return "";
    return value.trim().slice(0, max);
  }

  // 一题多卷的原卷列表只承载关系字段，绝不把契约外的键带进题库：
  // paper_title 必填，year 走 1900–2100，其余按存储列宽截断。
  var SOURCE_FIELD_LIMITS = { paper_title: 120, school: 64, exam_type: 64, question_no: 20 };
  function sourceList(payload) {
    if (!Object.prototype.hasOwnProperty.call(payload, "sources")) {
      return { ok: true, items: undefined };
    }
    var raw = payload.sources;
    if (!Array.isArray(raw) || raw.length > 8) {
      return { ok: false, message: "sources 必须是不超过 8 条的来源数组" };
    }
    var items = [];
    for (var index = 0; index < raw.length; index += 1) {
      var entry = raw[index];
      if (!entry || typeof entry !== "object" || Array.isArray(entry)) {
        return { ok: false, message: "sources[" + index + "] 必须是对象" };
      }
      var keys = Object.keys(entry);
      for (var k = 0; k < keys.length; k += 1) {
        if (keys[k] !== "year" && !SOURCE_FIELD_LIMITS.hasOwnProperty(keys[k])) {
          return { ok: false, message: "sources[" + index + "] 不支持字段 " + keys[k] };
        }
      }
      var paper = typeof entry.paper_title === "string" ? entry.paper_title.trim() : "";
      if (!paper) return { ok: false, message: "sources[" + index + "] 缺少原卷标题" };
      var clean = { paper_title: paper.slice(0, SOURCE_FIELD_LIMITS.paper_title) };
      if (entry.year !== undefined && entry.year !== null && entry.year !== "") {
        var year = Number(entry.year);
        if (!Number.isInteger(year) || year < 1900 || year > 2100) {
          return { ok: false, message: "sources[" + index + "] 年份必须是 1900–2100 的整数" };
        }
        clean.year = year;
      }
      for (var field in SOURCE_FIELD_LIMITS) {
        if (field === "paper_title") continue;
        var value = entry[field];
        if (typeof value === "string" && value.trim()) {
          clean[field] = value.trim().slice(0, SOURCE_FIELD_LIMITS[field]);
        }
      }
      items.push(clean);
    }
    return { ok: true, items: items };
  }

  /** 「全部 / all」是面板的展示值，到了查询层必须变成「不过滤」。 */
  function filterValue(payload, key, max) {
    var value = textValue(payload, key, max);
    if (value === "全部" || value.toLowerCase() === "all") return "";
    return value;
  }

  function intValue(payload, key, fallback, min, max) {
    var value = Number(payload[key]);
    if (!Number.isFinite(value)) return fallback;
    value = Math.floor(value);
    if (value < min) return fallback;
    return Math.min(value, max);
  }

  function fetchJson(url, options) {
    var settings = options || {};
    settings.headers = Object.assign({ Accept: "application/json" }, settings.headers || {});
    var controller = typeof AbortController === "function" ? new AbortController() : null;
    var timer = 0;
    // 默认 20s 够用，智能体接口要等模型：整条转发链路的上限由调用方给。
    var timeoutMs = Number(settings.timeout);
    delete settings.timeout;
    if (!(timeoutMs >= 1000)) timeoutMs = RELAY_TIMEOUT_MS;
    if (controller) {
      settings.signal = controller.signal;
      timer = window.setTimeout(function () { controller.abort(); }, timeoutMs);
    }
    return fetch(url, settings)
      .then(function (response) {
        return response.text().then(function (text) {
          var data = null;
          try {
            data = text ? JSON.parse(text) : {};
          } catch (error) {
            data = null;
          }
          if (!response.ok) {
            // 一行话也要能定位：状态 + 方法 + 完整地址 + 服务端原因；请求体摘要
            // 与响应全文挂在 error 上，底栏【报错诊断】原样铺开（http.js）。
            throw window.JzoHttp.failure({
              status: response.status,
              statusText: response.statusText || "",
              method: settings.method || "GET",
              url: url,
              text: text,
              data: data,
              payload: settings.body
            });
          }
          if (data === null) throw new Error("宿主接口返回了非 JSON 内容：" + String(settings.method || "GET") + " " + url);
          return data;
        });
      })
      .then(function (data) {
        if (timer) window.clearTimeout(timer);
        return data;
      }, function (error) {
        if (timer) window.clearTimeout(timer);
        if (error && error.name === "AbortError") {
          var timeout = new Error("宿主接口超时（" + Math.round(timeoutMs / 1000) + "s）："
            + String(settings.method || "GET") + " " + url);
          timeout.url = url;
          timeout.method = String(settings.method || "GET");
          timeout.timeout = timeoutMs;
          throw timeout;
        }
        if (error && !error.url) {
          // 网络层直接抛错（断网、连接被拒）：同样把地址带上，避免只剩一句「Failed to fetch」。
          error.url = url;
          error.method = String(settings.method || "GET");
        }
        throw error;
      });
  }

  /**
   * 写操作：先取一次性令牌（用后即焚），再把令牌放进请求头，插件全程不可见。
   *
   * 令牌**用后即焚**：验证成功就轮换。两笔写操作绝不能并行——两边拿到同一个令牌，
   * 先用的那个烧掉它，后到的那个就 401 了。队列是全局唯一的一条
   * （intake.js 那边的录库写入也走它），两边各排各的队只会互相踩。
   */
  var writeQueue = Promise.resolve();

  function serializeWrite(task) {
    var intake = window.JzoIntake;
    if (intake && typeof intake.serialize === "function") return intake.serialize(task);
    var next = writeQueue.then(task, task);
    writeQueue = next.then(function () {}, function () {});
    return next;
  }

  function withWriteToken(url, options) {
    return serializeWrite(function () {
      return fetchJson("/api/settings").then(function (data) {
        var token = data && data.local_token;
        if (!token) throw new Error("拿不到本地写操作令牌");
        options.headers = Object.assign({}, options.headers || {}, { "X-JZO-Token": token });
        return fetchJson(url, options);
      });
    });
  }

  /**
   * 二进制读取：同源取一张托管图片，转成 data URL。
   *
   * 沙箱插件是不透明源，宿主原点的图片画进它的 Canvas 会污染画布，
   * toDataURL 直接抛 SecurityError。宿主同源读出字节、编成 data URL 递过去，
   * 插件拿它自己造 Blob 解码，画布就干净了。
   */
  function fetchBinary(url) {
    return fetch(url, { cache: "no-store" }).then(function (response) {
      if (!response.ok) {
        var failure = new Error("宿主取图失败：" + response.status);
        failure.status = response.status;
        throw failure;
      }
      var mime = String(response.headers.get("Content-Type") || "").split(";")[0].trim();
      return response.arrayBuffer().then(function (buffer) {
        var bytes = new Uint8Array(buffer);
        var parts = [];
        var chunk = 0x8000;
        for (var index = 0; index < bytes.length; index += chunk) {
          parts.push(String.fromCharCode.apply(null, bytes.subarray(index, index + chunk)));
        }
        return {
          dataUrl: "data:" + (mime || "image/png") + ";base64," + window.btoa(parts.join("")),
          mime: mime || "image/png",
          bytes: bytes.length
        };
      });
    });
  }

  function plainObject(value) {
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  }

  function urlValue(value, max) {
    var text = String(value == null ? "" : value).trim().slice(0, max || 500);
    return /^https?:\/\//i.test(text) ? text : "";
  }

    return {
      SOURCE_FIELD_LIMITS: SOURCE_FIELD_LIMITS,
      fetchBinary: fetchBinary,
      fetchJson: fetchJson,
      filterValue: filterValue,
      intValue: intValue,
      plainObject: plainObject,
      serializeWrite: serializeWrite,
      sourceList: sourceList,
      textValue: textValue,
      urlValue: urlValue,
      withWriteToken: withWriteToken,
      writeQueue: writeQueue,
    };
  }

  global.JzoStageHttp = { create: create };
})(window);
