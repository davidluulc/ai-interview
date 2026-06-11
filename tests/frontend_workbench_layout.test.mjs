import assert from "node:assert/strict";
import fs from "node:fs";

const html = fs.readFileSync("index.html", "utf8");
const css = fs.readFileSync("styles.css", "utf8");
const app = fs.readFileSync("app.js", "utf8");

assert.match(html, /class="interview-panel workbench-panel"/);
assert.match(html, /class="interview-header workbench-header"/);
assert.match(html, /class="answer-box answer-composer"/);

assert.match(app, /class="compact-progress"/);
assert.match(app, /class="progress-dot/);
assert.match(app, /class="conversation-message interviewer-message/);
assert.match(app, /class="conversation-message candidate-message/);
assert.match(app, /class="agent-insight-grid"/);
assert.match(app, /class="agent-debug-panel-inline"/);

assert.match(css, /\.workbench-panel/);
assert.match(css, /\.compact-progress/);
assert.match(css, /\.conversation-message/);
assert.match(css, /\.agent-insight-bar/);
assert.match(css, /\.agent-debug-panel-inline/);
assert.match(css, /\.agent-debug-grid/);
assert.match(css, /\.agent-log-debug-summary/);
assert.match(css, /@media \(max-width: 980px\)[\s\S]*\.agent-debug-grid\s*{[\s\S]*grid-template-columns:\s*1fr/s);
assert.match(css, /\.answer-composer/);
assert.match(css, /\.interview-state\s*{[^}]*align-content:\s*start/s);
assert.match(css, /\.actions\s*{[^}]*align-items:\s*center/s);
assert.match(css, /\.actions\s+\.primary-button[\s\S]*?min-width:\s*180px/s);
assert.match(css, /\.answer-composer textarea\s*{[^}]*min-height:\s*112px/s);
assert.match(css, /\.conversation-list\s*{[^}]*border:\s*0/s);
assert.match(css, /\.stat-card\s*{[^}]*overflow-wrap:\s*anywhere/s);
