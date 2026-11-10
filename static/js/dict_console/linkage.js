/**
 * 四栏联动装配（阶段三）：教材章节 → 章节知识点 → 考向 → 辅助知识点标签。
 * 挂在教研属性分类页签顶部（DcTabs/ctx.openCategory 机制不变）：
 * 左栏由全局设置驱动，逐级选中逐级点亮下游；上游重选即清空下游。
 * 整块下架：删本目录 linkage*.js + CSS + panels.js 的 DcLinkage.mount 调用。
 */
(function () {
  "use strict";

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function column(grid, title, hint, label) {
    var section = el("section", "dcl-col");
    section.setAttribute("aria-label", label);
    section.appendChild(el("h3", "dcl-col-title", title));
    section.appendChild(el("p", "dcl-col-hint", hint));
    var body = el("div", "dcl-col-body");
    section.appendChild(body);
    grid.appendChild(section);
    return body;
  }

  function mount(panel, ctx) {
    var wrap = el("section", "dcl-wrap");
    wrap.setAttribute("aria-label", "四栏联动教研字典");
    wrap.appendChild(el("h3", "dc-panel-title", "四栏联动教研字典"));
    wrap.appendChild(el("p", "dc-panel-hint",
      "左起：教材章节 → 章节知识点 → 考向 → 辅助知识点标签。双击改名 · 拖拽或 Alt+方向键排序（自动保存）· 删除自动防呆。"));
    var grid = el("div", "dcl-grid");
    var treeBody = column(grid, "① 教材章节", "全局设置选教材后展示真实章节", "教材章节树");
    var pointsBody = column(grid, "② 章节知识点", "双击改名 · 拖拽排序", "章节知识点清单");
    var directionsBody = column(grid, "③ 考向", "新增 / 改名 / 删除防呆", "考向清单");
    var tagsBody = column(grid, "④ 辅助知识点标签", "全局搜索添加 · 拖拽排序", "辅助知识点标签");
    wrap.appendChild(grid);
    panel.appendChild(wrap);

    var tags = window.DcLinkTags.mount(tagsBody);
    var directions = window.DcLinkDirections.mount(directionsBody, {
      // 考向选中时保留上一步的主知识点，最右栏据此排除自身。
      onSelect: function (directionId) { tags.load(directionId); }
    });
    var points = window.DcLinkPoints.mount(pointsBody, {
      onSelect: function (pointId) {
        directions.load(pointId);
        tags.load(null, pointId);
      }
    });
    window.DcLinkTree.mount(treeBody, ctx, {
      onSelect: function (chapterId) {
        points.load(chapterId);
        directions.load(null);
        tags.load(null, null);
      }
    });
    return wrap;
  }

  window.DcLinkage = { mount: mount };
})();