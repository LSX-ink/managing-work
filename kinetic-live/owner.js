// Kinetic kit: the Owner area. Talks to /api/* (Pages Functions + D1 + R2).
// Every figure shown comes from the API; when there is no data the page says so.
(() => {
"use strict";
const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const app = $("#app");

let CFG = { siteName: "Your website", shop: false, text: false, events: [], currency: "gbp", stripe: false, photos: false };
let ME = null;
let tab = null, range = "day", txFilter = "all", confirmDel = null, leadKind = "briefs", confirmLead = null;
let catalog = null; // { lists: [...] } while on the Products tab

const money = (minor, cur = CFG.currency) => {
  try { return new Intl.NumberFormat("en-GB", { style: "currency", currency: cur.toUpperCase() }).format((minor || 0) / 100); }
  catch { return ((minor || 0) / 100).toFixed(2); }
};
const money0 = (minor, cur = CFG.currency) => {
  try { return new Intl.NumberFormat("en-GB", { style: "currency", currency: cur.toUpperCase(), maximumFractionDigits: 0 }).format((minor || 0) / 100); }
  catch { return String(Math.round((minor || 0) / 100)); }
};
const num = n => Number(n || 0).toLocaleString("en-GB");

let toastT;
function toast(msg) {
  let t = $(".toast");
  if (!t) { t = document.createElement("div"); t.className = "toast"; t.setAttribute("role", "status"); document.body.append(t); }
  t.textContent = msg; t.hidden = false; clearTimeout(toastT); toastT = setTimeout(() => (t.hidden = true), 2400);
}

// ---------- API ----------
class ApiError extends Error { constructor(msg, status, data) { super(msg); this.status = status; this.data = data; } }
async function api(path, { method = "GET", body, raw, type } = {}) {
  const opts = { method, headers: {}, credentials: "same-origin" };
  if (raw) { opts.body = raw; opts.headers["Content-Type"] = type; }
  else if (body !== undefined) { opts.body = JSON.stringify(body); opts.headers["Content-Type"] = "application/json"; }
  const res = await fetch(path, opts);
  let data = null;
  try { data = await res.json(); } catch {}
  if (!res.ok) {
    if (res.status === 401 && path !== "/api/auth/login" && path !== "/api/auth/me") { ME = null; renderLogin("Your login has ended. Log in again."); }
    else if (res.status === 403 && data && data.mustChange) renderChangePw(true);
    throw new ApiError((data && data.error) || "Something went wrong. Try again.", res.status, data);
  }
  return data;
}
const fail = e => { if (e && e.status !== 401 && !(e.data && e.data.mustChange)) toast(e.message || "Something went wrong"); };

// ---------- shells ----------
const top = (sub, right = "") => `<div class="oa-top"><div class="row"><h1>${esc(CFG.siteName)} <small>· ${esc(sub)}</small></h1><div class="sp">${right}</div></div>`;
function renderLogin(error = "", forgot = false) {
  document.title = "Owner's log in";
  app.innerHTML = `${top("Owner's log in", `<a class="btn ghost sm" href="/">Back to website</a>`)}</div>
    <div class="login"><form id="loginForm" novalidate>
      <h2>Owner's log in</h2>
      <p class="hint">Only the owner of ${esc(CFG.siteName)} can log in here. Your first login details come from Kinetic Web Designs by email.</p>
      <label class="f" for="lgUser">Username<input class="t" id="lgUser" type="text" autocomplete="username" autocapitalize="none" spellcheck="false" required></label>
      <label class="f" for="lgPw">Password<input class="t" id="lgPw" type="password" autocomplete="current-password" required></label>
      ${error ? `<p class="err" role="alert">${esc(error)}</p>` : ""}
      <button class="btn accent" type="submit">Log in</button>
      <button class="linkish" type="button" data-act="forgot">Forgot your password?</button>
      ${forgot ? `<p class="hint" role="status">Message Kinetic Web Designs and we'll reset it. You'll get a new temporary password by email, and you'll choose your own private one when you log in. We can reset your password, but we can never see it.</p>` : ""}
    </form></div>`;
  const last = sessionStorageGet("kk-user");
  if (last) $("#lgUser").value = last;
  (last ? $("#lgPw") : $("#lgUser")).focus();
}
function renderChangePw(first, error = "") {
  document.title = first ? "Choose your password" : "Change password";
  app.innerHTML = `${top(first ? "First login" : "Change password", first ? "" : `<button class="btn ghost sm" type="button" data-act="tab" data-tab="account">Cancel</button>`)}</div>
    <div class="login"><form id="pwForm" novalidate>
      <h2>${first ? "Choose your own password" : "Change your password"}</h2>
      <p class="hint">${first ? "This replaces the temporary one we sent you, so only you know it. Use at least 10 characters." : "Use at least 10 characters."}</p>
      ${first ? "" : `<label class="f" for="pw0">Current password<input class="t" id="pw0" type="password" autocomplete="current-password"></label>`}
      <label class="f" for="pw1">New password<input class="t" id="pw1" type="password" autocomplete="new-password" minlength="10"></label>
      <label class="f" for="pw2">Type it again<input class="t" id="pw2" type="password" autocomplete="new-password"></label>
      ${error ? `<p class="err" role="alert">${esc(error)}</p>` : ""}
      <button class="btn accent" type="submit">Save password</button></form></div>`;
  (first ? $("#pw1") : $("#pw0")).focus();
}
function sessionStorageGet(k) { try { return sessionStorage.getItem(k); } catch { return null; } }
function sessionStorageSet(k, v) { try { sessionStorage.setItem(k, v); } catch {} }

function tabs() {
  const t = [];
  if (CFG.shop) t.push(["products", "Products & stock"]);
  if (CFG.text) t.push(["text", "Text"]);
  t.push(["analytics", "Analytics"], ["leads", "Sign-ups & briefs"], ["transactions", "Transactions"], ["statements", "Monthly statements"], ["account", "Account"]);
  return t;
}
function renderOwner() {
  const T = tabs();
  if (!T.some(([id]) => id === tab)) tab = T[0][0];
  document.title = `${CFG.siteName} · Owner area`;
  app.innerHTML = `${top("Owner area", `<a class="btn ghost sm" href="/">View website</a><button class="btn ghost sm" type="button" data-act="logout">Log out</button>`)}
      <div class="oa-tabs" role="tablist">${T.map(([id, l]) => `<button type="button" role="tab" aria-selected="${tab === id}" data-act="tab" data-tab="${id}">${l}</button>`).join("")}</div></div>
    <div class="oa-body" id="body"><p class="loading">Loading…</p></div>`;
  try { history.replaceState(null, "", "#" + tab); } catch {}
  loadTab();
}
const body = () => $("#body");
async function loadTab(keepScroll) {
  const y = keepScroll ? window.scrollY : 0;
  const t = tab;
  try {
    const html = await ({ products: vProducts, text: vText, analytics: vAnalytics, leads: vLeads, transactions: vTx, statements: vStatements, account: vAccount })[t]();
    if (t !== tab || !body()) return;
    body().innerHTML = html;
    // on narrow screens charts scroll sideways: start at the newest end
    body().querySelectorAll(".chart").forEach(c => { c.scrollLeft = c.scrollWidth; });
    if (keepScroll) window.scrollTo(0, y);
  } catch (e) {
    if (body() && e.status !== 401) body().innerHTML = `<section class="panel"><p class="err">${esc(e.message)}</p></section>`;
  }
}

// ---------- Products & stock ----------
const totalQty = it => it.sizes.reduce((a, z) => a + (+z.qty || 0), 0);
const isOut = it => !it.inStock || (it.sizes.length > 0 && totalQty(it) === 0);
async function vProducts() {
  catalog = await api("/api/owner/products");
  return productsHtml();
}
function productsHtml() {
  const lists = catalog.lists;
  return `<p class="hint">Changes go live on your website as soon as you make them. Tap "View website" to check.</p>
    ${lists.length ? "" : `<section class="panel"><div class="empty"><b>No product lists yet</b>Start with a list, for example "New in", then add products to it.</div></section>`}
    ${lists.map(l => `<section class="panel" data-listbox="${l.id}"><div class="hd">
        <input class="list-title" aria-label="List name" data-ln="${l.id}" value="${esc(l.title)}">
        <span style="display:flex;gap:8px;flex-wrap:wrap">${l.items.length ? "" : `<button class="btn danger sm" type="button" data-act="dellist" data-list="${l.id}">Remove list</button>`}
        <button class="btn accent sm" type="button" data-act="add" data-list="${l.id}">+ Add product</button></span></div>
      <div class="items">${l.items.length ? l.items.map(itemRow).join("") : `<p class="hint">No products in this list yet. Tap "Add product" to put your first one up.</p>`}</div></section>`).join("")}
    <div><button class="btn ghost" type="button" data-act="addlist">+ Add a product list</button></div>`;
}
function stockHint(it) {
  const q = totalQty(it);
  return it.sizes.length ? `${q} in stock across ${it.sizes.length} size${it.sizes.length > 1 ? "s" : ""}${q === 0 ? ", shows as out of stock" : ""}` : "No sizes, uses the switch only";
}
function itemRow(it) {
  const out = isOut(it);
  return `<div class="item ${out ? "out" : ""} ${it.visible ? "" : "hiddenp"}" data-item="${it.id}">
    <div class="ph">${it.img ? `<img src="${esc(it.img)}" alt="">` : `<div class="noimg">No photo yet</div>`}
      <label class="btn ghost sm upl">${it.img ? "Change photo" : "Add photo"}<input type="file" accept="image/jpeg,image/png,image/webp,image/gif,image/avif" data-up="${it.id}" aria-label="Upload a photo for ${esc(it.name)}"></label></div>
    <div class="fields">
      <div class="r1"><label class="f" for="n-${it.id}">Name<input class="t" id="n-${it.id}" data-f="name" value="${esc(it.name)}" maxlength="120"></label>
        <label class="f" for="p-${it.id}">Price (£)<input class="t" id="p-${it.id}" data-f="price" type="number" min="0" step="0.01" inputmode="decimal" value="${(it.price / 100).toFixed(2)}"></label></div>
      <div class="r2"><button type="button" class="sw" aria-pressed="${it.inStock}" data-act="stock">${it.inStock ? "In stock" : "Out of stock"}<i></i></button>
        <button type="button" class="sw vis" aria-pressed="${it.visible}" data-act="visible">${it.visible ? "Shown on website" : "Hidden"}<i></i></button>
        <span class="hint" data-hint>${stockHint(it)}</span>
        <span style="margin-left:auto"></span>
        ${confirmDel === it.id ? `<span class="confirm">Remove ${esc(it.name)} from your website?<button class="btn danger sm" type="button" data-act="delyes">Remove</button><button class="btn ghost sm" type="button" data-act="delno">Keep</button></span>`
          : `<button class="btn danger sm" type="button" data-act="del">Remove</button>`}</div>
      <div class="sizes">${it.sizes.length ? `<table><thead><tr><th>Size name</th><th>Stock</th><th>Show</th><th></th></tr></thead><tbody>
        ${it.sizes.map(z => `<tr data-size="${esc(z.id)}"><td><input class="t l" aria-label="Size name" data-z="label" value="${esc(z.label)}" maxlength="40"></td>
          <td><input class="t q" aria-label="Stock for ${esc(z.label)}" data-z="qty" type="number" min="0" step="1" inputmode="numeric" value="${z.qty}"></td>
          <td><label class="chk"><input type="checkbox" data-z="show" ${z.show ? "checked" : ""}> Show</label></td>
          <td><button class="iconbtn" type="button" aria-label="Remove size ${esc(z.label)}" data-act="delsize">×</button></td></tr>`).join("")}</tbody></table>` : ""}
        <div><button class="btn ghost sm" type="button" data-act="addsize">+ Add a size</button></div></div>
    </div></div>`;
}
function findItem(el) {
  const row = el.closest("[data-item]"); if (!row || !catalog) return {};
  const id = +row.dataset.item;
  for (const l of catalog.lists) { const it = l.items.find(x => x.id === id); if (it) return { l, it, row }; }
  return {};
}
function replaceItem(updated) {
  for (const l of catalog.lists) { const i = l.items.findIndex(x => x.id === updated.id); if (i >= 0) l.items[i] = updated; }
}
function rerenderProducts() { if (tab === "products" && body()) { const y = window.scrollY; body().innerHTML = productsHtml(); window.scrollTo(0, y); } }
async function patchItem(it, changes, rerender = true) {
  const { product } = await api(`/api/owner/products/${it.id}`, { method: "PATCH", body: changes });
  replaceItem(product);
  if (rerender) rerenderProducts();
  return product;
}
const pending = new Map();
function debounce(key, fn, ms = 450) { clearTimeout(pending.get(key)); pending.set(key, setTimeout(() => { pending.delete(key); fn(); }, ms)); }

async function shrinkImage(file) {
  // Big phone photos are scaled down to 1600px before upload; small ones go as they are.
  if (file.size < 1.5e6 && /^image\/(jpeg|png|webp)$/.test(file.type)) return { blob: file, type: file.type };
  if (file.type === "image/gif" || file.type === "image/avif") return { blob: file, type: file.type };
  const url = URL.createObjectURL(file);
  try {
    const im = await new Promise((ok, no) => { const i = new Image(); i.onload = () => ok(i); i.onerror = no; i.src = url; });
    const scale = Math.min(1, 1600 / Math.max(im.naturalWidth, im.naturalHeight));
    const c = document.createElement("canvas");
    c.width = Math.round(im.naturalWidth * scale); c.height = Math.round(im.naturalHeight * scale);
    c.getContext("2d").drawImage(im, 0, 0, c.width, c.height);
    const blob = await new Promise(ok => c.toBlob(ok, "image/jpeg", .85));
    return { blob, type: "image/jpeg" };
  } finally { URL.revokeObjectURL(url); }
}

// ---------- Text ----------
let textFields = [];
async function vText() {
  const { fields } = await api("/api/owner/text");
  textFields = fields;
  if (!fields.length) return `<section class="panel"><h2>Website text</h2><div class="empty"><b>No editable text on this website yet</b>Ask Kinetic Web Designs which parts of your website you'd like to edit yourself.</div></section>`;
  return `<section class="panel"><h2>Website text</h2><p class="hint">Whatever you type here is what shows on your website. Changes save as you type.</p>
    ${fields.map(f => `<label class="f" for="tx-${esc(f.key)}">${esc(f.label)}${f.multiline
      ? `<textarea class="t" id="tx-${esc(f.key)}" data-t="${esc(f.key)}" style="min-height:120px">${esc(f.value)}</textarea>`
      : `<input class="t" id="tx-${esc(f.key)}" data-t="${esc(f.key)}" value="${esc(f.value)}">`}</label>`).join("")}</section>`;
}
const textDirty = {};
function saveText() {
  const values = { ...textDirty }; for (const k in textDirty) delete textDirty[k];
  if (!Object.keys(values).length) return;
  api("/api/owner/text", { method: "PUT", body: { values } }).then(() => toast("Saved")).catch(fail);
}

// ---------- charts ----------
const COLS = ["var(--c1)", "var(--c2)", "var(--c3)", "var(--c4)", "var(--c5)"];
function donut(parts) {
  parts = parts.filter(p => p[1] > 0);
  const tot = parts.reduce((a, p) => a + p[1], 0);
  if (!tot) return `<div class="empty">Nothing to show yet</div>`;
  let a0 = -Math.PI / 2; const R = 50, r = 30, c = 60;
  const segs = parts.map(([, v, col]) => {
    const a1 = a0 + (v / tot) * Math.PI * 2; const big = a1 - a0 > Math.PI ? 1 : 0;
    const p = (ang, rad) => `${(c + rad * Math.cos(ang)).toFixed(2)} ${(c + rad * Math.sin(ang)).toFixed(2)}`;
    const d = v / tot >= .9999 ? `M${c} ${c - R}A${R} ${R} 0 1 1 ${c - .01} ${c - R}L${c - .01} ${c - r}A${r} ${r} 0 1 0 ${c} ${c - r}Z`
      : `M${p(a0, R)}A${R} ${R} 0 ${big} 1 ${p(a1, R)}L${p(a1, r)}A${r} ${r} 0 ${big} 0 ${p(a0, r)}Z`;
    a0 = a1; return `<path d="${d}" fill="${col}" stroke="var(--surface)" stroke-width="1.5"/>`;
  }).join("");
  const pct = v => { const x = v / tot * 100; return x > 0 && x < 1 ? "<1%" : Math.round(x) + "%"; };
  return `<div class="pie"><svg viewBox="0 0 120 120" role="img" aria-label="${esc(parts.map(p => `${p[0]} ${pct(p[1])}`).join(", "))}">${segs}</svg>
    <div class="leg">${parts.map(([l, v, col]) => `<div><i style="background:${col}"></i><span title="${esc(l)}">${esc(l)}</span><b title="${num(v)}">${pct(v)}</b></div>`).join("")}</div></div>`;
}
// series: [{ key, cls, label }]; overlap = draw on top of each other (biggest first)
function barChart(data, series, { fmt = num, overlap = false, label = "" } = {}) {
  const vals = data.flatMap(d => series.map(s => d[s.key] || 0));
  const max = Math.max(...vals, 0);
  if (!max) return null;
  // four equal steps of 1, 2 or 5 x 10^n, so axis labels stay round (whole pounds or whole counts)
  const raw = Math.max(max / 4, fmt === num ? 1 : 100), mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 5, 10].map(m => m * mag).find(v => v >= raw);
  const topV = step * 4;
  const W = 720, H = 240, L = 58, B = 26, T = 10, bw = (W - L - 10) / data.length;
  const y = v => T + (H - T - B) * (1 - v / topV);
  const ticks = [0, .25, .5, .75, 1].map(f => topV * f);
  const every = Math.ceil(data.length / 12);
  const bars = data.map((d, i) => {
    const x0 = L + i * bw + bw * .15, w = bw * .7;
    const parts = series.map((s, j) => {
      const v = d[s.key] || 0; if (!v) return "";
      const bx = overlap ? x0 : x0 + j * (w / series.length), bwid = overlap ? w : w / series.length;
      return `<rect class="${s.cls}" x="${bx.toFixed(1)}" y="${y(v).toFixed(1)}" width="${Math.max(bwid - (overlap ? 0 : 1), 1).toFixed(1)}" height="${(y(0) - y(v)).toFixed(1)}" rx="2"><title>${esc(d.label)}: ${esc(s.label)} ${esc(fmt(v))}</title></rect>`;
    }).join("");
    return parts + (i % every === 0 ? `<text x="${(x0 + w / 2).toFixed(1)}" y="${H - 8}" text-anchor="middle">${esc(d.label)}</text>` : "");
  }).join("");
  return `<div class="chart"><svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="${esc(label)}">
    ${ticks.map(t => `<line class="grid" x1="${L}" x2="${W - 6}" y1="${y(t).toFixed(1)}" y2="${y(t).toFixed(1)}"/><text x="${L - 8}" y="${(y(t) + 4).toFixed(1)}" text-anchor="end">${esc(fmt(t))}</text>`).join("")}${bars}</svg></div>`;
}
const legend = items => `<div class="legend-inline">${items.map(([l, c]) => `<span><i style="background:${c}"></i>${esc(l)}</span>`).join("")}</div>`;

// ---------- Analytics ----------
const RANGE_LABELS = { minute: "Last hour", hour: "Last 24 hours", day: "Last 7 days", week: "Last 12 weeks", month: "Last 12 months", year: "Last 5 years" };
async function vAnalytics() {
  const tz = -new Date().getTimezoneOffset();
  const a = await api(`/api/owner/analytics?range=${range}&tz=${tz}`);
  const T = a.totals, lab = a.label.toLowerCase();
  const showMoney = a.stripe || a.hasPayments;
  const change = T.visitorsPrev24h > 0 ? Math.round((T.visitors24h - T.visitorsPrev24h) / T.visitorsPrev24h * 100) : null;
  const kpis = [
    `<div class="kpi"><span>Visitors, last 24 hours</span><b>${num(T.visitors24h)}</b><small class="${change > 0 ? "up" : change < 0 ? "down" : ""}">${change === null ? "No visits the day before to compare" : `${change > 0 ? "▲" : change < 0 ? "▼" : ""} ${Math.abs(change)}% on the day before`}</small></div>`,
    `<div class="kpi"><span>Page views, ${esc(lab)}</span><b>${num(T.views)}</b><small>${num(T.visitors)} visitor${T.visitors === 1 ? "" : "s"}</small></div>`,
    ...a.events.map(e => `<div class="kpi" data-kpi="${esc(e.name)}"><span>${esc(e.label)}, ${esc(lab)}</span><b>${num(T.events[e.name])}</b><small>${T.visitors ? `${(T.events[e.name] / T.visitors * 100).toFixed(1)}% of visitors` : "&nbsp;"}</small></div>`),
    ...(showMoney ? [
      `<div class="kpi"><span>Revenue, ${esc(lab)}</span><b>${money0(T.revenue)}</b><small>${num(T.payments)} payment${T.payments === 1 ? "" : "s"}</small></div>`,
      `<div class="kpi"><span>Refunds, ${esc(lab)}</span><b>${money0(T.refunds)}</b><small class="${T.revenue && T.refunds / T.revenue > .03 ? "down" : ""}">${T.revenue ? (T.refunds / T.revenue * 100).toFixed(1) + "% of revenue" : "&nbsp;"}</small></div>`] : [])
  ];
  const visChart = barChart(a.buckets, [{ key: "views", cls: "views", label: "Page views" }, { key: "visitors", cls: "vis", label: "Visitors" }], { overlap: true, label: `Visitors ${a.per}` });
  const evData = a.buckets.map(b => ({ label: b.label, ...b.events }));
  const evChart = a.events.length ? barChart(evData, a.events.map((e, i) => ({ key: e.name, cls: "e" + (i % 4), label: e.label })), { label: `Events ${a.per}` }) : null;
  const evCols = ["var(--c2)", "var(--c4)", "var(--c5)", "var(--c1)"];
  const moneyChart = showMoney ? barChart(a.buckets, [{ key: "revenue", cls: "rev", label: "Revenue" }, { key: "refunds", cls: "ref", label: "Refunds" }], { overlap: true, fmt: v => money0(v), label: `Revenue ${a.per}` }) : null;

  const noVisits = !T.views;
  const pages = a.topPages.slice(0, 5).map((p, i) => [p.path, p.views, COLS[i % 5]]);
  const restPages = a.topPages.slice(5).reduce((s, p) => s + p.views, 0) + Math.max(0, T.views - a.topPages.reduce((s, p) => s + p.views, 0));
  if (restPages) pages.push(["Other pages", restPages, "var(--muted)"]);
  const srcs = a.sources.slice(0, 5).map((s, i) => [s.host || "Typed your address or a bookmark", s.views, COLS[i % 5]]);
  const restSrc = a.sources.slice(5).reduce((s, x) => s + x.views, 0);
  if (restSrc) srcs.push(["Other sites", restSrc, "var(--muted)"]);
  const devName = { phone: "Phone", computer: "Computer", tablet: "Tablet" };
  const devCol = { phone: COLS[0], computer: COLS[2], tablet: COLS[4] };

  return `<div class="hd" style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between">
      <div class="seg" role="group" aria-label="Time range">${Object.entries(RANGE_LABELS).map(([k, v]) => `<button type="button" data-act="range" data-range="${k}" aria-pressed="${range === k}">${v}</button>`).join("")}</div></div>
    <div class="kpis">${kpis.join("")}</div>
    <section class="panel"><div class="hd"><h2>Visitors ${esc(a.per)}</h2>${legend([["Page views", "color-mix(in srgb, var(--accent) 35%, transparent)"], ["Visitors", "var(--c3)"]])}</div>
      ${visChart || `<div class="empty"><b>No visits recorded ${esc(lab === "last hour" ? "in the last hour" : "in this period")} yet</b>Visits show here as soon as people open your website.</div>`}</section>
    ${a.events.length ? `<section class="panel"><div class="hd"><h2>${esc(a.events.map(e => e.label).join(" and "))} ${esc(a.per)}</h2>${legend(a.events.map((e, i) => [e.label, evCols[i % 4]]))}</div>
      ${evChart || `<div class="empty"><b>None ${esc(lab === "last hour" ? "in the last hour" : "in this period")} yet</b>Each one is counted when the form is sent.</div>`}</section>` : ""}
    ${showMoney ? `<section class="panel"><div class="hd"><h2>Revenue ${esc(a.per)}</h2>${legend([["Revenue", "var(--accent)"], ["Refunds", "var(--bad)"]])}</div>
      ${moneyChart || `<div class="empty"><b>No payments in this period</b>Card payments show here as Stripe reports them.</div>`}</section>` : ""}
    <div class="pies">
      <section class="panel"><h2>Top pages</h2>${noVisits ? `<div class="empty">No page views yet</div>` : donut(pages) +
        `<div class="toprows">${a.topPages.slice(0, 10).map(p => `<div><span title="${esc(p.path)}">${esc(p.path)}</span><b>${num(p.views)}</b></div>`).join("")}</div>`}</section>
      <section class="panel"><h2>Where visitors come from</h2>${noVisits ? `<div class="empty">No page views yet</div>` : donut(srcs)}</section>
      <section class="panel"><h2>Phone or computer</h2>${noVisits ? `<div class="empty">No page views yet</div>` : donut(a.devices.map(d => [devName[d.device] || d.device, d.views, devCol[d.device] || COLS[1]]))}</section>
      ${showMoney ? `<section class="panel"><h2>Money in and out</h2>${T.revenue ? donut([["Kept as revenue", Math.max(0, T.revenue - T.refunds), "var(--c3)"], ["Refunded", T.refunds, "var(--bad)"]]) : `<div class="empty">No payments in this period</div>`}</section>` : ""}
    </div>
    <p class="hint">Counted without cookies: a visitor is recognised only within one day, and no IP addresses are stored.</p>`;
}

// ---------- Transactions ----------
const connectPanel = title => `<section class="panel"><h2>${title}</h2>
  <p class="hint">Card payments aren't connected yet. Kinetic Web Designs connects your website to Stripe, the card payment service, so every payment and refund shows here. Stripe pays the money straight into your bank account, and we never see your bank details.</p>
  <p class="hint">To get set up, message Kinetic Web Designs.</p></section>`;
async function vTx() {
  const d = await api(`/api/owner/transactions?filter=${txFilter}`);
  if (!d.stripe && !d.any) return connectPanel("Transactions");
  const fmt = t => new Date(t).toLocaleString("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
  const pill = r => {
    if (r.kind === "refund") return `<span class="pill refund">${r.status === "succeeded" ? "Refunded" : r.status === "pending" ? "Refund pending" : "Refund " + esc(r.status)}</span>`;
    return `<span class="pill ${r.status === "succeeded" ? "paid" : r.status === "pending" ? "pending" : "failed"}">${{ succeeded: "Paid", pending: "Pending", failed: "Failed" }[r.status] || esc(r.status)}</span>`;
  };
  return `<section class="panel"><div class="hd"><h2>Transaction history</h2></div>
    <div class="status"><span class="dot ${d.stripe ? "" : "off"}"></span>${d.stripe ? "Card payments connected through Stripe" : "Stripe is not connected right now; showing payments recorded earlier"}</div>
    <div class="seg" role="group" aria-label="Filter">${[["all", "All"], ["paid", "Paid"], ["refund", "Refunds"], ["pending", "Pending"]].map(([k, l]) => `<button type="button" data-act="txf" data-f="${k}" aria-pressed="${txFilter === k}">${l}</button>`).join("")}</div>
    ${d.transactions.length ? `<div class="tbl"><table><thead><tr><th>When</th><th>Reference</th><th>What</th><th>Status</th><th style="text-align:right">Amount</th></tr></thead><tbody>
    ${d.transactions.map(r => `<tr data-tx="${esc(r.id)}"><td>${fmt(r.created)}</td><td style="font-family:var(--mono);font-size:.78rem">${esc(r.id.slice(0, 14))}${r.id.length > 14 ? "…" : ""}</td>
      <td>${esc(r.description || (r.kind === "refund" ? "Refund" : "Card payment"))}${r.customer ? ` <span class="hint">· ${esc(r.customer)}</span>` : ""}</td>
      <td>${pill(r)}${r.livemode ? "" : `<span class="pill test">Test</span>`}</td>
      <td class="n">${r.kind === "refund" ? "−" : ""}${money(r.amount, r.currency)}</td></tr>`).join("")}
    </tbody></table></div>` : `<div class="empty"><b>${d.any ? "Nothing here for this filter" : "No payments yet"}</b>${d.any ? "" : "Payments show here as soon as someone pays."}</div>`}</section>`;
}

// ---------- Sign-ups & briefs ----------
async function vLeads() {
  const d = await api(`/api/owner/leads?kind=${leadKind}`);
  const when = t => new Date(t).toLocaleString("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
  const seg = `<div class="seg" role="group" aria-label="Show">${[["briefs", "Briefs"], ["signups", "Sign-ups"]].map(([k, l]) =>
    `<button type="button" data-act="leadkind" data-k="${k}" aria-pressed="${leadKind === k}">${l}</button>`).join("")}</div>`;
  const csv = d.total ? `<a class="btn ghost sm" href="/api/owner/leads?kind=${leadKind}&amp;format=csv" download>Download CSV</a>` : "";
  const mailNote = d.mail
    ? `<div class="status"><span class="dot"></span>${leadKind === "briefs" ? "New briefs are emailed to you as they arrive" : "New sign-ups get a welcome email"}</div>`
    : `<div class="status"><span class="dot off"></span>Email isn't set up yet: everything is saved here, but no emails are sent.</div>`;
  const del = r => confirmLead === r.id
    ? `<span class="hint">Delete?</span> <button class="btn sm" type="button" data-act="leadyes" data-id="${r.id}">Delete</button> <button class="btn ghost sm" type="button" data-act="leadno">Keep</button>`
    : `<button class="btn ghost sm" type="button" data-act="leaddel" data-id="${r.id}" aria-label="Delete">Delete</button>`;

  if (leadKind === "signups") {
    return `<section class="panel"><div class="hd"><h2>Sign-ups</h2>${csv}</div>${seg}${mailNote}
      <p class="hint">${num(d.total)} ${d.total === 1 ? "person has" : "people have"} signed up; ${num(d.marketing)} said yes to tips, offers and news. Only send marketing to those people.</p>
      ${d.rows.length ? `<div class="tbl"><table><thead><tr><th>Signed up</th><th>Email</th><th>Marketing</th><th>Welcome</th><th></th></tr></thead><tbody>
      ${d.rows.map(r => `<tr><td>${when(r.created)}</td><td>${esc(r.email)}</td>
        <td>${r.marketing ? `<span class="pill paid">Yes</span>` : `<span class="pill">No</span>`}</td>
        <td>${r.welcomed ? "Sent" : `<span class="hint">Not sent</span>`}</td><td class="n">${del(r)}</td></tr>`).join("")}
      </tbody></table></div>` : `<div class="empty"><b>No sign-ups yet</b>Emails from the sign-up box on your website show here.</div>`}</section>`;
  }
  const field = (l, v) => v ? `<div><span class="hint">${esc(l)}</span><div style="white-space:pre-wrap">${esc(v)}</div></div>` : "";
  return `<section class="panel"><div class="hd"><h2>Briefs</h2>${csv}</div>${seg}${mailNote}
    ${d.rows.length ? d.rows.map(r => { const b = r.data || {}; const col = Object.values(b.colours || {}).filter(Boolean);
      return `<details class="panel" style="margin-top:10px"><summary><b>${esc(r.business)}</b> · ${esc(r.name)} <span class="hint">· ${when(r.created)}</span></summary>
      <div style="display:grid;gap:8px;margin-top:10px">
        <div><a href="mailto:${esc(r.email)}">${esc(r.email)}</a>${r.phone ? ` · <a href="tel:${esc(r.phone)}">${esc(r.phone)}</a>` : ""}</div>
        ${field("What they do", b.what)}${field("Current website", b.currentSite)}${field("Look and feel", b.look)}${field("Sites they like", b.inspiration)}
        ${field("When", b.when)}${field("Style", b.style)}${field("Template", b.template)}${field("Package", b.package)}${field("Estimate", b.estimate)}
        ${col.length ? `<div><span class="hint">Colours</span><div>${col.map(c => `<span style="display:inline-block;width:18px;height:18px;border-radius:4px;vertical-align:middle;margin-right:4px;background:${esc(c)}"></span>${esc(c)} `).join("")}</div></div>` : ""}
        <div>${del(r)}</div></div></details>`; }).join("")
      : `<div class="empty"><b>No briefs yet</b>Briefs sent from "Start your website" on your site show here.</div>`}</section>`;
}

// ---------- Monthly statements ----------
function statementsToggle(acc) {
  return acc.statements
    ? `<button class="btn ghost sm" type="button" data-act="stmtoff">Stop these emails</button>`
    : `<button class="btn accent sm" type="button" data-act="stmton">Start these emails again</button>`;
}
function statementsStatus(acc) {
  return acc.statements ? `<span class="dot"></span>Sent to ${esc(acc.email)} on the 1st of every month`
    : `<span class="dot off"></span>Stopped${acc.optedOutAt ? ` on ${new Date(acc.optedOutAt).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}` : ""}. No more statements will be sent for ${esc(CFG.siteName)}.`;
}
async function vStatements() {
  const [acc, s] = await Promise.all([api("/api/owner/account"), api("/api/owner/statement")]);
  if (!s.stripe && !s.any) return `<section class="panel"><div class="hd"><h2>Monthly statements</h2>${statementsToggle(acc)}</div>
    <div class="status">${statementsStatus(acc)}</div>
    <p class="hint">Once card payments are connected, we email you a statement of your website's payments on the 1st of every month. Nothing is sent until then.</p></section>`;
  const st = s.statement;
  return `<section class="panel"><div class="hd"><h2>Monthly statement email</h2>${statementsToggle(acc)}</div>
    <div class="status">${statementsStatus(acc)}</div>
    <p class="hint">This is what your ${esc(st.label)} statement says, from the payments recorded so far:</p>
    <div class="email"><div class="meta"><span><b>From:</b> Kinetic Web Designs</span><span><b>To:</b> ${esc(acc.email)}</span><span><b>Subject:</b> ${esc(CFG.siteName)}: your ${esc(st.label)} statement</span></div>
      <p>${st.rows.length ? `Hi, here's what your website took in ${esc(st.label)}.` : `Hi, your website took no card payments in ${esc(st.label)}.`}</p>
      <table><tbody><tr><td>Payments (${st.payments})</td><td>${money(st.sales, st.currency)}</td></tr><tr><td>Refunds (${st.refundCount})</td><td>−${money(st.refunds, st.currency)}</td></tr>
        <tr><td><b>Total after refunds</b></td><td><b>${money(st.net, st.currency)}</b></td></tr></tbody></table>
      <p class="hint">Stripe's card fees aren't included; your Stripe dashboard shows them.</p>
      <p>The full list of payments is in your Owner area under Transactions.</p>
      <p class="stop">You get this email because card payments are connected to ${esc(CFG.siteName)}. <b>Reply STOP to stop these emails.</b></p></div></section>`;
}

// ---------- Account ----------
async function vAccount() {
  const acc = await api("/api/owner/account");
  return `<section class="panel"><h2>Your login</h2>
    <label class="f">Username<input class="t" value="${esc(acc.username || "")}" readonly></label>
    <p class="hint">Keep your username private. Statements go to ${esc(acc.email)}.</p>
    <div><button class="btn ghost" type="button" data-act="chpw">Change password</button></div>
    <p class="hint">Forgot it? Message Kinetic Web Designs and we'll send you a new temporary password. We can reset your password, but we can never see it.</p></section>
    <section class="panel"><div class="hd"><h2>Monthly statement emails</h2>${statementsToggle(acc)}</div>
    <div class="status" data-stmt-status>${statementsStatus(acc)}</div>
    <p class="hint">You can also reply STOP to any statement email.</p></section>`;
}

// ---------- events ----------
document.addEventListener("click", async e => {
  const b = e.target.closest("[data-act]"); if (!b) return;
  const act = b.dataset.act;
  const { l, it } = findItem(b);
  try {
    switch (act) {
      case "forgot": renderLogin("", true); break;
      case "logout": await api("/api/auth/logout", { method: "POST" }).catch(() => {}); ME = null; renderLogin(); toast("Logged out"); break;
      case "tab": tab = b.dataset.tab; confirmDel = null; ME && !ME.mustChange ? renderOwner() : null; break;
      case "range": range = b.dataset.range; loadTab(true); break;
      case "txf": txFilter = b.dataset.f; loadTab(true); break;
      case "leadkind": leadKind = b.dataset.k; confirmLead = null; loadTab(true); break;
      case "leaddel": confirmLead = +b.dataset.id; loadTab(true); break;
      case "leadno": confirmLead = null; loadTab(true); break;
      case "leadyes":
        await api(`/api/owner/leads?kind=${leadKind}&id=${+b.dataset.id}`, { method: "DELETE" });
        confirmLead = null; toast("Deleted"); loadTab(true); break;
      case "stock": await patchItem(it, { inStock: !it.inStock }); toast(!it.inStock ? `${it.name} is back in stock` : `${it.name} shows as out of stock`); break;
      case "visible": await patchItem(it, { visible: !it.visible }); toast(!it.visible ? `${it.name} is on your website` : `${it.name} is hidden from your website`); break;
      case "del": confirmDel = it.id; rerenderProducts(); break;
      case "delno": confirmDel = null; rerenderProducts(); break;
      case "delyes":
        await api(`/api/owner/products/${it.id}`, { method: "DELETE" });
        l.items = l.items.filter(x => x !== it); confirmDel = null; rerenderProducts(); toast(`Removed ${it.name}`); break;
      case "add": {
        const { product } = await api("/api/owner/products", { method: "POST", body: { listId: +b.dataset.list, name: "New product", price: 0 } });
        catalog.lists.find(x => x.id === +b.dataset.list).items.unshift(product); rerenderProducts();
        const first = $(`[data-item="${product.id}"] [data-f="name"]`); first?.focus(); first?.select();
        toast("Added. Upload a photo, then set the name and price."); break; }
      case "addlist": {
        const { list } = await api("/api/owner/lists", { method: "POST", body: { title: "New list" } });
        catalog.lists.push(list); rerenderProducts(); const inp = $(`[data-ln="${list.id}"]`); inp?.focus(); inp?.select(); break; }
      case "dellist":
        await api(`/api/owner/lists/${b.dataset.list}`, { method: "DELETE" });
        catalog.lists = catalog.lists.filter(x => x.id !== +b.dataset.list); rerenderProducts(); break;
      case "addsize": await patchItem(it, { sizes: [...it.sizes, { label: "New size", qty: 0, show: true }] }); break;
      case "delsize": { const zid = b.closest("[data-size]").dataset.size; await patchItem(it, { sizes: it.sizes.filter(z => z.id !== zid) }); break; }
      case "stmtoff": case "stmton":
        await api("/api/owner/account", { method: "PATCH", body: { statements: act === "stmton" } });
        toast(act === "stmton" ? "Statements will be sent again" : "Statements stopped"); loadTab(true); break;
      case "chpw": renderChangePw(false); break;
    }
  } catch (x) { fail(x); }
});

document.addEventListener("input", e => {
  const el = e.target;
  if (el.dataset.t) { textDirty[el.dataset.t] = el.value; debounce("text", saveText, 700); return; }
  if (el.dataset.ln) { const id = el.dataset.ln, v = el.value; debounce("ln" + id, () => api(`/api/owner/lists/${id}`, { method: "PATCH", body: { title: v } }).then(() => toast("Saved")).catch(fail)); return; }
  const { it, row } = findItem(el); if (!it) return;
  if (el.dataset.f === "name") { it.name = el.value; debounce("n" + it.id, () => patchItem(it, { name: it.name }, false).then(() => toast("Saved")).catch(fail)); }
  if (el.dataset.f === "price") {
    const v = Math.round(Math.max(0, parseFloat(el.value) || 0) * 100);
    it.price = v; debounce("p" + it.id, () => patchItem(it, { price: v }, false).then(() => toast("Saved")).catch(fail));
  }
  if (el.dataset.z) {
    const z = it.sizes.find(x => x.id === el.closest("[data-size]").dataset.size); if (!z) return;
    if (el.dataset.z === "label") z.label = el.value;
    if (el.dataset.z === "qty") z.qty = Math.max(0, parseInt(el.value, 10) || 0);
    if (el.dataset.z === "show") z.show = el.checked;
    row.classList.toggle("out", isOut(it));
    const h = row.querySelector("[data-hint]"); if (h) h.textContent = stockHint(it);
    debounce("z" + it.id, () => patchItem(it, { sizes: it.sizes }, false).then(p => { row.classList.toggle("out", p.out); toast("Saved"); }).catch(fail));
  }
});

document.addEventListener("change", async e => {
  const el = e.target; if (!el.dataset.up || !el.files || !el.files[0]) return;
  const { it } = findItem(el); const f = el.files[0];
  if (!/^image\//.test(f.type)) { toast("That file isn't a picture. Choose a JPG or PNG."); return; }
  const lbl = el.closest(".upl"); lbl?.classList.add("busy");
  try {
    const { blob, type } = await shrinkImage(f);
    if (blob.size > 5 * 1024 * 1024) { toast("That picture is too big. The limit is 5 MB."); return; }
    const { product } = await api(`/api/owner/products/${it.id}/photo`, { method: "POST", raw: blob, type });
    replaceItem(product); rerenderProducts(); toast("Photo updated");
  } catch (x) { fail(x); }
  finally { lbl?.classList.remove("busy"); }
});

document.addEventListener("submit", async e => {
  e.preventDefault();
  const btn = e.target.querySelector("[type=submit]"); if (btn) btn.disabled = true;
  try {
    if (e.target.id === "loginForm") {
      const username = $("#lgUser").value.trim().toLowerCase(), password = $("#lgPw").value;
      if (!username || !password) return renderLogin("Enter your username and password.");
      sessionStorageSet("kk-user", username);
      try {
        const r = await api("/api/auth/login", { method: "POST", body: { username, password } });
        ME = await api("/api/auth/me");
        if (r.mustChange) renderChangePw(true); else renderOwner();
      } catch (x) { renderLogin(x.message); }
    }
    if (e.target.id === "pwForm") {
      const first = !!(ME && ME.mustChange);
      const p1 = $("#pw1").value, p2 = $("#pw2").value, cur = $("#pw0") ? $("#pw0").value : undefined;
      if (p1.length < 10) return renderChangePw(first, "Use at least 10 characters.");
      if (p1 !== p2) return renderChangePw(first, "The two passwords don't match. Type them again.");
      try {
        await api("/api/auth/password", { method: "POST", body: { password: p1, current: cur } });
        ME = await api("/api/auth/me");
        tab = first ? null : "account"; renderOwner(); toast("Password saved. Only you know it now.");
      } catch (x) { if (x.status !== 401) renderChangePw(first, x.message); }
    }
  } finally { if (btn && btn.isConnected) btn.disabled = false; }
});

window.addEventListener("pagehide", () => { if (Object.keys(textDirty).length) saveText(); });

// ---------- start ----------
(async () => {
  try { CFG = await (await fetch("/api/config")).json(); } catch {}
  const h = location.hash.slice(1); if (h) tab = h;
  try {
    ME = await api("/api/auth/me");
    if (ME.mustChange) renderChangePw(true); else renderOwner();
  } catch { if (!ME) renderLogin(); }
})();
})();
