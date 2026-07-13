(function () {
  "use strict";

  const RAW_QUESTION_INDEX = Array.isArray(window.HOME_QUESTION_INDEX)
    ? window.HOME_QUESTION_INDEX
    : Array.isArray(window.QUESTIONS)
      ? window.QUESTIONS.map(({id, subject, type, answer}) => ({id, subject, type, answer}))
      : [];
  const QUESTION_INDEX = RAW_QUESTION_INDEX.filter((question) => !/^(?:uc|ue)-/i.test(String(question.id || "")));
  const QUESTION_IDS = new Set(QUESTION_INDEX.map((question) => question.id));
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

  function readLastLearning() {
    try {
      const value = JSON.parse(localStorage.getItem("shaoyang-last-learning") || "null");
      return value && typeof value === "object" ? value : null;
    } catch {
      return null;
    }
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

  function dueIds(progress) {
    const now = Date.now();
    const ids = new Set();
    const meta = progress.reviewMeta && typeof progress.reviewMeta === "object" ? progress.reviewMeta : {};
    Object.entries(meta).forEach(([id, item]) => {
      if (!QUESTION_IDS.has(id)) return;
      const due = item && Date.parse(item.nextReviewAt);
      if (Number.isFinite(due) && due <= now && !(progress.flagged || {})[id]) ids.add(id);
    });
    Object.keys(progress.wrong || {}).forEach((id) => {
      if (QUESTION_IDS.has(id) && !(progress.flagged || {})[id] && !meta[id]) ids.add(id);
    });
    return ids;
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
        const percent = stats.total ? Math.min(100, Math.round(stats.done * 100 / stats.total)) : 0;
        const noteHash = `#course=${encodeURIComponent(course.name)}`;
        return `<a class="home-course-card" href="./notes.html${noteHash}" aria-label="进入${course.name}讲义">
          <div class="home-course-title"><span aria-hidden="true">${course.icon}</span><div><strong>${course.name}</strong><small>${progressText}</small></div></div>
          <div class="course-progress" aria-label="已完成 ${percent}%"><span style="width:${percent}%"></span></div>
          <div class="course-card-footer"><span>${stats.done ? "继续课程" : "进入课程"}</span><b aria-hidden="true">→</b></div>
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
      });
    });
  }

  function updateStatus(progress) {
    const done = progress.done && typeof progress.done === "object" ? progress.done : {};
    const completed = QUESTION_INDEX.filter((question) => Object.prototype.hasOwnProperty.call(done, question.id));
    const correct = completed.filter((question) => isCorrect(question, done[question.id])).length;
    const wrongCount = QUESTION_INDEX.filter((question) => (progress.wrong || {})[question.id]).length;
    const dueCount = dueIds(progress).size;
    const rate = completed.length ? Math.round(correct * 100 / completed.length) : null;
    const last = readLastLearning();
    const $ = (id) => document.getElementById(id);

    $("home-done").textContent = completed.length;
    $("home-rate").textContent = rate === null ? "—" : `${rate}%`;
    $("home-due").textContent = dueCount;
    $("home-wrong").textContent = wrongCount;
    $("question-count").textContent = QUESTION_INDEX.length;
    $("short-count").textContent = QUESTION_INDEX.filter((question) => question.type === "简答").length;

    const action = $("continue-action");
    const recommendation = $("status-recommendation");
    const note = $("status-note");
    const status = $("learning-status");
    const statusTitle = $("status-title");
    const statusKicker = $("status-kicker");
    const hasProgress = completed.length > 0 || wrongCount > 0 || dueCount > 0 || !!last;
    status?.classList.toggle("has-progress", hasProgress);
    status?.closest(".home-hero")?.classList.toggle("has-progress", hasProgress);
    if (statusTitle) statusTitle.textContent = hasProgress ? "今天从这里继续" : "从一个课程开始";
    if (statusKicker) statusKicker.textContent = hasProgress ? "你的学习状态" : "新手起点";
    if (dueCount > 0) {
      action.href = "./quiz.html?mode=review";
      action.textContent = `复习 ${dueCount} 道到期题`;
      recommendation.textContent = `有 ${dueCount} 道题需要再次提取。先完成到期复习，再学习新内容。`;
    } else if (last && last.course) {
      const page = last.module === "color-notes" ? "color-notes.html" : "notes.html";
      const moduleName = last.module === "color-notes" ? "三色回忆" : "讲义";
      const position = new URLSearchParams({course: last.course});
      if (Number.isInteger(last.chapter) && last.chapter > 0) position.set("chapter", String(last.chapter));
      if (last.module === "color-notes" && Number.isInteger(last.card) && last.card > 0) position.set("card", String(last.card));
      action.href = `./${page}#${position.toString()}`;
      action.textContent = `继续：${last.course}`;
      recommendation.textContent = `上次学习了“${last.course}”${moduleName}，可以从这个科目继续完成学习闭环。`;
    } else if (wrongCount > 0) {
      action.href = "./quiz.html?mode=wrong";
      action.textContent = `处理 ${wrongCount} 道错题`;
      recommendation.textContent = `先定位错因并重做错题，连续答对后再扩大练习范围。`;
    } else if (completed.length > 0) {
      action.href = "./quiz.html?mode=seq";
      action.textContent = "继续练习";
      recommendation.textContent = `你已完成 ${completed.length} 道题。下一步可继续当前科目，并在答题后核对解析。`;
    } else {
      action.href = "#courses";
      action.textContent = "选择课程 →";
      recommendation.textContent = "先选一个科目，从讲义的一个小节开始，学完立即回忆并做题检验。";
    }
    note.textContent = completed.length
      ? `正确率基于 ${completed.length} 道已作答题；记录只保存在当前浏览器中。`
      : "学习记录只保存在当前浏览器中，可在刷题页导出备份。";
  }

  function registerServiceWorker() {
    if (!("serviceWorker" in navigator)) return;
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("./sw.js", {updateViaCache: "none"}).catch(() => {});
    });
  }

  const progress = readProgress();
  updateStatus(progress);
  buildCourseGrid(progress);
  bindCourseFilters();
  registerServiceWorker();
})();
