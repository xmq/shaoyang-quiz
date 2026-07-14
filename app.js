const QUESTIONS = Array.isArray(window.QUESTIONS) ? window.QUESTIONS : [];
const PUBLIC_QUESTIONS = QUESTIONS;
const QUESTION_MEDIA = window.QUESTION_MEDIA && typeof window.QUESTION_MEDIA === "object" ? window.QUESTION_MEDIA : {};
const BUILD_INFO = window.SHAOYANG_BUILD && typeof window.SHAOYANG_BUILD === "object" ? window.SHAOYANG_BUILD : {id: "development"};
const STORE_KEY = "shaoyang-quiz-v5";
const MOCK_STORE_KEY = "shaoyang-quiz-mock-v1";
const LEGACY_KEYS = ["shaoyang-quiz-v4", "shaoyang-quiz-v3", "shaoyang-quiz-v2", "shaoyang-quiz-v1"];
const STATE_SCHEMA_VERSION = 5;
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
const REVIEW_INTERVAL_DAYS = [1, 3, 7, 14, 30];
const ERROR_TAG_LABELS = Object.freeze({
  concept: "概念不清",
  method: "公式/方法选错",
  condition: "条件漏看",
  calculation: "计算/操作失误",
  recall: "想不起来",
});
const SUBJECT_ORDER = ["信息基础", "计算机基础", "办公软件", "教学论", "多媒体", "编程语言", "算法与数据结构", "计算机组成原理", "操作系统", "数据库", "计算机网络", "软件工程", "信息安全", "电路分析与电工技术", "模拟电子技术", "数字电子技术", "通信原理与高频电子线路", "大数据", "其他"];
const TYPE_ORDER = ["单选", "多选", "判断", "填空", "简答"];
const PROGRESS_FIELDS = ["done", "wrong", "streak", "fav", "flagged", "history", "reviewMeta", "errorTags"];

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

function loadMockSession() {
  const stored = readStore(MOCK_STORE_KEY, null);
  if (!stored || !Array.isArray(stored.ids) || !stored.ids.length || !isRecord(stored.answers)) return null;
  const validIds = new Set(PUBLIC_QUESTIONS.map((question) => question.id));
  const ids = stored.ids.filter((id) => validIds.has(id));
  if (!ids.length || ids.length !== stored.ids.length) return null;
  if (!Number.isFinite(stored.startedAt) || !Number.isFinite(stored.durationMinutes) || stored.durationMinutes <= 0) return null;
  return {
    ids,
    answers: Object.fromEntries(Object.entries(stored.answers).filter(([id]) => validIds.has(id))),
    startedAt: stored.startedAt,
    durationMinutes: stored.durationMinutes,
    subject: String(stored.subject || "全部课程"),
    finishedAt: Number.isFinite(stored.finishedAt) ? stored.finishedAt : null,
    result: isRecord(stored.result) ? stored.result : null,
  };
}

function persistMockSession() {
  try {
    if (mockSession) localStorage.setItem(MOCK_STORE_KEY, JSON.stringify(mockSession));
    else localStorage.removeItem(MOCK_STORE_KEY);
  } catch {}
}

let state = initialState();
applyLaunchParams();
let mockSession = loadMockSession();
let mockTimerId = null;
let saveWarningShown = false;
let drawerReturnFocus = null;
let drawerFiltersDirty = false;
let drawerFilterSnapshot = null;
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
    reviewMeta: {},
    errorTags: {},
    mode: "home",
    subject: "",
    typeFilter: "",
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
  if (q.type === "简答") return given === "掌握";
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
  return q.knowledge_point || q.chapter || q.subject || "未分类";
}

function searchableText(q) {
  const options = q.options ? Object.values(q.options).join(" ") : "";
  return [
    q.id, q.type, q.subject, chapterKey(q), q.source_chapter, q.stem, options,
    q.answer, q.explanation,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

function getScope() {
  let scope = PUBLIC_QUESTIONS;
  if (state.subject) scope = scope.filter((q) => q.subject === state.subject);
  if (state.typeFilter) scope = scope.filter((q) => q.type === state.typeFilter);
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
  if (state.mode === "mock" && mockSession?.ids?.length) {
    const map = Object.fromEntries(PUBLIC_QUESTIONS.map((q) => [q.id, q]));
    return mockSession.ids.map((id) => map[id]).filter(Boolean);
  }
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
      const ids = buildInterleavedIds(pool);
      state._shuffleIds = ids;
      state._shuffled = true;
    }
    const map = Object.fromEntries(pool.map((q) => [q.id, q]));
    pool = (state._shuffleIds || []).map((id) => map[id]).filter(Boolean);
  }
  return pool;
}

function shuffle(items) {
  const result = [...items];
  for (let index = result.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1));
    [result[index], result[swapIndex]] = [result[swapIndex], result[index]];
  }
  return result;
}

