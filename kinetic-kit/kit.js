/* Kinetic kit: site-side snippet. Add to every page:  <script src="/kit.js" defer></script>
 *  - Counts a page view (POST /api/track). No cookies, nothing stored in the browser.
 *  - KineticKit.event("signup") counts a site event (names must be listed in the EVENTS variable).
 *  - <form data-kit-event="quote"> counts that event when the form is submitted.
 *  - Shop sites: fills <div data-kit-products> with the products from the Owner area,
 *    and any element with data-kit-text="key" with that text. Listen for the "kit:catalog"
 *    event on document to render products your own way (add data-kit-render="custom").
 */
(() => {
  "use strict";
  if (window.KineticKit) return;
  const send = (url, data) => {
    try {
      return fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data), keepalive: true, credentials: "omit" }).catch(() => {});
    } catch { return Promise.resolve(); }
  };
  const refHost = () => {
    try { const h = document.referrer ? new URL(document.referrer).host : ""; return h && h !== location.host ? h : ""; } catch { return ""; }
  };
  let lastPath = null;
  function track(path) {
    path = path || location.pathname;
    if (path === lastPath || /^\/owner(\.html)?$/.test(path)) return;
    lastPath = path;
    send("/api/track", { p: path, r: refHost() });
  }
  function event(name) { return send("/api/event", { name: String(name), p: location.pathname }); }

  // ---------- forms marked data-kit-event ----------
  document.addEventListener("submit", e => {
    const f = e.target.closest && e.target.closest("form[data-kit-event]");
    if (f && f.checkValidity()) event(f.dataset.kitEvent);
  }, true);

  // ---------- Kinetic's own site: count sign-ups and briefs once they succeed ----------
  // The sign-up pop-up (#gate) closes only after a valid sign-up; the brief form fills #v-done
  // only after a valid brief. Watching those avoids counting forms that failed validation.
  function kineticHooks() {
    const gate = document.getElementById("gate"), gateForm = document.getElementById("gate-form");
    if (gate && gateForm) {
      let submitted = false;
      gateForm.addEventListener("submit", () => { submitted = true; }, true);
      new MutationObserver(() => { if (submitted && gate.hidden) { submitted = false; event("signup"); } })
        .observe(gate, { attributes: true, attributeFilter: ["hidden"] });
    }
    const done = document.getElementById("v-done");
    if (done && document.getElementById("vision-form")) {
      new MutationObserver(() => { if (!done.hidden && done.classList.contains("sent") && done.childNodes.length) event("quote"); })
        .observe(done, { childList: true });
    }
  }

  // ---------- products and text ----------
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  function price(minor, cur) {
    try { return new Intl.NumberFormat("en-GB", { style: "currency", currency: (cur || "gbp").toUpperCase() }).format(minor / 100); }
    catch { return (minor / 100).toFixed(2); }
  }
  const CSS = `.kk-list{margin:0 0 32px}.kk-list h2{margin:0 0 14px}.kk-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,210px),1fr));gap:18px}
.kk-card{display:grid;gap:8px;align-content:start;position:relative}.kk-card img,.kk-card .kk-noimg{width:100%;aspect-ratio:4/5;object-fit:cover;border-radius:10px;background:color-mix(in srgb,currentColor 8%,transparent);display:block}
.kk-name{font-weight:600}.kk-price{opacity:.8;font-variant-numeric:tabular-nums}.kk-sizes{display:flex;gap:6px;flex-wrap:wrap}
.kk-sizes span{border:1px solid color-mix(in srgb,currentColor 30%,transparent);border-radius:999px;padding:2px 10px;font-size:.78rem;font-weight:600}
.kk-sizes span.kk-none{opacity:.35;text-decoration:line-through}.kk-card.kk-out img{filter:grayscale(1);opacity:.55}.kk-card.kk-out .kk-name,.kk-card.kk-out .kk-price{opacity:.5}
.kk-flag{position:absolute;top:10px;left:10px;background:currentColor;border-radius:999px;padding:5px 9px;font-size:.72rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase}
.kk-flag b{color:Canvas;font-weight:700}`;
  function render(box, data) {
    if (!document.getElementById("kk-css")) { const st = document.createElement("style"); st.id = "kk-css"; st.textContent = CSS; document.head.append(st); }
    const only = box.dataset.kitProducts;
    const lists = only ? data.lists.filter(l => String(l.id) === only || l.title === only) : data.lists;
    box.innerHTML = lists.map(l => `<section class="kk-list"><h2>${esc(l.title)}</h2><div class="kk-grid">${l.items.map(it => {
      const sizes = it.sizes.length ? `<div class="kk-sizes">${it.sizes.map(z => `<span class="${z.available ? "" : "kk-none"}">${esc(z.label)}</span>`).join("")}</div>` : "";
      return `<article class="kk-card${it.outOfStock ? " kk-out" : ""}" data-product="${it.id}">${it.outOfStock ? `<span class="kk-flag"><b>Out of stock</b></span>` : ""}
        ${it.img ? `<img src="${esc(it.img)}" alt="${esc(it.name)}" loading="lazy">` : `<div class="kk-noimg" role="img" aria-label="${esc(it.name)}"></div>`}
        <div class="kk-name">${esc(it.name)}</div><div class="kk-price">${price(it.price, data.currency)}</div>${sizes}</article>`;
    }).join("")}</div></section>`).join("") || `<p class="kk-empty">${esc(box.dataset.kitEmpty || "New products coming soon.")}</p>`;
  }
  async function loadCatalog() {
    const boxes = document.querySelectorAll("[data-kit-products]"), texts = document.querySelectorAll("[data-kit-text]");
    if (!boxes.length && !texts.length) return;
    let data;
    try { const r = await fetch("/api/public/catalog", { credentials: "omit" }); if (!r.ok) return; data = await r.json(); } catch { return; }
    texts.forEach(el => { const v = data.text[el.dataset.kitText]; if (typeof v === "string" && v !== "") el.textContent = v; });
    boxes.forEach(box => { if (box.dataset.kitRender !== "custom") render(box, data); });
    document.dispatchEvent(new CustomEvent("kit:catalog", { detail: data }));
  }

  window.KineticKit = { track, event, reloadCatalog: loadCatalog };
  const start = () => { track(); kineticHooks(); loadCatalog(); };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
