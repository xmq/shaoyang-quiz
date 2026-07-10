const QUESTIONS = Array.isArray(window.QUESTIONS) ? window.QUESTIONS : [];
const QUESTION_MEDIA = window.QUESTION_MEDIA && typeof window.QUESTION_MEDIA === "object" ? window.QUESTION_MEDIA : {};
const BUILD_INFO = window.SHAOYANG_BUILD && typeof window.SHAOYANG_BUILD === "object" ? window.SHAOYANG_BUILD : {id: "development"};
const STORE_KEY = "shaoyang-quiz-v4";
const LEGACY_KEYS = ["shaoyang-quiz-v3", "shaoyang-quiz-v2", "shaoyang-quiz-v1"];
const STATE_SCHEMA_VERSION = 4;
const QUESTION_BANK_VERSION = BUILD_INFO.id;
const QUESTION_REVISIONS = Object.freeze({
  "web-17": 1,
  "cg-02-s1-q19": 1,
  "zg-26051": 1,
  "zg-42658": 1,
  "cg-03-s2-q11": 1,
  "cg-14-s1-q29": 1,
  "cg-14-s1-q30": 1,
  "cg-14-s1-q37": 1,
  "cg-14-s1-q41": 1,
  "cg-14-s2-q3": 1,
});
const MAX_IMPORT_BYTES = 5 * 1024 * 1024;
const MAX_HISTORY_PER_QUESTION = 50;
const MASTER_THRESHOLD = 2;
const SUBJECT_ORDER = ["信息基础", "计算机基础", "操作系统", "计算机网络", "数据库", "办公软件", "多媒体", "编程语言", "算法与数据结构", "信息安全", "教学论", "其他"];
const TYPE_ORDER = ["单选", "多选", "判断", "填空"];
const SOURCE_ORDER = ["题海训练", "超格", "中公", "德阳", "网络"];
const PROGRESS_FIELDS = ["done", "wrong", "streak", "fav", "flagged", "history"];

const $ = (id) => document.getElementById(id);

function readStore(key, fallback = {}) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : fallback;
  } catch {
    return fallback;
  }
}

function initialState() {
  let storedRevisions = {};
  let stored = readStore(STORE_KEY, null);
  if (stored && stored.state && typeof stored.state === "object") {
    storedRevisions = isRecord(stored.questionRevisions) ? stored.questionRevisions : {};
    stored = stored.state;
  }
  if (!stored) {
    stored = {};
    for (const key of LEGACY_KEYS) {
      const legacy = readStore(key, null);
      if (legacy) {
        storedRevisions = isRecord(legacy.questionRevisions) ? legacy.questionRevisions : {};
        stored = legacy.state && typeof legacy.state === "object" ? legacy.state : legacy;
        break;
      }
    }
  }

  return applyQuestionRevisionResets(sanitizeState(stored, false), storedRevisions);
}

let state = initialState();
let saveWarningShown = false;
let drawerReturnFocus = null;
let focusQuestionAfterRender = false;
let focusFeedbackAfterRender = false;
save({silent: true});

function save({silent = false} = {}) {
  const persisted = {...state};
  delete persisted._pending;
  delete persisted._stickyId;
  delete persisted._revisionResetCount;
  delete persisted._navBack;
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify({
      schemaVersion: STATE_SCHEMA_VERSION,
      questionBankVersion: QUESTION_BANK_VERSION,
      questionRevisions: QUESTION_REVISIONS,
      savedAt: new Date().toISOString(),
      state: persisted,
    }));
    return true;
  } catch {
    if (!silent && !saveWarningShown) {
      saveWarningShown = true;
      alert("学习进度保存失败：浏览器存储空间可能不足。请先导出进度备份。");
    }
    return false;
  }
}

function stateDefaults() {
  return {
    done: {},
    wrong: {},
    streak: {},
    fav: {},
    history: {},
    flagged: {},
    mode: "home",
    subject: "",
    typeFilter: "",
    sourceFilter: "",
    chapterFilter: "",
    searchQuery: "",
    currentId: null,
    cursor: 0,
  };
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[c]));
}

function normalizeAnswer(value) {
  return String(value || "")
    .replace(/\s+/g, "")
    .toLowerCase()
    .replace(/[，、；,;]/g, "|")
    .replace(/[(（].*?[)）]/g, "");
}

function isAnswerCorrect(q, given) {
  if (q.type === "多选") {
    return [...String(given || "")].sort().join("") === [...String(q.answer || "")].sort().join("");
  }
  if (q.type === "填空") {
    return normalizeAnswer(given) === normalizeAnswer(q.answer);
  }
  return given === q.answer;
}

function orderedValues(values, order) {
  return [...values].sort((a, b) => {
    const ai = order.indexOf(a);
    const bi = order.indexOf(b);
    if (ai !== -1 || bi !== -1) return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
    return a.localeCompare(b, "zh-CN");
  });
}

function countBy(items, getter) {
  const out = {};
  for (const item of items) {
    const key = getter(item);
    if (!key) continue;
    out[key] = (out[key] || 0) + 1;
  }
  return out;
}

function chapterKey(q) {
  return q.source_chapter || q.chapter || q.subject || "未分类";
}

