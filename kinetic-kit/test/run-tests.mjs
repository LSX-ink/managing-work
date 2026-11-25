#!/usr/bin/env node
// End-to-end tests for the Kinetic kit, run against `wrangler pages dev` (local D1 + R2 via
// miniflare) and `wrangler dev` for the statements Worker, driven by Playwright.
//
//   WRANGLER=/path/to/wrangler node test/run-tests.mjs
// Env: WRANGLER (default "npx wrangler"), PLAYWRIGHT (module path), CHROME (executable path),
//      KINETIC_LIVE (path to kinetic-live, default ../kinetic-live; set to "" to skip that part).
import { createRequire } from "node:module";
import { execSync, spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import http from "node:http";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT || "/tmp/node_modules/playwright");
const CHROME = process.env.CHROME || "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const KIT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const WR = process.env.WRANGLER || "npx wrangler";
const LIVE = process.env.KINETIC_LIVE ?? path.resolve(KIT, "../kinetic-live");
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), "kinetic-kit-test-"));
const DBID = "00000000-0000-4000-8000-000000000001";
const WHSEC = "whsec_test_" + crypto.randomBytes(12).toString("hex");
const PORT = 8799, WPORT = 8801, MAILPORT = 8802, LPORT = 8803;
const BASE = `http://localhost:${PORT}`;

// ---------- tiny test framework ----------
const results = [];
function check(name, ok, detail = "") {
  results.push({ name, ok: !!ok, detail });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail && !ok ? "  -> " + detail : detail ? "  (" + detail + ")" : ""}`);
}
const shot = async (pg, name) => { if (process.env.SHOTS) await pg.screenshot({ path: path.join(process.env.SHOTS, name + ".png"), fullPage: true }); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function until(fn, ms = 8000, step = 150) {
  const end = Date.now() + ms; let last;
  while (Date.now() < end) { try { last = await fn(); if (last) return last; } catch {} await sleep(step); }
  return last;
}

// ---------- helpers ----------
const sh = (cmd, cwd) => execSync(cmd, { cwd, stdio: ["ignore", "pipe", "pipe"], env: { ...process.env, WRANGLER_SEND_METRICS: "false" } }).toString();
function sql(dir, command) {
  const out = sh(`${WR} d1 execute kit-test-db --local --json --command ${JSON.stringify(command)}`, dir);
  return JSON.parse(out.slice(out.indexOf("[")))[0].results;
}
function createOwner(dir, email, username) {
  const f = path.join(dir, "reset-" + email.replace(/\W/g, "_") + ".sql");
  const out = sh(`node ${JSON.stringify(path.join(KIT, "tools/owner-password.mjs"))} ${email} --username ${username} --db kit-test-db --out ${JSON.stringify(f)}`, dir);
  const pw = /Temporary password:\s*\n\s{4}(\S+)/.exec(out)[1];
  const file = fs.readFileSync(f, "utf8");
  if (file.includes(pw)) throw new Error("temporary password leaked into the SQL file");
  sh(`${WR} d1 execute kit-test-db --local --file ${JSON.stringify(f)}`, dir);
  fs.unlinkSync(f);
  return pw;
}
const procs = [];
function start(cmd, cwd, readyUrl, log) {
  const p = spawn(cmd, { cwd, shell: true, detached: true, env: { ...process.env, WRANGLER_SEND_METRICS: "false" } });
  const out = fs.createWriteStream(log); p.stdout.pipe(out); p.stderr.pipe(out);
  procs.push(p);
  if (readyUrl === "log") return until(() => fs.existsSync(log) && /Ready on/.test(fs.readFileSync(log, "utf8")), 60000, 400);
  return until(async () => (await fetch(readyUrl)).status < 500, 60000, 400);
}
function stopAll() { for (const p of procs) { try { process.kill(-p.pid, "SIGTERM"); } catch {} } }
process.on("exit", stopAll);
process.on("SIGINT", () => process.exit(130));

function copyKit(dir) {
  fs.mkdirSync(dir, { recursive: true });
  for (const f of ["owner.html", "owner.js", "owner.css", "kit.js", "schema.sql", "_headers"]) fs.copyFileSync(path.join(KIT, f), path.join(dir, f));
  fs.cpSync(path.join(KIT, "functions"), path.join(dir, "functions"), { recursive: true });
}
function wranglerToml(dir) {
  fs.writeFileSync(path.join(dir, "wrangler.toml"), `name = "kit-test"\npages_build_output_dir = "."\ncompatibility_date = "2025-01-01"\n[[d1_databases]]\nbinding = "DB"\ndatabase_name = "kit-test-db"\ndatabase_id = "${DBID}"\n`);
}
function stripeSign(payload, t = Math.floor(Date.now() / 1000), secret = WHSEC) {
  const sig = crypto.createHmac("sha256", secret).update(`${t}.${payload}`).digest("hex");
  return `t=${t},v1=${sig}`;
}
async function webhook(event, header) {
  const payload = JSON.stringify(event);
  return fetch(`${BASE}/api/stripe/webhook`, { method: "POST", headers: { "Content-Type": "application/json", "Stripe-Signature": header ?? stripeSign(payload) }, body: payload });
}
async function login(page, username, password) {
  await page.waitForSelector("#loginForm");
  await page.$eval("#loginForm", f => { f.dataset.old = "1"; });
  await page.fill("#lgUser", username); await page.fill("#lgPw", password);
  const res = page.waitForResponse(r => r.url().endsWith("/api/auth/login"));
  await page.click("#loginForm [type=submit]");
  const r = await res;
  await page.waitForSelector("#loginForm:not([data-old]) .err, #pwForm, .oa-tabs");
  return r.status();
}
async function changePw(page, p1, p2 = p1) {
  await page.$eval("#pwForm", f => { f.dataset.old = "1"; });
  await page.fill("#pw1", p1); await page.fill("#pw2", p2);
  await page.click("#pwForm [type=submit]");
  await page.waitForSelector("#pwForm:not([data-old]) .err, .oa-tabs");
}
// a real 2x2 PNG
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGP4z8DAwMDAxMDAwMDAAAANHQEDasKb6QAAAABJRU5ErkJggg==", "base64");

// =====================================================================
async function main() {
  console.log("temp dir:", TMP);
  const site = path.join(TMP, "site");
  copyKit(site); wranglerToml(site);
  fs.writeFileSync(path.join(site, ".dev.vars"), `STRIPE_WEBHOOK_SECRET=${WHSEC}\n`);
  fs.writeFileSync(path.join(site, "index.html"), `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Loftline</title></head><body>
