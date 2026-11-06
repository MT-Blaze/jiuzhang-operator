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
      sourceToPatch: deps.sourceToPatch,
      hostCall: deps.hostCall,
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
      // 强保存是跨帧握手，归裁判台自己（ui_dup_judge.js:flushSource）；
      // 两帧各有一份 compare 实例，面板这头调不到画布那头的 textarea。
    });
    // 强保存握手（画布半边）：辅助栏点裁决时先来问一句，画布把 textarea 当下值落盘再回执。
    function onSaveRequest(payload) {
      var requestId = String((payload && payload.requestId) || "");
      function reply(ok, message) {
        deps.publish("editor.dup_compare", {
          pluginId: deps.coreState.PLUGIN_ID, from: "canvas", phase: "save_done",
          requestId: requestId, ok: ok, message: message || ""
        });
      }
      Promise.resolve(compare.saveNow()).then(function (result) {
        reply(!result || result.ok !== false, (result && result.message) || "");
      }, function (error) {
        reply(false, "源码没存回池：" + ((error && error.message) || "未知原因"));
      });
    }

    // 协议层要的五个口一次交齐：开/换/关/画布退/强保存两半。
    var protocol = {
      openDupCompare: compare.open,
      updateDupCompare: compare.update,
      closeDupCompare: compare.close,
      onDupCompareClosed: judge.onCanvasClosed,
      onDupSaveRequest: onSaveRequest,
      onDupSaveDone: judge.onSaveDone,
    };

    return { compare: compare, judge: judge, protocol: protocol };
  }

  global.JzoEditorDupWiring = { create: create };
})(window);