function buildInterleavedIds(pool) {
  const groups = new Map();
  pool.forEach((question) => {
    const key = `${question.subject}｜${chapterKey(question)}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(question.id);
  });
  groups.forEach((ids, key) => groups.set(key, shuffle(ids)));
  const result = [];
  let previousKey = "";
  while (result.length < pool.length) {
    const available = [...groups.keys()].filter((key) => groups.get(key).length);
    const candidates = available.length > 1 ? available.filter((key) => key !== previousKey) : available;
    const key = candidates[Math.floor(Math.random() * candidates.length)];
    if (!key) break;
    result.push(groups.get(key).pop());
    previousKey = key;
  }
  return result;
}

function buildReviewPool(scope) {
  return scope
    .filter((q) => !state.flagged[q.id] && (isReviewDue(q.id) || state._stickyId === q.id))
    .sort((a, b) => reviewScore(b) - reviewScore(a))
    .slice(0, 80);
}

function isReviewDue(id, now = Date.now()) {
  const meta = state.reviewMeta[id];
  if (!meta) return !!state.wrong[id];
  const dueAt = Date.parse(meta.nextReviewAt);
  return Number.isFinite(dueAt) && dueAt <= now;
}

function reviewScore(q) {
  const wrong = state.wrong[q.id] || 0;
  const streak = state.streak[q.id] || 0;
  const dueAt = Date.parse(state.reviewMeta[q.id]?.nextReviewAt || "");
  const overdueDays = Number.isFinite(dueAt) ? Math.max(0, Math.floor((Date.now() - dueAt) / 86400000)) : 0;
  return wrong * 100 + Math.max(0, MASTER_THRESHOLD - streak) * 20 + Math.min(overdueDays, 30);
}

function resetPosition() {
  state.cursor = 0;
  state.currentId = null;
  state._stickyId = null;
  state._pending = null;
  state._shuffled = false;
  state._navBack = [];
}

function applyLaunchParams() {
  const params = new URLSearchParams(location.search);
  const requestedMode = params.get("mode");
  const requestedSubject = params.get("subject");
  let changed = false;
  if (["home", "seq", "rnd", "mock", "review", "wrong", "fav"].includes(requestedMode)) {
    state.mode = requestedMode;
    changed = true;
  }
  if (requestedSubject && PUBLIC_QUESTIONS.some((question) => question.subject === requestedSubject)) {
    state.subject = requestedSubject;
    state.typeFilter = "";
    state.chapterFilter = "";
    state.searchQuery = "";
    if (!requestedMode) state.mode = "seq";
    changed = true;
  }
  if (changed) resetPosition();
}

function updateReviewSchedule(id, correct) {
  const now = new Date();
  const previous = state.reviewMeta[id] || {};
  if (!correct) {
    state.reviewMeta[id] = {
      level: 0,
      lastAnsweredAt: now.toISOString(),
      nextReviewAt: now.toISOString(),
      lastCorrect: false,
    };
    return;
  }
  const nextLevel = Math.min(REVIEW_INTERVAL_DAYS.length, Math.max(0, Number(previous.level) || 0) + 1);
  const nextReview = new Date(now.getTime() + REVIEW_INTERVAL_DAYS[nextLevel - 1] * 86400000);
  state.reviewMeta[id] = {
    level: nextLevel,
    lastAnsweredAt: now.toISOString(),
    nextReviewAt: nextReview.toISOString(),
    lastCorrect: true,
  };
}

function handleAnswer(q, given) {
  const active = document.activeElement;
  if (active && active.closest(".options, .multi-actions, .fill-blank, .short-answer") && active.matches(":focus-visible")) {
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
  updateReviewSchedule(q.id, correct);
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

function isMockActive() {
  return state.mode === "mock" && mockSession && !mockSession.finishedAt;
}

function submitAnswer(q, given) {
  if (isMockActive()) {
    mockSession.answers[q.id] = given;
    persistMockSession();
    state._pending = null;
    state.currentId = q.id;
    return;
  }
  handleAnswer(q, given);
}

function announceAnswer(q, correct) {
  const live = $("answer-live");
  if (!live) return;
  live.textContent = "";
  requestAnimationFrame(() => {
    if (q.type === "简答") {
      live.textContent = correct ? "已标记为基本答到，得分点已展开。" : "已标记为还需复习，参考答案已展开。";
      return;
    }
    live.textContent = correct ? "回答正确，解析已展开。" : `回答错误，正确答案是 ${q.answer}，解析已展开。`;
  });
}

function updateSubjectSelect() {
  const select = $("subject-select");
  const counts = countBy(PUBLIC_QUESTIONS, (q) => q.subject);
  const subjects = orderedValues(new Set(Object.keys(counts)), SUBJECT_ORDER);
  select.innerHTML = `<option value="">选择课程</option>` +
    subjects.map((s) => `<option value="${escapeHtml(s)}">${escapeHtml(s)} (${counts[s]})</option>`).join("");
  select.value = state.subject || "";
}

function updateStats() {
  updateSubjectSelect();
  updateCourseModuleLinks();
  renderActiveFilters();
  if ($("search-input").value !== (state.searchQuery || "")) $("search-input").value = state.searchQuery || "";
  const scope = state.subject ? getScope() : [];
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
  $("mini-stat").textContent = state.subject ? `${done}/${scope.length} · ${rate}%${wrongbook ? " · 错" + wrongbook : ""}` : "";
}

function updateCourseModuleLinks() {
  const moduleSelect = $("quiz-module-select");
  const hasLearningContent = Boolean(state.subject && !["信息基础", "计算机基础", "大数据"].includes(state.subject));
  [...moduleSelect.options].forEach((option) => {
    if (option.value !== "quiz") option.disabled = !hasLearningContent;
  });
  moduleSelect.value = "quiz";
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
    ["chapterFilter", "知识点", state.chapterFilter],
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
  const concealResult = isMockActive();
  const pending = state._pending && state._pending.qid === q.id
    ? state._pending.set
    : new Set(concealResult && chosen ? String(chosen).split("") : []);
  const options = optionKeys(q);
  const optsHtml = options.map((letter) => {
    let cls = "opt";
    if (chosen) {
      const answerSet = new Set(String(q.answer || "").split(""));
      const userSet = new Set(String(chosen || "").split(""));
      if (concealResult && userSet.has(letter)) cls += " selected";
      else if (!concealResult && answerSet.has(letter)) cls += " correct";
      else if (!concealResult && userSet.has(letter)) cls += " wrong";
    }
    if (isMulti && pending.has(letter) && !cls.includes("selected")) {
      cls += " selected";
    }
    const pressed = isMulti ? String(pending.has(letter)) : null;
    const disabled = chosen && !concealResult;
    return `<button type="button" class="${cls}" data-letter="${letter}"${pressed === null ? "" : ` aria-pressed="${pressed}"`}${disabled ? " disabled" : ""}>
      <span class="letter">${letter}</span>
      <span class="text">${escapeHtml(q.options[letter])}</span>
    </button>`;
  }).join("");

  const submit = isMulti && (!chosen || concealResult)
    ? `<div class="multi-actions"><button id="submit-multi" class="primary-btn">提交多选答案 (${pending.size})</button></div>`
    : "";
  return `<div class="options">${optsHtml}</div>${submit}`;
}

function renderJudgeQuestion(q, chosen) {
  const concealResult = isMockActive();
  return `<div class="options">${["正确", "错误"].map((value) => {
    let cls = "opt";
    if (chosen) {
      if (concealResult && value === chosen) cls += " selected";
      else if (!concealResult && value === q.answer) cls += " correct";
      else if (!concealResult && value === chosen) cls += " wrong";
    }
    return `<button type="button" class="${cls}" data-judge="${value}"${chosen && !concealResult ? " disabled" : ""}>
      <span class="letter">${value === "正确" ? "✓" : "×"}</span>
      <span class="text">${value}</span>
    </button>`;
  }).join("")}</div>`;
}

function renderFillQuestion(q, chosen) {
  const val = chosen || (state._pending && state._pending.qid === q.id ? state._pending.text : "");
  const cls = chosen && !isMockActive() ? (isAnswerCorrect(q, chosen) ? "correct" : "wrong") : "";
  const editable = !chosen || isMockActive();
  return `<div class="fill-blank">
    <input id="fill-input" class="${cls}" value="${escapeHtml(val)}" placeholder="输入答案..." ${editable ? "" : "disabled"}>
    ${editable ? `<button id="submit-fill" class="primary-btn">${chosen ? "更新答案" : "提交"}</button>${isMockActive() ? "" : '<button id="show-fill" class="secondary-btn">查看答案</button>'}` : ""}
  </div>`;
}

function renderShortAnswerQuestion(q, chosen) {
  const pending = state._pending && state._pending.qid === q.id ? state._pending : null;
  const draft = pending && typeof pending.text === "string" ? pending.text : "";
  const revealed = !!pending?.revealed;
  if (chosen) {
    return `<div class="short-answer short-graded">
      <strong>${chosen === "掌握" ? "已自评：基本答到" : "已自评：还需复习"}</strong>
      <span>已按参考得分点记录自评结果。</span>
    </div>`;
  }
  return `<div class="short-answer ${revealed ? "is-revealed" : ""}">
    <label for="short-input">作答要点</label>
    <textarea id="short-input" rows="6" placeholder="写出你的作答要点"${revealed ? " disabled" : ""}>${escapeHtml(draft)}</textarea>
    ${revealed ? `<div class="short-reference">
        <div class="exp-title">参考得分点</div>
        <p>${escapeHtml(q.answer)}</p>
        ${q.explanation ? `<div class="short-rubric"><strong>核对说明</strong>${escapeHtml(q.explanation)}</div>` : ""}
      </div>
      <div class="short-grade-actions" aria-label="简答题自评">
        <button type="button" class="primary-btn" data-short-grade="掌握">基本答到</button>
        <button type="button" class="secondary-btn" data-short-grade="未掌握">还需复习</button>
      </div>` : `<div class="short-draft-actions">
        <button type="button" id="show-short" class="primary-btn">核对参考答案</button>
      </div>`}
  </div>`;
}

function courseNameForSubject(subject) {
  return ({
    "办公软件": "Office软件操作",
    "教学论": "信息技术与教学论",
    "多媒体": "多媒体技术",
    "算法与数据结构": "数据结构与算法",
    "操作系统": "操作系统原理",
    "数据库": "数据库技术",
  })[subject] || subject;
}

function feedbackHtml(q, chosen) {
  if (!chosen) return "";
  if (isMockActive()) {
    return `<div class="mock-answer-saved" role="status">答案已记录；交卷后统一显示得分和解析。</div>`;
  }
  const ok = isAnswerCorrect(q, chosen);
  const isShort = q.type === "简答";
  const wrongCount = state.wrong[q.id] || 0;
  const streak = state.streak[q.id] || 0;
  const remain = Math.max(0, MASTER_THRESHOLD - streak);
  const grade = wrongGrade(wrongCount);
  const badge = wrongCount ? ` · ${isShort ? "需复习" : "已错"} ${wrongCount} 次${ok && remain ? ` · 还需连续答对 ${remain} 次出本` : ""}${grade ? `<span class="wrong-grade">${grade}</span>` : ""}` : "";
  const answer = `答案：${q.answer}`;
  const referenceAnswer = isShort
    ? `<div class="short-reference feedback-reference"><div class="exp-title">参考得分点</div><p>${escapeHtml(q.answer)}</p></div>`
    : "";
  const explanation = q.explanation && q.explanation.trim()
    ? `<div class="explanation"><div class="exp-title">解析</div>${escapeHtml(q.explanation)}</div>`
    : `<div class="explanation">本题暂无文字解析</div>`;
  const reviewMeta = state.reviewMeta[q.id];
  const reviewMessage = ok && reviewMeta?.nextReviewAt
    ? `已安排 ${new Date(reviewMeta.nextReviewAt).toLocaleDateString("zh-CN", {month: "numeric", day: "numeric"})} 再次练习`
    : "已加入待复习队列";
  const selectedErrorTag = state.errorTags[q.id] || "";
  const errorTagButtons = !ok
    ? `<div class="error-reflection">
        <strong>这次错在哪里？</strong>
        <span>选一个最主要原因，方便下次有针对性地修正。</span>
        <div>${Object.entries(ERROR_TAG_LABELS).map(([value, label]) => `<button type="button" data-error-tag="${value}" aria-pressed="${selectedErrorTag === value}">${label}</button>`).join("")}</div>
      </div>`
    : "";
  const courseHash = `#course=${encodeURIComponent(courseNameForSubject(q.subject))}`;
  const repairLinks = ok ? "" : `<div class="repair-links">
    <span>${reviewMessage}</span>
    <a href="./notes.html${courseHash}">回看讲义</a>
    <a href="./color-notes.html${courseHash}">三色笔记</a>
  </div>`;
  return `<div class="feedback" role="status" aria-live="polite" tabindex="-1">
    <div class="feedback-label ${ok ? "ok" : "ng"}">${isShort ? (ok ? "✓ 已自评为基本答到" : "× 已标记为还需复习") : (ok ? "✓ 正确" : "× 错误，" + answer)}${badge}</div>
    ${referenceAnswer}
    ${explanation}
    ${errorTagButtons}
    ${repairLinks}
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
  const chosen = isMockActive()
    ? mockSession.answers[q.id]
    : (inWrongFresh ? null : state.done[q.id]);
  const isFav = !!state.fav[q.id];
  const isFlagged = !!state.flagged[q.id];
  const canGoBack = isMockActive() ? state.cursor > 0 : Boolean(state._navBack && state._navBack.length);
  let body = "";

  if (q.type === "单选" || q.type === "多选") body = renderChoiceQuestion(q, chosen, inWrongFresh);
  else if (q.type === "判断") body = renderJudgeQuestion(q, chosen);
  else if (q.type === "填空") body = renderFillQuestion(q, chosen);
  else if (q.type === "简答") body = renderShortAnswerQuestion(q, chosen);

  $("card-area").innerHTML = `<article class="card" aria-labelledby="question-stem">
    <div class="meta">
      <span class="badge type-${escapeHtml(q.type)}">${escapeHtml(q.type)}</span>
      <span class="q-pos">${state.cursor + 1} / ${pool.length}</span>
      <div class="question-controls" aria-label="题目导航">
        <button type="button" id="question-exit">返回</button>
        <button type="button" id="prev" aria-label="上一题"${canGoBack ? "" : " disabled"}>←</button>
        <button type="button" class="fav ${isFav ? "active" : ""}" id="fav" aria-label="收藏" aria-pressed="${isFav}">${isFav ? "★" : "☆"}</button>
        <button type="button" class="next ${chosen ? "ready" : ""}" id="next">${chosen ? "下一题" : "跳过"}</button>
      </div>
      <span class="chapter">${escapeHtml(q.knowledge_point || q.chapter || "")}</span>
    </div>
    <div class="stem" id="question-stem" tabindex="-1">${escapeHtml(q.stem)}</div>
    ${mediaHtml(q)}
    ${body}
    ${feedbackHtml(q, chosen)}
    ${isMockActive() ? "" : `<div class="question-tools" aria-label="题目工具">
      <button class="flag ${isFlagged ? "active" : ""}" id="flag" aria-pressed="${isFlagged}">${isFlagged ? "已标记有误" : "题目有误"}</button>
      ${chosen ? '<button id="redo">重新作答</button>' : ""}
    </div>`}
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
      stem?.focus({preventScroll: true});
    });
  }
}

