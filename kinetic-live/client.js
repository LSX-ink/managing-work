// Client sign-in and account pages (owner, 16 Nov 2026): email and password (or Google). Signing in is needed
// before buying; "Forgot your password?" emails a one-time link that leads to choosing a new password.
window.KC = (() => {
  const $ = s => document.querySelector(s);
  const q = new URLSearchParams(location.search);
  const PLAN_NAMES = { single: "Single page, £20 a month", five: "Up to 5 pages, £25 a month", more: "More than 5 pages, £30 a month" };
  const BS = String.fromCharCode(92);
  const safeNext = n => (n && n.startsWith("/") && !n.startsWith("//") && !n.startsWith("/" + BS)) ? n : "/account/";
  const me = () => fetch("/api/client/me", { credentials: "same-origin" }).then(r => r.json()).catch(() => ({ signedIn: false }));
  const show = (el, on) => { el.hidden = !on; };
  const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
    .then(async r => ({ ok: r.ok, status: r.status, d: await r.json().catch(() => ({})) }))
    .catch(() => ({ ok: false, d: { error: "We couldn't reach the server. Check your connection and try again." } }));
  const EMAIL_OK = e => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);
  function showErr(msg) { const e = $("#err"); if (!e) return; e.textContent = msg || ""; show(e, !!msg); }
  function busy(btn, on, text) { btn.disabled = on; if (text) btn.textContent = text; }

  function loadGoogle(clientId, next) {
    if (!clientId) return;
    const s = document.createElement("script");
    s.src = "https://accounts.google.com/gsi/client"; s.async = true;
    s.onload = () => {
      google.accounts.id.initialize({
        client_id: clientId,
        callback: async ({ credential }) => {
          const r = await post("/api/client/google", { credential, next });
          if (r.ok) location.href = r.d.next || next; else showErr(r.d.error || "Google sign-in didn't work. Use your email instead.");
        }
      });
      google.accounts.id.renderButton($("#google-btn"), { theme: "outline", size: "large", text: "continue_with", shape: "pill", width: 300 });
      show($("#google-wrap"), true);
    };
    document.head.appendChild(s);
  }

  async function signinPage() {
    const next = safeNext(q.get("next"));
    const plan = q.get("plan");
    if (PLAN_NAMES[plan]) {
      const p = $("#plan"); p.textContent = "You're choosing: " + PLAN_NAMES[plan]; show(p, true);
      $("#why").textContent = "Sign in, or create your account, then you'll go straight to the secure payment page.";
    }
    if (q.get("e")) showErr(q.get("e"));
    const who = await me();
    if (who.signedIn) { location.replace(next); return; }
    loadGoogle(who.googleClientId, next);

    let mode = q.get("new") === "1" ? "new" : "in";
    const setMode = m => {
      mode = m; showErr("");
      $("#tab-in").setAttribute("aria-selected", String(m === "in"));
      $("#tab-new").setAttribute("aria-selected", String(m === "new"));
      show($("#name-field"), m === "new"); show($("#site-field"), m === "new"); show($("#pw-hint"), m === "new");
      $("#password").autocomplete = m === "new" ? "new-password" : "current-password";
      $("#go").textContent = m === "new" ? "Create account" : "Sign in";
      $("#t").textContent = m === "new" ? "Create your account" : "Sign in to continue";
      show($("#forgot").parentElement, m === "in");
    };
    $("#tab-in").addEventListener("click", () => setMode("in"));
    $("#tab-new").addEventListener("click", () => setMode("new"));
    setMode(mode);

    $("#show").addEventListener("click", () => {
      const pw = $("#password"), on = pw.type === "password";
      pw.type = on ? "text" : "password"; $("#show").textContent = on ? "Hide" : "Show"; $("#show").setAttribute("aria-pressed", String(on));
    });

    $("#form").addEventListener("submit", async ev => {
      ev.preventDefault();
      const email = $("#email").value.trim(), password = $("#password").value;
      if (!EMAIL_OK(email)) { showErr("Enter your email address, for example you@yourbusiness.co.uk."); $("#email").focus(); return; }
      if (mode === "new" && password.length < 10) { showErr("Choose a password of at least 10 characters."); $("#password").focus(); return; }
      if (!password) { showErr("Enter your password."); $("#password").focus(); return; }
      showErr(""); const b = $("#go"); const label = b.textContent; busy(b, true, mode === "new" ? "Creating your account…" : "Signing in…");
      const r = await post(mode === "new" ? "/api/client/register" : "/api/client/login", { email, password, name: $("#name").value.trim(), website: $("#website").value.trim(), next });
      busy(b, false, label);
      if (r.ok) { location.href = r.d.next || next; return; }
      if (r.d.exists) setMode("in");
      showErr(r.d.error || "Something went wrong. Please try again.");
    });

    $("#forgot").addEventListener("click", () => {
      showErr(""); $("#reset-email").value = $("#email").value.trim();
      show($("#form"), false); show($("#google-wrap"), false); show($("#reset"), true); $("#reset-email").focus();
    });
    $("#back").addEventListener("click", () => {
      show($("#reset"), false); show($("#sent"), false); show($("#form"), true); if (who.googleClientId) show($("#google-wrap"), true);
    });
    $("#reset").addEventListener("submit", async ev => {
      ev.preventDefault();
      const email = $("#reset-email").value.trim();
      if (!EMAIL_OK(email)) { showErr("Enter your email address."); return; }
      const b = $("#reset-go"); busy(b, true, "Sending…");
      const r = await post("/api/client/link", { email, next });
      busy(b, false, "Email me a reset link");
      if (!r.ok) { showErr(r.d.error || "We couldn't send the email. Please try again."); return; }
      showErr(""); show($("#reset"), false);
      const s = $("#sent"); s.textContent = "If there's an account for " + email + ", we've sent it a link to choose a new password. It runs out in 20 minutes. Check your spam folder if it isn't there.";
      show(s, true);
    });
  }

  async function accountPage() {
    const who = await me();
    if (!who.signedIn) { location.replace("/signin/?next=/account/"); return; }
    $("#who").textContent = who.email;

    // their own website (owner, 16 Nov 2026)
    let mySite = who.website || ((who.plans || []).find(p => p.website) || {}).website || "";
    const pretty = u => u.replace(/^https?:\/\//, "").replace(/\/$/, "");
    const drawSite = () => {
      show($("#site-show"), !!mySite); show($("#site-form"), !mySite);
      if (mySite) { $("#site-link").href = mySite; $("#site-link").textContent = pretty(mySite); }
      if (mySite && !$("#ch-site").value) $("#ch-site").value = mySite;
    };
    drawSite();
    $("#site-edit").addEventListener("click", () => { $("#site-input").value = mySite; show($("#site-show"), false); show($("#site-form"), true); $("#site-input").focus(); });
    $("#site-form").addEventListener("submit", async ev => {
      ev.preventDefault();
      const r = await post("/api/client/website", { website: $("#site-input").value.trim() });
      if (!r.ok) { $("#site-err").textContent = r.d.error || "That didn't save."; show($("#site-err"), true); return; }
      show($("#site-err"), false); mySite = r.d.website; $("#ch-site").value = mySite; drawSite();
    });

    // after "Forgot your password?" (or a Google account with no password yet): choose a password
    const reset = q.get("reset") === "1";
    if (reset || !who.hasPassword) {
      const box = $("#setpw"); show(box, true);
      if (!reset) { $("#setpw-t").textContent = "Add a password"; $("#setpw-p").textContent = "So you can also sign in with your email and password."; }
      $("#setpw-form").addEventListener("submit", async ev => {
        ev.preventDefault();
        const pw = $("#newpw").value;
        if (pw.length < 10) { $("#setpw-msg").textContent = "Choose a password of at least 10 characters."; show($("#setpw-msg"), true); return; }
        const r = await post("/api/client/password", { password: pw });
        if (!r.ok) { $("#setpw-msg").textContent = r.d.error || "That didn't work. Please try again."; show($("#setpw-msg"), true); return; }
        const next = safeNext(q.get("next"));
        if (reset && next !== "/account/") { location.href = next; return; }
        show(box, false); history.replaceState(null, "", "/account/");
      });
    }

    const money = (p, c) => (c || "gbp").toLowerCase() === "gbp" ? "£" + (p / 100).toFixed(p % 100 ? 2 : 0) : (p / 100).toFixed(2) + " " + c.toUpperCase();
    const live = (who.plans || []).filter(p => ["active", "trialing", "past_due"].includes(p.status));
    $("#plans").innerHTML = "";
    if (!who.plans || !who.plans.length) {
      $("#plans").innerHTML = '<p class="muted">You don\'t have a plan yet. Choose one below.</p>';
    } else {
      for (const p of who.plans) {
        const row = document.createElement("div"); row.className = "plan-row";
        const on = ["active", "trialing", "past_due"].includes(p.status);
        const left = document.createElement("div");
        left.innerHTML = "<b></b><br><span class='muted'></span>";
        left.querySelector("b").textContent = (p.amount ? money(p.amount, p.currency) + " a month" : "Hosting and care plan");
        left.querySelector("span").textContent = p.website || "";
        const tag = document.createElement("span"); tag.className = "tag" + (on ? "" : " off");
        tag.textContent = p.cancel_at ? "Ends " + new Date(p.cancel_at).toLocaleDateString("en-GB") : on ? "Active" : "Cancelled";
        row.append(left, tag); $("#plans").append(row);
      }
    }
    if (live.length) show($("#buy"), false);
    const portal = $("#portal");
    if (who.portal) { portal.href = who.portal; portal.target = "_blank"; portal.rel = "noopener"; }
    else { portal.href = "mailto:alfredw.lsx@gmail.com?subject=" + encodeURIComponent("My hosting and care plan (" + who.email + ")"); portal.textContent = "Email us about payments or cancelling"; }
    $("#out").addEventListener("click", async () => { await fetch("/api/client/logout", { method: "POST" }); location.href = "/"; });

    // change requests (owner, 16 Nov 2026)
    const site = (who.plans || []).find(p => p.website);
    if (site && !$("#ch-site").value) $("#ch-site").value = site.website;
    const STATUS = { received: ["Received", "wait"], "in progress": ["In progress", "wait"], done: ["Done", ""] };
    async function listChanges() {
      const r = await fetch("/api/client/changes", { credentials: "same-origin" }).then(x => x.json()).catch(() => ({}));
      const list = $("#ch-list"); const reqs = r.requests || [];
      if (!reqs.length) { list.innerHTML = '<p class="muted">No requests yet.</p>'; return; }
      list.innerHTML = "";
      for (const q of reqs) {
        const d = document.createElement("div"); d.className = "req";
        const [label, cls] = STATUS[q.status] || [q.status, "wait"];
        d.innerHTML = '<div class="top"><span></span><span class="tag"></span></div><p></p>';
        d.querySelector(".top span").textContent = q.kind + " · " + new Date(q.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
        const t = d.querySelector(".tag"); t.textContent = label; if (cls) t.classList.add(cls);
        d.querySelector("p").textContent = q.details + (q.files ? "\n\nAttached: " + q.files : "");
        list.append(d);
      }
    }
    listChanges();
    // screenshots, photos and PDFs (owner, 16 Nov 2026)
    const OK_TYPES = /^(image\/(jpeg|png|webp|gif|heic|heif)|application\/pdf)$/;
    const MAX_FILES = 6, MAX_FILE = 8 * 1024 * 1024, MAX_TOTAL = 20 * 1024 * 1024;
    let files = [];
    const mb = n => (n / 1048576).toFixed(n < 1048576 ? 2 : 1) + " MB";
    const fileErr = msg => { const e = $("#ch-err"); e.textContent = msg; show(e, true); };
    function drawFiles() {
      const ul = $("#ch-file-list"); ul.innerHTML = "";
      files.forEach((f, i) => {
        const li = document.createElement("li");
        if (f.type === "application/pdf") { const t = document.createElement("span"); t.className = "pdf"; t.textContent = "PDF"; li.append(t); }
        else { const img = document.createElement("img"); img.alt = ""; img.src = URL.createObjectURL(f); img.onload = () => URL.revokeObjectURL(img.src); li.append(img); }
        const nm = document.createElement("span"); nm.className = "nm"; nm.textContent = f.name + " · " + mb(f.size); li.append(nm);
        const x = document.createElement("button"); x.type = "button"; x.className = "link"; x.textContent = "Remove";
        x.setAttribute("aria-label", "Remove " + f.name); x.onclick = () => { files.splice(i, 1); drawFiles(); }; li.append(x);
        ul.append(li);
      });
    }
    function addFiles(list) {
      show($("#ch-err"), false);
      for (const f of list) {
        const type = f.type || (/\.hei[cf]$/i.test(f.name) ? "image/heic" : /\.pdf$/i.test(f.name) ? "application/pdf" : "");
        if (!OK_TYPES.test(type)) { fileErr("“" + f.name + "” isn't a picture or PDF."); continue; }
        if (f.size > MAX_FILE) { fileErr('"' + f.name + '" is over 8 MB. Make it smaller, or email it to us.'); continue; }
        if (files.length >= MAX_FILES) { fileErr("You can attach up to 6 files at once."); break; }
        if (files.reduce((a, x) => a + x.size, 0) + f.size > MAX_TOTAL) { fileErr("That's over 20 MB in total. Send the rest in another request."); break; }
        files.push(f);
      }
      drawFiles(); $("#ch-files").value = "";
    }
    $("#ch-files").addEventListener("change", e => addFiles(e.target.files));
    const drop = $(".drop");
    ["dragenter", "dragover"].forEach(t => drop.addEventListener(t, e => { e.preventDefault(); drop.classList.add("over"); }));
    ["dragleave", "drop"].forEach(t => drop.addEventListener(t, e => { e.preventDefault(); drop.classList.remove("over"); }));
    drop.addEventListener("drop", e => addFiles(e.dataTransfer.files));

    $("#change-form").addEventListener("submit", async ev => {
      ev.preventDefault();
      const e = $("#ch-err"), ok = $("#ch-ok"); show(e, false); show(ok, false);
      const details = $("#ch-details").value.trim();
      if (details.length < 5) { e.textContent = "Tell us what you'd like changed, and where on your website."; show(e, true); $("#ch-details").focus(); return; }
      const fd = new FormData();
      fd.append("website", $("#ch-site").value.trim()); fd.append("kind", $("#ch-kind").value);
      fd.append("details", details); fd.append("links", $("#ch-links").value.trim());
      files.forEach(f => fd.append("files", f, f.name));
      const b = $("#ch-go"); busy(b, true, files.length ? "Uploading…" : "Sending…");
      let r;
      try {
        const res = await fetch("/api/client/changes", { method: "POST", body: fd, credentials: "same-origin" });
        r = { ok: res.ok, d: await res.json().catch(() => ({})) };
      } catch { r = { ok: false, d: { error: "We couldn't reach the server. Check your connection and try again." } }; }
      busy(b, false, "Send request");
      if (!r.ok) { e.textContent = r.d.error || "That didn't send. Please try again."; show(e, true); return; }
      $("#ch-details").value = ""; $("#ch-links").value = ""; files = []; drawFiles();
      ok.textContent = r.d.filesNotSent
        ? "We've got your request (#" + r.d.id + "), but your files didn't come through. Please email them to alfredw.lsx@gmail.com."
        : "Thanks, we've got it (request #" + r.d.id + "). We'll email you when it's done.";
      show(ok, true);
      listChanges();
    });

    // cancel subscription (owner, 16 Nov 2026: at the bottom, a red block in white writing)
    const open = $("#cancel-open"), box = $("#cancel-box");
    open.addEventListener("click", () => {
      if (who.portal) { window.open(who.portal, "_blank", "noopener"); return; }
      const on = box.hidden; show(box, on); open.setAttribute("aria-expanded", String(on)); show(open, !on);
      if (on) $("#cancel-why").focus();
    });
    $("#cancel-keep").addEventListener("click", () => { show(box, false); show(open, true); open.setAttribute("aria-expanded", "false"); });
    $("#cancel-go").addEventListener("click", async () => {
      const b = $("#cancel-go"); busy(b, true, "Sending…");
      const why = $("#cancel-why").value.trim();
      const r = await post("/api/client/changes", { website: mySite, kind: "Cancel subscription",
        details: "Please cancel my subscription." + (why ? "\n\nWhy: " + why : "") });
      busy(b, false, "Yes, cancel my subscription");
      if (!r.ok) { $("#cancel-err").textContent = r.d.error || "That didn't send. Please try again, or email us."; show($("#cancel-err"), true); return; }
      show(box, false); const ok = $("#cancel-ok");
      ok.textContent = "We've got your cancellation (request #" + r.d.id + "). We'll stop your subscription and email you to confirm, usually within one working day.";
      show(ok, true); listChanges();
    });
  }
  return { signinPage, accountPage };
})();
