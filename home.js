(function () {
  "use strict";

  const RAW_QUESTION_INDEX = Array.isArray(window.HOME_QUESTION_INDEX)
    ? window.HOME_QUESTION_INDEX
    : Array.isArray(window.QUESTIONS)
      ? window.QUESTIONS.map(({id, subject, type, answer}) => ({id, subject, type, answer}))
      : [];
  const QUESTION_INDEX = RAW_QUESTION_INDEX.filter((question) => !/^(?:uc|ue)-/i.test(String(question.id || "")));
  const STORE_KEYS = ["shaoyang-quiz-v5", "shaoyang-quiz-v4", "shaoyang-quiz-v3", "shaoyang-quiz-v2", "shaoyang-quiz-v1"];
  const SUBJECT_ALIASES = {
    "Office软件操作": "办公软件",
    "信息技术与教学论": "教学论",
    "多媒体技术": "多媒体",
    "数据结构与算法": "算法与数据结构",
    "操作系统原理": "操作系统",
    "数据库技术": "数据库",
  };
  const COURSES = [
    {name: "Office软件操作", group: "信息技术应用", icon: "O"},
    {name: "信息技术与教学论", group: "信息技术应用", icon: "教"},
    {name: "多媒体技术", group: "信息技术应用", icon: "媒"},
    {name: "编程语言", group: "计算机专业", icon: "码"},
    {name: "数据结构与算法", group: "计算机专业", icon: "算"},
    {name: "计算机组成原理", group: "计算机专业", icon: "组"},
    {name: "操作系统原理", group: "计算机专业", icon: "OS"},
    {name: "数据库技术", group: "计算机专业", icon: "库"},
    {name: "计算机网络", group: "计算机专业", icon: "网"},
    {name: "软件工程", group: "计算机专业", icon: "软"},
    {name: "信息安全", group: "计算机专业", icon: "安"},
    {name: "电路分析与电工技术", group: "电子与通信", icon: "电"},
    {name: "模拟电子技术", group: "电子与通信", icon: "模"},
    {name: "数字电子技术", group: "电子与通信", icon: "数"},
    {name: "通信原理与高频电子线路", group: "电子与通信", icon: "通"},
  ];

  function readProgress() {
    for (const key of STORE_KEYS) {
      try {
        const parsed = JSON.parse(localStorage.getItem(key) || "null");
        if (parsed && typeof parsed === "object") {
          return parsed.state && typeof parsed.state === "object" ? parsed.state : parsed;
        }
      } catch {}
    }
    return {};
  }

  function normalizeAnswer(value) {
    return String(value || "")
      .replace(/\s+/g, "")
      .toLowerCase()
      .replace(/[，、；,;]/g, "|")
      .replace(/[(（].*?[)）]/g, "");
  }

  function isCorrect(question, given) {
    if (question.type === "简答") return given === "掌握";
    if (question.type === "多选") {
      return [...String(given || "")].sort().join("") === [...String(question.answer || "")].sort().join("");
    }
    if (question.type === "填空") return normalizeAnswer(given) === normalizeAnswer(question.answer);
    return given === question.answer;
  }

  function courseStats(progress, subject) {
    const questions = QUESTION_INDEX.filter((question) => question.subject === subject);
    const done = progress.done || {};
    const completed = questions.filter((question) => Object.prototype.hasOwnProperty.call(done, question.id));
    const correct = completed.filter((question) => isCorrect(question, done[question.id])).length;
    const wrong = questions.filter((question) => (progress.wrong || {})[question.id]).length;
    return {
      total: questions.length,
      done: completed.length,
      correct,
      wrong,
      rate: completed.length ? Math.round(correct * 100 / completed.length) : null,
    };
  }

  function buildCourseGrid(progress) {
    const root = document.getElementById("home-course-grid");
    if (!root) return;
    const groups = [
      {key: "信息技术应用", label: "信息技术应用"},
      {key: "计算机专业", label: "计算机专业"},
      {key: "电子与通信", label: "电子与通信"},
    ];
    root.innerHTML = groups.map((group, groupIndex) => {
      const cards = COURSES.filter((course) => course.group === group.key).map((course) => {
        const subject = SUBJECT_ALIASES[course.name] || course.name;
        const stats = courseStats(progress, subject);
        const progressText = stats.done
          ? `已做 ${stats.done}/${stats.total}${stats.rate === null ? "" : ` · ${stats.rate}%`}${stats.wrong ? ` · 错题 ${stats.wrong}` : ""}`
          : `${stats.total || "—"} 道配套题`;
        const noteHash = `#course=${encodeURIComponent(course.name)}`;
        return `<a class="home-course-card" href="./notes.html${noteHash}" aria-label="进入${course.name}讲义">
          <div class="home-course-title"><span aria-hidden="true">${course.icon}</span><div><strong>${course.name}</strong><small>${progressText}</small></div><b class="course-card-arrow" aria-hidden="true">→</b></div>
        </a>`;
      }).join("");
      return `<section class="home-course-group" data-course-group="${group.key}" aria-labelledby="course-group-${groupIndex}">
        <h3 id="course-group-${groupIndex}">${group.label}</h3>
        <div>${cards}</div>
      </section>`;
    }).join("");
  }

  function bindCourseFilters() {
    const buttons = [...document.querySelectorAll("[data-course-filter]")];
    const groups = [...document.querySelectorAll("[data-course-group]")];
    const grid = document.getElementById("home-course-grid");
    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        const filter = button.dataset.courseFilter;
        buttons.forEach((item) => {
          const active = item === button;
          item.setAttribute("aria-selected", String(active));
        });
        groups.forEach((group) => {
          group.hidden = filter !== "all" && group.dataset.courseGroup !== filter;
        });
        if (grid) grid.dataset.activeFilter = filter;
      });
    });
  }

  function registerServiceWorker() {
    if (!("serviceWorker" in navigator)) return;
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("./sw.js", {updateViaCache: "none"}).catch(() => {});
    });
  }

  const progress = readProgress();
  buildCourseGrid(progress);
  bindCourseFilters();
  registerServiceWorker();
})();
