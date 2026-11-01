/**
 * 底座微内核之二：页签模型（从 stage.js 拆出）。
 *
 * 只算账、不碰 DOM：优先级、排位、查找、存活页、最近使用时间与 LRU 的牺牲者。
 * 怎么画页签、怎么摘 iframe 仍归 stage.js。
 */
(function (global) {
  "use strict";

  /** 舞台优先级（stage.priority）：钳在 -100…100，缺省 0。 */
  function priorityOf(tab) {
    var stage = tab.plugin && tab.plugin.stage;
    var value = stage && typeof stage.priority === "number" ? stage.priority : 0;
    return Math.max(-100, Math.min(100, value));
  }

  /** 同排插件页签按优先级从高到低排，同优先级按打开先后。原生页签不参与抢位。 */
  function sortPluginTabs(list) {
    return list.slice().sort(function (a, b) {
      var delta = priorityOf(b) - priorityOf(a);
      return delta !== 0 ? delta : a.order - b.order;
    });
  }

  function find(list, key) {
    for (var i = 0; i < list.length; i += 1) {
      if (list[i].key === key) return list[i];
    }
    return null;
  }

  function liveFrames(list) {
    return list.filter(function (tab) { return tab.kind === "plugin" && tab.state === "live"; });
  }

  function touch(tab) {
    tab.lastUsed = Date.now();
  }

  /** LRU 的牺牲者：最久没被碰过、且不是当前页的那一个；全是活动页就返回 null。 */
  function lruVictim(list, activeKey) {
    var oldest = null;
    list.forEach(function (tab) {
      if (tab.key === activeKey) return;
      if (!oldest || tab.lastUsed < oldest.lastUsed) oldest = tab;
    });
    return oldest;
  }

  global.JzoCoreTabs = {
    priorityOf: priorityOf,
    sortPluginTabs: sortPluginTabs,
    find: find,
    liveFrames: liveFrames,
    touch: touch,
    lruVictim: lruVictim
  };
})(window);
