// Station LSX, part 2: the desert base on planet HOME. Pad 01 with the freighter, the crew in LSX suits, the crane arm,
// the fuel truck, the forklift, the LSX factory with its hauler and roads, two more ships loading on their own pads,
// dust devils, and day or night.
// frame(T, C, idle, blend): T is the trip's timeline (station.js), C the running clock for everything that loops,
// idle means the ship is home with nothing to do, blend (0..1) walks the crew from routine work to loading the ship.
window.LSX = window.LSX || {};
LSX.desert = (k) => {
    const { THREE, clamp, lerp, ease, rnd, fbm, V, canvas, tex, add, rbox, panelCanvas, hazardCanvas, logoCanvas, logoMat, mat, glow, navMat, winMat,
        ship, shipParts, thrust, worker, pose, face, crateMat, cgeo, skyMat, dayEnv, pad, aoTex, softPoints, pointsGeo, glowTex, cloudMat, heatMat } = k;
    const { legs, ramp, hold, cabin, radar, bellyStrobe, navR, navG, strobe, dish0, flames } = shipParts;

    const desert = new THREE.Scene();
    desert.add(new THREE.Mesh(new THREE.SphereGeometry(3000, 48, 24), skyMat));
    desert.environment = dayEnv;
    desert.fog = new THREE.FogExp2(0xd9c8ac, 0.0011);
    const hemi = new THREE.HemisphereLight(0xbfd4e6, 0x9c7650, 0.5); desert.add(hemi);
    const sun = new THREE.DirectionalLight(0xfff1dc, 2.2); sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048); Object.assign(sun.shadow.camera, { left: -110, right: 110, top: 110, bottom: -110, near: 10, far: 520 }); sun.position.copy(k.SUN).multiplyScalar(240);
    sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.04; desert.add(sun, sun.target);
    // terrain
    const hgt = (x, z) => {
        // flat round the three pads, the factory site and the road corridor from the factory to Pad 01
        const d = Math.min(Math.hypot(x, z), Math.hypot(x + 92, z + 66), Math.hypot(x - 84, z + 62), Math.hypot(x / 1.6, z + 118) + 8,
            Math.abs(x + 2) + (z < -25 && z > -100 ? 0 : 99)), flat = clamp((d - 38) / 70);
        return flat * (fbm(x * 0.006, 0, z * 0.006, 4) * 26 - 9 + Math.sin(x * 0.025 + z * 0.012) * 3) + (fbm(x * 0.05, 5, z * 0.05, 3) - 0.5) * 0.8;
    };
    const tg = new THREE.PlaneGeometry(2600, 2600, 200, 200); tg.rotateX(-Math.PI / 2);
    const tp = tg.attributes.position, tcol = new Float32Array(tp.count * 3), sand1 = new THREE.Color('#d2a877').convertSRGBToLinear(), sand2 = new THREE.Color('#9c6c40').convertSRGBToLinear(), tmpC = new THREE.Color();
    for (let i = 0; i < tp.count; i++) { const x = tp.getX(i), z = tp.getZ(i); tp.setY(i, hgt(x, z)); tmpC.copy(sand1).lerp(sand2, clamp(fbm(x * 0.01, 9, z * 0.01, 4) * 1.4 - 0.2)); tcol.set([tmpC.r, tmpC.g, tmpC.b], i * 3); }
    tg.setAttribute('color', new THREE.BufferAttribute(tcol, 3)); tg.computeVertexNormals();
    const grainC = canvas(512), gg = grainC.getContext('2d'); gg.fillStyle = '#808080'; gg.fillRect(0, 0, 512, 512);
    for (let i = 0; i < 26000; i++) { const v = 90 + rnd(i) * 80 | 0; gg.fillStyle = `rgb(${v},${v},${v})`; gg.fillRect(rnd(i + 1) * 512, rnd(i + 2) * 512, 1.5, 1.5); }
    gg.strokeStyle = 'rgba(40,40,40,.35)'; gg.lineWidth = 3; for (let y = 0; y < 512; y += 22) { gg.beginPath(); for (let x = 0; x <= 512; x += 16) gg.lineTo(x, y + Math.sin(x * 0.03 + y) * 5); gg.stroke(); }
    const ground = new THREE.Mesh(tg, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, bumpMap: tex(grainC, 160, 160, false), bumpScale: 0.06 }));
    ground.receiveShadow = true; desert.add(ground);
    // mesas and rocks
    const strataC = canvas(256, 512), sg = strataC.getContext('2d');
    for (let y = 0; y < 512; y += 2) { const kk = fbm(0, y * 0.03, 3, 3), c = [186 - kk * 70, 118 - kk * 50, 78 - kk * 36].map((v) => v + (rnd(y) - 0.5) * 14 | 0); sg.fillStyle = `rgb(${c})`; sg.fillRect(0, y, 256, 2); }
    for (let i = 0; i < 4000; i++) { sg.fillStyle = `rgba(0,0,0,${rnd(i) * 0.12})`; sg.fillRect(rnd(i + 1) * 256, rnd(i + 2) * 512, 2 + rnd(i + 3) * 6, 1); }
    for (let i = 0; i < 30; i++) { sg.fillStyle = 'rgba(60,30,15,.18)'; sg.fillRect(rnd(i + 70) * 256, 0, 2 + rnd(i + 71) * 5, 512); }
    const rockMat = new THREE.MeshStandardMaterial({ map: tex(strataC, 3, 1), bumpMap: tex(strataC, 3, 1, false), bumpScale: 0.6, roughness: 0.95, flatShading: true });
    for (let i = 0; i < 16; i++) {
        const a = -Math.PI * 0.95 + rnd(i + 200) * Math.PI * 1.3, d = 380 + rnd(i + 201) * 650, r = 30 + rnd(i + 202) * 70, h = 40 + rnd(i + 203) * 90;
        const g = new THREE.CylinderGeometry(r * 0.8, r * 1.15, h, 10, 5); const p = g.attributes.position;
        for (let q = 0; q < p.count; q++) { const y = p.getY(q); if (y < h / 2 - 0.1) { p.setX(q, p.getX(q) * (0.85 + rnd(q + i * 99) * 0.3)); p.setZ(q, p.getZ(q) * (0.85 + rnd(q + i * 77) * 0.3)); } }
        g.computeVertexNormals(); const m = new THREE.Mesh(g, rockMat); m.position.set(Math.sin(a) * d, h / 2 - 8 + hgt(Math.sin(a) * d, -Math.cos(a) * d), -Math.cos(a) * d); desert.add(m);
    }
    for (let i = 0; i < 60; i++) {
        const a = rnd(i + 300) * Math.PI * 2, d = 34 + rnd(i + 301) * 120, s = 0.4 + rnd(i + 302) * 2.2;
        const g = new THREE.DodecahedronGeometry(s, 0); const p = g.attributes.position; for (let q = 0; q < p.count; q++) p.setY(q, p.getY(q) * 0.6);
        const m = new THREE.Mesh(g, rockMat); const x = Math.cos(a) * d, z = Math.sin(a) * d; m.position.set(x, hgt(x, z) + s * 0.2, z); m.rotation.y = a; m.castShadow = m.receiveShadow = true; desert.add(m);
    }
    // landing pad
    desert.add(pad);
    const padLights = [];
    for (let i = 0; i < 16; i++) {
        const a = i / 16 * Math.PI * 2, m = new THREE.Mesh(new THREE.SphereGeometry(0.25, 8, 6), new THREE.MeshBasicMaterial({ color: 0xffb040 }));
        m.position.set(Math.cos(a) * 25.4, 0.5, Math.sin(a) * 25.4); desert.add(m); padLights.push(m);
    }
    // floodlight tower and fuel hose
    const tower = new THREE.Group(); tower.position.set(20, 0, -24); desert.add(tower);
    for (const [x, z] of [[-1.5, -1.5], [1.5, -1.5], [-1.5, 1.5], [1.5, 1.5]]) add(tower, new THREE.BoxGeometry(0.3, 26, 0.3), mat.dark, x, 13, z);
    for (let y = 1; y < 26; y += 2.6) {
        for (const [rx, rz, ry] of [[0, 1.5, 0], [0, -1.5, 0], [1.5, 0, Math.PI / 2], [-1.5, 0, Math.PI / 2]]) {
            const b = add(tower, new THREE.BoxGeometry(4.2, 0.14, 0.14), mat.dark, rx, y + 1.3, rz); b.rotation.set(0, ry, 0.55);
        }
    }
    const lampC = canvas(256, 128), lg = lampC.getContext('2d'); lg.fillStyle = '#222'; lg.fillRect(0, 0, 256, 128);
    for (let r = 0; r < 3; r++) for (let q = 0; q < 6; q++) { lg.fillStyle = '#fff7e0'; lg.beginPath(); lg.arc(22 + q * 42, 22 + r * 42, 16, 0, 7); lg.fill(); }
    add(tower, new THREE.BoxGeometry(8, 4, 0.6), mat.dark, 0, 27.5, 0);
    const lamp = new THREE.Mesh(new THREE.PlaneGeometry(7.6, 3.7), new THREE.MeshBasicMaterial({ map: tex(lampC) })); lamp.position.set(0, 27.5, 0.32); tower.add(lamp);
    const flood = new THREE.SpotLight(0xfff0d0, 1.5, 120, 0.5, 0.6, 1.5); flood.position.set(20, 27, -23); flood.target.position.set(0, 4, 0); desert.add(flood, flood.target);
    const arm = add(tower, new THREE.BoxGeometry(12, 0.8, 0.8), mat.hullB, -6, 11, 1.5);
    const hoseCurve = new THREE.CatmullRomCurve3([V(18.5, 1, -22.5), V(16, 0.4, -14), V(12, 0.3, -6), V(9, 1.5, -2.5), V(8, 2.8, -1.2)]);
    const hose = new THREE.Mesh(new THREE.TubeGeometry(hoseCurve, 40, 0.28, 8), new THREE.MeshStandardMaterial({ color: 0x151618, roughness: 0.6 }));
    hose.castShadow = true; desert.add(hose);
    // crates, a cargo sled and a scissor lift
    const crates = new THREE.Group(); crates.position.set(-30, 0, 12); desert.add(crates);
    [[0, 0, 0], [1.3, 0, 0], [2.6, 0, 0.1], [0.6, 1, 0], [1.9, 1, 0], [0, 0, 1.3], [1.3, 0, 1.3], [0.7, 1, 1.3]].forEach(([x, y, z], i) => { add(crates, cgeo, i % 3 ? crateMat : mat.hullB, x, y + 0.5, z).rotation.y = (rnd(i) - 0.5) * 0.2; });
    const restock = [[3.9, 0, 0.2], [3.9, 0, 1.4], [2.6, 0, 1.4], [3.3, 1, 0.8], [2, 1, 0.1], [1.4, 2, 0.6]].map(([x, y, z], i) => { const m = add(crates, cgeo, i % 2 ? crateMat : mat.hullB, x, y + 0.5, z); m.rotation.y = (rnd(i + 70) - 0.5) * 0.25; return m; });
    const scissor = new THREE.Group(); scissor.position.set(-9.5, 0.4, 7.0); desert.add(scissor);
    add(scissor, new THREE.BoxGeometry(3, 0.6, 2.2), mat.orange, 0, 0.3, 0);
    for (let q = 0; q < 4; q++) { const s = add(scissor, new THREE.BoxGeometry(3, 0.12, 0.12), mat.dark, 0, 1 + q * 1.3, 0); s.rotation.z = q % 2 ? 0.4 : -0.4; }
    add(scissor, new THREE.BoxGeometry(3, 0.2, 2.2), mat.dark, 0, 5.8, 0);
    add(scissor, new THREE.BoxGeometry(3, 0.8, 0.06), mat.hazard, 0, 6.3, 1.1);
    // the base: habitat, mast, fuel tanks, containers, rover, drifting sand
    const hab = new THREE.Group(); hab.position.set(-58, 0, -34); hab.rotation.y = 0.35; desert.add(hab);
    const tube = add(hab, new THREE.CylinderGeometry(4, 4, 16, 28), mat.hullB, 0, 4.6, 0); tube.rotation.z = Math.PI / 2;
    for (const x of [-8, 8]) add(hab, new THREE.CylinderGeometry(4.3, 4.3, 0.6, 28), mat.dark, x, 4.6, 0).rotation.z = Math.PI / 2;
    add(hab, new THREE.SphereGeometry(4, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2), mat.glass, 9, 4.6, 0).rotation.z = -Math.PI / 2;
    for (let i = 0; i < 9; i++) add(hab, new THREE.BoxGeometry(0.9, 0.5, 0.1), winMat, -6 + i * 1.5, 5.4, 4.02);
    for (const x of [-6, 6]) for (const z of [-2.5, 2.5]) add(hab, new THREE.BoxGeometry(0.5, 1.2, 0.5), mat.dark, x, 0.6, z);
    add(hab, new THREE.BoxGeometry(3, 3, 3), mat.hullB, -4, 10, 0);
    add(hab, new THREE.CylinderGeometry(0.15, 0.2, 16, 6), mat.steel, 4, 16, 0);
    const mastLamp = add(hab, new THREE.SphereGeometry(0.3, 8, 6), glow(0xff3b30), 4, 24.2, 0);
    const habDish = add(hab, new THREE.SphereGeometry(2.2, 20, 10, 0, Math.PI * 2, 0, 1.0), mat.steel, -4, 12.4, 0); habDish.rotation.set(-0.7, 0, 0.4);
    const sock = new THREE.Mesh(new THREE.ConeGeometry(0.5, 2.6, 12, 1, true), new THREE.MeshStandardMaterial({ map: tex(hazardCanvas(), 1, 3), side: THREE.DoubleSide }));
    const sockPivot = new THREE.Group(); sockPivot.position.set(4, 22.8, 0); sock.rotation.z = Math.PI / 2; sock.position.x = 1.3; sockPivot.add(sock); hab.add(sockPivot);
    const tankMat = new THREE.MeshStandardMaterial({ color: 0xe6e2da, metalness: 0.4, roughness: 0.35 });
    for (let i = 0; i < 3; i++) {
        const t = new THREE.Group(); t.position.set(34 + i * 5.6, 0, 6 - i * 2); desert.add(t);
        add(t, new THREE.CylinderGeometry(2.2, 2.2, 6, 24), tankMat, 0, 4.4, 0); add(t, new THREE.SphereGeometry(2.2, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2), tankMat, 0, 7.4, 0);
        add(t, new THREE.CylinderGeometry(2.25, 2.25, 0.6, 24), mat.orange, 0, 5.8, 0); for (const a of [0, 2.1, 4.2]) add(t, new THREE.BoxGeometry(0.3, 1.6, 0.3), mat.dark, Math.cos(a) * 1.8, 0.8, Math.sin(a) * 1.8);
    }
    const pipeRun = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([V(34, 1.5, 6), V(28, 0.4, 2), V(24, 0.4, -12), V(19, 1, -22)]), 30, 0.22, 8), mat.steel); pipeRun.castShadow = true; desert.add(pipeRun);
    const ribC = canvas(256), rg = ribC.getContext('2d'); rg.fillStyle = '#9a9a9a'; rg.fillRect(0, 0, 256, 256);
    for (let x = 0; x < 256; x += 16) { rg.fillStyle = 'rgba(0,0,0,.35)'; rg.fillRect(x, 0, 4, 256); rg.fillStyle = 'rgba(255,255,255,.25)'; rg.fillRect(x + 5, 0, 2, 256); }
    for (let i = 0; i < 2500; i++) { rg.fillStyle = `rgba(60,30,10,${rnd(i) * 0.15})`; rg.fillRect(rnd(i + 1) * 256, rnd(i + 2) * 256, 3, 2); }
    [[0xb8582a, -40, 1.3, 4, 0.2], [0x2f5d8a, -40, 1.3, 7, 0.15], [0x6a6d70, -39.6, 3.9, 5.5, 0.18], [0xb8582a, 38, 1.3, -14, 1.3]].forEach(([c, x, y, z, ry]) => {
        const m = new THREE.MeshStandardMaterial({ color: c, map: tex(ribC, 2, 1), bumpMap: tex(ribC, 2, 1, false), bumpScale: 0.05, metalness: 0.5, roughness: 0.6 });
        add(desert, new THREE.BoxGeometry(6, 2.6, 2.5), m, x, y, z).rotation.y = ry;
    });
    const rover = new THREE.Group(); desert.add(rover);
    add(rover, new THREE.BoxGeometry(4.2, 0.8, 2.2), mat.orange, 0, 1.2, 0); add(rover, new THREE.BoxGeometry(1.4, 1.2, 2), mat.hullB, 1.6, 2.1, 0);
    add(rover, new THREE.BoxGeometry(0.1, 0.6, 1.7), mat.glass, 2.32, 2.3, 0); add(rover, new THREE.BoxGeometry(1.5, 1.1, 1.5), crateMat, -0.9, 2.15, 0);
    const wheels = []; for (const x of [-1.4, 0, 1.4]) for (const z of [-1.25, 1.25]) { const wh = add(rover, new THREE.CylinderGeometry(0.55, 0.55, 0.45, 14), mat.dark, x, 0.55, z); wh.rotation.x = Math.PI / 2; wheels.push(wh); }
    for (const z of [-0.7, 0.7]) add(rover, new THREE.BoxGeometry(0.1, 0.2, 0.3), glow(0xfff4dc), 2.36, 1.3, z);
    const roverLamp = add(rover, new THREE.SphereGeometry(0.14, 6, 4), glow(0xffa020), 1.6, 2.8, 0);
    const SAND = 500, sandGeo = pointsGeo(SAND);
    function desertExtras(C) {
        const ang = C * 0.16 + 2.2, rx = 36, rz = 24;
        rover.position.set(Math.cos(ang) * rx - 4, 0.4, Math.sin(ang) * rz);
        rover.rotation.y = Math.atan2(-(Math.cos(ang) * rz), -Math.sin(ang) * rx);
        wheels.forEach((w) => { w.rotation.y = -C * 5; });
        roverLamp.visible = Math.floor(C * 2) % 2 === 0; mastLamp.visible = Math.floor(C * 1.2) % 2 === 0;
        sockPivot.rotation.y = 0.3 + Math.sin(C * 0.8) * 0.25; sock.rotation.x = Math.sin(C * 3) * 0.08;
        const sp = sandGeo.attributes.position, sa = sandGeo.attributes.aA, ss = sandGeo.attributes.aS;
        for (let i = 0; i < SAND; i++) {
            const ph = (C * (0.05 + rnd(i) * 0.05) + rnd(i + 1)) % 1, x = -160 + ph * 320, z = -90 + rnd(i + 2) * 150;
            sp.setXYZ(i, x, hgt(x, z) + 0.3 + rnd(i + 3) * 2.5 + Math.sin(C * 2 + i) * 0.3, z); sa.setX(i, Math.sin(ph * Math.PI) * 0.16); ss.setX(i, 1.2 + rnd(i + 4) * 2.5);
        }
        sp.needsUpdate = sa.needsUpdate = ss.needsUpdate = true;
    }
    // the crew, and one more who walks between the habitat and the pad at each shift change
    const crew = Array.from({ length: 7 }, worker); crew.forEach((w) => desert.add(w));
    const shiftW = worker(); desert.add(shiftW);
    crew[5].userData.baseY = 6.3; crew[6].userData.baseY = 0.4;
    // two more ships idling on their own pads, crews loading cargo through a side hatch (they never take off)
    const idx = (o) => ship.children.indexOf(o);
    const rampI = idx(ramp), pivotI = flames.map((f) => idx(f.pivot)), glowI = flames.map((f) => idx(f.glow));
    const BG = [{ x: -92, z: -66, ry: 0.45, base: '#bdb7aa', seed: 61 }, { x: 84, z: -62, ry: -0.5, base: '#4f6275', seed: 83 }];
    const bgShips = BG.map((b, n) => {
        const sh = ship.clone(); sh.position.set(b.x, 5.1, b.z); sh.rotation.y = b.ry; desert.add(sh);
        const pd = pad.clone(); pd.position.set(b.x, 0, b.z); desert.add(pd);
        const tints = new Map();
        sh.traverse((o) => {
            if (o.isSpotLight) o.visible = false;
            if (o.isMesh && (o.material === mat.hullE || o.material === mat.hullB || o.material === mat.hullBE)) {
                if (!tints.has(o.material)) { const m = o.material.clone(), c = panelCanvas(b.base, b.seed, 512), r = o.material.map.repeat; m.map = tex(c, r.x, r.y); m.bumpMap = tex(c, r.x, r.y, false); tints.set(o.material, m); }
                o.material = tints.get(o.material);
            }
        });
        sh.children[rampI].rotation.z = 0.74;
        const idle = [];
        pivotI.forEach((i, q) => {
            const pv = sh.children[i]; pv.visible = flames[q].dir === 'back'; pv.scale.set(1, 0.2, 1);
            pv.children.forEach((c) => { c.material = c.material.clone(); idle.push(c.material); });
        });
        glowI.forEach((i) => { sh.children[i].material = new THREE.MeshBasicMaterial({ color: 0xff8a3a, transparent: true, opacity: 0.55 }); });
        // open side hatch with a lit hold and cargo stacked inside
        add(sh, new THREE.BoxGeometry(5, 4, 0.1), new THREE.MeshBasicMaterial({ color: 0x3a2814 }), -3, 3.9, 5.67);
        for (const [x, y, w, h] of [[-4.6, 2.5, 1.3, 1.1], [-3.2, 2.5, 1.3, 1.1], [-3.9, 3.65, 1.2, 1], [-1.6, 2.5, 1, 1.1]]) add(sh, new THREE.BoxGeometry(w, h, 0.1), crateMat, x, y, 5.72);
        add(sh, new THREE.BoxGeometry(5, 0.08, 0.1), winMat, -3, 5.85, 5.73);
        const awning = add(sh, new THREE.BoxGeometry(5.2, 0.2, 3.2), tints.get(mat.hullB) || mat.hullB, -3, 6.3, 7.25); awning.rotation.x = 0.12;
        for (const x of [-5.4, -0.6]) add(sh, new THREE.CylinderGeometry(0.05, 0.05, 1.8, 6), mat.steel, x, 5.5, 8.6).rotation.x = -0.9;
        const holdLight = new THREE.PointLight(0xffc88a, 1.3, 16, 2); holdLight.position.set(-3, 3.8, 8); sh.add(holdLight);
        // conveyor from the ground up to the hatch, with crates riding it
        const G = V(-3, -4.7, 15.5), Tp = V(-3, 2.0, 6.1), dv = Tp.clone().sub(G), L = dv.length(), th = Math.atan2(dv.y, -dv.z);
        const belt = add(sh, new THREE.BoxGeometry(1.6, 0.3, L), mat.dark, -3, (G.y + Tp.y) / 2, (G.z + Tp.z) / 2); belt.rotation.x = th;
        for (const side of [-0.85, 0.85]) { const r = add(sh, new THREE.BoxGeometry(0.12, 0.35, L), mat.orange, -3 + side, (G.y + Tp.y) / 2 + 0.2, (G.z + Tp.z) / 2); r.rotation.x = th; }
        for (const f of [0.3, 0.65]) { const q = G.clone().lerp(Tp, f), leg = add(sh, new THREE.CylinderGeometry(0.12, 0.12, q.y - G.y, 6), mat.steel, -3, (q.y + G.y) / 2, q.z); leg.visible = q.y - G.y > 0.2; }
        const boxes = Array.from({ length: 5 }, () => { const c = add(sh, new THREE.BoxGeometry(0.9, 0.7, 0.9), crateMat); c.rotation.x = th; return c; });
        const pile = V(-9, -4.7, 17.5);
        [[0, 0, 0], [1.2, 0, 0], [0.6, 1, 0], [0, 0, 1.2], [1.2, 0, 1.2]].forEach(([x, y, z]) => add(sh, cgeo, crateMat, pile.x + x, pile.y + y + 0.5, pile.z + z));
        const bcrew = Array.from({ length: 5 }, () => { const w = worker(); sh.add(w); return w; });
        return { sh, idle, G, Tp, boxes, pile, bcrew, n };
    });
    const blob = (x, z, sx, sz, ry = 0, op = 0.5, y = 0.43) => {
        const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: aoTex, transparent: true, opacity: op, depthWrite: false }));
        m.rotation.set(-Math.PI / 2, 0, ry); m.scale.set(sx, sz, 1); m.position.set(x, y, z); desert.add(m); return m;
    };
    const mainAO = blob(-1, 0, 52, 17, 0, 0.55);
    BG.forEach((b) => blob(b.x, b.z, 52, 17, b.ry, 0.55));
    for (let i = 0; i < 3; i++) blob(34 + i * 5.6, 6 - i * 2, 7, 7, 0, 0.5, 0.05);
    blob(-58, -34, 22, 12, 0.35, 0.45, 0.05); blob(-30 + 1.3, 12.6, 5, 4, 0, 0.5, 0.05);
    const tracks = new THREE.Mesh(new THREE.RingGeometry(0.965, 1.035, 128), new THREE.MeshBasicMaterial({ color: 0x5a3f22, transparent: true, opacity: 0.22, depthWrite: false }));
    tracks.rotation.x = -Math.PI / 2; tracks.scale.set(36, 24, 1); tracks.position.set(-4, 0.44, 0); desert.add(tracks);
    // base machinery: a crane arm loading the cargo pods, a fuel truck, a forklift, light masts, a solar field, a spaceport sign, barrels
    const ARM0 = V(7.5, 0.4, 12.5), PALLET = V(13, 0.4, 14.5), L1 = 5.6, L2 = 5.4;
    add(desert, new THREE.BoxGeometry(2.4, 0.3, 2.4), mat.dark, PALLET.x, 0.55, PALLET.z);
    [[0, 0], [1.1, 0], [0, 1.1], [1.1, 1.1]].forEach(([dx, dz]) => add(desert, cgeo, crateMat, PALLET.x - 0.55 + dx, 1.2, PALLET.z - 0.55 + dz));
    const armBase = new THREE.Group(); armBase.position.copy(ARM0); desert.add(armBase);
    add(armBase, new THREE.CylinderGeometry(1.3, 1.6, 0.8, 20), mat.dark, 0, 0.4, 0);
    const yawG = new THREE.Group(); yawG.position.y = 0.8; armBase.add(yawG);
    add(yawG, new THREE.CylinderGeometry(0.9, 1.1, 1.2, 16), mat.orange, 0, 0.6, 0);
    const shG = new THREE.Group(); shG.position.y = 1.5; yawG.add(shG);
    add(shG, new THREE.CylinderGeometry(0.55, 0.55, 1.4, 16), mat.dark).rotation.x = Math.PI / 2;
    add(shG, rbox(L1, 0.7, 0.8, 0.15), mat.orange, L1 / 2, 0, 0);
    const elG = new THREE.Group(); elG.position.x = L1; shG.add(elG);
    add(elG, new THREE.CylinderGeometry(0.45, 0.45, 1.1, 14), mat.dark).rotation.x = Math.PI / 2;
    add(elG, rbox(L2, 0.55, 0.6, 0.12), mat.orange, L2 / 2, 0, 0);
    const wrist = new THREE.Group(); wrist.position.x = L2; elG.add(wrist);
    add(wrist, new THREE.BoxGeometry(0.5, 0.5, 1.2), mat.dark, 0, -0.3, 0);
    for (const z of [-0.45, 0.45]) add(wrist, new THREE.BoxGeometry(0.12, 0.8, 0.12), mat.steel, 0, -0.8, z);
    const heldCrate = add(desert, cgeo, crateMat);
    const armHose = new THREE.Mesh(new THREE.TorusGeometry(1.2, 0.08, 6, 16, Math.PI), mat.dark); armHose.position.set(1.2, 0.5, 0.45); shG.add(armHose);
    const armLamp = add(yawG, new THREE.SphereGeometry(0.18, 8, 6), new THREE.MeshBasicMaterial({ color: 0xffb030 }), 0, 1.4, 0.6);
    const operator = worker(); desert.add(operator); operator.position.set(11, 0.4, 16.5); operator.userData.baseY = 0.4;
    const POD = V(3, 11.8, 6.2), wp = new THREE.Vector3();
    function ik(target) {
        const d = V(target.x - ARM0.x, 0, target.z - ARM0.z), yaw = Math.atan2(-d.z, d.x), hor = d.length(), h = target.y - (ARM0.y + 2.3);
        const r = Math.min(Math.hypot(hor, h), L1 + L2 - 0.05), a = Math.atan2(h, hor), b = Math.acos(clamp((L1 * L1 + r * r - L2 * L2) / (2 * L1 * r), -1, 1));
        const c = Math.acos(clamp((L1 * L1 + L2 * L2 - r * r) / (2 * L1 * L2), -1, 1));
        yawG.rotation.y = yaw; shG.rotation.z = a + b; elG.rotation.z = -(Math.PI - c); wrist.rotation.z = -(shG.rotation.z + elG.rotation.z);
    }
    // fuel truck: drives out to refuel the ship idling on the east pad, then comes home
    const truck = new THREE.Group(); truck.position.set(27, 0.4, 16); truck.rotation.y = -0.6; desert.add(truck);
    add(truck, rbox(9, 0.6, 2.6, 0.1), mat.dark, 0, 1.1, 0); add(truck, rbox(2.4, 2.4, 2.6, 0.25), mat.orange, 4, 2.4, 0); add(truck, new THREE.BoxGeometry(0.1, 1, 2.2), mat.glass, 5.21, 2.9, 0);
    const tankT = add(truck, new THREE.CylinderGeometry(1.25, 1.25, 6, 24), tankMat, -1.4, 2.6, 0); tankT.rotation.z = Math.PI / 2;
    add(truck, new THREE.CylinderGeometry(1.28, 1.28, 0.3, 24), mat.orange, -1.4, 2.6, 0).rotation.z = Math.PI / 2;
    for (const x of [-3.2, -1.6, 3.8]) for (const z of [-1.2, 1.2]) add(truck, new THREE.CylinderGeometry(0.6, 0.6, 0.4, 16), mat.dark, x, 0.6, z).rotation.x = Math.PI / 2;
    for (const z of [-0.8, 0.8]) add(truck, new THREE.BoxGeometry(0.08, 0.3, 0.45), glow(0xfff4dc), 5.25, 1.5, z);
    const truckBeacon = add(truck, new THREE.SphereGeometry(0.18, 8, 6), glow(0xffa020), 4, 3.75, 0);
    const fuelRoute = new THREE.CatmullRomCurve3([V(27, 0, 16), V(44, 0, 6), V(60, 0, -22), V(69, 0, -43)]);
    const truckDriver = worker(); desert.add(truckDriver);
    function truckFrame(C) {
        const w = (C / 40) % 1; let f, back = false;
        if (w < 0.3) f = ease(w / 0.3); else if (w < 0.55) f = 1; else if (w < 0.85) { f = 1 - ease((w - 0.55) / 0.3); back = true; } else f = 0;
        const p = fuelRoute.getPointAt(f), tgn = fuelRoute.getTangentAt(Math.min(0.999, Math.max(0.001, f))); if (back) tgn.negate();
        truck.position.set(p.x, hgt(p.x, p.z) + 0.4, p.z); if (f > 0 && f < 1) truck.rotation.y = Math.atan2(-tgn.z, tgn.x); else if (f === 0) truck.rotation.y = -0.6;
        truckBeacon.visible = f > 0 && f < 1 && Math.floor(C * 3) % 2 === 0;
        const at = f === 1; truckDriver.visible = at;
        if (at) { truck.updateMatrixWorld(); const q = truck.localToWorld(V(-1.4, 0, 2.3)); truckDriver.position.set(q.x, truck.position.y, q.z); truckDriver.userData.baseY = truck.position.y; face(truckDriver, 1, 0.5); pose(truckDriver, C, false, false, false); truckDriver.userData.armR.rotation.z = 1.1; }
    }
    const truckLogo = new THREE.Mesh(new THREE.PlaneGeometry(1.6, 1.6), logoMat); truckLogo.position.set(-1.4, 2.6, 1.3); truck.add(truckLogo);
    // forklift shuttling a pallet of barrels
    const fork = new THREE.Group(); desert.add(fork);
    add(fork, rbox(2.6, 1, 1.6, 0.15), mat.orange, 0, 0.9, 0); add(fork, new THREE.BoxGeometry(1.2, 1.4, 1.4), mat.glass, -0.3, 2, 0);
    for (const z of [-0.6, 0.6]) add(fork, new THREE.BoxGeometry(0.12, 3, 0.12), mat.dark, 1.4, 1.9, z);
    const forkLoad = new THREE.Group(); forkLoad.position.set(2.3, 0.5, 0); fork.add(forkLoad);
    add(forkLoad, new THREE.BoxGeometry(1.8, 0.15, 1.4), mat.dark, 0, 0, 0);
    const barrelM = [new THREE.MeshStandardMaterial({ color: 0x2f5d8a, metalness: 0.4, roughness: 0.5 }), new THREE.MeshStandardMaterial({ color: 0xc8612a, metalness: 0.4, roughness: 0.5 })];
    for (const [x, z] of [[-0.4, -0.35], [0.4, -0.35], [-0.4, 0.35], [0.4, 0.35]]) add(forkLoad, new THREE.CylinderGeometry(0.32, 0.32, 0.95, 14), barrelM[(x > 0) ^ (z > 0) ? 1 : 0], x, 0.55, z);
    for (const x of [-0.9, 0.9]) for (const z of [-0.7, 0.7]) add(fork, new THREE.CylinderGeometry(0.35, 0.35, 0.3, 12), mat.dark, x, 0.35, z).rotation.x = Math.PI / 2;
    for (let i = 0; i < 14; i++) add(desert, new THREE.CylinderGeometry(0.32, 0.32, 0.95, 14), barrelM[i % 2], -35 + (i % 5) * 0.72, 0.48, 14 + Math.floor(i / 5) * 0.72);
    // light masts round the pad (their lamps come on after dark)
    const mastLights = [];
    for (const a of [0, 1.57, 3.14, 4.71]) {
        const g = new THREE.Group(); g.position.set(Math.cos(a) * 31, 0, Math.sin(a) * 31); g.rotation.y = -a + Math.PI; desert.add(g);
        add(g, new THREE.CylinderGeometry(0.18, 0.28, 12, 8), mat.dark, 0, 6, 0); add(g, new THREE.BoxGeometry(0.5, 0.8, 2.4), mat.dark, 0.3, 12.2, 0);
        add(g, new THREE.BoxGeometry(0.06, 0.6, 2.2), new THREE.MeshBasicMaterial({ color: 0xfff4dc }), -0.02, 12.2, 0);
        mastLights.push(V(Math.cos(a) * 21, 0, Math.sin(a) * 21));
    }
    // solar field by the habitat
    const solarC = canvas(128), sc2 = solarC.getContext('2d'); sc2.fillStyle = '#132b4a'; sc2.fillRect(0, 0, 128, 128); sc2.strokeStyle = '#6a8aaa'; for (let q = 0; q < 128; q += 16) { sc2.strokeRect(q, 0, 16, 128); sc2.beginPath(); sc2.moveTo(0, q); sc2.lineTo(128, q); sc2.stroke(); }
    const solarM = new THREE.MeshStandardMaterial({ map: tex(solarC, 3, 2), metalness: 0.7, roughness: 0.25 });
    for (let r = 0; r < 4; r++) {
        for (let q = 0; q < 6; q++) {
            const g = new THREE.Group(); g.position.set(-86 + q * 5.2, 0, -12 - r * 5.5); desert.add(g);
            add(g, new THREE.CylinderGeometry(0.1, 0.1, 1.6, 6), mat.steel, 0, 0.8, 0); const pnl = add(g, new THREE.BoxGeometry(4.6, 0.1, 2.8), solarM, 0, 1.7, 0); pnl.rotation.x = -0.5;
        }
    }
    // spaceport sign
    const signC = canvas(1024, 320), sgn = signC.getContext('2d'); sgn.fillStyle = '#14161a'; sgn.fillRect(0, 0, 1024, 320);
    sgn.drawImage(logoCanvas(256), 24, 32, 256, 256); sgn.fillStyle = '#e9e6de'; sgn.font = '700 110px "Share Tech Mono", sans-serif'; sgn.fillText('SPACEPORT', 300, 170);
    sgn.fillStyle = '#e8813a'; sgn.font = '500 44px "Share Tech Mono", monospace'; sgn.fillText('PAD 01 · CARGO OPERATIONS', 304, 250); sgn.fillRect(0, 300, 1024, 20);
    const sign = new THREE.Group(); sign.position.set(-30, 0, -34); sign.rotation.y = 0.45; desert.add(sign);
    add(sign, new THREE.BoxGeometry(13, 4.2, 0.3), mat.dark, 0, 6, 0); const signFace = new THREE.Mesh(new THREE.PlaneGeometry(12.6, 3.9), new THREE.MeshBasicMaterial({ map: tex(signC) })); signFace.position.set(0, 6, 0.16); sign.add(signFace);
    for (const x of [-5, 5]) add(sign, new THREE.BoxGeometry(0.4, 4, 0.4), mat.dark, x, 2, 0);
    function baseFrame(C, u) {
        const prep = u < 0, cyc = (C / 6) % 1;
        let tgt, carrying;
        const liftArc = (a, b, f) => a.clone().lerp(b, f).add(V(0, Math.sin(f * Math.PI) * 3, 0));
        const pick = V(PALLET.x, 2.4, PALLET.z);
        if (!prep) { tgt = V(10, 6, 13); carrying = false; }
        else if (cyc < 0.35) { tgt = liftArc(pick, POD, ease(cyc / 0.35)); carrying = true; }
        else if (cyc < 0.5) { tgt = POD.clone(); carrying = cyc < 0.42; }
        else if (cyc < 0.85) { tgt = liftArc(POD, pick, ease((cyc - 0.5) / 0.35)); carrying = false; }
        else { tgt = pick.clone(); carrying = cyc > 0.93; }
        ik(tgt); armLamp.visible = Math.floor(C * 2) % 2 === 0;
        heldCrate.visible = carrying; if (carrying) { wrist.updateMatrixWorld(); wrist.localToWorld(wp.set(0, -1.1, 0)); heldCrate.position.copy(wp); heldCrate.rotation.set(0, yawG.rotation.y, 0); }
        face(operator, -0.6, -1); pose(operator, C, false, false, false); operator.userData.armR.rotation.z = 0.9; operator.userData.foR.rotation.z = 1.2;
        const fp = (C * 0.09) % 1, ff = ease(fp < 0.5 ? fp * 2 : 2 - fp * 2), fa = V(-36, 0.4, 6), fb = V(-26, 0.4, 20);
        fork.position.copy(fa).lerp(fb, ff); fork.rotation.y = Math.atan2(-(fb.z - fa.z), fb.x - fa.x) + (fp < 0.5 ? 0 : Math.PI);
        forkLoad.position.y = 0.5 + (fp > 0.45 && fp < 0.55 ? 0 : 0.6); forkLoad.visible = fp < 0.5;
    }
    function bgFrame(C) {
        bgShips.forEach(({ sh, idle, G, Tp, boxes, pile, bcrew, n }) => {
            const rd = sh.getObjectByName('radar'); if (rd) rd.rotation.y = C * 1.5 + n;
            idle.forEach((m) => { m.uniforms.uK.value = 0.5 + Math.sin(C * 9 + n) * 0.1; m.uniforms.uT.value = C; });
            boxes.forEach((c, q) => { const t = (C * 0.09 + q / 5 + n * 0.13) % 1; c.position.copy(G).lerp(Tp, t); c.position.y += 0.5; c.visible = t < 0.97; });
            for (let q = 0; q < 2; q++) {
                const w = (C / 6 + q * 0.5 + n * 0.3) % 1, out = w < 0.5, f = ease(out ? w * 2 : 2 - w * 2);
                const a = pile.clone().add(V(0.6 + q * 0.8, 0, -1.2)), b = G.clone().add(V(1.1 - q * 2.2, 0, 1)), p = a.lerp(b, f);
                const wk = bcrew[q]; wk.position.copy(p); wk.userData.baseY = p.y; face(wk, (b.x - a.x) * (out ? 1 : -1), (b.z - a.z) * (out ? 1 : -1)); pose(wk, C + q + n, true, out, false);
            }
            const d = bcrew[2]; d.position.set(-3.6, 2.0, 6.0); d.userData.baseY = 2.0; face(d, 0, 1); pose(d, C, false, false, false); d.userData.armR.rotation.z = 1 + Math.sin(C * 2 + n) * 0.5;
            const d2 = bcrew[3]; d2.position.set(-2.2, 2.0, 5.9); d2.userData.baseY = 2.0; face(d2, -0.3, 1); pose(d2, C, false, Math.sin(C * 0.6 + n) > 0, false);
            const c = bcrew[4], x = -2 + Math.sin(C * 0.3 + n * 2) * 9, dir = Math.cos(C * 0.3 + n * 2);
            c.position.set(x, -4.7, 10.5); c.userData.baseY = -4.7; face(c, dir, 0); pose(c, C + n, true, false, false); c.userData.armR.rotation.z = 1.1;
        });
    }
    const drone = new THREE.Group(); add(drone, new THREE.BoxGeometry(0.8, 0.3, 0.8), mat.dark); for (const [x, z] of [[-0.6, -0.6], [0.6, -0.6], [-0.6, 0.6], [0.6, 0.6]]) add(drone, new THREE.CylinderGeometry(0.35, 0.35, 0.05, 12), mat.steel, x, 0.2, z);
    const droneLight = add(drone, new THREE.SphereGeometry(0.1, 6, 4), navMat(0xff3b30), 0, -0.2, 0); desert.add(drone);
    // welding sparks
    const SPARKS = 40, sparkSpots = [V(1.9, 3.1, 5.7), V(-5.2, 3.3, 5.7), V(-9.5, 7.6, 4.7)];
    const sparkGeo = new THREE.BufferGeometry(); sparkGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(SPARKS * 3 * 3), 3));
    const sparks = new THREE.Points(sparkGeo, new THREE.PointsMaterial({ color: 0xffd9a0, size: 0.14, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    desert.add(sparks);
    const arcLights = sparkSpots.map((p) => { const l = new THREE.PointLight(0x9fd0ff, 0, 10, 2); l.position.copy(p).add(V(0, 0, 0.6)); desert.add(l); return l; });
    // dust
    const DUST = 420, dustGeo = pointsGeo(DUST);
    const dust = new THREE.Points(dustGeo, softPoints('#cfae84', THREE.NormalBlending)); dust.frustumCulled = false; desert.add(dust);
    const sand = new THREE.Points(sandGeo, softPoints('#e2c49a', THREE.NormalBlending)); sand.frustumCulled = false; desert.add(sand);
    // ---- LSX factory: where the cargo is built, with a road out to the ships -----------------------------------
    const FC = V(0, 0, -118), FW = 64, FD = 34, FH = 16, DOORW = 22, DOORH = 12;
    const factory = new THREE.Group(); factory.position.copy(FC); desert.add(factory);
    const wallM = new THREE.MeshStandardMaterial({ color: 0xb9b6ae, map: tex(ribC, 6, 1), bumpMap: tex(ribC, 6, 1, false), bumpScale: 0.05, metalness: 0.5, roughness: 0.55 });
    const floorM = new THREE.MeshStandardMaterial({ color: 0x8e8a82, roughness: 0.85 });
    add(factory, new THREE.BoxGeometry(FW, 0.4, FD), floorM, 0, 0.2, 0);
    add(factory, new THREE.BoxGeometry(FW, FH, 0.6), wallM, 0, FH / 2, -FD / 2);
    for (const x of [-FW / 2, FW / 2]) add(factory, new THREE.BoxGeometry(0.6, FH, FD), wallM, x, FH / 2, 0);
    const sideW = (FW - DOORW) / 2; for (const s of [-1, 1]) add(factory, new THREE.BoxGeometry(sideW, FH, 0.6), wallM, s * (DOORW / 2 + sideW / 2), FH / 2, FD / 2);
    add(factory, new THREE.BoxGeometry(DOORW, FH - DOORH, 0.6), wallM, 0, DOORH + (FH - DOORH) / 2, FD / 2);
    add(factory, new THREE.BoxGeometry(DOORW, 1.2, 0.8), mat.dark, 0, DOORH + 0.6, FD / 2 + 0.2);   // rolled-up door drum
    for (const x of [-DOORW / 2, DOORW / 2]) add(factory, new THREE.BoxGeometry(0.5, DOORH, 0.9), mat.hazard, x, DOORH / 2, FD / 2 + 0.1);
    // sawtooth roof with north-light glazing
    const glassRoof = new THREE.MeshStandardMaterial({ color: 0x9fc4dc, metalness: 0.3, roughness: 0.1, transparent: true, opacity: 0.55 });
    for (let q = 0; q < 6; q++) {
        const z = -FD / 2 + 2.8 + q * 5.7;
        const slope = add(factory, new THREE.BoxGeometry(FW, 0.3, 6.3), wallM, 0, FH + 1.4, z + 0.3); slope.rotation.x = -0.45;
        const glz = add(factory, new THREE.BoxGeometry(FW - 1, 2.8, 0.15), glassRoof, 0, FH + 1.4, z + 3.0); glz.castShadow = false;
    }
    // stripe and sign
    add(factory, new THREE.BoxGeometry(FW + 0.2, 0.8, 0.2), mat.orange, 0, 3.2, -FD / 2 - 0.35);
    for (const s of [-1, 1]) { add(factory, new THREE.BoxGeometry(0.2, 0.8, FD + 0.2), mat.orange, s * (FW / 2 + 0.35), 3.2, 0); add(factory, new THREE.BoxGeometry(sideW, 0.8, 0.2), mat.orange, s * (DOORW / 2 + sideW / 2), 3.2, FD / 2 + 0.35); }
    const fsC = canvas(1024, 200), fsg = fsC.getContext('2d'); fsg.fillStyle = '#14161a'; fsg.fillRect(0, 0, 1024, 200); fsg.drawImage(logoCanvas(170), 16, 15, 170, 170);
    fsg.fillStyle = '#e9e6de'; fsg.font = '700 96px "Share Tech Mono", sans-serif'; fsg.fillText('LSX FACTORY', 206, 120); fsg.fillStyle = '#e8813a'; fsg.font = '500 34px "Share Tech Mono", monospace'; fsg.fillText('CARGO WORKS · BAY 1', 210, 172);
    const fSign = new THREE.Mesh(new THREE.PlaneGeometry(20, 3.9), new THREE.MeshBasicMaterial({ map: tex(fsC) })); fSign.position.set(-FW / 4 - 4, 12.2, FD / 2 + 0.35); factory.add(fSign);
    // inside: bright ceiling lights, a conveyor with crates, two robot arms, a gantry crane, racks and crew
    const ceilM = new THREE.MeshBasicMaterial({ color: 0xfff4dc });
    for (let i = 0; i < 5; i++) for (let j = 0; j < 3; j++) add(factory, new THREE.BoxGeometry(5, 0.15, 0.8), ceilM, -22 + i * 11, FH - 0.4, -9 + j * 9);
    const inLight = new THREE.PointLight(0xfff0d8, 1.6, 70, 1.6); inLight.position.set(0, FH - 3, 0); factory.add(inLight);
    const beltY = 1.3, beltZ = -3; add(factory, new THREE.BoxGeometry(46, 0.25, 2.2), mat.dark, -2, beltY, beltZ);
    for (let x = -24; x <= 20; x += 4) { add(factory, new THREE.BoxGeometry(0.2, beltY, 0.2), mat.steel, x, beltY / 2, beltZ - 1); add(factory, new THREE.BoxGeometry(0.2, beltY, 0.2), mat.steel, x, beltY / 2, beltZ + 1); }
    for (const s of [-1, 1]) add(factory, new THREE.BoxGeometry(46, 0.35, 0.12), mat.hazard, -2, beltY + 0.2, beltZ + s * 1.12);
    const beltCrates = Array.from({ length: 9 }, (_, i) => add(factory, cgeo, i % 3 ? crateMat : mat.hullB));
    const rArms = [-10, 6].map((x, n) => {
        const base = new THREE.Group(); base.position.set(x, 0.4, beltZ - 3.2); factory.add(base);
        add(base, new THREE.CylinderGeometry(0.9, 1.1, 0.8, 16), mat.orange, 0, 0.4, 0); const yaw = new THREE.Group(); yaw.position.y = 0.8; base.add(yaw);
        const s1 = new THREE.Group(); yaw.add(s1); add(s1, new THREE.BoxGeometry(0.5, 3, 0.5), mat.orange, 0, 1.5, 0);
        const s2 = new THREE.Group(); s2.position.y = 3; s1.add(s2); add(s2, new THREE.BoxGeometry(0.4, 2.6, 0.4), mat.orange, 0, 1.3, 0); add(s2, new THREE.SphereGeometry(0.35, 10, 8), mat.dark);
        add(s2, new THREE.BoxGeometry(0.6, 0.3, 0.6), mat.dark, 0, 2.7, 0); const spark = add(s2, new THREE.SphereGeometry(0.18, 8, 6), glow(0x9fd0ff), 0, 2.95, 0); return { yaw, s1, s2, spark, n };
    });
    const gantry = new THREE.Group(); factory.add(gantry); add(gantry, new THREE.BoxGeometry(1, 1, FD - 2), mat.hazard, 0, FH - 2, 0);
    for (const z of [-FD / 2 + 1, FD / 2 - 1]) add(factory, new THREE.BoxGeometry(FW - 2, 0.6, 0.6), mat.dark, 0, FH - 2.2, z);
    const hook = add(gantry, new THREE.BoxGeometry(1.4, 0.6, 1.4), mat.dark, 0, FH - 5, 4); const hookLine = add(gantry, new THREE.CylinderGeometry(0.05, 0.05, 2.4, 4), mat.dark, 0, FH - 3.6, 4);
    const hookCrate = add(gantry, cgeo, crateMat, 0, FH - 5.9, 4); hookCrate.scale.setScalar(1.6);
    for (let r = 0; r < 4; r++) {
        const x = -26 + r * 7; add(factory, new THREE.BoxGeometry(6, 7, 0.2), mat.dark, x, 3.5, -FD / 2 + 2.2);
        for (let lv = 0; lv < 3; lv++) { add(factory, new THREE.BoxGeometry(6, 0.15, 2), mat.orange, x, 0.8 + lv * 2.4, -FD / 2 + 3); for (let c = 0; c < 3; c++) if (rnd(r * 9 + lv * 3 + c + 900) > 0.25) add(factory, cgeo, crateMat, x - 2 + c * 2, 1.4 + lv * 2.4, -FD / 2 + 3); }
    }
    const fCrew = Array.from({ length: 5 }, () => { const w = worker(); factory.add(w); return w; });
    // outside: the loading apron, a chimney venting steam, a perimeter fence and the cargo hauler that runs to the pads
    add(factory, new THREE.BoxGeometry(34, 0.3, 14), floorM, 0, 0.15, FD / 2 + 7);
    add(factory, new THREE.CylinderGeometry(1.4, 1.8, 26, 18), mat.hullB, FW / 2 - 6, 13, -FD / 2 + 5); add(factory, new THREE.CylinderGeometry(1.5, 1.5, 1, 18), mat.orange, FW / 2 - 6, 24, -FD / 2 + 5);
    const stackLamp = add(factory, new THREE.SphereGeometry(0.3, 8, 6), glow(0xff3b30), FW / 2 - 6, 26.3, -FD / 2 + 5);
    for (let i = 0; i < 28; i++) { const a = i / 28 * Math.PI * 2, x = Math.cos(a) * (FW / 2 + 12), z = Math.sin(a) * (FD / 2 + 12); if (z > FD / 2 && Math.abs(x) < 20) continue; add(factory, new THREE.BoxGeometry(0.15, 2.2, 0.15), mat.steel, x, 1.1, z); }
    const STM = 60, stmGeo = pointsGeo(STM);
    const stm = new THREE.Points(stmGeo, softPoints('#e9e6e0', THREE.NormalBlending)); stm.frustumCulled = false; desert.add(stm);
    const hauler = new THREE.Group(); desert.add(hauler);
    add(hauler, rbox(7, 0.5, 2.6, 0.1), mat.dark, 0, 1, 0); add(hauler, rbox(2, 2.2, 2.6, 0.25), mat.orange, 2.7, 2.2, 0); add(hauler, new THREE.BoxGeometry(0.1, 0.9, 2.2), mat.glass, 3.71, 2.6, 0);
    for (const x of [-2.4, 0, 2.6]) for (const z of [-1.2, 1.2]) add(hauler, new THREE.CylinderGeometry(0.55, 0.55, 0.4, 14), mat.dark, x, 0.55, z).rotation.x = Math.PI / 2;
    for (const z of [-0.8, 0.8]) add(hauler, new THREE.BoxGeometry(0.08, 0.3, 0.4), glow(0xfff4dc), 3.75, 1.4, z);
    const haulLoad = [[-2.2, -0.6], [-2.2, 0.6], [-0.9, -0.6], [-0.9, 0.6], [-1.55, 0]].map(([x, z], i) => add(hauler, cgeo, crateMat, x, 1.75 + (i === 4 ? 1 : 0), z));
    const haulBeacon = add(hauler, new THREE.SphereGeometry(0.16, 8, 6), glow(0xffa020), 2.7, 3.45, 0);
    const haulRoute = new THREE.CatmullRomCurve3([V(0, 0, -98), V(2, 0, -70), V(-2, 0, -48), V(-6, 0, -31)]);
    function factoryFrame(C) {
        for (let i = 0; i < beltCrates.length; i++) { const f = ((C * 0.06 + i / beltCrates.length) % 1); beltCrates[i].position.set(-24 + f * 44, beltY + 0.62, beltZ); beltCrates[i].visible = f < 0.97; }
        rArms.forEach(({ yaw, s1, s2, spark, n }) => { const t = C * 1.3 + n * 2; yaw.rotation.y = Math.sin(t * 0.7) * 0.5; s1.rotation.z = -0.5 + Math.sin(t) * 0.25; s2.rotation.z = -1.3 + Math.sin(t * 1.3 + 1) * 0.3; spark.visible = Math.floor(t * 4) % 3 !== 0; });
        gantry.position.x = Math.sin(C * 0.2) * 22; hook.position.y = FH - 5 - (Math.sin(C * 0.4) * 0.5 + 0.5) * 4; hookLine.scale.y = 1 + (FH - 5 - hook.position.y) / 2.4; hookLine.position.y = (FH - 2 + hook.position.y) / 2 + 0.3; hookCrate.position.y = hook.position.y - 0.9;
        fCrew.forEach((w, i) => {
            let p, d = V(0, 0, 1), walk = false, weld = false, carry = false;
            if (i < 2) { p = V(-10 + i * 16, 0.4, beltZ + 2.2); d = V(0, 0, -1); weld = true; }
            else if (i === 2) { const f = (C * 0.05) % 1, x = -20 + Math.abs(f * 2 - 1) * 36; p = V(x, 0.4, beltZ + 5); d = V(f < 0.5 ? 1 : -1, 0, 0); walk = true; }
            else { const f = ((C * 0.07 + i * 0.4) % 1), a = V(-24 + i * 3, 0.4, -FD / 2 + 5.5), b = V(-6 + i * 3, 0.4, FD / 2 + 4), out = f < 0.5; p = a.clone().lerp(b, ease(out ? f * 2 : 2 - f * 2)); d = (out ? b.clone().sub(a) : a.clone().sub(b)); walk = true; carry = out; }
            w.position.copy(p); w.userData.baseY = 0.4; face(w, d.x, d.z); pose(w, C * 1.2 + i, walk, carry, weld);
        });
        stackLamp.visible = Math.floor(C * 1.4) % 2 === 0;
        const sp = stmGeo.attributes.position, sa = stmGeo.attributes.aA, ss = stmGeo.attributes.aS;
        for (let i = 0; i < STM; i++) { const age = (C * 0.25 + rnd(i + 8000)) % 1; sp.setXYZ(i, FC.x + FW / 2 - 6 + age * 9 + Math.sin(age * 5 + i) * age * 2, 26 + age * 18, FC.z - FD / 2 + 5 + (rnd(i + 8001) - 0.5) * age * 6); sa.setX(i, (1 - age) * 0.5); ss.setX(i, 3 + age * 14); }
        sp.needsUpdate = sa.needsUpdate = ss.needsUpdate = true;
        // the hauler: loads at the factory, drives to the pad, drops its cargo by the crate pile, drives back empty
        const w = (C / 26) % 1; let f, back = false;
        if (w < 0.15) f = 0; else if (w < 0.45) f = ease((w - 0.15) / 0.3); else if (w < 0.6) f = 1; else if (w < 0.9) { f = 1 - ease((w - 0.6) / 0.3); back = true; } else f = 0;
        const p = haulRoute.getPointAt(f), tgn = haulRoute.getTangentAt(Math.min(0.999, Math.max(0.001, f))); if (back) tgn.negate();
        hauler.position.set(p.x, hgt(p.x, p.z) + 0.1, p.z); hauler.rotation.y = Math.atan2(-tgn.z, tgn.x); haulLoad.forEach((c) => { c.visible = w < 0.52 || w >= 0.95; }); haulBeacon.visible = f > 0 && f < 1 && Math.floor(C * 3) % 2 === 0;
    }
    // roads: factory to Pad 01, and on to both idle pads, laid on the ground
    const roadMat = new THREE.MeshStandardMaterial({ color: 0x3b3834, roughness: 0.95 }), lineMat = new THREE.MeshBasicMaterial({ color: 0xe8b04a });
    const road = (pts, wdt = 7) => {
        const cur = new THREE.CatmullRomCurve3(pts.map(([x, z]) => V(x, 0, z))), N = 60, pos = [], ix = [];
        for (let i = 0; i <= N; i++) {
            const p = cur.getPointAt(i / N), t = cur.getTangentAt(i / N), s = V(-t.z, 0, t.x).normalize();
            for (const q of [-1, 1]) { const pt = p.clone().addScaledVector(s, q * wdt / 2); pos.push(pt.x, hgt(pt.x, pt.z) + 0.12, pt.z); }
            if (i < N) { const a = i * 2; ix.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
        }
        const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setIndex(ix); g.computeVertexNormals();
        const m = new THREE.Mesh(g, roadMat); m.receiveShadow = true; desert.add(m);
        for (let i = 0; i < N; i += 2) { const p = cur.getPointAt((i + 0.5) / N); const dsh = add(desert, new THREE.BoxGeometry(0.25, 0.04, 1.6), lineMat, p.x, hgt(p.x, p.z) + 0.16, p.z); const t = cur.getTangentAt((i + 0.5) / N); dsh.rotation.y = Math.atan2(t.x, t.z); }
    };
    road([[0, -99], [2, -70], [-2, -48], [-6, -27]]); road([[-26, -99], [-50, -92], [-74, -80]]); road([[26, -99], [50, -90], [68, -76]]);

    // clouds and take-off effects
    for (let i = 0; i < 34; i++) {
        const sp = new THREE.Sprite(cloudMat(0.75, 0xfff4e8)), sc = 30 + rnd(i + 820) * 50;
        sp.position.set((rnd(i + 821) - 0.5) * 200, 55 + rnd(i + 822) * 50, (rnd(i + 823) - 0.5) * 200 + 20); sp.scale.set(sc, sc * 0.6, 1); desert.add(sp);
    }
    for (let i = 0; i < 14; i++) {
        const sp = new THREE.Sprite(cloudMat(0.35, 0xfff0e0)), sc = 300 + rnd(i + 840) * 400;
        sp.position.set((rnd(i + 841) - 0.5) * 2400, 380 + rnd(i + 842) * 250, -900 - rnd(i + 843) * 700); sp.scale.set(sc, sc * 0.25, 1); desert.add(sp);
    }
    const rings = [0, 1].map(() => {
        const m = new THREE.Mesh(new THREE.RingGeometry(0.8, 1, 64), new THREE.MeshBasicMaterial({ color: 0xd8bc94, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide }));
        m.rotation.x = -Math.PI / 2; m.position.y = 0.6; desert.add(m); return m;
    });
    const scorchGlow = new THREE.Mesh(new THREE.CircleGeometry(12, 40), new THREE.MeshBasicMaterial({ map: glowTex, color: 0xff7a2a, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false }));
    scorchGlow.rotation.x = -Math.PI / 2; scorchGlow.position.y = 0.46; desert.add(scorchGlow);
    const beacons = [0.8, 2.4, 3.9, 5.5].map((a) => {
        const g = new THREE.Group(); g.position.set(Math.cos(a) * 27.5, 0, Math.sin(a) * 27.5); desert.add(g);
        add(g, new THREE.CylinderGeometry(0.35, 0.45, 1.2, 12), mat.dark, 0, 0.6, 0); const bulb = add(g, new THREE.SphereGeometry(0.32, 10, 8), new THREE.MeshBasicMaterial({ color: 0x4a3008 }), 0, 1.35, 0);
        const beam = new THREE.Mesh(new THREE.ConeGeometry(0.9, 9, 20, 1, true), new THREE.MeshBasicMaterial({ color: 0xffb030, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
        beam.geometry.translate(0, -4.5, 0); beam.rotation.z = Math.PI / 2; const spin = new THREE.Group(); spin.position.y = 1.35; spin.add(beam); g.add(spin); return { bulb, beam, spin };
    });
    const RCS = 64, rcsGeo = pointsGeo(RCS);
    const rcs = new THREE.Points(rcsGeo, softPoints('#f4f6fa', THREE.NormalBlending)); rcs.frustumCulled = false; desert.add(rcs);
    const RCS_AT = [[19, 6, 3.6, 1], [19, 6, -3.6, -1], [-20, 9, 5.6, 1], [-20, 9, -5.6, -1]];
    // after landing the engines cool: bells glow down from orange and vent steam for a few seconds
    const STEAM = 60, steamGeo = pointsGeo(STEAM);
    const steam = new THREE.Points(steamGeo, softPoints('#eef0f2', THREE.NormalBlending)); steam.frustumCulled = false; desert.add(steam);
    const ventAt = flames.map((f) => f.glow);
    // dust devils: small whirlwinds wandering across the open desert, well away from the pads
    const DEV = 3, DEVP = 110, devGeo = pointsGeo(DEV * DEVP);
    const devils = new THREE.Points(devGeo, softPoints('#d2b48a', THREE.NormalBlending)); devils.frustumCulled = false; desert.add(devils);
    function devilFx(C) {
        const p = devGeo.attributes.position, a = devGeo.attributes.aA, sz = devGeo.attributes.aS;
        for (let d = 0; d < DEV; d++) {
            const life = (C / 19 + d / DEV) % 1, fade = Math.sin(life * Math.PI), ang = d * 2.1 + 0.6, r0 = 60 + d * 25;
            const cx = Math.cos(ang) * r0 + (life - 0.5) * 60 * Math.cos(ang + 1.6), cz = Math.sin(ang) * r0 + (life - 0.5) * 60 * Math.sin(ang + 1.6), cy = hgt(cx, cz);
            for (let i = 0; i < DEVP; i++) {
                const q = d * DEVP + i, h = (rnd(q + 4000) + C * 0.35) % 1, spn = C * (5 + rnd(q + 4001) * 3) + rnd(q + 4002) * 6.3, rad = 0.4 + h * h * 5 + Math.sin(C * 2 + d) * 0.3 * h;
                p.setXYZ(q, cx + Math.cos(spn) * rad + Math.sin(C * 1.3 + h * 4) * h * 1.5, cy + h * 16, cz + Math.sin(spn) * rad); a.setX(q, fade * (1 - h) * 0.42); sz.setX(q, 1.5 + h * 5);
            }
        }
        p.needsUpdate = a.needsUpdate = sz.needsUpdate = true;
    }
    function coolFx(T, C) {
        const cool = T >= 45.6 ? 1 - clamp((T - 45.6) / 6.4) : 0;
        if (cool > 0) { const c = heatMat.color; c.setRGB(Math.max(c.r, 0.2 + cool * 0.7), Math.max(c.g, 0.05 + cool * 0.22), Math.max(c.b, 0.01 + cool * 0.03)); }
        steam.visible = cool > 0;
        if (!steam.visible) return;
        const sp = steamGeo.attributes.position, sa = steamGeo.attributes.aA, ss = steamGeo.attributes.aS, w = V();
        for (let i = 0; i < STEAM; i++) {
            const age = (C * 0.8 + rnd(i + 3000)) % 1; ventAt[i % ventAt.length].getWorldPosition(w);
            sp.setXYZ(i, w.x + (rnd(i + 3001) - 0.5) * 2 + age * 1.5, w.y + age * 6, w.z + (rnd(i + 3002) - 0.5) * 2); sa.setX(i, cool * (1 - age) * 0.75); ss.setX(i, 2.5 + age * 9);
        }
        sp.needsUpdate = sa.needsUpdate = ss.needsUpdate = true;
    }
    function takeoffFx(T, C, u, lift) {
        const warn = (T >= 10.6 && T < 15.5) || (T >= 39.5 && T < 46.5);
        beacons.forEach((b, i) => { b.spin.rotation.y = C * 5 + i; b.beam.material.opacity = warn ? 0.13 : 0; b.bulb.material.color.setHex(warn ? 0xffb030 : 0x4a3008); });
        rings.forEach((r, i) => { const q = u < 0 ? 0 : clamp((u - 0.1 - i * 0.14) / 0.5), rad = 6 + q * 90; r.scale.set(rad, rad, 1); r.material.opacity = q > 0 && q < 1 ? (1 - q) * 0.45 : 0; });
        mainAO.material.opacity = 0.55 * (1 - clamp(lift * 4));
        scorchGlow.material.opacity = u < 0 ? 0 : clamp(u / 0.15) * (1 - clamp(lift * 2)) * 0.9;
        ship.updateMatrixWorld();
        const rp = rcsGeo.attributes.position, ra = rcsGeo.attributes.aA, rs = rcsGeo.attributes.aS, on = u > 0.15 && u < 0.75;
        rcs.visible = on;
        if (!on) return;
        for (let i = 0; i < RCS; i++) {
            const [x, y, z, sd] = RCS_AT[i % 4], age = (C * 3 + rnd(i)) % 1, q = ship.localToWorld(V(x, y, z + sd * age * 4));
            rp.setXYZ(i, q.x, q.y + age * 1.5, q.z); ra.setX(i, Math.floor(C * 4 + (i % 4)) % 3 === 0 ? (1 - age) * 0.7 : 0); rs.setX(i, 0.8 + age * 3.5);
        }
        rp.needsUpdate = ra.needsUpdate = rs.needsUpdate = true;
    }

    // ---- the trip at the base -------------------------------------------------------------------------------------
    // ship phase: -1 loading, 0..1 take-off, 1 away, 1..0 landing, 0 settled
    const baseU = (T) => (T < 12 ? -1 : T < 15.5 ? (T - 12) / 3.5 : T < 41 ? 1 : T < 46 ? 1 - (T - 41) / 5 : 0);
    const CARRY_A = V(-27.5, 0.4, 9.6), CARRY_B = V(-18.6, 0.4, 0), CARRY_C = V(-12.8, 5.3, 0);
    function carrier(t, q) {   // crates up the ramp: walk out with one, set it down, come back for the next
        const w = (t / 7 + q / 3) % 1, z = (q - 1) * 0.9;
        const a = CARRY_A.clone().add(V(q * 0.8, 0, 0)), b = CARRY_B.clone().setZ(z), c = CARRY_C.clone().setZ(z);
        if (w < 0.42) { const f = w / 0.42; return { p: a.lerp(b, f), d: b.clone().sub(CARRY_A), carry: true, walk: true }; }
        if (w < 0.55) { const f = (w - 0.42) / 0.13; return { p: b.clone().lerp(c, f), d: c.clone().sub(b), carry: true, walk: true }; }
        if (w < 0.62) return { p: c, d: V(1, 0, 0), carry: false, walk: false };
        if (w < 0.72) { const f = (w - 0.62) / 0.1; return { p: c.clone().lerp(b, f), d: b.clone().sub(c), carry: false, walk: true }; }
        const f = (w - 0.72) / 0.28; return { p: b.clone().lerp(a, f), d: a.clone().sub(b), carry: false, walk: true };
    }
    const STATIC = [[V(1.5, 0.4, 7.0), Math.PI / 2], [V(-5.5, 0.4, 7.1), Math.PI / 2], [null, Math.PI / 2], [V(12, 0.4, -4), 2.4]];
    const homeOf = (i) => (i < 3 ? carrier(12, i).p : (STATIC[i - 3][0] || V(-9.5, 0.4, 6.6)));
    const safe = (i) => { const h = homeOf(i), d = V(h.x, 0, h.z).normalize(); return h.clone().addScaledVector(d, 26).setY(0.4); };
    // routine work: what each crew member does when the ship is away, or home with nothing to load
    function task(i, t, shipHome) {
        if (i < 3) {
            const a = V(-28.6 + i * 0.9, 0.4, 10.4), b = V(-36.6, 0.4, 3.6 + i * 1.3), w = (t / 9 + i / 3) % 1, out = w < 0.5, f = ease(out ? w * 2 : 2 - w * 2);
            return { p: a.lerp(b, f), d: out ? b.clone().sub(a) : a.clone().sub(b), walk: true, carry: !out };
        }
        if (i === 3 || i === 4) {   // inspecting: round the empty pad, or round the parked ship
            const a = t * (shipHome ? 0.05 : 0.07) + (i - 3) * Math.PI, stop = Math.floor(t * 0.4 + i) % 3 === 0;
            const rx = shipHome ? 28 + (i - 3) * 3 : 11 + (i - 3) * 4, rz = shipHome ? 11 + (i - 3) * 2 : rx;
            return { p: V(Math.cos(a) * rx, 0.4, Math.sin(a) * rz), d: V(-Math.sin(a) * rx, 0, Math.cos(a) * rz), walk: !stop, crouch: stop };
        }
        if (i === 5) return { p: V(-9.5, 0.4, 9.2), d: V(0, 0, -1), walk: false, look: true };
        const a = V(12, 0.4, -4.6), b = V(20, 0.4, 10), w = (t / 14) % 1, f = ease(w < 0.5 ? w * 2 : 2 - w * 2);
        return { p: a.clone().lerp(b, f), d: w < 0.5 ? b.clone().sub(a) : a.clone().sub(b), walk: w % 0.5 > 0.04 && w % 0.5 < 0.46, look: true };
    }
    function prepSpot(i, C) {   // loading the ship: three carry crates up the ramp, three weld, one stands by
        if (i < 3) return carrier(C, i);
        const [p, ry] = STATIC[i - 3];
        return { p: p ? p.clone() : V(-9.5, 6.3, 6.6), d: V(Math.cos(ry), 0, -Math.sin(ry)), walk: false, carry: false, weld: i - 3 < 3 };
    }
    function frame(T, C, idle, blend = 1) {
        const u = idle ? 0 : baseU(T);
        desertExtras(C); bgFrame(C); baseFrame(C, u); truckFrame(C); factoryFrame(C);
        {
            const HAB = V(-50.5, 0.4, -29.5), PADE = V(-27, 0.4, -15), w = (C / 26) % 1, f = w < 0.4 ? ease(w / 0.4) : w < 0.5 ? 1 : w < 0.9 ? 1 - ease((w - 0.5) / 0.4) : 0;
            shiftW.visible = w < 0.95; shiftW.position.copy(HAB).lerp(PADE, f); shiftW.userData.baseY = 0.4; const out = w < 0.4; face(shiftW, (PADE.x - HAB.x) * (out ? 1 : -1), (PADE.z - HAB.z) * (out ? 1 : -1));
            pose(shiftW, C * 1.2, (w < 0.4 || (w >= 0.5 && w < 0.9)), false, false);
        }
        { const have = u < 0 ? 6 - Math.floor((C % 12) / 2) : idle ? 6 : T < 18 ? 0 : Math.min(6, Math.floor((T - 18) / 3.2)); restock.forEach((c, q) => { c.visible = q < have; }); }
        const lift = u < 0 ? 0 : Math.pow(clamp((u - 0.22) / 0.78), 2.2);
        if (ship.parent !== desert) desert.add(ship);
        ship.scale.setScalar(1); ship.visible = true;
        ship.position.set(0, 5.1 + lift * 190, 0); ship.rotation.set(0, 0, lift * 0.16);
        const gear = u < 0 ? 1 : 1 - clamp((u - 0.35) / 0.3);
        legs.forEach((l, i) => { l.rotation.z = (1 - gear) * (i < 2 ? -1.45 : 1.45); });
        ramp.rotation.z = 0.74 * (u < 0 ? 1 : 1 - clamp(u / 0.15)); hold.visible = ramp.rotation.z > 0.03; cabin.intensity = u < 0 || idle || T >= 47 ? 1.2 : 0;
        const belly = u < 0 ? 0 : clamp(u / 0.18) * (1 - lift * 0.4), rear = clamp((lift - 0.12) * 3);
        thrust(C, rear, belly); coolFx(idle ? 0 : T, C); devilFx(C);
        // crew
        crew.forEach((w, i) => {
            let p, d, walk = false, crouch = false, carry = false, look = false, weld = false;
            if (u < 0) {
                const s = prepSpot(i, C);
                if (blend < 1) {   // walking over from routine work to load the ship
                    const r = task(i, C, true).p, to = i === 5 ? V(-9.5, 0.4, 6.6) : s.p, q = ease(blend);
                    p = r.clone().lerp(to, q); d = to.clone().sub(r); walk = q < 0.98 && d.lengthSq() > 0.01;
                    if (!walk) d = s.d;
                } else { p = s.p; d = s.d; walk = s.walk; carry = s.carry; weld = !!s.weld; }
            } else if (idle) {
                const tk = task(i, C, true); p = tk.p; d = tk.d; walk = tk.walk; crouch = !!tk.crouch; carry = !!tk.carry; look = !!tk.look;
            } else if (T < 15.5) {   // take-off: everyone runs clear and crouches
                const run = clamp(u / 0.55), h = homeOf(i);
                if (i === 5) { w.position.set(-9.5, 5.9 * (1 - clamp(u / 0.2)) + 0.4, 6.6); w.userData.baseY = w.position.y; pose(w, C, false, false, false); return; }
                p = h.clone().lerp(safe(i), run); p.y = 0.4; d = V(h.x, 0, h.z); walk = run < 1; crouch = run >= 1;
            } else if (T < 39) {
                const tk = task(i, C, false), q = clamp((T - 15.5) / 3) * (1 - clamp((T - 37) / 2)), from = safe(i);
                p = from.clone().lerp(tk.p, q); d = q > 0 && q < 1 ? (T < 20 ? tk.p.clone().sub(from) : from.clone().sub(tk.p)) : tk.d;
                walk = (q > 0 && q < 1) || tk.walk; crouch = q >= 1 && tk.crouch; carry = q >= 1 && tk.carry; look = q >= 1 && tk.look;
            } else if (T < 46.5) { p = safe(i); d = p.clone().negate(); look = T > 40; }
            else { const q = ease(clamp((T - 46.5) / 5)), to = task(i, C, true).p; p = safe(i).lerp(to, q); d = to.clone().sub(safe(i)); walk = q < 1; }
            w.position.copy(p); w.userData.baseY = p.y; face(w, d.x, d.z); pose(w, C * 1.3 + i, walk, carry, weld, crouch);
            if (look) { w.userData.head.rotation.z = -0.45 + Math.sin(C * 0.5 + i) * 0.1; w.userData.head.rotation.y = 0; }
        });
        scissor.scale.y = u < 0 ? 1 : 1 - clamp(u / 0.2) * 0.9;
        hose.visible = u < 0; arm.scale.x = u < 0 ? 1 : Math.max(0.05, 1 - u * 4); arm.position.x = -6 * arm.scale.x;
        // sparks
        const sp = sparkGeo.attributes.position; let n = 0;
        sparkSpots.forEach((o, s) => {
            const on = u < 0 && blend >= 1 && Math.floor(C * 2.3 + s * 1.7) % 5 !== 4; arcLights[s].intensity = on ? 1.4 + Math.sin(C * 80 + s) * 0.8 : 0;
            for (let i = 0; i < SPARKS; i++) {
                const age = ((C * 2.2 + rnd(i + s * 50)) % 1) * 0.7, vx = (rnd(i + s * 9) - 0.5) * 4, vy = rnd(i + s * 9 + 1) * 3.5, vz = rnd(i + s * 9 + 2) * 3;
                const q = on ? 1 : 0; sp.setXYZ(n++, o.x + vx * age * q, o.y + (vy * age - 4.9 * age * age) * q - (on ? 0 : 999), o.z + vz * age * q);
            }
        });
        sp.needsUpdate = true;
        // dust kicked up by the thrusters
        const dk = u < 0 ? 0 : clamp(u / 0.15) * (1 - clamp((lift - 0.25) * 1.6)), dp = dustGeo.attributes.position, da = dustGeo.attributes.aA, ds = dustGeo.attributes.aS;
        dust.visible = dk > 0.001;
        if (dust.visible) {
            for (let i = 0; i < DUST; i++) {
                const ph = (C * 0.45 + rnd(i)) % 1, a = rnd(i + 1) * Math.PI * 2, r = 6 + ph * (28 + rnd(i + 2) * 40);
                dp.setXYZ(i, Math.cos(a) * r, 0.8 + ph * (2 + rnd(i + 3) * 9), Math.sin(a) * r); da.setX(i, (1 - ph) * 0.5 * dk * (0.4 + rnd(i + 4) * 0.6)); ds.setX(i, 2.5 + ph * 11);
            }
            dp.needsUpdate = da.needsUpdate = ds.needsUpdate = true;
        }
        // lights and the drone
        dish0.rotation.z = Math.sin(C * 0.6) * 0.4; radar.rotation.y = C * 1.8; bellyStrobe.visible = (C % 1.1) < 0.12;
        const blink = Math.floor(C * 1.6) % 2 === 0; navR.visible = navG.visible = blink; strobe.visible = (C % 1.3) < 0.08;
        padLights.forEach((m, i) => { m.material.color.setHex(u > 0 && u < 1 ? ((Math.floor(C * 6) + i) % 4 ? 0x301800 : 0xff3b20) : ((Math.floor(C * 3) + i) % 8 ? 0x5a3a10 : 0xffb040)); });
        drone.position.set(13 + Math.cos(C * 0.7) * 5, 12 + Math.sin(C * 1.3) * 0.6 + (u > 0 ? u * 10 : 0), Math.sin(C * 0.7) * 7); drone.rotation.y = -C * 0.7; droneLight.visible = blink;
        takeoffFx(T, C, u, lift);
        ship.visible = lift < 0.97;
    }

    // ---- day and night ---------------------------------------------------------------------------------------------
    const lightPools = mastLights.map((p) => {
        const m = new THREE.Mesh(new THREE.CircleGeometry(16, 40), new THREE.MeshBasicMaterial({ map: glowTex, color: 0xffd9a8, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false }));
        m.rotation.x = -Math.PI / 2; m.position.copy(p).setY(0.47); m.visible = false; desert.add(m); return m;
    });
    let sprites = null;
    function night(nf, env) {
        if (!sprites) { sprites = []; desert.traverse((o) => { if (o.isSprite) sprites.push([o, o.material.color.clone()]); }); }
        desert.environment = env;
        sun.intensity = lerp(2.2, 0.28, nf); sun.color.setRGB(lerp(1, 0.62, nf), lerp(0.88, 0.7, nf), lerp(0.72, 1, nf));
        hemi.intensity = lerp(0.5, 0.1, nf); desert.fog.color.setRGB(lerp(0.69, 0.035, nf), lerp(0.58, 0.04, nf), lerp(0.42, 0.055, nf));
        lightPools.forEach((m) => { m.material.opacity = nf * 0.5; m.visible = nf > 0.01; }); flood.intensity = lerp(1.5, 3, nf);
        sprites.forEach(([o, c]) => o.material.color.copy(c).multiplyScalar(lerp(1, 0.13, nf)));
        return { intensity: sun.intensity, color: sun.color };
    }

    k.linearize(desert);
    return { scene: desert, frame, night, hgt, FACTORY: V(0, 0, -96) };
};