function bindQuestionEvents(q, inWrongFresh) {
  const canAnswer = isMockActive() ? true : (!state.done[q.id] || inWrongFresh);
  document.querySelectorAll("[data-letter]").forEach((el) => {
    el.addEventListener("click", () => {
      if (!canAnswer) return;
      const letter = el.dataset.letter;
      if (q.type === "单选") {
        submitAnswer(q, letter);
        save();
        render();
      } else {
        if (!state._pending || state._pending.qid !== q.id) {
          state._pending = {qid: q.id, set: new Set(isMockActive() && mockSession.answers[q.id] ? String(mockSession.answers[q.id]).split("") : [])};
        }
        if (state._pending.set.has(letter)) state._pending.set.delete(letter);
        else state._pending.set.add(letter);
        render();
      }
    });
  });

  document.querySelectorAll("[data-judge]").forEach((el) => {
    el.addEventListener("click", () => {
      if (!canAnswer) return;
      submitAnswer(q, el.dataset.judge);
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
      submitAnswer(q, answer);
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
      submitAnswer(q, value);
      save();
      render();
    });
  }
  if (showFill) {
    showFill.addEventListener("click", () => {
      submitAnswer(q, "【放弃】");
      save();
      render();
    });
  }

  const shortInput = $("short-input");
  const showShort = $("show-short");
  if (shortInput && !shortInput.disabled) {
    shortInput.addEventListener("input", () => {
      state._pending = {qid: q.id, text: shortInput.value, revealed: false};
    });
  }
  if (showShort) {
    showShort.addEventListener("click", () => {
      state._pending = {qid: q.id, text: shortInput?.value || "", revealed: true};
      render();
    });
  }
  document.querySelectorAll("[data-short-grade]").forEach((button) => {
    button.addEventListener("click", () => {
      state._pending = null;
      submitAnswer(q, button.dataset.shortGrade);
      save();
      render();
    });
  });

  $("prev").addEventListener("click", prevQuestion);
  $("next").addEventListener("click", nextQuestion);
  $("question-exit").addEventListener("click", exitRunner);
  $("fav").addEventListener("click", () => {
    if (state.fav[q.id]) delete state.fav[q.id];
    else state.fav[q.id] = true;
    save();
    render();
  });
  $("flag")?.addEventListener("click", () => {
    if (state.flagged[q.id]) delete state.flagged[q.id];
    else state.flagged[q.id] = new Date().toISOString();
    save();
    render();
  });

  const redo = $("redo");
  if (redo) {
    redo.addEventListener("click", () => {
      if (isMockActive()) delete mockSession.answers[q.id];
      else delete state.done[q.id];
      state._pending = null;
      save();
      render();
    });
  }

  document.querySelectorAll("[data-error-tag]").forEach((button) => {
    button.addEventListener("click", () => {
      state.errorTags[q.id] = button.dataset.errorTag;
      save();
      render();
    });
  });
}

function renderEmpty() {
  let title = "当前条件下题目已全部刷完";
  let text = "可以切换科目、题型、章节，或进入错题本继续练。";
  if (state.searchQuery) {
    title = "没有找到匹配题目";
    text = "换个关键词，或清空科目、题型、章节筛选后再搜。";
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
    title = "暂无到期复习";
    text = "作答后系统会按间隔安排再次练习；标记有问题的题会暂停复习，等待核对。";
  }
  $("card-area").innerHTML = `<div class="card empty"><strong>${title}</strong>${text}</div>`;
}

function renderDashboard() {
  updateStats();
  updateModeTabs();
  const scope = getScope();
  const wrongCount = scope.filter((question) => state.wrong[question.id]).length;
  const favCount = scope.filter((question) => state.fav[question.id]).length;
  const reviewCount = buildReviewPool(scope).length;
  const hasReviewTasks = Boolean(state.subject && (reviewCount || wrongCount || favCount));

  const activeMock = mockSession && !mockSession.finishedAt;
  const remainingMinutes = activeMock ? Math.max(0, Math.ceil(mockRemainingMs() / 60000)) : 0;

  $("card-area").innerHTML = `<section class="dashboard quiz-hub-dashboard">
    <header class="hub-heading">
      <h1>刷题</h1>
    </header>
    ${activeMock ? `<button type="button" class="resume-mock" data-resume-mock>
      <span><strong>继续模拟考试</strong><small>${escapeHtml(mockSession.subject)} · 已答 ${Object.keys(mockSession.answers).length}/${mockSession.ids.length}</small></span>
      <b>约 ${remainingMinutes} 分钟 →</b>
    </button>` : ""}
    <article class="card hub-tasks">
      <div class="hub-primary-actions">
        <button class="primary mode-card" data-jump-mode="seq">
          <span class="mode-symbol" aria-hidden="true">顺</span>
          <span class="mode-copy"><strong>顺序刷题</strong><small>按知识点依次练习</small></span>
          <span class="mode-arrow" aria-hidden="true">→</span>
        </button>
        <button class="mode-card" data-jump-mode="rnd">
          <span class="mode-symbol" aria-hidden="true">随</span>
          <span class="mode-copy"><strong>随机刷题</strong><small>打乱题序，交叉检验</small></span>
          <span class="mode-arrow" aria-hidden="true">→</span>
        </button>
        <button class="mode-card" data-jump-mode="mock">
          <span class="mode-symbol" aria-hidden="true">考</span>
          <span class="mode-copy"><strong>模拟考试</strong><small>计时组卷，交卷后判分</small></span>
          <span class="mode-arrow" aria-hidden="true">→</span>
        </button>
      </div>
    </article>
    ${hasReviewTasks ? `<article class="card hub-review">
      <div class="hub-review-actions">
        ${reviewCount ? `<button data-jump-mode="review"><span>到期复习</span><b>${reviewCount}</b></button>` : ""}
        ${wrongCount ? `<button data-jump-mode="wrong"><span>错题本</span><b>${wrongCount}</b></button>` : ""}
        ${favCount ? `<button data-jump-mode="fav"><span>收藏题</span><b>${favCount}</b></button>` : ""}
      </div>
    </article>` : ""}
  </section>`;

  document.querySelectorAll("[data-jump-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      const mode = button.dataset.jumpMode;
      if (!state.subject && ["seq", "rnd", "mock"].includes(mode)) {
        $("subject-select").focus();
        $("subject-select").classList.add("needs-subject");
        window.setTimeout(() => $("subject-select").classList.remove("needs-subject"), 900);
        return;
      }
      state.mode = mode;
      resetPosition();
      focusQuestionAfterRender = true;
      save();
      render();
    });
  });
  document.querySelector("[data-resume-mock]")?.addEventListener("click", () => {
    state.mode = "mock";
    const nextId = mockSession.ids.find((id) => mockSession.answers[id] === undefined) || mockSession.ids[0];
    state.currentId = nextId;
    state.cursor = Math.max(0, mockSession.ids.indexOf(nextId));
    state._navBack = [];
    save();
    render();
  });
}

