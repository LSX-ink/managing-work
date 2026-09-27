// Folder stars: every folder made inside a memory folder ("Work/Invoices") is a bright star on the HUD.
// Hover a star to see its name, click it to open that folder on the PC. When Alfred opens one, its star flares.
window.HudStars = (() => {
    const layer = document.createElement('div');
    layer.id = 'folder-stars';
    const stars = new Map();   // "Work/Invoices" -> button

    // A stable spot for each folder, in open sky: clear of the wolf, the panels and the text.
    const BLOCKERS = '.hud-panel:not([hidden]), .hud-bar, #orb-wrap, #status, #transcript, #type-form, .folder-star';
    function place(path, star) {
        let h = 2166136261;
        for (const c of path.toLowerCase()) h = Math.imul(h ^ c.charCodeAt(0), 16777619) >>> 0;
        const next = () => ((h = Math.imul(h ^ (h >>> 15), 2246822507) >>> 0) / 4294967296);
        const W = innerWidth, H = innerHeight, pad = 18;
        const rects = [...document.querySelectorAll(BLOCKERS)].filter((el) => el !== star && el.offsetParent !== null)
            .map((el) => el.getBoundingClientRect()).filter((r) => r.width && r.height);
        let x = 0, y = 0;
        for (let tries = 0; tries < 400; tries++) {
            x = 2 + next() * 96; y = 4 + next() * 93;
            const px = (x / 100) * W, py = (y / 100) * H;
            if (!rects.some((r) => px > r.left - pad && px < r.right + pad && py > r.top - pad && py < r.bottom + pad)) break;
        }
        star.style.left = `${x}%`;
        star.style.top = `${y}%`;
    }

    function placeAll() { for (const [key, star] of stars) place(key, star); }

    function flare(path) {
        const star = stars.get(path.toLowerCase());
        if (!star) return;
        star.classList.remove('flare');
        void star.offsetWidth;   // restart the animation
        star.classList.add('flare');
    }

    async function load() {
        let folders = [];
        try { folders = (await (await fetch('/memory')).json()).folders || []; } catch (e) { return; }
        const seen = new Set();
        folders.forEach((top, index) => (top.folders || []).forEach((sub) => {
            const path = `${top.name}/${sub.name}`, key = path.toLowerCase();
            seen.add(key);
            let star = stars.get(key);
            if (!star) {
                star = document.createElement('button');
                star.type = 'button';
                star.className = 'folder-star new';
                star.innerHTML = '<span class="dot"></span><span class="name"></span>';
                star.addEventListener('click', async () => {
                    flare(path);
                    await fetch(`/memory/${star.dataset.index}/open`, {
                        method: 'POST', headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ folder: star.dataset.sub }),
                    });
                });
                layer.append(star);
                stars.set(key, star);
                place(key, star);
                setTimeout(() => star.classList.remove('new'), 2500);
            }
            star.dataset.index = index;
            star.dataset.sub = sub.name;
            star.querySelector('.name').textContent = `${path} · ${sub.count}`;
            star.setAttribute('aria-label', `Open the ${path} folder`);
        }));
        for (const [key, star] of stars) if (!seen.has(key)) { star.remove(); stars.delete(key); }
    }

    function start() {
        if (!document.body.classList.contains('hud')) return;
        document.body.append(layer);
        load();
        let resizing;
        addEventListener('resize', () => { clearTimeout(resizing); resizing = setTimeout(placeAll, 200); });
        // Alfred may have made or opened a folder while thinking: refresh when a reply finishes.
        const orb = document.getElementById('orb');
        let wasThinking = false;
        new MutationObserver(() => {
            const thinking = orb.classList.contains('thinking');
            if (wasThinking && !thinking) load();
            wasThinking = thinking;
        }).observe(orb, { attributes: true, attributeFilter: ['class'] });
        document.addEventListener('jarvis:memory', async (e) => {
            if (!e.detail.star) return;
            await load();
            flare(e.detail.star);
        });
    }

    document.addEventListener('jarvis:config', start);
    return { load, flare };
})();
