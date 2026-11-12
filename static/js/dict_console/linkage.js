/**
 * 知识点与考向装配：面板交给折叠树，树里每层自己懒加载下游。
 * 挂在教研属性分类页签顶部（DcTabs/ctx.openCategory 机制不变）。
 * 整块下架：删本目录 linkage*.js + CSS + panels.js 的 DcLinkage.mount 调用。
 */
(function () {
  "use strict";

  function mount(panel, ctx) {
    return window.DcLinkTree.mount(panel, ctx);
  }

  window.DcLinkage = { mount: mount };
})();