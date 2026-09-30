// Station LSX, part 1 (station.js loads it): shared maths, textures, materials, the LSX freighter and the crew.
// LSX.kit(THREE, renderer) builds them once; the desert, forest and space parts take what they need from it.
window.LSX = window.LSX || {};
LSX.kit = (THREE, renderer) => {
    // ---- small maths ---------------------------------------------------------------------------------------------
    const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
    const lerp = (a, b, t) => a + (b - a) * t;
    const ease = (x) => (x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2);
    const rnd = (s) => { const x = Math.sin(s * 12.9898 + 78.233) * 43758.5453; return x - Math.floor(x); };
    const hash = (x, y, z) => {
        let h = Math.imul(x, 374761393) ^ Math.imul(y, 668265263) ^ Math.imul(z, 1274126177);
        h = Math.imul(h ^ (h >>> 13), 1274126177); return ((h ^ (h >>> 16)) >>> 0) / 4294967295;
    };
    const sm = (t) => t * t * (3 - 2 * t);
    function noise3(x, y, z) {
        const xi = Math.floor(x), yi = Math.floor(y), zi = Math.floor(z), xf = sm(x - xi), yf = sm(y - yi), zf = sm(z - zi);
        const c = (a, b, d) => hash(xi + a, yi + b, zi + d);
        const x00 = lerp(c(0, 0, 0), c(1, 0, 0), xf), x10 = lerp(c(0, 1, 0), c(1, 1, 0), xf);
        const x01 = lerp(c(0, 0, 1), c(1, 0, 1), xf), x11 = lerp(c(0, 1, 1), c(1, 1, 1), xf);
        return lerp(lerp(x00, x10, yf), lerp(x01, x11, yf), zf);
    }
    const fbm = (x, y, z, o = 5) => { let s = 0, a = 0.5, f = 1; for (let i = 0; i < o; i++) { s += a * noise3(x * f, y * f, z * f); f *= 2.03; a *= 0.5; } return s; };
    const V = (x, y, z) => new THREE.Vector3(x, y, z);
    const canvas = (w, h = w) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; };
    const tex = (c, rx = 1, ry = 1, srgb = true) => {
        const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(rx, ry);
        if (srgb) t.encoding = THREE.sRGBEncoding; t.anisotropy = 4; return t;
    };
    const add = (parent, geo, m, x = 0, y = 0, z = 0) => { const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); o.castShadow = o.receiveShadow = true; parent.add(o); return o; };
    const extrude = (pts, depth, bevel = 0.5) => {
        const s = new THREE.Shape(); pts.forEach(([x, y], i) => (i ? s.lineTo(x, y) : s.moveTo(x, y)));
        const g = new THREE.ExtrudeGeometry(s, { depth, bevelEnabled: true, bevelThickness: bevel, bevelSize: bevel, bevelSegments: 2 }); g.translate(0, 0, -depth / 2); return g;
    };
    const rbox = (w, h, d, r = 0.35) => {
        const s2 = new THREE.Shape(); s2.moveTo(-w / 2 + r, -h / 2 + r); s2.lineTo(w / 2 - r, -h / 2 + r); s2.lineTo(w / 2 - r, h / 2 - r); s2.lineTo(-w / 2 + r, h / 2 - r); s2.closePath();
        const g = new THREE.ExtrudeGeometry(s2, { depth: d - 2 * r, bevelEnabled: true, bevelThickness: r, bevelSize: r, bevelSegments: 3 }); g.translate(0, 0, -(d - 2 * r) / 2); return g;
    };

    // ---- textures ------------------------------------------------------------------------------------------------
    function panelCanvas(base, seed, size = 1024) {
        const c = canvas(size), g = c.getContext('2d');
        g.fillStyle = base; g.fillRect(0, 0, size, size);
        for (let i = 0; i < 5000; i++) {
            const v = rnd(seed + i) < 0.5 ? 0 : 255; g.fillStyle = `rgba(${v},${v},${v},${0.01 + rnd(seed + i + 1) * 0.02})`;
            g.fillRect(rnd(seed + i + 2) * size, rnd(seed + i + 3) * size, 1 + rnd(seed + i + 4) * 5, 1 + rnd(seed + i + 5) * 5);
        }
        const cell = size / 16;
        for (let i = 0; i < 70; i++) {
            const x = Math.floor(rnd(seed + i * 7) * 16) * cell, y = Math.floor(rnd(seed + i * 7 + 1) * 16) * cell;
            const w = (1 + Math.floor(rnd(seed + i * 7 + 2) * 5)) * cell, h = (1 + Math.floor(rnd(seed + i * 7 + 3) * 4)) * cell;
            const tone = rnd(seed + i * 3) < 0.5 ? 0 : 255; g.fillStyle = `rgba(${tone},${tone},${tone},${0.02 + rnd(seed + i * 7 + 4) * 0.04})`; g.fillRect(x, y, w, h);
            g.strokeStyle = 'rgba(0,0,0,.55)'; g.lineWidth = 2.5; g.strokeRect(x + 1, y + 1, w - 2, h - 2);
            g.strokeStyle = 'rgba(255,255,255,.12)'; g.lineWidth = 1; g.strokeRect(x + 3, y + 3, w - 6, h - 6);
            g.fillStyle = 'rgba(0,0,0,.45)'; for (let k = 6; k < w - 4; k += 14) { g.fillRect(x + k, y + 6, 2, 2); g.fillRect(x + k, y + h - 8, 2, 2); }
        }
        for (let i = 0; i < 40; i++) {
            const x = rnd(seed + i + 500) * size, gr = g.createLinearGradient(0, 0, 0, size);
            gr.addColorStop(0, 'rgba(40,30,20,0)'); gr.addColorStop(rnd(i + 3), 'rgba(40,30,20,.16)'); gr.addColorStop(1, 'rgba(40,30,20,0)');
            g.fillStyle = gr; g.fillRect(x, 0, 3 + rnd(seed + i) * 18, size);
        }
        g.strokeStyle = 'rgba(255,255,255,.08)'; g.lineWidth = 1;
        for (let i = 0; i < 120; i++) { const x = rnd(seed + i + 900) * size, y = rnd(seed + i + 901) * size; g.beginPath(); g.moveTo(x, y); g.lineTo(x + (rnd(i) - 0.5) * 40, y + (rnd(i + 1) - 0.5) * 12); g.stroke(); }
        return c;
    }
    function hazardCanvas() {
        const c = canvas(256, 32), g = c.getContext('2d'); g.fillStyle = '#d9a82a'; g.fillRect(0, 0, 256, 32);
        g.fillStyle = '#141414'; for (let x = -32; x < 288; x += 32) { g.beginPath(); g.moveTo(x, 32); g.lineTo(x + 16, 0); g.lineTo(x + 32, 0); g.lineTo(x + 16, 32); g.fill(); }
        for (let i = 0; i < 400; i++) { g.fillStyle = `rgba(0,0,0,${rnd(i) * 0.2})`; g.fillRect(rnd(i + 1) * 256, rnd(i + 2) * 32, 3, 2); } return c;
    }
    function decal(text, w = 512, h = 128, col = '#e9e6de') {
        const c = canvas(w, h), g = c.getContext('2d');
        g.fillStyle = col; g.font = `700 ${h * 0.62}px "Share Tech Mono", monospace`; g.textBaseline = 'middle'; g.fillText(text, 6, h / 2); return c;
    }
    // the LSX emblem: orange ring, bold letters, a small star; on the ships, the signs and every spacesuit
    const logoCanvas = (size = 256, dark = false) => {
        const c = canvas(size), g = c.getContext('2d'), m = size / 2;
        g.fillStyle = dark ? '#16181c' : 'rgba(0,0,0,0)'; g.beginPath(); g.arc(m, m, m * 0.96, 0, 7); g.fill();
        g.strokeStyle = '#e8813a'; g.lineWidth = size * 0.07; g.beginPath(); g.arc(m, m, m * 0.84, 0, 7); g.stroke();
        g.strokeStyle = '#e9e6de'; g.lineWidth = size * 0.02; g.beginPath(); g.arc(m, m, m * 0.7, 0, 7); g.stroke();
        g.fillStyle = '#e9e6de'; g.font = `700 ${size * 0.3}px "Share Tech Mono", sans-serif`; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('LSX', m, m + size * 0.02);
        g.fillStyle = '#e8813a'; g.beginPath(); for (let i = 0; i < 10; i++) { const a = -Math.PI / 2 + i * Math.PI / 5, r = i % 2 ? size * 0.025 : size * 0.06; g.lineTo(m + Math.cos(a) * r, m - size * 0.28 + Math.sin(a) * r); } g.fill();
        return c;
    };
    const logoMat = new THREE.MeshStandardMaterial({ map: tex(logoCanvas(256)), transparent: true, roughness: 0.5, metalness: 0.1 });
    const patchMat = new THREE.MeshStandardMaterial({ map: tex(logoCanvas(128, true)), transparent: true, roughness: 0.7 });
    const hullTexC = panelCanvas('#5b5f65', 11), hullTexB = panelCanvas('#4a4d52', 29), podTex = panelCanvas('#6f5038', 47);
    const mat = {
        hullE: new THREE.MeshStandardMaterial({ map: tex(hullTexC, 0.07, 0.07), bumpMap: tex(hullTexC, 0.07, 0.07, false), roughnessMap: tex(hullTexC, 0.07, 0.07, false), bumpScale: 0.05, metalness: 0.72, roughness: 0.95 }),
        hullB: new THREE.MeshStandardMaterial({ map: tex(hullTexB, 1, 1), bumpMap: tex(hullTexB, 1, 1, false), bumpScale: 0.04, metalness: 0.7, roughness: 0.5 }),
        pod: new THREE.MeshStandardMaterial({ map: tex(podTex, 1, 1), bumpMap: tex(podTex, 1, 1, false), bumpScale: 0.04, metalness: 0.55, roughness: 0.6 }),
        hullBE: new THREE.MeshStandardMaterial({ map: tex(hullTexB, 0.11, 0.11), bumpMap: tex(hullTexB, 0.11, 0.11, false), roughnessMap: tex(hullTexB, 0.11, 0.11, false), bumpScale: 0.05, metalness: 0.72, roughness: 0.95 }),
        podE: new THREE.MeshStandardMaterial({ map: tex(podTex, 0.19, 0.19), bumpMap: tex(podTex, 0.19, 0.19, false), roughnessMap: tex(podTex, 0.19, 0.19, false), bumpScale: 0.05, metalness: 0.55, roughness: 1 }),
        dark: new THREE.MeshStandardMaterial({ color: 0x1d1f23, metalness: 0.6, roughness: 0.55 }),
        steel: new THREE.MeshStandardMaterial({ color: 0x8a8f96, metalness: 0.85, roughness: 0.3 }),
        orange: new THREE.MeshStandardMaterial({ color: 0xc8612a, metalness: 0.3, roughness: 0.55 }),
        hazard: new THREE.MeshStandardMaterial({ map: tex(hazardCanvas(), 4, 1), metalness: 0.2, roughness: 0.7 }),
        glass: new THREE.MeshPhysicalMaterial({ color: 0x0b1824, metalness: 0.9, roughness: 0.06, clearcoat: 1, clearcoatRoughness: 0.05 }),
        bell: new THREE.MeshStandardMaterial({ color: 0x3b3431, metalness: 0.85, roughness: 0.35, side: THREE.DoubleSide }),
    };
    const glow = (c) => new THREE.MeshBasicMaterial({ color: c });
    const navMat = glow;
    const winMat = glow(0xffd29a), redLamp = glow(0xff3b30);
    const heatMat = new THREE.MeshBasicMaterial({ color: 0x331000 });

    // ---- the ship (metres; nose along +x, belly at y=0) ------------------------------------------------------------
    const ship = new THREE.Group();
    add(ship, extrude([[-13, 1], [9, 1], [10.5, 2.5], [10.5, 7.5], [9, 8.5], [-13, 8.5]], 8), mat.hullE);
    add(ship, extrude([[9, 1.4], [16, 1.4], [21, 3.4], [22.2, 5], [19, 7.1], [9, 8]], 6, 0.45), mat.hullE);
    const canopy = add(ship, new THREE.BoxGeometry(3.9, 0.25, 5.2), mat.glass, 20.4, 6.15, 0); canopy.rotation.z = -0.62;
    add(ship, new THREE.BoxGeometry(2.2, 0.2, 5.4), mat.glass, 17.6, 7.45, 0).rotation.z = -0.1;
    add(ship, rbox(9.5, 9, 11, 0.6), mat.hullBE, -17.6, 4.8, 0);
    add(ship, rbox(16, 2.2, 6, 0.4), mat.hullBE, -2, 9.6, 0);
    add(ship, rbox(20, 1.1, 7, 0.3), mat.dark, -2, 0.55, 0);
    add(ship, new THREE.BoxGeometry(11, 0.5, 11.2), mat.hazard, -17.6, 9.1, 0);
    for (const z of [-1, 1]) {
        for (const [i, x] of [-9, -3, 3].entries()) add(ship, rbox(5.4, 4.6, 1.3, 0.25), i === 1 ? mat.podE : mat.hullBE, x, 3.9, z * 4.95);
        add(ship, new THREE.BoxGeometry(5.4, 0.35, 1.35), mat.hazard, -9, 1.75, z * 4.97);
        const pipe = add(ship, new THREE.CylinderGeometry(0.18, 0.18, 21, 8), mat.steel, -2, 7.2, z * 4.35); pipe.rotation.z = Math.PI / 2;
        add(ship, new THREE.BoxGeometry(6, 0.25, 3.2), mat.hullB, -17, 4.2, z * 7.2);
        for (let k = 0; k < 6; k++) add(ship, new THREE.BoxGeometry(0.15, 3.4, 3), mat.dark, -19.5 + k * 1, 4.2, z * 7.2);
        const fin = add(ship, extrude([[-21, 9], [-15, 9], [-17.5, 14], [-20, 14]], 0.35, 0.1), mat.hullE, 0, 0, z * 3.8); fin.rotation.x = z * 0.25;
        add(ship, new THREE.BoxGeometry(12, 0.25, 0.1), mat.orange, 14.5, 2.4, z * 3.52);
    }
    for (let i = 0; i < 70; i++) {
        const w = 0.3 + rnd(i) * 1.6, h = 0.2 + rnd(i + 1) * 0.8, d = 0.3 + rnd(i + 2) * 1.4;
        add(ship, new THREE.BoxGeometry(w, h, d), rnd(i + 3) < 0.7 ? mat.dark : mat.steel, -12 + rnd(i + 4) * 19, 8.5 + h / 2 + (rnd(i + 5) < 0.3 ? 2.2 : 0), (rnd(i + 6) - 0.5) * 7);
    }
    for (let i = 0; i < 14; i++) add(ship, new THREE.BoxGeometry(0.2, 0.9, 5), mat.dark, -9 + i * 1, 11.1, 0);
    add(ship, new THREE.CylinderGeometry(0.08, 0.08, 4, 6), mat.steel, 2, 12.6, 1.5);
    add(ship, new THREE.CylinderGeometry(0.06, 0.06, 2.6, 6), mat.steel, -5, 12, -2);
    const dish0 = add(ship, new THREE.SphereGeometry(1, 16, 8, 0, Math.PI * 2, 0, 1.1), mat.steel, -7, 11.5, 1.8); dish0.rotation.x = -0.6;
    const idTag = new THREE.Mesh(new THREE.PlaneGeometry(4.4, 1.1), new THREE.MeshStandardMaterial({ map: tex(decal('LSX-01')), transparent: true, metalness: 0.2, roughness: 0.6 }));
    idTag.position.set(13.5, 5.2, 3.51); ship.add(idTag);
    const idTag2 = new THREE.Mesh(new THREE.PlaneGeometry(6, 1.2), new THREE.MeshStandardMaterial({ map: tex(decal('CARGO 03', 512, 128, '#1b1b1b')), transparent: true }));
    idTag2.position.set(-3, 5.4, 5.62); ship.add(idTag2);
    // engine bells, nozzle glow and flames
    const bellGeo = new THREE.LatheGeometry([[0.9, 0], [1.0, 0.3], [1.3, 1.1], [1.7, 2.1], [1.85, 2.5]].map(([r, y]) => new THREE.Vector2(r, y)), 28);
    const flameMat = (c1, c2) => new THREE.ShaderMaterial({
        transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
        uniforms: { uT: { value: 0 }, uK: { value: 0 }, c1: { value: new THREE.Color(c1) }, c2: { value: new THREE.Color(c2) } },
        vertexShader: 'varying vec2 vUv; varying vec3 vN; varying vec3 vV; void main(){ vUv=uv; vN=normalize(normalMatrix*normal); vec4 mv=modelViewMatrix*vec4(position,1.); vV=normalize(-mv.xyz); gl_Position=projectionMatrix*mv; }',
        fragmentShader: 'uniform float uT; uniform float uK; uniform vec3 c1; uniform vec3 c2; varying vec2 vUv; varying vec3 vN; varying vec3 vV; void main(){ float a=vUv.y; float edge=pow(abs(dot(vN,vV)),1.5); float fl=0.85+0.15*sin(uT*60.+a*20.); vec3 col=mix(c1,c2,smoothstep(0.,.55,a)); float al=pow(1.-a,1.6)*edge*fl*uK; gl_FragColor=vec4(col*al*1.6,al); }',
    });
    const flames = [];
    function engine(x, y, z, dir, len, r) {
        const bell = add(ship, bellGeo, mat.bell, x, y, z); bell.scale.setScalar(r);
        const gl = new THREE.Mesh(new THREE.CircleGeometry(0.95 * r, 20), new THREE.MeshBasicMaterial({ color: 0xff8a3a, transparent: true, opacity: 0 }));
        const pivot = new THREE.Group(); pivot.position.set(x, y, z);
        if (dir === 'back') { bell.rotation.z = Math.PI / 2; gl.rotation.y = -Math.PI / 2; gl.position.set(x - 0.4 * r, y, z); pivot.rotation.z = Math.PI / 2; pivot.position.x -= 2.3 * r; }
        else { bell.rotation.x = Math.PI; gl.rotation.x = Math.PI / 2; gl.position.set(x, y - 0.4 * r, z); pivot.rotation.x = Math.PI; pivot.position.y -= 2.3 * r; }
        ship.add(gl);
        for (const [k, c1, c2, rr] of [[1, '#fff6e6', '#ff7a2a', 1.05], [0.55, '#ffffff', '#ffc27a', 0.6]]) {
            const cone = new THREE.Mesh(new THREE.ConeGeometry(1.7 * r * rr, len * k, 24, 1, true), flameMat(c1, c2));
            cone.position.y = len * k / 2; pivot.add(cone);
        }
        ship.add(pivot); flames.push({ dir, pivot, glow: gl });
    }
    for (const y of [3, 6.6]) for (const z of [-2.6, 2.6]) engine(-22.4, y, z, 'back', 16, 1);
    for (const x of [-8, 4]) for (const z of [-2, 2]) engine(x, 0, z, 'down', 9, 0.55);
    const rearLight = new THREE.PointLight(0xff8a3a, 0, 60, 2); rearLight.position.set(-30, 5, 0); ship.add(rearLight);
    const bellyLight = new THREE.PointLight(0xffa050, 0, 40, 2); bellyLight.position.set(-2, -3, 0); ship.add(bellyLight);
    function thrust(T, rear, belly) {
        for (const f of flames) {
            const k = f.dir === 'back' ? rear : belly;
            f.pivot.visible = k > 0.01; f.pivot.scale.set(1, 0.3 + 0.7 * k * (0.92 + 0.08 * Math.sin(T * 47 + f.pivot.id)), 1);
            f.pivot.traverse((o) => { if (o.material && o.material.uniforms) { o.material.uniforms.uK.value = k; o.material.uniforms.uT.value = T; } });
            f.glow.material.opacity = clamp(k * 1.5);
        }
        rearLight.intensity = rear * 3.5; bellyLight.intensity = belly * 4;
        const heat = Math.max(rear, belly * 0.5); heatMat.color.setRGB(0.2 + heat * 0.8, 0.05 + heat * 0.35, 0.01 + heat * 0.08);
    }
    // legs and ramp
    const legs = [];
    for (const [x, z] of [[-11, 4], [-11, -4], [6, 3.4], [6, -3.4]]) {
        const pivot = new THREE.Group(); pivot.position.set(x, 0.6, z); ship.add(pivot);
        add(pivot, new THREE.CylinderGeometry(0.35, 0.28, 5, 10), mat.steel, 0, -2.5, 0);
        add(pivot, new THREE.CylinderGeometry(0.5, 0.5, 2, 10), mat.dark, 0, -1, 0);
        add(pivot, new THREE.CylinderGeometry(1.1, 1.25, 0.35, 16), mat.dark, 0, -5.1, 0);
        legs.push(pivot);
    }
    const ramp = new THREE.Group(); ramp.position.set(-12.2, 0.5, 0); ship.add(ramp);
    add(ramp, new THREE.BoxGeometry(8, 0.3, 3.6), mat.hullB, -4, -0.15, 0);
    add(ramp, new THREE.BoxGeometry(8, 0.32, 0.25), mat.hazard, -4, -0.12, 1.7); add(ramp, new THREE.BoxGeometry(8, 0.32, 0.25), mat.hazard, -4, -0.12, -1.7);
    const cabin = new THREE.PointLight(0xffe0b0, 0, 14, 2); cabin.position.set(-12, -1, 0); ship.add(cabin);
    // the lit cargo hold you see up through the open ramp: light strips, racked crates and tie-down rails
    const holdC = (() => {
        const c = canvas(512, 224), g = c.getContext('2d'), gr = g.createLinearGradient(0, 0, 512, 0);
        gr.addColorStop(0, '#2a2622'); gr.addColorStop(0.5, '#4a4238'); gr.addColorStop(1, '#2a2622'); g.fillStyle = gr; g.fillRect(0, 0, 512, 224);
        for (let x = 16; x < 512; x += 64) { g.fillStyle = '#fff1d0'; g.fillRect(x, 104, 34, 16); g.fillStyle = 'rgba(255,230,180,.18)'; g.fillRect(x - 12, 86, 58, 52); }
        g.strokeStyle = 'rgba(0,0,0,.5)'; g.lineWidth = 3; for (let x = 0; x < 512; x += 32) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, 224); g.stroke(); }
        for (let i = 0; i < 14; i++) {
            const x = 8 + (i % 7) * 72, y = i < 7 ? 12 : 164; g.fillStyle = ['#8a6a3f', '#6b6f74', '#9a7a4a'][i % 3]; g.fillRect(x, y, 54, 46); g.strokeStyle = '#2a1c10'; g.lineWidth = 2; g.strokeRect(x + 3, y + 3, 48, 40);
            g.fillStyle = '#e8813a'; g.fillRect(x, y + 20, 54, 4);
        }
        g.fillStyle = '#d9a82a'; for (let x = 0; x < 512; x += 24) { g.fillRect(x, 70, 12, 4); g.fillRect(x + 12, 150, 12, 4); } return c;
    })();
    const hold = new THREE.Mesh(new THREE.PlaneGeometry(7.8, 3.3), new THREE.MeshBasicMaterial({ map: tex(holdC) })); hold.rotation.x = Math.PI / 2; hold.position.set(-12.2, 0.46, 0); hold.name = 'hold'; ship.add(hold);
    const navR = add(ship, new THREE.SphereGeometry(0.22, 8, 6), navMat(0xff3b30), -18.8, 14, -3.9), navG = add(ship, new THREE.SphereGeometry(0.22, 8, 6), navMat(0x3cff8a), -18.8, 14, 3.9);
    const strobe = add(ship, new THREE.SphereGeometry(0.25, 8, 6), navMat(0xffffff), 2, 14.6, 1.5);
    // extra ship detail: lit windows, handrails, pipes, headlights, heat rings, decals, antennas
    for (const z of [-1, 1]) {
        for (let i = 0; i < 5; i++) add(ship, new THREE.BoxGeometry(0.8, 0.4, 0.06), winMat, 10.6 + i * 1.25, 6.3, z * 3.47);
        for (let i = 0; i < 10; i++) add(ship, new THREE.BoxGeometry(0.55, 0.28, 0.06), winMat, -11 + i * 1.95, 7.95, z * 4.52);
        const rail = add(ship, new THREE.CylinderGeometry(0.06, 0.06, 15, 6), mat.steel, -2, 11.35, z * 3.1); rail.rotation.z = Math.PI / 2;
        for (let i = 0; i < 6; i++) add(ship, new THREE.CylinderGeometry(0.05, 0.05, 0.7, 6), mat.steel, -9 + i * 2.8, 11, z * 3.1);
        for (let k = 0; k < 3; k++) { const pp = add(ship, new THREE.CylinderGeometry(0.13, 0.13, 9, 8), k === 1 ? mat.orange : mat.steel, -17.6, 1.6 + k * 0.34, z * 5.62); pp.rotation.z = Math.PI / 2; }
        for (let i = 0; i < 5; i++) add(ship, new THREE.BoxGeometry(0.12, 0.12, 0.5), mat.dark, -21.5 + i * 2, 1.6, z * 5.5);
        const chev = new THREE.Mesh(new THREE.PlaneGeometry(3.2, 0.6), mat.hazard); chev.position.set(18.3, 2.6, z * 3.48); if (z < 0) chev.rotation.y = Math.PI; ship.add(chev);
        const brand = new THREE.Mesh(new THREE.PlaneGeometry(10, 1.1), new THREE.MeshStandardMaterial({ map: tex(decal('LSX FREIGHT CO.', 1024, 112)), transparent: true, roughness: 0.6 }));
        brand.position.set(-2, 10, z * 3.02); if (z < 0) brand.rotation.y = Math.PI; ship.add(brand);
        const num = new THREE.Mesh(new THREE.PlaneGeometry(3, 2.2), new THREE.MeshStandardMaterial({ map: tex(decal('07', 256, 188, '#d9a82a')), transparent: true }));
        num.position.set(-15.2, 1.9, z * 5.52); num.scale.setScalar(0.6); if (z < 0) num.rotation.y = Math.PI; ship.add(num);
    }
    for (const z of [-1.7, 1.7]) {
        const lens = add(ship, new THREE.CylinderGeometry(0.35, 0.35, 0.2, 14), glow(0xfff4dc), 21.1, 3.2, z); lens.rotation.z = Math.PI / 2;
        const hl = new THREE.SpotLight(0xfff2dc, 1.4, 90, 0.32, 0.6, 1.5); hl.position.set(21.3, 3.2, z); hl.target.position.set(60, -6, z * 3); ship.add(hl, hl.target);
    }
    for (const x of [-4, 12]) add(ship, new THREE.CylinderGeometry(0.4, 0.4, 0.1, 12), glow(0xfff0d0), x, 0.02, 0);
    const padFlood = new THREE.SpotLight(0xfff0d0, 1.2, 30, 0.9, 0.7, 1.5); padFlood.position.set(4, 0, 0); padFlood.target.position.set(4, -10, 0); ship.add(padFlood, padFlood.target);
    flames.filter((f) => f.dir === 'back').forEach((f) => { const ring = add(ship, new THREE.TorusGeometry(1.8, 0.12, 8, 28), heatMat, -24.8, f.glow.position.y, f.glow.position.z); ring.rotation.y = Math.PI / 2; ring.castShadow = false; });
    for (const [x, h, z] of [[4, 3.6, -2.2], [6, 2.4, -2.4], [-10, 2.8, 2.2]]) { add(ship, new THREE.CylinderGeometry(0.05, 0.05, h, 6), mat.steel, x, 10.7 + h / 2, z); add(ship, new THREE.SphereGeometry(0.12, 6, 4), redLamp, x, 10.7 + h, z); }
    for (let i = 0; i < 4; i++) add(ship, new THREE.BoxGeometry(1.4, 0.5, 1.4), mat.dark, -20 + i * 1.8, 9.6, 3.2 - (i % 2) * 6.4);
    // weathering: soot behind the engines, rain-streak grime down the hull, cargo straps and stencils, a spinning radar bar
    const sootC = canvas(256, 128), so = sootC.getContext('2d'), sg2 = so.createLinearGradient(0, 0, 256, 0); sg2.addColorStop(0, 'rgba(10,8,6,.85)'); sg2.addColorStop(1, 'rgba(10,8,6,0)');
    so.fillStyle = sg2; so.fillRect(0, 0, 256, 128); for (let i = 0; i < 300; i++) { so.fillStyle = `rgba(0,0,0,${rnd(i + 950) * 0.25})`; so.fillRect(rnd(i + 951) * 120, rnd(i + 952) * 128, 8 + rnd(i) * 40, 2); }
    const sootMat = new THREE.MeshBasicMaterial({ map: tex(sootC), transparent: true, depthWrite: false, color: 0x888888 });
    const grimeC = canvas(512, 256), gr2 = grimeC.getContext('2d');
    for (let i = 0; i < 90; i++) { const x = rnd(i + 970) * 512, l = 40 + rnd(i + 971) * 180, gd = gr2.createLinearGradient(0, 0, 0, l); gd.addColorStop(0, 'rgba(30,22,14,.35)'); gd.addColorStop(1, 'rgba(30,22,14,0)'); gr2.fillStyle = gd; gr2.fillRect(x, 0, 1 + rnd(i + 972) * 5, l); }
    for (let i = 0; i < 40; i++) { gr2.fillStyle = `rgba(120,90,60,${rnd(i + 990) * 0.18})`; gr2.fillRect(rnd(i + 991) * 512, 200 + rnd(i + 992) * 56, 20 + rnd(i) * 60, 4 + rnd(i + 1) * 10); }
    const grimeMat = new THREE.MeshBasicMaterial({ map: tex(grimeC), transparent: true, depthWrite: false, color: 0xffffff });
    for (const z of [-1, 1]) {
        const soot = new THREE.Mesh(new THREE.PlaneGeometry(5, 8.4), sootMat); soot.position.set(-19.9, 4.8, z * 5.535); if (z < 0) soot.rotation.y = Math.PI; ship.add(soot);
        const grime = new THREE.Mesh(new THREE.PlaneGeometry(22, 7.2), grimeMat); grime.position.set(-1.5, 4.8, z * 4.515); if (z < 0) grime.rotation.y = Math.PI; ship.add(grime);
        const grime2 = new THREE.Mesh(new THREE.PlaneGeometry(9, 8.6), grimeMat); grime2.position.set(-17.6, 4.8, z * 5.545); if (z < 0) grime2.rotation.y = Math.PI; ship.add(grime2);
        for (const [i, x] of [-9, -3, 3].entries()) {
            for (const dx of [-1.6, 1.6]) add(ship, new THREE.BoxGeometry(0.18, 4.7, 0.08), i === 1 ? mat.hazard : mat.dark, x + dx, 3.9, z * 5.62);
            const st = new THREE.Mesh(new THREE.PlaneGeometry(2.4, 0.5), new THREE.MeshStandardMaterial({ map: tex(decal(['LSX-C1', 'HAZMAT', 'LSX-C3'][i], 512, 110, i === 1 ? '#e0b12c' : '#d8d4cc')), transparent: true }));
            st.position.set(x, 5.6, z * 5.625); if (z < 0) st.rotation.y = Math.PI; ship.add(st);
        }
    }
    const radar = new THREE.Group(); radar.name = 'radar'; radar.position.set(-12, 11.6, 0); ship.add(radar);
    add(radar, new THREE.CylinderGeometry(0.3, 0.4, 0.8, 10), mat.dark, 0, 0, 0); add(radar, new THREE.BoxGeometry(0.3, 0.6, 3.2), mat.steel, 0, 0.6, 0);
    for (let k = -3; k <= 3; k++) add(radar, new THREE.BoxGeometry(0.06, 0.5, 0.12), mat.dark, 0.18, 0.6, k * 0.42);
    const bellyStrobe = add(ship, new THREE.SphereGeometry(0.22, 8, 6), new THREE.MeshBasicMaterial({ color: 0xff3b30 }), 0, -0.05, 0); bellyStrobe.name = 'bellyStrobe';
    // more hull detail: emblems, raised strakes, RCS quads, a ladder, hatches, sensor domes, heat vents, leg lights
    for (const z of [-1, 1]) {
        const lg = new THREE.Mesh(new THREE.PlaneGeometry(3.2, 3.2), logoMat); lg.position.set(-17.6, 7.4, z * 5.53); if (z < 0) lg.rotation.y = Math.PI; ship.add(lg);
        const lg2 = new THREE.Mesh(new THREE.PlaneGeometry(2.2, 2.2), logoMat); lg2.position.set(8, 5.2, z * 4.53); if (z < 0) lg2.rotation.y = Math.PI; ship.add(lg2);
        for (const y of [1.25, 8.3]) add(ship, new THREE.BoxGeometry(22, 0.18, 0.12), mat.steel, -1.5, y, z * 4.55);
        for (const [x, y, zz] of [[18.5, 6.4, 3.3], [-20.8, 9.6, 5.3], [4, 1.4, 4.5]]) {
            const q = new THREE.Group(); q.position.set(x, y, z * zz); ship.add(q);
            add(q, new THREE.BoxGeometry(0.7, 0.7, 0.5), mat.dark); for (const [dx, dy] of [[0.45, 0], [-0.45, 0], [0, 0.45]]) { const nz = add(q, new THREE.CylinderGeometry(0.1, 0.16, 0.3, 8), mat.steel, dx, dy, 0); nz.rotation.z = dx ? Math.PI / 2 : 0; }
        }
        for (const [x, w, h] of [[11.5, 1.6, 2.2], [15.6, 1.2, 1.4]]) { add(ship, new THREE.BoxGeometry(w, h, 0.06), mat.dark, x, 3.4, z * 3.5); add(ship, new THREE.BoxGeometry(w * 0.4, 0.1, 0.1), mat.orange, x, 3.4 + h * 0.3, z * 3.55); }
        for (let k = 0; k < 3; k++) add(ship, new THREE.BoxGeometry(2.4, 0.22, 0.14), glow(0x5a1c06), -17.6, 2.6 + k * 0.35, z * 5.56);
    }
    for (const x of [6.4, 7.4]) add(ship, new THREE.BoxGeometry(0.08, 6.6, 0.08), mat.steel, x, 4.7, 5.72);
    for (let k = 0; k < 11; k++) add(ship, new THREE.BoxGeometry(1.1, 0.06, 0.06), mat.steel, 6.9, 1.6 + k * 0.62, 5.72);
    for (const [x, z] of [[14, 0], [16.5, 1.4], [16.5, -1.4]]) add(ship, new THREE.SphereGeometry(0.45, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2), mat.glass, x, 7.75, z);
    for (let k = 0; k < 4; k++) add(ship, new THREE.BoxGeometry(1.6, 0.12, 8), k % 2 ? mat.dark : glow(0x4a1604), -20.6 + k * 1.8, 9.42, 0);
    legs.forEach((l) => { add(l, new THREE.SphereGeometry(0.16, 8, 6), glow(0xfff0d0), 0.45, -4.3, 0); add(l, new THREE.CylinderGeometry(0.12, 0.12, 2.6, 8), mat.orange, 0.35, -2.6, 0).rotation.z = 0.12; });
    for (let x = -11; x < 7; x += 4) add(ship, new THREE.BoxGeometry(0.12, 0.2, 9.4), mat.dark, x, 8.62, 0);
    ship.traverse((o) => { if (o.isMesh && o.material && o.material.isShaderMaterial) o.castShadow = false; });

    // ---- crew members (1.8 m tall, face +x): jointed legs and arms, LSX suits, helmet with lamp, air tanks and hose ----
    const white = new THREE.MeshStandardMaterial({ color: 0xe9e7e1, roughness: 0.5 });
    const visor = new THREE.MeshPhysicalMaterial({ color: 0x1a2a3a, metalness: 0.9, roughness: 0.08, clearcoat: 1 }), gray = new THREE.MeshStandardMaterial({ color: 0x5a5e64, roughness: 0.6, metalness: 0.4 });
    const crateTex = panelCanvas('#7a5a38', 77, 256);
    const crateMat = new THREE.MeshStandardMaterial({ map: tex(crateTex), bumpMap: tex(crateTex, 1, 1, false), bumpScale: 0.03, roughness: 0.7, metalness: 0.3 });
    let workerN = 0;
    const LSX_SUIT = new THREE.MeshStandardMaterial({ color: 0xe9e7e2, roughness: 0.72 }), LSX_JOINT = new THREE.MeshStandardMaterial({ color: 0x2a2c31, roughness: 0.85 }), LSX_ORANGE = new THREE.MeshStandardMaterial({ color: 0xe0702c, roughness: 0.6 });
    const ROLES = [0xe0702c, 0xe0b12c, 0x2f9a96].map((c) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.6 }));
    const lampM = new THREE.MeshBasicMaterial({ color: 0xfff6e0 }), chestM = new THREE.MeshBasicMaterial({ color: 0x5fe0ff }), darkM = new THREE.MeshStandardMaterial({ color: 0x24262a, roughness: 0.8 });
    // helmet lamps: a soft beam that shows after dark
    const helmetBeams = [], helmetBeamGeo = new THREE.ConeGeometry(0.7, 3.2, 16, 1, true).translate(0, -1.6, 0);
    const helmetBeamMat = new THREE.MeshBasicMaterial({ color: 0xfff0d0, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
    // the parts every crew member shares, made once
    const G = {
        th: new THREE.CylinderGeometry(0.13, 0.13 * 0.86, 0.46, 10).translate(0, -0.23, 0), thJ: new THREE.SphereGeometry(0.13 * 1.02, 10, 6),
        sh: new THREE.CylinderGeometry(0.11, 0.11 * 0.86, 0.44, 10).translate(0, -0.22, 0), shJ: new THREE.SphereGeometry(0.11 * 1.02, 10, 6),
        up: new THREE.CylinderGeometry(0.085, 0.085 * 0.86, 0.32, 10).translate(0, -0.16, 0), upJ: new THREE.SphereGeometry(0.085 * 1.02, 10, 6),
        fo: new THREE.CylinderGeometry(0.075, 0.075 * 0.86, 0.3, 10).translate(0, -0.15, 0), foJ: new THREE.SphereGeometry(0.075 * 1.02, 10, 6),
    };
    function worker() {
        const n = workerN++, w = new THREE.Group(), suitM = LSX_SUIT;
        const seg = (geo, joint, m) => { const p = new THREE.Group(); add(p, geo, m); add(p, joint, m); return p; };
        const leg = (z) => {
            const th = seg(G.th, G.thJ, suitM); th.position.set(0, 0.95, z); const sh = seg(G.sh, G.shJ, LSX_SUIT);
            add(th, new THREE.TorusGeometry(0.125, 0.025, 6, 16), LSX_ORANGE, 0, -0.2, 0).rotation.x = Math.PI / 2; add(sh, new THREE.SphereGeometry(0.118, 14, 10), LSX_JOINT); sh.position.y = -0.46; th.add(sh);
            add(sh, new THREE.BoxGeometry(0.1, 0.15, 0.17), gray, 0.1, -0.02, 0); add(sh, new THREE.BoxGeometry(0.36, 0.15, 0.22), darkM, 0.07, -0.47, 0); add(sh, new THREE.BoxGeometry(0.38, 0.04, 0.24), gray, 0.07, -0.55, 0);
            w.add(th); return [th, sh];
        };
        const [thL, shL] = leg(0.13), [thR, shR] = leg(-0.13);
        add(w, new THREE.BoxGeometry(0.3, 0.22, 0.44), gray, 0, 1.0, 0);
        add(w, new THREE.CylinderGeometry(0.25, 0.22, 0.5, 12), suitM, 0, 1.25, 0);
        add(w, new THREE.BoxGeometry(0.36, 0.36, 0.52), suitM, 0.02, 1.52, 0);
        add(w, new THREE.BoxGeometry(0.1, 0.26, 0.34), LSX_JOINT, 0.2, 1.53, 0);
        const chestLogo = new THREE.Mesh(new THREE.PlaneGeometry(0.2, 0.2), patchMat); chestLogo.position.set(0.215, 1.58, -0.13); chestLogo.rotation.y = Math.PI / 2; w.add(chestLogo);
        const backLogo = new THREE.Mesh(new THREE.PlaneGeometry(0.36, 0.36), patchMat); backLogo.position.set(-0.56, 1.52, 0); backLogo.rotation.y = -Math.PI / 2; w.add(backLogo);
        add(w, new THREE.BoxGeometry(0.37, 0.05, 0.53), LSX_ORANGE, 0.02, 1.36, 0);
        add(w, new THREE.BoxGeometry(0.03, 0.05, 0.22), chestM, 0.26, 1.6, 0);
        add(w, new THREE.BoxGeometry(0.03, 0.1, 0.12), ROLES[n % ROLES.length], 0.21, 1.42, 0.12);
        for (const z of [0.29, -0.29]) { const sp = add(w, new THREE.SphereGeometry(0.13, 10, 8), ROLES[n % ROLES.length], 0, 1.68, z); sp.scale.y = 0.65; }
        const belt = add(w, new THREE.TorusGeometry(0.245, 0.045, 6, 18), darkM, 0, 1.07, 0); belt.rotation.x = Math.PI / 2;
        for (const z of [0.18, -0.18]) add(w, new THREE.BoxGeometry(0.12, 0.14, 0.1), gray, 0.18, 1.02, z);
        add(w, new THREE.BoxGeometry(0.26, 0.58, 0.44), gray, -0.31, 1.45, 0);
        for (const z of [0.11, -0.11]) add(w, new THREE.CylinderGeometry(0.075, 0.075, 0.5, 10), white, -0.47, 1.45, z);
        const hose = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([V(-0.38, 1.74, 0.14), V(-0.25, 1.9, 0.26), V(-0.02, 1.84, 0.24)]), 10, 0.022, 5), darkM); w.add(hose);
        add(w, new THREE.CylinderGeometry(0.015, 0.015, 0.5, 4), gray, -0.4, 1.95, -0.14);
        add(w, new THREE.TorusGeometry(0.19, 0.04, 6, 14), white, 0, 1.73, 0).rotation.x = Math.PI / 2;
        const head = new THREE.Group(); head.position.y = 1.92; w.add(head);
        add(head, new THREE.SphereGeometry(0.235, 18, 14), white);
        add(head, new THREE.SphereGeometry(0.24, 16, 12, -0.95, 1.9, 0.85, 1.0), visor, 0.01, 0, 0);
        add(head, new THREE.BoxGeometry(0.1, 0.07, 0.1), lampM, 0.1, 0.19, 0.13);
        { const b = new THREE.Mesh(helmetBeamGeo, helmetBeamMat); b.position.set(0.14, 0.19, 0.13); b.rotation.z = Math.PI / 2 - 0.35; b.visible = false; head.add(b); helmetBeams.push(b); }
        add(head, new THREE.BoxGeometry(0.16, 0.04, 0.3), gray, 0.02, 0.24, 0);
        add(head, new THREE.TorusGeometry(0.236, 0.022, 6, 24), LSX_ORANGE).rotation.y = Math.PI / 2;
        const hl = new THREE.Mesh(new THREE.PlaneGeometry(0.13, 0.13), patchMat); hl.position.set(-0.05, 0.05, 0.237); head.add(hl);
        const arm = (z) => {
            const up = seg(G.up, G.upJ, suitM); up.position.set(0, 1.64, z); const fo = seg(G.fo, G.foJ, suitM); fo.position.y = -0.32; up.add(fo);
            add(fo, new THREE.SphereGeometry(0.09, 8, 6), darkM, 0, -0.32, 0); add(fo, new THREE.TorusGeometry(0.08, 0.022, 6, 14), LSX_ORANGE, 0, -0.26, 0).rotation.x = Math.PI / 2; add(fo, new THREE.SphereGeometry(0.09, 8, 6), LSX_JOINT); w.add(up); return [up, fo];
        };
        const [armL, foL] = arm(0.34), [armR, foR] = arm(-0.34);
        const box = add(w, new THREE.BoxGeometry(0.55, 0.42, 0.5), crateMat, 0.5, 1.28, 0); box.visible = false;
        const tool = add(foR, new THREE.CylinderGeometry(0.04, 0.04, 0.4, 6), gray, 0.05, -0.42, 0);
        w.userData = { thL, thR, shL, shR, armL, armR, foL, foR, head, box, tool, n };
        return w;
    }
    function pose(w, t, walk, carry, weld, crouch = false) {
        const u = w.userData, ph = t * 9, s = walk ? Math.sin(ph) * 0.5 : 0;
        u.thL.rotation.z = s; u.thR.rotation.z = -s;
        u.shL.rotation.z = walk ? -Math.max(0, Math.sin(ph - 1.2)) * 0.9 : 0; u.shR.rotation.z = walk ? -Math.max(0, -Math.sin(ph - 1.2)) * 0.9 : 0;
        u.box.visible = carry; u.tool.visible = weld;
        if (carry) { u.armL.rotation.z = u.armR.rotation.z = 0.7; u.foL.rotation.z = u.foR.rotation.z = 0.9; }
        else if (weld) { u.armL.rotation.z = 0.25; u.foL.rotation.z = 0.5; u.armR.rotation.z = 1.2 + Math.sin(t * 5) * 0.06; u.foR.rotation.z = 0.8; }
        else { u.armL.rotation.z = -s * 0.7; u.armR.rotation.z = s * 0.7; u.foL.rotation.z = u.foR.rotation.z = 0.3; }
        let y = (u.baseY || 0) + (walk ? Math.abs(Math.cos(ph)) * 0.05 : 0);
        if (crouch) { u.thL.rotation.z = u.thR.rotation.z = 1.25; u.shL.rotation.z = u.shR.rotation.z = -2.1; u.armL.rotation.z = u.armR.rotation.z = 2.5; u.foL.rotation.z = u.foR.rotation.z = 1.6; y -= 0.38; }
        u.head.rotation.y = walk || weld ? 0 : Math.sin(t * 0.7 + u.n) * 0.5; u.head.rotation.z = weld ? 0.35 : 0;
        w.position.y = y;
    }
    const face = (w, dx, dz) => { w.rotation.y = Math.atan2(-dz, dx); };

    // ---- the sky over both bases (day, night with stars and a moon) ------------------------------------------------
    const SUN = V(-0.55, 0.62, 0.56).normalize();
    const skyMat = new THREE.ShaderMaterial({
        side: THREE.BackSide, depthWrite: false, fog: false, uniforms: { sun: { value: SUN }, night: { value: 0 } },
        vertexShader: 'varying vec3 vD; void main(){ vD=normalize(position); gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }',
        fragmentShader: 'uniform vec3 sun; uniform float night; varying vec3 vD; float hs(vec3 p){ return fract(sin(dot(p, vec3(127.1,311.7,74.7)))*43758.5453); } void main(){ float h=max(vD.y,0.); vec3 zen=vec3(.23,.39,.55), hor=vec3(.86,.78,.66), gr=vec3(.74,.60,.45); vec3 c=mix(hor,zen,pow(h,.45)); if(vD.y<0.) c=mix(hor,gr,clamp(-vD.y*4.,0.,1.)); float d=max(dot(vD,sun),0.); c+=vec3(1.,.95,.85)*pow(d,900.)*8.; c+=vec3(1.,.85,.6)*pow(d,12.)*.35; vec3 nc=mix(vec3(.05,.06,.09),vec3(.012,.018,.035),pow(h,.5)); if(vD.y<0.) nc=vec3(.03,.028,.03); vec3 q=floor(vD*260.); float st=step(.9975,hs(q))*smoothstep(0.,.25,vD.y); nc+=vec3(st)*(.6+.4*hs(q+1.)); vec3 mdir=normalize(vec3(.5,.55,-.66)); nc+=vec3(.9,.92,1.)*smoothstep(.9994,.9997,dot(vD,mdir))*1.2+vec3(.2,.24,.35)*pow(max(dot(vD,mdir),0.),40.)*.4; gl_FragColor=vec4(mix(c,nc,night),1.); }',
    });
    const skyOnly = new THREE.Scene(); skyOnly.add(new THREE.Mesh(new THREE.SphereGeometry(100, 32, 16), skyMat));
    const cubeEnv = (scn) => {
        const rt = new THREE.WebGLCubeRenderTarget(128, { generateMipmaps: true, minFilter: THREE.LinearMipmapLinearFilter });
        new THREE.CubeCamera(1, 1000, rt).update(renderer, scn); return rt.texture;
    };
    const dayEnv = cubeEnv(skyOnly); skyMat.uniforms.night.value = 1; const nightEnv = cubeEnv(skyOnly); skyMat.uniforms.night.value = 0;

    // ---- the landing pad (both bases use it) --------------------------------------------------------------------------
    const padC = canvas(1024), pg = padC.getContext('2d'); pg.fillStyle = '#77726b'; pg.fillRect(0, 0, 1024, 1024);
    for (let i = 0; i < 30000; i++) { const v = rnd(i + 7) < 0.5 ? 0 : 255; pg.fillStyle = `rgba(${v},${v},${v},${rnd(i) * 0.06})`; pg.fillRect(rnd(i + 1) * 1024, rnd(i + 2) * 1024, 2 + rnd(i + 3) * 4, 2); }
    pg.strokeStyle = 'rgba(0,0,0,.35)'; pg.lineWidth = 3; for (let k = 0; k <= 1024; k += 128) { pg.beginPath(); pg.moveTo(k, 0); pg.lineTo(k, 1024); pg.moveTo(0, k); pg.lineTo(1024, k); pg.stroke(); }
    const scorch = pg.createRadialGradient(512, 512, 20, 512, 512, 330); scorch.addColorStop(0, 'rgba(20,16,12,.7)'); scorch.addColorStop(1, 'rgba(20,16,12,0)'); pg.fillStyle = scorch; pg.fillRect(0, 0, 1024, 1024);
    pg.strokeStyle = 'rgba(235,232,225,.8)'; pg.lineWidth = 14; pg.beginPath(); pg.arc(512, 512, 330, 0, 7); pg.stroke();
    pg.lineWidth = 34; pg.setLineDash([60, 40]); pg.strokeStyle = '#d9a82a'; pg.beginPath(); pg.arc(512, 512, 480, 0, 7); pg.stroke(); pg.setLineDash([]);
    pg.fillStyle = 'rgba(235,232,225,.75)'; pg.font = '700 130px "Share Tech Mono", monospace'; pg.textAlign = 'center'; pg.fillText('LSX', 512, 560); pg.font = '700 44px "Share Tech Mono", monospace'; pg.fillText('PAD 01', 512, 250);
    const pad = new THREE.Mesh(new THREE.CylinderGeometry(26, 27, 0.8, 72), [new THREE.MeshStandardMaterial({ color: 0x5e5a54, roughness: 0.9 }), new THREE.MeshStandardMaterial({ map: tex(padC), roughness: 0.85 }), new THREE.MeshStandardMaterial({ color: 0x5e5a54 })]);
    pad.receiveShadow = true;
    const cgeo = rbox(1.2, 1, 1.1, 0.06);

    // ---- soft sprites and particles ----------------------------------------------------------------------------
    const aoTex = (() => { const c = canvas(128), g = c.getContext('2d'), gr = g.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(0,0,0,.85)'); gr.addColorStop(0.6, 'rgba(0,0,0,.35)'); gr.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = gr; g.fillRect(0, 0, 128, 128); return new THREE.CanvasTexture(c); })();
    const softPoints = (color, blending) => new THREE.ShaderMaterial({
        transparent: true, depthWrite: false, blending, uniforms: { c: { value: new THREE.Color(color) } },
        vertexShader: 'attribute float aA; attribute float aS; varying float vA; void main(){ vA=aA; vec4 mv=modelViewMatrix*vec4(position,1.); gl_PointSize=aS*(600./-mv.z); gl_Position=projectionMatrix*mv; }',
        fragmentShader: 'uniform vec3 c; varying float vA; void main(){ float d=length(gl_PointCoord-.5); float a=smoothstep(.5,0.,d)*vA; gl_FragColor=vec4(c,a); }',
    });
    const pointsGeo = (n) => {   // positions plus per-point alpha (aA) and size (aS), for softPoints
        const g = new THREE.BufferGeometry();
        g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
        g.setAttribute('aA', new THREE.BufferAttribute(new Float32Array(n), 1)); g.setAttribute('aS', new THREE.BufferAttribute(new Float32Array(n), 1));
        return g;
    };
    const glowTex = (() => {
        const c = canvas(128), g = c.getContext('2d'), gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
        gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.25, 'rgba(255,255,255,.55)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, 128, 128); return tex(c);
    })();
    const cloudTex = (() => {
        const c = canvas(256), g = c.getContext('2d');
        for (let i = 0; i < 26; i++) {
            const x = 60 + rnd(i + 800) * 136, y = 80 + rnd(i + 801) * 96, r = 30 + rnd(i + 802) * 50, gr = g.createRadialGradient(x, y, 0, x, y, r);
            gr.addColorStop(0, 'rgba(255,255,255,.55)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, 256, 256);
        } return tex(c);
    })();
    const cloudMat = (op, col = 0xffffff) => new THREE.SpriteMaterial({ map: cloudTex, color: col, transparent: true, opacity: op, depthWrite: false });

    // colours above were written as sRGB; plain material colours are converted to linear once so they render true
    const seen = new Set();
    function linearize(root) {
        root.traverse((o) => {
            const ms = o.material ? (Array.isArray(o.material) ? o.material : [o.material]) : [];
            ms.forEach((m) => { if (!seen.has(m) && m.color && !m.isShaderMaterial) { seen.add(m); m.color.convertSRGBToLinear(); } });
            if (o.isLight && o.color && !seen.has(o)) { seen.add(o); o.color.convertSRGBToLinear(); }
        });
    }
    linearize(ship);
    // the ship's parts that move, and its pose for a scene: parked (legs down) or flying (legs folded)
    const shipParts = { legs, ramp, hold, cabin, radar, bellyStrobe, navR, navG, strobe, dish0, flames };

    return {
        THREE, renderer, clamp, lerp, ease, rnd, hash, sm, fbm, V, canvas, tex, add, extrude, rbox, panelCanvas, hazardCanvas, decal, logoCanvas,
        logoMat, patchMat, mat, glow, navMat, winMat, redLamp, heatMat, ship, shipParts, thrust, worker, pose, face, crateMat, cgeo,
        helmetBeams, helmetBeamMat, SUN, skyMat, cubeEnv, dayEnv, nightEnv, pad, aoTex, softPoints, pointsGeo, glowTex, cloudTex, cloudMat, linearize,
    };
};
