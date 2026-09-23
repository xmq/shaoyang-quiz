(function () {
  "use strict";

  const SUBJECT_ALIASES = {
    "Office软件操作": "办公软件",
    "多媒体技术": "多媒体",
    "数据结构与算法": "算法与数据结构",
    "操作系统原理": "操作系统",
    "数据库技术": "数据库",
  };
  const COURSE_GROUPS = {
    "计算机专业主干": ["计算机组成原理", "操作系统原理", "数据结构与算法", "计算机网络", "数据库技术", "编程语言", "软件工程"],
    "计算机应用与安全": ["信息安全", "Office软件操作", "多媒体技术"],
    "电子通信方向扩展": ["数字电子技术", "电路分析与电工技术", "模拟电子技术", "通信原理与高频电子线路", "信号与系统"],
  };
  const COURSES = Object.values(COURSE_GROUPS).flat();

  function selectedCourseName() {
    try {
      const selected = localStorage.getItem("shaoyang-selected-course-v1");
      if (COURSES.includes(selected)) return selected;
      const last = JSON.parse(localStorage.getItem("shaoyang-last-learning") || "null");
      return COURSES.includes(last?.course) ? last.course : "";
    } catch {
      return "";
    }
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
  registerServiceWorker();
})();
