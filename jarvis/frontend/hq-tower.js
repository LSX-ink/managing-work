// LSX HQ inside Alfred (owner, 24 Oct 2026: "it needs to be in Alfred"): the HQ chip (or Alt+H) opens the dashboard
// (owner, 27 Oct 2026: today's DMs, replies, follow-ups, the week's numbers and what Claude is doing), served through
// Alfred at /hq/dashboard so it works on the phone too. On the PC, TOWER switches to the glass tower with every agent
// from http://127.0.0.1:8341. Esc or × closes it.
function setupHQ() {
    const DASH = '/hq/dashboard';
    const TOWER = 'http://127.0.0.1:8341/';
    const onPC = ['127.0.0.1', 'localhost', '[::1]'].includes(location.hostname);
    const chip = document.getElementById('hud-hq');
    const fab = document.getElementById('hq-fab');   // always on screen, even with the HUD hidden
    const box = document.getElementById('hq-overlay');
    const frame = document.getElementById('hq-frame');
    const towerBtn = document.getElementById('hq-tower');
    if (!chip || !box || !frame) return;
    let open = false, view = DASH;
    function show(url) {
        view = url;
        frame.src = url;
        if (towerBtn) towerBtn.textContent = url === DASH ? 'TOWER' : 'DASHBOARD';
    }
    function setOpen(on) {
        open = on;
        if (on && !frame.src) show(DASH);   // load the dashboard the first time it's opened
        box.hidden = !on;
        chip.setAttribute('aria-pressed', String(on));
        if (fab) fab.setAttribute('aria-pressed', String(on));
    }
    chip.addEventListener('click', () => setOpen(!open));
    if (fab) fab.addEventListener('click', () => setOpen(!open));
    if (towerBtn) {
        towerBtn.hidden = !onPC;   // the tower only runs on the PC itself
        towerBtn.addEventListener('click', () => show(view === DASH ? TOWER : DASH));
    }
    // say or type "show HQ", "open the dashboard", "show the tower"... and Alfred opens it; "close HQ" closes it
    document.addEventListener('jarvis:line', (e) => {
        const d = e.detail || {}, text = (d.text || '').toLowerCase();
        if (d.who !== 'user') return;
        if (!/(hq|headquarters|tower|dashboard)/.test(text)) { if (open) setOpen(false); return; }
        if (/(close|hide|shut)/.test(text)) { setOpen(false); return; }
        setOpen(true);
        if (/tower/.test(text) && onPC) show(TOWER);
        else if (/dashboard/.test(text)) show(DASH);
    });
    document.getElementById('hq-close').addEventListener('click', () => setOpen(false));
    document.getElementById('hq-reload').addEventListener('click', () => show(view));
    window.addEventListener('keydown', (e) => {
        if (e.altKey && (e.code === 'KeyH' || e.key === 'h' || e.key === 'H')) { e.preventDefault(); e.stopPropagation(); setOpen(!open); }
        else if (e.key === 'Escape' && open) setOpen(false);
    }, true);
    frame.addEventListener('error', () => { box.querySelector('.hq-msg').hidden = false; });
    try { localStorage.removeItem('alfred.hq.open'); } catch (e) { /* ignore */ }   // never reopens by itself: Alfred comes first
    if (location.hash === '#dashboard' || /(?:^|[?&])dash(?:=|&|$)/.test(location.search)) setOpen(true);   // a phone notification opens straight onto it
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setupHQ); else setupHQ();