function searchableText(q) {
  const options = q.options ? Object.values(q.options).join(" ") : "";
  return [q.id, q.source, q.type, q.subject, chapterKey(q), q.stem, options, q.answer, q.explanation]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

function getScope() {
  let scope = QUESTIONS;
  if (state.subject) scope = scope.filter((q) => q.subject === state.subject);
  if (state.typeFilter) scope = scope.filter((q) => q.type === state.typeFilter);
  if (state.sourceFilter) scope = scope.filter((q) => q.source === state.sourceFilter);
  if (state.chapterFilter) scope = scope.filter((q) => chapterKey(q) === state.chapterFilter);
  const query = String(state.searchQuery || "").trim().toLowerCase();
  if (query) {
    const parts = query.split(/\s+/).filter(Boolean);
    scope = scope.filter((q) => {
      const text = searchableText(q);
      return parts.every((part) => text.includes(part));
    });
  }
  return scope;
}

function getPool() {
  let pool = getScope();
  if (state.mode === "review") {
    pool = buildReviewPool(pool);
  } else if (state.mode === "wrong") {
    pool = pool.filter((q) => state.wrong[q.id] || state._stickyId === q.id);
  } else if (state.mode === "fav") {
    pool = pool.filter((q) => state.fav[q.id]);
  } else {
    pool = pool.filter((q) => state.searchQuery || !state.done[q.id] || state._stickyId === q.id);
  }

  if (state.mode === "rnd") {
    if (!state._shuffled) {
      const ids = [...pool].sort(() => Math.random() - 0.5).map((q) => q.id);
      state._shuffleIds = ids;
      state._shuffled = true;
    }
    const map = Object.fromEntries(pool.map((q) => [q.id, q]));
    pool = (state._shuffleIds || []).map((id) => map[id]).filter(Boolean);
  }
  return pool;
}

function buildReviewPool(scope) {
  return scope
    .filter((q) => !state.flagged[q.id] && (state.wrong[q.id] || state.fav[q.id] || state._stickyId === q.id))
    .sort((a, b) => reviewScore(b) - reviewScore(a))
    .slice(0, 80);
}

function reviewScore(q) {
  const wrong = state.wrong[q.id] || 0;
  const streak = state.streak[q.id] || 0;
  const fav = state.fav[q.id] ? 1 : 0;
  return wrong * 100 + Math.max(0, MASTER_THRESHOLD - streak) * 20 + fav * 8;
}

function resetPosition() {
  state.cursor = 0;
  state.currentId = null;
  state._stickyId = null;
  state._pending = null;
  state._shuffled = false;
  state._navBack = [];
}

function handleAnswer(q, given) {
  const active = document.activeElement;
  if (active && active.closest(".options, .multi-actions, .fill-blank") && active.matches(":focus-visible")) {
    focusFeedbackAfterRender = true;
  }
  state.done[q.id] = given;
  state.history[q.id] = state.history[q.id] || [];
  state.history[q.id].push(given);
  if (state.history[q.id].length > MAX_HISTORY_PER_QUESTION) {
    state.history[q.id] = state.history[q.id].slice(-MAX_HISTORY_PER_QUESTION);
  }
  state._stickyId = q.id;
  state.currentId = q.id;

  const correct = isAnswerCorrect(q, given);
  if (!correct) {
    state.wrong[q.id] = (state.wrong[q.id] || 0) + 1;
    state.streak[q.id] = 0;
    announceAnswer(q, false);
    return;
  }

  if (state.wrong[q.id]) {
    state.streak[q.id] = (state.streak[q.id] || 0) + 1;
    if (state.streak[q.id] >= MASTER_THRESHOLD) {
      delete state.wrong[q.id];
      delete state.streak[q.id];
    }
  }
  announceAnswer(q, true);
}

function announceAnswer(q, correct) {
  const live = $("answer-live");
  if (!live) return;
  live.textContent = "";
  requestAnimationFrame(() => {
    live.textContent = correct ? "回答正确，解析已展开。" : `回答错误，正确答案是 ${q.answer}，解析已展开。`;
  });
}

function updateSubjectSelect() {
  const select = $("subject-select");
  const counts = countBy(QUESTIONS, (q) => q.subject);
  const subjects = orderedValues(new Set(Object.keys(counts)), SUBJECT_ORDER);
  select.innerHTML = `<option value="">全部科目 (${QUESTIONS.length})</option>` +
    subjects.map((s) => `<option value="${escapeHtml(s)}">${escapeHtml(s)} (${counts[s]})</option>`).join("");
  select.value = state.subject || "";
}

function updateStats() {
  updateSubjectSelect();
  renderActiveFilters();
  if ($("search-input").value !== (state.searchQuery || "")) $("search-input").value = state.searchQuery || "";
  const scope = getScope();
  const done = scope.filter((q) => state.done[q.id]).length;
  const correct = scope.filter((q) => state.done[q.id] && isAnswerCorrect(q, state.done[q.id])).length;
  const wrong = done - correct;
  const wrongbook = scope.filter((q) => state.wrong[q.id]).length;
  const pct = scope.length ? Math.round(done * 100 / scope.length) : 0;
  const rate = done ? Math.round(correct * 100 / done) : 0;

  $("stat-done").textContent = done;
  $("stat-correct").textContent = correct;
  $("stat-wrong").textContent = wrong;
  $("stat-rate").textContent = `${rate}%`;
  $("stat-wrongbook").textContent = wrongbook;
  $("progress-fill").style.width = `${pct}%`;
  $("progress").setAttribute("aria-valuenow", String(pct));
  $("progress").setAttribute("aria-valuetext", `已完成 ${done} 道，共 ${scope.length} 道，${pct}%`);
  $("mini-stat").textContent = `${done}/${scope.length} · ${rate}%${wrongbook ? " · 错" + wrongbook : ""}`;
}

function subjectStats(subject) {
  const subset = subject ? QUESTIONS.filter((q) => q.subject === subject) : QUESTIONS;
  const done = subset.filter((q) => state.done[q.id]).length;
  const correct = subset.filter((q) => state.done[q.id] && isAnswerCorrect(q, state.done[q.id])).length;
  const wrongbook = subset.filter((q) => state.wrong[q.id]).length;
  const rate = done ? Math.round(correct * 100 / done) : 0;
  const progress = subset.length ? Math.round(done * 100 / subset.length) : 0;
  return {total: subset.length, done, correct, wrongbook, rate, progress};
}

function wrongGrade(count) {
  if (count >= 3) return "高频错";
  if (count === 2) return "二刷错";
  if (count === 1) return "新错题";
  return "";
}

function renderActiveFilters() {
  const container = $("active-filters");
  const filters = [
    ["typeFilter", "题型", state.typeFilter],
    ["sourceFilter", "来源", state.sourceFilter],
    ["chapterFilter", "章节", state.chapterFilter],
  ].filter(([, , value]) => value);
  container.classList.toggle("hidden", filters.length === 0);
  if (!filters.length) {
    container.innerHTML = "";
    return;
  }
  container.innerHTML = filters.map(([key, label, value]) =>
    `<button type="button" data-clear-filter="${key}" aria-label="清除${label}筛选：${escapeHtml(value)}">${label}：${escapeHtml(value)} ×</button>`
  ).join("") + '<button type="button" class="clear-all" data-clear-filter="all">清除全部</button>';
  container.querySelectorAll("[data-clear-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      const key = button.dataset.clearFilter;
      if (key === "all") {
        state.typeFilter = "";
        state.sourceFilter = "";
        state.chapterFilter = "";
      } else {
        state[key] = "";
        if (key !== "chapterFilter") state.chapterFilter = "";
      }
      resetPosition();
      save();
      render();
    });
  });
}

function optionKeys(q) {
  return Object.keys(q.options || {})
    .filter((key) => /^[A-Z]$/.test(key))
    .sort((a, b) => a.localeCompare(b, "en"));
}

