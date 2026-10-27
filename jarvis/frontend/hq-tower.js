// LSX HQ inside Alfred (owner, 24 Oct 2026: "it needs to be in Alfred"): the HQ chip (or Alt+H) opens the live
// office screen from http://127.0.0.1:8341, the glass tower with every agent, over Alfred's HUD. Esc or × closes it.
function setupHQ() {
    const HQ = 'http://127.0.0.1:8341/';
    const chip = document.getElementById('hud-hq');
    const fab = document.getElementById('hq-fab');   // always on screen, even with the HUD hidden
    const box = document.getElementById('hq-overlay');
    const frame = document.getElementById('hq-frame');
    if (!chip || !box || !frame) return;
    let open = false;
    function setOpen(on) {
        open = on;
        if (on && !frame.src) frame.src = HQ;   // load the tower the first time it's opened
        box.hidden = !on;
        chip.setAttribute('aria-pressed', String(on));
        if (fab) fab.setAttribute('aria-pressed', String(on));
    }
    chip.addEventListener('click', () => setOpen(!open));
    if (fab) fab.addEventListener('click', () => setOpen(!open));
    // say or type "show HQ", "open the tower"... and Alfred opens it; "close HQ" closes it
    document.addEventListener('jarvis:line', (e) => {
        const d = e.detail || {}, text = (d.text || '').toLowerCase();
        if (d.who !== 'user') return;
        if (!/(hq|headquarters|tower)/.test(text)) { if (open) setOpen(false); return; }
        setOpen(!/(close|hide|shut)/.test(text));
    });
    document.getElementById('hq-close').addEventListener('click', () => setOpen(false));
    document.getElementById('hq-reload').addEventListener('click', () => { frame.src = HQ; });
    window.addEventListener('keydown', (e) => {
        if (e.altKey && (e.code === 'KeyH' || e.key === 'h' || e.key === 'H')) { e.preventDefault(); e.stopPropagation(); setOpen(!open); }
        else if (e.key === 'Escape' && open) setOpen(false);
    }, true);
    frame.addEventListener('error', () => { box.querySelector('.hq-msg').hidden = false; });
    try { localStorage.removeItem('alfred.hq.open'); } catch (e) { /* ignore */ }   // never reopens by itself: Alfred comes first
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setupHQ); else setupHQ();