function availableMockQuestions() {
  if (!state.subject) return [];
  return PUBLIC_QUESTIONS.filter((question) => {
    if (question.type === "简答" || state.flagged[question.id]) return false;
    return question.subject === state.subject;
  });
}

function buildMockIds(scope, count) {
  const groups = new Map();
  scope.forEach((question) => {
    if (!groups.has(question.type)) groups.set(question.type, []);
    groups.get(question.type).push(question.id);
  });
  groups.forEach((ids, key) => groups.set(key, shuffle(ids)));
  const preferred = ["单选", "判断", "多选", "填空"];
  const result = [];
  while (result.length < count) {
    let added = false;
    for (const type of preferred) {
      const ids = groups.get(type);
      if (!ids?.length || result.length >= count) continue;
      result.push(ids.pop());
      added = true;
    }
    if (!added) break;
  }
  return shuffle(result);
}

function clearMockTimer() {
  if (mockTimerId) window.clearInterval(mockTimerId);
  mockTimerId = null;
}

function mockRemainingMs() {
  if (!mockSession) return 0;
  return mockSession.durationMinutes * 60000 - (Date.now() - mockSession.startedAt);
}

function updateMockClock() {
  if (!isMockActive()) {
    clearMockTimer();
    return;
  }
  const remaining = Math.max(0, mockRemainingMs());
  const clock = $("mock-clock");
  if (clock) {
    const totalSeconds = Math.ceil(remaining / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = String(totalSeconds % 60).padStart(2, "0");
    clock.textContent = `${minutes}:${seconds}`;
    clock.classList.toggle("is-urgent", remaining <= 5 * 60000);
  }
  if (remaining <= 0) finishMock(true);
}

function ensureMockTimer() {
  if (mockTimerId || !isMockActive()) return;
  mockTimerId = window.setInterval(updateMockClock, 1000);
  updateMockClock();
}

function startMock(count) {
  if (!state.subject) {
    alert("请先选择课程");
    return;
  }
  const scope = availableMockQuestions();
  const actualCount = Math.min(count, scope.length);
  if (!actualCount) {
    alert("当前课程没有可用于模拟的客观题，请换一个课程或清除筛选。");
    return;
  }
  const durationMinutes = Math.max(20, Math.ceil(actualCount * 1.5));
  mockSession = {
    ids: buildMockIds(scope, actualCount),
    answers: {},
    startedAt: Date.now(),
    durationMinutes,
    subject: state.subject,
    finishedAt: null,
    result: null,
  };
  state._pending = null;
  state.currentId = mockSession.ids[0] || null;
  state.cursor = 0;
  state._navBack = [];
  persistMockSession();
  save();
  render();
}

function finishMock(autoSubmitted = false) {
  if (!mockSession || mockSession.finishedAt) return;
  const map = Object.fromEntries(PUBLIC_QUESTIONS.map((question) => [question.id, question]));
  const answers = {...mockSession.answers};
  const rows = mockSession.ids.map((id) => ({question: map[id], answer: answers[id]})).filter((row) => row.question);
  const answered = rows.filter((row) => row.answer !== undefined);
  const correct = answered.filter((row) => isAnswerCorrect(row.question, row.answer)).length;
  const weakAbilities = {};
  rows.filter((row) => row.answer === undefined || !isAnswerCorrect(row.question, row.answer)).forEach(({question}) => {
    const ability = question.ability || "待归类";
    weakAbilities[ability] = (weakAbilities[ability] || 0) + 1;
  });
  mockSession.finishedAt = Date.now();
  mockSession.result = {
    answered: answered.length,
    correct,
    total: rows.length,
    score: rows.length ? Math.round(correct * 100 / rows.length) : 0,
    autoSubmitted,
    weakAbilities,
  };
  persistMockSession();
  clearMockTimer();
  answered.forEach(({question, answer}) => handleAnswer(question, answer));
  rows.filter((row) => row.answer === undefined).forEach(({question}) => {
    state.wrong[question.id] = (state.wrong[question.id] || 0) + 1;
    state.streak[question.id] = 0;
    updateReviewSchedule(question.id, false);
  });
  save();
  render();
}

function renderMockSetup() {
  updateStats();
  updateModeTabs();
  const scope = availableMockQuestions();
  const choices = [20, 30, 50].filter((count) => count <= scope.length);
  if (scope.length && !choices.length) choices.push(scope.length);
  $("card-area").innerHTML = `<section class="mock-setup card">
    <div class="mock-setup-heading"><h2>${state.subject ? "选择题量" : "请先选择课程"}</h2>${state.subject ? `<span>可抽 ${scope.length} 题</span>` : ""}</div>
    <div class="mock-choices">
      ${choices.map((count) => `<button type="button" data-mock-count="${count}"><strong>${count}题</strong><span>${Math.max(20, Math.ceil(count * 1.5))}分钟</span></button>`).join("")}
    </div>
    ${state.subject && !scope.length ? '<div class="empty">当前课程没有可抽取的客观题。</div>' : ""}
  </section>`;
  document.querySelectorAll("[data-mock-count]").forEach((button) => {
    button.addEventListener("click", () => startMock(Number(button.dataset.mockCount)));
  });
}

function renderMockResult() {
  updateStats();
  updateModeTabs();
  const result = mockSession.result;
  const questionMap = Object.fromEntries(PUBLIC_QUESTIONS.map((question) => [question.id, question]));
  const reviewRows = mockSession.ids.map((id, index) => ({
    index,
    question: questionMap[id],
    answer: mockSession.answers[id],
  })).filter(({question, answer}) => question && (answer === undefined || !isAnswerCorrect(question, answer)));
  const weak = Object.entries(result.weakAbilities || {})
    .sort((a, b) => b[1] - a[1])
    .map(([ability, count]) => `<span>${escapeHtml(ability)} <b>${count}</b></span>`)
    .join("");
  $("card-area").innerHTML = `<section class="mock-result card">
    <h2>考试结果</h2>
    <div class="mock-score"><strong>${result.score}</strong><span>分</span></div>
    <div class="mock-result-grid">
      <div><strong>${result.correct}</strong><span>答对</span></div>
      <div><strong>${result.answered}</strong><span>已答</span></div>
      <div><strong>${result.total - result.answered}</strong><span>未答</span></div>
      <div><strong>${result.total}</strong><span>总题数</span></div>
    </div>
    ${result.autoSubmitted ? '<p class="mock-notice">时间到，系统已自动交卷。</p>' : ""}
    ${weak ? `<div class="mock-weak"><strong>失分能力类型</strong>${weak}</div>` : '<p class="mock-notice success">本卷全部答对。</p>'}
    ${reviewRows.length ? `<details class="mock-review">
      <summary>查看本卷错题与解析（${reviewRows.length}）</summary>
      <div class="mock-review-list">${reviewRows.map(({index, question, answer}) => `<article>
        <strong>${index + 1}. ${escapeHtml(question.stem)}</strong>
        <p><span>你的答案</span>${answer === undefined ? "未作答" : escapeHtml(answer)}</p>
        <p><span>正确答案</span>${escapeHtml(question.answer)}</p>
        ${question.explanation ? `<p><span>解析</span>${escapeHtml(question.explanation)}</p>` : ""}
      </article>`).join("")}</div>
    </details>` : ""}
    <div class="dash-actions">
      <button class="primary" id="mock-new">再来一套</button>
      <button id="mock-wrong">查看错题本</button>
    </div>
  </section>`;
  $("mock-new").addEventListener("click", () => {
    mockSession = null;
    persistMockSession();
    resetPosition();
    render();
  });
  $("mock-wrong").addEventListener("click", () => {
    state.mode = "wrong";
    resetPosition();
    save();
    render();
  });
}

function renderMock() {
  if (!mockSession) {
    renderMockSetup();
    return;
  }
  if (mockSession.finishedAt) {
    renderMockResult();
    return;
  }
  updateStats();
  updateModeTabs();
  const pool = getPool();
  let question = state.currentId ? pool.find((item) => item.id === state.currentId) : null;
  if (!question) question = pool[0];
  if (!question) {
    mockSession = null;
    renderMockSetup();
    return;
  }
  state.currentId = question.id;
  state.cursor = pool.indexOf(question);
  renderQuestion(question, pool);
  const answered = Object.keys(mockSession.answers).length;
  $("card-area").insertAdjacentHTML("afterbegin", `<section class="mock-toolbar" aria-label="模拟进度">
    <div><span>模拟进度</span><strong>${answered} / ${mockSession.ids.length}</strong></div>
    <div><span>剩余时间</span><strong id="mock-clock">--:--</strong></div>
    <button type="button" class="mock-sheet-button" id="mock-sheet-toggle" aria-controls="mock-answer-sheet" aria-expanded="false">答题卡</button>
    <button type="button" class="mock-finish-button" id="mock-finish">交卷</button>
  </section>
  <section class="mock-answer-sheet" id="mock-answer-sheet" aria-label="模拟答题卡" hidden>
    <div class="mock-sheet-head"><strong>答题卡</strong><span>点题号可跳转；已答题仍可修改</span></div>
    <div class="mock-sheet-grid">${mockSession.ids.map((id, index) => `<button type="button" data-mock-id="${escapeHtml(id)}" class="${id === question.id ? "current " : ""}${mockSession.answers[id] !== undefined ? "answered" : ""}" aria-label="第 ${index + 1} 题${mockSession.answers[id] !== undefined ? "，已作答" : "，未作答"}"${id === question.id ? ' aria-current="true"' : ""}>${index + 1}</button>`).join("")}</div>
  </section>`);
  $("mock-sheet-toggle").addEventListener("click", () => {
    const sheet = $("mock-answer-sheet");
    sheet.hidden = !sheet.hidden;
    $("mock-sheet-toggle").setAttribute("aria-expanded", String(!sheet.hidden));
  });
  document.querySelectorAll("[data-mock-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.currentId = button.dataset.mockId;
      state.cursor = Math.max(0, mockSession.ids.indexOf(state.currentId));
      state._pending = null;
      state._navBack = [];
      focusQuestionAfterRender = true;
      save();
      render();
    });
  });
  $("mock-finish").addEventListener("click", () => {
    const unanswered = mockSession.ids.length - Object.keys(mockSession.answers).length;
    if (unanswered && !confirm(`还有 ${unanswered} 道未作答，确定交卷吗？`)) return;
    finishMock(false);
  });
  ensureMockTimer();
}

