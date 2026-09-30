// Station LSX, part 4: space. Planet HOME (the desert base) on the left, planet LSX (the forest port) on the right,
// with the wolf free in the middle between them; around them the rest of the solar system: the sun, a ringed gas
// giant, a small ice world, an asteroid belt, faint orbit lines, and the galaxy behind it all.
// It is built in steps (await between the heavy textures) so the HUD stays smooth while it loads.
window.LSX = window.LSX || {};
LSX.space = async (k, pause) => {
    const { THREE, clamp, lerp, ease, rnd, hash, fbm, V, canvas, tex, add, mat, glow, winMat, ship, shipParts, thrust, softPoints, pointsGeo, glowTex, cloudMat } = k;
    const { legs, ramp, hold, cabin } = shipParts;

    const space = new THREE.Scene(); space.background = new THREE.Color(0x010204);
    // the sky (galaxy band, stars, a nebula) travels with the camera, so it stays behind even from deep space
    const sky = new THREE.Group(); space.add(sky);
    const galaxy = (() => {
        const W = 1024, H = 512, c = canvas(W, H), g = c.getContext('2d'), img = g.createImageData(W, H), d = img.data;
        for (let y = 0; y < H; y++) {
            for (let x = 0; x < W; x++) {
                const u = x / W, v = y / H, band = v - 0.5 - Math.sin(u * Math.PI * 2) * 0.16, kk = Math.exp(-band * band * 70);
                const n = fbm(u * 9, v * 9, 1, 5), lane = clamp(1 - Math.exp(-band * band * 900) * (0.6 + n * 0.8)), b = kk * (0.25 + n * 0.9) * lane, i = (y * W + x) * 4;
                d[i] = 10 + b * 150; d[i + 1] = 10 + b * 128; d[i + 2] = 18 + b * 150; d[i + 3] = 255;
            }
        }
        g.putImageData(img, 0, 0);
        return new THREE.Mesh(new THREE.SphereGeometry(2900, 48, 24), new THREE.MeshBasicMaterial({ map: tex(c), side: THREE.BackSide, depthWrite: false, fog: false }));
    })();
    galaxy.rotation.set(0.4, 0.2, 0.5); sky.add(galaxy);
    const starGeo = (n, r, seed) => {
        const g = new THREE.BufferGeometry(), a = new Float32Array(n * 3);
        for (let i = 0; i < n; i++) { const u = rnd(seed + i) * 2 - 1, th = rnd(seed + i + 0.5) * Math.PI * 2, s = Math.sqrt(1 - u * u); a.set([s * Math.cos(th) * r, u * r, s * Math.sin(th) * r], i * 3); }
        g.setAttribute('position', new THREE.BufferAttribute(a, 3)); return g;
    };
    sky.add(new THREE.Points(starGeo(5000, 2500, 1), new THREE.PointsMaterial({ color: 0xc8d2e6, size: 1.2, sizeAttenuation: false, depthWrite: false })));
    sky.add(new THREE.Points(starGeo(500, 2500, 9), new THREE.PointsMaterial({ color: 0xffffff, size: 2.4, sizeAttenuation: false, depthWrite: false })));
    const nebC = canvas(512), ng = nebC.getContext('2d');
    for (let i = 0; i < 30; i++) {
        const x = 100 + rnd(i) * 320, y = 140 + rnd(i + 1) * 240, r = 60 + rnd(i + 2) * 140, gr = ng.createRadialGradient(x, y, 0, x, y, r);
        gr.addColorStop(0, `rgba(${80 + rnd(i + 3) * 80 | 0},${70 + rnd(i + 4) * 60 | 0},${140 + rnd(i + 5) * 90 | 0},.10)`); gr.addColorStop(1, 'rgba(0,0,0,0)'); ng.fillStyle = gr; ng.fillRect(0, 0, 512, 512);
    }
    const nebula = (x, y, z, s, tint) => {
        const m = new THREE.Mesh(new THREE.PlaneGeometry(s, s), new THREE.MeshBasicMaterial({ map: tex(nebC), color: tint, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
        m.position.set(x, y, z); m.lookAt(0, 0, 0); sky.add(m); return m;
    };
    nebula(200, 150, -1800, 2600, 0xffffff); nebula(-1900, 700, 600, 2200, 0xffb0c8); nebula(1500, -900, 1200, 2000, 0x9fd8ff);
    const spaceSun = new THREE.DirectionalLight(0xfff4e6, 2.1); spaceSun.position.set(-300, 160, 260); space.add(spaceSun);
    space.add(new THREE.AmbientLight(0x2a3040, 0.25));
    const envScene = new THREE.Scene();
    envScene.add(new THREE.Mesh(new THREE.SphereGeometry(100, 32, 16), new THREE.ShaderMaterial({
        side: THREE.BackSide,
        vertexShader: 'varying vec3 vD; void main(){ vD=normalize(position); gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }',
        fragmentShader: 'varying vec3 vD; void main(){ float d=max(dot(vD,normalize(vec3(-.7,.37,.6))),0.); gl_FragColor=vec4(vec3(.015,.02,.03)+vec3(1.,.95,.85)*pow(d,40.)*6.+vec3(.1,.08,.06)*pow(d,3.),1.); }',
    })));
    space.environment = k.cubeEnv(envScene);
    await pause();

    function planetTexture(kind, W = 1024, H = 512) {
        const c = canvas(W, H), g = c.getContext('2d'), img = g.createImageData(W, H), d = img.data;
        const hc = canvas(W, H), hg = hc.getContext('2d'), himg = hg.createImageData(W, H), hd = himg.data;
        const lc = canvas(W, H), lg2 = lc.getContext('2d'), limg = lg2.createImageData(W, H), ld = limg.data;
        for (let y = 0; y < H; y++) {
            const lat = (y / H - 0.5) * Math.PI;
            for (let x = 0; x < W; x++) {
                const lon = x / W * Math.PI * 2, px = Math.cos(lat) * Math.cos(lon), py = Math.sin(lat), pz = Math.cos(lat) * Math.sin(lon);
                let r, gg, b; const n = fbm(px * 2.4 + 3, py * 2.4, pz * 2.4, 5), m = fbm(px * 7, py * 7 + 9, pz * 7, 3);
                if (kind === 'home') {
                    const band = 0.5 + 0.5 * Math.sin(py * 9 + n * 5), t = clamp(n * 1.6 - 0.35);
                    r = lerp(205, 140, t) - band * 22 + m * 20; gg = lerp(160, 84, t) - band * 18 + m * 14; b = lerp(112, 52, t) - band * 12;
                    { const cn = clamp((n - 0.56) / 0.14); r *= 1 - cn * 0.3; gg *= 1 - cn * 0.36; b *= 1 - cn * 0.4; }
                    if (Math.abs(py) > 0.9) { const q = clamp((Math.abs(py) - 0.9) * 12); r = lerp(r, 236, q); gg = lerp(gg, 232, q); b = lerp(b, 226, q); }
                } else if (kind === 'lsx') {
                    if (n < 0.52) { const t = clamp(n / 0.52); r = lerp(8, 28, t); gg = lerp(40, 110, t); b = lerp(80, 150, t); }
                    else { const t = clamp((n - 0.52) * 4); r = lerp(70, 120, t) + m * 30; gg = lerp(110, 96, t) + m * 20; b = lerp(58, 70, t); }
                    if (Math.abs(py) > 0.84) { const q = clamp((Math.abs(py) - 0.84) * 10); r = lerp(r, 240, q); gg = lerp(gg, 246, q); b = lerp(b, 250, q); }
                } else if (kind === 'giant') {   // banded gas: cream, rust and a storm
                    const band = Math.sin(py * 22 + n * 3.2) * 0.5 + 0.5, fine = Math.sin(py * 70 + m * 4) * 0.5 + 0.5;
                    r = lerp(222, 170, band) - fine * 18; gg = lerp(196, 118, band) - fine * 14; b = lerp(150, 78, band) - fine * 10;
                    const st = clamp(1 - Math.hypot((lon - 2.2) * 2.2, (py + 0.32) * 7)); r = lerp(r, 196, st); gg = lerp(gg, 92, st); b = lerp(b, 62, st);
                } else if (kind === 'ice') {
                    const cr = clamp((m - 0.6) * 4); r = lerp(170, 220, n) - cr * 30; gg = lerp(196, 232, n) - cr * 25; b = lerp(214, 246, n) - cr * 10;
                } else if (kind === 'moon') { const cr = clamp((m - 0.55) * 5); r = gg = b = 150 - n * 70 - cr * 40; }
                else { const cl = clamp((fbm(px * 3.5, py * 6 + 4, pz * 3.5, 5) - 0.47) * 3.2); r = gg = b = 255; d[(y * W + x) * 4 + 3] = cl * 235; }
                const i = (y * W + x) * 4; d[i] = r; d[i + 1] = gg; d[i + 2] = b; if (kind !== 'cloud') d[i + 3] = 255;
                const hv = kind === 'lsx' ? (n < 0.52 ? 70 : 150 + (n - 0.52) * 500 + m * 60) : n * 255 + m * 40; hd[i] = hd[i + 1] = hd[i + 2] = clamp(hv, 0, 255); hd[i + 3] = 255;
                const city = kind === 'lsx' && n > 0.53 && n < 0.7 && Math.abs(py) < 0.8 && hash(x, y, 7) > 0.93 - m * 0.1 ? 255 : 0; ld[i] = city; ld[i + 1] = city * 0.75; ld[i + 2] = city * 0.4; ld[i + 3] = 255;
            }
        }
        g.putImageData(img, 0, 0); hg.putImageData(himg, 0, 0); lg2.putImageData(limg, 0, 0); c.bump = hc; c.lights = lc; return c;
    }
    const halo = (fragment) => (r, color, q, back = false) => new THREE.Mesh(new THREE.SphereGeometry(r, 64, 32), new THREE.ShaderMaterial({
        transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: back ? THREE.BackSide : THREE.FrontSide,
        uniforms: { c: { value: new THREE.Color(color) }, k: { value: q } },
        vertexShader: 'varying vec3 vN; varying vec3 vV; void main(){ vN=normalize(normalMatrix*normal); vec4 mv=modelViewMatrix*vec4(position,1.); vV=normalize(-mv.xyz); gl_Position=projectionMatrix*mv; }',
        fragmentShader: fragment,
    }));
    const atmoMesh = halo('uniform vec3 c; uniform float k; varying vec3 vN; varying vec3 vV; void main(){ float f=pow(clamp(1.-abs(dot(vN,vV)),0.,1.),.9); float a=pow(1.-f,3.)*k; gl_FragColor=vec4(c*a,a); }');
    const rimMesh = halo('uniform vec3 c; uniform float k; varying vec3 vN; varying vec3 vV; void main(){ float f=pow(1.-abs(dot(vN,vV)),3.); gl_FragColor=vec4(c*f*k,f*k); }');
    const atmo = (r, color, q) => atmoMesh(r, color, q, true), rim = (r, color, q) => rimMesh(r, color, q);

    // ---- HOME and LSX, spaced out to the two sides of the screen -------------------------------------------------
    const HOMEC = V(-190, -38, 0), HOMER = 58, LSXC = V(190, -30, -30), LSXR = 50;
    const homeT = planetTexture('home');
    const homeP = new THREE.Mesh(new THREE.SphereGeometry(HOMER, 96, 48), new THREE.MeshStandardMaterial({ map: tex(homeT), bumpMap: tex(homeT.bump, 1, 1, false), bumpScale: 1.2, roughness: 0.95 }));
    homeP.position.copy(HOMEC); space.add(homeP);
    const homeRim = rim(HOMER * 1.005, '#9fc0e0', 1.3); homeRim.position.copy(HOMEC); space.add(homeRim);
    const homeHalo = atmo(HOMER * 1.07, '#8fb4dc', 0.9); homeHalo.position.copy(HOMEC); space.add(homeHalo);
    await pause();
    const lsxT = planetTexture('lsx');
    const lsxP = new THREE.Mesh(new THREE.SphereGeometry(LSXR, 96, 48), new THREE.MeshStandardMaterial({ map: tex(lsxT), bumpMap: tex(lsxT.bump, 1, 1, false), bumpScale: 1.4, emissiveMap: tex(lsxT.lights), emissive: 0xffc070, emissiveIntensity: 0.55, roughnessMap: tex(lsxT.bump, 1, 1, false), roughness: 1, metalness: 0 }));
    lsxP.position.copy(LSXC); space.add(lsxP);
    await pause();
    const clouds = new THREE.Mesh(new THREE.SphereGeometry(LSXR * 1.012, 96, 48), new THREE.MeshStandardMaterial({ map: tex(planetTexture('cloud')), transparent: true, depthWrite: false, roughness: 1 }));
    clouds.position.copy(LSXC); space.add(clouds);
    const lsxRim = rim(LSXR * 1.02, '#7fd0ff', 1.6); lsxRim.position.copy(LSXC); space.add(lsxRim);
    const lsxHalo = atmo(LSXR * 1.09, '#6cc6ff', 1.1); lsxHalo.position.copy(LSXC); space.add(lsxHalo);
    // auroras: green and violet curtains waving round both of LSX's poles
    const auroraU = { t: { value: 0 } };
    const auroraM = new THREE.ShaderMaterial({
        uniforms: auroraU, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
        vertexShader: 'varying vec2 vU; void main(){ vU=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }',
        fragmentShader: `uniform float t; varying vec2 vU; void main(){ float x=vU.x*6.2832;
            float w=.5+.5*sin(x*7.+t*.7+sin(x*3.-t*.4)*2.), band=pow(w,3.)*(.35+.65*(.5+.5*sin(x*23.+t*1.7)));
            float fade=smoothstep(0.,.25,vU.y)*(1.-vU.y); vec3 c=mix(vec3(.2,1.,.55),vec3(.6,.3,1.),vU.y);
            gl_FragColor=vec4(c*band*fade*.9,band*fade*.9); }`,
    });
    for (const sgn of [1, -1]) {
        const cur = new THREE.Mesh(new THREE.CylinderGeometry(LSXR * 0.36, LSXR * 0.3, LSXR * 0.09, 96, 1, true), auroraM);
        cur.position.copy(LSXC).add(V(0, sgn * LSXR * 0.955, 0)); if (sgn < 0) cur.rotation.x = Math.PI; space.add(cur);
    }
    await pause();
    const moonT = planetTexture('moon', 512, 256);
    const moon = new THREE.Mesh(new THREE.SphereGeometry(8, 48, 24), new THREE.MeshStandardMaterial({ map: tex(moonT), bumpMap: tex(moonT.bump, 1, 1, false), bumpScale: 1.5, roughness: 1 })); space.add(moon);
    const station = new THREE.Group(); space.add(station);
    add(station, new THREE.TorusGeometry(6, 0.7, 12, 48), mat.hullB); add(station, new THREE.CylinderGeometry(1.2, 1.2, 8, 16), mat.steel).rotation.x = Math.PI / 2;
    for (let i = 0; i < 4; i++) { const sp = add(station, new THREE.BoxGeometry(0.3, 0.3, 6), mat.dark); sp.position.set(Math.cos(i * Math.PI / 2) * 3, Math.sin(i * Math.PI / 2) * 3, 0); sp.rotation.set(0, 0, i * Math.PI / 2 + Math.PI / 2); }
    const panelC = canvas(128), pc = panelC.getContext('2d'); pc.fillStyle = '#132b4a'; pc.fillRect(0, 0, 128, 128); pc.strokeStyle = '#3a6a9a'; for (let q = 0; q < 128; q += 16) { pc.strokeRect(q, 0, 16, 128); pc.beginPath(); pc.moveTo(0, q); pc.lineTo(128, q); pc.stroke(); }
    const panelM = new THREE.MeshStandardMaterial({ map: tex(panelC, 4, 1), metalness: 0.6, roughness: 0.3 });
    for (const z of [-5.5, 5.5]) add(station, new THREE.BoxGeometry(12, 0.1, 3), panelM, 0, 0, z);
    for (let i = 0; i < 12; i++) add(station, new THREE.BoxGeometry(0.4, 0.4, 0.4), winMat, Math.cos(i / 12 * Math.PI * 2) * 6, Math.sin(i / 12 * Math.PI * 2) * 6, 0.72);
    const stationLamp = add(station, new THREE.SphereGeometry(0.4, 6, 4), glow(0xff3b30), 0, 0, 4.2);
    station.position.copy(HOMEC).add(V(52, 50, 44)); station.scale.setScalar(1.3);
    const rockM = new THREE.MeshStandardMaterial({ color: 0x6f665c, roughness: 1, flatShading: true });
    const rocks = []; for (let i = 0; i < 70; i++) {
        const r = new THREE.Mesh(new THREE.DodecahedronGeometry(0.6 + rnd(i + 400) * 2.4, 0), rockM);
        r.position.set((i % 2 ? 1 : -1) * (120 + rnd(i + 401) * 200), -95 + rnd(i + 402) * 50, -150 + rnd(i + 403) * 110); r.userData.s = V(rnd(i + 404), rnd(i + 405), rnd(i + 406)); space.add(r); rocks.push(r);
    }
    // space traffic: small freighters between the planets, satellites round LSX, and a small moon for LSX
    const traffic = [0, 1, 2].map(() => { const t = ship.clone(); t.scale.setScalar(0.12); t.traverse((c) => { if (c.isLight) c.visible = false; }); space.add(t); return t; });
    const satPanel = new THREE.MeshStandardMaterial({ map: tex(panelC, 1, 2), metalness: 0.6, roughness: 0.3 });
    const sats = Array.from({ length: 6 }, (_, q) => {
        const g = new THREE.Group(); add(g, new THREE.BoxGeometry(0.8, 0.8, 1.2), mat.steel); add(g, new THREE.BoxGeometry(0.05, 3.2, 1), satPanel, 0, 0, 0).rotation.z = Math.PI / 2;
        add(g, new THREE.SphereGeometry(0.12, 6, 4), new THREE.MeshBasicMaterial({ color: q % 2 ? 0xff3b30 : 0x3cff8a }), 0, 0.5, 0); space.add(g); return g;
    });
    const lsxMoonT = planetTexture('moon', 256, 128);
    const lsxMoon = new THREE.Mesh(new THREE.SphereGeometry(5, 32, 16), new THREE.MeshStandardMaterial({ map: tex(lsxMoonT), bumpMap: tex(lsxMoonT.bump, 1, 1, false), bumpScale: 1, roughness: 1, color: 0xd8cfc4 })); space.add(lsxMoon);
    await pause();

    // ---- the rest of the solar system ------------------------------------------------------------------------------
    // the orbits lie in the plane through the sun, HOME and LSX
    const SUNP = spaceSun.position.clone().normalize().multiplyScalar(2600).add(V(0, -40, 0)), SUNR = 120;
    const e1 = HOMEC.clone().sub(SUNP).normalize(), nrm = e1.clone().cross(LSXC.clone().sub(SUNP)).normalize();
    if (nrm.y < 0) nrm.negate();
    const e2 = nrm.clone().cross(e1).normalize();
    const onOrbit = (r, a, lift = 0) => SUNP.clone().addScaledVector(e1, Math.cos(a) * r).addScaledVector(e2, Math.sin(a) * r).addScaledVector(nrm, lift);
    const angleOf = (p) => { const d = p.clone().sub(SUNP); return Math.atan2(d.dot(e2), d.dot(e1)); };
    const R_HOME = HOMEC.distanceTo(SUNP), R_LSX = LSXC.distanceTo(SUNP), A_LSX = angleOf(LSXC);
    // the sun's surface: boiling granulation, darker towards the limb, with a few sunspots drifting round
    const sunU = { t: { value: 0 } };
    const sunM = new THREE.Mesh(new THREE.SphereGeometry(SUNR, 64, 32), new THREE.ShaderMaterial({
        uniforms: sunU, fog: false,
        vertexShader: 'varying vec3 vP; varying vec3 vN; varying vec3 vV; void main(){ vP=position; vN=normalize(normalMatrix*normal); vec4 mv=modelViewMatrix*vec4(position,1.); vV=normalize(-mv.xyz); gl_Position=projectionMatrix*mv; }',
        fragmentShader: `uniform float t; varying vec3 vP; varying vec3 vN; varying vec3 vV;
            float h(vec3 p){ return fract(sin(dot(p,vec3(127.1,311.7,74.7)))*43758.5453); }
            float n3(vec3 p){ vec3 i=floor(p), f=fract(p); f=f*f*(3.-2.*f);
                return mix(mix(mix(h(i),h(i+vec3(1,0,0)),f.x),mix(h(i+vec3(0,1,0)),h(i+vec3(1,1,0)),f.x),f.y),mix(mix(h(i+vec3(0,0,1)),h(i+vec3(1,0,1)),f.x),mix(h(i+vec3(0,1,1)),h(i+vec3(1,1,1)),f.x),f.y),f.z); }
            void main(){ vec3 p=normalize(vP);
                float g=n3(p*28.+vec3(t*.30))*.55+n3(p*60.-vec3(t*.5))*.3+n3(p*7.+vec3(0.,t*.05,0.))*.35;
                float mu=clamp(dot(vN,vV),0.,1.), limb=.42+.58*pow(mu,.55);
                float a=t*.01; vec3 q=vec3(p.x*cos(a)-p.z*sin(a),p.y,p.x*sin(a)+p.z*cos(a));
                float spots=smoothstep(.73,.8,n3(q*5.+11.))*smoothstep(.55,.2,abs(q.y));
                vec3 c=mix(vec3(1.,.62,.26),vec3(1.,.97,.86),g)*limb; c*=1.-spots*.55; c+=vec3(.25,.12,0.)*pow(1.-mu,3.);
                gl_FragColor=vec4(c*1.25,1.); }`,
    }));
    sunM.position.copy(SUNP); space.add(sunM);
    const sunGlow = [[SUNR * 5, 0xffd9a0, 0.9], [SUNR * 14, 0xff9a50, 0.35], [SUNR * 34, 0xff8a40, 0.12]].map(([s, c, o]) => {
        const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: c, transparent: true, opacity: o, blending: THREE.AdditiveBlending, depthWrite: false }));
        sp.scale.setScalar(s); sp.position.copy(SUNP); space.add(sp); return sp;
    });
    // a ringed gas giant and a small ice world further out
    const R_GIANT = 3900, R_ICE = 4600, GIANTR = 170, ICER = 40;
    // the outer planets go round the far side, behind the camera of the both-planets view, so the middle stays clear
    const behind = (r) => { let best = 0, bz = -1e9; for (let a = 0; a < Math.PI * 2; a += 0.02) { const z = onOrbit(r, a).z; if (z > bz) { bz = z; best = a; } } return best; };
    const giantT = planetTexture('giant', 1024, 512);
    const giant = new THREE.Mesh(new THREE.SphereGeometry(GIANTR, 64, 32), new THREE.MeshStandardMaterial({ map: tex(giantT), roughness: 1 }));
    giant.position.copy(onOrbit(R_GIANT, behind(R_GIANT) + 0.55, 60)); giant.rotation.z = 0.35; space.add(giant);
    const giantHalo = atmo(GIANTR * 1.05, '#ffcf96', 0.7); giantHalo.position.copy(giant.position); space.add(giantHalo);
    const ringC = canvas(512, 8), rc = ringC.getContext('2d');
    for (let x = 0; x < 512; x++) { const u = x / 512, a = (0.35 + 0.65 * fbm(u * 30, 1, 2, 3)) * (u < 0.08 || (u > 0.55 && u < 0.6) ? 0.1 : 1) * clamp(u * 10) * clamp((1 - u) * 6); rc.fillStyle = `rgba(${220 - u * 50 | 0},${196 - u * 60 | 0},${160 - u * 70 | 0},${a.toFixed(3)})`; rc.fillRect(x, 0, 1, 8); }
    const ringGeo = new THREE.RingGeometry(GIANTR * 1.3, GIANTR * 2.3, 160, 1);
    { const p = ringGeo.attributes.position, uv = ringGeo.attributes.uv; for (let i = 0; i < p.count; i++) { const r = Math.hypot(p.getX(i), p.getY(i)); uv.setXY(i, (r - GIANTR * 1.3) / GIANTR, 0.5); } }
    const ringT = tex(ringC); ringT.wrapS = ringT.wrapT = THREE.ClampToEdgeWrapping;
    const giantRing = new THREE.Mesh(ringGeo, new THREE.MeshStandardMaterial({ map: ringT, transparent: true, side: THREE.DoubleSide, depthWrite: false, roughness: 1 }));
    giantRing.position.copy(giant.position); giantRing.rotation.set(-Math.PI / 2 + 0.45, 0.2, 0.35); space.add(giantRing);
    await pause();
    const iceT = planetTexture('ice', 512, 256);
    const ice = new THREE.Mesh(new THREE.SphereGeometry(ICER, 48, 24), new THREE.MeshStandardMaterial({ map: tex(iceT), bumpMap: tex(iceT.bump, 1, 1, false), bumpScale: 1, roughness: 0.7 }));
    ice.position.copy(onOrbit(R_ICE, behind(R_ICE) - 0.9, -40)); space.add(ice);
    const iceHalo = atmo(ICER * 1.1, '#bfe6ff', 0.8); iceHalo.position.copy(ice.position); space.add(iceHalo);
    // the asteroid belt between LSX and the giant
    const BELT = 1400, R_BELT = 3350, beltI = new THREE.InstancedMesh(new THREE.DodecahedronGeometry(1, 0), rockM, BELT);
    { const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler();
        for (let i = 0; i < BELT; i++) {
            const a = rnd(i + 9000) * Math.PI * 2, r = R_BELT + (rnd(i + 9001) + rnd(i + 9002) - 1) * 150, s = 3 + Math.pow(rnd(i + 9003), 3) * 18;
            e.set(rnd(i + 9004) * 6, rnd(i + 9005) * 6, 0); q.setFromEuler(e);
            m4.compose(onOrbit(r, a, (rnd(i + 9006) - 0.5) * 50).sub(SUNP), q, V(s, s * (0.6 + rnd(i + 9007) * 0.5), s)); beltI.setMatrixAt(i, m4);
        } }
    const belt = new THREE.Group(); belt.position.copy(SUNP); belt.add(beltI); space.add(belt);
    const DUSTN = 3000, beltDust = new THREE.BufferGeometry(), bd = new Float32Array(DUSTN * 3);
    for (let i = 0; i < DUSTN; i++) { const p = onOrbit(R_BELT + (rnd(i + 9100) - 0.5) * 320, rnd(i + 9101) * Math.PI * 2, (rnd(i + 9102) - 0.5) * 70).sub(SUNP); bd.set([p.x, p.y, p.z], i * 3); }
    beltDust.setAttribute('position', new THREE.BufferAttribute(bd, 3));
    const beltDustM = new THREE.PointsMaterial({ color: 0x8a7f72, size: 1.5, sizeAttenuation: false, transparent: true, opacity: 0.55, depthWrite: false });
    belt.add(new THREE.Points(beltDust, beltDustM));
    // faint orbit lines
    const orbitM = new THREE.LineBasicMaterial({ color: 0x8fb4dc, transparent: true, opacity: 0.16, depthWrite: false });
    const orbitLine = (r) => { const pts = []; for (let i = 0; i < 256; i++) pts.push(onOrbit(r, i / 256 * Math.PI * 2)); const l = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts), orbitM); space.add(l); return l; };
    // a small cratered world close in to the sun, baked on the day side
    const R_INNER = 1250, INNERR = 26, innerT = planetTexture('moon', 512, 256);
    const inner = new THREE.Mesh(new THREE.SphereGeometry(INNERR, 48, 24), new THREE.MeshStandardMaterial({ map: tex(innerT), bumpMap: tex(innerT.bump, 1, 1, false), bumpScale: 1.2, color: 0xd8b89a, roughness: 1 }));
    inner.position.copy(onOrbit(R_INNER, behind(R_INNER) - 2.1, 20)); space.add(inner);
    const orbits = [R_HOME, R_LSX, R_GIANT, R_ICE, R_INNER].map(orbitLine);
    // the corona: long faint streamers round the sun that turn slowly
    const coronaC = canvas(512), cg = coronaC.getContext('2d'); cg.translate(256, 256);
    for (let i = 0; i < 40; i++) {
        const a = rnd(i + 9300) * Math.PI * 2, len = 120 + rnd(i + 9301) * 130, w = 0.03 + rnd(i + 9302) * 0.06;
        const gr = cg.createLinearGradient(0, 0, Math.cos(a) * len, Math.sin(a) * len); gr.addColorStop(0.2, 'rgba(255,220,170,.35)'); gr.addColorStop(1, 'rgba(255,200,140,0)');
        cg.fillStyle = gr; cg.beginPath(); cg.moveTo(Math.cos(a - w) * 50, Math.sin(a - w) * 50); cg.lineTo(Math.cos(a) * len, Math.sin(a) * len); cg.lineTo(Math.cos(a + w) * 50, Math.sin(a + w) * 50); cg.fill();
    }
    const corona = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex(coronaC), color: 0xffe0b8, transparent: true, opacity: 0.8, blending: THREE.AdditiveBlending, depthWrite: false }));
    corona.scale.setScalar(SUNR * 5.2); corona.position.copy(SUNP); space.add(corona);
    // a comet on a long thin orbit: a bright head, a straight blue ion tail pointing away from the sun and a curved dusty one
    const cometHead = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: 0xdff4ff, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false })); space.add(cometHead);
    const CT = 420, cometGeo = pointsGeo(CT), comet = new THREE.Points(cometGeo, softPoints('#bfe4ff', THREE.AdditiveBlending)); comet.frustumCulled = false; space.add(comet);
    const DT = 420, dustGeo = pointsGeo(DT), dust = new THREE.Points(dustGeo, softPoints('#ffe6c0', THREE.AdditiveBlending)); dust.frustumCulled = false; space.add(dust);
    const cometAt = (C) => {   // an ellipse with the sun at one focus, swinging slowly round
        const ecc = 0.82, sa = 3000, M = C * 0.004 + 1.2; let E = M; for (let i = 0; i < 6; i++) E = M + ecc * Math.sin(E);
        const x = sa * (Math.cos(E) - ecc), y = sa * Math.sqrt(1 - ecc * ecc) * Math.sin(E), rot = 2.4;
        return SUNP.clone().addScaledVector(e1, x * Math.cos(rot) - y * Math.sin(rot)).addScaledVector(e2, x * Math.sin(rot) + y * Math.cos(rot)).addScaledVector(nrm, 140 + y * 0.08);
    };
    const cometPos = V(0, 0, 0);
    function cometFrame(C, deep) {
        const on = deep > 0.02; cometHead.visible = comet.visible = dust.visible = on; if (!on) return;
        cometPos.copy(cometAt(C)); cometHead.position.copy(cometPos);
        const away = cometPos.clone().sub(SUNP), rs = away.length(); away.normalize();
        const heat = clamp(1600 / rs), len = 200 + heat * 900, vel = cometAt(C + 1).sub(cometPos).normalize();
        cometHead.scale.setScalar(70 + heat * 150); cometHead.material.opacity = deep * (0.6 + heat * 0.4);
        const cp = cometGeo.attributes.position, ca = cometGeo.attributes.aA, cs = cometGeo.attributes.aS;
        for (let i = 0; i < CT; i++) {
            const f = ((i / CT) + C * 0.08) % 1, sp = (rnd(i + 9400) - 0.5) * 18 * (0.3 + f);
            const p = cometPos.clone().addScaledVector(away, f * len).addScaledVector(nrm, sp).addScaledVector(vel, (rnd(i + 9401) - 0.5) * 14 * f);
            cp.setXYZ(i, p.x, p.y, p.z); ca.setX(i, (1 - f) * 0.4 * deep * (0.5 + heat)); cs.setX(i, 40 + f * 90);
        }
        const dp = dustGeo.attributes.position, da = dustGeo.attributes.aA, ds = dustGeo.attributes.aS;
        for (let i = 0; i < DT; i++) {
            const f = ((i / DT) + C * 0.05) % 1, bend = f * f * len * 0.45;
            const p = cometPos.clone().addScaledVector(away, f * len * 0.8).addScaledVector(vel, -bend).addScaledVector(nrm, (rnd(i + 9500) - 0.5) * 30 * f);
            dp.setXYZ(i, p.x, p.y, p.z); da.setX(i, (1 - f) * 0.3 * deep * (0.5 + heat)); ds.setX(i, 50 + f * 120);
        }
        cp.needsUpdate = ca.needsUpdate = cs.needsUpdate = dp.needsUpdate = da.needsUpdate = ds.needsUpdate = true;
    }
    await pause();

    function spaceExtras(C) {
        traffic.forEach((t, q) => {
            const f = ((C * 0.02 + q / 3) % 1), dirOut = q % 2 === 0, a = HOMEC.clone().add(V(40, -30 + q * 22, -50 - q * 20)), b = LSXC.clone().add(V(-40, -25 + q * 18, -45 - q * 15));
            const p0 = dirOut ? a : b, p1 = dirOut ? b : a; t.position.copy(p0).lerp(p1, f); t.quaternion.setFromUnitVectors(V(1, 0, 0), p1.clone().sub(p0).normalize()); t.visible = f > 0.03 && f < 0.97;
        });
        sats.forEach((g, q) => {
            const a = C * (0.25 + q * 0.03) + q * 1.05, r = LSXR + 8 + (q % 3) * 4, tilt = 0.4 + q * 0.25;
            g.position.set(LSXC.x + Math.cos(a) * r, LSXC.y + Math.sin(a) * r * Math.sin(tilt), LSXC.z + Math.sin(a) * r * Math.cos(tilt)); g.rotation.set(C * 0.3, a, 0);
        });
        const ma = C * 0.18 + 3; lsxMoon.position.set(LSXC.x + Math.cos(ma) * 78, LSXC.y + 20 + Math.sin(ma) * 10, LSXC.z + Math.sin(ma) * 60);
        const a = C * 0.12 + 1; moon.position.copy(HOMEC).add(V(Math.cos(a) * 92, Math.sin(a) * 26, Math.sin(a) * -70)); moon.rotation.y = C * 0.05;
        station.rotation.set(0.5, C * 0.15, 0.3); stationLamp.visible = Math.floor(C * 1.5) % 2 === 0;
        rocks.forEach((r) => { r.rotation.set(C * r.userData.s.x * 0.5, C * r.userData.s.y * 0.5, 0); });
        giant.rotation.y = C * 0.02; ice.rotation.y = C * 0.01; belt.quaternion.setFromAxisAngle(nrm, C * 0.0015);
        sunGlow.forEach((s, q) => { s.material.rotation = C * 0.01 * (q + 1); });
        sunU.t.value = C; auroraU.t.value = C; corona.material.rotation = C * 0.004; inner.rotation.y = C * 0.004;
    }
    // where the base is on HOME (N, P) and the port on LSX (LN, LP), with the tangents along each surface
    const N = V(0.42, 0.36, 0.83).normalize(), P = HOMEC.clone().addScaledVector(N, HOMER);
    const tA = N.clone().cross(V(0, 1, 0)).normalize(), tB = N.clone().cross(tA).normalize();
    const orbitClouds = new THREE.Group(); space.add(orbitClouds);
    for (let i = 0; i < 60; i++) {
        const sp = new THREE.Sprite(cloudMat(0.8, 0xfff2e2)), sc = 6 + rnd(i + 860) * 14;
        sp.position.copy(P).addScaledVector(N, 1.5 + rnd(i + 861) * 7).addScaledVector(tA, (rnd(i + 862) - 0.5) * 60).addScaledVector(tB, (rnd(i + 863) - 0.5) * 60); sp.scale.set(sc, sc * 0.6, 1); orbitClouds.add(sp);
    }
    // high-detail surface patch round the base, so zooming down from orbit shows dunes, canyons and the lit spaceport
    const surf = (() => {
        const W = 1024, c = canvas(W), g = c.getContext('2d'), img = g.createImageData(W, W), d = img.data, lc = canvas(W), lg = lc.getContext('2d'), li = lg.createImageData(W, W), ld = li.data;
        for (let y = 0; y < W; y++) {
            for (let x = 0; x < W; x++) {
                const u = x / W - 0.5, v = y / W - 0.5, rr = Math.hypot(u, v) * 2, i = (y * W + x) * 4;
                const n = fbm(u * 9 + 5, v * 9, 1.7, 5), m = fbm(u * 40, v * 40 + 3, 2.2, 3), dune = Math.sin((u * 0.8 + v) * 260 + n * 30) * 0.5 + 0.5;
                const canyon = clamp(1 - Math.abs(fbm(u * 5 + 11, v * 5, 4.1, 4) - 0.5) * 26), mesa = clamp((n - 0.6) * 8);
                let r = 204 + m * 26 - dune * 16 * (1 - mesa), gg = 158 + m * 18 - dune * 13 * (1 - mesa), b = 110 + m * 8 - dune * 9 * (1 - mesa);
                r = lerp(r, 150, mesa * 0.7); gg = lerp(gg, 92, mesa * 0.7); b = lerp(b, 60, mesa * 0.7);
                const base = clamp(1 - rr * 14); r = lerp(r, r * (1 - canyon * 0.55), 1 - base); gg = lerp(gg, gg * (1 - canyon * 0.6), 1 - base); b = lerp(b, b * (1 - canyon * 0.62), 1 - base);
                d[i] = r; d[i + 1] = gg; d[i + 2] = b; d[i + 3] = 255 * clamp((1 - rr) * 4); ld[i + 3] = 255;
            }
        }
        g.putImageData(img, 0, 0); lg.putImageData(li, 0, 0);
        // spaceport marks at the centre, laid out like the desert base (1 px ~ 4 m), with the factory to the north
        const C = W / 2, s = 0.25, padAt = (px, pz, rad) => {
            g.fillStyle = '#8d8a84'; g.beginPath(); g.arc(C + px * s, C + pz * s, rad, 0, 7); g.fill(); g.strokeStyle = '#e8813a'; g.lineWidth = 1; g.stroke();
            lg.fillStyle = '#ffd08a'; for (let q = 0; q < 8; q++) { const a = q / 8 * Math.PI * 2; lg.fillRect(C + px * s + Math.cos(a) * rad - 0.5, C + pz * s + Math.sin(a) * rad - 0.5, 1.5, 1.5); }
        };
        g.strokeStyle = 'rgba(90,80,70,.8)'; g.lineWidth = 1.5; g.beginPath(); g.moveTo(C, C); g.lineTo(C - 58 * s, C - 34 * s); g.moveTo(C, C); g.lineTo(C - 92 * s, C - 66 * s); g.moveTo(C, C); g.lineTo(C + 84 * s, C - 62 * s); g.moveTo(C, C); g.lineTo(C, C - 118 * s); g.moveTo(C, C); g.lineTo(C + 420 * s, C + 260 * s); g.stroke();
        padAt(0, 0, 7); padAt(-92, -66, 5); padAt(84, -62, 5);
        g.fillStyle = '#b9b6ae'; g.fillRect(C - 32 * s, C - 135 * s, 64 * s, 34 * s); lg.fillStyle = '#ffe2b0'; lg.fillRect(C - 30 * s, C - 133 * s, 60 * s, 2);
        g.fillStyle = '#c9ccd0'; g.fillRect(C - 62 * s, C - 38 * s, 4, 3); g.fillStyle = '#23324a'; for (let q = 0; q < 6; q++) g.fillRect(C + (20 + q * 5) * s, C + 40 * s, 1, 4);
        lg.fillStyle = '#ffe2b0'; lg.fillRect(C - 62 * s, C - 38 * s, 4, 3); for (let q = 0; q < 40; q++) { const a = rnd(q + 1500) * 7, dd = 4 + rnd(q + 1501) * 30; lg.globalAlpha = 0.5; lg.fillRect(C + Math.cos(a) * dd, C + Math.sin(a) * dd, 1, 1); } lg.globalAlpha = 1;
        return { c, lc };
    })();
    const PATCH_A = 0.3, patchGeo = new THREE.SphereGeometry(HOMER * 1.0012, 160, 60, 0, Math.PI * 2, 0, PATCH_A);
    { const pos = patchGeo.attributes.position, uv = patchGeo.attributes.uv, S = HOMER * 1.0012 * Math.sin(PATCH_A); for (let i = 0; i < pos.count; i++) uv.setXY(i, 0.5 + pos.getX(i) / S / 2, 0.5 - pos.getZ(i) / S / 2); }
    const surfPatch = new THREE.Mesh(patchGeo, new THREE.MeshStandardMaterial({ map: tex(surf.c), emissiveMap: tex(surf.lc), emissive: 0xffc27a, emissiveIntensity: 1.4, transparent: true, roughness: 1, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 }));
    surfPatch.position.copy(HOMEC); surfPatch.quaternion.setFromUnitVectors(V(0, 1, 0), N);
    { const ax = V(1, 0, 0).applyQuaternion(surfPatch.quaternion); surfPatch.quaternion.premultiply(new THREE.Quaternion().setFromUnitVectors(ax, tA.clone().negate())); }
    space.add(surfPatch);
    await pause();
    // LSX port: where deliveries land. A detailed patch of coast, farmland and the lit port, with cargo trucks on the roads
    const LN = V(-1, 0.25, 0.55).normalize(), LP = LSXC.clone().addScaledVector(LN, LSXR);
    const lA = LN.clone().cross(V(0, 1, 0)).normalize(), lB = LN.clone().cross(lA).normalize();
    const portTex = (() => {
        const W = 1024, c = canvas(W), g = c.getContext('2d'), img = g.createImageData(W, W), d = img.data, lc = canvas(W), lg = lc.getContext('2d'), li = lg.createImageData(W, W), ld = li.data;
        for (let y = 0; y < W; y++) {
            for (let x = 0; x < W; x++) {
                const u = x / W - 0.5, v = y / W - 0.5, rr = Math.hypot(u, v) * 2, i = (y * W + x) * 4;
                const n = fbm(u * 6 + 2, v * 6, 8.3, 5) + clamp(0.18 - rr * 0.6), m = fbm(u * 50, v * 50, 1.1, 3), field = (Math.floor((u + 3) * 60 + m * 2) + Math.floor((v + 3) * 44)) % 3;
                let r, gg, b;
                if (n < 0.47) { const t = clamp(n / 0.47); r = lerp(8, 30, t); gg = lerp(40, 105, t); b = lerp(80, 150, t); }
                else if (n < 0.49) { r = 196; gg = 184; b = 140; }
                else { r = 70 + m * 30 + field * 10; gg = 112 + m * 20 - field * 6; b = 58 + field * 4; if (n > 0.66) { r = lerp(r, 120, 0.6); gg = lerp(gg, 100, 0.6); b = lerp(b, 76, 0.6); } }
                d[i] = r; d[i + 1] = gg; d[i + 2] = b; d[i + 3] = 255 * clamp((1 - rr) * 4); ld[i + 3] = 255;
                const town = clamp(1 - Math.hypot(u - 0.13, v + 0.09) * 9) + clamp(1 - Math.hypot(u + 0.1, v - 0.12) * 11);
                if (n > 0.5 && town > 0 && hash(x, y, 9) > 1 - town * 0.12) { ld[i] = 255; ld[i + 1] = 196; ld[i + 2] = 118; d[i] = 128; d[i + 1] = 124; d[i + 2] = 118; }
            }
        }
        g.putImageData(img, 0, 0); lg.putImageData(li, 0, 0);
        const C = W / 2; g.fillStyle = '#6f6c68'; g.fillRect(C - 26, C - 20, 52, 40); g.fillStyle = '#8d8a84'; for (const [px, pz] of [[-17, -12], [17, -12], [0, 0]]) { g.beginPath(); g.arc(C + px, C + pz, 11, 0, 7); g.fill(); }
        g.strokeStyle = '#e8813a'; g.lineWidth = 1.2; g.beginPath(); g.arc(C, C, 11, 0, 7); g.stroke();
        lg.fillStyle = '#ffd08a'; for (let q = 0; q < 26; q++) lg.fillRect(C - 26 + (q % 13) * 4, C + (q < 13 ? -21 : 20), 1.5, 1.5);
        g.strokeStyle = 'rgba(70,66,60,.9)'; lg.strokeStyle = 'rgba(255,200,120,.35)'; g.lineWidth = lg.lineWidth = 1.5;
        const roads = [[C, C, C + 300, C - 120], [C, C, C - 260, C + 200], [C, C, C + 60, C + 330], [C, C, C - 180, C - 280]];
        roads.forEach(([a, b2, c2, d2]) => { for (const ctx of [g, lg]) { ctx.beginPath(); ctx.moveTo(a, b2); ctx.lineTo(c2, d2); ctx.stroke(); } });
        return { c, lc, roads, W };
    })();
    const PA = 0.26, portGeo = new THREE.SphereGeometry(LSXR * 1.0015, 160, 60, 0, Math.PI * 2, 0, PA);
    { const pos = portGeo.attributes.position, uv = portGeo.attributes.uv, S = LSXR * 1.0015 * Math.sin(PA); for (let i = 0; i < pos.count; i++) uv.setXY(i, 0.5 + pos.getX(i) / S / 2, 0.5 - pos.getZ(i) / S / 2); }
    const portPatch = new THREE.Mesh(portGeo, new THREE.MeshStandardMaterial({ map: tex(portTex.c), emissiveMap: tex(portTex.lc), emissive: 0xffc27a, emissiveIntensity: 1.6, transparent: true, roughness: 0.9, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 }));
    portPatch.position.copy(LSXC); portPatch.quaternion.setFromUnitVectors(V(0, 1, 0), LN);
    { const ax = V(1, 0, 0).applyQuaternion(portPatch.quaternion); portPatch.quaternion.premultiply(new THREE.Quaternion().setFromUnitVectors(ax, lA.clone().negate())); }
    space.add(portPatch);
    // map a texture pixel of the port patch back to a point on LSX (inverse of the uv mapping above)
    const portPoint = (px, py, lift = 0.06) => {
        const S = LSXR * Math.sin(PA), lx = (px / portTex.W - 0.5) * 2 * S, lz = -(py / portTex.W - 0.5) * 2 * S;
        const q = V(lx, Math.sqrt(Math.max(0, LSXR * LSXR - lx * lx - lz * lz)), lz).applyQuaternion(portPatch.quaternion); return LSXC.clone().add(q).addScaledVector(q.normalize(), lift);
    };
    const TRUCKS = 16, truckGeo = pointsGeo(TRUCKS);
    truckGeo.attributes.aA.array.fill(0.95); truckGeo.attributes.aS.array.fill(0.05);
    const trucks = new THREE.Points(truckGeo, softPoints('#ffcf8a', THREE.AdditiveBlending)); trucks.frustumCulled = false; space.add(trucks);
    function portFrame(C) {
        const tp = truckGeo.attributes.position;
        for (let i = 0; i < TRUCKS; i++) {
            const [a, b, c, d] = portTex.roads[i % 4], f = (C * (0.02 + (i % 3) * 0.006) + i / TRUCKS) % 1, back = i % 2, q = back ? 1 - f : f;
            const p = portPoint(lerp(a, c, q), lerp(b, d, q)); tp.setXYZ(i, p.x, p.y, p.z);
        }
        tp.needsUpdate = true;
    }
    const plasma = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: 0xff8a3a, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false })); space.add(plasma);
    const flash = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: 0xffd9a8, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false })); space.add(flash);
    const beacon = new THREE.Mesh(new THREE.SphereGeometry(0.9, 12, 8), new THREE.MeshBasicMaterial({ color: 0xe8813a, transparent: true })); beacon.position.copy(P); space.add(beacon);
    const TRAIL = 90, trailGeo = pointsGeo(TRAIL);
    const trail = new THREE.Points(trailGeo, softPoints('#ff9a50', THREE.AdditiveBlending)); trail.frustumCulled = false; space.add(trail);
    // the flight out (B) and home (Bret): up out of HOME's sky, a wide arc across, and down onto the LSX port
    const B = (f) => {
        const p0 = P.clone().addScaledVector(N, 4), p1 = P.clone().addScaledVector(N, 70).add(V(20, 22, 0)), p2 = LSXC.clone().add(V(-120, 40, 70)),
            p3 = LSXC.clone().addScaledVector(LN, LSXR + 0.12), u = 1 - f;
        return p0.multiplyScalar(u * u * u).add(p1.multiplyScalar(3 * u * u * f)).add(p2.multiplyScalar(3 * u * f * f)).add(p3.multiplyScalar(f * f * f));
    };
    const Bret = (f) => B(1 - f).add(V(0, -18, 26).multiplyScalar(Math.sin(f * Math.PI)));

    // T: the trip's timeline (station.js); C: the running clock; nearLsx 0..1 as the camera dives to the port
    function frame(T, C, { idle, nearLsx, rampOpen, camera, deep = 0 }) {
        // the belt and the orbit lines come up as you zoom out, so the both-planets view stays calm round the wolf
        belt.visible = deep > 0.02; beltDustM.opacity = 0.55 * deep; orbitM.opacity = 0.05 + 0.13 * deep;
        spaceExtras(C); cometFrame(C, deep);
        clouds.rotation.y = C * 0.02; portFrame(C);
        clouds.material.opacity = 1 - nearLsx * 0.85; lsxRim.visible = lsxHalo.visible = nearLsx < 0.7;
        if (ship.parent !== space) space.add(ship);
        trail.visible = false; ship.visible = false; plasma.visible = false; flash.visible = false;
        const fly = (path, f, s0, s1) => {   // the ship along a path, scaling from s0 at the start to s1 on touchdown
            const sp = path(f); if (f >= 1) return sp;
            ship.visible = true; ship.position.copy(sp);
            const dir = path(Math.min(1, f + 0.004)).sub(sp).normalize();
            ship.quaternion.setFromUnitVectors(V(1, 0, 0), dir.lengthSq() ? dir : V(1, 0, 0));
            ship.scale.setScalar(Math.max(0.001, f < 0.08 ? lerp(s0, 0.4, f / 0.08) : f > 0.9 ? lerp(0.4, s1, (f - 0.9) / 0.1) : 0.4));
            legs.forEach((l, i) => { l.rotation.z = i < 2 ? -1.45 : 1.45; }); ramp.rotation.z = 0; cabin.intensity = 0; hold.visible = false;
            thrust(C, 1, 0);
            const tp = trailGeo.attributes.position, ta = trailGeo.attributes.aA, ts = trailGeo.attributes.aS;
            for (let i = 0; i < TRAIL; i++) {
                const q = path(Math.max(0, f - i * 0.0022)).addScaledVector(dir, -9 * ship.scale.x / 0.4); tp.setXYZ(i, q.x, q.y, q.z);
                ta.setX(i, (1 - i / TRAIL) * 0.35 * (f > 0.95 ? 0 : 1) * (s0 < 0.4 ? clamp(f / 0.08) : 1)); ts.setX(i, 1.2 + i * 0.03);
            }
            tp.needsUpdate = ta.needsUpdate = ts.needsUpdate = true; trail.visible = true;
            const q = clamp((f - 0.86) / 0.07) * (1 - clamp((f - 0.97) / 0.03));
            plasma.visible = q > 0; plasma.position.copy(sp); plasma.scale.setScalar((4 + q * 16) * Math.min(1, ship.scale.x / 0.4 + 0.15)); plasma.material.opacity = q * (0.8 + 0.2 * Math.sin(C * 50));
            return sp;
        };
        beacon.visible = idle || T < 15.5 || T >= 41; beacon.material.opacity = 0.5 + 0.5 * Math.sin(C * 6);
        if (!idle && T >= 15.5 && T < 27) fly(B, ease(clamp((T - 15.5) / 11.5)), 0.4, 0.016);
        if (!idle && T >= 31 && T < 41) fly(Bret, ease(clamp((T - 31) / 10)), 0.016, 0.001);
        if (!idle && T >= 27 && T < 31) {   // parked on the LSX port pad, waiting for the tick
            ship.visible = true; ship.scale.setScalar(0.016); ship.position.copy(LP).addScaledVector(LN, 0.09);
            const fw = lA.clone(), up = LN.clone(), m4 = new THREE.Matrix4().makeBasis(fw, up, fw.clone().cross(up)); ship.quaternion.setFromRotationMatrix(m4);
            legs.forEach((l) => { l.rotation.z = 0; }); ramp.rotation.z = 0.74 * rampOpen; hold.visible = ramp.rotation.z > 0.03; cabin.intensity = 1.2; thrust(C, 0, 0);
        }
        const fl = !idle && T >= 26.8 && T < 28.3 ? 1 - Math.abs(T - 27.1) / 1.2 : 0; flash.visible = fl > 0; flash.position.copy(B(1)); flash.scale.setScalar(2 + fl * 8); flash.material.opacity = clamp(fl);
        const gl = !idle && T >= 27 && T < 31 ? 1 + Math.max(0, 1 - (T - 27)) * 2.2 : 1;
        lsxHalo.material.uniforms.k.value = 1.1 * gl; lsxRim.material.uniforms.k.value = 1.6 * gl;
        const cd = camera.position.distanceTo(P); orbitClouds.visible = cd < 120; orbitClouds.children.forEach((c) => { c.material.opacity = 0.8 * clamp((120 - cd) / 60); });
        sky.position.copy(camera.position);
    }

    // the emptiest direction round the sun (the middle of the widest gap between the planets): station.js turns the
    // deep-space view so that this side lies behind the wolf
    const angles = [HOMEC, LSXC, giant.position, ice.position, inner.position].map(angleOf).sort((x, y) => x - y);
    let gapAt = 0, gap = -1;
    angles.forEach((x, i) => { const next = i + 1 < angles.length ? angles[i + 1] : angles[0] + Math.PI * 2; if (next - x > gap) { gap = next - x; gapAt = x + gap / 2; } });
    const free = e1.clone().multiplyScalar(Math.cos(gapAt)).addScaledVector(e2, Math.sin(gapAt)).normalize();

    k.linearize(space);
    return { free,
        scene: space, frame, sky, HOMEC, HOMER, LSXC, LSXR, P, N, LP, LN, lA, lB, SUNP, SUNR, nrm,
        giant: { pos: giant.position, r: GIANTR * 2.3 }, ice: { pos: ice.position, r: ICER }, belt: R_BELT, inner: { pos: inner.position, r: INNERR }, comet: cometPos,
        pickables: { home: [homeP, surfPatch], lsx: [lsxP, portPatch] },
    };
};
