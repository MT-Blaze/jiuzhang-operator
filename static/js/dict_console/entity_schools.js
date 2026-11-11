/**
 * 实体维度 · 行政区划与学校（2026-11-11）：
 * 底层仍是 dim_regions / dim_schools 两张独立表，前端按 parent_id、region_id 合树。
 * 默认只露 34 个省级；点省展开地级市，点市展开该市学校。
 * 双击节点改名、行尾＋/改名/删；市节点＋默认在该市下新建学校。
 * 整块下架：删本文件与 entities.css 的 det-* 段即可。
 */
(function () {
  "use strict";

  var S = window.DcEntityShared;
  var REGION_URL = "/api/bank/engine/dict/dim_regions";
  var SCHOOL_URL = "/api/bank/engine/dict/dim_schools";

  function mount(host) {
    var section = S.el("section", "det-panel dc-entity-regions");
    section.setAttribute("aria-label", "行政区划与学校");

    var tools = S.el("div", "dc-table-tools");
    var search = document.createElement("input");
    search.type = "search";
    search.className = "dc-table-search";
    search.placeholder = "搜索省 / 市 / 学校…（例如：哈尔滨）";
    search.setAttribute("aria-label", "搜索行政区划与学校");
    var addProvince = S.el("button", "dc-btn dc-table-add", "新增省份");
    addProvince.type = "button";
    var count = S.el("span", "dc-table-count", "");
    count.setAttribute("role", "status");
    tools.appendChild(search);
    tools.appendChild(addProvince);
    tools.appendChild(count);
    section.appendChild(tools);

    var tree = S.el("div", "det-tree");
    section.appendChild(tree);
    var stateEl = S.el("p", "dc-table-state", "");
    stateEl.setAttribute("role", "status");
    stateEl.setAttribute("aria-live", "polite");
    section.appendChild(stateEl);
    host.appendChild(section);

    var state = {
      provinces: [], cities: {}, schools: {}, unassigned: [],
      expanded: new Set(), keyword: "", seq: 0, loaded: false
    };

    function setStatus(text) { stateEl.textContent = text; }

    function byOrder(a, b) {
      var ao = Number(a.sort_order) || 0;
      var bo = Number(b.sort_order) || 0;
      return ao - bo || Number(a.id) - Number(b.id);
    }

    function schoolCount(city) {
      return (state.schools[city.id] || []).length;
    }

    function provinceSchools(province) {
      return (state.cities[province.id] || []).reduce(function (sum, city) {
        return sum + schoolCount(city);
      }, 0);
    }

    function select(li) {
      var old = tree.querySelector(".det-row.is-selected");
      if (old) old.classList.remove("is-selected");
      li.querySelector(".det-row").classList.add("is-selected");
    }

    var makeRow = S.bindTree(state.expanded, select);
    var childList = S.childList;

    function renameRegion(row, anchor) {
      S.rename({
        title: "修改区划名称",
        message: "编码保持不变；同一父级下名称不能重复。",
        anchor: anchor,
        url: REGION_URL + "/" + row.id,
        fields: [{ key: "name", label: "区划名称", required: true, value: row.name }],
        onDone: function () { reload().then(function () { setStatus("已改名。"); }); }
      });
    }

    function removeRegion(row, anchor) {
      S.remove({
        url: REGION_URL, row: row, anchor: anchor,
        reload: reload, setStatus: setStatus
      });
    }

    function addCity(province, anchor) {
      var siblings = state.cities[province.id] || [];
      S.add({
        title: "在「" + province.name + "」下新增地级市",
        message: "名称只填核心地名，不带“市/地区”后缀；编码填六位行政区划代码。",
        anchor: anchor,
        url: REGION_URL,
        fields: [
          { key: "name", label: "市名称", required: true, placeholder: "如 哈尔滨" },
          { key: "code", label: "行政区划代码", required: true, placeholder: "如 230100" }
        ],
        build: function (values) {
          return {
            name: values.name, code: values.code, level: 2,
            parent_id: province.id, sort_order: S.nextOrder(siblings)
          };
        },
        onDone: function () {
          state.expanded.add("r:" + province.id);
          reload().then(function () { setStatus("已新增地级市。"); });
        }
      });
    }

    function addProvinceRow(anchor) {
      S.add({
        title: "新增省级行政区",
        message: "名称只填核心地名，不带“省/自治区”后缀；编码填六位行政区划代码。",
        anchor: anchor,
        url: REGION_URL,
        fields: [
          { key: "name", label: "省级名称", required: true, placeholder: "如 黑龙江" },
          { key: "code", label: "行政区划代码", required: true, placeholder: "如 230000" }
        ],
        build: function (values) {
          return {
            name: values.name, code: values.code, level: 1,
            sort_order: S.nextOrder(state.provinces)
          };
        },
        onDone: function () { reload().then(function () { setStatus("已新增省级行政区。"); }); }
      });
    }

    function renameSchool(row, anchor) {
      S.rename({
        title: "修改学校",
        message: "全称与简称都要保留；编码不变。",
        anchor: anchor,
        url: SCHOOL_URL + "/" + row.id,
        fields: [
          { key: "name", label: "学校全称", required: true, value: row.name },
          { key: "short_name", label: "学校简称", required: true, value: row.short_name }
        ],
        onDone: function () { reload().then(function () { setStatus("已改名。"); }); }
      });
    }

    function addSchool(city, anchor) {
      var siblings = state.schools[city.id] || [];
      S.add({
        title: "在「" + city.name + "」下新增学校",
        message: "学校全称全局唯一；简称在同一地区内唯一。",
        anchor: anchor,
        url: SCHOOL_URL,
        fields: [
          { key: "name", label: "学校全称", required: true, placeholder: "如 哈尔滨市第三中学校" },
          { key: "short_name", label: "学校简称", required: true, placeholder: "如 哈三中" },
          { key: "code", label: "学校编码", required: true, placeholder: "如 hrb3z" }
        ],
        build: function (values) {
          return {
            name: values.name, short_name: values.short_name, code: values.code,
            region: city.name, region_id: city.id, sort_order: S.nextOrder(siblings)
          };
        },
        onDone: function () {
          state.expanded.add("c:" + city.id);
          reload().then(function () { setStatus("已新增学校。"); });
        }
      });
    }

    function removeSchool(row, anchor) {
      S.remove({
        url: SCHOOL_URL, row: row, anchor: anchor,
        reload: reload, setStatus: setStatus
      });
    }

    function renderSchool(school) {
      return makeRow({
        level: 3, depth: 2, name: school.name,
        sub: (school.short_name || "") + (school.code ? " · " + school.code : ""),
        crumb: school._crumb || "",
        remove: function (btn) { removeSchool(school, btn); },
        rename: function (btn) { renameSchool(school, btn); }
      });
    }

    function renderCity(province, city) {
      var kids = state.schools[city.id] || [];
      var expanded = state.expanded.has("c:" + city.id);
      var box = kids.length ? childList(2, expanded) : null;
      if (box) kids.forEach(function (school) { box.appendChild(renderSchool(school)); });
      return makeRow({
        level: 2, depth: 1, name: city.name, sub: city.code,
        badge: kids.length + " 校",
        key: "c:" + city.id,
        hasChildren: kids.length > 0,
        expanded: expanded,
        children: box,
        addText: "校", addLabel: "在「" + city.name + "」下新增学校",
        add: function (btn) { addSchool(city, btn); },
        rename: function (btn) { renameRegion(city, btn); },
        remove: function (btn) { removeRegion(city, btn); }
      });
    }

    function renderProvince(province) {
      var cities = (state.cities[province.id] || []).slice().sort(byOrder);
      var expanded = state.expanded.has("r:" + province.id);
      var box = cities.length ? childList(1, expanded) : null;
      if (box) {
        cities.forEach(function (city) { box.appendChild(renderCity(province, city)); });
      }
      return makeRow({
        level: 1, depth: 0, name: province.name, sub: province.code,
        badge: cities.length + " 市 · " + provinceSchools(province) + " 校",
        key: "r:" + province.id,
        hasChildren: cities.length > 0,
        expanded: expanded,
        children: box,
        addText: "市", addLabel: "在「" + province.name + "」下新增地级市",
        add: function (btn) { addCity(province, btn); },
        rename: function (btn) { renameRegion(province, btn); },
        remove: function (btn) { removeRegion(province, btn); }
      });
    }

    function renderSearch(keyword) {
      var needle = keyword.toLowerCase();
      var hits = 0;
      function hit(value) {
        return value != null && String(value).toLowerCase().indexOf(needle) !== -1;
      }
      var ul = S.el("ul", "det-list");
      state.provinces.forEach(function (province) {
        if (hit(province.name) || hit(province.code)) {
          hits += 1;
          ul.appendChild(renderProvince(province));
        }
        (state.cities[province.id] || []).forEach(function (city) {
          if (hit(city.name) || hit(city.code)) {
            hits += 1;
            var li = renderCity(province, city);
            li.querySelector(".det-crumb").textContent = province.name;
            ul.appendChild(li);
          }
          (state.schools[city.id] || []).forEach(function (school) {
            if (!hit(school.name) && !hit(school.short_name) && !hit(school.code)) return;
            hits += 1;
            var schoolLi = renderSchool(school);
            schoolLi.querySelector(".det-crumb").textContent =
              province.name + " › " + city.name;
            ul.appendChild(schoolLi);
          });
        });
      });
      tree.textContent = "";
      if (!hits) {
        tree.appendChild(S.el("p", "det-empty", "没有匹配的省 / 市 / 学校。"));
        count.textContent = "命中 0 项";
        return;
      }
      tree.appendChild(ul);
      count.textContent = "命中 " + hits + " 项";
    }

    function renderTree() {
      tree.textContent = "";
      var ul = S.el("ul", "det-list");
      state.provinces.forEach(function (province) {
        ul.appendChild(renderProvince(province));
      });
      if (state.unassigned.length) {
        var orphanOpen = state.expanded.has("u:");
        var box = childList(1, orphanOpen);
        state.unassigned.forEach(function (school) { box.appendChild(renderSchool(school)); });
        ul.appendChild(makeRow({
          level: 1, depth: 0, name: "未归属区划", sub: "region_id 为空",
          badge: state.unassigned.length + " 校",
          key: "u:",
          hasChildren: true,
          expanded: orphanOpen,
          children: box
        }));
      }
      tree.appendChild(ul);
      var cityTotal = state.provinces.reduce(function (sum, province) {
        return sum + (state.cities[province.id] || []).length;
      }, 0);
      var schoolTotal = state.provinces.reduce(function (sum, province) {
        return sum + provinceSchools(province);
      }, state.unassigned.length);
      count.textContent = "共 " + state.provinces.length + " 省 · " + cityTotal + " 市 · "
        + schoolTotal + " 校";
    }

    function render() {
      if (state.keyword) renderSearch(state.keyword);
      else renderTree();
    }

    function reload() {
      var seq = (state.seq || 0) + 1;
      state.seq = seq;
      if (!state.loaded) setStatus("正在读取区划与学校…");
      return Promise.all([
        S.listAll("dim_regions"),
        S.listAll("dim_schools")
      ]).then(function (results) {
        if (!section.isConnected || seq !== state.seq) return;
        var regions = results[0].items.slice().sort(byOrder);
        var schools = results[1].items.slice().sort(byOrder);
        state.provinces = regions.filter(function (row) { return row.level === 1; });
        state.cities = {};
        regions.forEach(function (row) {
          if (row.level !== 2) return;
          (state.cities[row.parent_id] = state.cities[row.parent_id] || []).push(row);
        });
        state.schools = {};
        state.unassigned = [];
        schools.forEach(function (row) {
          if (row.region_id == null) state.unassigned.push(row);
          else (state.schools[row.region_id] = state.schools[row.region_id] || []).push(row);
        });
        state.loaded = true;
        render();
        setStatus(state.keyword ? "" : "双击节点可改名；市节点＋默认在该市下建学校。");
      }).catch(function (error) {
        if (!section.isConnected || seq !== state.seq) return;
        setStatus("加载失败：" + error.message);
      });
    }

    addProvince.addEventListener("click", function () { addProvinceRow(addProvince); });

    var timer = null;
    search.addEventListener("input", function () {
      window.clearTimeout(timer);
      timer = window.setTimeout(function () {
        state.keyword = search.value.trim();
        render();
      }, 220);
    });

    reload();
    return { reload: reload };
  }

  window.DcEntitySchools = { mount: mount };
})();
