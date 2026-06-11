import assert from "node:assert/strict";
import fs from "node:fs";

const html = fs.readFileSync("index.html", "utf8");
const css = fs.readFileSync("styles.css", "utf8");
const app = fs.readFileSync("app.js", "utf8");

assert.match(html, /id="productNav"/);
assert.match(html, /data-product-section="account-profile"/);
assert.match(html, /data-product-section="interview-workbench"/);
assert.match(html, /data-product-section="training-center"/);
assert.match(html, /data-product-section="rag-knowledge"/);
assert.match(html, /data-product-section="admin-dashboard"/);

assert.match(html, /data-section-target="account-profile"/);
assert.match(html, /data-section-target="interview-workbench"/);
assert.match(html, /data-section-target="training-center"/);
assert.match(html, /data-section-target="rag-knowledge"/);
assert.match(html, /data-section-target="admin-dashboard"/);

assert.match(css, /\.product-nav/);
assert.match(css, /\.product-section/);
assert.match(css, /\.product-section\.is-active/);

assert.match(app, /function switchProductSection/);
assert.match(app, /function bindProductNavigation/);