<h1 data-kit-text="hero">Default heading</h1><div data-kit-products></div>
<form data-kit-event="quote" id="q" onsubmit="event.preventDefault()"><input name="x" required><button>Send</button></form>
<script src="/kit.js" defer></script></body></html>`);
  // statements worker next to the site's functions/, as in the repo
  fs.cpSync(path.join(KIT, "statements-worker"), path.join(site, "statements-worker"), { recursive: true });
  const wt = path.join(site, "statements-worker/wrangler.toml");
  fs.writeFileSync(wt, fs.readFileSync(wt, "utf8").replace("REPLACE_WITH_D1_DATABASE_ID", DBID).replace('database_name = "kinetic-db"', 'database_name = "kit-test-db"'));

  sh(`${WR} d1 execute kit-test-db --local --file schema.sql`, site);
  sh(`${WR} d1 execute kit-test-db --local --file schema.sql`, site); // schema re-runs cleanly
  check("schema applies to local D1 (twice, idempotent)", true);
  sql(site, "INSERT INTO texts (key, label, value, multiline, sort) VALUES ('hero', 'Big heading', 'Made for the cold', 0, 1)");

  const ownerEmail = "owner@loftline.test", lockEmail = "lockme@loftline.test";
  const ownerUser = "loftline.owner", lockUser = "lockme.owner";
  const tempPw = createOwner(site, ownerEmail, ownerUser);
  const lockPw = createOwner(site, lockEmail, lockUser);
  const u = sql(site, "SELECT email, pw_hash, must_change FROM users ORDER BY id");
  check("owner-password.mjs stores only a PBKDF2 hash (100k iterations, per-user salt)",
    u.length === 2 && u.every(r => /^pbkdf2-sha256\$100000\$[A-Za-z0-9+/=]{24}\$[A-Za-z0-9+/=]{44}$/.test(r.pw_hash) && r.must_change === 1) && u[0].pw_hash.split("$")[2] !== u[1].pw_hash.split("$")[2]
      && !u.some(r => r.pw_hash.includes(tempPw)), `temp pw looks like ${tempPw.replace(/\w/g, "x")}`);

  const ok = await start(`${WR} pages dev . --port ${PORT} --ip 127.0.0.1 --d1 DB=${DBID} --r2 PHOTOS -b SITE_NAME=Loftline -b SHOP=1 -b TEXT=1 -b "EVENTS=signup:Sign-ups,quote:Quote requests"`,
    site, `http://127.0.0.1:${PORT}/api/config`, path.join(TMP, "pages-dev.log"));
  check("wrangler pages dev starts", ok, "see " + path.join(TMP, "pages-dev.log"));
  if (!ok) return;

  const browser = await chromium.launch({ executablePath: CHROME });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  const pageErrors = [];
  page.on("pageerror", e => pageErrors.push(e.message));

  // ---------- lockout ----------
  await page.goto(`${BASE}/owner`);
  await page.waitForSelector("#loginForm");
  let lastErr = "";
  for (let i = 0; i < 5; i++) {
    await login(page, lockUser, "wrong-password-" + i);
    lastErr = await page.textContent(".err");
  }
  check("5 wrong passwords lock the login", /locked/i.test(lastErr), lastErr);
  const lockedStatus = await login(page, lockUser, lockPw);
  check("right password is refused while locked", lockedStatus === 429 && /locked/i.test(await page.textContent(".err")));
  const lockRow = sql(site, `SELECT locked_until FROM users WHERE email = '${lockEmail}'`)[0];
  check("lock lasts about 15 minutes", lockRow.locked_until > Date.now() + 14 * 6e4 && lockRow.locked_until < Date.now() + 16 * 6e4);
  const unknown = await fetch(`${BASE}/api/auth/login`, { method: "POST", headers: { "Content-Type": "application/json", Origin: BASE }, body: JSON.stringify({ username: "nobody.here", password: "whatever123" }) });
  check("unknown email gets the same 401 as a wrong password", unknown.status === 401);
  const xsite = await fetch(`${BASE}/api/auth/login`, { method: "POST", headers: { "Content-Type": "application/json", Origin: "https://evil.example" }, body: "{}" });
  check("cross-site login POST is refused", xsite.status === 403);

  // ---------- first login + forced password change ----------
  const byEmail = await fetch(`${BASE}/api/auth/login`, { method: "POST", headers: { "Content-Type": "application/json", Origin: BASE }, body: JSON.stringify({ username: ownerEmail, password: tempPw }) });
  check("the public email is not a login (only the private username is)", byEmail.status === 401);
  await login(page, ownerUser, tempPw);
  await page.waitForSelector("#pwForm");
  check("first login with the temporary password asks for a new one", /Choose your own password/.test(await page.textContent("#pwForm h2")));
  const before = await page.evaluate(async () => (await fetch("/api/owner/account")).status);
  check("owner API is blocked until the password is changed", before === 403, "status " + before);
  const cookies = await ctx.cookies();
  const sc = cookies.find(c => c.name === "kk_session");
  check("session cookie is HttpOnly, Secure, SameSite=Strict", sc && sc.httpOnly && sc.secure && sc.sameSite === "Strict", JSON.stringify(sc && { httpOnly: sc.httpOnly, secure: sc.secure, sameSite: sc.sameSite }));
  const sessRow = sql(site, "SELECT id FROM sessions LIMIT 1")[0];
  check("only a hash of the session token is stored", sessRow && sessRow.id !== sc.value && /^[a-f0-9]{64}$/.test(sessRow.id));
  await changePw(page, "short");
  check("too-short password is refused", /at least 10/.test(await page.textContent("#pwForm .err")));
  await changePw(page, tempPw);
  check("re-using the temporary password is refused", /new password/i.test(await page.textContent("#pwForm .err")));
  const NEWPW = "correct horse battery";
  await changePw(page, NEWPW);
  await page.waitForSelector(".oa-tabs");
  const tabNames = await page.$$eval(".oa-tabs button", b => b.map(x => x.textContent));
  check("owner area opens after the change, with shop tabs", tabNames.join("|") === "Products & stock|Text|Analytics|Transactions|Monthly statements|Account", tabNames.join("|"));
  check("must_change cleared in D1", sql(site, `SELECT must_change FROM users WHERE email = '${ownerEmail}'`)[0].must_change === 0);
  const oldLogin = await fetch(`${BASE}/api/auth/login`, { method: "POST", headers: { "Content-Type": "application/json", Origin: BASE }, body: JSON.stringify({ username: ownerUser, password: tempPw }) });
  check("temporary password no longer works", oldLogin.status === 401);

  // ---------- products ----------
  const pub = async () => (await fetch(`${BASE}/api/public/catalog`)).json();
  const wait = (re, method = "PATCH") => page.waitForResponse(r => re.test(r.url()) && r.request().method() === method);
  await page.waitForSelector("text=+ Add a product list");
  await page.click("text=+ Add a product list");
  await page.waitForSelector("[data-ln]");
  const lnSaved = wait(/\/api\/owner\/lists\/\d+$/);
  await page.fill("[data-ln]", "New in"); await lnSaved;
  await page.click("[data-act=add]"); await page.waitForSelector("[data-item]");
  const pid = +(await page.getAttribute("[data-item]", "data-item"));
  let saved = wait(new RegExp(`/api/owner/products/${pid}$`));
  await page.fill(`[data-item="${pid}"] [data-f=name]`, "Heavyweight tee"); await saved;
  saved = wait(new RegExp(`/api/owner/products/${pid}$`));
  await page.fill(`[data-item="${pid}"] [data-f=price]`, "32"); await saved;
  for (let i = 0; i < 2; i++) { saved = wait(new RegExp(`/api/owner/products/${pid}$`)); await page.click(`[data-item="${pid}"] [data-act=addsize]`); await saved; }
  const labels = await page.$$(`[data-item="${pid}"] [data-z=label]`), qtys = await page.$$(`[data-item="${pid}"] [data-z=qty]`);
  await labels[0].fill("S"); await labels[1].fill("XXL"); await qtys[0].fill("5");
  saved = wait(new RegExp(`/api/owner/products/${pid}$`)); await qtys[1].fill("0"); await saved;
  let cat = await pub(); let p = cat.lists[0] && cat.lists[0].items.find(x => x.id === pid);
  check("added product appears in the public API with name, price and sizes",
    cat.lists[0].title === "New in" && p && p.name === "Heavyweight tee" && p.price === 3200 && !p.outOfStock
      && JSON.stringify(p.sizes) === JSON.stringify([{ label: "S", available: true }, { label: "XXL", available: false }]), JSON.stringify(p));

  saved = wait(new RegExp(`/api/owner/products/${pid}$`)); await page.click(`[data-item="${pid}"] [data-act=stock]`); await saved;
  p = (await pub()).lists[0].items.find(x => x.id === pid);
  check("out-of-stock switch shows in the public API", p.outOfStock === true);
  saved = wait(new RegExp(`/api/owner/products/${pid}$`)); await page.click(`[data-item="${pid}"] [data-act=stock]`); await saved;
  saved = wait(new RegExp(`/api/owner/products/${pid}$`)); await (await page.$$(`[data-item="${pid}"] [data-z=qty]`))[0].fill("0"); await saved;
  p = (await pub()).lists[0].items.find(x => x.id === pid);
  check("all sizes at 0 also counts as out of stock", p.outOfStock === true);
  saved = wait(new RegExp(`/api/owner/products/${pid}$`)); await (await page.$$(`[data-item="${pid}"] [data-z=qty]`))[0].fill("4"); await saved;
  saved = wait(new RegExp(`/api/owner/products/${pid}$`)); await page.click(`[data-item="${pid}"] [data-act=visible]`); await saved;
  cat = await pub();
  check("hidden product is left out of the public API", !cat.lists.some(l => l.items.some(x => x.id === pid)));
  saved = wait(new RegExp(`/api/owner/products/${pid}$`)); await page.click(`[data-item="${pid}"] [data-act=visible]`); await saved;

  // photo upload
  const up = wait(new RegExp(`/api/owner/products/${pid}/photo$`), "POST");
  await page.setInputFiles(`[data-item="${pid}"] input[type=file]`, { name: "tee.png", mimeType: "image/png", buffer: PNG });
  const upRes = await up;
  p = (await pub()).lists[0].items.find(x => x.id === pid);
  const img = p.img ? await fetch(BASE + p.img) : null;
  const imgBuf = img ? Buffer.from(await img.arrayBuffer()) : null;
  check("photo upload goes to R2 and is served back", upRes.status() === 200 && img && img.status === 200 && img.headers.get("content-type") === "image/png" && imgBuf.equals(PNG), `${upRes.status()} ${img && img.status} ${img && img.headers.get("content-type")} ${imgBuf && imgBuf.length}/${PNG.length}`);
  const photoKey = decodeURIComponent(p.img.replace("/api/photo/", ""));
  const upl = (body, type) => page.evaluate(async ([id, b, t]) => (await fetch(`/api/owner/products/${id}/photo`, { method: "POST", headers: { "Content-Type": t }, body: b })).status, [pid, body, type]);
  check("non-image upload is refused (415)", await upl("hello", "text/plain") === 415);
  check("text pretending to be a PNG is refused (415)", await upl("not really a png at all", "image/png") === 415);
  check("SVG upload is refused (415)", await upl("<svg xmlns='http://www.w3.org/2000/svg'/>", "image/svg+xml") === 415);
  const big = await page.evaluate(async id => { const b = new Uint8Array(5.5 * 1024 * 1024); b.set([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]); return (await fetch(`/api/owner/products/${id}/photo`, { method: "POST", headers: { "Content-Type": "image/png" }, body: b })).status; }, pid);
  check("photo over 5 MB is refused (413)", big === 413, "status " + big);
  const anonUp = await fetch(`${BASE}/api/owner/products/${pid}/photo`, { method: "POST", headers: { "Content-Type": "image/png", Origin: BASE }, body: PNG });
  check("upload without a login is refused (401)", anonUp.status === 401);

  // a second, out-of-stock product, then the public shop page
  await page.click("[data-act=add]");
  await until(async () => (await page.$$("[data-item]")).length === 2);
  const pid2 = +(await page.getAttribute("[data-item]:not([data-item='" + pid + "'])", "data-item"));
  saved = wait(new RegExp(`/api/owner/products/${pid2}$`)); await page.fill(`[data-item="${pid2}"] [data-f=name]`, "Puffer, rust"); await saved;
  saved = wait(new RegExp(`/api/owner/products/${pid2}$`)); await page.click(`[data-item="${pid2}"] [data-act=stock]`); await saved;

  await shot(page, "1-products");
  // text
  await page.click("[data-tab=text]"); await page.waitForSelector("#tx-hero");
  const tsaved = wait(/\/api\/owner\/text$/, "PUT");
  await page.fill("#tx-hero", "Built to last"); await tsaved;
  check("text edit reaches the public API", (await pub()).text.hero === "Built to last");

  const shop = await ctx.newPage();
  shop.on("pageerror", e => pageErrors.push("shop: " + e.message));
  const tracked = shop.waitForResponse(r => r.url().endsWith("/api/track"));
  await shop.goto(`${BASE}/?utm=x`, { referer: "https://www.instagram.com/some/post" });
  await tracked;
  await shop.waitForSelector(".kk-card");
  const cards = await shop.$$eval(".kk-card", cs => cs.map(c => ({ name: c.querySelector(".kk-name").textContent, out: c.classList.contains("kk-out"), img: !!c.querySelector("img") })));
  check("kit.js renders products; out-of-stock one is greyed", cards.length === 2 && cards.find(c => c.name === "Puffer, rust").out && !cards.find(c => c.name === "Heavyweight tee").out && cards.find(c => c.name === "Heavyweight tee").img, JSON.stringify(cards));
  check("kit.js fills data-kit-text", (await shop.textContent("h1")) === "Built to last");
  await shop.evaluate(() => KineticKit.event("signup"));
  await shop.fill("#q input", "hello"); const ev2 = shop.waitForResponse(r => r.url().endsWith("/api/event")); await shop.click("#q button"); await ev2;
  const badEvent = await shop.evaluate(async () => (await fetch("/api/event", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: "made-up" }) })).status);
  check("events not listed in EVENTS are refused", badEvent === 400);
  const pv = sql(site, "SELECT * FROM pageviews");
  check("page view stored with path, referrer host, hashed visitor, no IP",
    pv.length === 1 && pv[0].path === "/" && pv[0].ref_host === "instagram.com" && /^[a-f0-9]{32}$/.test(pv[0].visitor) && Object.keys(pv[0]).join() === "id,ts,path,ref_host,visitor,device", JSON.stringify(pv[0]));
  await shop.goto(`${BASE}/owner`); // the owner page itself is not counted
  check("owner page views are not counted", sql(site, "SELECT COUNT(*) AS n FROM pageviews")[0].n === 1);

  // remove product 2 through the UI
  await page.click("[data-tab=products]"); await page.waitForSelector(`[data-item="${pid2}"]`);
  await page.click(`[data-item="${pid2}"] [data-act=del]`);
  const del = wait(new RegExp(`/api/owner/products/${pid2}$`), "DELETE");
  await page.click(`[data-item="${pid2}"] [data-act=delyes]`); await del;
  check("removed product is gone from the public API", !(await pub()).lists.some(l => l.items.some(x => x.id === pid2)));

  // ---------- analytics ----------
  await page.click("[data-tab=analytics]"); await page.waitForSelector(".kpi");
  const kpi = async label => page.$eval(".kpis", (el, l) => { const k = [...el.querySelectorAll(".kpi")].find(x => x.querySelector("span").textContent.startsWith(l)); return k ? k.querySelector("b").textContent : null; }, label);
  check("analytics: visitors in the last 24 hours = 1", await kpi("Visitors, last 24 hours") === "1");
  check("analytics: page views = 1", await kpi("Page views") === "1");
  check("analytics: sign-ups = 1 and quote requests = 1", await kpi("Sign-ups") === "1" && await kpi("Quote requests") === "1");
  check("analytics: top pages lists /", (await page.textContent(".toprows")).includes("/"));
  check("analytics: referrer shows in sources", (await page.content()).includes("instagram.com"));
  check("analytics: revenue shows £0 before any payment (no invented figures)", await kpi("Revenue") === "£0");
  const rangeOk = [];
  for (const r of ["minute", "hour", "day", "week", "month", "year"]) {
    const res = page.waitForResponse(x => x.url().includes("/api/owner/analytics?range=" + r));
    await page.click(`[data-range=${r}]`); const rr = await res; const j = await rr.json();
    await page.waitForSelector(`[data-range=${r}][aria-pressed=true]`);
    if (process.env.DEBUG) console.log(r, rr.status(), JSON.stringify(j.totals), j.buckets.length, j.buckets.filter(b => b.views).length);
    rangeOk.push(rr.status() === 200 && j.totals.views === 1 && j.buckets.filter(b => b.views).length === 1 && j.buckets.length === { minute: 60, hour: 24, day: 7, week: 12, month: 12, year: 5 }[r]);
  }
  check("analytics: minute/hour/day/week/month/year all bucket the view once", rangeOk.every(Boolean), JSON.stringify(rangeOk));
  check("analytics: bar chart drawn", !!(await page.$(".chart rect.vis")));

  // ---------- Stripe webhook ----------
  const nowS = Math.floor(Date.now() / 1000);
  const d = new Date(); const lastMonth = Math.floor(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() - 1, 15, 12) / 1000);
  const charge = (id, amount, created, extra = {}) => ({ id: "evt_" + id, type: "charge.succeeded", data: { object: { id, object: "charge", amount, currency: "gbp", status: "succeeded", created, livemode: false, description: "Heavyweight tee x1", billing_details: { name: "Sam Buyer" }, ...extra } } });
  let r = await webhook(charge("ch_test_1", 4500, nowS));
  check("signed Stripe charge.succeeded is accepted", r.status === 200, await r.text());
  r = await webhook(charge("ch_test_1", 4500, nowS));
  check("replayed event is harmless", r.status === 200 && sql(site, "SELECT COUNT(*) AS n FROM payments")[0].n === 1);
  r = await webhook(charge("ch_bad", 999, nowS), stripeSign(JSON.stringify(charge("ch_bad", 999, nowS)), nowS, "whsec_wrong"));
  check("wrong signature is rejected (400)", r.status === 400);
  const ev = JSON.stringify(charge("ch_old", 999, nowS));
  r = await fetch(`${BASE}/api/stripe/webhook`, { method: "POST", headers: { "Stripe-Signature": stripeSign(ev, nowS - 3600) }, body: ev });
  check("stale signature timestamp is rejected (400)", r.status === 400);
  r = await fetch(`${BASE}/api/stripe/webhook`, { method: "POST", headers: { "Stripe-Signature": stripeSign(ev) }, body: ev.replace("999", "1") });
  check("tampered body is rejected (400)", r.status === 400);
  check("rejected events stored nothing", sql(site, "SELECT COUNT(*) AS n FROM payments WHERE id IN ('ch_bad','ch_old')")[0].n === 0);
  r = await webhook({ id: "evt_re1", type: "refund.created", data: { object: { id: "re_test_1", object: "refund", amount: 1500, currency: "gbp", status: "succeeded", charge: "ch_test_1", created: nowS, reason: "requested_by_customer" } } });
  check("signed refund.created is accepted", r.status === 200);
  await webhook(charge("ch_last_month", 12000, lastMonth, { description: "Field jacket" }));
  await webhook({ id: "evt_ch2p", type: "charge.pending", data: { object: { id: "ch_pending", amount: 700, currency: "gbp", status: "pending", created: nowS } } });

  await page.click("[data-tab=transactions]"); await page.waitForSelector("[data-tx]");
  const txRows = await page.$$eval("[data-tx]", rs => rs.map(x => x.dataset.tx + ":" + x.querySelector(".pill").textContent + ":" + x.querySelector(".n").textContent));
  check("transactions tab lists the payments and the refund",
    txRows.includes("ch_test_1:Paid:£45.00") && txRows.includes("re_test_1:Refunded:−£15.00") && txRows.includes("ch_last_month:Paid:£120.00") && txRows.includes("ch_pending:Pending:£7.00"), txRows.join(" | "));
  check("refund row picked up the buyer name from its charge", sql(site, "SELECT customer FROM payments WHERE id = 're_test_1'")[0].customer === "Sam Buyer");
  await shot(page, "2-transactions");
  await page.click("[data-f=refund]"); await page.waitForSelector("[data-f=refund][aria-pressed=true]");
  check("transactions filter: refunds only", (await page.$$eval("[data-tx]", rs => rs.map(x => x.dataset.tx))).join() === "re_test_1");
  await page.click("[data-tab=analytics]"); await page.waitForSelector(".kpi");
  await page.click("[data-range=hour]"); await page.waitForSelector("[data-range=hour][aria-pressed=true]");
  check("analytics revenue/refunds read the payments table", await kpi("Revenue") === "£45" && await kpi("Refunds") === "£15", `${await kpi("Revenue")} / ${await kpi("Refunds")}`);
  await shot(page, "3-analytics");
  check("revenue chart drawn", !!(await page.$(".chart rect.rev")) && !!(await page.$(".chart rect.ref")));

  // ---------- statements: preview, opt-out toggle, STOP link ----------
  await page.click("[data-tab=statements]"); await page.waitForSelector(".email");
  const em = await page.textContent(".email");
  await shot(page, "4-statements");
  check("statement preview shows last month's real figures and the STOP line", em.includes("£120.00") && em.includes("Reply STOP to stop these emails"));
  await page.click("[data-tab=account]"); await page.waitForSelector("[data-act=stmtoff]");
  const tog = page.waitForResponse(x => x.url().endsWith("/api/owner/account") && x.request().method() === "PATCH");
  await page.click("[data-act=stmtoff]"); await tog;
  check("Account toggle sets opted_out", sql(site, `SELECT opted_out FROM users WHERE email = '${ownerEmail}'`)[0].opted_out === 1);
  await page.waitForSelector("[data-act=stmton]");
  const tog2 = page.waitForResponse(x => x.url().endsWith("/api/owner/account") && x.request().method() === "PATCH");
  await page.click("[data-act=stmton]"); await tog2;
  check("Account toggle turns statements back on", sql(site, `SELECT opted_out FROM users WHERE email = '${ownerEmail}'`)[0].opted_out === 0);
  const token = sql(site, `SELECT stop_token FROM users WHERE email = '${lockEmail}'`)[0].stop_token;
  const g = await fetch(`${BASE}/api/statements/stop?token=${token}`);
  check("GET /api/statements/stop only shows a confirm button", g.status === 200 && (await g.text()).includes("<form method=\"post\"") && sql(site, `SELECT opted_out FROM users WHERE email = '${lockEmail}'`)[0].opted_out === 0);
  const pst = await fetch(`${BASE}/api/statements/stop?token=${token}`, { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: "List-Unsubscribe=One-Click" });
  check("POST /api/statements/stop (one-click) sets opted_out", pst.status === 200 && sql(site, `SELECT opted_out FROM users WHERE email = '${lockEmail}'`)[0].opted_out === 1);
  const badTok = await fetch(`${BASE}/api/statements/stop?token=${"0".repeat(32)}`, { method: "POST" });
  check("unknown stop token changes nothing (404)", badTok.status === 404);

  // ---------- statements Worker: cron + inbound STOP ----------
  const mails = [];
  const mail = http.createServer((req, res) => { let b = ""; req.on("data", c => b += c); req.on("end", () => { mails.push({ auth: req.headers.authorization, body: JSON.parse(b) }); res.setHeader("Content-Type", "application/json"); res.end('{"id":"test"}'); }); }).listen(MAILPORT);
  const wdir = path.join(site, "statements-worker");
  const wok = await start(`${WR} dev --port ${WPORT} --ip 127.0.0.1 --persist-to ../.wrangler/state --var RESEND_API_KEY:re_test --var RESEND_API_URL:http://127.0.0.1:${MAILPORT}/emails --var SITE_URL:${BASE} --var SITE_NAME:Loftline`,
    wdir, "log", path.join(TMP, "worker-dev.log"));
  check("statements Worker starts under wrangler dev", wok, "see " + path.join(TMP, "worker-dev.log"));
  await sleep(500);
  const sched = await fetch(`http://127.0.0.1:${WPORT}/cdn-cgi/handler/scheduled?cron=${encodeURIComponent("0 7 1 * *")}`);
  await until(() => mails.length >= 1, 8000);
  await sleep(800);
  const m0 = mails[0] && mails[0].body;
  check("cron sends one statement (opted-out owner skipped)", sched.status === 200 && mails.length === 1 && m0.to[0] === ownerEmail, `${sched.status} mails=${mails.length}`);
  check("statement has real figures, the STOP line and List-Unsubscribe",
    m0 && m0.text.includes("£120.00") && m0.text.includes("Field jacket") && m0.text.includes("Reply STOP to stop these emails") && m0.html.includes("Reply STOP to stop these emails")
      && /api\/statements\/stop\?token=[a-f0-9]{32}/.test(m0.headers["List-Unsubscribe"]) && mails[0].auth === "Bearer re_test", m0 && m0.subject);
  await fetch(`http://127.0.0.1:${WPORT}/cdn-cgi/handler/scheduled?cron=${encodeURIComponent("0 7 1 * *")}`); await sleep(1500);
  check("re-running the cron does not send twice", mails.length === 1);
  const rawReply = (body, subject = "Re: Loftline: your statement") => `From: Owner <${ownerEmail}>\r\nTo: statements@kineticwebdesigns.co.uk\r\nSubject: ${subject}\r\nMessage-ID: <${crypto.randomUUID()}@test>\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n${body}`;
  const em1 = await fetch(`http://127.0.0.1:${WPORT}/cdn-cgi/handler/email?from=${encodeURIComponent(ownerEmail)}&to=statements%40kineticwebdesigns.co.uk`, { method: "POST", body: rawReply("Thanks, looks good!\r\n\r\nOn Mon, Kinetic wrote:\r\n> Reply STOP to stop these emails") });
  await sleep(600);
  check("an ordinary reply (quoting the STOP line) does not opt out", em1.status < 300 && sql(site, `SELECT opted_out FROM users WHERE email = '${ownerEmail}'`)[0].opted_out === 0, "status " + em1.status);
  const em2 = await fetch(`http://127.0.0.1:${WPORT}/cdn-cgi/handler/email?from=${encodeURIComponent(ownerEmail)}&to=statements%40kineticwebdesigns.co.uk`, { method: "POST", body: rawReply("STOP\r\n\r\nOn Mon, Kinetic wrote:\r\n> Hi, here's what your website took") });
  await until(() => sql(site, `SELECT opted_out FROM users WHERE email = '${ownerEmail}'`)[0].opted_out === 1, 4000, 300);
  check("emailed STOP reply sets opted_out (email handler)", em2.status < 300 && sql(site, `SELECT opted_out FROM users WHERE email = '${ownerEmail}'`)[0].opted_out === 1, "status " + em2.status);
  await page.click("[data-tab=statements]"); await page.waitForSelector("[data-act=stmton]");
  check("owner area shows statements stopped after the STOP reply", (await page.textContent(".status")).includes("Stopped"));
  mail.close();

  // ---------- logout ----------
  await page.click("[data-act=logout]"); await page.waitForSelector("#loginForm");
  const after = await page.evaluate(async () => (await fetch("/api/owner/account")).status);
  check("logout ends the session", after === 401 && sql(site, "SELECT COUNT(*) AS n FROM sessions")[0].n === 0);
  check("no JavaScript errors on owner or shop pages", pageErrors.length === 0, pageErrors.join(" | "));

  // ---------- Kinetic's own site ----------
  if (LIVE) await kineticLive(browser);
  await browser.close();
}

