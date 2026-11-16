// Client sign-in and account pages (owner, 16 Nov 2026). Email link or Google; no passwords.
window.KC = (() => {
  const $ = s => document.querySelector(s);
  const q = new URLSearchParams(location.search);
  const PLAN_NAMES = { single: "Single page, £20 a month", five: "Up to 5 pages, £25 a month", more: "More than 5 pages, £30 a month" };
  const safeNext = n => (n && n.startsWith("/") && !n.startsWith("//") && !n.startsWith("/\\")) ? n : "/account/";
  const me = () => fetch("/api/client/me", { credentials: "same-origin" }).then(r => r.json()).catch(() => ({ signedIn: false }));
  const show = (el, on) => { el.hidden = !on; };

  function loadGoogle(clientId, next) {
    if (!clientId) return;
    const s = document.createElement("script");
    s.src = "https://accounts.google.com/gsi/client"; s.async = true;
    s.onload = () => {
      google.accounts.id.initialize({
        client_id: clientId,
        callback: async ({ credential }) => {
          const r = await fetch("/api/client/google", { method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ credential, next }) });
          const d = await r.json().catch(() => ({}));
          if (r.ok) location.href = d.next || next; else showErr(d.error || "Google sign-in didn't work. Use your email instead.");
        }
      });
      google.accounts.id.renderButton($("#google-btn"), { theme: "outline", size: "large", text: "continue_with", shape: "pill", width: 300 });
      show($("#google-wrap"), true);
    };
    document.head.appendChild(s);
  }
  function showErr(msg) { const e = $("#err"); e.textContent = msg; show(e, !!msg); }

  async function signinPage() {
    const next = safeNext(q.get("next"));
    const plan = q.get("plan");
    if (PLAN_NAMES[plan]) { const p = $("#plan"); p.textContent = "You're choosing: " + PLAN_NAMES[plan]; show(p, true);
      $("#why").textContent = "Sign in or create your account first, then you'll go straight to the secure payment page."; }
    if (q.get("e")) showErr(q.get("e"));
    const who = await me();
    if (who.signedIn) { location.replace(next); return; }
    loadGoogle(who.googleClientId, next);
    $("#form").addEventListener("submit", async ev => {
      ev.preventDefault();
      const email = $("#email").value.trim();
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { showErr("Enter your email address, for example you@yourbusiness.co.uk."); $("#email").focus(); return; }
      showErr(""); const b = $("#send"); b.disabled = true; b.textContent = "Sending…";
      const r = await fetch("/api/client/link", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, next }) })
        .catch(() => null);
      const d = r ? await r.json().catch(() => ({})) : {};
      b.disabled = false; b.textContent = "Email me a sign-in link";
      if (!r || !r.ok) { showErr(d.error || "We couldn't send the email. Check your connection and try again."); return; }
      $("#sent-to").textContent = email; show($("#form"), false); show($("#google-wrap"), false); show($("#sent"), true);
    });
    $("#again").addEventListener("click", () => { show($("#sent"), false); show($("#form"), true); if (who.googleClientId) show($("#google-wrap"), true); $("#email").focus(); });
  }

  async function accountPage() {
    const who = await me();
    if (!who.signedIn) { location.replace("/signin/?next=/account/"); return; }
    $("#who").textContent = who.email;
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
  }
  return { signinPage, accountPage };
})();
