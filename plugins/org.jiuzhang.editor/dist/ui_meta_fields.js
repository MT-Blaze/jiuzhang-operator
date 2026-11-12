/**
 * ui_meta_fields.js —— 公共元数据的「字段与候选」层：无箭头组合框、字典灌入、原文件名回填。
 *
 * 军令：候选框一律不带原生下拉箭头；打字才弹悬浮列表，点中才绑定字典 ID。
 * 标准名与批次同步在 ui_std_name.js；这里只管「字段值怎么来、怎么填」。
 */
(function (global) {
  "use strict";

  var EXAM_ALIASES = {
    "模拟考": ["模考", "模拟", "模拟考试", "一模", "二模", "三模",
      "四模", "五模", "六模", "七模", "八模", "九模", "十模"],
    "高考": ["全国卷", "新高考"],
    "学业水平": ["会考", "学考"],
    "月考": ["月测"],
    "周测": ["周考"],
    "开学考": ["摸底考"]
  };

  function create(deps) {
    var panel = deps.coreState.panel;
    var dom = deps.dom;
    var hostCall = deps.hostCall;
    var metaParse = window.JzoEditorMetaParse;
    var MetaCombo = window.JzoEditorMetaCombo;
    var combos = {};

    function text(value) { return String(value == null ? "" : value).trim(); }

    function valueOf(name) {
      var instance = combos[name];
      if (instance) return instance.getValue();
      var node = {
        year: dom.panelMetaYearEl,
        month: dom.panelMetaMonthEl,
        mock_round: dom.panelMetaMockRoundEl
      }[name];
      return node ? text(node.value) : "";
    }

    function namesOf(rows) {
      return (rows || []).map(function (row) {
        return text(typeof row === "string" ? row : (row && row.name));
      }).filter(Boolean);
    }

    function uniqueNames(groups) {
      var seen = {};
      var out = [];
      groups.forEach(function (group) {
        namesOf(group).forEach(function (name) {
          if (seen[name]) return;
          seen[name] = true;
          out.push(name);
        });
      });
      return out;
    }

    function itemsOf(names, hint) {
      return names.map(function (name) { return { id: name, name: name, hint: hint || "" }; });
    }

    function examItems() {
      return uniqueNames([namesOf(panel.engineMeta && panel.engineMeta.exam_types),
        panel.history && panel.history.exam_type]).map(function (name) {
        return { id: name, name: name, aliases: EXAM_ALIASES[name] || [] };
      });
    }

    function bodyItems() {
      var items = itemsOf(uniqueNames([
        panel.engineMeta && panel.engineMeta.exam_orgs,
        panel.history && panel.history.body
      ]), "考试主体");
      panel.schools.forEach(function (school) {
        items.push({
          id: "school:" + text(school.id),
          name: text(school.short_name || school.full_name),
          hint: "学校",
          kind: "school"
        });
      });
      return items;
    }

    /** 字典是活的：引擎、历史、本批学校任何一处变了，所有候选框跟着换。 */
    function refresh() {
      var feed = {
        subject: uniqueNames([namesOf(panel.engineMeta && panel.engineMeta.subjects),
          panel.history && panel.history.subject]),
        grade: uniqueNames([namesOf(panel.engineMeta && panel.engineMeta.grades)]),
        // 地区一律来自底座字典：全国/东三省这类宏观节点也由后端给，前端不再硬编码。
        region: uniqueNames([namesOf(panel.engineMeta && panel.engineMeta.regions),
          panel.history && panel.history.region]),
        exam_level: namesOf(panel.engineMeta && panel.engineMeta.exam_levels),
        semester: ["上学期", "下学期"],
        scene: panel.scenes || []
      };
      Object.keys(feed).forEach(function (name) {
        if (combos[name]) combos[name].setItems(itemsOf(feed[name]));
      });
      if (combos.exam_type) combos.exam_type.setItems(examItems());
      if (combos.body) combos.body.setItems(bodyItems());
    }

    function setValue(name, value, id) {
      var instance = combos[name];
      if (!instance) return;
      if (instance.input === document.activeElement) return;
      instance.setValue(text(value), id);
    }

    function syncFromMeta(meta) {
      setValue("subject", meta.subject);
      setValue("grade", meta.grade);
      setValue("region", meta.region);
      setValue("semester", meta.semester);
      setValue("exam_level", meta.exam_level);
      setValue("exam_type", meta.exam_type);
      setValue("body", meta.body);
      setValue("scene", meta.scene_type);
    }

    // ---------- 考试层级级联：全国统考收起参考地区与考试主体 ----------

    function applyExamLevelCascade() {
      var national = valueOf("exam_level") === "全国统考";
      if (dom.panelRegionFieldEl) dom.panelRegionFieldEl.hidden = national;
      if (dom.panelBodyFieldEl) dom.panelBodyFieldEl.hidden = national;
      if (national) {
        setValue("region", "");
        setValue("body", "");
      }
    }

    // ---------- 主体是学校：立即绑定字典 ID，让第五行能据此收起 ----------

    function isSchoolItem(item) {
      return Boolean(item) && (item.kind === "school" || /^school:/.test(text(item.id)));
    }

    function onBodyAccept(item, typed) {
      if (isSchoolItem(item)) {
        deps.onBodySchool({
          id: text(item.id).replace(/^school:/, ""),
          short_name: item.name,
          full_name: item.name
        });
        return;
      }
      var name = text(typed || (item && item.name));
      if (!name) return;
      hostCall("meta.schools", { q: name, limit: 5 }).then(function (result) {
        var rows = (result && Array.isArray(result.schools)) ? result.schools : [];
        var hit = rows.filter(function (row) {
          return text(row.short_name) === name || text(row.full_name) === name;
        })[0];
        if (hit) deps.onBodySchool(hit);
      }, function () { return null; });
    }

    /** 考试类型敲「二模」也要认：先归一成模拟考，再把轮次填上。 */
    function onExamTypeAccept(item, typed) {
      var raw = text(typed || (item && item.name));
      var canonical = text(item && item.name);
      var mock = canonical === "模拟考" || canonical === "模考"
        || /[一二三四五六七八九十\d]+模/.test(canonical + raw);
      if (!mock) return;
      var round = raw.match(/([一二三四五六七八九十\d]+)模/);
      if (round && dom.panelMetaMockRoundEl) {
        var value = metaParse ? metaParse.toNumber(round[1]) : Number(round[1]);
        if (value >= 1 && value <= 10) dom.panelMetaMockRoundEl.value = String(value);
      }
      deps.onChange();
    }

    // ---------- 原文件名：正则回填，只做加法 ----------

    function parseDict() {
      return {
        grades: namesOf(panel.engineMeta && panel.engineMeta.grades),
        subjects: namesOf(panel.engineMeta && panel.engineMeta.subjects),
        regions: uniqueNames([namesOf(panel.engineMeta && panel.engineMeta.regions),
          panel.history && panel.history.region])
      };
    }

    function parseSourceName(raw) {
      return metaParse ? metaParse.parseSourceName(raw, parseDict()) : {};
    }

    function resolveParsedSchool(name) {
      if (!name) return Promise.resolve(null);
      return hostCall("meta.schools", { q: name, limit: 5 }).then(function (result) {
        var rows = (result && Array.isArray(result.schools)) ? result.schools : [];
        var hit = rows.filter(function (row) {
          return text(row.short_name) === name || text(row.full_name) === name;
        })[0];
        if (hit) deps.onBodySchool(hit);
        return hit || null;
      }, function () { return null; });
    }

    function applyParsed(parsed) {
      var data = parsed || {};
      if (data.year && dom.panelMetaYearEl) dom.panelMetaYearEl.value = text(data.year);
      if (data.month && dom.panelMetaMonthEl) dom.panelMetaMonthEl.value = text(data.month);
      if (data.mock_round && dom.panelMetaMockRoundEl) {
        dom.panelMetaMockRoundEl.value = text(data.mock_round);
      }
      if (data.exam_type) setValue("exam_type", data.exam_type);
      if (data.grade) setValue("grade", data.grade);
      if (data.subject) setValue("subject", data.subject);
      if (data.region) setValue("region", data.region);
      if (data.semester) setValue("semester", data.semester);
      if (data.body) setValue("body", data.body);
      deps.onChange();
      if (data.body_kind === "school" && data.body) {
        resolveParsedSchool(data.body);
      } else if (data.school) {
        resolveParsedSchool(data.school);
      }
    }

    // ---------- 控件接线 ----------

    function makeCombo(name, input, options) {
      if (!input || !MetaCombo) return null;
      var settings = options || {};
      var instance = MetaCombo.create({
        input: input,
        strict: settings.strict !== false,
        allowFreeText: Boolean(settings.allowFreeText),
        preferRemote: Boolean(settings.preferRemote),
        emptyText: settings.emptyText,
        remote: function (query, done) {
          hostCall("meta.schools", { q: query, limit: 8 }).then(function (result) {
            var rows = (result && Array.isArray(result.schools)) ? result.schools : [];
            done(rows.map(function (row) {
              return {
                id: "school:" + text(row.id),
                name: text(row.short_name || row.full_name),
                hint: "学校",
                kind: "school"
              };
            }));
          }, function () { done([]); });
        },
        onAccept: settings.onAccept,
        onChange: deps.onChange
      });
      combos[name] = instance;
      return instance;
    }

    function bindFields() {
      makeCombo("subject", dom.panelMetaSubjectEl, {});
      makeCombo("grade", dom.panelMetaGradeEl, {});
      makeCombo("region", dom.panelMetaRegionEl, {});
      makeCombo("semester", dom.panelMetaSemesterEl, {});
      makeCombo("scene", dom.panelMetaSceneEl, {});
      makeCombo("exam_level", dom.panelMetaExamLevelEl, {});
      // 类型允许手填：老师写的新类型后端会立即建档，前端不许在失焦时把字清掉。
      makeCombo("exam_type", dom.panelMetaExamTypeEl, {
        strict: false,
        allowFreeText: true,
        onAccept: onExamTypeAccept
      });
      // 主体可能是学校也可能是一个联盟：允许手填，命中学校字典才收起第五行。
      makeCombo("body", dom.panelMetaBodyEl, {
        strict: false,
        allowFreeText: true,
        preferRemote: true,
        onAccept: onBodyAccept
      });
      [dom.panelMetaYearEl, dom.panelMetaMonthEl, dom.panelMetaMockRoundEl]
        .forEach(function (node) {
          if (!node) return;
          node.addEventListener("input", deps.onPlainInput);
          node.addEventListener("change", deps.onPlainInput);
        });
      if (dom.panelSrcNameEl) {
        dom.panelSrcNameEl.addEventListener("input", deps.onSourceEdited);
        dom.panelSrcNameEl.addEventListener("blur", deps.onSourceBlur);
        dom.panelSrcNameEl.addEventListener("keydown", function (event) {
          if (event.key === "Enter") dom.panelSrcNameEl.blur();
        });
      }
      refresh();
    }

    return {
      applyExamLevelCascade: applyExamLevelCascade,
      applyParsed: applyParsed,
      bindFields: bindFields,
      getValue: valueOf,
      parseSourceName: parseSourceName,
      refresh: refresh,
      setScene: function (value) { setValue("scene", value); },
      setValue: setValue,
      syncFromMeta: syncFromMeta,
    };
  }

  global.JzoEditorMetaFields = { create: create };
})(window);
