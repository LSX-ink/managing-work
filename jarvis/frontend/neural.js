// HUD "thinking" visual: a neuron network shaped like a brain that fires in brainwaves.
// hud.js cross-fades the particle sphere into this while Alfred is thinking.
window.HudBrain = (() => {
    // Head in profile, facing left, in unit coordinates (y points down). Not drawn: it only shapes the brain.
    const HEAD = [
        [0.31, 0.92], [0.34, 0.72], [0.52, 0.52], [0.66, 0.22], [0.70, -0.08], [0.64, -0.38], [0.48, -0.64],
        [0.24, -0.82], [-0.04, -0.88], [-0.32, -0.78], [-0.50, -0.58], [-0.58, -0.34], [-0.58, -0.16],
        [-0.63, -0.08], [-0.61, 0.02], [-0.74, 0.20], [-0.65, 0.26], [-0.63, 0.31], [-0.67, 0.37],
        [-0.62, 0.42], [-0.66, 0.48], [-0.59, 0.55], [-0.56, 0.64], [-0.44, 0.70], [-0.24, 0.71],
        [-0.14, 0.82], [-0.13, 0.92],
    ];
    const CENTRE = [0.06, -0.26];   // middle of the brain: brainwaves ripple out from here
    const REGIONS = [
        { name: 'PREFRONTAL', at: [-0.34, -0.48], hue: 12 },
        { name: 'MOTOR', at: [-0.02, -0.66], hue: -22 },
        { name: 'SENSORY', at: [0.30, -0.50], hue: 6 },
        { name: 'ASSOCIATION', at: [0.04, -0.30], hue: -8 },
        { name: 'LANGUAGE', at: [-0.30, -0.12], hue: 18 },
        { name: 'PREDICTIVE', at: [0.48, -0.18], hue: -30 },
        { name: 'HIPPOCAMPUS', at: [0.10, 0.02], hue: 24 },
        { name: 'CEREBELLUM', at: [0.44, 0.22], hue: -14 },
    ];

    // seeded random so the network looks the same every time
    let seed = 7;
    const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    const gauss = () => (rand() + rand() + rand() - 1.5) / 1.5;

    const headPath = new Path2D();
    headPath.moveTo(...HEAD[0]);
    for (let i = 1; i < HEAD.length - 1; i++) {   // smooth curve through the midpoints
        const [x, y] = HEAD[i], [nx, ny] = HEAD[i + 1];
        headPath.quadraticCurveTo(x, y, (x + nx) / 2, (y + ny) / 2);
    }
    headPath.lineTo(...HEAD[HEAD.length - 1]);
    const probe = document.createElement('canvas').getContext('2d');
    const inHead = (x, y) => probe.isPointInPath(headPath, x, y);

    const NODES = [];
    REGIONS.forEach((r, ri) => {
        for (let n = 0; n < 30; n++) {
            const x = r.at[0] + gauss() * 0.24, y = r.at[1] + gauss() * 0.18;
            if (inHead(x, y) && inHead(x + 0.06, y) && inHead(x - 0.06, y - 0.06)) {
                NODES.push({ x, y, region: ri, phase: rand() * Math.PI * 2, size: 0.8 + rand() * 1.6 });
            }
        }
    });
    const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
    const EDGES = [];
    NODES.forEach((a, i) => {
        NODES.map((b, j) => [j, dist(a, b)])
            .filter(([j, d]) => j > i && d < (NODES[j].region === a.region ? 0.16 : 0.12))
            .sort((p, q) => p[1] - q[1]).slice(0, 3)
            .forEach(([j]) => EDGES.push([i, j]));
    });
    // strands reaching out of the head, like dendrites
    const STRANDS = Array.from({ length: 70 }, () => {
        const from = NODES[Math.floor(rand() * NODES.length)];
        const ang = Math.atan2(from.y - CENTRE[1], from.x - CENTRE[0]) + gauss() * 0.9;
        return { from, ang, len: 0.35 + rand() * 0.45, bend: gauss() * 0.5, phase: rand() * Math.PI * 2 };
    });
    function hexToHsl(hex) {
        const m = hex.replace('#', '').match(/../g);
        if (!m) return [35, 100, 60];
        const [r, g, b] = m.map((v) => parseInt(v, 16) / 255);
        const max = Math.max(r, g, b), min = Math.min(r, g, b), l = (max + min) / 2;
        if (max === min) return [0, 0, l * 100];
        const d = max - min, s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
        const h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
        return [h * 60, s * 100, l * 100];
    }
    let base = null;   // [hue, saturation] of the theme's main colour

    const pulses = [];   // signals travelling along edges
    let lastSpawn = 0;

    function draw(ctx, w, h, t, mix, themeColor, slow) {
        if (!base) base = hexToHsl(themeColor);
        const hsl = (dh, l, a) => `hsla(${base[0] + dh}, ${base[1]}%, ${l}%, ${a})`;
        const speed = slow ? 0.25 : 1;
        const T = t * speed;
        const S = Math.min(w, h) * 0.42 * (0.85 + 0.15 * mix);
        const ox = w / 2 - CENTRE[0] * S, oy = h / 2 - (CENTRE[1] + 0.12) * S;
        const X = (x) => ox + x * S, Y = (y) => oy + y * S;
        const ccx = X(CENTRE[0]), ccy = Y(CENTRE[1]);

        ctx.save();
        ctx.globalAlpha = mix;
        ctx.globalCompositeOperation = 'lighter';

        // brainwave rings rippling out of the brain
        for (let k = 0; k < 3; k++) {
            const p = ((T / 1800) + k / 3) % 1;
            ctx.strokeStyle = hsl(0, 65, (1 - p) * 0.35 * mix);
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.arc(ccx, ccy, S * (0.2 + p * 1.3), 0, Math.PI * 2);
            ctx.stroke();
        }

        // strands swaying like brainwaves
        ctx.lineWidth = 1;
        for (const st of STRANDS) {
            const sway = Math.sin(T / 900 + st.phase) * 0.18 + Math.sin(T / 370 + st.phase * 2) * 0.05;
            const a = st.ang + sway * 0.4;
            const x0 = X(st.from.x), y0 = Y(st.from.y);
            const x2 = x0 + Math.cos(a) * st.len * S, y2 = y0 + Math.sin(a) * st.len * S;
            const perp = a + Math.PI / 2, off = (st.bend + sway) * st.len * S * 0.5;
            const x1 = (x0 + x2) / 2 + Math.cos(perp) * off, y1 = (y0 + y2) / 2 + Math.sin(perp) * off;
            const grad = ctx.createLinearGradient(x0, y0, x2, y2);
            const hue = REGIONS[st.from.region].hue;
            grad.addColorStop(0, hsl(hue, 70, 0.55));
            grad.addColorStop(1, hsl(hue, 70, 0));
            ctx.strokeStyle = grad;
            ctx.beginPath();
            ctx.moveTo(x0, y0);
            ctx.quadraticCurveTo(x1, y1, x2, y2);
            ctx.stroke();
            const tip = 0.5 + 0.5 * Math.sin(T / 500 + st.phase * 3);
            ctx.fillStyle = hsl(hue, 85, 0.25 + tip * 0.5);
            ctx.beginPath();
            ctx.arc(x2, y2, 1 + tip * 1.6, 0, Math.PI * 2);
            ctx.fill();
        }

        // soft glow behind the brain
        const glow = ctx.createRadialGradient(ccx, ccy, 0, ccx, ccy, S * 0.8);
        glow.addColorStop(0, hsl(10, 80, 0.28));
        glow.addColorStop(1, hsl(0, 60, 0));
        ctx.fillStyle = glow;
        ctx.fillRect(ccx - S, ccy - S, S * 2, S * 2);

        // how strongly each node fires: a wave front sweeping out from the centre, plus its own rhythm
        const fire = NODES.map((n) => {
            const d = Math.hypot(n.x - CENTRE[0], n.y - CENTRE[1]);
            const wave = Math.max(0, Math.sin(T / 260 - d * 9)) ** 6;
            const own = 0.5 + 0.5 * Math.sin(T / 330 + n.phase);
            return Math.min(1, 0.2 + wave * 0.8 + own * 0.25);
        });

        // connections
        ctx.lineWidth = 1;
        for (const [i, j] of EDGES) {
            const a = NODES[i], b = NODES[j];
            ctx.strokeStyle = hsl(REGIONS[a.region].hue, 70, 0.2 + (fire[i] + fire[j]) * 0.3);
            ctx.beginPath();
            ctx.moveTo(X(a.x), Y(a.y));
            ctx.lineTo(X(b.x), Y(b.y));
            ctx.stroke();
        }

        // signals travelling along connections
        if (T - lastSpawn > 40 && EDGES.length) {
            lastSpawn = T;
            for (let k = 0; k < 3; k++) pulses.push({ e: EDGES[Math.floor(Math.random() * EDGES.length)], at: T });
        }
        for (let k = pulses.length - 1; k >= 0; k--) {
            const p = pulses[k], f = (T - p.at) / 500;
            if (f > 1) { pulses.splice(k, 1); continue; }
            const a = NODES[p.e[0]], b = NODES[p.e[1]];
            ctx.fillStyle = hsl(REGIONS[a.region].hue, 90, 1 - f);
            ctx.beginPath();
            ctx.arc(X(a.x + (b.x - a.x) * f), Y(a.y + (b.y - a.y) * f), 1.6, 0, Math.PI * 2);
            ctx.fill();
        }

        // neurons
        NODES.forEach((n, i) => {
            const hue = REGIONS[n.region].hue, f = fire[i];
            const r = n.size * (1.2 + f * 1.4);
            const g = ctx.createRadialGradient(X(n.x), Y(n.y), 0, X(n.x), Y(n.y), r * 3);
            g.addColorStop(0, hsl(hue, 80, f * 0.35));
            g.addColorStop(1, hsl(hue, 70, 0));
            ctx.fillStyle = g;
            ctx.fillRect(X(n.x) - r * 3, Y(n.y) - r * 3, r * 6, r * 6);
            ctx.fillStyle = hsl(hue, 90, 0.45 + f * 0.55);
            ctx.fillRect(X(n.x) - r / 2, Y(n.y) - r / 2, r, r);
        });
        ctx.restore();

        // region labels, fading in after the brain
        ctx.save();
        ctx.globalAlpha = Math.max(0, mix * 1.6 - 0.6);
        ctx.font = `${Math.min(11, Math.max(8, S * 0.046))}px 'Share Tech Mono', monospace`;
        ctx.textBaseline = 'middle';
        REGIONS.forEach((r, ri) => {
            const nodes = NODES.map((n, i) => [n, fire[i]]).filter(([n]) => n.region === ri);
            if (!nodes.length) return;
            const level = nodes.reduce((sum, [, f]) => sum + f, 0) / nodes.length;
            const text = `${r.name} ${level.toFixed(2)}`;
            const tw = ctx.measureText(text).width, th = Math.min(16, S * 0.07);
            const lx = X(r.at[0]) - tw / 2, ly = Y(r.at[1] + 0.11);
            ctx.fillStyle = 'rgba(0, 0, 0, 0.45)';
            ctx.fillRect(lx - 4, ly - th / 2, tw + 8, th);
            ctx.strokeStyle = hsl(r.hue, 70, 0.8);
            ctx.lineWidth = 1;
            ctx.strokeRect(lx - 4, ly - th / 2, tw + 8, th);
            ctx.fillStyle = hsl(r.hue, 85, 1);
            ctx.fillText(text, lx, ly + 0.5);
        });
        ctx.restore();
    }

    return { draw, resetColors: () => { base = null; } };
})();