async function kineticLive(browser) {
  const dir = path.join(TMP, "kinetic-live");
  fs.mkdirSync(dir);
  for (const f of fs.readdirSync(LIVE)) {
    if (f === "clips") fs.symlinkSync(path.join(LIVE, f), path.join(dir, f));
    else fs.cpSync(path.join(LIVE, f), path.join(dir, f), { recursive: true });
  }
  const toml = fs.readFileSync(path.join(dir, "wrangler.toml"), "utf8");
  const vars = {}; for (const m of toml.matchAll(/^([A-Z_]+)\s*=\s*"([^"]*)"/gm)) vars[m[1]] = m[2];
  fs.writeFileSync(path.join(dir, "wrangler.toml"), toml.replace("REPLACE_WITH_D1_DATABASE_ID", DBID).replace('database_name = "kinetic-db"', 'database_name = "kit-test-db"'));
  sh(`${WR} d1 execute kit-test-db --local --file ${JSON.stringify(path.join(KIT, "schema.sql"))}`, dir);
  const pw = createOwner(dir, "alfred@kinetic.test", "kinetic.owner");
  const binds = Object.entries(vars).map(([k, v]) => `-b ${JSON.stringify(`${k}=${v}`)}`).join(" ");
  const ok = await start(`${WR} pages dev . --port ${LPORT} --ip 127.0.0.1 --d1 DB=${DBID} ${binds}`, dir, `http://127.0.0.1:${LPORT}/api/config`, path.join(TMP, "kinetic-dev.log"));
  check("kinetic-live serves with the kit under pages dev", ok);
  const B = `http://localhost:${LPORT}`;
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  const errs = []; page.on("pageerror", e => errs.push(e.message));
  // the sign-up DNS check calls dns.google; answer it locally so the test doesn't need the internet
  await ctx.route("https://dns.google/**", r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ Status: 0, Answer: [{ type: 15, data: "10 mx.example.com." }] }) }));
  await ctx.route(/^https?:\/\/(?!localhost)/, r => r.request().url().startsWith("https://dns.google") ? r.fallback() : r.abort());
  const tr = page.waitForResponse(r => r.url().endsWith("/api/track"));
  await page.goto(B + "/", { waitUntil: "domcontentloaded" });
  check("kinetic: page view is recorded", (await tr).status() === 204);
  await page.waitForSelector("#gate:not([hidden])", { timeout: 15000 });
  await page.fill("#gate-email", "someone@example.com");
  const sev = page.waitForResponse(r => r.url().endsWith("/api/event"), { timeout: 15000 });
  await page.click("#gate-go");
  check("kinetic: completed sign-up is counted", (await sev).status() === 204);
  await page.click("#menu-open");
  const link = await page.waitForSelector("#menu .owner-login", { state: "visible" });
  await sleep(900); await page.screenshot({ path: process.env.SHOTS ? path.join(process.env.SHOTS, "6-kinetic-menu.png") : path.join(TMP, "menu.png") });
  check("kinetic: side menu has the Owner's log in link", (await link.textContent()).includes("Owner's log in") && (await link.getAttribute("href")) === "/owner");
  await page.click("#menu-close");
  await page.fill("#v-name", "Test Person"); await page.fill("#v-biz", "Test Biz"); await page.fill("#v-look", "Bright and simple");
  await page.fill("#v-email", "someone@example.com");
  const qev = page.waitForResponse(r => r.url().endsWith("/api/event"), { timeout: 15000 });
  await page.$eval("#vision-form", f => f.requestSubmit());
  check("kinetic: sent brief is counted as a quote request", (await qev).status() === 204);
  await page.goto(B + "/owner");
  await page.waitForSelector("#loginForm");
  await login(page, "kinetic.owner", pw);
  await page.waitForSelector("#pwForm"); await changePw(page, "kinetic-owner-pass");
  await page.waitForSelector(".kpi");
  const tabs = await page.$$eval(".oa-tabs button", b => b.map(x => x.textContent));
  check("kinetic: owner area has no Products/Text tabs and opens on Analytics", tabs.join("|") === "Analytics|Transactions|Monthly statements|Account", tabs.join("|"));
  const k = await page.$$eval(".kpi", ks => Object.fromEntries(ks.map(x => [x.querySelector("span").textContent.split(",")[0], x.querySelector("b").textContent])));
  check("kinetic: analytics shows visitors, page views, sign-ups and quote requests", k["Visitors"] === "1" && k["Page views"] === "1" && k["Sign-ups"] === "1" && k["Quote requests"] === "1", JSON.stringify(k));
  check("kinetic: no revenue tiles until Stripe is connected", !("Revenue" in k));
  await shot(page, "5-kinetic-analytics-phone");
  await page.click("[data-tab=transactions]"); await page.waitForSelector(".panel");
  check("kinetic: transactions shows the connect empty state", (await page.textContent(".oa-body")).includes("aren't connected yet"));
  const sw = await page.evaluate(() => document.documentElement.scrollWidth);
  check("kinetic: owner area fits a 390px phone", sw <= 390, "scrollWidth " + sw);
  const prod = await page.evaluate(async () => (await fetch("/api/owner/products")).status);
  check("kinetic: products API is off when SHOP=0", prod === 404);
  check("kinetic: no JavaScript errors on the live page or owner area", errs.length === 0, errs.slice(0, 3).join(" | "));
}

main().then(() => {
  const failed = results.filter(r => !r.ok);
  console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
  stopAll();
  process.exit(failed.length ? 1 : 0);
}).catch(e => { console.error(e); stopAll(); process.exit(2); });