function renderChoiceQuestion(q, chosen, inWrongFresh) {
  const isMulti = q.type === "多选";
  const pending = state._pending && state._pending.qid === q.id ? state._pending.set : new Set();
  const options = optionKeys(q);
  const optsHtml = options.map((letter) => {
    let cls = "opt";
    if (chosen) {
      const answerSet = new Set(String(q.answer || "").split(""));
      const userSet = new Set(String(chosen || "").split(""));
      if (answerSet.has(letter)) cls += " correct";
      else if (userSet.has(letter)) cls += " wrong";
    } else if (isMulti && pending.has(letter)) {
      cls += " selected";
    }
    const pressed = isMulti && !chosen ? String(pending.has(letter)) : null;
    return `<button type="button" class="${cls}" data-letter="${letter}"${pressed === null ? "" : ` aria-pressed="${pressed}"`}${chosen ? " disabled" : ""}>
      <span class="letter">${letter}</span>
      <span class="text">${escapeHtml(q.options[letter])}</span>
    </button>`;
  }).join("");

  const submit = isMulti && !chosen
    ? `<div class="multi-actions"><button id="submit-multi" class="primary-btn">提交多选答案 (${pending.size})</button></div>`
    : "";
  return `<div class="options">${optsHtml}</div>${submit}`;
}

function renderJudgeQuestion(q, chosen) {
  return `<div class="options">${["正确", "错误"].map((value) => {
    let cls = "opt";
    if (chosen) {
      if (value === q.answer) cls += " correct";
      else if (value === chosen) cls += " wrong";
    }
    return `<button type="button" class="${cls}" data-judge="${value}"${chosen ? " disabled" : ""}>
      <span class="letter">${value === "正确" ? "✓" : "×"}</span>
      <span class="text">${value}</span>
    </button>`;
  }).join("")}</div>`;
}

function renderFillQuestion(q, chosen) {
  const val = chosen || (state._pending && state._pending.qid === q.id ? state._pending.text : "");
  const cls = chosen ? (isAnswerCorrect(q, chosen) ? "correct" : "wrong") : "";
  return `<div class="fill-blank">
    <input id="fill-input" class="${cls}" value="${escapeHtml(val)}" placeholder="输入答案..." ${chosen ? "disabled" : ""}>
    ${!chosen ? '<button id="submit-fill" class="primary-btn">提交</button><button id="show-fill" class="secondary-btn">查看答案</button>' : ""}
  </div>`;
}

function feedbackHtml(q, chosen) {
  if (!chosen) return "";
  const ok = isAnswerCorrect(q, chosen);
  const wrongCount = state.wrong[q.id] || 0;
  const streak = state.streak[q.id] || 0;
  const remain = Math.max(0, MASTER_THRESHOLD - streak);
  const grade = wrongGrade(wrongCount);
  const badge = wrongCount ? ` · 已错 ${wrongCount} 次${ok && remain ? ` · 还需连续答对 ${remain} 次出本` : ""}${grade ? `<span class="wrong-grade">${grade}</span>` : ""}` : "";
  const answer = q.type === "填空" || q.type === "判断" ? `答案：${q.answer}` : `答案：${q.answer}`;
  const explanation = q.explanation && q.explanation.trim()
    ? `<div class="explanation"><div class="exp-title">解析</div>${escapeHtml(q.explanation)}</div>`
    : `<div class="explanation">本题暂无文字解析</div>`;
  return `<div class="feedback" role="status" aria-live="polite" tabindex="-1">
    <div class="feedback-label ${ok ? "ok" : "ng"}">${ok ? "✓ 正确" : "× 错误，" + answer}${badge}</div>
    ${explanation}
  </div>`;
}

function mediaHtml(q) {
  const media = QUESTION_MEDIA[q.id];
  if (!media || !media.src) return "";
  return `<figure class="question-media">
    <img src="${escapeHtml(media.src)}" alt="${escapeHtml(media.alt || "题图重绘示意")}" loading="lazy">
    <figcaption><strong>${escapeHtml(media.label || "重绘示意")}</strong>${media.note ? `：${escapeHtml(media.note)}` : ""}</figcaption>
  </figure>`;
}

function renderQuestion(q, pool) {
  const inWrongFresh = state.mode === "wrong" && state._stickyId !== q.id;
  const chosen = inWrongFresh ? null : state.done[q.id];
  const isFav = !!state.fav[q.id];
  const isFlagged = !!state.flagged[q.id];
  let body = "";

  if (q.type === "单选" || q.type === "多选") body = renderChoiceQuestion(q, chosen, inWrongFresh);
  else if (q.type === "判断") body = renderJudgeQuestion(q, chosen);
  else if (q.type === "填空") body = renderFillQuestion(q, chosen);

  $("card-area").innerHTML = `<article class="card" aria-labelledby="question-stem">
    <div class="meta">
      <span class="badge source source-${escapeHtml(q.source)}">${escapeHtml(q.source)}</span>
      <span class="badge type-${escapeHtml(q.type)}">${escapeHtml(q.type)}</span>
      <span class="badge subject">${escapeHtml(q.subject)}</span>
      <span class="chapter">${escapeHtml(q.source_chapter || q.chapter || "")}</span>
      <span class="q-pos">${state.cursor + 1} / ${pool.length}</span>
    </div>
    <div class="stem" id="question-stem" tabindex="-1">${escapeHtml(q.stem)}</div>
    ${mediaHtml(q)}
    ${body}
    ${feedbackHtml(q, chosen)}
    <div class="nav ${chosen ? "answered" : "unanswered"}">
      <button class="nav-icon" id="prev" aria-label="上一题"${state._navBack && state._navBack.length ? "" : " disabled"}>←</button>
      <button class="nav-icon fav ${isFav ? "active" : ""}" id="fav" aria-label="收藏" aria-pressed="${isFav}">${isFav ? "★" : "☆"}</button>
      <button class="nav-icon flag ${isFlagged ? "active" : ""}" id="flag" aria-label="标记有问题" aria-pressed="${isFlagged}">!</button>
      ${state.done[q.id] ? '<button class="nav-icon" id="redo" aria-label="重答">↻</button>' : ""}
      <button class="next ${state.done[q.id] ? "ready" : ""}" id="next">${state.done[q.id] ? "下一题 →" : "跳过 →"}</button>
    </div>
  </article>`;

  bindQuestionEvents(q, inWrongFresh);
  if (focusFeedbackAfterRender && chosen) {
    focusFeedbackAfterRender = false;
    requestAnimationFrame(() => {
      const feedback = document.querySelector(".feedback");
      feedback?.focus({preventScroll: true});
      feedback?.scrollIntoView({behavior: "smooth", block: "nearest"});
    });
  }
  if (focusQuestionAfterRender) {
    focusQuestionAfterRender = false;
    requestAnimationFrame(() => {
      const stem = $("question-stem");
      stem?.scrollIntoView({behavior: "smooth", block: "start"});
      stem?.focus({preventScroll: true});
    });
  }
}

