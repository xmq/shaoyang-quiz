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

  function mapOldPosition(course, chapter, card = 1) {
    const topicId = course.previous_layout?.[Number(chapter) - 1]?.topic_ids?.[Number(card) - 1];
    for (let index = 0; index < (course.review_topic_ids || []).length; index += 1) {
      const cardIndex = course.review_topic_ids[index].indexOf(topicId);
      if (cardIndex >= 0) return {chapter: index + 1, card: cardIndex + 1};
    }
    return {chapter: 1, card: 1};
  }

  function migrateLayouts(courses) {
    try {
      const ratings = read();
      const progress = JSON.parse(localStorage.getItem("shaoyang-reading-progress-v1") || "{}");
      let recent = JSON.parse(localStorage.getItem("shaoyang-last-learning") || "null");
      let changed = false;
      for (const course of courses) {
        const revision = course.layout_revision;
        if (!revision || !course.previous_layout?.length) continue;
        const name = course.name;
        const versions = ratings.__layoutVersions || {};
        if (versions[name] !== revision) {
          const oldEntries = Object.entries(ratings).filter(([ratingKey]) => ratingKey.startsWith(`${name}::`));
          oldEntries.forEach(([ratingKey]) => delete ratings[ratingKey]);
          oldEntries.forEach(([ratingKey, value]) => {
            const [, chapter, card] = ratingKey.split("::");
            if (!course.previous_layout[Number(chapter) - 1]?.topic_ids?.[Number(card) - 1]) {
              ratings.__archived = {...ratings.__archived, [ratingKey]: value};
              return;
            }
            const target = mapOldPosition(course, chapter, card);
            ratings[`${name}::${target.chapter}::${target.card}`] = value;
          });
          ratings.__layoutVersions = {...versions, [name]: revision};
          changed = true;
        }
        const previous = progress[name] || {};
        if (previous.layoutRevision !== revision) {
          const target = mapOldPosition(course, previous.lastLectureChapter || 1);
          progress[name] = {
            ...previous,
            previousLayoutProgress: {...previous},
            completed: (previous.completed || []).filter(id => course.keep_completed?.includes(id)),
            lecture: (previous.lecture || []).filter(id => course.chapter_ids?.includes(id)),
            "color-notes": (previous["color-notes"] || []).filter(id => course.chapter_ids?.includes(id)),
            lastLectureChapter: target.chapter,
            layoutRevision: revision,
          };
          changed = true;
        }
        if (recent?.course === name && recent.layoutRevision !== revision) {
          const target = mapOldPosition(course, recent.chapter || 1, recent.module === "color-notes" ? recent.card || 1 : 1);
          recent = {...recent, ...target, layoutRevision: revision};
          changed = true;
        }
      }
      if (changed) {
        localStorage.setItem(key, JSON.stringify(ratings));
        localStorage.setItem("shaoyang-reading-progress-v1", JSON.stringify(progress));
        if (recent) localStorage.setItem("shaoyang-last-learning", JSON.stringify(recent));
      }
    } catch {}
  }

  globalThis.StudyReview = Object.freeze({key, read, isDue, nextRating, mapOldPosition, migrateLayouts});
})();
