(function () {
  "use strict";

  const SUBJECT_ALIASES = {
    "Office软件操作": "办公软件",
    "信息技术与教学论": "教学论",
    "多媒体技术": "多媒体",
    "数据结构与算法": "算法与数据结构",
    "操作系统原理": "操作系统",
    "数据库技术": "数据库",
  };
  const COURSES = [
    "Office软件操作", "信息技术与教学论", "多媒体技术", "编程语言", "数据结构与算法",
    "计算机组成原理", "操作系统原理", "数据库技术", "计算机网络", "软件工程", "信息安全",
    "电路分析与电工技术", "模拟电子技术", "数字电子技术", "通信原理与高频电子线路", "信号与系统",
  ];

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
    select.insertAdjacentHTML("beforeend", COURSES.map((course) => `<option value="${course}">${course}</option>`).join(""));
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