function bindQuestionEvents(q, inWrongFresh) {
  const canAnswer = !state.done[q.id] || inWrongFresh;
  document.querySelectorAll("[data-letter]").forEach((el) => {
    el.addEventListener("click", () => {
      if (!canAnswer) return;
      const letter = el.dataset.letter;
      if (q.type === "单选") {
        handleAnswer(q, letter);
        save();
        render();
      } else {
        if (!state._pending || state._pending.qid !== q.id) state._pending = {qid: q.id, set: new Set()};
        if (state._pending.set.has(letter)) state._pending.set.delete(letter);
        else state._pending.set.add(letter);
        render();
      }
    });
  });

  document.querySelectorAll("[data-judge]").forEach((el) => {
    el.addEventListener("click", () => {
      if (!canAnswer) return;
      handleAnswer(q, el.dataset.judge);
      save();
      render();
    });
  });

  const multi = $("submit-multi");
  if (multi) {
    multi.addEventListener("click", () => {
      if (!state._pending || state._pending.qid !== q.id || state._pending.set.size === 0) {
        alert("请至少选一项");
        return;
      }
      const answer = [...state._pending.set].sort().join("");
      state._pending = null;
      handleAnswer(q, answer);
      save();
      render();
    });
  }

  const input = $("fill-input");
  const submitFill = $("submit-fill");
  const showFill = $("show-fill");
  if (input) {
    input.addEventListener("input", () => {
      state._pending = {qid: q.id, text: input.value};
    });
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && submitFill) submitFill.click();
    });
  }
  if (submitFill) {
    submitFill.addEventListener("click", () => {
      const value = input.value.trim();
      if (!value) {
        alert("请输入答案");
        return;
      }
      handleAnswer(q, value);
      save();
      render();
    });
  }
  if (showFill) {
    showFill.addEventListener("click", () => {
      handleAnswer(q, "【放弃】");
      save();
      render();
    });
  }

  $("prev").addEventListener("click", prevQuestion);
  $("next").addEventListener("click", nextQuestion);
  $("fav").addEventListener("click", () => {
    if (state.fav[q.id]) delete state.fav[q.id];
    else state.fav[q.id] = true;
    save();
    render();
  });
  $("flag").addEventListener("click", () => {
    if (state.flagged[q.id]) delete state.flagged[q.id];
    else state.flagged[q.id] = new Date().toISOString();
    save();
    render();
  });

  const redo = $("redo");
  if (redo) {
    redo.addEventListener("click", () => {
      delete state.done[q.id];
      state._pending = null;
      save();
      render();
    });
  }
}

function renderEmpty() {
  let title = "当前条件下题目已全部刷完";
  let text = "可以切换科目、题型、来源，或进入错题本继续练。";
  if (state.searchQuery) {
    title = "没有找到匹配题目";
    text = "换个关键词，或清空科目、章节、来源筛选后再搜。";
  } else if (state.chapterFilter) {
    title = "当前章节没有可刷题目";
    text = "可以切换模式，或在侧栏清空章节筛选。";
  }
  if (state.mode === "wrong") {
    title = "错题本已清空";
    text = "当前筛选条件下没有待复习错题。";
  } else if (state.mode === "fav") {
    title = "收藏夹为空";
    text = "刷题时点击 ☆ 收藏题目。";
  } else if (state.mode === "review") {
    title = "暂无复习队列";
    text = "答错或收藏的题会进入复习候选；标记有问题的题会暂停复习，等待核对。";
  }
  $("card-area").innerHTML = `<div class="card empty"><strong>${title}</strong>${text}</div>`;
}

function renderDashboard() {
  updateStats();
  updateModeTabs();
  const all = subjectStats("");
  const wrongIds = Object.keys(state.wrong || {});
  const favCount = Object.keys(state.fav || {}).length;
  const flaggedCount = Object.keys(state.flagged || {}).length;
  const reviewCount = buildReviewPool(getScope()).length;
  const wrongLevel = wrongIds.reduce((acc, id) => {
    const count = state.wrong[id] || 0;
    if (count >= 3) acc.high += 1;
    else if (count === 2) acc.mid += 1;
    else if (count === 1) acc.low += 1;
    return acc;
  }, {low: 0, mid: 0, high: 0});

  const subjectCounts = countBy(QUESTIONS, (q) => q.subject);
  const rows = orderedValues(new Set(Object.keys(subjectCounts)), SUBJECT_ORDER)
    .map((subject) => ({subject, ...subjectStats(subject)}))
    .sort((a, b) => (b.wrongbook - a.wrongbook) || (a.rate - b.rate) || (b.total - a.total))
    .slice(0, 8)
    .map((row) => `<div class="subject-row">
      <strong>${escapeHtml(row.subject)}</strong>
      <div class="subject-bar" title="${row.done}/${row.total}"><span style="width:${row.progress}%"></span></div>
      <span>${row.rate}% · 错${row.wrongbook}</span>
    </div>`).join("");

  $("card-area").innerHTML = `<section class="dashboard">
    <article class="card">
      <div class="dash-grid">
        <div class="dash-stat"><span class="value">${all.done}</span><span class="label">已做 / ${all.total}</span></div>
        <div class="dash-stat"><span class="value">${all.rate}%</span><span class="label">总正确率</span></div>
        <div class="dash-stat"><span class="value">${wrongIds.length}</span><span class="label">错题本</span></div>
        <div class="dash-stat"><span class="value">${reviewCount}</span><span class="label">今日复习候选</span></div>
      </div>
    </article>
    <article class="card">
      <div class="dash-actions">
        <button class="primary" data-jump-mode="seq">继续刷题</button>
        <button data-jump-mode="review">今日复习</button>
        <button data-jump-mode="wrong">错题本</button>
        <button data-jump-mode="fav">收藏 ${favCount}</button>
      </div>
    </article>
    <article class="card">
      <div class="meta"><span class="badge subject">错题分级</span><span class="chapter">高频错题优先处理</span></div>
      <div class="dash-grid">
        <div class="dash-stat"><span class="value">${wrongLevel.low}</span><span class="label">新错题</span></div>
        <div class="dash-stat"><span class="value">${wrongLevel.mid}</span><span class="label">二刷错</span></div>
        <div class="dash-stat"><span class="value">${wrongLevel.high}</span><span class="label">高频错</span></div>
        <div class="dash-stat"><span class="value">${flaggedCount}</span><span class="label">纠错标记</span></div>
      </div>
    </article>
    <article class="card">
      <div class="meta"><span class="badge source">薄弱科目</span><span class="chapter">按错题数和正确率排序</span></div>
      <div class="subject-table">${rows}</div>
    </article>
  </section>`;

  document.querySelectorAll("[data-jump-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      state.mode = button.dataset.jumpMode;
      resetPosition();
      focusQuestionAfterRender = true;
      save();
      render();
    });
  });
}

