const QUESTIONS = Array.isArray(window.QUESTIONS) ? window.QUESTIONS : [];
const STORE_KEY = "shaoyang-quiz-v3";
const LEGACY_KEYS = ["shaoyang-quiz-v2", "shaoyang-quiz-v1"];
const MASTER_THRESHOLD = 2;
const SUBJECT_ORDER = ["信息基础", "计算机基础", "操作系统", "计算机网络", "数据库", "办公软件", "多媒体", "编程语言", "算法与数据结构", "信息安全", "教学论", "其他"];
const TYPE_ORDER = ["单选", "多选", "判断", "填空"];
const SOURCE_ORDER = ["题海训练", "超格", "中公", "德阳", "网络"];

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
  let state = readStore(STORE_KEY, null);
  if (!state) {
    state = {};
    for (const key of LEGACY_KEYS) {
      const legacy = readStore(key, null);
      if (legacy) {
        state = legacy;
        break;
      }
    }
  }

  state.done = state.done || {};
  state.wrong = state.wrong || {};
  state.streak = state.streak || {};
  state.fav = state.fav || {};
  state.history = state.history || {};
  state.mode = state.mode || "seq";
  state.subject = state.subject || "";
  state.typeFilter = state.typeFilter || "";
  state.sourceFilter = state.sourceFilter || "";
  state.cursor = state.cursor || 0;
  delete state._pending;
  delete state._stickyId;
  return state;
}

let state = initialState();

function save() {
  const persisted = {...state};
  delete persisted._pending;
  delete persisted._stickyId;
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(persisted));
  } catch {}
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

function getScope() {
  let scope = QUESTIONS;
  if (state.subject) scope = scope.filter((q) => q.subject === state.subject);
  if (state.typeFilter) scope = scope.filter((q) => q.type === state.typeFilter);
  if (state.sourceFilter) scope = scope.filter((q) => q.source === state.sourceFilter);
  return scope;
}

function getPool() {
  let pool = getScope();
  if (state.mode === "wrong") {
    pool = pool.filter((q) => state.wrong[q.id] || state._stickyId === q.id);
  } else if (state.mode === "fav") {
    pool = pool.filter((q) => state.fav[q.id]);
  } else {
    pool = pool.filter((q) => !state.done[q.id] || state._stickyId === q.id);
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

function resetPosition() {
  state.cursor = 0;
  state.currentId = null;
  state._stickyId = null;
  state._pending = null;
  state._shuffled = false;
}

function handleAnswer(q, given) {
  state.done[q.id] = given;
  state.history[q.id] = state.history[q.id] || [];
  state.history[q.id].push(given);
  state._stickyId = q.id;
  state.currentId = q.id;

  if (!isAnswerCorrect(q, given)) {
    state.wrong[q.id] = (state.wrong[q.id] || 0) + 1;
    state.streak[q.id] = 0;
    return;
  }

  if (state.wrong[q.id]) {
    state.streak[q.id] = (state.streak[q.id] || 0) + 1;
    if (state.streak[q.id] >= MASTER_THRESHOLD) {
      delete state.wrong[q.id];
      delete state.streak[q.id];
    }
  }
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
  $("mini-stat").textContent = `${done}/${scope.length} · ${rate}%${wrongbook ? " · 错" + wrongbook : ""}`;
}

function renderChoiceQuestion(q, chosen, inWrongFresh) {
  const isMulti = q.type === "多选";
  const pending = state._pending && state._pending.qid === q.id ? state._pending.set : new Set();
  const options = ["A", "B", "C", "D"].filter((letter) => q.options && q.options[letter]);
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
    return `<button class="${cls}" data-letter="${letter}">
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
    return `<button class="${cls}" data-judge="${value}">
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
  const badge = wrongCount ? ` · 已错 ${wrongCount} 次${ok && remain ? ` · 还需连续答对 ${remain} 次出本` : ""}` : "";
  const answer = q.type === "填空" || q.type === "判断" ? `答案：${q.answer}` : `答案：${q.answer}`;
  const explanation = q.explanation && q.explanation.trim()
    ? `<div class="explanation"><div class="exp-title">解析</div>${escapeHtml(q.explanation)}</div>`
    : `<div class="explanation">本题暂无文字解析</div>`;
  return `<div class="feedback">
    <div class="feedback-label ${ok ? "ok" : "ng"}">${ok ? "✓ 正确" : "× 错误，" + answer}${badge}</div>
    ${explanation}
  </div>`;
}

function renderQuestion(q, pool) {
  const inWrongFresh = state.mode === "wrong" && state._stickyId !== q.id;
  const chosen = inWrongFresh ? null : state.done[q.id];
  const isFav = !!state.fav[q.id];
  let body = "";

  if (q.type === "单选" || q.type === "多选") body = renderChoiceQuestion(q, chosen, inWrongFresh);
  else if (q.type === "判断") body = renderJudgeQuestion(q, chosen);
  else if (q.type === "填空") body = renderFillQuestion(q, chosen);

  $("card-area").innerHTML = `<article class="card">
    <div class="meta">
      <span class="badge source source-${escapeHtml(q.source)}">${escapeHtml(q.source)}</span>
      <span class="badge type-${escapeHtml(q.type)}">${escapeHtml(q.type)}</span>
      <span class="badge subject">${escapeHtml(q.subject)}</span>
      <span class="chapter">${escapeHtml(q.source_chapter || q.chapter || "")}</span>
      <span class="q-pos">${state.cursor + 1} / ${pool.length}</span>
    </div>
    <div class="stem">${escapeHtml(q.stem)}</div>
    ${body}
    ${feedbackHtml(q, chosen)}
    <div class="nav">
      <button class="nav-icon" id="prev" aria-label="上一题">←</button>
      <button class="nav-icon fav ${isFav ? "active" : ""}" id="fav" aria-label="收藏">${isFav ? "★" : "☆"}</button>
      ${state.done[q.id] ? '<button class="nav-icon" id="redo" aria-label="重答">↻</button>' : ""}
      <button class="next ${state.done[q.id] ? "ready" : ""}" id="next">${state.done[q.id] ? "下一题 →" : "跳过 →"}</button>
    </div>
  </article>`;

  bindQuestionEvents(q, inWrongFresh);
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
  if (state.mode === "wrong") {
    title = "错题本已清空";
    text = "当前筛选条件下没有待复习错题。";
  } else if (state.mode === "fav") {
    title = "收藏夹为空";
    text = "刷题时点击 ☆ 收藏题目。";
  }
  $("card-area").innerHTML = `<div class="card empty"><strong>${title}</strong>${text}</div>`;
}

function render() {
  if (!QUESTIONS.length) {
    $("card-area").innerHTML = `<div class="card empty"><strong>题库未加载</strong>请确认 questions.js 与 app.js 在同一目录。</div>`;
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
  state.currentId = pool[Math.max(0, idx)].id;
  save();
  render();
}

function prevQuestion() {
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
  idx = idx >= 0 ? (idx - 1 + pool.length) % pool.length : 0;
  state.currentId = pool[idx].id;
  save();
  render();
}

function updateModeTabs() {
  document.querySelectorAll(".mode").forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === state.mode);
  });
}

