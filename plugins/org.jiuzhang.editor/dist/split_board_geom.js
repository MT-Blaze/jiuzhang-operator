/**
 * split_board_geom.js —— 悬浮切题画板的「整条纸带」坐标换算。
 *
 * 画板里所有页面接成一条纸带，框只认纸带坐标（页面按同一显示宽度缩放后的
 * 像素），不再受单页容器约束；落到存储层时再按页界线机械拆成每页一块。
 * 这一层只算数、不碰 DOM，独立可拆；拆掉它切题画板就退回单页框选。
 */
(function (global) {
  "use strict";

  function create() {
    function clamp(value, min, max) {
      if (max < min) return min;
      return Math.min(max, Math.max(min, value));
    }

    /** 每页在纸带里的基准位置：显示宽度统一为 baseWidth，高度按原图比例。 */
    function layout(pages, baseWidth) {
      var rows = [];
      var top = 0;
      for (var index = 0; index < pages.length; index += 1) {
        var width = Math.max(1, Number(pages[index].width) || 1);
        var height = Math.max(1, Number(pages[index].height) || 1);
        var rowHeight = Math.max(1, baseWidth * height / width);
        rows.push({ top: top, height: rowHeight });
        top += rowHeight;
      }
      return rows;
    }

    function stripHeight(rows) {
      var total = 0;
      for (var index = 0; index < rows.length; index += 1) total += rows[index].height;
      return total;
    }

    /** 鼠标位置 → 纸带基准坐标（与缩放无关）。 */
    function point(rect, scale, clientX, clientY, baseWidth, totalHeight) {
      var safeScale = Number(scale) > 0 ? Number(scale) : 1;
      if (!rect || !(rect.width > 0)) return null;
      return {
        x: clamp((clientX - rect.left) / safeScale, 0, baseWidth),
        y: clamp((clientY - rect.top) / safeScale, 0, Math.max(0, totalHeight))
      };
    }

    function rectBetween(start, end) {
      return {
        x: Math.min(start.x, end.x),
        y: Math.min(start.y, end.y),
        w: Math.abs(end.x - start.x),
        h: Math.abs(end.y - start.y)
      };
    }

    function clampRect(rect, baseWidth, totalHeight) {
      var width = Math.max(0, Math.min(rect.w, baseWidth));
      var height = Math.max(0, Math.min(rect.h, totalHeight));
      return {
        x: clamp(rect.x, 0, Math.max(0, baseWidth - width)),
        y: clamp(rect.y, 0, Math.max(0, totalHeight - height)),
        w: width,
        h: height
      };
    }

    /** 单页原始像素框 → 纸带基准矩形。 */
    function rectOfRegion(pageIndex, region, pages, rows, baseWidth) {
      var page = pages[pageIndex];
      if (!page || !rows[pageIndex]) return null;
      var row = rows[pageIndex];
      return {
        x: (Number(region.x) || 0) / page.width * baseWidth,
        y: row.top + (Number(region.y) || 0) / page.height * row.height,
        w: (Number(region.w) || 0) / page.width * baseWidth,
        h: (Number(region.h) || 0) / page.height * row.height
      };
    }

    /** 纸带矩形 → 按页剪好的原始像素块；跨页只拆坐标，不改框的形状。 */
    function piecesOf(rect, pages, rows, baseWidth) {
      var pieces = [];
      var left = Math.max(0, rect.x);
      var right = Math.min(baseWidth, rect.x + rect.w);
      if (right - left <= 0.01) return pieces;
      for (var index = 0; index < pages.length; index += 1) {
        var row = rows[index];
        var top = Math.max(rect.y, row.top);
        var bottom = Math.min(rect.y + rect.h, row.top + row.height);
        if (bottom - top <= 0.01) continue;
        var page = pages[index];
        pieces.push({
          pageIndex: index,
          pageNo: page.pageNo,
          region: {
            x: (left / baseWidth) * page.width,
            y: ((top - row.top) / row.height) * page.height,
            w: ((right - left) / baseWidth) * page.width,
            h: ((bottom - top) / row.height) * page.height
          }
        });
      }
      return pieces;
    }

    /** 多块原始像素框 → 一个纸带矩形（重开画板时把同一题的跨页块还原成整框）。 */
    function rectOfPieces(pieces, pages, rows, baseWidth) {
      var box = null;
      for (var index = 0; index < pieces.length; index += 1) {
        var each = rectOfRegion(pieces[index].pageIndex, pieces[index].region,
          pages, rows, baseWidth);
        if (!each) continue;
        if (!box) {
          box = { x: each.x, y: each.y, w: each.w, h: each.h };
        } else {
          var left = Math.min(box.x, each.x);
          var top = Math.min(box.y, each.y);
          var right = Math.max(box.x + box.w, each.x + each.w);
          var bottom = Math.max(box.y + box.h, each.y + each.h);
          box = { x: left, y: top, w: right - left, h: bottom - top };
        }
      }
      return box;
    }

    function pageIndexOf(rect, rows) {
      var middle = rect.y + Math.min(rect.h / 2, 1);
      for (var index = 0; index < rows.length; index += 1) {
        if (middle < rows[index].top + rows[index].height) return index;
      }
      return Math.max(0, rows.length - 1);
    }

    return {
      clamp: clamp,
      layout: layout,
      piecesOf: piecesOf,
      pageIndexOf: pageIndexOf,
      point: point,
      rectBetween: rectBetween,
      rectOfPieces: rectOfPieces,
      rectOfRegion: rectOfRegion,
      stripHeight: stripHeight,
      clampRect: clampRect
    };
  }

  global.JzoEditorSplitBoardGeom = { create: create };
})(window);
