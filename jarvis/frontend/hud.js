// HUD theme: the wolf (or the particle sphere if it can't load), radar, audio waveform, clock and live status. Only runs when body.hud is set.
(() => {
    const COLORS = { idle: '#3fa9ff', listening: '#4fd1ff', thinking: '#ffc24a', speaking: '#8ae9ff' };
    function loadColors() {   // the theme's CSS variables decide the colours
        const css = getComputedStyle(document.body);
        const pick = (name, fallback) => css.getPropertyValue(name).trim() || fallback;
        COLORS.idle = pick('--hud-idle', COLORS.idle);
        COLORS.listening = pick('--hud-listen', COLORS.listening);
        COLORS.thinking = pick('--hud-think', COLORS.thinking);
        COLORS.speaking = pick('--hud-speak', COLORS.speaking);
    }
    const ENERGY = { idle: 0.25, listening: 0.6, thinking: 0.8, speaking: 1 };
    let reduceMotion = window.jarvisAccess ? document.documentElement.classList.contains('a11y-motion') : window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    document.addEventListener('jarvis:motion', () => { reduceMotion = document.documentElement.classList.contains('a11y-motion'); });   // access.js
    const orb = document.getElementById('orb');
    const $ = (id) => document.getElementById(id);
    let config = {};
    let started = false;

    const state = () => (['listening', 'thinking', 'speaking'].find((s) => orb.classList.contains(s)) || 'idle');

    function fitCanvas(canvas) {
        const dpr = window.devicePixelRatio || 1;
        const { width, height } = canvas.getBoundingClientRect();
        if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {
            canvas.width = Math.round(width * dpr);
            canvas.height = Math.round(height * dpr);
        }
        const ctx = canvas.getContext('2d');
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        return [ctx, width, height];
    }

    // ---- particle sphere with rotating tick rings ------------------------------

    const N_POINTS = 900;
    const POINTS = Array.from({ length: N_POINTS }, (_, i) => {
        const y = 1 - (i / (N_POINTS - 1)) * 2;           // fibonacci sphere
        const r = Math.sqrt(1 - y * y);
        const theta = i * Math.PI * (3 - Math.sqrt(5));
        return [Math.cos(theta) * r, y, Math.sin(theta) * r];
    });
    let level = 0.25;
    let wolfMix = 0;     // fades the wolf in when the page loads; it replaces the particle sphere
    let streamMix = 0;   // how much the wolf's dots stream out: only while thinking

    function drawSphere(t) {
        const [ctx, w, h] = fitCanvas($('hud-sphere'));
        const s = state();
        const color = COLORS[s];
        level += (ENERGY[s] + (s === 'listening' ? micLevel * 1.5 : 0) - level) * 0.05;
        const memory = window.HudMemory && window.HudMemory.open;
        wolfMix += ((window.HudWolf ? 1 : 0) - wolfMix) * 0.06;
        streamMix += ((s === 'thinking' ? 1 : 0) - streamMix) * 0.04;
        const fade = 1 - wolfMix;
        const cx = w / 2, cy = h / 2, R = Math.min(w, h, 420) * 0.27 * (1 + level * 0.08 + Math.sin(t / 400) * 0.01 * level) * (1 - wolfMix * 0.5);
        ctx.clearRect(0, 0, w, h);
        if (wolfMix > 0.01) {
            window.HudWolf.draw(ctx, w, h, t, wolfMix, COLORS.idle, reduceMotion, {
                stream: reduceMotion ? 0 : streamMix, labels: memory ? window.HudMemory.labels() : null, hover: memory ? window.HudMemory.hover : -1,
            });
        }
        if (fade < 0.01) return;

        // core glow
        const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * 1.1);
        glow.addColorStop(0, color + 'cc');
        glow.addColorStop(0.35, color + '33');
        glow.addColorStop(1, 'transparent');
        ctx.fillStyle = glow;
        ctx.globalAlpha = fade;
        ctx.fillRect(0, 0, w, h);

        // particles
        const rotY = t / (reduceMotion ? 20000 : 4000) * (0.6 + level);
        const rotX = 0.4;
        const [sy, cyr, sx, cxr] = [Math.sin(rotY), Math.cos(rotY), Math.sin(rotX), Math.cos(rotX)];
        ctx.fillStyle = color;
        for (const [x0, y0, z0] of POINTS) {
            const x1 = x0 * cyr + z0 * sy, z1 = -x0 * sy + z0 * cyr;
            const y2 = y0 * cxr - z1 * sx, z2 = y0 * sx + z1 * cxr;
            const depth = (z2 + 1) / 2;
            ctx.globalAlpha = (0.15 + depth * 0.85) * fade;
            const size = 0.6 + depth * 1.4;
            ctx.fillRect(cx + x1 * R - size / 2, cy + y2 * R - size / 2, size, size);
        }
        ctx.globalAlpha = 1;

        // tick ring
        ctx.strokeStyle = color;
        const ring = R * 1.42, spin = t / (reduceMotion ? 60000 : 12000);
        for (let i = 0; i < 90; i++) {
            const a = spin + (i / 90) * Math.PI * 2;
            const long = i % 5 === 0;
            ctx.globalAlpha = (long ? 0.9 : 0.4) * fade;
            ctx.lineWidth = long ? 2 : 1;
            ctx.beginPath();
            ctx.moveTo(cx + Math.cos(a) * ring, cy + Math.sin(a) * ring);
            ctx.lineTo(cx + Math.cos(a) * (ring + (long ? 12 : 6)), cy + Math.sin(a) * (ring + (long ? 12 : 6)));
            ctx.stroke();
        }
        // counter-rotating arcs
        ctx.lineWidth = 2;
        for (let i = 0; i < 3; i++) {
            const start = -spin * 1.6 + (i * Math.PI * 2) / 3;
            ctx.globalAlpha = 0.7 * fade;
            ctx.beginPath();
            ctx.arc(cx, cy, R * 1.25, start, start + 0.9);
            ctx.stroke();
        }
        ctx.globalAlpha = 0.25 * fade;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(cx, cy, ring + 20, 0, Math.PI * 2);
        ctx.stroke();
        ctx.globalAlpha = 1;
    }

    // ---- radar -------------------------------------------------------------------

    function drawRadar(t) {
        const [ctx, w, h] = fitCanvas($('hud-radar'));
        const cx = w / 2, cy = h / 2, r = Math.min(w, h) / 2 - 4;
        const color = COLORS[state()];
        ctx.clearRect(0, 0, w, h);
        if (r <= 0) return;   // the radar panel is hidden in narrow windows
        ctx.strokeStyle = color;
        ctx.globalAlpha = 0.35;
        for (let i = 1; i <= 4; i++) {
            ctx.beginPath();
            ctx.arc(cx, cy, (r * i) / 4, 0, Math.PI * 2);
            ctx.stroke();
        }
        ctx.beginPath();
        ctx.moveTo(cx - r, cy); ctx.lineTo(cx + r, cy);
        ctx.moveTo(cx, cy - r); ctx.lineTo(cx, cy + r);
        ctx.stroke();
        const a = reduceMotion ? 0.8 : (t / 3000) % (Math.PI * 2);   // reduced motion: the sweep stands still
        for (let i = 0; i < 30; i++) {                     // fading sweep trail
            ctx.globalAlpha = 0.5 * (1 - i / 30);
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.arc(cx, cy, r, a - (i + 1) * 0.03, a - i * 0.03);
            ctx.closePath();
            ctx.fillStyle = color;
            ctx.fill();
        }
        ctx.globalAlpha = 1;
    }

    // ---- audio waveform (real microphone level while listening) ----------------------

    let analyser = null, samples = null, micLevel = 0;

    async function startMic() {
        if (analyser || !navigator.mediaDevices) return;
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            analyser = ctx.createAnalyser();
            analyser.fftSize = 128;
            samples = new Uint8Array(analyser.frequencyBinCount);
            ctx.createMediaStreamSource(stream).connect(analyser);
            $('hud-mic').textContent = 'MIC · ON';
            $('hud-mic').classList.add('on');
        } catch (e) { /* no mic permission: the waveform just animates */ }
    }

    function drawWave(t) {
        const [ctx, w, h] = fitCanvas($('hud-wave'));
        const s = state();
        const bars = 40;
        ctx.clearRect(0, 0, w, h);
        ctx.fillStyle = COLORS[s];
        if (analyser) {
            analyser.getByteFrequencyData(samples);
            micLevel = samples.reduce((a, b) => a + b, 0) / samples.length / 255;
        }
        for (let i = 0; i < bars; i++) {
            let v;
            if (analyser && s === 'listening') v = samples[Math.floor((i / bars) * samples.length * 0.8)] / 255;
            else v = (0.15 + ENERGY[s] * 0.6) * (0.5 + 0.5 * Math.sin(t / 180 + i * 0.6) * Math.sin(t / 530 + i * 0.23));
            const bh = Math.max(2, Math.abs(v) * h);
            ctx.globalAlpha = 0.5 + Math.abs(v) * 0.5;
            ctx.fillRect(i * (w / bars) + 1, (h - bh) / 2, w / bars - 2, bh);
        }
        ctx.globalAlpha = 1;
    }

    // ---- text readouts -------------------------------------------------------------

    const pad = (n) => String(n).padStart(2, '0');
    const t0 = Date.now();

    function tickText() {
        const now = new Date();
        $('hud-clock').textContent = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
        $('hud-date').textContent = now.toLocaleDateString('en-GB', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' }).toUpperCase();
        const up = Math.floor((Date.now() - t0) / 1000);
        $('hud-uptime').textContent = `${pad(Math.floor(up / 3600))}:${pad(Math.floor(up / 60) % 60)}:${pad(up % 60)}`;
        $('hud-status').textContent = state().toUpperCase();
        const conn = navigator.connection && navigator.connection.effectiveType;
        $('hud-net').textContent = navigator.onLine ? `ONLINE${conn ? ' · ' + conn.toUpperCase() : ''}` : 'OFFLINE';
        const link = $('hud-link');
        link.textContent = started ? 'LINK · ACTIVE' : 'LINK · STANDBY';
        link.classList.toggle('on', started);
    }

    async function loadWeather() {
        try {
            const data = await (await fetch('/weather')).json();
            if (data.text) $('hud-weather').textContent = data.text;
        } catch (e) { /* keep the last reading */ }
    }

    async function loadEmails() {
        try {
            const data = await (await fetch('/emails')).json();
            const el = $('hud-emails');
            if (data.error) {
                el.textContent = data.error;   // e.g. WRONG PASSWORD; hover for how to fix it
            } else if (data.unread === null || data.unread === undefined) {
                el.textContent = 'NOT SET UP';
            } else {
                el.textContent = `${data.unread} UNREAD`;
            }
            el.title = data.fix || '';
        } catch (e) { /* keep the last count */ }
    }

    let lastFrame = 0;
    function frame(t) {
        requestAnimationFrame(frame);   // first, so one bad frame can't stop the animation
        if (t - lastFrame < 30) return;   // about 30 fps is smooth for the wolf, radar and wave, at half the work
        lastFrame = t;
        drawSphere(t);
        drawRadar(t);
        drawWave(t);
    }

    // the weather panel shrinks to its title bar and back; the choice is kept in this browser
    function envToggle() {
        const panel = $('hud-env'), button = $('hud-env-toggle');
        if (!panel || !button || button.dataset.ready) return;
        button.dataset.ready = '1';
        const show = (open) => {
            panel.classList.toggle('shut', !open);
            button.setAttribute('aria-expanded', String(open));
            $('hud-env-sign').textContent = open ? '−' : '+';
            try { localStorage.setItem('jarvis-env-open', open ? '1' : '0'); } catch (e) { /* private window */ }
        };
        let open = true;
        try { open = localStorage.getItem('jarvis-env-open') !== '0'; } catch (e) { /* private window */ }
        show(open);
        button.addEventListener('click', () => show(panel.classList.contains('shut')));
    }

    function start(cfg) {
        if (!document.body.classList.contains('hud')) return;
        config = cfg;
        loadColors();
        $('hud-title').textContent = config.name.toUpperCase().split('').join('.') + '.';
        $('hud-model').textContent = (config.model || '—').toUpperCase();
        $('hud-voice').textContent = config.serverVoice ? 'ELEVENLABS' : 'BROWSER';
        if (config.city) $('hud-city').textContent = `ENVIRONMENT · ${config.city.toUpperCase()}`;
        envToggle();
        if (navigator.getBattery) {
            navigator.getBattery().then((b) => {
                const show = () => { $('hud-battery').textContent = `${Math.round(b.level * 100)}%${b.charging ? ' · CHARGING' : ''}`; };
                show();
                b.addEventListener('levelchange', show);
                b.addEventListener('chargingchange', show);
            });
        }
        orb.addEventListener('click', () => { started = true; startMic(); });
        document.getElementById('type-form').addEventListener('submit', () => { started = true; });
        tickText();
        setInterval(tickText, 1000);
        loadWeather();
        setInterval(loadWeather, 10 * 60 * 1000);
        loadEmails();
        setInterval(loadEmails, 60 * 1000);
        requestAnimationFrame(frame);
    }

    document.addEventListener('jarvis:config', (e) => start(e.detail));
    // hudplus.js switches the colour theme live: pick up the new colours.
    document.addEventListener('jarvis:theme', () => { loadColors(); if (window.HudWolf) window.HudWolf.resetColors(); });
})();
