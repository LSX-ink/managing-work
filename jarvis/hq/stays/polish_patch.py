"""Polish the 3D floor plan on every stays page (owner, 24 Oct 2026: "make it even better, everything"):
studio lighting with real reflections (RoomEnvironment), soft shadows, rounded furniture edges, taller walls,
each room's own photo hung as framed art above the bed, glowing bedside lamps, and a camera fly-in when the
house scrolls into view. Applies to stays_page.py (all stays_build concepts + Moseley) and ash_page.py. Idempotent."""
from pathlib import Path

HERE = Path(__file__).parent
IMPORTS = ('import {{ OrbitControls }} from "three/addons/controls/OrbitControls.js";',
           'import {{ OrbitControls }} from "three/addons/controls/OrbitControls.js";\n'
           'import {{ RoomEnvironment }} from "three/addons/environments/RoomEnvironment.js";\n'
           'import {{ RoundedBoxGeometry }} from "three/addons/geometries/RoundedBoxGeometry.js";')
ENV = ('renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.ACESFilmicToneMapping;',
       'renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.ACESFilmicToneMapping;\n'
       'renderer.toneMappingExposure = .72; renderer.shadowMap.type = THREE.PCFSoftShadowMap;')
ENV2 = 'const pmrem = new THREE.PMREMGenerator(renderer); scene.environment = pmrem.fromScene(new RoomEnvironment(), .04).texture;\n'
ROUND = "new THREE.Mesh(new RoundedBoxGeometry(w, h, d, 2, Math.min(.035, Math.min(w, h, d) * .3)), "
COMMON = [
    ("const Hh = 1.05, T = .12, wm", "const Hh = 1.3, T = .12, wm"),
    # the bedside lamps glow
    ("put(.14, .3, .14, linen, lx + o, .6, lz + .8); }}",
     "put(.14, .3, .14, mat(0xfff1d6, {{emissive: 0xffc77a, emissiveIntensity: .9}}), lx + o, .6, lz + .8); }}"),
    # their own photo, framed above the bed
    ("    put(bw + .2, .9, .08, dark, lx, .45, lz + 1.06);\n",
     "    put(bw + .2, .9, .08, dark, lx, .45, lz + 1.06);\n"
     "    if (img && wide) {{ put(1.0, .7, .04, dark, lx, 1.12, lz + 1.12); const ph = new THREE.Mesh(new THREE.PlaneGeometry(.9, .6), new THREE.MeshStandardMaterial({{map: art(img), roughness: .6}}));\n"
     "      const [px, pz] = P(lx, lz + 1.09); ph.position.set(px, 1.12, pz); ph.rotation.y = s > 0 ? Math.PI : 0; g.add(ph); }}\n"),
    ("function furnish(kind, g, x, z, W, D, s, accent) {{", "function furnish(kind, g, x, z, W, D, s, accent, img) {{"),
    ("const FLOORTEX = {{", "const ARTS = {{}}; const art = src => {{ if (!ARTS[src]) {{ const tx = new THREE.TextureLoader().load(src); tx.colorSpace = THREE.SRGBColorSpace; ARTS[src] = tx; }} return ARTS[src]; }};\nconst FLOORTEX = {{"),
]
INTRO = ("function resize() {{",
         "// a cinematic fly-in the first time the house scrolls into view\n"
         "const introIO = new IntersectionObserver(es => {{ if (!es[0].isIntersecting) return; introIO.disconnect();\n"
         "  const from = HOME.clone().multiplyScalar(1.8); from.y = HOME.y * 2.3; camera.position.copy(from); controls.autoRotate = false;\n"
         "  fly = {{t: 0, from, to: HOME.clone(), tf: controls.target.clone(), tt: controls.target.clone(), done: () => controls.autoRotate = true}}; }}, {{threshold: .3}});\n"
         "introIO.observe(stage);\nfunction resize() {{")


def patch(name: str, box_old: str, furnish_old: str, furnish_new: str, light_old: str) -> None:
    f = HERE / name
    t = f.read_text(encoding="utf-8")
    if "RoomEnvironment" in t:
        print(name, "already polished"); return
    R = [IMPORTS, ENV, (box_old, box_old.replace("new THREE.Mesh(new THREE.BoxGeometry(w, h, d), ", ROUND)), *COMMON,
         (furnish_old, furnish_new), INTRO, (light_old, ENV2 + light_old)]
    for a, b in R:
        assert a in t, (name, a[:70])
        t = t.replace(a, b, 1)
    f.write_text(t, encoding="utf-8")
    print(name, "polished")


patch("stays_page.py",
      "const box = (w, h, d, mat, x, y, z, g) => {{ const o = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);",
      'furnish(kind, g, x, z, W, D, p.s, new THREE.Color(r.accent || "#c9a77a"));',
      'furnish(kind, g, x, z, W, D, p.s, new THREE.Color(r.accent || "#c9a77a"), r.cover);',
      "scene.add(new THREE.HemisphereLight(")
patch("ash_page.py",
      "const box = (w, h, d, mat, x, y, z) => {{ const o = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);",
      'furnish(kind, scene, cx, cz, w, d, s, new THREE.Color("#7f9b8a"));',
      'furnish(kind, scene, cx, cz, w, d, s, new THREE.Color("#7f9b8a"), r.gallery[0]);',
      "scene.add(new THREE.HemisphereLight(")