function updateViewState() {
  const isHub = state.mode === "home";
  const isQuestionActive = !isHub && (state.mode !== "mock" || isMockActive());
  document.body.classList.toggle("quiz-hub", isHub);
  document.body.classList.toggle("quiz-runner", !isHub);
  document.body.classList.toggle("quiz-question-active", isQuestionActive);
  document.body.classList.toggle("quiz-mock-active", !!isMockActive());
  const labels = {
    seq: "顺序刷题",
    rnd: "随机刷题",
    review: "到期复习",
    wrong: "错题本",
    fav: "收藏题",
    mock: "模拟考试",
  };
  if ($("runner-title")) $("runner-title").textContent = labels[state.mode] || "练习";
  if ($("runner-scope")) $("runner-scope").textContent = isMockActive() ? mockSession.subject : (state.subject || "全部课程");
}

function render() {
  updateViewState();
  if (!PUBLIC_QUESTIONS.length) {
    $("card-area").innerHTML = `<div class="card empty"><strong>题库未加载</strong>请确认 questions.js 与 app.js 在同一目录。</div>`;
    return;
  }

  const canShowStoredMock = state.mode === "mock" && Boolean(mockSession);
  if (!state.subject && state.mode !== "home" && !canShowStoredMock) {
    state.mode = "home";
    resetPosition();
    save();
    updateViewState();
  }

  if (state.mode === "home") {
    renderDashboard();
    return;
  }

  if (state.mode === "mock") {
    renderMock();
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
  if (isMockActive()) {
    const pool = getPool();
    const index = pool.findIndex((question) => question.id === state.currentId);
    if (index <= 0) return;
    state.currentId = pool[index - 1].id;
    state.cursor = index - 1;
    focusQuestionAfterRender = true;
    save();
    render();
    return;
  }
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
  const typeBase = state.subject ? PUBLIC_QUESTIONS.filter((q) => q.subject === state.subject) : PUBLIC_QUESTIONS;
  const typeCounts = countBy(typeBase, (q) => q.type);
  const types = [{value: "", label: "全部题型", count: typeBase.length}].concat(
    orderedValues(new Set(Object.keys(typeCounts)), TYPE_ORDER).map((t) => ({value: t, label: t, count: typeCounts[t]}))
  );
  renderDrawerList($("drawer-types"), types, state.typeFilter || "", (value) => {
    state.typeFilter = value;
    state.chapterFilter = "";
    drawerFiltersDirty = true;
    save();
    buildDrawer();
  });

  let chapterBase = PUBLIC_QUESTIONS;
  if (state.subject) chapterBase = chapterBase.filter((q) => q.subject === state.subject);
  if (state.typeFilter) chapterBase = chapterBase.filter((q) => q.type === state.typeFilter);
  const chapterCounts = countBy(chapterBase, chapterKey);
  const chapters = [{value: "", label: "全部知识点", count: chapterBase.length}].concat(
    Object.keys(chapterCounts)
      .sort((a, b) => a.localeCompare(b, "zh-CN", {numeric: true}))
      .map((chapter) => ({value: chapter, label: chapter, count: chapterCounts[chapter]}))
  );
  renderDrawerList($("drawer-chapters"), chapters, state.chapterFilter || "", (value) => {
    state.chapterFilter = value;
    drawerFiltersDirty = true;
    save();
    buildDrawer();
  });
}

function openDrawer() {
  drawerFiltersDirty = false;
  drawerFilterSnapshot = {
    typeFilter: state.typeFilter,
    chapterFilter: state.chapterFilter,
    searchQuery: state.searchQuery,
  };
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

function closeDrawer({apply = false, restoreFocus = true} = {}) {
  const wasOpen = $("drawer").classList.contains("show");
  const applyFilters = wasOpen && drawerFiltersDirty && apply;
  if (wasOpen && drawerFiltersDirty && !apply && drawerFilterSnapshot) {
    state.typeFilter = drawerFilterSnapshot.typeFilter;
    state.chapterFilter = drawerFilterSnapshot.chapterFilter;
    state.searchQuery = drawerFilterSnapshot.searchQuery;
    $("search-input").value = state.searchQuery || "";
    save();
  }
  $("drawer").classList.remove("show");
  $("drawer-mask").classList.remove("show");
  $("drawer").setAttribute("aria-hidden", "true");
  $("drawer").inert = true;
  $("drawer-toggle").setAttribute("aria-expanded", "false");
  $("app-main").inert = false;
  document.body.classList.remove("drawer-open");
  if (wasOpen && restoreFocus && drawerReturnFocus && document.contains(drawerReturnFocus)) {
    drawerReturnFocus.focus();
  }
  drawerReturnFocus = null;
  drawerFiltersDirty = false;
  drawerFilterSnapshot = null;
  if (applyFilters) {
    resetPosition();
    save();
    render();
  }
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
  const map = Object.fromEntries(PUBLIC_QUESTIONS.map((q) => [q.id, q]));
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
  const map = Object.fromEntries(PUBLIC_QUESTIONS.map((q) => [q.id, q]));
  const rows = ids.map((id) => ({id, q: map[id], markedAt: state.flagged[id]})).filter((row) => row.q);
  let text = `纠错标记导出 · ${new Date().toLocaleString("zh-CN")}\n共 ${rows.length} 道\n\n`;
  rows.forEach(({id, q, markedAt}, index) => {
    text += `${index + 1}. [${markedAt}] ${q.stem}\n`;
    text += `   ID：${id}\n`;
    text += `   题型：${q.type} / ${q.subject} / ${chapterKey(q)}\n`;
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
  const questionMap = new Map(PUBLIC_QUESTIONS.map((q) => [q.id, q]));
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
    if (question.type === "简答") return value === "掌握" || value === "未掌握";
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
  clean.reviewMeta = Object.fromEntries(entries("reviewMeta").filter(([, value]) => {
    if (!isRecord(value)) return false;
    const level = Number(value.level);
    return Number.isInteger(level) && level >= 0 && level <= REVIEW_INTERVAL_DAYS.length
      && typeof value.lastAnsweredAt === "string" && Number.isFinite(Date.parse(value.lastAnsweredAt))
      && typeof value.nextReviewAt === "string" && Number.isFinite(Date.parse(value.nextReviewAt))
      && typeof value.lastCorrect === "boolean";
  }).map(([id, value]) => [id, {
    level: Number(value.level),
    lastAnsweredAt: value.lastAnsweredAt,
    nextReviewAt: value.nextReviewAt,
    lastCorrect: value.lastCorrect,
  }]));
  clean.errorTags = Object.fromEntries(entries("errorTags")
    .filter(([, value]) => typeof value === "string" && Object.prototype.hasOwnProperty.call(ERROR_TAG_LABELS, value)));

  if (["home", "seq", "rnd", "mock", "review", "wrong", "fav"].includes(input.mode)) clean.mode = input.mode;
  const allowedSubjects = new Set(PUBLIC_QUESTIONS.map((q) => q.subject));
  const allowedTypes = new Set(PUBLIC_QUESTIONS.map((q) => q.type));
  if (typeof input.subject === "string" && (!input.subject || allowedSubjects.has(input.subject))) clean.subject = input.subject;
  if (typeof input.typeFilter === "string" && (!input.typeFilter || allowedTypes.has(input.typeFilter))) clean.typeFilter = input.typeFilter;
  if (typeof input.chapterFilter === "string" && input.chapterFilter.length <= 300
      && (!input.chapterFilter || PUBLIC_QUESTIONS.some((question) => chapterKey(question) === input.chapterFilter))) {
    clean.chapterFilter = input.chapterFilter;
  }
  if (typeof input.searchQuery === "string" && input.searchQuery.length <= 300) clean.searchQuery = input.searchQuery;
  if (typeof input.currentId === "string" && questionMap.has(input.currentId)) clean.currentId = input.currentId;
  if (Number.isInteger(input.cursor) && input.cursor >= 0 && input.cursor < PUBLIC_QUESTIONS.length) clean.cursor = input.cursor;
  return clean;
}

function applyQuestionRevisionResets(clean, storedRevisions = {}) {
  let resetCount = 0;
  for (const [id, revision] of Object.entries(QUESTION_REVISIONS)) {
    if (storedRevisions[id] === revision) continue;
    const hadProgress = ["done", "wrong", "streak", "history", "reviewMeta", "errorTags"].some((key) => Object.prototype.hasOwnProperty.call(clean[key], id));
    for (const key of ["done", "wrong", "streak", "history", "reviewMeta", "errorTags"]) delete clean[key][id];
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

function exitRunner() {
  if (isMockActive() && !confirm("模拟考试仍在计时，返回刷题主页？稍后可以继续作答。")) return;
  if (!isMockActive() && state._pending?.text && !confirm("当前输入尚未提交，确定返回吗？")) return;
  state.mode = "home";
  state._pending = null;
  clearMockTimer();
  save();
  render();
}

function bindGlobalEvents() {
  $("drawer-toggle").addEventListener("click", openDrawer);
  $("drawer-close").addEventListener("click", closeDrawer);
  $("drawer-mask").addEventListener("click", closeDrawer);
  window.addEventListener("pageshow", () => closeDrawer({restoreFocus: false}));

  $("quiz-module-select").addEventListener("change", (event) => {
    const module = event.target.value;
    event.target.value = "quiz";
    if (module === "quiz") return;
    if (!state.subject) {
      $("subject-select").focus();
      return;
    }
    const course = courseNameForSubject(state.subject);
    const target = module === "lecture" ? "notes.html" : "color-notes.html";
    location.href = `./${target}#course=${encodeURIComponent(course)}`;
  });

  $("subject-select").addEventListener("change", (event) => {
    state.subject = event.target.value;
    state.typeFilter = "";
    state.chapterFilter = "";
    state.searchQuery = "";
    $("search-input").value = "";
    try {
      if (state.subject) localStorage.setItem("shaoyang-selected-course-v1", courseNameForSubject(state.subject));
    } catch {}
    resetPosition();
    save();
    render();
  });

  $("search-input").addEventListener("input", (event) => {
    state.searchQuery = event.target.value;
    drawerFiltersDirty = true;
    save();
  });
  $("clear-search").addEventListener("click", () => {
    state.searchQuery = "";
    $("search-input").value = "";
    drawerFiltersDirty = true;
    save();
  });

  $("drawer-reset-filters").addEventListener("click", () => {
    state.typeFilter = "";
    state.chapterFilter = "";
    state.searchQuery = "";
    $("search-input").value = "";
    drawerFiltersDirty = true;
    save();
    buildDrawer();
  });
  $("drawer-apply").addEventListener("click", () => {
    closeDrawer({apply: true});
  });

  $("runner-exit").addEventListener("click", exitRunner);

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
    mockSession = null;
    persistMockSession();
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
    const canAnswer = isMockActive() ? true : (!state.done[q.id] || inWrongFresh);
    const keys = optionKeys(q);
    const typedLetter = event.key.length === 1 ? event.key.toUpperCase() : "";
    const numericIndex = /^\d$/.test(event.key) ? Number(event.key) - 1 : -1;
    const isLetter = keys.includes(typedLetter);
    const isNum = numericIndex >= 0 && numericIndex < keys.length;

    if (q.type === "判断" && canAnswer) {
      if (event.key === "1" || event.key === "t" || event.key === "T" || event.key === "√") {
        focusFeedbackAfterRender = true;
        submitAnswer(q, "正确");
        save();
        render();
        return;
      }
      if (event.key === "0" || event.key === "f" || event.key === "F" || event.key === "×") {
        focusFeedbackAfterRender = true;
        submitAnswer(q, "错误");
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
        submitAnswer(q, letter);
        save();
        render();
      } else {
        if (!state._pending || state._pending.qid !== q.id) {
          state._pending = {qid: q.id, set: new Set(isMockActive() && mockSession.answers[q.id] ? String(mockSession.answers[q.id]).split("") : [])};
        }
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
      submitAnswer(q, answer);
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
