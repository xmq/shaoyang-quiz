(function () {
  "use strict";

  const cardArea = document.getElementById("card-area");
  const expectedCount = Number(globalThis.SHAOYANG_BUILD?.questionCount || 0);

  function showStatus(title, detail, retry = false) {
    cardArea.innerHTML = `<section class="card empty quiz-load-status">
      <strong>${title}</strong>
      <p>${detail}</p>
      ${retry ? '<button type="button" class="primary-btn" id="quiz-load-retry">重新加载题库</button>' : ""}
    </section>`;
    document.getElementById("quiz-load-retry")?.addEventListener("click", () => start());
  }

  function loadScript(source, timeoutMs = 12000) {
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      const timer = window.setTimeout(() => {
        script.remove();
        reject(new Error(`${source} 加载超时`));
      }, timeoutMs);
      script.src = source;
      script.onload = () => {
        window.clearTimeout(timer);
        resolve();
      };
      script.onerror = () => {
        window.clearTimeout(timer);
        script.remove();
        reject(new Error(`${source} 下载失败`));
      };
      document.body.appendChild(script);
    });
  }

  async function loadQuestions() {
    for (let attempt = 0; attempt < 2; attempt += 1) {
      try {
        delete globalThis.QUESTIONS;
        const suffix = attempt ? `?retry=${Date.now()}` : "";
        await loadScript(`./questions.js${suffix}`);
        if (!Array.isArray(globalThis.QUESTIONS) || !globalThis.QUESTIONS.length) throw new Error("题库内容为空");
        if (expectedCount && globalThis.QUESTIONS.length !== expectedCount) {
          throw new Error(`题库版本不一致：应为${expectedCount}题，实际${globalThis.QUESTIONS.length}题`);
        }
        return;
      } catch (error) {
        if (attempt) throw error;
        showStatus("正在重新连接题库", "首次下载未完成，正在自动重试。", false);
        await new Promise((resolve) => window.setTimeout(resolve, 400));
      }
    }
  }

  async function start() {
    showStatus("正在加载题库", "首次打开或版本更新时可能需要几秒。", false);
    try {
      await loadQuestions();
      await loadScript("./question-media.js");
      await loadScript("./app.js");
    } catch (error) {
      console.error("刷题页启动失败", error);
      showStatus("题库加载失败", "请检查网络后重试；已离线使用过的版本会优先尝试本地缓存。", true);
    }
  }

  start();
})();
