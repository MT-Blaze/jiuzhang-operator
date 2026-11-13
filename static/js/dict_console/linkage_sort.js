/**
 * 知识点与考向树 · 排序芯片与落库（2026-11-13）：
 * 行尾排序号点一下变数字框，Enter / 失焦立即落库并重排该父节点下的子节点。
 * 章节 / 册次 / 版本直接 PUT 自身 sort_order；知识点走桥表 order 接口提交完整清单。
 * 整块下架：删本文件、linkage_tree.js 的 DcLinkageSort 调用与 HTML 引用行即可。
 */
(function () {
  "use strict";

  function chip(value, label, apply) {
    return window.DcTreeAdd.sortChip({
      value: value, label: label, className: "dc-sort dkl-sort", apply: apply
    });
  }

  /** 字典行直接改自身 sort_order，成功后重载当前树。 */
  function save(url, row, value, refresh) {
    return window.DcClient.writeJson(url + "/" + row.id, { sort_order: value }, "PUT")
      .then(function (saved) {
        row.sort_order = saved.sort_order;
        return refresh();
      });
  }

  /** 知识点顺序住在桥表：把该点移到目标位置，提交完整 id 清单后重画。 */
  function reorderPoints(chapterId, pointId, siblings, value, refresh) {
    var ids = (siblings || []).map(function (item) { return item.id; })
      .filter(function (id) { return id !== pointId; });
    var index = Math.max(0, Math.min(ids.length, value));
    ids.splice(index, 0, pointId);
    return window.DcClient.writeJson(
      "/api/bank/engine/linkage/chapters/" + chapterId + "/points/order",
      { point_ids: ids }, "PUT"
    ).then(refresh);
  }

  window.DcLinkageSort = { chip: chip, save: save, reorderPoints: reorderPoints };
})();
