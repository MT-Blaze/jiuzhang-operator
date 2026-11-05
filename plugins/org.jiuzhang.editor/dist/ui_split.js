/**
 * ui_split.js —— 框选切题：左栏原卷上框出一块，立刻生成一道待审新题。
 *
 * 无文本层时底座只给整卷页面图，一页上有几道题只有老师看得见；
 * 这里不猜题数、不编题干，只把框选的像素挂成一道新待审题（``p_`` 开头），
 * 排在右栏最上面，老师接着在中间栏录入。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var state = deps.coreState.state;
    var buildExamSource = deps.buildExamSource;
    var dock = deps.dock;
    var dockWarn = deps.dockWarn;
    var errorDetail = deps.errorDetail;
    var hostCall = deps.hostCall;
    var jumpTo = deps.jumpTo;
    var makeItem = deps.makeItem;
    var refreshBatches = deps.refreshBatches;
    var renderAll = deps.renderAll;

    function splitAssetId() {
      return "img_split_" + Math.random().toString(36).slice(2, 10);
    }

    /** 新题的开场白：只说明从哪一页框出来的，题干一个字都不编。 */
    function placeholderDoc(pageNo, assetId) {
      return {
        schema_version: "2.0",
        type: "solution",
        stem: "（框选切题：已从原卷第 " + pageNo + " 页框出，请在此录入题干与答案）",
        difficulty: "L2",
        images: [{ id: assetId, role: "stem", uri: "/static/uploads/" + assetId + ".png" }]
      };
    }

    /** 切出来的图落进当前批次的中转站，新题紧跟在源题后面。 */
    function splitFromCrop(item, dataUrl, info) {
      if (!item || !item.batchId) {
        dockWarn("切分新题需要先在一个批次里：当前题不在中转站。");
        return Promise.resolve(null);
      }
      if (!dataUrl) {
        dockWarn("框选区域没有截到像素，新题没建。");
        return Promise.resolve(null);
      }
      var pageNo = Number((info && info.page) || (item.pageImage && item.pageImage.page) || 1) || 1;
      var assetId = splitAssetId();
      var doc = placeholderDoc(pageNo, assetId);
      var payload = {
        batch_id: item.batchId,
        origin: "editor.split",
        // 新题置顶：老师刚框出来的这一道要立刻出现在右栏第一条。
        position: "top",
        questions: [{
          question: doc,
          assets: [{ id: assetId, data_url: dataUrl }],
          page_no: pageNo
        }]
      };
      return hostCall("pending.save_draft", payload).then(function (result) {
        var savedId = String((result && result.saved_ids && result.saved_ids[0]) || "");
        var saved = result && result.saved_assets && result.saved_assets[0];
        var asset = saved && saved.assets && saved.assets[0];
        if (asset && asset.uri) doc.images[0].uri = asset.uri;
        if (savedId) doc.id = savedId;
        var at = 0;
        var created = makeItem(doc, buildExamSource(doc), at);
        created.pendingId = savedId;
        created.batchId = item.batchId;
        created.pageImage = item.pageImage
          ? { uri: item.pageImage.uri, page: pageNo }
          : null;
        // 置顶：框出来一道就在最上面一道，老师不用往下翻着找刚切的那题。
        state.items.splice(at, 0, created);
        state.active = at;
        renderAll();
        jumpTo(at);
        refreshBatches();
        focusStem(at);
        dock("已从原卷第 " + pageNo + " 页框出新待审题（池子编号 "
          + (savedId || "—") + "），请在中间栏录入题干与答案。");
        return created;
      }, function (error) {
        var message = (error && error.message) || "未知原因";
        dockWarn("切分新题没成功：" + message, errorDetail(error));
        return null;
      });
    }

    /** 新题建好后把光标送进题干：源码视图进整段源码，卡片视图进题干框。 */
    function focusStem(index) {
      window.requestAnimationFrame(function () {
        var node = document.querySelector(
          '.ed-src-area[data-index="' + index + '"]')
          || document.querySelector(
            '.ed-box-textarea[data-index="' + index + '"][data-field="stem"]');
        if (!node) return;
        node.focus();
        if (node.tagName === "TEXTAREA") {
          try { node.setSelectionRange(0, 0); } catch (error) { /* 光标落点不影响保存 */ }
        }
      });
    }

    return {
      focusStem: focusStem,
      placeholderDoc: placeholderDoc,
      splitFromCrop: splitFromCrop,
    };
  }

  global.JzoEditorSplit = { create: create };
})(window);
