/**
 * ui_dup_wiring.js —— 查重三栏两半的装配线（军令·查重三栏）。
 *
 * 画布半边（ui_dup_compare.js）与辅助栏裁判台（ui_dup_judge.js）都只经 deps 取依赖；
 * 装配搬出 plugin.js，主文件才守得住单文件 800 行的舱位线。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var compare = global.JzoEditorDupCompare.create({
      dom: deps.dom,
      coreState: deps.coreState,
      el: deps.el,
      renderDoc: deps.renderDoc,
      buildExamSource: deps.buildExamSource,
      setMode: function () { return deps.uiBatches().setMode.apply(deps.uiBatches(), arguments); },
      renderAll: function () { return deps.uiColumns().renderAll.apply(deps.uiColumns(), arguments); },
      publish: deps.publish,
      dockWarn: deps.dockWarn,
      errorDetail: deps.errorDetail,
    });
    var judge = global.JzoEditorDupJudge.create({
      dom: deps.dom,
      coreState: deps.coreState,
      el: deps.el,
      hostCall: deps.hostCall,
      publish: deps.publish,
      panelSay: deps.panelSay,
      dock: deps.dock,
      dockWarn: deps.dockWarn,
      errorDetail: deps.errorDetail,
      openModal: deps.openModal,
      closeModal: deps.closeModal,
      poolPanel: deps.poolPanel,
    });
    return { compare: compare, judge: judge };
  }

  global.JzoEditorDupWiring = { create: create };
})(window);
