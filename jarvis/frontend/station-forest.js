// Station LSX, part 3: the port on planet LSX. A clearing in the forest with the landing pad in the middle, a ring
// road, and an office for every TikTok page (setPages builds them from the studio's accounts, with empty plots kept
// for the next pages). When a video is approved, that page's crate comes off the ship and its courier carries it
// home to the office. frame(T, C, deliveries): T is the trip's timeline, C the running clock,
// deliveries [{slot, d, fromShip}] the approvals being delivered (d = seconds since the tick).
window.LSX = window.LSX || {};
LSX.forest = (k) => {
    const { THREE, clamp, lerp, ease, rnd, fbm, V, canvas, tex, add, logoCanvas, mat, glow, ship, shipParts, thrust, worker, pose, face, crateMat, cgeo,
        skyMat, dayEnv, pad, softPoints, pointsGeo, glowTex } = k;
    const { legs, ramp, hold, cabin, radar, bellyStrobe } = shipParts;

    const forest = new THREE.Scene();
    forest.add(new THREE.Mesh(new THREE.SphereGeometry(3000, 48, 24), skyMat));
    forest.environment = dayEnv; forest.fog = new THREE.FogExp2(0xc4cbb8, 0.0016);
    const fHemi = new THREE.HemisphereLight(0xcfe0ee, 0x4a5a36, 0.55); forest.add(fHemi);
    const fSun = new THREE.DirectionalLight(0xfff1dc, 2.1); fSun.position.copy(k.SUN).multiplyScalar(240); fSun.castShadow = true;
    fSun.shadow.mapSize.set(2048, 2048); Object.assign(fSun.shadow.camera, { left: -90, right: 90, top: 90, bottom: -90, near: 10, far: 520 }); forest.add(fSun);
    const LAKE = V(-104, 0, -38), LAKE_R = 24;   // a lake in the forest south-west of the clearing
    const fh0 = (x, z) => { const r = Math.hypot(x, z); return clamp((r - 110) / 120) * (fbm(x * 0.006 + 3, z * 0.006, 1.3, 4) - 0.35) * 60; };
    const fh = (x, z) => { const d = Math.hypot(x - LAKE.x, z - LAKE.z) / LAKE_R, h = fh0(x, z); return d > 1.35 ? h : lerp(-2.2, h, clamp((d - 0.85) / 0.5)); };
    const grassC = canvas(512), gc = grassC.getContext('2d'); gc.fillStyle = '#3c5428'; gc.fillRect(0, 0, 512, 512);
    for (let i = 0; i < 30000; i++) { const t = rnd(i + 5000); gc.fillStyle = `rgba(${50 + t * 50 | 0},${72 + t * 50 | 0},${28 + t * 24 | 0},${0.25 + rnd(i + 5001) * 0.35})`; gc.fillRect(rnd(i + 5002) * 512, rnd(i + 5003) * 512, 1.5, 3); }
    const fGround = new THREE.Mesh(new THREE.PlaneGeometry(1600, 1600, 120, 120), new THREE.MeshStandardMaterial({ map: tex(grassC, 90, 90), roughness: 1 }));
    { const p = fGround.geometry.attributes.position; for (let i = 0; i < p.count; i++) p.setZ(i, fh(p.getX(i), -p.getY(i))); fGround.geometry.computeVertexNormals(); }
    fGround.rotation.x = -Math.PI / 2; fGround.receiveShadow = true; forest.add(fGround);
    const fPad = pad.clone(); fPad.position.set(0, 0, 0); forest.add(fPad);
    const roadM = new THREE.MeshStandardMaterial({ color: 0x3a3a3c, roughness: 0.9 }), kerbM = new THREE.MeshStandardMaterial({ color: 0xd8d4c8, roughness: 0.8 });
    const ring = new THREE.Mesh(new THREE.RingGeometry(33, 39, 96), roadM); ring.rotation.x = -Math.PI / 2; ring.position.y = 0.05; ring.receiveShadow = true; forest.add(ring);
    const ringLine = new THREE.Mesh(new THREE.RingGeometry(35.9, 36.1, 96), kerbM); ringLine.rotation.x = -Math.PI / 2; ringLine.position.y = 0.07; forest.add(ringLine);

    // ---- the pages: one office each, plus plots kept for the next pages --------------------------------------------
    const OFF_R = 60, MAX_SLOTS = 10;
    const slotAngle = (i, n) => i / n * Math.PI * 2 + Math.PI / 6;
    const lampHeadM = new THREE.MeshBasicMaterial({ color: 0x3a3630 });
    const plotM = new THREE.MeshStandardMaterial({ color: 0x8a8272, roughness: 1 }), bushM = new THREE.MeshStandardMaterial({ color: 0x3d6a2c, roughness: 1, flatShading: true });
    let ownTex = [], town = null, offices = [], fPools = [], unloaders = [], couriers = [], parcels = [], nightNow = 0, pageKey = '';
    const own = (t) => { ownTex.push(t); return t; };   // textures made for one set of offices, freed when they're rebuilt
    const signCanvas = (w, h) => { const c = canvas(w, h); return [c, c.getContext('2d')]; };
    const fitText = (g, text, max, size, font) => { let s = size; do { g.font = `700 ${s}px ${font}`; s -= 4; } while (g.measureText(text).width > max && s > 20); };
    function streetLamp(group, x, z, ry) {
        const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = ry; group.add(g);
        add(g, new THREE.CylinderGeometry(0.1, 0.14, 6, 6), mat.dark, 0, 3, 0); add(g, new THREE.BoxGeometry(1.4, 0.1, 0.1), mat.dark, 0.6, 6, 0); add(g, new THREE.BoxGeometry(0.6, 0.18, 0.35), lampHeadM, 1.2, 5.92, 0);
        const pool = new THREE.Mesh(new THREE.CircleGeometry(6, 28), new THREE.MeshBasicMaterial({ map: glowTex, color: 0xffd9a8, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false }));
        pool.rotation.x = -Math.PI / 2; pool.position.set(x + Math.cos(ry) * 1.2, 0.09, z - Math.sin(ry) * 1.2); group.add(pool); fPools.push(pool);
    }
    function office(group, pg, i, n) {
        const a = slotAngle(i, n), dir = V(Math.cos(a), 0, Math.sin(a));
        const road = new THREE.Mesh(new THREE.PlaneGeometry(OFF_R - 6 - 27, 6), roadM); road.rotation.set(-Math.PI / 2, 0, -a); road.position.copy(dir).multiplyScalar((OFF_R - 6 + 27) / 2).setY(0.06); road.receiveShadow = true; group.add(road);
        const g = new THREE.Group(); g.position.copy(dir).multiplyScalar(OFF_R); g.rotation.y = Math.atan2(-dir.z, dir.x); group.add(g);
        const door = dir.clone().multiplyScalar(OFF_R - 8.6).setY(0.4), pile = dir.clone().multiplyScalar(24).setY(0.4), wait = dir.clone().multiplyScalar(31).setY(0.4);
        const side = V(-dir.z, 0, dir.x);
        for (const r of [44, 52]) { const p = dir.clone().multiplyScalar(r).addScaledVector(side, 3.8); streetLamp(group, p.x, p.z, Math.atan2(side.z, -side.x)); }
        if (!pg) {
            add(g, new THREE.BoxGeometry(14, 0.2, 18), plotM, 0, 0.1, 0);
            const [sc, sg] = signCanvas(512, 160); sg.fillStyle = '#16181c'; sg.fillRect(0, 0, 512, 160); sg.fillStyle = '#e9e6de'; sg.font = '700 52px "Share Tech Mono", sans-serif'; sg.fillText('PLOT ' + (i + 1), 24, 70);
            sg.fillStyle = '#e8813a'; sg.font = '500 30px "Share Tech Mono", monospace'; sg.fillText('KEPT FOR YOUR NEXT PAGE', 24, 124);
            add(g, new THREE.BoxGeometry(0.3, 3, 0.3), mat.dark, -7.5, 1.5, -3); add(g, new THREE.BoxGeometry(0.3, 3, 0.3), mat.dark, -7.5, 1.5, 3);
            const s = new THREE.Mesh(new THREE.PlaneGeometry(6, 1.9), new THREE.MeshBasicMaterial({ map: own(tex(sc)) })); s.position.set(-7.6, 3.3, 0); s.rotation.y = -Math.PI / 2; g.add(s);
            for (let q = 0; q < 4; q++) add(g, new THREE.CylinderGeometry(0.2, 0.2, 1, 6), mat.orange, -6 + (q % 2) * 12, 0.5, q < 2 ? -8.5 : 8.5);
            return { pg: null, dir, door, pile, wait, empty: true };
        }
        const accM = new THREE.MeshStandardMaterial({ color: new THREE.Color(pg.colour || '#e8c547'), roughness: 0.5, metalness: 0.2 });
        const [winC, wg] = signCanvas(512, 256); wg.fillStyle = '#1b2530'; wg.fillRect(0, 0, 512, 256);
        for (let r = 0; r < 3; r++) {
            for (let c = 0; c < 8; c++) {
                const lit = rnd(i * 50 + r * 8 + c) > 0.3; wg.fillStyle = lit ? '#ffe2b0' : '#2c3a48'; wg.fillRect(8 + c * 63, 10 + r * 82, 54, 66);
                if (lit && rnd(i * 70 + r * 8 + c) > 0.55) { wg.fillStyle = 'rgba(40,40,50,.8)'; wg.fillRect(20 + c * 63, 40 + r * 82, 12, 36); wg.beginPath(); wg.arc(26 + c * 63, 36 + r * 82, 6, 0, 7); wg.fill(); }
            }
        }
        const winMap = own(tex(winC)), glass = new THREE.MeshStandardMaterial({ map: winMap, emissiveMap: winMap, emissive: 0xffffff, emissiveIntensity: 0.15, roughness: 0.15, metalness: 0.4 });
        add(g, new THREE.BoxGeometry(12, 10.5, 18), mat.hullB, 0, 5.25, 0); add(g, new THREE.BoxGeometry(0.2, 9, 16.6), glass, -6.05, 5.2, 0);
        add(g, new THREE.BoxGeometry(12.4, 0.5, 18.4), accM, 0, 10.6, 0); add(g, new THREE.BoxGeometry(12.2, 0.35, 18.2), accM, 0, 3.6, 0);
        add(g, new THREE.BoxGeometry(3, 0.25, 5), mat.dark, -7.4, 3.2, 0); add(g, new THREE.BoxGeometry(0.1, 2.8, 2.4), new THREE.MeshBasicMaterial({ color: 0xfff0d0 }), -6.2, 1.4, 0);
        for (const z of [-2.2, 2.2]) add(g, new THREE.BoxGeometry(0.2, 3.2, 0.2), mat.dark, -8.7, 1.6, z);
        const [sc, sg] = signCanvas(1024, 256); sg.fillStyle = '#121418'; sg.fillRect(0, 0, 1024, 256); sg.drawImage(logoCanvas(200), 20, 28, 200, 200);
        sg.fillStyle = '#f2efe8'; fitText(sg, pg.name, 760, 96, '"Share Tech Mono", sans-serif'); sg.fillText(pg.name, 240, 130);
        sg.fillStyle = pg.colour || '#e8c547'; sg.font = '500 40px "Share Tech Mono", monospace'; sg.fillText(`${pg.label || 'VIDEOS'} · OFFICE`.slice(0, 36), 244, 200); sg.fillRect(0, 238, 1024, 18);
        const sign = new THREE.Mesh(new THREE.PlaneGeometry(11, 2.75), new THREE.MeshBasicMaterial({ map: own(tex(sc)) })); sign.position.set(-6.2, 12.4, 0); sign.rotation.y = -Math.PI / 2; g.add(sign);
        add(g, new THREE.BoxGeometry(0.4, 3.2, 11.4), mat.dark, -5.9, 12.4, 0);
        for (const [x, z] of [[2, -5], [2, 5]]) { add(g, new THREE.BoxGeometry(2.6, 1.4, 2.6), mat.steel, x, 11.5, z); add(g, new THREE.CylinderGeometry(1, 1, 0.2, 16), mat.dark, x, 12.3, z); }
        for (const z of [-7.5, 7.5]) { add(g, new THREE.BoxGeometry(2, 0.8, 2), mat.dark, -8, 0.4, z); add(g, new THREE.SphereGeometry(1.2, 10, 8), bushM, -8, 1.6, z); }
        return { pg, dir, door, pile, wait, glass };
    }
    // trees: conifers and broadleaf, packed outside the clearing (instanced so the forest stays cheap)
    const TREES = 4200, trunkG = new THREE.CylinderGeometry(0.22, 0.34, 3, 6).translate(0, 1.5, 0), coneG = new THREE.ConeGeometry(2.1, 7, 7).translate(0, 6, 0), crownG = new THREE.IcosahedronGeometry(2.8, 0).translate(0, 5.2, 0);
    const trunkI = new THREE.InstancedMesh(trunkG, new THREE.MeshStandardMaterial({ color: 0x4a3526, roughness: 1 }), TREES);
    const coneI = new THREE.InstancedMesh(coneG, new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 1, flatShading: true }), TREES);
    const crownI = new THREE.InstancedMesh(crownG, new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 1, flatShading: true }), TREES);
    function plantTrees(n) {   // the trees close to the clearing keep clear of each page's road
        const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), c = new THREE.Color(), hide = new THREE.Matrix4().makeScale(0, 0, 0), step = Math.PI * 2 / n;
        for (let i = 0; i < TREES; i++) {
            let r = 76 + Math.pow(rnd(i + 6000), 0.8) * 330, a = rnd(i + 6001) * Math.PI * 2;
            if (i < 160) {
                r = 44 + rnd(i + 6005) * 30; const slot = Math.round((a - Math.PI / 6) / step), off = a - (slot * step + Math.PI / 6);
                if (Math.abs(off) < 0.24) a += Math.sign(off || 1) * 0.3;
                const toT = Math.atan2(Math.sin(a - towerAng), Math.cos(a - towerAng));
                if (Math.abs(toT) < 0.26) r = 58 + rnd(i + 6009) * 16;   // behind the tower, not through it
            }
            let x = Math.cos(a) * r, z = Math.sin(a) * r; const s = 0.8 + rnd(i + 6002) * 0.8;
            const ld = Math.hypot(x - LAKE.x, z - LAKE.z);
            if (ld < LAKE_R + 6) { const k2 = (LAKE_R + 6 + rnd(i + 6010) * 20) / Math.max(ld, 0.1); x = LAKE.x + (x - LAKE.x) * k2; z = LAKE.z + (z - LAKE.z) * k2; }
            const y = fh(x, z);
            q.setFromAxisAngle(V(0, 1, 0), rnd(i + 6003) * 6.3); m4.compose(V(x, y, z), q, V(s, s * (0.9 + rnd(i + 6004) * 0.4), s)); trunkI.setMatrixAt(i, m4);
            const conifer = rnd(i + 6006) < 0.65;
            c.setHSL(conifer ? 0.3 + rnd(i + 6007) * 0.05 : 0.2 + rnd(i + 6007) * 0.08, 0.45, conifer ? 0.16 + rnd(i + 6008) * 0.08 : 0.24 + rnd(i + 6008) * 0.1);
            c.convertSRGBToLinear(); coneI.setMatrixAt(i, conifer ? m4 : hide); crownI.setMatrixAt(i, conifer ? hide : m4); coneI.setColorAt(i, c); crownI.setColorAt(i, c);
        }
        for (const m of [trunkI, coneI, crownI]) { m.instanceMatrix.needsUpdate = true; if (m.instanceColor) m.instanceColor.needsUpdate = true; }
    }
    for (const m of [trunkI, coneI, crownI]) { m.castShadow = true; m.receiveShadow = true; forest.add(m); }
    const RAMP_END = V(-18.5, 0.4, 0);
    const ringLamps = new THREE.Group(); forest.add(ringLamps);
    for (let q = 0; q < 12; q++) { const a = q / 12 * Math.PI * 2, p = V(Math.cos(a) * 40.5, 0, Math.sin(a) * 40.5); streetLamp(ringLamps, p.x, p.z, Math.atan2(Math.sin(a), -Math.cos(a))); }
    const ringPools = fPools.slice();

    // control tower: a concrete shaft with a glass cab, beacon, radar and windsock, set between two pages' roads
    const tower = new THREE.Group(); forest.add(tower);
    const concM = new THREE.MeshStandardMaterial({ color: 0xb9b4aa, roughness: 0.95 });
    const cabGlass = new THREE.MeshStandardMaterial({ color: 0x1d2c38, emissive: 0x8fc4ff, emissiveIntensity: 0.05, metalness: 0.6, roughness: 0.12 });
    const beaconM = new THREE.MeshBasicMaterial({ color: 0x3a1010 }), sockM = new THREE.MeshStandardMaterial({ color: 0xe8702a, roughness: 0.8, side: THREE.DoubleSide });
    add(tower, new THREE.BoxGeometry(9, 4, 7), concM, 0, 2, 0); add(tower, new THREE.BoxGeometry(0.1, 2.6, 1.8), new THREE.MeshBasicMaterial({ color: 0xfff0d0 }), -4.55, 1.3, 0);
    add(tower, new THREE.BoxGeometry(9.3, 0.3, 7.3), mat.dark, 0, 4.1, 0);
    add(tower, new THREE.CylinderGeometry(1.5, 1.8, 15, 12), concM, 1.5, 11.5, 0);
    for (let q = 0; q < 5; q++) add(tower, new THREE.BoxGeometry(0.12, 0.8, 0.5), cabGlass, -0.05, 6 + q * 2.6, 0).position.x = 1.5 - 1.62;
    add(tower, new THREE.CylinderGeometry(3.4, 2.4, 0.6, 8), mat.dark, 1.5, 19.2, 0);
    const cab = add(tower, new THREE.CylinderGeometry(3.3, 3.0, 2.8, 8, 1, true), cabGlass, 1.5, 20.9, 0); cab.material.side = THREE.DoubleSide;
    for (let q = 0; q < 8; q++) { const a = q / 8 * Math.PI * 2 + Math.PI / 8; add(tower, new THREE.BoxGeometry(0.14, 2.8, 0.14), mat.dark, 1.5 + Math.cos(a) * 3.15, 20.9, Math.sin(a) * 3.15); }
    add(tower, new THREE.CylinderGeometry(3.7, 3.5, 0.5, 8), mat.hullB, 1.5, 22.5, 0);
    for (let q = 0; q < 2; q++) { const c = worker(); c.position.set(1.5 - 1.2 + q * 1.4, 19.5, -1 + q * 1.6); c.scale.setScalar(0.95); tower.add(c); face(c, -1, q ? 0.4 : -0.3); pose(c, q, false, false, false); }
    add(tower, new THREE.CylinderGeometry(0.06, 0.06, 5, 6), mat.steel, 2.6, 25, 0.8);
    const beacon = add(tower, new THREE.SphereGeometry(0.28, 10, 8), beaconM, 2.6, 27.6, 0.8);
    const radarArm = new THREE.Group(); radarArm.position.set(0.6, 23.2, -1); tower.add(radarArm);
    add(radarArm, new THREE.BoxGeometry(0.3, 0.9, 0.3), mat.dark, 0, -0.2, 0); add(radarArm, new THREE.BoxGeometry(0.25, 0.6, 3.2), mat.steel, 0.1, 0.35, 0);
    const sockPole = add(tower, new THREE.CylinderGeometry(0.05, 0.06, 3, 6), mat.steel, -3.6, 5.6, 2.8);
    const sock = new THREE.Mesh(new THREE.ConeGeometry(0.4, 2.2, 10, 1, true).rotateZ(Math.PI / 2).translate(-1.1, 0, 0), sockM); sock.position.set(-3.6, 6.9, 2.8); tower.add(sock);
    tower.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    const towerPool = new THREE.Mesh(new THREE.CircleGeometry(9, 28), new THREE.MeshBasicMaterial({ map: glowTex, color: 0xcfe2ff, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false }));
    towerPool.rotation.x = -Math.PI / 2; towerPool.position.set(-5, 0.09, 0); tower.add(towerPool);
    let towerAng = 0;
    // edge lights round the pad: steady amber, and a white chase running in towards the centre while she lands or lifts off
    const edgeOn = new THREE.MeshBasicMaterial({ color: 0xffb040 }), edgeOff = new THREE.MeshBasicMaterial({ color: 0x4a3a22 }), chaseM = new THREE.MeshBasicMaterial({ color: 0xffffff });
    const edgeLights = [], EDGE = 32;
    for (let q = 0; q < EDGE; q++) { const a = q / EDGE * Math.PI * 2; edgeLights.push(add(forest, new THREE.CylinderGeometry(0.2, 0.24, 0.16, 8), edgeOn, Math.cos(a) * 26.2, 0.48, Math.sin(a) * 26.2)); }
    // electric cargo carts doing rounds of the ring road, one lane each way
    const cartM = new THREE.MeshStandardMaterial({ color: 0xe9e6de, roughness: 0.5, metalness: 0.3 }), tyreM = new THREE.MeshStandardMaterial({ color: 0x151515, roughness: 0.9 });
    const headM = new THREE.MeshBasicMaterial({ color: 0xfff4dc }), tailM = new THREE.MeshBasicMaterial({ color: 0x5a1010 }), ambM = new THREE.MeshBasicMaterial({ color: 0x5a3a10 });
    const carts = [];
    for (let q = 0; q < 4; q++) {
        const c = new THREE.Group(); forest.add(c);
        add(c, new THREE.BoxGeometry(3.6, 0.35, 1.7), mat.dark, 0, 0.55, 0); add(c, new THREE.BoxGeometry(1.2, 1.3, 1.6), cartM, 1.3, 1.35, 0);
        add(c, new THREE.BoxGeometry(0.05, 0.7, 1.4), mat.glass, 1.93, 1.55, 0); add(c, new THREE.BoxGeometry(2.3, 0.08, 1.72), mat.orange, -0.55, 0.77, 0);
        for (const [x, z] of [[1.2, 0.85], [1.2, -0.85], [-1.2, 0.85], [-1.2, -0.85]]) add(c, new THREE.CylinderGeometry(0.34, 0.34, 0.24, 12).rotateX(Math.PI / 2), tyreM, x, 0.34, z);
        for (let b = 0; b < 1 + (q % 3); b++) add(c, cgeo, crateMat, -1.3 + b * 1.25, 1.25, 0).castShadow = true;
        for (const z of [0.6, -0.6]) { add(c, new THREE.BoxGeometry(0.06, 0.16, 0.26), headM, 1.93, 0.95, z); add(c, new THREE.BoxGeometry(0.06, 0.14, 0.24), tailM, -1.82, 0.8, z); }
        const amb = add(c, new THREE.SphereGeometry(0.13, 8, 6), ambM, 1.3, 2.08, 0);
        const beam = new THREE.Mesh(new THREE.CircleGeometry(4, 20), new THREE.MeshBasicMaterial({ map: glowTex, color: 0xfff0d0, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false }));
        beam.rotation.x = -Math.PI / 2; beam.position.set(5, 0.1, 0); beam.scale.set(1.5, 0.7, 1); c.add(beam);
        c.traverse((o) => { if (o.isMesh && o !== beam) o.castShadow = true; });
        carts.push({ g: c, amb, beam, lane: q % 2 ? 34.6 : 37.4, dir: q % 2 ? -1 : 1, off: q * 1.7, speed: 3.2 + (q % 3) * 0.5 });
    }
    function portTraffic(T, C) {
        // the carts pull over to the kerb and wait while the ship is coming down or lifting off
        const hold = (T > 23.8 && T < 27.6) || (T > 30.3 && T < 32.8);
        carts.forEach((ct) => {
            ct.pos = ct.pos === undefined ? ct.off : ct.pos;
            ct.v = (ct.v || 0) + ((hold ? 0 : 1) - (ct.v || 0)) * 0.05;
            ct.pos += ct.dir * ct.v * ct.speed / ct.lane * (ct.dt || 0);
            const a = ct.pos, x = Math.cos(a) * ct.lane, z = Math.sin(a) * ct.lane;
            ct.g.position.set(x, 0.05, z); const tx = -Math.sin(a) * ct.dir, tz = Math.cos(a) * ct.dir; ct.g.rotation.y = Math.atan2(-tz, tx);
            ct.amb.material = (C * 1.6 + ct.off) % 1 < 0.35 ? edgeOn : ambM;
        });
        const landing = (T > 23.5 && T < 27.2) || (T > 30.3 && T < 32.6);
        edgeLights.forEach((m, q) => {
            const ph = ((C * 14 - q) % EDGE + EDGE) % EDGE;
            m.material = landing && ph < 3 ? chaseM : (nightNow > 0.2 || landing ? edgeOn : edgeOff);
        });
        beacon.material.color.setRGB((C % 1.4) < 0.18 ? 1 : 0.23, 0.05, 0.05);
        radarArm.rotation.y = C * 1.2;
        const wind = 0.6 + Math.sin(C * 0.21) * 0.4; sock.rotation.set(0, -towerAng + 2.2 + Math.sin(C * 0.4) * 0.25, -0.9 * (1 - wind));
    }
    let lastC = null;

    // ---- the lake: still water with ripples, reeds, a wooden jetty with a worker fishing, and a small boat going round
    const waterC = canvas(256), wc = waterC.getContext('2d'); wc.fillStyle = '#808080'; wc.fillRect(0, 0, 256, 256);
    for (let i = 0; i < 900; i++) { wc.strokeStyle = `rgba(${rnd(i) > 0.5 ? 255 : 0},${rnd(i) > 0.5 ? 255 : 0},${rnd(i) > 0.5 ? 255 : 0},.08)`; wc.beginPath(); const x = rnd(i + 1) * 256, y = rnd(i + 2) * 256; wc.ellipse(x, y, 4 + rnd(i + 3) * 12, 1 + rnd(i + 4) * 2, 0, 0, 7); wc.stroke(); }
    const waterBump = tex(waterC, 6, 6, false);
    const water = new THREE.Mesh(new THREE.CircleGeometry(LAKE_R * 1.15, 64), new THREE.MeshStandardMaterial({ color: 0x1d3a44, metalness: 0.9, roughness: 0.08, bumpMap: waterBump, bumpScale: 0.02, transparent: true, opacity: 0.93 }));
    water.rotation.x = -Math.PI / 2; water.position.set(LAKE.x, -0.35, LAKE.z); forest.add(water);
    const reedM = new THREE.MeshStandardMaterial({ color: 0x6b7a3a, roughness: 1, side: THREE.DoubleSide });
    const reedG = new THREE.ConeGeometry(0.06, 1.8, 3).translate(0, 0.9, 0), REEDS = 260, reeds = new THREE.InstancedMesh(reedG, reedM, REEDS);
    { const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler();
        for (let i = 0; i < REEDS; i++) {
            const a = rnd(i + 9700) * Math.PI * 2; if (Math.abs(Math.atan2(Math.sin(a - 0.35), Math.cos(a - 0.35))) < 0.25) { reeds.setMatrixAt(i, new THREE.Matrix4().makeScale(0, 0, 0)); continue; }
            const r = LAKE_R * (0.95 + rnd(i + 9701) * 0.25), x = LAKE.x + Math.cos(a) * r, z = LAKE.z + Math.sin(a) * r;
            e.set((rnd(i + 9702) - 0.5) * 0.3, 0, (rnd(i + 9703) - 0.5) * 0.3); q.setFromEuler(e); const sc = 0.6 + rnd(i + 9704) * 0.8;
            m4.compose(V(x, Math.max(-0.35, fh(x, z)) - 0.1, z), q, V(sc, sc, sc)); reeds.setMatrixAt(i, m4);
        } }
    forest.add(reeds);
    // the jetty points from the clearing side of the shore out over the water
    const woodM = new THREE.MeshStandardMaterial({ color: 0x7a5a3c, roughness: 0.9 });
    const jetty = new THREE.Group(); const jA = 0.35, jBase = V(LAKE.x + Math.cos(jA) * (LAKE_R + 2), 0, LAKE.z + Math.sin(jA) * (LAKE_R + 2));
    jetty.position.copy(jBase).setY(0.1); jetty.rotation.y = Math.atan2(Math.sin(jA), -Math.cos(jA)); forest.add(jetty);
    for (let q = 0; q < 12; q++) add(jetty, new THREE.BoxGeometry(0.35, 0.12, 3), woodM, q * 1.0 + 0.5, 0.3, 0);
    for (let q = 0; q < 4; q++) for (const z of [-1.3, 1.3]) add(jetty, new THREE.CylinderGeometry(0.12, 0.12, 2.4, 6), woodM, 1 + q * 3.5, -0.5, z);
    const fisher = worker(); jetty.add(fisher); fisher.position.set(11.2, 0.36, 0.6); fisher.userData.baseY = 0.36;
    const rod = add(jetty, new THREE.CylinderGeometry(0.02, 0.035, 3.6, 4), mat.dark, 12.6, 2.1, 0.7); rod.rotation.z = -0.9;
    const bobber = add(forest, new THREE.SphereGeometry(0.1, 6, 4), mat.orange);
    const boat = new THREE.Group(); forest.add(boat);
    add(boat, new THREE.BoxGeometry(3.8, 0.6, 1.5), new THREE.MeshStandardMaterial({ color: 0xe9e6de, roughness: 0.6 }), 0, 0.3, 0); add(boat, new THREE.ConeGeometry(0.75, 1.2, 4).rotateZ(-Math.PI / 2).rotateX(Math.PI / 4), new THREE.MeshStandardMaterial({ color: 0xe9e6de, roughness: 0.6 }), 2.5, 0.3, 0);
    add(boat, new THREE.BoxGeometry(1, 0.8, 1.1), mat.hullB, -0.6, 0.9, 0); add(boat, new THREE.BoxGeometry(3.9, 0.12, 1.55), mat.orange, 0, 0.55, 0);
    const boatWake = new THREE.Mesh(new THREE.PlaneGeometry(9, 2.4), new THREE.MeshBasicMaterial({ map: glowTex, color: 0xd8e8f0, transparent: true, opacity: 0.35, blending: THREE.AdditiveBlending, depthWrite: false }));
    boatWake.rotation.x = -Math.PI / 2; boatWake.position.set(-4.5, 0.02, 0); boat.add(boatWake);
    const boatLamp = add(boat, new THREE.SphereGeometry(0.1, 6, 4), glow(0x3cff8a), -0.6, 1.4, 0);
    function lakeFrame(C) {
        waterBump.offset.set(C * 0.004, C * 0.003);
        const a = C * 0.05, r = LAKE_R * 0.6; boat.position.set(LAKE.x + Math.cos(a) * r, -0.45 + Math.sin(C * 1.3) * 0.04, LAKE.z + Math.sin(a) * r);
        boat.rotation.set(Math.sin(C * 1.1) * 0.03, Math.atan2(-Math.cos(a), -Math.sin(a)), Math.sin(C * 0.9) * 0.03); boatLamp.visible = Math.floor(C * 1.4) % 2 === 0;
        pose(fisher, C, false, false, false); face(fisher, 1, 0);
        fisher.updateMatrixWorld(); rod.updateMatrixWorld();
        const tip = V(0, 1.8, 0).applyMatrix4(rod.matrixWorld), bob = jBase.clone().add(V(-Math.cos(jA) * 16, 0, -Math.sin(jA) * 16));
        bobber.position.set(bob.x + Math.sin(C * 0.3) * 0.4, -0.3 + Math.max(0, Math.sin(C * 2.1)) * 0.05 - (Math.sin(C * 0.37) > 0.97 ? 0.15 : 0), bob.z); void tip;
    }

    // pages: [{name, label, colour}] from GET /station/state. Rebuilds the offices only when the list changes.
    function setPages(pages) {
        const list = (pages || []).slice(0, MAX_SLOTS);
        const key = list.map((p) => `${p.name}|${p.label}|${p.colour}`).join(';');
        if (key === pageKey && town) return;
        pageKey = key;
        if (town) {
            forest.remove(town);
            ownTex.forEach((t) => t.dispose()); ownTex = [];
        }
        town = new THREE.Group(); forest.add(town);
        fPools = ringPools.slice();
        const n = Math.min(MAX_SLOTS, Math.max(6, list.length + 2));
        towerAng = Math.PI / 6 - Math.PI / n;   // halfway between the last page's road and the first
        tower.position.set(Math.cos(towerAng) * 49, 0, Math.sin(towerAng) * 49); tower.rotation.y = Math.atan2(-Math.sin(towerAng), Math.cos(towerAng));
        offices = Array.from({ length: n }, (_, i) => office(town, list[i] || null, i, n));
        plantTrees(n);
        // delivery crew: an unloader at the ramp and a courier for each office, and one crate per page
        unloaders = []; couriers = []; parcels = [];
        offices.forEach((o, i) => {
            if (o.empty) return;
            const un = worker(); town.add(un); unloaders[i] = un;
            const cw = worker(); town.add(cw); couriers[i] = cw;
            const c = add(town, cgeo, crateMat); c.position.copy(o.pile).setY(0.9); c.visible = false; parcels[i] = c;
        });
        k.linearize(town);
        applyNight(nightNow);
    }

    // thruster wash: dust and leaves blown out across the pad while she lands and lifts off
    const WASH = 260, washGeo = pointsGeo(WASH);
    const wash = new THREE.Points(washGeo, softPoints('#b9b39a', THREE.NormalBlending)); wash.frustumCulled = false; forest.add(wash);
    const LEAVES = 120, leafGeo = new THREE.BufferGeometry(); leafGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(LEAVES * 3), 3));
    const leaves = new THREE.Points(leafGeo, new THREE.PointsMaterial({ color: 0x6b7a2e, size: 0.25 })); leaves.frustumCulled = false; forest.add(leaves);
    // birds circling over the trees
    const BIRDS = 18, birdGeo = new THREE.BufferGeometry(); birdGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(BIRDS * 9), 3));
    const birds = new THREE.Mesh(birdGeo, new THREE.MeshBasicMaterial({ color: 0x1c1c1c, side: THREE.DoubleSide })); birds.frustumCulled = false; forest.add(birds);
    function portLife(T, C, l) {
        const wk = l < 0.35 && ((T >= 24.5 && T < 27.4) || (T >= 30.5 && T < 32.5)) ? (1 - l / 0.35) : 0;
        wash.visible = wk > 0; leaves.visible = wk > 0.2;
        if (wash.visible) {
            const wp = washGeo.attributes.position, wa = washGeo.attributes.aA, ws = washGeo.attributes.aS;
            for (let i = 0; i < WASH; i++) {
                const ph = (C * 0.6 + rnd(i + 7000)) % 1, a = rnd(i + 7001) * 6.28, r = 5 + ph * (30 + rnd(i + 7002) * 30);
                wp.setXYZ(i, Math.cos(a) * r, 0.6 + ph * (1.5 + rnd(i + 7003) * 6), Math.sin(a) * r); wa.setX(i, (1 - ph) * 0.4 * wk); ws.setX(i, 2 + ph * 9);
            }
            wp.needsUpdate = wa.needsUpdate = ws.needsUpdate = true;
            const lp = leafGeo.attributes.position;
            for (let i = 0; i < LEAVES; i++) {
                const ph = (C * 0.5 + rnd(i + 7100)) % 1, a = rnd(i + 7101) * 6.28, r = 24 + ph * 40;
                lp.setXYZ(i, Math.cos(a + ph) * r, 0.3 + Math.sin(ph * Math.PI) * (3 + rnd(i + 7102) * 5) + Math.sin(C * 9 + i) * 0.2, Math.sin(a + ph) * r);
            }
            lp.needsUpdate = true;
        }
        const bp = birdGeo.attributes.position;
        for (let i = 0; i < BIRDS; i++) {
            const a = C * 0.18 + i * 0.35 + Math.sin(i) * 0.3, r = 120 + (i % 5) * 9, cx = 60, cz = -140;
            const x = cx + Math.cos(a) * r, z = cz + Math.sin(a) * r, y = 38 + (i % 4) * 3 + Math.sin(C + i) * 2, fl = Math.sin(C * 9 + i * 1.7) * 0.9, dx = -Math.sin(a), dz = Math.cos(a), sx = -dz, sz = dx;
            bp.setXYZ(i * 3, x + dx * 0.9, y, z + dz * 0.9); bp.setXYZ(i * 3 + 1, x + sx * 1.3, y + fl, z + sz * 1.3); bp.setXYZ(i * 3 + 2, x - sx * 1.3, y + fl, z - sz * 1.3);
        }
        bp.needsUpdate = true;
    }
    // a delivery's steps, in seconds after the tick: the crate comes down the ramp to the page's pile (0 to 2.2),
    // the courier walks out from the office (0 to 8), carries it home (8 to 19) and stays inside a while (to 35)
    const COURIER_OUT = 8, COURIER_HOME = 19, COURIER_IN = 35;
    function frame(T, C, deliveries = []) {
        let l = 1;
        if (T >= 24.5 && T < 27.1) l = Math.pow(1 - clamp((T - 24.5) / 2.6), 2.4);
        else if (T >= 27.1 && T < 30.6) l = 0;
        else if (T >= 30.6 && T < 32.5) l = Math.pow(clamp((T - 30.6) / 1.9), 2.2);
        if (ship.parent !== forest) forest.add(ship);
        ship.visible = l < 0.98; ship.scale.setScalar(1); ship.position.set(0, 5.1 + l * 190, 0); ship.rotation.set(0, 0, 0);
        const gear = 1 - clamp((l - 0.04) / 0.3); legs.forEach((lg, i) => { lg.rotation.z = (1 - gear) * (i < 2 ? -1.45 : 1.45); });
        let open = 0;
        deliveries.forEach((dl) => { if (dl.fromShip) open = Math.max(open, clamp(dl.d / 0.5) * (1 - clamp((dl.d - 3.4) / 0.4))); });
        ramp.rotation.z = l === 0 ? 0.74 * ease(open) : 0; hold.visible = ramp.rotation.z > 0.03; cabin.intensity = l < 0.02 ? 1.2 : 0;
        const firing = (T >= 24.5 && T < 27.2) || (T >= 30.5 && T < 32.5); thrust(C, l > 0.25 ? 0.7 : 0, firing ? 0.9 : 0);
        radar.rotation.y = C * 1.8; bellyStrobe.visible = (C % 1.1) < 0.12; portLife(T, C, l);
        carts.forEach((ct) => { ct.dt = lastC === null ? 0 : clamp(C - lastC, 0, 0.1); }); lastC = C; portTraffic(T, C); lakeFrame(C);
        const bySlot = [];
        deliveries.forEach((dl) => { if (!bySlot[dl.slot] || dl.d < bySlot[dl.slot].d) bySlot[dl.slot] = dl; });   // the newest per page
        const landing = T > 23 && T < 27.4;
        offices.forEach((o, i) => {
            if (o.empty) return;
            const dl = bySlot[i], d = dl ? dl.d : Infinity, n = offices.length;
            // unloader: waits off the pad, comes to the ramp, carries the page's crate to its pile, goes back
            const un = unloaders[i], home = o.wait.clone().add(V(0, 0, 2)), ramp2 = RAMP_END.clone().add(V(0, 0, (i - n / 2) * 1.0));
            let p = home, dir = home.clone().negate(), walk = false, carry = false;
            if (dl && dl.fromShip && d < 3.6) {
                if (d < 0.6) { const f = ease(d / 0.6); p = home.clone().lerp(ramp2, f); dir = ramp2.clone().sub(home); walk = true; }
                else if (d < 2.2) { const f = ease((d - 0.6) / 1.6); p = ramp2.clone().lerp(o.pile, f); dir = o.pile.clone().sub(ramp2); walk = carry = true; }
                else { const f = ease((d - 2.2) / 1.4); p = o.pile.clone().lerp(home, f); dir = home.clone().sub(o.pile); walk = f < 1; }
            }
            un.position.copy(p); un.userData.baseY = 0.4; face(un, dir.x, dir.z); pose(un, C * 1.3 + i, walk, carry, false);
            if (!walk && !carry) un.userData.head.rotation.z = landing ? -0.45 : 0;
            parcels[i].visible = !!dl && d >= (dl.fromShip ? 2.2 : 0) && d < COURIER_OUT;
            // courier: walks out from the office, picks the crate up, carries it home and goes inside
            const cw = couriers[i], outside = o.door.clone().addScaledVector(o.dir, -2.5);
            cw.visible = true; walk = false; carry = false; p = outside; dir = o.dir.clone().negate();
            if (d < COURIER_OUT) { const f = ease(d / COURIER_OUT); p = outside.clone().lerp(o.pile, f); dir = o.pile.clone().sub(outside); walk = true; }
            else if (d < COURIER_HOME) { const f = ease((d - COURIER_OUT) / (COURIER_HOME - COURIER_OUT)); p = o.pile.clone().lerp(o.door, f); dir = o.door.clone().sub(o.pile); walk = carry = true; }
            else if (d < COURIER_IN) { cw.visible = false; }
            cw.position.copy(p); cw.userData.baseY = 0.4; face(cw, dir.x, dir.z); pose(cw, C * 1.3 + i * 2, walk, carry, false);
            if (!walk) cw.userData.head.rotation.z = landing ? -0.45 : 0;
        });
    }
    // how long a delivery takes, so station.js knows when to drop it
    const DELIVERY_SECONDS = COURIER_IN;

    function applyNight(nf) {
        offices.forEach((o) => { if (o.glass) o.glass.emissiveIntensity = 0.15 + (1.1 - 0.15) * nf; });
        fPools.forEach((m) => { m.material.opacity = nf * 0.55; m.visible = nf > 0.01; });
        cabGlass.emissiveIntensity = 0.05 + nf * 0.9; towerPool.material.opacity = nf * 0.45;
        carts.forEach((ct) => { ct.beam.material.opacity = nf * 0.5; });
    }
    function night(nf, env, sunLight) {
        nightNow = nf;
        forest.environment = env;
        fSun.intensity = sunLight.intensity; fSun.color.copy(sunLight.color); fHemi.intensity = 0.55 + (0.1 - 0.55) * nf;
        forest.fog.color.setRGB(0.55 + (0.03 - 0.55) * nf, 0.6 + (0.04 - 0.6) * nf, 0.47 + (0.05 - 0.47) * nf);
        lampHeadM.color.setRGB(0.2 + 0.8 * nf, 0.19 + 0.66 * nf, 0.17 + 0.43 * nf);
        applyNight(nf);
    }

    k.linearize(forest);
    setPages([]);
    return { scene: forest, frame, night, setPages, fh, slotOf: (name) => offices.findIndex((o) => o.pg && o.pg.name === name), DELIVERY_SECONDS };
};
