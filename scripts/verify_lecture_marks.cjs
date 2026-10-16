"use strict";
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");

const source = fs.readFileSync(path.join(__dirname, "../notes.template.html"), "utf8");
const start = source.indexOf("    function formatInline(");
const end = source.indexOf("    function tableCells(", start);
const escapeStart = source.indexOf("    function escapeHtml(");
const escapeEnd = source.indexOf("\n    }", escapeStart) + 6;
assert.ok(start >= 0 && end > start && escapeEnd > escapeStart);
const context = vm.createContext({colorMode: false, publicFacingText: value => String(value || "")});
vm.runInContext(source.slice(escapeStart, escapeEnd) + source.slice(start, end), context);
const format = context.formatInline;

assert.equal(format("定义中的==并发、共享==保持原文"), '定义中的<mark class="answer-key">并发、共享</mark>保持原文');
assert.equal(format("==`C=B log₂(1+S/N)`=="), '<mark class="answer-key"><code>C=B log₂(1+S/N)</code></mark>');
assert.equal(format("`a == b` 与 `x == y`"), '<code>a == b</code> 与 <code>x == y</code>', "equality operators must remain code");
assert.equal(format("`**literal**`"), '<code>**literal**</code>', "formatting characters inside code stay literal");
assert.equal(format("==<img src=x onerror=alert(1)>=="), '<mark class="answer-key">&lt;img src=x onerror=alert(1)&gt;</mark>', "markup must never allow HTML injection");
assert.equal(format("未配对==保持文本"), "未配对==保持文本");
assert.ok(format("🔴 **基本特征**：==并发、共享、虚拟、异步==").includes('class="lecture-line lecture-core"'));
assert.ok(format("⚫ **边界**：==不等于已经死锁==").includes('<mark class="answer-key">不等于已经死锁</mark>'));
console.log("讲义标记：关键词、公式、否定条件、代码比较符与HTML转义通过");
