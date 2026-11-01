/**
 * 组卷排版引擎（org.jiuzhang.paper-gen / core_layout.js）。
 *
 * 从 plugin.js 拆出（PLUGIN_SPEC §2.8.1「单文件不得过 800 行」）：一题一量的版式
 * 缓存、纯算术落页、视口级物化，以及「同步只排眼前几页、余下交空闲」的重排驱动。
 *
 * 本模块不认宿主协议、不读题篮、不碰侧栏 DOM：
 * 题块怎么建、配图尺寸怎么量归 ui_rich.js；什么时候重排、参数怎么改归 plugin.js。
 * 它只吃 ctx 里那几样——题篮状态 state、测量列与纸面三个 DOM、指标条 metricsEl，
 * 以及 dock / renderSide / isStage 三个回调。
 *
 * 视口级虚拟渲染（v0.8.1）的五条约束：
 * 1. 一题只量一次。每道题构建一次 DOM，进测量列量出「每个子件的落位高度
 *    （含子件间距与 KaTeX 墨迹外溢）」并缓存，键是 题目ID + 密度 + 内容签名。
 * 2. 答案态不二次测量。答案与解析整体包在 .pg-ansbox 里，该容器上下无外边距
 *    逃逸，隐藏时等于整段从流里摘掉、其余子件落位高度一个不变，于是
 *    「显示答案」总高 = 整题高，「隐藏答案」总高 = 整题高 - 答案段高。
 * 3. 分页是纯算术。落页只写 items 数组，不碰 DOM、不读布局；只有进入视口
 *    ±1 的页才把节点挂进纸面（物化），离得远的页清空退化为占位纸。
 *    七十二页的卷子，同步代价只等于眼前这两三页。
 * 4. 墨迹兜底就地做。物化后只读该页 scrollHeight（页内有 contain:strict，
 *    不牵动整份卷子），越界就把尾件顺延到下一页头部。
 * 5. 剩余页在空闲片里补齐（每片 ≤ CHUNK_MS），补完才写 data-doc-ready=1；
 *    打印前先同步补齐，绝不发缺页的 PDF。
 */