function render() {
  if (!QUESTIONS.length) {
    $("card-area").innerHTML = `<div class="card empty"><strong>题库未加载</strong>请确认 questions.js 与 app.js 在同一目录。</div>`;
    return;
  }

  if (state.mode === "home") {
    renderDashboard();
    return;
  }

  updateStats();
  updateModeTabs();
  const pool = getPool();
  if (!pool.length) {
    renderEmpty();
    return;
  }

  let q = state.currentId ? pool.find((item) => item.id === state.currentId) : null;
  if (!q) {
    q = pool[0];
    state.currentId = q.id;
  }
  state.cursor = pool.indexOf(q);
  renderQuestion(q, pool);
}

function nextQuestion() {
  const leavingId = state.currentId;
  state._stickyId = null;
  state._pending = null;
  const pool = getPool();
  if (!pool.length) {
    state.currentId = null;
    save();
    render();
    return;
  }
  let idx = pool.findIndex((q) => q.id === state.currentId);
  idx = idx >= 0 ? (idx + 1) % pool.length : Math.min(state.cursor, pool.length - 1);
  state._navBack = state._navBack || [];
  if (leavingId && state._navBack[state._navBack.length - 1] !== leavingId) state._navBack.push(leavingId);
  state.currentId = pool[Math.max(0, idx)].id;
  focusQuestionAfterRender = true;
  save();
  render();
}

function prevQuestion() {
  state._stickyId = null;
  state._pending = null;
  const previousId = state._navBack && state._navBack.pop();
  if (previousId) {
    state.currentId = previousId;
    state._stickyId = previousId;
    focusQuestionAfterRender = true;
    save();
    render();
    return;
  }
  const pool = getPool();
  if (!pool.length) {
    state.currentId = null;
    save();
    render();
    return;
  }
  state.currentId = pool[0].id;
  focusQuestionAfterRender = true;
  save();
  render();
}

