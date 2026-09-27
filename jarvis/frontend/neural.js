// HUD wolf: a wolf head made of dots, half solid and half wireframe, with glowing eyes.
// It sits in the centre of the HUD; while Alfred is thinking, streams of dots flow out of it and back. In memory mode its six parts are
// the memory folders (memory.js), each labelled with the folder's name.
window.HudWolf = (() => {
    // seeded random so the wolf looks the same every time
    let seed = 11;
    const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);

    const poly = (pts) => { const p = new Path2D(); pts.forEach(([a, b], i) => (i ? p.lineTo(a, b) : p.moveTo(a, b))); p.closePath(); return p; };
    const seg = (ax, ay, bx, by, w) => {
        const l = Math.hypot(bx - ax, by - ay), nx = -(by - ay) / l * w, ny = (bx - ax) / l * w;
        return poly([[ax + nx, ay + ny], [bx + nx, by + ny], [bx - nx, by - ny], [ax - nx, ay - ny]]);
    };
    const mirror = (half) => [...half, ...half.slice(0, -1).reverse().map(([a, b]) => [-a, b])];
    const along = (pts, n, spread) => Array.from({ length: n }, () => {   // dots scattered along a line
        const k = rand() * (pts.length - 1), i = Math.floor(k), f = k - i, [ax, ay] = pts[i], [bx, by] = pts[Math.min(i + 1, pts.length - 1)];
        return [ax + (bx - ax) * f + (rand() - 0.5) * spread, ay + (by - ay) * f + (rand() - 0.5) * spread];
    });

    // Front-on wolf head in unit coordinates (y points down), right half drawn as wireframe.
    const FACE = mirror([[0, -0.28], [0.14, -0.32], [0.3, -0.68], [0.42, -0.3], [0.5, -0.18], [0.64, 0.0], [0.52, 0.04], [0.6, 0.16],
        [0.46, 0.2], [0.5, 0.3], [0.32, 0.32], [0.16, 0.46], [0.1, 0.62], [0, 0.66]]);
    const EYES = [[[-0.32, -0.1], [-0.1, -0.02], [-0.26, 0.01]], [[0.32, -0.1], [0.1, -0.02], [0.26, 0.01]]];
    const FACETS = [[0, -0.28, 0.1, -0.02], [0.3, -0.68, 0.32, -0.1], [0.5, -0.18, 0.32, -0.1], [0.64, 0, 0.26, 0.01],
        [0.26, 0.01, 0.16, 0.46], [0.46, 0.2, 0.16, 0.46], [0.1, -0.02, 0, 0.5], [0.16, 0.46, 0, 0.66]];
    const facePath = poly(FACE);
    const holes = [...EYES.map(poly), poly([[-0.06, 0.5], [0.06, 0.5], [0, 0.6]]), poly([[-0.18, -0.32], [-0.28, -0.58], [-0.34, -0.33]]),
        seg(-0.09, 0.03, -0.05, 0.46, 0.015), poly([[0, -1], [1, -1], [1, 1], [0, 1]])];
    const probe = document.createElement('canvas').getContext('2d');

    // The six parts of the head, in folder order.
    const PARTS = [
        { name: 'forehead', label: [0, -0.2] },
        { name: 'left ear', label: [-0.3, -0.46] },
        { name: 'right ear', label: [0.3, -0.46] },
        { name: 'left cheek', label: [-0.4, 0.14] },
        { name: 'right cheek', label: [0.4, 0.14] },
        { name: 'muzzle', label: [0, 0.4] },
    ];
    function partAt(x, y) {
        if (y < -0.3) return x < 0 ? 1 : 2;
        if (y < -0.06) return 0;
        if (Math.abs(x) <= 0.13 || y >= 0.34) return 5;
        return x < 0 ? 3 : 4;
    }

    const DOTS = [];
    const add = (x, y, shade, eye = false) => DOTS.push({ x, y, shade, eye, part: partAt(x, y), r: rand(),
        a: Math.atan2(y, x) + (rand() - 0.5) * 0.6 });
    while (DOTS.length < 1500) {                                          // solid left half
        const x = rand() * 1.4 - 0.7, y = rand() * 1.4 - 0.7;
        if (probe.isPointInPath(facePath, x, y) && !holes.some((h) => probe.isPointInPath(h, x, y))) add(x, y, 0);
    }
    along([...FACE.filter(([x]) => x >= 0), [0, 0.66]], 420, 0.01).forEach(([x, y]) => add(x, y, 8));   // wireframe outline
    FACETS.forEach(([a, b, c, d]) => along([[a, b], [c, d]], 34, 0.007).forEach(([x, y]) => add(x, y, -6)));
    EYES.forEach((eye) => {                                              // glowing eyes
        const path = poly(eye);
        for (let n = 0; n < 130;) {
            const x = rand() * 0.7 - 0.35, y = rand() * 0.14 - 0.11;
            if (probe.isPointInPath(path, x, y)) { add(x, y, 36, true); n++; }
        }
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
    let view = null;   // where the wolf was last drawn, for clicks

    // stream: 0..1 how much the dots flow out (thinking); labels: folder names to show (memory mode), or null
    function draw(ctx, w, h, t, mix, themeColor, slow, { stream = 1, labels = null, hover = -1 } = {}) {
        if (!base) base = hexToHsl(themeColor);
        const hsl = (l, a) => `hsla(${base[0]}, ${base[1]}%, ${Math.min(100, l)}%, ${a})`;
        const T = t * (slow ? 0.25 : 1);
        const S = Math.min(w, h) * 0.42 * (0.85 + 0.15 * mix);
        const ox = w / 2, oy = h / 2;
        view = { ox, oy, S };

        ctx.save();
        ctx.globalAlpha = mix;
        ctx.globalCompositeOperation = 'lighter';

        // eye glow
        EYES.forEach((eye) => {
            const cx = ox + (eye[0][0] + eye[1][0]) / 2 * S, cy = oy - 0.04 * S, pulse = 0.8 + 0.2 * Math.sin(T / 300);
            const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, S * 0.22);
            g.addColorStop(0, hsl(90, 0.35 * pulse));
            g.addColorStop(1, hsl(90, 0));
            ctx.fillStyle = g;
            ctx.fillRect(cx - S * 0.22, cy - S * 0.22, S * 0.44, S * 0.44);
        });

        DOTS.forEach((d, i) => {
            const lit = labels && d.part === hover ? 22 : 0;
            const x0 = ox + d.x * S, y0 = oy + d.y * S;
            if (d.eye) {
                const size = 1.8 + Math.sin(T / 200 + i) * 0.4;
                ctx.fillStyle = hsl(95, 0.9);
                ctx.fillRect(x0 - size / 2, y0 - size / 2, size, size);
                return;
            }
            if (i % 12 || stream < 0.02) {
                const size = 1.7 + lit * 0.02;
                ctx.fillStyle = hsl(62 + d.shade + lit, 0.7 + 0.3 * Math.sin(T / 400 + i));
                ctx.fillRect(x0 - size / 2, y0 - size / 2, size, size);
                return;
            }
            // a stream: flows out along a curve and back
            const p = (T / 2600 + d.r) % 1, f = Math.sin(p * Math.PI) ** 2 * stream, len = 0.2 + d.r * 0.35;
            const ang = d.a + Math.sin(p * Math.PI * 2 + i) * 0.5 * f;
            for (let k = 0; k < 4; k++) {
                const ff = Math.max(0, f - k * 0.05), size = 1.8 - k * 0.3;
                ctx.fillStyle = hsl(70 + lit, (1 - k / 4) * (0.25 + f * 0.5) + (k ? 0 : 0.3));
                ctx.fillRect(x0 + Math.cos(ang - k * 0.05) * len * ff * S - size / 2, y0 + Math.sin(ang - k * 0.05) * len * ff * S - size / 2, size, size);
            }
        });
        ctx.restore();

        if (!labels) return;
        ctx.save();
        ctx.globalAlpha = Math.max(0, mix * 1.6 - 0.6);
        ctx.font = `${Math.min(12, Math.max(9, S * 0.05))}px 'Share Tech Mono', monospace`;
        ctx.textBaseline = 'middle';
        PARTS.forEach((part, i) => {
            if (!labels[i]) return;
            const text = labels[i], tw = ctx.measureText(text).width, th = 18;
            const lx = ox + part.label[0] * S - tw / 2, ly = oy + part.label[1] * S;
            ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
            ctx.fillRect(lx - 5, ly - th / 2, tw + 10, th);
            ctx.strokeStyle = hsl(i === hover ? 95 : 70, i === hover ? 1 : 0.6);
            ctx.lineWidth = 1;
            ctx.strokeRect(lx - 5, ly - th / 2, tw + 10, th);
            ctx.fillStyle = hsl(95, 1);
            ctx.fillText(text, lx, ly + 0.5);
        });
        ctx.restore();
    }

    // Which part of the head (folder number) is under a point on the page, or -1.
    function partAtPoint(canvas, clientX, clientY) {
        if (!view) return -1;
        const rect = canvas.getBoundingClientRect();
        const x = (clientX - rect.left - view.ox) / view.S, y = (clientY - rect.top - view.oy) / view.S;
        const onLabel = PARTS.some((p) => Math.hypot(x - p.label[0], y - p.label[1]) < 0.14);
        return probe.isPointInPath(facePath, x, y) || onLabel ? partAt(x, y) : -1;
    }

    return { draw, partAtPoint, parts: PARTS, resetColors: () => { base = null; } };
})();
