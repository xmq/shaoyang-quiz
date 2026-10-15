"use strict";
const assert = require("node:assert/strict");
require("../study-review.js");
const review = globalThis.StudyReview;
const now = Date.parse("2026-10-15T08:00:00Z");
const day = 86400000;
const first = review.nextRating(null, "known", now);
assert.equal(Date.parse(first.nextReviewAt), now + day);
assert.equal(review.isDue(first, now + day - 1), false);
assert.equal(review.isDue(first, now + day), true);
const repeat = review.nextRating(first, "known", now + 60000);
assert.equal(repeat.level, 1, "same-session repeats cannot count as spaced recall");
const later = review.nextRating(first, "known", now + day);
assert.equal(later.level, 2);
assert.equal(Date.parse(later.nextReviewAt), now + 4 * day);
const forgotten = review.nextRating(later, "again", now + 4 * day);
assert.equal(forgotten.level, 0);
assert.equal(Date.parse(forgotten.nextReviewAt), now + 4 * day + 600000);
const fuzzy = review.nextRating(later, "fuzzy", now);
assert.equal(Date.parse(fuzzy.nextReviewAt), now + day);
assert.equal(review.isDue({value: "known", savedAt: new Date(now - 2 * day).toISOString()}, now), true);
assert.equal(review.isDue({value: "known", savedAt: new Date(now).toISOString()}, now), false);
assert.equal(review.isDue({value: "fuzzy"}, now), true);
assert.equal(review.isDue({}, now), false);
assert.equal(review.nextRating(null, "invalid", now), null);
// A textbook reordering must move old ratings by topic, never by position.
const storage = new Map();
globalThis.localStorage = {
  getItem: key => storage.get(key) || null,
  setItem: (key, value) => storage.set(key, value),
};
const course = {
  name: "test-course", layout_revision: "textbook-v1",
  previous_layout: [{chapter_id: "old-a", topic_ids: ["t1", "t2"]}, {chapter_id: "old-b", topic_ids: ["t3"]}],
  chapter_ids: ["new-a", "old-a", "new-b"],
  review_topic_ids: [["t3", "new-topic"], ["t1"], ["t2"]],
  keep_completed: ["old-a"],
};
storage.set(review.key, JSON.stringify({"test-course::1::1": first, "test-course::1::2": fuzzy, "test-course::2::1": forgotten, "other::1::1": later}));
storage.set("shaoyang-reading-progress-v1", JSON.stringify({"test-course": {completed: ["old-a", "old-b"], lastLectureChapter: 2}, other: {completed: ["other-ch"]}}));
storage.set("shaoyang-last-learning", JSON.stringify({course: "test-course", module: "color-notes", chapter: 1, card: 2}));
storage.set("shaoyang-quiz-v5", "untouched-quiz-records");
review.migrateLayouts([course]);
let migrated = review.read();
assert.deepEqual(migrated["test-course::2::1"], first);
assert.deepEqual(migrated["test-course::3::1"], fuzzy);
assert.deepEqual(migrated["test-course::1::1"], forgotten);
assert.equal(migrated["test-course::1::2"], undefined, "new topics cannot inherit old mastery");
assert.deepEqual(migrated["other::1::1"], later);
let reading = JSON.parse(storage.get("shaoyang-reading-progress-v1"));
assert.deepEqual(reading["test-course"].completed, ["old-a"]);
assert.deepEqual(reading["test-course"].previousLayoutProgress.completed, ["old-a", "old-b"]);
assert.equal(reading["test-course"].lastLectureChapter, 1);
assert.deepEqual(reading.other.completed, ["other-ch"]);
let recent = JSON.parse(storage.get("shaoyang-last-learning"));
assert.equal(recent.chapter, 3);
assert.equal(recent.card, 1);
const afterFirstMigration = [...storage.entries()];
review.migrateLayouts([course]);
assert.deepEqual([...storage.entries()], afterFirstMigration, "migration must be idempotent");
assert.equal(storage.get("shaoyang-quiz-v5"), "untouched-quiz-records");
console.log("间隔回忆：首次、隔日、重复作答、遗忘与旧记录兼容检查通过");
