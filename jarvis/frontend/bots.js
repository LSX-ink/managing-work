// Alfred's bots on the HUD (owner, 31 Oct 2026: "all bots made also be put into Alfred ... and the HUD"). The BOTS
// chip, the BOTS button (always on screen, even with the HUD hidden) and Alt+B ask Alfred for the bots window
// (bots.py); HIGGSFIELD asks for the Higgsfield guide (higgsfield_guide.py). Both windows are "showme" pop-ups.
(() => {
    const ask = (text) => { if (window.jarvisAsk) window.jarvisAsk(text); };
    const BOTS = 'Show my bots';
    const HIGGSFIELD = 'Show the Higgsfield features';
    for (const id of ['hud-bots', 'bots-fab']) {
        const b = document.getElementById(id);
        if (b) b.addEventListener('click', () => ask(BOTS));
    }
    const h = document.getElementById('higgsfield-fab');
    if (h) h.addEventListener('click', () => ask(HIGGSFIELD));
    document.addEventListener('keydown', (e) => {
        if (e.altKey && !e.ctrlKey && !e.metaKey && (e.key === 'b' || e.key === 'B')) {
            e.preventDefault();
            ask(BOTS);
        }
    });
})();