function updateModeTabs() {
  document.querySelectorAll(".mode").forEach((button) => {
    const active = button.dataset.mode === state.mode;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
}

function renderDrawerList(el, items, active, onPick) {
  el.innerHTML = "";
  for (const item of items) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `drawer-item${item.value === active ? " active" : ""}`;
    button.setAttribute("aria-pressed", String(item.value === active));
    button.innerHTML = `<span>${escapeHtml(item.label)}</span><span class="count">${escapeHtml(item.count)}</span>`;
    button.addEventListener("click", () => onPick(item.value));
    el.appendChild(button);
  }
}

function buildDrawer() {
  const subjectCounts = countBy(QUESTIONS, (q) => q.subject);
  const subjects = [{value: "", label: "全部科目", count: QUESTIONS.length}].concat(
    orderedValues(new Set(Object.keys(subjectCounts)), SUBJECT_ORDER).map((s) => ({value: s, label: s, count: subjectCounts[s]}))
  );
  renderDrawerList($("drawer-subjects"), subjects, state.subject || "", (value) => {
    state.subject = value;
    state.chapterFilter = "";
    resetPosition();
    save();
    closeDrawer();
    render();
  });

  const typeCounts = countBy(QUESTIONS, (q) => q.type);
  const types = [{value: "", label: "全部题型", count: QUESTIONS.length}].concat(
    orderedValues(new Set(Object.keys(typeCounts)), TYPE_ORDER).map((t) => ({value: t, label: t, count: typeCounts[t]}))
  );
  renderDrawerList($("drawer-types"), types, state.typeFilter || "", (value) => {
    state.typeFilter = value;
    state.chapterFilter = "";
    resetPosition();
    save();
    closeDrawer();
    render();
  });

  const sourceCounts = countBy(QUESTIONS, (q) => q.source);
  const sources = [{value: "", label: "全部来源", count: QUESTIONS.length}].concat(
    orderedValues(new Set(Object.keys(sourceCounts)), SOURCE_ORDER).map((s) => ({value: s, label: s, count: sourceCounts[s]}))
  );
  renderDrawerList($("drawer-sources"), sources, state.sourceFilter || "", (value) => {
    state.sourceFilter = value;
    state.chapterFilter = "";
    resetPosition();
    save();
    closeDrawer();
    render();
  });

  let chapterBase = QUESTIONS;
  if (state.subject) chapterBase = chapterBase.filter((q) => q.subject === state.subject);
  if (state.typeFilter) chapterBase = chapterBase.filter((q) => q.type === state.typeFilter);
  if (state.sourceFilter) chapterBase = chapterBase.filter((q) => q.source === state.sourceFilter);
  const chapterCounts = countBy(chapterBase, chapterKey);
  const chapters = [{value: "", label: "全部章节", count: chapterBase.length}].concat(
    Object.keys(chapterCounts)
      .sort((a, b) => a.localeCompare(b, "zh-CN", {numeric: true}))
      .map((chapter) => ({value: chapter, label: chapter, count: chapterCounts[chapter]}))
  );
  renderDrawerList($("drawer-chapters"), chapters, state.chapterFilter || "", (value) => {
    state.chapterFilter = value;
    resetPosition();
    save();
    closeDrawer();
    render();
  });
}

function openDrawer() {
  buildDrawer();
  drawerReturnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : $("drawer-toggle");
  $("drawer").classList.add("show");
  $("drawer-mask").classList.add("show");
  $("drawer").setAttribute("aria-hidden", "false");
  $("drawer").inert = false;
  $("drawer-toggle").setAttribute("aria-expanded", "true");
  $("app-main").inert = true;
  document.body.classList.add("drawer-open");
  requestAnimationFrame(() => $("drawer-close").focus());
}

function closeDrawer() {
  const wasOpen = $("drawer").classList.contains("show");
  $("drawer").classList.remove("show");
  $("drawer-mask").classList.remove("show");
  $("drawer").setAttribute("aria-hidden", "true");
  $("drawer").inert = true;
  $("drawer-toggle").setAttribute("aria-expanded", "false");
  $("app-main").inert = false;
  document.body.classList.remove("drawer-open");
  if (wasOpen && drawerReturnFocus && document.contains(drawerReturnFocus)) {
    drawerReturnFocus.focus();
  }
  drawerReturnFocus = null;
}

function trapDrawerFocus(event) {
  const focusable = [...$("drawer").querySelectorAll("button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex='-1'])")]
    .filter((element) => !element.hidden && element.getClientRects().length);
  if (!focusable.length) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

function exportWrong() {
  const ids = Object.keys(state.wrong);
  if (!ids.length) {
    alert("错题本是空的");
    return;
  }
  const map = Object.fromEntries(QUESTIONS.map((q) => [q.id, q]));
  const groups = {};
  for (const id of ids) {
    const q = map[id];
    if (!q) continue;
    const key = q.source_chapter || q.chapter || q.subject || "未分类";
    groups[key] = groups[key] || [];
    groups[key].push({q, count: state.wrong[id]});
  }

  let text = `错题本导出 · ${new Date().toLocaleString("zh-CN")}\n共 ${ids.length} 道错题\n\n`;
  for (const chapter of Object.keys(groups).sort()) {
    text += `\n========== ${chapter} (${groups[chapter].length} 题) ==========\n\n`;
    groups[chapter].forEach(({q, count}, index) => {
      text += `${index + 1}. [错${count}次] ${q.stem}\n`;
      for (const letter of optionKeys(q)) {
        if (q.options && q.options[letter]) text += `   ${letter}. ${q.options[letter]}\n`;
      }
      text += `   【答案】${q.answer}\n`;
      if (q.explanation) text += `   【解析】${q.explanation}\n`;
      text += "\n";
    });
  }
  downloadText(`错题本_${new Date().toISOString().slice(0, 10)}.txt`, text, "text/plain;charset=utf-8");
}

function exportProgress() {
  const payload = {
    app: "shaoyang-quiz",
    schemaVersion: STATE_SCHEMA_VERSION,
    questionBankVersion: QUESTION_BANK_VERSION,
    questionRevisions: QUESTION_REVISIONS,
    exportedAt: new Date().toISOString(),
    state: {...state, _pending: undefined, _stickyId: undefined},
  };
  downloadText(`刷题进度_${new Date().toISOString().slice(0, 10)}.json`, JSON.stringify(payload, null, 2), "application/json;charset=utf-8");
}

function exportFlags() {
  const ids = Object.keys(state.flagged || {});
  if (!ids.length) {
    alert("当前没有纠错标记");
    return;
  }
  const map = Object.fromEntries(QUESTIONS.map((q) => [q.id, q]));
  const rows = ids.map((id) => ({id, q: map[id], markedAt: state.flagged[id]})).filter((row) => row.q);
  let text = `纠错标记导出 · ${new Date().toLocaleString("zh-CN")}\n共 ${rows.length} 道\n\n`;
  rows.forEach(({id, q, markedAt}, index) => {
    text += `${index + 1}. [${markedAt}] ${q.stem}\n`;
    text += `   ID：${id}\n`;
    text += `   来源：${q.source} / ${q.type} / ${q.subject} / ${chapterKey(q)}\n`;
    for (const letter of optionKeys(q)) {
      if (q.options && q.options[letter]) text += `   ${letter}. ${q.options[letter]}\n`;
    }
    text += `   【答案】${q.answer}\n`;
    if (q.explanation) text += `   【解析】${q.explanation}\n`;
    text += "\n";
  });
  downloadText(`纠错标记_${new Date().toISOString().slice(0, 10)}.txt`, text, "text/plain;charset=utf-8");
}

function isRecord(value) {
  return value && typeof value === "object" && !Array.isArray(value);
}

function sanitizeState(input, strict = false) {
  if (!isRecord(input)) {
    if (strict) throw new Error("进度数据不是对象");
    return stateDefaults();
  }
  if (strict && !PROGRESS_FIELDS.some((key) => Object.prototype.hasOwnProperty.call(input, key))) {
    throw new Error("文件中没有学习进度字段");
  }
  for (const key of PROGRESS_FIELDS) {
    if (input[key] !== undefined && !isRecord(input[key])) {
      if (strict) throw new Error(`${key} 字段格式不正确`);
    }
  }

  const clean = stateDefaults();
  const questionMap = new Map(QUESTIONS.map((q) => [q.id, q]));
  const entries = (key) => (isRecord(input[key]) ? Object.entries(input[key]) : []).filter(([id]) => questionMap.has(id));
  clean.done = Object.fromEntries(entries("done").filter(([id, value]) => {
    if (typeof value !== "string" || value.length > 500) return false;
    const question = questionMap.get(id);
    if (question.type === "单选" || question.type === "多选") {
      const letters = [...value];
      if (!letters.length || new Set(letters).size !== letters.length) return false;
      if (question.type === "单选" && letters.length !== 1) return false;
      return letters.every((letter) => optionKeys(question).includes(letter));
    }
    if (question.type === "判断") return value === "正确" || value === "错误";
    return true;
  }));
  for (const key of ["wrong", "streak"]) {
    clean[key] = Object.fromEntries(entries(key).filter(([, value]) => Number.isInteger(value) && value >= (key === "wrong" ? 1 : 0) && value <= 100000));
  }
  clean.fav = Object.fromEntries(entries("fav").filter(([, value]) => Boolean(value)).map(([id]) => [id, true]));
  clean.flagged = Object.fromEntries(entries("flagged").filter(([, value]) => typeof value === "string" && value.length <= 100));
  clean.history = Object.fromEntries(entries("history")
    .filter(([, value]) => Array.isArray(value) && value.every((entry) => typeof entry === "string" && entry.length <= 500))
    .map(([id, value]) => [id, value.slice(-MAX_HISTORY_PER_QUESTION)]));

  if (["home", "seq", "rnd", "review", "wrong", "fav"].includes(input.mode)) clean.mode = input.mode;
  const allowedSubjects = new Set(QUESTIONS.map((q) => q.subject));
  const allowedTypes = new Set(QUESTIONS.map((q) => q.type));
  const allowedSources = new Set(QUESTIONS.map((q) => q.source));
  if (typeof input.subject === "string" && (!input.subject || allowedSubjects.has(input.subject))) clean.subject = input.subject;
  if (typeof input.typeFilter === "string" && (!input.typeFilter || allowedTypes.has(input.typeFilter))) clean.typeFilter = input.typeFilter;
  if (typeof input.sourceFilter === "string" && (!input.sourceFilter || allowedSources.has(input.sourceFilter))) clean.sourceFilter = input.sourceFilter;
  if (typeof input.chapterFilter === "string" && input.chapterFilter.length <= 300) clean.chapterFilter = input.chapterFilter;
  if (typeof input.searchQuery === "string" && input.searchQuery.length <= 300) clean.searchQuery = input.searchQuery;
  if (typeof input.currentId === "string" && questionMap.has(input.currentId)) clean.currentId = input.currentId;
  if (Number.isInteger(input.cursor) && input.cursor >= 0 && input.cursor < QUESTIONS.length) clean.cursor = input.cursor;
  return clean;
}

function applyQuestionRevisionResets(clean, storedRevisions = {}) {
  let resetCount = 0;
  for (const [id, revision] of Object.entries(QUESTION_REVISIONS)) {
    if (storedRevisions[id] === revision) continue;
    const hadProgress = ["done", "wrong", "streak", "history"].some((key) => Object.prototype.hasOwnProperty.call(clean[key], id));
    for (const key of ["done", "wrong", "streak", "history"]) delete clean[key][id];
    if (hadProgress) resetCount += 1;
  }
  if (resetCount) clean._revisionResetCount = resetCount;
  return clean;
}

function validateImportedState(next, storedRevisions = {}) {
  return applyQuestionRevisionResets(sanitizeState(next, true), storedRevisions);
}

function backupProgress(progress) {
  const current = {...progress};
  delete current._pending;
  delete current._stickyId;
  try {
    localStorage.setItem(`${STORE_KEY}-backup`, JSON.stringify({
      backedUpAt: new Date().toISOString(),
      questionBankVersion: QUESTION_BANK_VERSION,
      questionRevisions: QUESTION_REVISIONS,
      state: current,
    }));
    return true;
  } catch {
    throw new Error("无法创建设备内备份，请先导出进度文件");
  }
}

function backupCurrentProgress() {
  return backupProgress(state);
}

function applyImportedState(next) {
  const previous = state;
  state = sanitizeState(next, false);
  resetPosition();
  if (!save()) {
    state = previous;
    render();
    return false;
  }
  render();
  return true;
}

function importProgressFile(file) {
  if (!file || file.size > MAX_IMPORT_BYTES) {
    alert("导入失败：进度文件不能超过 5 MB。");
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const payload = JSON.parse(String(reader.result || "{}"));
      if (payload.app && payload.app !== "shaoyang-quiz") throw new Error("不是本应用的进度文件");
      if (payload.schemaVersion && payload.schemaVersion > STATE_SCHEMA_VERSION) {
        throw new Error("该进度文件来自更新版本，请先升级应用");
      }
      const next = validateImportedState(payload.state || payload, payload.questionRevisions);
      const revisionResetCount = next._revisionResetCount || 0;
      const versionWarning = payload.questionBankVersion && payload.questionBankVersion !== QUESTION_BANK_VERSION
        ? "\n该文件来自不同题库版本，已自动清除修订题的旧作答记录。"
        : "";
      if (!confirm(`导入将替换当前设备上的学习进度，是否继续？${versionWarning}`)) return;
      backupCurrentProgress();
      if (!applyImportedState(next)) return;
      alert(`进度已导入；原进度已自动备份在本设备中。${revisionResetCount ? `另有 ${revisionResetCount} 道修订题已重新加入待练。` : ""}`);
    } catch (error) {
      alert(`导入失败：${error.message || "文件格式不正确"}`);
    }
  };
  reader.readAsText(file, "utf-8");
}

function restoreProgressBackup() {
  const payload = readStore(`${STORE_KEY}-backup`, null);
  if (!payload || !isRecord(payload.state)) {
    alert("当前设备上没有可恢复的导入前进度。");
    return;
  }
  if (!confirm(`确定恢复导入前的进度${payload.backedUpAt ? `（备份时间：${new Date(payload.backedUpAt).toLocaleString("zh-CN")}）` : ""}？`)) return;
  try {
    const next = validateImportedState({...payload.state}, payload.questionRevisions);
    const revisionResetCount = next._revisionResetCount || 0;
    const previous = state;
    if (!applyImportedState(next)) return;
    try {
      backupProgress(previous);
    } catch {
      alert("进度已恢复，但恢复前的状态因存储空间不足未能继续备份。建议立即导出进度文件。");
      return;
    }
    alert(`已恢复进度；恢复前的状态也已保留为最新备份。${revisionResetCount ? `另有 ${revisionResetCount} 道修订题已重新加入待练。` : ""}`);
  } catch (error) {
    alert(`恢复失败：${error.message || "备份格式不正确"}`);
  }
}

function downloadText(filename, content, type) {
  const blob = new Blob([content], {type});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();

  // Some mobile browsers/PWAs finish handling the click asynchronously. Keep
  // the object URL alive briefly and offer a visible fallback link.
  const notice = document.createElement("div");
  notice.className = "download-notice";
  notice.setAttribute("role", "status");

  const message = document.createElement("span");
  message.textContent = `已生成 ${filename}`;
  const fallback = document.createElement("a");
  fallback.href = url;
  fallback.download = filename;
  fallback.textContent = "未自动下载？点此保存";
  const close = document.createElement("button");
  close.type = "button";
  close.setAttribute("aria-label", "关闭提示");
  close.textContent = "×";
  close.addEventListener("click", () => notice.remove());

  notice.append(message, fallback, close);
  document.querySelectorAll(".download-notice").forEach((item) => item.remove());
  document.body.appendChild(notice);

  window.setTimeout(() => a.remove(), 1000);
  window.setTimeout(() => notice.remove(), 15000);
  window.setTimeout(() => URL.revokeObjectURL(url), 60000);
}

function bindGlobalEvents() {
  $("drawer-toggle").addEventListener("click", openDrawer);
  $("drawer-close").addEventListener("click", closeDrawer);
  $("drawer-mask").addEventListener("click", closeDrawer);

  $("subject-select").addEventListener("change", (event) => {
    state.subject = event.target.value;
    state.chapterFilter = "";
    resetPosition();
    save();
    render();
  });

  $("search-input").addEventListener("input", (event) => {
    state.searchQuery = event.target.value;
    resetPosition();
    save();
    render();
  });
  $("clear-search").addEventListener("click", () => {
    state.searchQuery = "";
    resetPosition();
    save();
    render();
  });

  $("stats-toggle").addEventListener("click", () => {
    const stats = $("stats");
    stats.classList.toggle("collapsed");
    const collapsed = stats.classList.contains("collapsed");
    $("stats-toggle").textContent = collapsed ? "▸" : "▾";
    $("stats-toggle").setAttribute("aria-expanded", String(!collapsed));
    $("stats-toggle").setAttribute("aria-label", collapsed ? "展开统计" : "收起统计");
  });

  document.querySelectorAll(".mode").forEach((button) => {
    button.addEventListener("click", () => {
      state.mode = button.dataset.mode;
      resetPosition();
      focusQuestionAfterRender = true;
      save();
      render();
    });
  });

  $("export-wrong").addEventListener("click", () => {
    closeDrawer();
    exportWrong();
  });
  $("export-flags").addEventListener("click", () => {
    closeDrawer();
    exportFlags();
  });
  $("export-progress").addEventListener("click", () => {
    closeDrawer();
    exportProgress();
  });
  $("import-progress").addEventListener("click", () => {
    closeDrawer();
    $("progress-file").click();
  });
  $("restore-progress").addEventListener("click", () => {
    closeDrawer();
    restoreProgressBackup();
  });
  $("progress-file").addEventListener("change", (event) => {
    const file = event.target.files && event.target.files[0];
    if (file) importProgressFile(file);
    event.target.value = "";
  });
  $("reset").addEventListener("click", () => {
    closeDrawer();
    if (!confirm("确定重置所有进度？错题、收藏、历史记录将一并清除。")) return;
    try {
      localStorage.removeItem(STORE_KEY);
      localStorage.removeItem(`${STORE_KEY}-backup`);
      for (const key of LEGACY_KEYS) {
        localStorage.removeItem(key);
        localStorage.removeItem(`${key}-backup`);
      }
    } catch {}
    state = initialState();
    render();
  });

  document.addEventListener("keydown", (event) => {
    if ($("drawer").classList.contains("show")) {
      if (event.key === "Escape") {
        event.preventDefault();
        closeDrawer();
      } else if (event.key === "Tab") {
        trapDrawerFocus(event);
      }
      return;
    }
    const activeElement = document.activeElement;
    if (activeElement && activeElement.closest("button, a, input, select, textarea, [contenteditable='true']")) return;
    const pool = getPool();
    const q = pool[state.cursor];
    if (!q) return;
    const inWrongFresh = state.mode === "wrong" && state._stickyId !== q.id;
    const canAnswer = !state.done[q.id] || inWrongFresh;
    const keys = optionKeys(q);
    const typedLetter = event.key.length === 1 ? event.key.toUpperCase() : "";
    const numericIndex = /^\d$/.test(event.key) ? Number(event.key) - 1 : -1;
    const isLetter = keys.includes(typedLetter);
    const isNum = numericIndex >= 0 && numericIndex < keys.length;

    if (q.type === "判断" && canAnswer) {
      if (event.key === "1" || event.key === "t" || event.key === "T" || event.key === "√") {
        focusFeedbackAfterRender = true;
        handleAnswer(q, "正确");
        save();
        render();
        return;
      }
      if (event.key === "0" || event.key === "f" || event.key === "F" || event.key === "×") {
        focusFeedbackAfterRender = true;
        handleAnswer(q, "错误");
        save();
        render();
        return;
      }
    }

    if ((isLetter || isNum) && canAnswer && (q.type === "单选" || q.type === "多选")) {
      const letter = isNum ? keys[numericIndex] : typedLetter;
      if (!q.options || !q.options[letter]) return;
      if (q.type === "单选") {
        focusFeedbackAfterRender = true;
        handleAnswer(q, letter);
        save();
        render();
      } else {
        if (!state._pending || state._pending.qid !== q.id) state._pending = {qid: q.id, set: new Set()};
        if (state._pending.set.has(letter)) state._pending.set.delete(letter);
        else state._pending.set.add(letter);
        render();
      }
      return;
    }

    if (q.type === "多选" && event.key === "Enter" && canAnswer && state._pending && state._pending.qid === q.id && state._pending.set.size) {
      const answer = [...state._pending.set].sort().join("");
      state._pending = null;
      focusFeedbackAfterRender = true;
      handleAnswer(q, answer);
      save();
      render();
      return;
    }

    if (event.key === "ArrowLeft") prevQuestion();
    else if (event.key === "ArrowRight" || event.key === " " || event.key === "Enter") {
      event.preventDefault();
      nextQuestion();
  } else if (event.shiftKey && event.key.toLowerCase() === "f") {
      if (state.fav[q.id]) delete state.fav[q.id];
      else state.fav[q.id] = true;
      save();
      render();
    } else if (event.shiftKey && event.key.toLowerCase() === "m") {
      state.mode = "home";
      resetPosition();
      save();
      render();
    }
  });

  let startX = 0;
  let startY = 0;
  let startTime = 0;
  let tracking = false;
  document.addEventListener("touchstart", (event) => {
    if (event.target.closest(".opt, button, input, select, .drawer")) {
      tracking = false;
      return;
    }
    const touch = event.touches[0];
    startX = touch.clientX;
    startY = touch.clientY;
    startTime = Date.now();
    tracking = true;
  }, {passive: true});

  document.addEventListener("touchend", (event) => {
    if (!tracking) return;
    tracking = false;
    const touch = event.changedTouches[0];
    const dx = touch.clientX - startX;
    const dy = touch.clientY - startY;
    if (Math.abs(dx) < 44 || Math.abs(dx) < Math.abs(dy) * 1.2 || Date.now() - startTime > 900) return;
    if (dx < 0) nextQuestion();
    else prevQuestion();
  }, {passive: true});
}

const startupRevisionResetCount = state._revisionResetCount || 0;
delete state._revisionResetCount;
bindGlobalEvents();
render();
if (startupRevisionResetCount) {
  setTimeout(() => alert(`题库已更新：${startupRevisionResetCount} 道修订题的旧作答记录已清除，并重新加入待练。`), 0);
}

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    let reloading = false;
    let reloadForConfirmedUpdate = false;
    navigator.serviceWorker.addEventListener("controllerchange", () => {
      if (!reloadForConfirmedUpdate || reloading) return;
      reloading = true;
      location.reload();
    });
    navigator.serviceWorker.register("./sw.js", {updateViaCache: "none"}).then((registration) => {
      const offerUpdate = (worker) => {
        if (!worker || !navigator.serviceWorker.controller) return;
        if (confirm("发现新版本和新题库，是否立即更新？")) {
          reloadForConfirmedUpdate = true;
          worker.postMessage("SKIP_WAITING");
        }
      };
      if (registration.waiting) offerUpdate(registration.waiting);
      registration.addEventListener("updatefound", () => {
        const worker = registration.installing;
        worker?.addEventListener("statechange", () => {
          if (worker.state === "installed") offerUpdate(worker);
        });
      });
      registration.update().catch(() => {});
    }).catch(() => {
      console.warn("Service Worker 注册失败，离线功能暂不可用。");
    });
  });
}
