/**
 * ui_split.js —— 扫描卷的手动切题：左栏框出一块，就地生成一条待审占位题。
 *
 * 无文本层时底座只给「原卷页入口」，一页上有几道题只有老师看得见；
 * 这里不猜题数、不编题干，只把框选的像素挂成一道新待审题，
 * 题干留明写的占位，老师接着在中间栏录入。
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

    /** 新题占位：只说明从哪一页切出来的，题干一个字都不编。 */
    function placeholderDoc(pageNo, assetId) {
      return {
        schema_version: "2.0",
        type: "solution",
        stem: "（待录入题干：已从原卷第 " + pageNo + " 页框选，请在中间栏补录题干与答案）",
        difficulty: "L2",
        tags: ["待识别"],
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
        var sourceIndex = state.items.indexOf(item);
        var at = sourceIndex < 0 ? state.items.length : sourceIndex + 1;
        // 同一页切出来的题按切题先后排在一起：新题跟在同页最后一条之后，
        // 否则连着切第二题时它会插到第一题前面，题序倒着长。
        var sourcePage = item.pageImage ? Number(item.pageImage.page) || 1 : 0;
        for (var index = at; index < state.items.length; index += 1) {
          var each = state.items[index];
          var eachPage = each.pageImage ? Number(each.pageImage.page) || 1 : 0;
          if (eachPage !== sourcePage) break;
          at = index + 1;
        }
        var created = makeItem(doc, buildExamSource(doc), at);
        created.pendingId = savedId;
        created.batchId = item.batchId;
        created.pageImage = item.pageImage
          ? { uri: item.pageImage.uri, page: pageNo }
          : null;
        state.items.splice(at, 0, created);
        state.active = at;
        renderAll();
        jumpTo(at);
        refreshBatches();
        focusStem(at);
        dock("已从原卷第 " + pageNo + " 页切出新待审题（池子编号 "
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
