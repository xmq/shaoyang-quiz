"use strict";
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const template = fs.readFileSync(path.join(__dirname, "../notes.template.html"), "utf8");
const escapeStart = template.indexOf("    function escapeHtml(");
const escapeEnd = template.indexOf("\n    }", escapeStart) + 6;
const start = template.indexOf("    function highlightCode(");
const end = template.indexOf("    function tableCells(", start);
assert.ok(escapeStart >= 0 && start >= 0 && end > start);
const context = vm.createContext({});
vm.runInContext(template.slice(escapeStart, escapeEnd) + template.slice(start, end), context);
const highlight = context.highlightCode;
const plain = html => html.replace(/<[^>]*>/g, "").replace(/&(amp|lt|gt|quot|#39);/g, (_match, name) => ({amp:"&",lt:"<",gt:">",quot:'"',"#39":"'"}[name]));
const examples = [
  ["c", '#include <stdio.h>\nint main(void) {\n    int x = 3; --x; // if x\n    printf("<tag>\\n");\n}'],
  ["python", 'def f(x):\n    url = "https://example/#tag"  # comment\n    return x // 2 == 3'],
  ["sql", "select '--literal', COUNT(*) from Student where id = 2; -- comment"],
  ["text", "如果 队列非空：\n    取出队首 u\n    返回 u\n输出 A → B → C"],
  ["unknown", "<script>alert('x')</script> && **text** == value"],
];
for (const [language, code] of examples) assert.equal(plain(highlight(code, language)), code, `${language}: code and indentation must stay unchanged`);
assert.ok(highlight('return x // 2', 'python').includes('class="code-keyword">return'));
assert.ok(!highlight('return x // 2', 'python').includes('code-comment'));
assert.ok(!highlight('--x;', 'c').includes('code-comment'));
assert.ok(highlight("SELECT '--literal'", 'sql').includes('class="code-string">&#39;--literal&#39;'));
assert.ok(!highlight("SELECT '--literal'", 'sql').includes('code-comment'));
assert.ok(context.renderCodeBlock('a < b', 'text').includes('code-steps'));
assert.ok(context.renderCodeBlock('x == 1', 'python').includes('Python代码，可横向滚动'));
assert.ok(!context.renderCodeBlock('<script>alert(1)</script>', 'python').includes('<script>'));
console.log("代码展示：C/Python/SQL/伪代码原文、缩进、字符串与注释、转义通过");