(function (global) {
  "use strict";

  var PAGE_W = 794;
  var PAGE_H = 1123;
  // 排版留白：给 KaTeX 分式的上下墨迹留出余量，避免末行墨迹被纸边裁掉
  var PAGE_FILL_H = 885;
  var PAGE_GAP = 16;          // .pg-pages 的 flex gap
  var PREVIEW_PAD = 18;       // .pg-preview 的上内边距
  var LIVE_BUFFER = 1;        // 视口前后各多挂一页
  var DROP_BUFFER = 3;        // 远于三页才回收，慢滚时不必来回重建
  var MAX_LIVE = 6;           // 同时物化的页数上限
  var SCROLL_BUDGET_MS = 140; // 滚动追页的同步预算，超预算交后台补
  var CHUNK_MS = 24;          // 空闲补齐每片时限

  function create(ctx) {
    var state = ctx.state;
    var el = ctx.el;
    var answerText = ctx.answerText;
    var buildQuestionBlock = ctx.buildQuestionBlock;
    var measureEl = ctx.measureEl;
    var previewEl = ctx.previewEl;
    var pagesEl = ctx.pagesEl;
    var metricsEl = ctx.metricsEl;
    var dock = ctx.dock;
    var renderSide = ctx.renderSide;
    var isStage = ctx.isStage;

    var reflowSeq = 0;
    // 重排期间预览宽度不会变，缩放只算一次；每开一页都读 clientWidth 会强制整页回流。
    var activeScale = 1;
    var inkMoves = 0;
    var inkPages = 0;
    // 版式缓存：键 = 题目ID + 密度 + 内容签名；值 = 量好的落件清单
    var layouts = new Map();
    // 当前题篮的逐题版式记录（按题序），每次重排整组重建
    var recs = [];
    // 每种密度下「（接上题）」标记的占位高度
    var contHeights = {};
    // 装配态：pages = 页记录，cursor = 下一个待排的题号，complete = 全卷是否排完。
    // 换卷只改字段、不换对象——plugin.js 也握着这个引用，换对象会让它读到旧卷。
    var doc = { pages: [], page: null, cursor: 0, complete: true, idle: 0, token: 0, startedAt: 0 };
    // 分段耗时台账：每次 reflow 清零，只累计「同步段」真发生的构建/测量/落页/物化
    var tally = { build: 0, measure: 0, place: 0, settle: 0 };

    // ---------- 版式测量与缓存 ----------
    function hashText(text) {
      var hash = 5381;
      var i = 0;
      var len = text.length;
      // 逐字符 djb2：只扫首尾各 4K，足够抓住改题；50 题签名成本压在毫秒级
      var head = text.slice(0, 4096);
      var tail = len > 8192 ? text.slice(-4096) : (len > 4096 ? text.slice(4096) : "");
      while (i < head.length) { hash = (hash * 33) ^ head.charCodeAt(i); i += 1; }
      i = 0;
      while (i < tail.length) { hash = (hash * 33) ^ tail.charCodeAt(i); i += 1; }
      return (hash >>> 0).toString(36) + "_" + len;
    }

    function signatureOf(question) {
      return [
        question.stem == null ? "" : String(question.stem),
        question.solution == null ? "" : String(question.solution),
        answerText(question),
        (question.options || []).map(function (option) {
          return option.key + ":" + (option.content || "") + ":" + (option.image_ids || []).join(",");
        }).join("|"),
        (question.images || []).map(function (image) { return image.id + ":" + image.uri; }).join("|")
      ].map(hashText).join("~");
    }

    function layoutKey(question) {
      return question.id + "\u0001" + state.density + "\u0001" + signatureOf(question);
    }

    /** 「（接上题）」标记在同一密度下高度恒定，量一次存一次。 */
    function contHeight() {
      if (contHeights[state.density] !== undefined) return contHeights[state.density];
      var probe = el("p", "pg-cont", "（接上题）");
      measureEl.appendChild(probe);
      var height = probe.offsetHeight + 4;   // 4 = .pg-cont 的下边距
      measureEl.removeChild(probe);
      contHeights[state.density] = height;
      return height;
    }

    function buildRecord(index) {
      var question = state.items[index];
      var key = layoutKey(question);
      var cached = layouts.get(key);
      if (cached) return cached;
      var started = performance.now();
      var container = buildQuestionBlock(question);
      var rec = {
        key: key,
        qid: question.id,
        container: container,
        children: Array.prototype.slice.call(container.children),
        ansIdx: -1,
        spans: [],
        subs: [],
        hiddenTotal: 0,
        box: null,
        gap: null,
        boxH: undefined,
        numEl: container.querySelector(".pg-q-no"),
        marker: null,
        markerH: 0,
        units: {},
        measured: false
      };
      rec.children.forEach(function (node, idx) {
        if (node.classList.contains("pg-ansbox")) rec.ansIdx = idx;
      });
      layouts.set(key, rec);
      tally.build += performance.now() - started;
      return rec;
    }

    /**
     * 批量测量（隐藏答案态）：一批题块一次进列、一次强制布局、连续读数。
     * 逐题「插入-读数-移除」会让浏览器为每个题块各回流一次。
     *
     * 答案段先摘下来不进这一趟：题干行的落位高度与答案段在不在场无关
     * （.pg-ansbox 自己无外边距，摘掉只让后续子件整体上移、各自跨距不变），
     * 所以隐藏态量「不含答案的题干」，答案段另量一次独立高度相加即可。
     * 50 道长题带答案的内容量约是纯题干的四倍，这一刀把首屏代价砍回达标线内。
     */
    function measureRecords(list) {
      var todo = list.filter(function (rec) { return !rec.measured; });
      if (!todo.length) return 0;
      var started = performance.now();
      var frag = document.createDocumentFragment();
      todo.forEach(function (rec) {
        if (rec.ansIdx >= 0) {
          rec.box = rec.children[rec.ansIdx];
          rec.gap = rec.children[rec.children.length - 1];
          rec.container.removeChild(rec.box);
        }
        frag.appendChild(rec.container);
      });
      measureEl.appendChild(frag);
      // 先读一次容器位置，把这批题块的布局一次性算完；后续读数不再触发回流。
      measureEl.getBoundingClientRect();
      todo.forEach(readSpans);
      measureEl.textContent = "";
      var cost = performance.now() - started;
      tally.measure += cost;
      return cost;
    }

    function readSpans(rec) {
      var block = rec.container;
      var blockTop = block.offsetTop;
      var height = block.offsetHeight;
      var ink = Math.max(0, block.scrollHeight - height);
      var spans = rec.children.map(function (node, index) {
        if (index === rec.ansIdx) return { node: node, h: 0, box: true };   // 答案段单独量
        var top = node.offsetTop - blockTop;
        var nextIndex = index + 1 === rec.ansIdx ? index + 2 : index + 1;
        var nextTop = nextIndex < rec.children.length
          ? rec.children[nextIndex].offsetTop - blockTop
          : height;
        // 落位高度 = 到下一题干子件的距离，再叠加本子件自身的墨迹外溢
        var overflow = Math.max(0, node.scrollHeight - node.offsetHeight);
        return { node: node, h: Math.max(nextTop - top, node.offsetHeight + overflow) };
      });
      rec.spans = spans;
      var sum = spans.reduce(function (total, span) { return total + span.h; }, 0);
      rec.hiddenTotal = Math.max(height + ink, sum);
      rec.measured = true;
    }

    /**
     * 答案段独立量高：摘下来进测量列量一次，再装回题块（整块落页时它要随题块走）。
     * 只在「显示答案」真的轮到这道题时才量——切答案的同步段因此只碰眼前几页。
     */
    function measureBoxes(list) {
      var todo = list.filter(function (rec) {
        return rec.ansIdx >= 0 && rec.boxH === undefined;
      });
      if (!todo.length) return 0;
      var started = performance.now();
      var frag = document.createDocumentFragment();
      todo.forEach(function (rec) { frag.appendChild(rec.box); });
      measureEl.appendChild(frag);
      measureEl.getBoundingClientRect();
      todo.forEach(function (rec) {
        var box = rec.box;
        rec.boxH = Math.max(box.offsetHeight, box.scrollHeight);
        if (rec.boxH > PAGE_FILL_H) {
          // 单是答案段就超一页：把它的直系子件也量出来，供拆件落页
          var boxTop = box.offsetTop;
          var kids = Array.prototype.slice.call(box.children);
          rec.subs = kids.map(function (node, index) {
            var top = node.offsetTop - boxTop;
            var nextTop = index + 1 < kids.length ? kids[index + 1].offsetTop - boxTop : box.offsetHeight;
            return { node: node, h: Math.max(nextTop - top, node.offsetHeight) };
          });
        }
      });
      measureEl.textContent = "";
      // 装回原位：答案段永远排在末尾间距之前
      todo.forEach(function (rec) {
        if (rec.gap) rec.container.insertBefore(rec.box, rec.gap);
        else rec.container.appendChild(rec.box);
      });
      var cost = performance.now() - started;
      tally.measure += cost;
      return cost;
    }

    function boxHeight(rec) {
      if (rec.ansIdx < 0) return 0;
      if (rec.boxH === undefined) measureBoxes([rec]);
      return rec.boxH || 0;
    }

    function getRecord(index) {
      var rec = recs[index];
      if (!rec) {
        rec = buildRecord(index);
        recs[index] = rec;
      }
      if (!rec.measured) measureRecords([rec]);
      return rec;
    }

    function totalOf(rec, shown) {
      return shown ? rec.hiddenTotal + boxHeight(rec) : rec.hiddenTotal;
    }

    /**
     * 落件清单：整题放得下一页就整块落页（答案段随容器走，靠 data-ans 显隐）；
     * 放不下就按子件拆，超一页的答案段再降一级拆到解析行。
     */
    function unitsFor(rec, shown) {
      var cacheKey = shown ? "S" : "H";
      if (rec.units[cacheKey]) return rec.units[cacheKey];
      var total = totalOf(rec, shown);
      var units = [];
      if (total <= PAGE_FILL_H) {
        units = [{ node: rec.container, h: total, whole: true }];
      } else {
        rec.spans.forEach(function (span, index) {
          if (index === rec.ansIdx) {
            if (!shown) return;                        // 隐藏答案：整段不落纸
            var height = boxHeight(rec);
            if (height > PAGE_FILL_H && rec.subs.length) {
              rec.subs.forEach(function (sub) { units.push({ node: sub.node, h: sub.h }); });
              return;
            }
            units.push({ node: span.node, h: height });
            return;
          }
          units.push({ node: span.node, h: span.h, head: index === 0 });
        });
      }
      rec.units[cacheKey] = units;
      return units;
    }

    // ---------- 页与落页 ----------
    function computeScale() {
      if (!previewEl) return 1;
      var width = previewEl.clientWidth - 32;
      if (width <= 0) return 1;
      return Math.max(0.45, Math.min(1, Math.round((width / PAGE_W) * 1000) / 1000));
    }

    function applyScale() {
      var scale = computeScale();
      activeScale = scale;
      document.documentElement.style.setProperty("--pg-scale", String(scale));
      doc.pages.forEach(function (record) {
        record.wrap.style.width = (PAGE_W * scale) + "px";
        record.wrap.style.height = (PAGE_H * scale) + "px";
      });
    }

    function newPage() {
      var wrap = el("div", "pg-page-wrap");
      var section = el("section", "pg-page");
      section.setAttribute("data-page", String(doc.pages.length + 1));
      section.setAttribute("data-mat", "false");

      var head = el("header", "pg-page-head");
      var title = el("span", "pg-doc-title", state.title);
      head.appendChild(title);
      head.appendChild(el("span", "pg-doc-info", "姓名 ________ 得分 ________"));

      var body = el("div", "pg-page-body");
      var foot = el("footer", "pg-page-foot", "第 " + (doc.pages.length + 1) + " 页");

      section.appendChild(head);
      section.appendChild(body);
      section.appendChild(foot);
      wrap.appendChild(section);
      wrap.style.width = (PAGE_W * activeScale) + "px";
      wrap.style.height = (PAGE_H * activeScale) + "px";
      pagesEl.appendChild(wrap);

      var record = {
        index: doc.pages.length, wrap: wrap, page: section, body: body, foot: foot,
        title: title, used: 0, items: [], mat: false
      };
      doc.pages.push(record);
      return record;
    }

    function placeUnit(record, unit) {
      record.items.push(unit);
      record.used += unit.h;
      unit.node.setAttribute("data-qid", unit.qid);
      unit.node.setAttribute("data-height", String(Math.round(unit.h)));
      if (unit.h > PAGE_FILL_H) unit.node.setAttribute("data-overflow", "true");
      if (record.mat) record.body.appendChild(unit.node);
    }

    /**
     * 按量好的高度落页；放不下就换纸。整题放不下就拆件，且拆件题另起一张纸，
     * 避免题号头孤零零落在页脚——这是原来的「题号+首行合体」做法，
     * 现在靠算术保证，不再改 DOM 结构。
     */
    function placeQuestion(index) {
      var rec = getRecord(index);                 // 建 DOM 与测量各自记台账
      var workStart = performance.now();
      var measureAt = tally.measure;               // 取件时可能就地补量答案段，别重复计一次
      var shown = state.showAnswers;
      var units = unitsFor(rec, shown);
      var page = doc.page;
      var started = false;
      var marked = false;
      var split = units.length > 1;

      if (rec.numEl) rec.numEl.textContent = String(index + 1) + ".";

      units.forEach(function (unit) {
        var item = { node: unit.node, h: unit.h, qid: rec.qid };
        if (!started) {
          started = true;
          if (split && page.used > 0) {
            page = doc.page = closePage(page) || newPage();
          }
        }
        if (page.items.length && page.used + item.h > PAGE_FILL_H) {
          page = doc.page = closePage(page) || newPage();
          if (split && !marked) {
            marked = true;
            placeUnit(page, { node: markerNode(rec), h: contHeight(), qid: rec.qid });
          }
        }
        placeUnit(page, item);
      });
      tally.place += performance.now() - workStart - (tally.measure - measureAt);
      return page;
    }

    function markerNode(rec) {
      if (!rec.marker) rec.marker = el("p", "pg-cont", "（接上题）");
      return rec.marker;
    }

    /**
     * 页收口：已物化的页在此做一次墨迹复核。
     * 若复核把尾件顺延出去了，就返回那张接住尾件的下一页，让落页接力到它上面，
     * 否则再 newPage() 会在卷中插出一张空页。
     */
    function closePage(record) {
      if (!record.mat) return null;
      var before = record.items.length;
      inkSettle(record);
      return record.items.length < before ? doc.pages[record.index + 1] : null;
    }

    /**
     * 只读这一页：contain:strict 把布局代价锁在纸内，越界就把尾件顺延到下一页头部。
     * 下一页若还没物化，等它进视口时再各自复核，天然接力、不必连锁搬整卷。
     */
    function inkSettle(record) {
      var guard = 0;
      while (guard < 8 && record.items.length > 1 &&
             record.body.scrollHeight > record.body.clientHeight + 1) {
        guard += 1;
        var last = record.items.pop();
        record.used -= last.h;
        record.body.removeChild(last.node);
        var next = doc.pages[record.index + 1];
        if (!next) next = newPage();
        next.items.unshift(last);
        next.used += last.h;
        if (next.mat) next.body.insertBefore(last.node, next.body.firstChild);
        if (guard === 1) inkPages += 1;
        inkMoves += 1;
      }
    }

    // ---------- 视口物化 ----------
    function pageStep() {
      return PAGE_H * activeScale + PAGE_GAP;
    }

    function viewportRange() {
      var step = pageStep();
      var top = Math.max(0, previewEl.scrollTop - PREVIEW_PAD);
      var bottom = top + previewEl.clientHeight;
      return {
        first: Math.max(0, Math.floor(top / step)),
        last: Math.max(0, Math.floor(bottom / step))
      };
    }

    function materialize(record) {
      if (record.mat) return;
      var started = performance.now();
      var frag = document.createDocumentFragment();
      record.items.forEach(function (unit) { frag.appendChild(unit.node); });
      record.body.appendChild(frag);
      record.mat = true;
      record.page.setAttribute("data-mat", "true");
      inkSettle(record);
      tally.settle += performance.now() - started;
    }

    function dematerialize(record) {
      if (!record.mat) return;
      record.body.textContent = "";
      record.mat = false;
      record.page.setAttribute("data-mat", "false");
    }

    /** 把卷面排到至少 minPages 页（同步，受时间预算约束），预算用尽交后台补。 */
    function ensurePages(minPages, budgetMs) {
      var started = performance.now();
      while (!doc.complete && doc.pages.length < minPages) {
        advance();
        if (budgetMs && performance.now() - started > budgetMs) break;
      }
    }

    /** 排一题：不足一页就继续往后排，保证每次调用至少产出内容。 */
    function advance() {
      if (doc.complete) return;
      var before = doc.pages.length;
      while (doc.cursor < state.items.length) {
        var index = doc.cursor;
        doc.cursor += 1;
        placeQuestion(index);
        if (doc.pages.length > before) return;    // 已开新页，交回控制权
      }
      finishDoc();
    }

    function finishDoc() {
      if (doc.complete) return;
      doc.complete = true;
      if (doc.idle) {
        if (window.cancelIdleCallback) window.cancelIdleCallback(doc.idle);
        else window.clearTimeout(doc.idle);
        doc.idle = 0;
      }
      doc.pages.forEach(function (record, index) {
        record.foot.textContent = "第 " + (index + 1) + " 页 / 共 " + doc.pages.length + " 页";
      });
      var readyMs = Math.round((performance.now() - (doc.startedAt || performance.now())) * 10) / 10;
      metricsEl.setAttribute("data-ready-ms", String(readyMs));
      metricsEl.setAttribute("data-total-build", String(Math.round(tally.build * 10) / 10));
      metricsEl.setAttribute("data-total-measure", String(Math.round(tally.measure * 10) / 10));
      metricsEl.setAttribute("data-settle", inkPages + "轮/" + inkMoves + "件");
      emitProgress();
      updateMetricsProgress();
      dock("组卷补齐：" + state.items.length + " 题 · " + doc.pages.length + " 页 · 同步 " +
        state.renderMs + " ms / 全卷 " + readyMs + " ms");
    }

    function scheduleIdle() {
      if (doc.complete || doc.idle || !isStage()) return;
      var token = doc.token;
      var run = function () {
        doc.idle = 0;
        if (token !== doc.token || doc.complete || !isStage()) return;
        var started = performance.now();
        do { advance(); } while (!doc.complete && performance.now() - started < CHUNK_MS);
        if (!doc.complete) {
          updateMetricsProgress();
          scheduleIdle();
        }
      };
      if (window.requestIdleCallback) doc.idle = window.requestIdleCallback(run, { timeout: 300 });
      else doc.idle = window.setTimeout(run, 16);
    }

    /** 视口驱动的挂/收：先补页，再挂眼前 ±1 页，远的退回占位纸。 */
    function syncViewport(budgetMs) {
      if (!isStage() || !previewEl || !doc.pages.length) return 0;
      var range = viewportRange();
      var wantLast = range.last + LIVE_BUFFER;
      if (!doc.complete && wantLast >= doc.pages.length) {
        ensurePages(wantLast + 1, budgetMs === undefined ? SCROLL_BUDGET_MS : budgetMs);
        if (!doc.complete) scheduleIdle();
      }
      var lo = Math.max(0, range.first - LIVE_BUFFER);
      var hi = Math.min(doc.pages.length - 1, range.last + LIVE_BUFFER);
      var live = 0;
      for (var i = lo; i <= hi; i += 1) live += 1;
      if (live > MAX_LIVE) hi = lo + MAX_LIVE - 1;
      var cost = performance.now();
      var changed = 0;
      doc.pages.forEach(function (record, index) {
        if (index >= lo && index <= hi) {
          if (!record.mat) { materialize(record); changed += 1; }
        } else if (record.mat && (index < lo - DROP_BUFFER || index > hi + DROP_BUFFER)) {
          dematerialize(record);
          changed += 1;
        }
      });
      return changed ? performance.now() - cost : 0;
    }

    // ---------- 重排驱动 ----------
    function showPreviewEmpty() {
      pagesEl.textContent = "";
      doc.token += 1;
      resetDoc(true, 0);
      var box = el("div", "pg-preview-empty");
      box.appendChild(el("strong", null, "题篮还是空的"));
      box.appendChild(el("p", null, "去「真题题库」挑几道题入篮，本页会自动生成 A4 练习卷。"));
      pagesEl.appendChild(box);
      metricsEl.textContent = "0 题 · 0 页 · 0 ms";
      metricsEl.setAttribute("data-render-ms", "0");
      metricsEl.setAttribute("data-pages", "0");
      metricsEl.setAttribute("data-questions", "0");
      metricsEl.setAttribute("data-doc-ready", "1");
      reflowSeq += 1;
      metricsEl.setAttribute("data-reflow", String(reflowSeq));
    }

    function emitProgress() {
      var overflow = 0;
      doc.pages.forEach(function (record) {
        record.items.forEach(function (unit) {
          if (unit.h > PAGE_FILL_H) overflow += 1;
        });
      });
      metricsEl.setAttribute("data-pages", String(doc.pages.length));
      metricsEl.setAttribute("data-overflow", String(overflow));
      metricsEl.setAttribute("data-placed", String(doc.cursor));
      metricsEl.setAttribute("data-doc-ready", doc.complete ? "1" : "0");
      metricsEl.setAttribute("data-live", String(doc.pages.filter(function (r) { return r.mat; }).length));
    }

    function updateMetricsProgress() {
      emitProgress();
      var ready = doc.complete ? "" : " · 排版中 " + doc.cursor + "/" + state.items.length;
      metricsEl.textContent = state.items.length + " 题 · " + doc.pages.length + " 页 · " +
        state.renderMs + " ms" + ready;
    }

    /**
     * 重排：只同步做「眼前这 2-3 页」——建 DOM、量版式、算术分页、挂进纸面。
     * 其余页交空闲补齐；data-render-ms 记的是同步段，data-ready-ms 记全卷补齐。
     */
    function reflow() {
      if (!isStage() || !pagesEl) return;
      var started = performance.now();

      if (doc.idle) {
        if (window.cancelIdleCallback) window.cancelIdleCallback(doc.idle);
        else window.clearTimeout(doc.idle);
        doc.idle = 0;
      }
      doc.token += 1;
      pagesEl.textContent = "";
      resetDoc(false, started);
      inkMoves = 0;
      inkPages = 0;
      pagesEl.setAttribute("data-density", state.density);
      pagesEl.setAttribute("data-ans", state.showAnswers ? "show" : "hide");

      if (!state.items.length) {
        showPreviewEmpty();
        state.renderMs = Math.round((performance.now() - started) * 10) / 10;
        renderSide();
        return;
      }

      activeScale = computeScale();
      document.documentElement.style.setProperty("--pg-scale", String(activeScale));
      measureEl.setAttribute("data-density", state.density);
      recs = [];
      tally = { build: 0, measure: 0, place: 0, settle: 0 };

      var page = newPage();
      doc.page = page;

      // 同步段只做视口那几页：先按眼前范围补齐页数，再挂进纸面
      var range = viewportRange();
      ensurePages(range.last + LIVE_BUFFER + 1, 0);
      syncViewport(0);
      var sync = { build: tally.build, measure: tally.measure, place: tally.place, settle: tally.settle };
      var syncInkPages = inkPages;
      var syncInkMoves = inkMoves;

      state.renderMs = Math.round((performance.now() - started) * 10) / 10;
      metricsEl.setAttribute("data-render-ms", String(state.renderMs));
      metricsEl.setAttribute("data-questions", String(state.items.length));
      metricsEl.setAttribute("data-density", state.density);
      metricsEl.setAttribute("data-virtual", "1");
      metricsEl.setAttribute("data-answers", String(state.items.filter(function (question) {
        return Boolean(answerText(question));
      }).length));
      reflowSeq += 1;
      metricsEl.setAttribute("data-reflow", String(reflowSeq));
      // 分段耗时沿用旧指标名，保证历史探针口径连续；记的是同步段真实耗时
      metricsEl.setAttribute("data-t-build", String(Math.round(sync.build * 10) / 10));
      metricsEl.setAttribute("data-t-measure-blocks", String(Math.round(sync.measure * 10) / 10));
      metricsEl.setAttribute("data-t-place", String(Math.round(sync.place * 10) / 10));
      metricsEl.setAttribute("data-t-settle", String(Math.round(sync.settle * 10) / 10));
      metricsEl.setAttribute("data-settle", syncInkPages + "轮/" + syncInkMoves + "件");
      metricsEl.setAttribute("data-t-sync", String(state.renderMs));
      emitProgress();
      updateMetricsProgress();

      if (!doc.complete) scheduleIdle();
      else finishDoc();
    }

    /** 换卷：只改 doc 的字段，不换对象——plugin.js 也握着同一个引用。 */
    function resetDoc(complete, startedAt) {
      doc.pages = [];
      doc.page = null;
      doc.cursor = 0;
      doc.complete = complete;
      doc.idle = 0;
      doc.startedAt = startedAt;
    }

    /** 题篮变了就丢掉逐题记录：旧记录里的题号已经对不上纸面。 */
    function forgetRecords() {
      recs = [];
    }

    /** 版式缓存瘦身：只留当前题篮在两种密度下的记录。 */
    function pruneLayouts() {
      if (layouts.size <= state.items.length * 2) return;
      var keep = new Set();
      state.items.forEach(function (question) {
        keep.add(question.id + "\u0001" + "normal");
        keep.add(question.id + "\u0001" + "compact");
      });
      Array.from(layouts.keys()).forEach(function (key) {
        var prefix = key.slice(0, key.lastIndexOf("\u0001"));
        if (!keep.has(prefix)) layouts.delete(key);
      });
    }

    return {
      doc: doc,
      reflow: reflow,
      applyScale: applyScale,
      syncViewport: syncViewport,
      advance: advance,
      materialize: materialize,
      pruneLayouts: pruneLayouts,
      forgetRecords: forgetRecords
    };
  }

  global.JzoPaperLayout = { create: create };
})(window);
