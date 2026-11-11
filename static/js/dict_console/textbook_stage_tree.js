/**
 * 教材与章节 · 树顶两级（2026-11-11）：
 * 「实体维度字典 → 教材与章节」由平铺的 版本 → 册次 升为 学段 → 科目 → 版本。
 * 第一层固定 高中 / 初中 / 小学 三档（默认折叠），第二层按 subject_id 聚合出
 * 「数学 · 17个版本」；版本及以下的渲染与读写交互仍归 entity_textbooks.js。
 * 本模块只负责分组、两级行与搜索时的可见性谓词，不碰任何数据读写。
 * 整块下架：删本文件、dict_console.html 的引用行与 entities.css 的 det-stage 段即可。
 */
(function () {
  "use strict";

  var STAGES = ["高中", "初中", "小学"];

  function order(a, b) {
    var ao = Number(a.sort_order) || 0;
    var bo = Number(b.sort_order) || 0;
    return ao - bo || Number(a.id) - Number(b.id);
  }

  function stageKey(name) { return "st:" + name; }

  function subjectKey(name, subjectId) { return "s:" + name + ":" + subjectId; }

  /**
   * versions → 三档学段，每档再按 subject_id 分组。
   * 同一版本跨学段时在每档各计一次，与全局设置按学段收口的口径一致；
   * 学段来自版本下挂册次的年级反推，未知学段名忽略（由调用方兜底展示）。
   */
  function group(versions, subjects) {
    var meta = {};
    (subjects || []).forEach(function (item) { meta[item.id] = item; });
    var buckets = STAGES.map(function (name) {
      return { name: name, subjects: [], bySubject: {} };
    });
    var byName = {};
    buckets.forEach(function (bucket) { byName[bucket.name] = bucket; });
    (versions || []).forEach(function (version) {
      (version.stages || []).forEach(function (stage) {
        var bucket = byName[stage];
        if (!bucket) return;
        var item = bucket.bySubject[version.subject_id];
        if (!item) {
          var known = meta[version.subject_id];
          item = {
            id: version.subject_id,
            name: known ? known.name : "学科 " + version.subject_id,
            sort_order: known ? known.sort_order : 0,
            versions: []
          };
          bucket.bySubject[version.subject_id] = item;
          bucket.subjects.push(item);
        }
        item.versions.push(version);
      });
    });
    buckets.forEach(function (bucket) {
      bucket.subjects.sort(order);
      bucket.subjects.forEach(function (item) { item.versions.sort(order); });
    });
    return buckets;
  }

  function subjectRow(bucket, item, versions, ctx) {
    var key = subjectKey(bucket.name, item.id);
    var expanded = ctx.expanded.has(key);
    var box = ctx.childList(2, expanded);
    var full = item.versions.length;
    var li = ctx.makeRow({
      level: 2, depth: 1,
      name: item.name + " · " + full + "个版本",
      badge: ctx.hitMode ? versions.length + " 条命中" : "",
      key: key,
      hasChildren: versions.length > 0,
      expanded: expanded,
      children: box,
      lazy: versions.length ? function () {
        versions.forEach(function (version) { box.appendChild(ctx.renderVersion(version)); });
      } : null
    });
    li.classList.add("det-stage-subject");
    return li;
  }

  function stageRow(bucket, rows, ctx) {
    var key = stageKey(bucket.name);
    var expanded = ctx.expanded.has(key);
    var box = ctx.childList(1, expanded);
    var total = 0;
    rows.forEach(function (entry) {
      total += entry.versions.length;
      box.appendChild(subjectRow(bucket, entry.item, entry.versions, ctx));
    });
    var li = ctx.makeRow({
      level: 1, depth: 0, name: bucket.name,
      badge: rows.length + " 个科目 · " + total + " 个版本",
      key: key,
      hasChildren: rows.length > 0,
      expanded: expanded,
      children: box
    });
    li.classList.add("det-stage-root");
    return li;
  }

  /**
   * 渲染三档学段。搜索态（hitMode）只保留有命中的科目分支；
   * 常态即使某档暂时没版本也保留节点，保证第一层恒为三档。
   */
  function render(list, ctx) {
    var emitted = 0;
    (ctx.groups || []).forEach(function (bucket) {
      var rows = [];
      bucket.subjects.forEach(function (item) {
        var versions = ctx.versionsOf ? ctx.versionsOf(item) : item.versions;
        if (ctx.hitMode && !versions.length) return;
        rows.push({ item: item, versions: versions });
      });
      if (ctx.hitMode && !rows.length) return;
      list.appendChild(stageRow(bucket, rows, ctx));
      emitted += 1;
    });
    return emitted;
  }

  function singleNode(ctx, key, name, sub, badge, build) {
    var expanded = ctx.expanded.has(key);
    var box = ctx.childList(1, expanded);
    return ctx.makeRow({
      level: 1, depth: 0, name: name, sub: sub, badge: badge,
      key: key, hasChildren: true, expanded: expanded, children: box,
      lazy: function () { build(box); }
    });
  }

  /** 数据体检兜底：版本没册次反推不出学段、册次没版本可挂，仍要看得见、点得动。 */
  function renderFallback(list, ctx) {
    var pending = ctx.pending || [];
    if (ctx.hitMode) pending = pending.filter(ctx.versionVisible);
    if (pending.length) {
      list.appendChild(singleNode(ctx, "st:pending", "未定学段",
        "版本尚未挂册次，暂时归不入学段", pending.length + " 个版本",
        function (box) {
          pending.forEach(function (version) { box.appendChild(ctx.renderVersion(version)); });
        }));
    }
    var books = ctx.orphans || [];
    if (ctx.hitMode) books = books.filter(ctx.bookVisible);
    if (books.length) {
      list.appendChild(singleNode(ctx, "v:orphan", "未挂版本", "version_id 为空",
        books.length + " 册", function (box) {
          books.forEach(function (book) {
            box.appendChild(ctx.renderBook(book, 3, ctx.bookShowAll(book)));
          });
        }));
    }
  }

  window.DcTextbookStageTree = {
    STAGES: STAGES,
    group: group,
    render: render,
    renderFallback: renderFallback,
    stageKey: stageKey,
    subjectKey: subjectKey
  };
})();
