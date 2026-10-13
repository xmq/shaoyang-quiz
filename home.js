(function () {
  "use strict";

  const SUBJECT_ALIASES = {
    "Office软件操作": "办公软件",
    "大学计算机基础与新技术": "计算机基础",
    "C与Python程序设计": "编程语言",
    "多媒体技术": "多媒体",
    "数据结构与算法": "算法与数据结构",
    "操作系统原理": "操作系统",
    "数据库技术": "数据库",
  };
  const COURSE_GROUPS = {
    "计算机专业主干": ["计算机组成原理", "操作系统原理", "数据结构与算法", "计算机网络", "数据库技术", "C与Python程序设计", "软件工程"],
    "计算机应用与安全": ["信息安全", "Office软件操作", "大学计算机基础与新技术", "多媒体技术"],
    "电子通信方向扩展": ["数字电子技术", "电路分析与电工技术", "模拟电子技术", "通信原理与高频电子线路", "信号与系统"],
  };
  const COURSES = Object.values(COURSE_GROUPS).flat();

  function normalizeCourseName(name) {
    return name === "编程语言" ? "C与Python程序设计" : name;
  }

  function lastLearning() {
    try {
      const value = JSON.parse(localStorage.getItem("shaoyang-last-learning") || "null");
      if (!value || !COURSES.includes(normalizeCourseName(value.course))) return null;
      return {...value, course: normalizeCourseName(value.course)};
    } catch {
      return null;
    }
  }

  function selectedCourseName() {
    try {
      const selected = normalizeCourseName(localStorage.getItem("shaoyang-selected-course-v1"));
      if (COURSES.includes(selected)) return selected;
      return lastLearning()?.course || "";
    } catch {
      return "";
    }
  }

  function updateContinueLink() {
    const link = document.getElementById("home-continue");
    const last = lastLearning();
    if (!last) {
      link.classList.add("hidden");
      return;
    }
    const moduleName = last.module === "color-notes" ? "重点与易错" : "讲义";
    const path = last.module === "color-notes" ? "color-notes.html" : "notes.html";
    const route = new URLSearchParams({course: last.course, chapter: String(last.chapter || 1)});
    if (last.module === "color-notes" && last.card) route.set("card", String(last.card));
    link.href = `./${path}#${route.toString()}`;
    link.textContent = `继续上次学习：${last.course} · 第${last.chapter || 1}章 · ${moduleName} →`;
    link.classList.remove("hidden");
  }

  function updateCourseLinks(courseName) {
    const actions = document.getElementById("home-module-actions");
    if (!courseName) {
      actions.classList.add("hidden");
      return;
    }
    const subject = SUBJECT_ALIASES[courseName] || courseName;
    const hash = `#course=${encodeURIComponent(courseName)}`;
    document.getElementById("home-notes-link").href = `./notes.html${hash}`;
    document.getElementById("home-recall-link").href = `./color-notes.html${hash}`;
    document.getElementById("home-quiz-link").href = `./quiz.html?subject=${encodeURIComponent(subject)}&mode=home`;
    actions.classList.remove("hidden");
  }

  function buildCourseMenu() {
    const select = document.getElementById("home-course-select");
    select.insertAdjacentHTML("beforeend", Object.entries(COURSE_GROUPS).map(([group, courses]) => `<optgroup label="${group}">${courses.map((course) => `<option value="${course}">${course}</option>`).join("")}</optgroup>`).join(""));
    select.value = selectedCourseName();
    updateCourseLinks(select.value);
    select.addEventListener("change", () => {
      try {
        if (select.value) localStorage.setItem("shaoyang-selected-course-v1", select.value);
        else localStorage.removeItem("shaoyang-selected-course-v1");
      } catch {}
      updateCourseLinks(select.value);
    });
  }

  function registerServiceWorker() {
    if (!("serviceWorker" in navigator)) return;
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("./sw.js", {updateViaCache: "none"}).catch(() => {});
    });
  }

  buildCourseMenu();
  updateContinueLink();
  registerServiceWorker();
})();
