// Station LSX: the 3D world behind the HUD. Planet HOME with the desert base (and the LSX factory) on the left, planet
// LSX with the forest port on the right, the wolf free in the middle, and the rest of the solar system further out.
// The scene follows the TikTok studio (GET /station/state, every 10 s while the tab is visible): the crew load the
// ship while videos are made, she flies to LSX when they are ready and waits at the port for your tick or cross, and
// each approved video's crate is carried to its page's office before the ship flies home.
// Layering: one fixed canvas at z-index -1, above the page background and below every panel and the wolf. Pointer,
// wheel and drag reach the scene only when they land on empty background. Alfred drives it with station_view cards
// (kind "station"), and when he listens or speaks the scene eases in and dims behind the wolf.
// Off switch: JARVIS_STATION=false, or "station off" (kept in this browser), falls back to the old background.
(() => {
    'use strict';
    const $ = (id) => document.getElementById(id);
    const KEY = 'jarvis-station';
    const POLL_MS = 10000;
    const load = (k, d) => { try { const v = JSON.parse(localStorage.getItem(`${KEY}-${k}`)); return v === null ? d : v; } catch (e) { return d; } };
    const save = (k, v) => { try { localStorage.setItem(`${KEY}-${k}`, JSON.stringify(v)); } catch (e) { /* private window */ } };
    const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
    const lerp = (a, b, t) => a + (b - a) * t;
    const sm = (t) => t * t * (3 - 2 * t);
    const reduced = () => document.documentElement.classList.contains('a11y-motion') || matchMedia('(prefers-reduced-motion: reduce)').matches;
    const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; };

    let config = {}, allowed = false, running = false, booting = false;
    let THREE = null, renderer = null, camera = null, k = null, space = null, desert = null, forest = null;
    let canvas = null, veil = null, ui = null, controls = null, panel = null, raf = 0, pollTimer = 0;

    // ---- loading --------------------------------------------------------------------------------------------------
    const script = (src) => new Promise((ok, fail) => {
        const s = document.createElement('script'); s.src = src; s.onload = ok; s.onerror = () => fail(new Error(src)); document.head.append(s);
    });
    async function loadScripts() {
        if (!window.THREE) await script('/static/vendor/three.min.js');
        for (const part of ['kit', 'desert', 'forest', 'space']) if (!(window.LSX && window.LSX[part])) await script(`/static/station-${part}.js`);
    }
    const webgl = () => { try { const c = document.createElement('canvas'); return !!(window.WebGLRenderingContext && (c.getContext('webgl2') || c.getContext('webgl'))); } catch (e) { return false; } };
    const pause = () => new Promise((ok) => setTimeout(ok, 0));

    async function start() {
        if (running || booting || !allowed || !load('on', true) || !webgl()) return;
        booting = true;
        try {
            await loadScripts();
            THREE = window.THREE;
            if (!canvas) buildDom();
            renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
            renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
            renderer.outputEncoding = THREE.sRGBEncoding;
            renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
            renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
            camera = new THREE.PerspectiveCamera(38, 1, 0.1, 6000);
            resize();
            k = window.LSX.kit(THREE, renderer);
            space = await window.LSX.space(k, pause);
            document.body.classList.add('station-on');
            canvas.hidden = veil.hidden = ui.hidden = controls.hidden = false;
            running = true; nightNow = -1; last = null;
            raf = requestAnimationFrame(tick);
            poll();
            // the two ground scenes are heavy: build them after the first frames, one at a time
            setTimeout(() => { if (running && !desert) { desert = window.LSX.desert(k); nightNow = -1; } }, 600);
            setTimeout(() => { if (running && !forest) { forest = window.LSX.forest(k); if (pages) forest.setPages(pages); nightNow = -1; } }, 1400);
        } catch (e) {
            console.warn('Station could not start:', e);
            stop();
        } finally { booting = false; }
    }
    function stop() {
        running = false; cancelAnimationFrame(raf); clearTimeout(pollTimer);
        document.body.classList.remove('station-on', 'station-focus');
        if (canvas) canvas.hidden = true; if (veil) veil.hidden = true; if (ui) ui.hidden = true; if (controls) controls.hidden = true;
        closePanel();
        if (renderer) { renderer.dispose(); renderer.forceContextLoss(); renderer = null; }
        if (canvas) { canvas.remove(); canvas = null; buildCanvas(); canvas.hidden = true; }
        k = space = desert = forest = null;
    }

    // ---- page elements ------------------------------------------------------------------------------------------------
    let tagHome, tagLsx, pinBase, pinLsx, deepTags = [], btnTod, btnShip, btnWaiting, fadeTo = 0;
    function buildCanvas() {
        canvas = el('canvas'); canvas.id = 'station'; canvas.setAttribute('aria-hidden', 'true');
        document.body.prepend(canvas);
    }
    function buildDom() {
        buildCanvas();
        veil = el('div'); veil.id = 'station-veil'; veil.setAttribute('aria-hidden', 'true');
        ui = el('div'); ui.id = 'station-ui'; ui.setAttribute('aria-hidden', 'true');
        tagHome = el('div', 'st-tag st-home'); tagLsx = el('div', 'st-tag st-lsx');
        pinBase = el('div', 'st-pin', 'BASE'); pinLsx = el('div', 'st-pin st-lsx', 'PORT');
        tagHome.dataset.go = 'home'; pinBase.dataset.go = 'home'; tagLsx.dataset.go = 'lsx-tag'; pinLsx.dataset.go = 'lsx';
        deepTags = ['SUN', 'GAS GIANT', 'ICE WORLD', 'ASTEROID BELT', 'INNER WORLD', 'COMET'].map((t) => el('div', 'st-tag st-deep', t));
        ui.append(tagHome, tagLsx, pinBase, pinLsx, ...deepTags);
        controls = el('nav'); controls.id = 'station-controls'; controls.setAttribute('aria-label', 'Station view');
        const button = (label, title, fn) => { const b = el('button', '', label); b.type = 'button'; b.title = title; b.setAttribute('aria-label', title); b.addEventListener('click', fn); controls.append(b); return b; };
        button('DEEP', 'Zoom out to deep space', () => act('deep'));
        button('SPACE', 'Show both planets', () => act('space'));
        button('BASE', 'Fly down to the base on HOME', () => act('base'));
        button('FACTORY', 'Show the factory at the base', () => act('factory'));
        button('LSX', 'Fly down to the port on LSX', () => act('lsx'));
        button('−', 'Zoom out', () => act('zoom_out'));
        button('+', 'Zoom in', () => act('zoom_in'));
        btnTod = button(todMode, 'Day and night: auto, day or night', () => act({ AUTO: 'day', DAY: 'night', NIGHT: 'auto' }[todMode]));
        btnShip = button(grounded ? 'SHIP · GROUNDED' : 'SHIP · FLYING', 'Keep the ship on the ground at HOME, or let her fly to LSX', () => act(grounded ? 'fly' : 'ground'));
        btnWaiting = button('', 'Videos waiting for approval at LSX', () => act('approvals')); btnWaiting.className = 'st-waiting'; btnWaiting.hidden = true;
        document.body.append(veil, ui, controls);
        canvas.hidden = veil.hidden = ui.hidden = controls.hidden = true;
    }
    function resize() {
        if (!renderer) return;
        const w = window.innerWidth, h = window.innerHeight;
        renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
    }
    window.addEventListener('resize', resize);

    // ---- the camera: zoom -1 deep space, 0 both planets, 0.5 through the clouds, 1 standing on the pad ----------------
    const view = { zoom: 0, target: 0, yaw: 0, pitch: 0, dest: 'home', pending: null, fx: 0, focus: 0, panX: 0, panZ: 0, deepPan: null };
    let alfred = 0, alfredTo = 0;   // 0..1: Alfred is listening or speaking, so the scene eases in behind the wolf
    const setZoom = (z) => { view.target = clamp(z, -1, groundReady(view.dest) ? 1 : 0.46); };
    const goTo = (dest, z) => { if (view.dest === dest && !view.pending) setZoom(z); else { view.pending = [dest, z]; view.target = Math.min(view.target, 0); } };
    const groundReady = (dest) => !!(dest === 'lsx' ? forest : desert);
    function wide() {   // the both-planets view: far enough back that HOME and LSX sit out towards the two sides
        const t = Math.tan(38 * Math.PI / 360), a = Math.max(camera.aspect, 0.3);
        const D = clamp(215 / (0.62 * t * a), 420, 2800);
        return { tgt: new THREE.Vector3(0, 42, -15), dir: new THREE.Vector3(0, 0.12, 1).normalize(), D };
    }
    let upCache = null;
    function deepUp(w, h) {   // the camera's up in the deep view, so that the system's empty side points at the wolf
        const key = `${w}x${h}`; if (upCache && upCache.key === key) return upCache.up;
        const v = space.free, n = space.nrm, a = Math.atan2(0.25 * w, 0.37 * h);
        let up = v.clone().applyAxisAngle(n, a);
        if (v.dot(up.clone().cross(n)) < 0) up = v.clone().applyAxisAngle(n, -a);
        upCache = { key, up }; return up;
    }
    function placeCamera() {
        const V = (x, y, z) => new THREE.Vector3(x, y, z);
        camera.fov = 38 * (1 - 0.18 * alfred); camera.near = 0.1; camera.far = 6000;
        const W = wide();
        let near = 0.1, far = 6000;
        camera.up.set(0, 1, 0);
        const w = window.innerWidth, h = window.innerHeight;
        if (view.zoom < 0) {   // out past the planets: the whole solar system from above its plane
            // the sun sits low on the left (a view offset), and the emptiest side of the system lies behind the wolf
            const q = sm(clamp(-view.zoom)), n = space.nrm, up = deepUp(w, h);
            const tgt = W.tgt.clone().lerp(space.SUNP, q), D = W.D * Math.pow(16500 / W.D, q);
            if (view.deepPan) tgt.addScaledVector(view.deepPan, q);
            const deepDir = n.clone().multiplyScalar(0.94).addScaledVector(up, -0.34).normalize();
            const dir = W.dir.clone().lerp(deepDir, q).normalize().applyAxisAngle(n, view.yaw * q).applyAxisAngle(V(0, 1, 0), view.yaw * (1 - q));
            camera.up.copy(V(0, 1, 0).lerp(up.clone().applyAxisAngle(n, view.yaw), q).normalize());
            camera.position.copy(tgt).addScaledVector(dir, D); camera.lookAt(tgt);
            camera.setViewOffset(w, h, 0.25 * w * q, -0.2 * h * q, w, h);
            near = clamp(D * 0.004, 0.5, 30); far = D + 7000;
            camera.near = near; camera.far = far; camera.updateProjectionMatrix();
            return;
        }
        camera.clearViewOffset();
        if (view.dest ==='lsx' && view.zoom < 0.5) {   // flying in to the LSX port
            const q = clamp(view.zoom / 0.5), sN = sm(clamp(q * 1.8)), tgt = W.tgt.clone().lerp(space.LP, sN), D = W.D * Math.pow(2.2 / W.D, q);
            const dir = W.dir.clone().lerp(space.LN.clone().multiplyScalar(0.75).add(space.lB.clone().multiplyScalar(-0.66)), sN).normalize().applyAxisAngle(space.LN, view.yaw);
            const right = dir.clone().cross(space.LN).normalize(); dir.applyAxisAngle(right, -view.pitch * 0.6);
            camera.position.copy(tgt).addScaledVector(dir, D); camera.lookAt(tgt);
            near = clamp(D * 0.004, 0.02, 4); far = Math.max(3200, D + 3200);
        } else if (view.zoom < 0.5) {   // flying in to the base on HOME
            const q = clamp(view.zoom / 0.5), sN = sm(clamp(q * 1.8)), tgt = W.tgt.clone().lerp(space.P, sN), D = W.D * Math.pow(10 / W.D, q);
            const dir = W.dir.clone().lerp(space.N, sN).normalize().applyAxisAngle(V(0, 1, 0), view.yaw);
            const right = dir.clone().cross(V(0, 1, 0)).normalize(); dir.applyAxisAngle(right, -view.pitch * 0.6);
            camera.position.copy(tgt).addScaledVector(dir, D); camera.lookAt(tgt);
            near = clamp(D * 0.004, 0.02, 4); far = Math.max(3200, D + 3200);
        } else {   // on the ground
            const d = clamp((view.zoom - 0.5) / 0.5), R = 560 * Math.pow(16 / 560, d), elv = clamp(lerp(1.3, 0.14, sm(d)) + view.pitch, 0.04, 1.5), az = view.yaw + 0.25;
            const tgt = V(-2, lerp(0, 4.5, d), 0).lerp(V(0, lerp(0, 5, d), -96), view.dest === 'home' ? sm(view.fx) : 0).add(V(view.panX, 0, view.panZ));
            if (view.panX || view.panZ) tgt.y += (view.dest === 'lsx' ? forest.fh : desert.hgt)(tgt.x, tgt.z);
            camera.position.set(tgt.x + Math.sin(az) * Math.cos(elv) * R, tgt.y + Math.sin(elv) * R, tgt.z + Math.cos(az) * Math.cos(elv) * R);
            const ground = view.dest === 'lsx' ? forest.fh : desert.hgt;
            camera.position.y = Math.max(camera.position.y, ground(camera.position.x, camera.position.z) + 1.6); camera.lookAt(tgt);
        }
        camera.near = near; camera.far = far; camera.updateProjectionMatrix();
    }

    // ---- day and night: follow the viewer's clock (AUTO) or forced -------------------------------------------------
    let todMode = load('tod', 'AUTO'), nightNow = -1;
    if (!['AUTO', 'DAY', 'NIGHT'].includes(todMode)) todMode = 'AUTO';
    const clockNight = () => { const d = new Date(), h = d.getHours() + d.getMinutes() / 60; return h < 5.5 || h > 20.5 ? 1 : h < 7 ? 1 - (h - 5.5) / 1.5 : h > 19 ? (h - 19) / 1.5 : 0; };
    function applyNight(nf) {
        if (Math.abs(nf - nightNow) < 0.01) return; nightNow = nf;
        k.skyMat.uniforms.night.value = nf;
        const env = nf > 0.5 ? k.nightEnv : k.dayEnv;
        const sun = desert ? desert.night(nf, env) : { intensity: lerp(2.2, 0.28, nf), color: new THREE.Color(lerp(1, 0.62, nf), lerp(0.88, 0.7, nf), lerp(0.72, 1, nf)) };
        if (forest) forest.night(nf, env, sun);
        renderer.toneMappingExposure = lerp(1.05, 1.35, nf);
        k.helmetBeamMat.opacity = nf * 0.1; k.helmetBeams.forEach((b) => { b.visible = nf > 0.05; });
        if (btnTod) btnTod.textContent = todMode;
    }

    // ---- the trip, from the studio's real state ---------------------------------------------------------------------
    // mode: idle (ship home, routine work), loading (videos being made), out (flying to LSX), parked (waiting at the
    // LSX port for approval), back (flying home). T is the trip's timeline in the scene parts; C runs for the loops.
    const trip = { mode: 'idle', T: 52, blend: 1, since: 0, want: 'idle', first: true };
    let st = null, waitingIds = new Set(), delivered = new Set(), deliveries = [], pages = null, pageKey = '';
    // grounded (the user's word, kept in this browser) or paused content: the ship stays on the pad at HOME
    let grounded = load('grounded', true);
    function wantOf(s) { return grounded || s.paused ? 'idle' : s.waiting.length ? 'parked' : s.making ? 'loading' : 'idle'; }
    function jump(mode) {
        trip.mode = mode; trip.since = 0;
        trip.T = { idle: 52, loading: 8, parked: 28.4 }[mode]; trip.blend = 1;
    }
    function stepTrip(dt) {
        const w = trip.want; trip.since += dt;
        if (trip.mode === 'idle') {
            if (w !== 'idle') { trip.mode = 'loading'; trip.T = 8; trip.blend = reduced() ? 1 : 0; trip.since = 0; }
        } else if (trip.mode === 'loading') {
            trip.T = 8; trip.blend = Math.min(1, trip.blend + dt / 3);
            if (w === 'parked' && trip.since >= 4) { trip.mode = 'out'; trip.T = 10; }
            else if (w === 'idle' && trip.since >= 4) { jump('idle'); }
        } else if (trip.mode === 'out') {
            trip.T += dt; if (trip.T >= 28.4) { trip.mode = 'parked'; trip.T = 28.4; }
        } else if (trip.mode === 'parked') {
            trip.T = 28.4;
            if (w !== 'parked' && !deliveries.some((d) => d.fromShip && d.d < 4)) { trip.mode = 'back'; trip.T = 30.4; }
        } else if (trip.mode === 'back') {
            trip.T += dt; if (trip.T >= 52) jump('idle');
        }
        if (reduced() && (trip.mode === 'out' || trip.mode === 'back')) { if (trip.mode === 'out') { trip.mode = 'parked'; trip.T = 28.4; } else jump('idle'); }
        deliveries.forEach((d) => { d.d += dt; });
        const keep = forest ? forest.DELIVERY_SECONDS : 35;
        deliveries = deliveries.filter((d) => d.d < keep);
    }
    function deliver(item) {
        if (!item || delivered.has(item.id)) return;
        delivered.add(item.id);
        const slot = forest ? forest.slotOf(item.account) : -1;
        if (slot >= 0) deliveries.push({ slot, d: 0, fromShip: trip.mode === 'parked' });
    }
    function takeState(s) {
        if (!s || !Array.isArray(s.waiting)) return;
        const ids = new Set(s.waiting.map((v) => v.id)), approvedIds = new Set((s.approvals || []).map((a) => a.id));
        if (!trip.first) (st ? st.waiting : []).forEach((v) => { if (!ids.has(v.id) && approvedIds.has(v.id)) deliver(v); });
        waitingIds = ids; st = s; trip.want = wantOf(s);
        if (trip.first) { trip.first = false; jump(trip.want); (s.approvals || []).forEach((a) => delivered.add(a.id)); }
        const list = (s.accounts || []).map((a) => ({ name: a.name, label: a.label, colour: a.colour }));
        const key = JSON.stringify(list);
        if (key !== pageKey) { pageKey = key; pages = list; if (forest) forest.setPages(list); }
        const n = s.waiting.length;
        btnWaiting.hidden = !n; btnWaiting.textContent = `✓ ${n} WAITING`;
        if (panel && !panel.hidden) renderPanel();
    }
    async function poll() {
        clearTimeout(pollTimer);
        if (!running) return;
        if (!document.hidden) {
            try { const r = await fetch('/station/state'); if (r.ok) takeState(await r.json()); } catch (e) { /* the server is restarting */ }
        }
        if (running) pollTimer = setTimeout(poll, POLL_MS);
    }
    document.addEventListener('visibilitychange', () => {
        if (!running) return;
        if (document.hidden) { cancelAnimationFrame(raf); clearTimeout(pollTimer); }
        else { last = null; raf = requestAnimationFrame(tick); poll(); }
    });

    // ---- approval at LSX: each video waiting with a preview and a tick or a cross -----------------------------------
    let queue = [], panelMsg = '';
    async function fetchQueue() {
        try {
            const r = await fetch('/creator/queue');
            if (r.ok) { const q = await r.json(); queue = Array.isArray(q) ? q : (q.queue || q.videos || []); return; }
        } catch (e) { /* fall back below */ }
        queue = st ? st.waiting.slice() : [];
    }
    async function openPanel() {
        if (!panel) buildPanel();
        panel.hidden = false; panelMsg = '';
        placePanel();
        await fetchQueue();
        renderPanel();
    }
    function closePanel() {
        if (!panel) return;
        panel.querySelectorAll('video').forEach((v) => v.pause());
        panel.hidden = true;
    }
    function buildPanel() {
        panel = el('aside', 'hud-panel'); panel.id = 'station-panel'; panel.hidden = true; panel.setAttribute('aria-label', 'Videos waiting at LSX');
        document.body.append(panel);
        panel.addEventListener('keydown', (e) => { if (e.key === 'Escape') closePanel(); });
    }
    function placePanel() {
        // next to planet LSX when it is on screen, else in the right-hand corner
        const w = Math.min(380, window.innerWidth - 32);
        let x = window.innerWidth - w - 24, y = 84;
        if (space && camera && view.zoom < 0.2) {
            const p = space.LSXC.clone().project(camera);
            if (p.z < 1 && Math.abs(p.x) < 1.1) {
                const sx = (p.x * 0.5 + 0.5) * window.innerWidth, sy = (-p.y * 0.5 + 0.5) * window.innerHeight;
                x = sx - w - 70 > window.innerWidth / 2 ? sx - w - 70 : Math.min(sx + 70, window.innerWidth - w - 16); y = sy - 180;
            }
        }
        panel.style.width = `${w}px`;
        panel.style.left = `${clamp(x, 16, window.innerWidth - w - 16)}px`;
        panel.style.top = `${clamp(y, 64, Math.max(64, window.innerHeight - 420))}px`;
    }
    function renderPanel() {
        const list = queue.filter((v) => !delivered.has(v.id));
        panel.textContent = '';
        const head = el('div', 'st-head');
        head.append(el('h2', '', list.length ? `LSX · ${list.length} VIDEO${list.length === 1 ? '' : 'S'} WAITING` : 'LSX · NOTHING WAITING'));
        const x = el('button', 'st-close', '×'); x.type = 'button'; x.setAttribute('aria-label', 'Close'); x.addEventListener('click', closePanel); head.append(x);
        panel.append(head);
        if (panelMsg) panel.append(el('p', 'st-msg', panelMsg));
        const ul = el('ul');
        list.forEach((v) => {
            const li = el('li');
            const acc = el('div', 'st-acc', v.account || '');
            const page = st && (st.accounts || []).find((a) => a.name === v.account); if (page) acc.style.color = page.colour;
            li.append(acc, el('div', 'st-title', v.title || '(untitled)'));
            if (v.kind || v.created) li.append(el('div', 'st-meta', [v.kind, v.created].filter(Boolean).join(' · ').toUpperCase()));
            if (v.video_url) {
                const vid = el('video'); vid.src = v.video_url; vid.controls = true; vid.muted = true; vid.preload = 'metadata'; vid.playsInline = true;
                if (v.thumb_url) vid.poster = v.thumb_url; li.append(vid);
            } else if (v.thumb_url) { const img = el('img'); img.src = v.thumb_url; img.alt = ''; li.append(img); }
            else li.append(el('div', 'st-nopreview', 'NO PREVIEW YET'));
            const row = el('div', 'st-row');
            const reason = el('input'); reason.type = 'text'; reason.placeholder = 'REASON (OPTIONAL)'; reason.setAttribute('aria-label', `Why not "${v.title || ''}" (optional)`); reason.maxLength = 200;
            const yes = el('button', 'st-yes', '✓'); yes.type = 'button'; yes.title = 'Approve for upload'; yes.setAttribute('aria-label', `Approve "${v.title || ''}"`);
            const no = el('button', 'st-no', '✗'); no.type = 'button'; no.title = 'Reject'; no.setAttribute('aria-label', `Reject "${v.title || ''}"`);
            yes.addEventListener('click', () => decide(v, true, '', [yes, no]));
            no.addEventListener('click', () => decide(v, false, reason.value.trim(), [yes, no]));
            reason.addEventListener('keydown', (e) => { if (e.key === 'Enter') no.click(); });
            row.append(reason, yes, no); li.append(row); ul.append(li);
        });
        panel.append(ul);
    }
    async function decide(v, approve, reason, buttons) {
        buttons.forEach((b) => { b.disabled = true; });
        let out = null;
        try {
            const r = await fetch(`/creator/videos/${encodeURIComponent(v.id)}/${approve ? 'approve' : 'reject'}`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(approve ? {} : (reason ? { reason } : {})),
            });
            out = r.ok ? await r.json().catch(() => ({ ok: true })) : { ok: false, said: r.status === 404 ? 'The studio is not answering approvals yet.' : `The studio said no (${r.status}).` };
        } catch (e) { out = { ok: false, said: 'Could not reach the studio.' }; }
        if (out && out.ok !== false) {
            if (approve) deliver(v); else delivered.add(v.id);
            waitingIds.delete(v.id);
            if (st) { st.waiting = st.waiting.filter((w) => w.id !== v.id); trip.want = wantOf(st); }
            const n = st ? st.waiting.length : 0; btnWaiting.hidden = !n; btnWaiting.textContent = `✓ ${n} WAITING`;
            panelMsg = out.said || (approve ? `Approved "${v.title}".` : `Rejected "${v.title}".`);
            setTimeout(poll, 1500);
        } else {
            panelMsg = (out && out.said) || 'That did not work.';
            buttons.forEach((b) => { b.disabled = false; });
        }
        renderPanel();
    }

    // ---- Alfred: station_view cards, and easing in behind the wolf while he listens or speaks ------------------------
    function act(action) {
        if (action === 'off') { save('on', false); stop(); return; }
        if (action === 'on') { save('on', true); start(); return; }
        if (!running) return;
        const z = reduced();
        if (action === 'base') { view.panX = view.panZ = 0; view.focus = 0; goTo('home', 0.86); }
        else if (action === 'factory') { view.panX = view.panZ = 0; view.focus = 1; view.yaw = 0; view.pitch = -0.1; goTo('home', 0.84); }
        else if (action === 'lsx') goTo('lsx', 0.86);
        else if (action === 'space') { view.deepPan = null; goTo(view.dest, 0); view.yaw = 0; view.pitch = 0; }
        else if (action === 'deep') { view.deepPan = null; if (view.zoom > 0.02) { view.pending = [view.dest, -1]; view.target = 0; } else setZoom(-1); view.yaw = 0; view.pitch = 0; }
        else if (action === 'zoom_in') setZoom(view.target + 0.12);
        else if (action === 'zoom_out') setZoom(view.target - 0.12);
        else if (action === 'night' || action === 'day' || action === 'auto') { todMode = action.toUpperCase(); save('tod', todMode); nightNow = -1; if (btnTod) btnTod.textContent = todMode; }
        else if (action === 'approvals') openPanel();
        else if (action === 'ground' || action === 'fly') { grounded = action === 'ground'; save('grounded', grounded); if (st) trip.want = wantOf(st); if (btnShip) btnShip.textContent = grounded ? 'SHIP · GROUNDED' : 'SHIP · FLYING'; }
        if (z && !view.pending) view.zoom = view.target;
    }
    window.addEventListener('jarvis:popup', (e) => {
        const card = e.detail || {};
        if (card.kind === 'station') { e.stopImmediatePropagation(); act((card.data || {}).action); }
    }, true);
    window.jarvisPopupKinds = window.jarvisPopupKinds || {};
    window.jarvisPopupKinds.station = (card, body) => {   // if a card reaches popup.js some other way
        act((card.data || {}).action);
        setTimeout(() => { const win = body.closest('.popup'); const b = win && win.querySelector('.pop-bar .pop-btn[title="Close"]'); if (b) b.click(); }, 0);
    };
    function watchAlfred() {
        const orb = $('orb'); if (!orb) return;
        const check = () => {
            alfredTo = /thinking|speaking/.test(orb.className) ? 1 : 0;
            document.body.classList.toggle('station-focus', running && alfredTo > 0);
            const r = orb.getBoundingClientRect();
            if (veil && r.width) { veil.style.setProperty('--sx', `${r.left + r.width / 2}px`); veil.style.setProperty('--sy', `${r.top + r.height / 2}px`); }
        };
        new MutationObserver(check).observe(orb, { attributes: true, attributeFilter: ['class'] });
        check();
    }

    // ---- pointer, wheel and drag: only on empty background ---------------------------------------------------------
    function background(t) {
        if (!running || !t) return false;
        if (t === document.documentElement || t === document.body || t === canvas || t === ui || ui.contains(t)) return true;
        if (t.id === 'app' || t.id === 'chat') return true;
        if (t.id === 'orb-wrap') return !t.classList.contains('memory');
        return false;
    }
    let drag = null, pinch = 0; const touches = new Map();
    document.addEventListener('pointerdown', (e) => {
        if (!background(e.target) || (e.pointerType === 'mouse' && e.button !== 0)) return;
        touches.set(e.pointerId, [e.clientX, e.clientY]);
        if (touches.size === 1) drag = { x: e.clientX, y: e.clientY, at: performance.now(), moved: false };
    });
    window.addEventListener('pointermove', (e) => {
        if (!touches.has(e.pointerId)) return;
        const [px, py] = touches.get(e.pointerId); touches.set(e.pointerId, [e.clientX, e.clientY]);
        if (touches.size === 1 && drag) {
            if (Math.hypot(e.clientX - drag.x, e.clientY - drag.y) > 6) drag.moved = true;
            if (drag.moved) { view.yaw -= (e.clientX - px) * 0.006; view.pitch = clamp(view.pitch + (e.clientY - py) * 0.004, -0.6, 0.9); }
        } else if (touches.size === 2) {
            const [a, b] = [...touches.values()], dist = Math.hypot(a[0] - b[0], a[1] - b[1]);
            if (pinch) setZoom(view.target + (dist - pinch) * 0.0025); pinch = dist; if (drag) drag.moved = true;
        }
    });
    const up = (e) => {
        if (!touches.has(e.pointerId)) return;
        touches.delete(e.pointerId); if (touches.size < 2) pinch = 0;
        if (e.type === 'pointerup' && drag && !drag.moved && performance.now() - drag.at < 600 && touches.size === 0) tap(e.clientX, e.clientY);
        if (!touches.size) drag = null;
    };
    window.addEventListener('pointerup', up); window.addEventListener('pointercancel', up);
    document.addEventListener('wheel', (e) => {
        if (e.ctrlKey || !background(e.target)) return;
        e.preventDefault(); setZoom(view.target - e.deltaY * 0.0007);
    }, { passive: false });
    let ray = null;
    function tap(x, y) {
        // the tags and pins sit under the HUD's layout box, so look for them under the pointer
        const hit = document.elementsFromPoint(x, y).find((n) => n.dataset && n.dataset.go && ui.contains(n) && getComputedStyle(n).opacity > 0.3);
        if (hit) {
            const go = hit.dataset.go, waiting = st ? st.waiting.length : 0;
            if (go === 'home') { view.focus = 0; goTo('home', 0.86); }
            else if (go === 'lsx-tag') { if (waiting) openPanel(); else goTo('lsx', 0.86); }
            else if (go === 'lsx') { goTo('lsx', 0.86); if (waiting) openPanel(); }
            return;
        }
        if (view.zoom >= 0.5 || !space) return;
        ray = ray || new THREE.Raycaster();
        ray.setFromCamera({ x: x / window.innerWidth * 2 - 1, y: -y / window.innerHeight * 2 + 1 }, camera);
        const home = space.pickables.home, lsx = space.pickables.lsx, got = ray.intersectObjects([...home, ...lsx])[0];
        if (got) { if (lsx.includes(got.object)) goTo('lsx', 0.86); else { view.focus = 0; goTo('home', 0.86); } }
    }

    // ---- overlays -------------------------------------------------------------------------------------------------
    function screenOf(p) {
        const q = p.clone().project(camera);
        return { x: (q.x * 0.5 + 0.5) * window.innerWidth, y: (-q.y * 0.5 + 0.5) * window.innerHeight, on: q.z < 1 && Math.abs(q.x) < 1.2 && Math.abs(q.y) < 1.2 };
    }
    function place(node, p, show) {
        if (!show || !p.on) { node.style.opacity = 0; return; }
        node.style.transform = `translate(${p.x.toFixed(1)}px, ${p.y.toFixed(1)}px)`; node.style.opacity = 1;
    }
    function overlays(onGround) {
        const THREEV = (x, y, z) => new THREE.Vector3(x, y, z), tags = view.zoom < 0.12 && !onGround;
        const n = st ? st.waiting.length : 0, making = st ? st.making : 0, m = trip.mode;
        const deep = view.zoom < -0.3, lift = deep ? 0 : 1; ui.classList.toggle('deep', deep);
        place(tagHome, screenOf(space.HOMEC.clone().add(THREEV(0, space.HOMER * 1.15 * lift, 0))), tags);
        place(tagLsx, screenOf(space.LSXC.clone().add(THREEV(0, space.LSXR * 1.2 * lift, 0))), tags);
        const homeSub = m === 'loading' ? `MAKING ${making || ''} VIDEO${making === 1 ? '' : 'S'} · LOADING`.replace('  ', ' ') : m === 'out' ? 'SHIP ON ITS WAY TO LSX' : m === 'parked' ? 'CREW WAITING' : m === 'back' ? 'SHIP ON ITS WAY BACK' : 'ALL QUIET';
        const lsxSub = n ? `${n} VIDEO${n === 1 ? '' : 'S'} WAITING` : deliveries.length ? 'DELIVERING' : m === 'out' ? 'SHIP INBOUND' : '';
        setTag(tagHome, 'HOME', homeSub); setTag(tagLsx, 'LSX', lsxSub); tagLsx.classList.toggle('waiting', n > 0);
        const pp = screenOf(space.P), showB = !onGround && view.dest === 'home' && view.zoom < 0.42 && view.zoom > -0.35 && space.P.clone().sub(space.HOMEC).dot(camera.position.clone().sub(space.P)) > 0;
        place(pinBase, pp, showB);
        const lp = screenOf(space.LP), showL = !onGround && view.zoom > -0.35 && (view.dest === 'home' ? view.zoom < 0.12 : view.zoom < 0.3) && space.LN.dot(camera.position.clone().sub(space.LP)) > 0;
        place(pinLsx, lp, showL); pinLsx.textContent = n ? `PORT · ${n} WAITING` : 'PORT'; pinLsx.classList.toggle('waiting', n > 0);
        const bodies = [space.SUNP.clone().add(THREEV(0, space.SUNR * 1.6, 0)), space.giant.pos.clone().add(THREEV(0, 220, 0)), space.ice.pos.clone().add(THREEV(0, 80, 0)),
            space.SUNP.clone().add(space.free.clone().applyAxisAngle(space.nrm, -1.1).multiplyScalar(space.belt)),
            space.inner.pos.clone().add(THREEV(0, 60, 0)), space.comet.clone().add(THREEV(0, 50, 0))];
        deepTags.forEach((t, i) => place(t, screenOf(bodies[i]), deep));
    }
    function setTag(node, name, sub) {
        const key = `${name}|${sub}`; if (node.dataset.key === key) return; node.dataset.key = key;
        node.textContent = name; if (sub) node.append(el('small', '', sub));
    }

    // ---- arrow keys: on the ground they walk the camera round the base or the port; out in space left and right
    // turn round the planets and up and down tilt; zoomed out to deep space they slide across the solar system.
    // + and - zoom. Keys typed into the chat box, or any other field, are left alone.
    const keys = new Set(), ARROWS = ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'];
    const typing = (t) => t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName));
    window.addEventListener('keydown', (e) => {
        if (!running || typing(e.target) || e.ctrlKey || e.metaKey || e.altKey) return;
        // a game or a calendar in a pop-up may want the same keys: wait until every handler has had the key, and
        // leave it if one of them used it
        setTimeout(() => {
            if (e.defaultPrevented) return;
            if (ARROWS.includes(e.key)) keys.add(e.key);
            else if (e.key === '+' || e.key === '=') setZoom(view.target + 0.06);
            else if (e.key === '-' || e.key === '_') setZoom(view.target - 0.06);
        }, 0);
    });
    window.addEventListener('keyup', (e) => keys.delete(e.key));
    window.addEventListener('blur', () => keys.clear());
    function arrowMove(dt) {
        if (!keys.size || !dt) return;
        const x = (keys.has('ArrowRight') ? 1 : 0) - (keys.has('ArrowLeft') ? 1 : 0), y = (keys.has('ArrowUp') ? 1 : 0) - (keys.has('ArrowDown') ? 1 : 0);
        if (view.zoom >= 0.5) {   // walk: up goes the way the camera faces, left and right step sideways
            const d = clamp((view.zoom - 0.5) / 0.5), R = 560 * Math.pow(16 / 560, d), az = view.yaw + 0.25, sp = Math.max(8, R * 0.7) * dt;
            view.panX += (-Math.sin(az) * y + Math.cos(az) * x) * sp; view.panZ += (-Math.cos(az) * y - Math.sin(az) * x) * sp;
            const lim = view.dest === 'lsx' ? 300 : 450, r = Math.hypot(view.panX, view.panZ);
            if (r > lim) { view.panX *= lim / r; view.panZ *= lim / r; }
        } else if (view.zoom < -0.3 && camera) {   // slide across the system's plane
            const n = space.nrm, right = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 0).projectOnPlane(n).normalize();
            const fwd = n.clone().cross(right).normalize();
            view.deepPan = view.deepPan || new THREE.Vector3();
            view.deepPan.addScaledVector(right, x * 5000 * dt).addScaledVector(fwd, y * 5000 * dt).clampLength(0, 9000);
        } else {
            view.yaw -= x * 1.2 * dt; view.pitch = clamp(view.pitch + y * 0.8 * dt, -0.6, 0.9);
        }
    }

    // ---- the loop ---------------------------------------------------------------------------------------------------
    let last = null, C = 0, lastDraw = 0;
    function tick(now) {
        if (!running) return;
        raf = requestAnimationFrame(tick);
        const moving = Math.abs(view.target - view.zoom) > 0.002 || view.pending || drag || keys.size || Math.abs(alfredTo - alfred) > 0.01 || Math.abs(view.focus - view.fx) > 0.01;
        const calm = reduced();
        const every = calm && !moving ? 250 : moving || view.zoom >= 0.5 || trip.mode === 'out' || trip.mode === 'back' ? 0 : 32;   // about 30 fps when nothing moves
        if (now - lastDraw < every) return;
        lastDraw = now;
        const dt = last === null ? 0 : Math.min(0.1, (now - last) / 1000); last = now;
        if (!calm) C += dt;
        arrowMove(dt);
        const rate = calm ? 1 : Math.min(1, dt * (view.pending ? 3 : 5));
        view.zoom += (view.target - view.zoom) * rate; view.fx += (view.focus - view.fx) * (calm ? 1 : Math.min(1, dt * 2));
        alfred += (alfredTo - alfred) * (calm ? 1 : Math.min(1, dt * 2.2));
        if (view.pending && view.zoom < 0.02) { view.panX = view.panZ = 0; view.dest = view.pending[0]; view.zoom = Math.min(view.zoom, 0); setZoom(view.pending[1]); view.pending = null; if (calm) view.zoom = view.target; }
        if (view.zoom >= 0.5 && !groundReady(view.dest)) { view.zoom = 0.46; view.target = Math.min(view.target, 0.46); }
        stepTrip(dt);
        applyNight(todMode === 'AUTO' ? clockNight() : todMode === 'NIGHT' ? 1 : 0);
        const onGround = view.zoom >= 0.5, inDesert = onGround && view.dest === 'home', scene = onGround ? (inDesert ? desert.scene : forest.scene) : space.scene;
        placeCamera();
        const idle = trip.mode === 'idle';
        if (!onGround) {
            let open = 0; deliveries.forEach((d) => { if (d.fromShip) open = Math.max(open, clamp(d.d / 0.5) * (1 - clamp((d.d - 3.4) / 0.4))); });
            space.frame(trip.T, C, { idle, nearLsx: view.dest === 'lsx' ? sm(clamp(view.zoom / 0.5)) : 0, rampOpen: open, camera, deep: sm(clamp(-view.zoom / 0.4)) });
        } else if (inDesert) desert.frame(trip.T, C, idle, trip.mode === 'loading' ? trip.blend : 1);
        else forest.frame(idle ? 52 : trip.T, C, deliveries);
        renderer.render(scene, camera);
        canvas.style.opacity = (1 - clamp(1 - Math.abs(view.zoom - 0.5) / 0.06)).toFixed(3);
        veil.style.opacity = Math.max(alfred * 0.85, onGround ? 0.3 : 0).toFixed(3);   // bright ground scenes dim a little behind the wolf
        overlays(onGround);
    }

    // ---- start ------------------------------------------------------------------------------------------------------
    document.addEventListener('jarvis:config', (e) => {
        config = e.detail || {};
        allowed = config.station !== false && String(config.theme || '').startsWith('hud');
        watchAlfred();
        start();
    });
    document.addEventListener('jarvis:motion', () => { if (reduced()) { view.zoom = view.target; alfred = alfredTo; } });
    window.JarvisStation = { act, state: () => ({ running, trip: { ...trip }, view: { ...view }, deliveries: deliveries.length }) };
})();
