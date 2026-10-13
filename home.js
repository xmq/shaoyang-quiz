(function () {
  "use strict";

  const QUESTION_INDEX = Array.isArray(window.HOME_QUESTION_INDEX) ? window.HOME_QUESTION_INDEX : [];
  const STORE_KEYS = ["shaoyang-quiz-v5", "shaoyang-quiz-v4", "shaoyang-quiz-v3", "shaoyang-quiz-v2", "shaoyang-quiz-v1"];
  const SUBJECT_ALIASES = {
    "Office软件操作": "办公软件",
    "大学计算机基础与新技术": "计算机基础",
    "C与Python程序设计": "编程语言",
    "多媒体技术": "多媒体",
    "数据结构与算法": "算法与数据结构",
    "操作系统原理": "操作系统",
    "数据库技术": "数据库",
  };
  const COURSES = [
    {name: "计算机组成原理", group: "计算机专业主干", icon: "组", topics: 7},
    {name: "操作系统原理", group: "计算机专业主干", icon: "OS", topics: 8},
    {name: "数据结构与算法", group: "计算机专业主干", icon: "算", topics: 8},
    {name: "计算机网络", group: "计算机专业主干", icon: "网", topics: 26},
    {name: "数据库技术", group: "计算机专业主干", icon: "库", topics: 9},
    {name: "C与Python程序设计", group: "计算机专业主干", icon: "码", topics: 11},
    {name: "软件工程", group: "计算机专业主干", icon: "软", topics: 8},
    {name: "信息安全", group: "计算机应用与安全", icon: "安", topics: 8},
    {name: "Office软件操作", group: "计算机应用与安全", icon: "O", topics: 7},
    {name: "大学计算机基础与新技术", group: "计算机应用与安全", icon: "基", topics: 10},
    {name: "多媒体技术", group: "计算机应用与安全", icon: "媒", topics: 7},
    {name: "数字电子技术", group: "电子通信方向扩展", icon: "数", topics: 7},
    {name: "电路分析与电工技术", group: "电子通信方向扩展", icon: "电", topics: 9},
    {name: "模拟电子技术", group: "电子通信方向扩展", icon: "模", topics: 8},
    {name: "通信原理与高频电子线路", group: "电子通信方向扩展", icon: "通", topics: 9},
    {name: "信号与系统", group: "电子通信方向扩展", icon: "信", topics: 7},
  ];
  const GROUPS = ["计算机专业主干", "计算机应用与安全", "电子通信方向扩展"];

  function normalizeCourseName(name) {
    return name === "编程语言" ? "C与Python程序设计" : name;
  }

  function readProgress() {
    for (const key of STORE_KEYS) {
      try {
        const parsed = JSON.parse(localStorage.getItem(key) || "null");
        if (parsed && typeof parsed === "object") return parsed.state && typeof parsed.state === "object" ? parsed.state : parsed;
      } catch {}
    }
    return {};
  }

  function lastLearning() {
    try {
      const value = JSON.parse(localStorage.getItem("shaoyang-last-learning") || "null");
      if (!value) return null;
      const course = normalizeCourseName(value.course);
      return COURSES.some((item) => item.name === course) ? {...value, course} : null;
    } catch {
      return null;
    }
  }

  function selectedCourseName() {
    try {
      const selected = normalizeCourseName(localStorage.getItem("shaoyang-selected-course-v1"));
      if (COURSES.some((course) => course.name === selected)) return selected;
      return lastLearning()?.course || "计算机网络";
    } catch {
      return "";
    }
  }

  function normalizeAnswer(value) {
    return String(value || "").replace(/\s+/g, "").toLowerCase().replace(/[，、；,;]/g, "|").replace(/[(（].*?[)）]/g, "");
  }

  function isCorrect(question, given) {
    if (question.type === "简答") return given === "掌握";
    if (question.type === "多选") return [...String(given || "")].sort().join("") === [...String(question.answer || "")].sort().join("");
    if (question.type === "填空") return normalizeAnswer(given) === normalizeAnswer(question.answer);
    return given === question.answer;
  }

  function courseStats(progress, courseName) {
    const subject = SUBJECT_ALIASES[courseName] || courseName;
    const questions = QUESTION_INDEX.filter((question) => question.subject === subject);
    const done = progress.done || {};
    const completed = questions.filter((question) => Object.prototype.hasOwnProperty.call(done, question.id));
    const correct = completed.filter((question) => isCorrect(question, done[question.id])).length;
    return {
      total: questions.length,
      done: completed.length,
      wrong: questions.filter((question) => (progress.wrong || {})[question.id]).length,
      rate: completed.length ? Math.round(correct * 100 / completed.length) : null,
    };
  }

  function updateCourseLinks(courseName, progress) {
    const actions = document.getElementById("home-module-actions");
    const status = document.getElementById("selected-course-status");
    if (!courseName) {
      actions.classList.add("hidden");
      status.textContent = "选课后可直接进入讲义、重点与易错或专项练习。";
      return;
    }
    const subject = SUBJECT_ALIASES[courseName] || courseName;
    const hash = `#course=${encodeURIComponent(courseName)}`;
    const stats = courseStats(progress, courseName);
    const course = COURSES.find((item) => item.name === courseName);
    const notesLink = document.getElementById("home-notes-link");
    notesLink.href = `./notes.html${hash}`;
    notesLink.innerHTML = "<strong>开始讲义</strong><small>进入 →</small>";
    document.getElementById("home-recall-link").href = `./color-notes.html${hash}`;
    document.getElementById("home-quiz-link").href = `./quiz.html?subject=${encodeURIComponent(subject)}&mode=home`;
    const last = lastLearning();
    if (last?.course === courseName) {
      const path = last.module === "color-notes" ? "color-notes.html" : "notes.html";
      const moduleName = last.module === "color-notes" ? "重点" : "讲义";
      const route = new URLSearchParams({course: last.course, chapter: String(last.chapter || 1)});
      if (last.module === "color-notes" && last.card) route.set("card", String(last.card));
      notesLink.href = `./${path}#${route.toString()}`;
      notesLink.innerHTML = `<strong>继续第${last.chapter || 1}章</strong><small>${moduleName} →</small>`;
    }
    status.textContent = stats.done
      ? `已完成 ${stats.done}/${stats.total} 题 · 正确率 ${stats.rate}%${stats.wrong ? ` · 错题 ${stats.wrong}` : ""}`
      : `${course?.topics || "—"} 个知识点 · ${stats.total || "—"} 道题`;
    actions.classList.remove("hidden");
  }

  function buildCourseMenu(progress) {
    const select = document.getElementById("home-course-select");
    select.insertAdjacentHTML("beforeend", GROUPS.map((group) => `<optgroup label="${group}">${COURSES.filter((course) => course.group === group).map((course) => `<option value="${course.name}">${course.name}</option>`).join("")}</optgroup>`).join(""));
    select.value = selectedCourseName();
    updateCourseLinks(select.value, progress);
    select.addEventListener("change", () => {
      try {
        if (select.value) localStorage.setItem("shaoyang-selected-course-v1", select.value);
        else localStorage.removeItem("shaoyang-selected-course-v1");
      } catch {}
      updateCourseLinks(select.value, progress);
    });
  }

  function buildCourseGrid(progress) {
    const root = document.getElementById("home-course-grid");
    root.innerHTML = GROUPS.map((group, groupIndex) => {
      const cards = COURSES.filter((course) => course.group === group).map((course) => {
        const stats = courseStats(progress, course.name);
        const noteHash = `#course=${encodeURIComponent(course.name)}`;
        const progressText = stats.done ? `已做 ${stats.done}/${stats.total} · ${stats.rate}%` : `${course.topics} 个知识点 · ${stats.total || "—"} 题`;
        const progressWidth = stats.total ? Math.min(100, Math.round(stats.done * 100 / stats.total)) : 0;
        return `<article class="home-course-card">
          <a class="home-course-main" href="./notes.html${noteHash}">
            <span class="home-course-icon" aria-hidden="true">${course.icon}</span>
            <span class="home-course-copy"><strong>${course.name}</strong><small>${progressText}</small><i><b style="width:${progressWidth}%"></b></i></span>
            <span class="course-card-arrow" aria-hidden="true">›</span>
          </a>
        </article>`;
      }).join("");
      return `<section class="home-course-group" data-course-group="${group}" aria-labelledby="course-group-${groupIndex}"><h3 id="course-group-${groupIndex}">${group}</h3><div>${cards}</div></section>`;
    }).join("");
  }

  function bindCourseFilters() {
    const buttons = [...document.querySelectorAll("[data-course-filter]")];
    const groups = [...document.querySelectorAll("[data-course-group]")];
    buttons.forEach((button) => button.addEventListener("click", () => {
      const filter = button.dataset.courseFilter;
      buttons.forEach((item) => item.setAttribute("aria-selected", String(item === button)));
      groups.forEach((group) => { group.hidden = filter !== "all" && group.dataset.courseGroup !== filter; });
      document.getElementById("home-course-grid").dataset.activeFilter = filter;
    }));
  }

  function registerServiceWorker() {
    if (!("serviceWorker" in navigator)) return;
    window.addEventListener("load", () => {
      const hadController = Boolean(navigator.serviceWorker.controller);
      let reloading = false;
      navigator.serviceWorker.addEventListener("controllerchange", () => {
        if (!hadController || reloading) return;
        reloading = true;
        location.reload();
      });
      navigator.serviceWorker.register("./sw.js", {updateViaCache: "none"}).then((registration) => {
        if (registration.waiting) registration.waiting.postMessage("SKIP_WAITING");
        registration.addEventListener("updatefound", () => {
          const worker = registration.installing;
          worker?.addEventListener("statechange", () => {
            if (worker.state === "installed" && navigator.serviceWorker.controller) worker.postMessage("SKIP_WAITING");
          });
        });
        registration.update().catch(() => {});
      }).catch(() => {});
    });
  }

  const progress = readProgress();
  buildCourseMenu(progress);
  buildCourseGrid(progress);
  bindCourseFilters();
  registerServiceWorker();
})();
