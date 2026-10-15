(function () {
  "use strict";

  const QUESTION_INDEX = Array.isArray(window.HOME_QUESTION_INDEX) ? window.HOME_QUESTION_INDEX : [];
  const COURSE_INDEX = Array.isArray(window.HOME_COURSE_INDEX) ? window.HOME_COURSE_INDEX : [];
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
    {name: "计算机组成原理", group: "计算机专业主干", icon: "组"},
    {name: "操作系统原理", group: "计算机专业主干", icon: "OS"},
    {name: "数据结构与算法", group: "计算机专业主干", icon: "算"},
    {name: "计算机网络", group: "计算机专业主干", icon: "网"},
    {name: "数据库技术", group: "计算机专业主干", icon: "库"},
    {name: "C与Python程序设计", group: "计算机专业主干", icon: "码"},
    {name: "软件工程", group: "计算机专业主干", icon: "软"},
    {name: "信息安全", group: "计算机应用与安全", icon: "安"},
    {name: "Office软件操作", group: "计算机应用与安全", icon: "O"},
    {name: "大学计算机基础与新技术", group: "计算机应用与安全", icon: "基"},
    {name: "多媒体技术", group: "计算机应用与安全", icon: "媒"},
    {name: "数字电子技术", group: "电子通信方向扩展", icon: "数"},
    {name: "电路分析与电工技术", group: "电子通信方向扩展", icon: "电"},
    {name: "模拟电子技术", group: "电子通信方向扩展", icon: "模"},
    {name: "通信原理与高频电子线路", group: "电子通信方向扩展", icon: "通"},
    {name: "信号与系统", group: "电子通信方向扩展", icon: "信"},
  ];
  const GROUPS = ["计算机专业主干", "计算机应用与安全", "电子通信方向扩展"];

  function normalizeCourseName(name) {
    return name === "编程语言" ? "C与Python程序设计" : name;
  }

  function readProgress() {
    for (const key of STORE_KEYS) {
      try {
        const parsed = JSON.parse(localStorage.getItem(key) || "null");
        if (parsed && typeof parsed === "object") {
          const progress = parsed.state && typeof parsed.state === "object" ? parsed.state : parsed;
          QUESTION_INDEX.forEach((question) => {
            if (!question.answer_revision || parsed.questionRevisions?.[question.id] === question.answer_revision) return;
            ["done", "wrong", "streak", "history", "reviewMeta", "errorTags"].forEach((field) => {
              if (progress[field]) delete progress[field][question.id];
            });
          });
          return progress;
        }
      } catch {}
    }
    return {};
  }

  function readLectureProgress() {
    try {
      const value = JSON.parse(localStorage.getItem("shaoyang-reading-progress-v1") || "{}");
      return value && typeof value === "object" ? value : {};
    } catch {
      return {};
    }
  }

  function chapterNumberFromId(value) {
    const match = String(value || "").match(/(\d+)$/);
    return match ? Number(match[1]) : 0;
  }

  function resumeChapter(courseName, lectureProgress) {
    const chapterCount = COURSE_INDEX.find((item) => item.name === courseName)?.chapter_count || 0;
    const courseProgress = lectureProgress[courseName];
    let chapter = Number(courseProgress?.lastLectureChapter) || 0;
    const recent = lastLearning();
    if (!chapter && recent?.course === courseName) chapter = Number(recent.chapter) || 0;
    if (!chapter && Array.isArray(courseProgress?.lecture) && courseProgress.lecture.length) {
      chapter = chapterNumberFromId(courseProgress.lecture.at(-1));
    }
    return chapter > 0 && chapter <= chapterCount ? chapter : 1;
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

  function highlightedCourseName() {
    try {
      const selected = normalizeCourseName(localStorage.getItem("shaoyang-selected-course-v1"));
      if (COURSES.some((course) => course.name === selected)) return selected;
      return lastLearning()?.course || "";
    } catch {
      return "";
    }
  }

  function normalizeAnswer(value) {
    return String(value || "").normalize("NFKC").replace(/\s+/g, "").toLowerCase().replace(/[，、；,;]/g, "|").replace(/[−–]/g, "-");
  }

  function isCorrect(question, given) {
    if (question.type === "简答") return given === "掌握";
    if (question.type === "多选") return [...String(given || "")].sort().join("") === [...String(question.answer || "")].sort().join("");
    if (question.type === "填空") return [question.answer, ...(Array.isArray(question.accepted_answers) ? question.accepted_answers : [])].some((answer) => normalizeAnswer(given) === normalizeAnswer(answer));
    return given === question.answer;
  }

  function courseStats(progress, courseName) {
    const course = COURSE_INDEX.find((item) => item.name === courseName);
    const subjects = Array.isArray(course?.subjects) && course.subjects.length
      ? course.subjects
      : [course?.subject || SUBJECT_ALIASES[courseName] || courseName];
    const questions = QUESTION_INDEX.filter((question) => subjects.includes(question.subject));
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

  function updateMobileLinks(courseName, lectureProgress = readLectureProgress()) {
    const chapter = resumeChapter(courseName, lectureProgress);
    const hash = `#course=${encodeURIComponent(courseName)}&chapter=${chapter}`;
    document.getElementById("mobile-notes-link").href = `./notes.html${hash}`;
    document.getElementById("mobile-recall-link").href = `./color-notes.html${hash}`;
    document.getElementById("mobile-quiz-link").href = `./quiz.html?course=${encodeURIComponent(courseName)}&mode=home`;
  }

  function courseIcon(name) {
    if (name.includes("网络")) return "network";
    if (name.includes("数据库")) return "database";
    if (name.includes("Office")) return "office";
    if (name.includes("程序") || name.includes("软件")) return "code";
    if (name.includes("安全")) return "shield";
    if (name.includes("多媒体")) return "media";
    if (name.includes("信号")) return "wave";
    if (name.includes("通信")) return "signal";
    if (name.includes("电子") || name.includes("电路")) return "chip";
    if (name.includes("数据结构")) return "layers";
    return "cpu";
  }

  function buildCourseGrid(progress, lectureProgress) {
    const root = document.getElementById("home-course-grid");
    const highlighted = highlightedCourseName();
    root.innerHTML = GROUPS.map((group, groupIndex) => {
      const cards = COURSES.filter((course) => course.group === group).map((course) => {
        const stats = courseStats(progress, course.name);
        const chapterCount = COURSE_INDEX.find((item) => item.name === course.name)?.chapter_count || 0;
        const completedCount = new Set(lectureProgress[course.name]?.completed || []).size;
        const resumeAt = resumeChapter(course.name, lectureProgress);
        const noteHash = `#course=${encodeURIComponent(course.name)}&chapter=${resumeAt}`;
        const isCurrent = course.name === highlighted;
        const progressParts = [];
        if (completedCount) progressParts.push(`讲义 ${completedCount}/${chapterCount} 章`);
        if (stats.done) progressParts.push(`做题 ${stats.done} · ${stats.rate}%`);
        const progressText = progressParts.join(" · ") || "未开始";
        const progressWidth = completedCount && chapterCount
          ? Math.min(100, Math.round(completedCount * 100 / chapterCount))
          : stats.total ? Math.min(100, Math.round(stats.done * 100 / stats.total)) : 0;
        return `<article class="home-course-card${isCurrent ? " is-current" : ""}">
          <a class="home-course-main" href="./notes.html${noteHash}" data-course-name="${course.name}">
            <span class="home-course-icon" aria-hidden="true"><svg class="ui-icon"><use href="./ui-icons.svg#${courseIcon(course.name)}"></use></svg></span>
            <span class="home-course-copy"><strong>${course.name}${isCurrent ? '<em>最近</em>' : ""}</strong><small>${progressText}</small>${completedCount || stats.done ? `<i><b style="width:${progressWidth}%"></b></i>` : ""}</span>
            <span class="course-card-arrow" aria-hidden="true"><svg class="ui-icon"><use href="./ui-icons.svg#arrow-right"></use></svg></span>
          </a>
        </article>`;
      }).join("");
      return `<section class="home-course-group" data-course-group="${group}" aria-labelledby="course-group-${groupIndex}"><h3 id="course-group-${groupIndex}">${group}</h3><div>${cards}</div></section>`;
    }).join("");
  }

  function bindCourseLinks() {
    document.querySelectorAll("[data-course-name]").forEach((link) => {
      link.addEventListener("click", (event) => {
        event.preventDefault();
        const courseName = link.dataset.courseName;
        try {
          localStorage.setItem("shaoyang-selected-course-v1", courseName);
        } catch {}
        updateMobileLinks(courseName);
        document.querySelectorAll(".home-course-card").forEach((card) => {
          card.classList.toggle("is-current", card.contains(link));
        });
        location.assign(link.href);
      });
    });
  }

  function applyCourseFilter(filter) {
    const buttons = [...document.querySelectorAll("[data-course-filter]")];
    const groups = [...document.querySelectorAll("[data-course-group]")];
    buttons.forEach((item) => item.setAttribute("aria-selected", String(item.dataset.courseFilter === filter)));
    groups.forEach((group) => { group.hidden = filter !== "all" && group.dataset.courseGroup !== filter; });
    document.getElementById("home-course-grid").dataset.activeFilter = filter;
  }

  function bindCourseFilters() {
    const buttons = [...document.querySelectorAll("[data-course-filter]")];
    buttons.forEach((button) => button.addEventListener("click", () => {
      applyCourseFilter(button.dataset.courseFilter);
    }));
  }

  function renderHome() {
    const root = document.getElementById("home-course-grid");
    const activeFilter = root.dataset.activeFilter || "all";
    const courseName = selectedCourseName();
    const lectureProgress = readLectureProgress();
    updateMobileLinks(courseName, lectureProgress);
    const progress = readProgress();
    buildCourseGrid(progress, lectureProgress);
    renderReviewTasks(progress);
    bindCourseLinks();
    applyCourseFilter(activeFilter);
  }

  function renderReviewTasks(progress) {
    const root = document.getElementById("home-review-tasks");
    const ratings = StudyReview.read();
    const entries = [];
    const now = Date.now();
    COURSE_INDEX.forEach((course) => {
      const dueCards = Object.entries(ratings).filter(([key, value]) => {
        const [name, chapter, card] = key.split("::");
        return name === course.name && Number.isInteger(Number(chapter)) && Number(chapter) > 0
          && Number.isInteger(Number(card)) && Number(card) > 0
          && Number(card) <= (course.review_card_counts?.[Number(chapter) - 1] || 0)
          && StudyReview.isDue(value, now);
      });
      const subjects = course.subjects || [course.subject];
      const dueQuestions = QUESTION_INDEX.filter((question) => {
        if (!subjects.includes(question.subject) || progress.flagged?.[question.id]) return false;
        const meta = progress.reviewMeta?.[question.id];
        return meta ? Date.parse(meta.nextReviewAt) <= now : Boolean(progress.wrong?.[question.id]);
      }).length;
      if (dueCards.length) {
        const [, chapter, card] = dueCards[0][0].split("::");
        const params = new URLSearchParams({course: course.name, chapter, card, recall: "due"});
        entries.push({label: `${course.name} · 回忆 ${dueCards.length} 个知识点`, href: `./color-notes.html#${params}`, count: dueCards.length});
      }
      if (dueQuestions) entries.push({label: `${course.name} · 重练 ${dueQuestions} 题`, href: `./quiz.html?${new URLSearchParams({course: course.name, mode: "review"})}`, count: dueQuestions});
    });
    root.hidden = !entries.length;
    root.replaceChildren();
    if (!entries.length) return;
    const heading = document.createElement("h2");
    heading.textContent = "待复习";
    root.appendChild(heading);
    entries.sort((left, right) => right.count - left.count).forEach((entry, index) => {
      const link = document.createElement("a");
      link.href = entry.href;
      link.textContent = `${entry.label} →`;
      if (index < 3) root.appendChild(link);
    });
    if (entries.length > 3) {
      const more = document.createElement("details");
      const summary = document.createElement("summary");
      summary.textContent = `其余 ${entries.length - 3} 项`;
      more.appendChild(summary);
      entries.slice(3).forEach((entry) => {
        const link = document.createElement("a");
        link.href = entry.href;
        link.textContent = `${entry.label} →`;
        more.appendChild(link);
      });
      root.appendChild(more);
    }
  }

  function registerServiceWorker() {
    if (!("serviceWorker" in navigator)) return;
    window.addEventListener("load", () => {
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

  document.getElementById("home-reset").addEventListener("click", () => window.clearStudyData());
  bindCourseFilters();
  renderHome();
  window.addEventListener("pageshow", renderHome);
  window.addEventListener("storage", (event) => {
    if (!event.key || [...STORE_KEYS, StudyReview.key, "shaoyang-selected-course-v1", "shaoyang-last-learning", "shaoyang-reading-progress-v1"].includes(event.key)) renderHome();
  });
  registerServiceWorker();
})();