function renderDrawerList(el, items, active, onPick) {
  el.innerHTML = "";
  for (const item of items) {
    const button = document.createElement("button");
    button.className = `drawer-item${item.value === active ? " active" : ""}`;
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
    resetPosition();
    save();
    closeDrawer();
    render();
  });
}

function openDrawer() {
  buildDrawer();
  $("drawer").classList.add("show");
  $("drawer-mask").classList.add("show");
}

function closeDrawer() {
  $("drawer").classList.remove("show");
  $("drawer-mask").classList.remove("show");
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
      for (const letter of ["A", "B", "C", "D"]) {
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
    version: 3,
    exportedAt: new Date().toISOString(),
    state: {...state, _pending: undefined, _stickyId: undefined},
  };
  downloadText(`刷题进度_${new Date().toISOString().slice(0, 10)}.json`, JSON.stringify(payload, null, 2), "application/json;charset=utf-8");
}

function importProgressFile(file) {
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const payload = JSON.parse(String(reader.result || "{}"));
      const next = payload.state || payload;
      if (!next || typeof next !== "object") throw new Error("bad format");
      state = {...initialState(), ...next};
      state.done = next.done || {};
      state.wrong = next.wrong || {};
      state.streak = next.streak || {};
      state.fav = next.fav || {};
      state.history = next.history || {};
      resetPosition();
      save();
      render();
      alert("进度已导入");
    } catch {
      alert("导入失败：文件格式不正确");
    }
  };
  reader.readAsText(file, "utf-8");
}

function downloadText(filename, content, type) {
  const blob = new Blob([content], {type});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function bindGlobalEvents() {
  $("drawer-toggle").addEventListener("click", openDrawer);
  $("drawer-close").addEventListener("click", closeDrawer);
  $("drawer-mask").addEventListener("click", closeDrawer);

  $("subject-select").addEventListener("change", (event) => {
    state.subject = event.target.value;
    resetPosition();
    save();
    render();
  });

  $("stats-toggle").addEventListener("click", () => {
    const stats = $("stats");
    stats.classList.toggle("collapsed");
    $("stats-toggle").textContent = stats.classList.contains("collapsed") ? "▸" : "▾";
  });

  document.querySelectorAll(".mode").forEach((button) => {
    button.addEventListener("click", () => {
      state.mode = button.dataset.mode;
      resetPosition();
      save();
      render();
    });
  });

  $("export-wrong").addEventListener("click", () => {
    closeDrawer();
    exportWrong();
  });
  $("export-progress").addEventListener("click", () => {
    closeDrawer();
    exportProgress();
  });
  $("import-progress").addEventListener("click", () => $("progress-file").click());
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
      for (const key of LEGACY_KEYS) localStorage.removeItem(key);
    } catch {}
    state = initialState();
    render();
  });

  document.addEventListener("keydown", (event) => {
    if (document.activeElement && ["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement.tagName)) return;
    const pool = getPool();
    const q = pool[state.cursor];
    if (!q) return;
    const inWrongFresh = state.mode === "wrong" && state._stickyId !== q.id;
    const canAnswer = !state.done[q.id] || inWrongFresh;
    const isLetter = event.key.length === 1 && "abcdABCD".includes(event.key);
    const isNum = event.key >= "1" && event.key <= "4";

    if (q.type === "判断" && canAnswer) {
      if (event.key === "1" || event.key === "t" || event.key === "T" || event.key === "√") {
        handleAnswer(q, "正确");
        save();
        render();
        return;
      }
      if (event.key === "0" || event.key === "f" || event.key === "F" || event.key === "×") {
        handleAnswer(q, "错误");
        save();
        render();
        return;
      }
    }

    if ((isLetter || isNum) && canAnswer && (q.type === "单选" || q.type === "多选")) {
      const letter = isNum ? ["A", "B", "C", "D"][Number(event.key) - 1] : event.key.toUpperCase();
      if (!q.options || !q.options[letter]) return;
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
      return;
    }

    if (q.type === "多选" && event.key === "Enter" && canAnswer && state._pending && state._pending.qid === q.id && state._pending.set.size) {
      const answer = [...state._pending.set].sort().join("");
      state._pending = null;
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

bindGlobalEvents();
render();
