(function () {
  "use strict";

  async function clearStudyData(options = {}) {
    const confirmed = window.confirm("确定清除全部学习记录和离线缓存？此操作不能撤销。");
    if (!confirmed) return false;

    for (const storage of [localStorage, sessionStorage]) {
      const keys = [];
      for (let index = 0; index < storage.length; index += 1) {
        const key = storage.key(index);
        if (key?.startsWith("shaoyang-")) keys.push(key);
      }
      keys.forEach((key) => storage.removeItem(key));
    }

    if ("caches" in window) {
      const names = await caches.keys();
      await Promise.all(names.filter((name) => name.startsWith("shaoyang-quiz-")).map((name) => caches.delete(name)));
    }

    if ("serviceWorker" in navigator) {
      const registration = await navigator.serviceWorker.getRegistration("./");
      await registration?.unregister();
    }

    const target = options.redirect || "./index.html";
    const separator = target.includes("?") ? "&" : "?";
    location.replace(`${target}${separator}reset=${Date.now()}`);
    return true;
  }

  window.clearStudyData = clearStudyData;
})();
