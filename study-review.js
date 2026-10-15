(function () {
  "use strict";

  const key = "shaoyang-recall-ratings-v2";
  const intervals = [1, 3, 7, 14, 30];

  function read() {
    try {
      const value = JSON.parse(localStorage.getItem(key) || "{}");
      return value && typeof value === "object" && !Array.isArray(value) ? value : {};
    } catch { return {}; }
  }

  function isDue(rating, now = Date.now()) {
    if (!rating || !["again", "fuzzy", "known"].includes(rating.value)) return false;
    const due = Date.parse(rating.nextReviewAt);
    if (Number.isFinite(due)) return due <= now;
    // Older ratings have no schedule. A known card returns after a day.
    if (rating.value !== "known") return true;
    const saved = Date.parse(rating.savedAt);
    return !Number.isFinite(saved) || saved + 86400000 <= now;
  }

  function nextRating(previous, value, now = Date.now()) {
    if (!["again", "fuzzy", "known"].includes(value)) return null;
    const priorLevel = Math.min(intervals.length, Math.max(0, Number(previous?.level) || 0));
    // Repeated taps on the same day must not advance a long-term schedule.
    const eligible = !previous || (previous.value === "known" && isDue(previous, now));
    const level = value === "known" ? Math.max(1, Math.min(intervals.length, priorLevel + Number(eligible))) : 0;
    const delay = value === "known" ? intervals[level - 1] * 86400000 : value === "fuzzy" ? 86400000 : 10 * 60000;
    return {value, level, savedAt: new Date(now).toISOString(), nextReviewAt: new Date(now + delay).toISOString()};
  }

  globalThis.StudyReview = Object.freeze({key, read, isDue, nextRating});
})();
