// LSX HQ shared data layer for every design: polls the brain, feeds events, and opens an agent's sheet.
export const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
export const state = { agents: [], brain: {}, pipeline: {}, outbox: { sent_today: 0, cap: 15 }, divisions: [], time: "--:--", colours: { hq: "#f6b44b" }, names: { hq: "HQ" }, said: {}, ready: false };
let lastId = 0;
const listeners = { state: [], events: [] };
export const on = (kind, fn) => listeners[kind].push(fn);

async function pullState() {
  try {
    const s = await (await fetch("/api/state")).json();
    Object.assign(state, { agents: s.agents, brain: s.brain, pipeline: s.pipeline || {}, cities: s.cities || {}, outbox: s.outbox || state.outbox, divisions: s.divisions || [], time: s.time, hour: s.hour });
    s.agents.forEach(a => { state.colours[a.key] = a.colour; state.names[a.key] = a.name; });
    listeners.state.forEach(fn => fn(state));
  } catch (e) { console.warn(e); }
}
async function pullEvents() {
  try {
    const list = (await (await fetch(`/api/events?after=${lastId}`)).json()).filter(e => e.kind !== "start");
    if (list.length) lastId = list[list.length - 1].id;
    if (state.ready) list.forEach(e => { if (e.kind !== "done") state.said[e.agent] = { text: e.text.length > 120 ? e.text.slice(0, 118) + "…" : e.text, until: Date.now() + 9000 }; });
    listeners.events.forEach(fn => fn(list, state.ready));
    state.ready = true;
  } catch (e) { console.warn(e); }
}
export async function start() { await pullState(); await pullEvents(); setInterval(pullState, 3000); setInterval(pullEvents, 2000); }
export const saying = a => a.status === "working" ? `Working: ${a.job.split(".")[0].toLowerCase()}…` : (state.said[a.key] && state.said[a.key].until > Date.now() ? state.said[a.key].text : "");
export const working = () => state.agents.filter(a => a.status === "working").length;
export function numbers() {
  const pl = state.pipeline, ig = state.brain.instagram || {}, ob = state.outbox;
  return { leads: pl.leads || 0, drafted: pl.drafted || 0, contacted: pl.contacted || 0, replies: (pl.replied || 0) + (pl.interested || 0),
           won: (pl.won || 0) + (pl.live || 0), optedOut: pl["opted out"] || 0, sent: ob.sent_today, cap: ob.cap, ig: ig.replied || 0, handed: ig.handed_off || 0 };
}
export const fmtTime = ts => new Date(ts * 1000).toTimeString().slice(0, 8);

// the agent sheet (same on every design)
const css = `.lsx-sheet{position:fixed;inset:0;background:rgba(0,0,0,.62);display:none;place-items:center;z-index:99;font-family:inherit}.lsx-sheet.open{display:grid}
.lsx-card{width:min(560px,92vw);max-height:84vh;overflow:auto;background:#121118;color:#eee;border:1px solid var(--c);border-radius:14px;padding:20px;box-shadow:0 0 50px -10px var(--c)}
.lsx-card h2{margin:0;color:var(--c);font-size:18px}.lsx-card p{color:#9a96a8}.lsx-row{display:flex;gap:8px;margin:12px 0}
.lsx-card button{font:700 12px system-ui;border-radius:8px;padding:8px 14px;border:1px solid #333;background:#22202a;color:#eee;cursor:pointer}.lsx-card button.go{background:var(--c);color:#111;border-color:var(--c)}
.lsx-ev{font:11.5px/1.45 ui-monospace,Consolas,monospace;padding:3px 0;white-space:pre-wrap;color:#cfc8ba}.lsx-ev time{color:#888}`;
document.head.insertAdjacentHTML("beforeend", `<style>${css}</style>`);
document.body.insertAdjacentHTML("beforeend", `<div class="lsx-sheet" id="lsx-sheet"><div class="lsx-card" id="lsx-card"></div></div>`);
document.getElementById("lsx-sheet").onclick = e => { if (e.target.id === "lsx-sheet") e.target.classList.remove("open"); };
export async function openAgent(key) {
  const a = state.agents.find(x => x.key === key); if (!a) return;
  const evs = await (await fetch(`/api/events?agent=${key}&limit=25`)).json(), c = document.getElementById("lsx-card");
  c.style.setProperty("--c", a.colour);
  c.innerHTML = `<h2>${a.emoji} ${esc(a.name)} · ${esc(a.title)}</h2><p>${esc(a.division)} · ${esc(a.job)}</p>
    <div class="lsx-row"><button class="go" data-a="run">Run now</button><button data-a="pause">${a.status === "paused" ? "Resume" : "Pause"}</button><button data-a="close">Close</button></div>
    <p>Last: ${a.last ? esc(a.last.when + " · " + a.last.result) : "not yet"} · Next: ${esc(a.next)}</p>
    ${evs.reverse().filter(e => e.kind !== "start").map(e => `<div class="lsx-ev"><time>${new Date(e.ts * 1000).toLocaleString("en-GB").slice(0, 17)}</time> ${esc(e.text)}</div>`).join("") || "<p>No work logged yet.</p>"}`;
  document.getElementById("lsx-sheet").classList.add("open");
  c.querySelectorAll("button").forEach(b => b.onclick = async () => {
    if (b.dataset.a === "run") await fetch(`/api/run/${key}`, { method: "POST" });
    if (b.dataset.a === "pause") await fetch(`/api/pause/${key}`, { method: "POST" });
    document.getElementById("lsx-sheet").classList.remove("open"); pullState();
  });
}
// city positions for the world views (lat, lon)
export const CITIES = { birmingham: [52.48, -1.9], manchester: [53.48, -2.24], leeds: [53.8, -1.55], london: [51.51, -0.13], liverpool: [53.41, -2.98],
  bristol: [51.45, -2.59], sheffield: [53.38, -1.47], nottingham: [52.95, -1.15], leicester: [52.64, -1.13], croydon: [51.37, -0.1], glasgow: [55.86, -4.25],
  cardiff: [51.48, -3.18], newcastle: [54.98, -1.61], coventry: [52.41, -1.51], bradford: [53.8, -1.75], brighton: [50.82, -0.14], dublin: [53.35, -6.26],
  houston: [29.76, -95.37], atlanta: [33.75, -84.39], chicago: [41.88, -87.63], miami: [25.76, -80.19], dallas: [32.78, -96.8], "los angeles": [34.05, -118.24],
  "new york": [40.71, -74.0], toronto: [43.65, -79.38], lagos: [6.52, 3.38], johannesburg: [-26.2, 28.05], nairobi: [-1.29, 36.82], sydney: [-33.87, 151.21],
  dubai: [25.2, 55.27], accra: [5.6, -0.19], "cape town": [-33.92, 18.42], paris: [48.86, 2.35], berlin: [52.52, 13.4], madrid: [40.42, -3.7], amsterdam: [52.37, 4.9] };
