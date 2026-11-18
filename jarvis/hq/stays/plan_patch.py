"""Rebuild the stays page's 3D house from the council's approved floor plans (Birmingham 2023/07524/PA):
street/bay end at the front, a central corridor with the stair, two rooms each side, the lower-ground guest lounge,
the front entrance, bay windows and the first-floor rear balcony."""
from pathlib import Path

f = Path(__file__).with_name("stays_page.py")
t = f.read_text(encoding="utf-8")
a = t.index("const loader = new THREE.TextureLoader();")
b = t.index("let mode = \"all\"")
NEW = r'''const loader = new THREE.TextureLoader(); const D = 3.8, C = 1.5, H = 1.35, FLOOR_H = 3.2, LEN = 11.2;
// Room positions follow the approved plans: x runs from the street (bay window, -x) to the garden (+x),
// z = which side of the central corridor (+z is the bay side). Suites fill each floor's rooms in order.
const PLAN = {{
  0: [{{x: -1, s: -1, l: 5.7}}, {{x: -1, s: 1, l: 5.7, bay: 1}}, {{x: 1, s: 1, l: 5.3}}, {{x: 1, s: -1, l: 5.3}}],
  1: [{{x: 1, s: -1, l: 4.9, balcony: 1}}, {{x: 1, s: 1, l: 4.9}}, {{x: -1, s: -1, l: 6.1}}, {{x: -1, s: 1, l: 6.1, bay: 1}}],
  2: [{{x: 1, s: -1, l: 4.9}}, {{x: 1, s: 1, l: 4.9}}, {{x: -1, s: -1, l: 6.1}}, {{x: -1, s: 1, l: 6.1}}],
}};
const floors = {{}}, pick = [], labelEls = [];
const gold = () => new THREE.MeshStandardMaterial({{color: 0xc8960f, roughness: .35, metalness: .5}});
const glass = () => {{ const m = new THREE.MeshStandardMaterial({{color: 0xfff6e6, roughness: .15, metalness: .1, transparent: true, opacity: .22}}); m.userData.base = .22; return m; }};
const box = (w, h, d, mat, x, y, z, g) => {{ const o = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat); o.position.set(x, y, z); o.castShadow = true; g.add(o); return o; }};
function marker(text, g, x, y, z, f) {{
  const o = new THREE.Object3D(); o.position.set(x, y, z); g.add(o);
  const lab = document.createElement("span"); lab.className = "x"; lab.textContent = text; document.getElementById("labels").appendChild(lab);
  labelEls.push({{el: lab, obj: o, f}});
}}
function level(f) {{
  const g = new THREE.Group(); g.position.y = f * FLOOR_H; scene.add(g); floors[f] = g;
  const slab = box(LEN + .4, .22, D * 2 + C + .4, new THREE.MeshStandardMaterial({{color: 0xe9e1d3, roughness: .9}}), 0, -.12, 0, g);
  slab.receiveShadow = true;
  const hall = new THREE.Mesh(new THREE.PlaneGeometry(LEN, C), new THREE.MeshStandardMaterial({{color: 0xd9c3a0, roughness: .7}}));
  hall.rotation.x = -Math.PI / 2; hall.position.y = .012; hall.receiveShadow = true; g.add(hall);
  // the stair in the middle of the corridor, as on every plan
  const step = new THREE.MeshStandardMaterial({{color: 0xf6efe3, roughness: .6}});
  for (let i = 0; i < 8; i++) box(.36, .12 + i * .14, C * .8, step, -1.3 + i * .36, (.12 + i * .14) / 2, 0, g);
  return g;
}}
[0, 1, 2].forEach(f => {{
  const g = level(f), list = rooms.map((r, i) => [r, i]).filter(([r]) => r.floor === f);
  list.forEach(([r, idx], k) => {{
    const p = PLAN[f][k], x = p.x * (LEN / 2 - p.l / 2), z = p.s * (C / 2 + D / 2), W = p.l - .1;
    const tex = loader.load(r.cover); tex.colorSpace = THREE.SRGBColorSpace;
    const floorMesh = new THREE.Mesh(new THREE.PlaneGeometry(W, D), new THREE.MeshStandardMaterial({{map: tex, roughness: .55, emissive: 0xffffff, emissiveMap: tex, emissiveIntensity: .35}}));
    floorMesh.rotation.x = -Math.PI / 2; floorMesh.position.set(x, .02, z); floorMesh.receiveShadow = true; g.add(floorMesh);
    const wallMat = glass(), trimMat = new THREE.MeshStandardMaterial({{color: 0xc8960f, roughness: .35, metalness: .5, emissive: 0xe0b84a, emissiveIntensity: 0}});
    [[0, -D / 2, W, .12], [0, D / 2, W, .12], [-W / 2, 0, .12, D], [W / 2, 0, .12, D]].forEach(([wx, wz, ww, wd]) => {{
      box(ww, H, wd, wallMat, x + wx, H / 2, z + wz, g);
      box(ww + .01, .07, wd + .01, trimMat, x + wx, H, z + wz, g);
    }});
    if (p.bay) {{   // the canted bay window on the street front
      const bay = new THREE.Mesh(new THREE.CylinderGeometry(1.5, 1.5, H, 6, 1, true, Math.PI, Math.PI), wallMat);
      bay.rotation.y = Math.PI / 2; bay.scale.set(1, 1, .45); bay.position.set(-LEN / 2, H / 2, z); g.add(bay);
      box(.07, .07, 3, trimMat, -LEN / 2 - .67, H, z, g);
    }}
    if (p.balcony) {{   // first-floor balcony over the garden
      box(1.4, .1, 4, new THREE.MeshStandardMaterial({{color: 0xe9e1d3, roughness: .9}}), LEN / 2 + .7, -.05, z, g);
      box(.05, .7, 4, gold(), LEN / 2 + 1.38, .35, z, g); box(1.4, .7, .05, gold(), LEN / 2 + .7, .35, z - 2, g); box(1.4, .7, .05, gold(), LEN / 2 + .7, .35, z + 2, g);
      marker("Balcony", g, LEN / 2 + .7, .9, z, f);
    }}
    const hit = new THREE.Mesh(new THREE.BoxGeometry(W, H, D), new THREE.MeshBasicMaterial({{visible: false}}));
    hit.position.set(x, H / 2, z); hit.userData = {{idx, trimMat, floorMesh, f}}; g.add(hit); pick.push(hit);
    const lab = document.createElement("span"); lab.textContent = r.name.replace(/^The /, ""); document.getElementById("labels").appendChild(lab);
    labelEls.push({{el: lab, obj: hit, f}});
  }});
}});
// the front door off School Road, with the self check-in kiosk
const gf = floors[0];
box(.12, 1.9, .12, gold(), -LEN / 2 - .05, .95, -.6, gf); box(.12, 1.9, .12, gold(), -LEN / 2 - .05, .95, .6, gf); box(.12, .12, 1.32, gold(), -LEN / 2 - .05, 1.9, 0, gf);
box(.8, .08, 1.6, new THREE.MeshStandardMaterial({{color: 0xd8cfbf}}), -LEN / 2 - .45, .04, 0, gf);
marker("Entrance · self check-in", gf, -LEN / 2 - .6, 2.4, 0, 0);
// lower ground: guest lounge with pool table, kitchenette and the team's rooms
const lg = level(-1);
const lounge = new THREE.Mesh(new THREE.PlaneGeometry(6, D * 2 + C), new THREE.MeshStandardMaterial({{color: 0xcbb38c, roughness: .8}}));
lounge.rotation.x = -Math.PI / 2; lounge.position.set(-LEN / 2 + 3, .02, 0); lg.add(lounge);
box(2.2, .5, 1.2, new THREE.MeshStandardMaterial({{color: 0x1f5b3a, roughness: .9}}), -LEN / 2 + 2.6, .25, 1.6, lg);
box(1.6, .45, 1.1, new THREE.MeshStandardMaterial({{color: 0x8a6b4a, roughness: .8}}), LEN / 2 - 1.6, .22, 1.9, lg);
const lw = glass(); box(.12, H, D * 2 + C, lw, 0, H / 2, 0, lg); box(LEN, H, .12, lw, 0, H / 2, -(D + C / 2), lg); box(LEN, H, .12, lw, 0, H / 2, D + C / 2, lg);
marker("Guest lounge · pool table", lg, -LEN / 2 + 3, 1.4, 1, -1);
marker("Kitchenette", lg, LEN / 2 - 2, 1.4, 2, -1);
// warm lamps through the house
for (let i = 0; i < 20; i++) {{ const l = new THREE.PointLight(0xffc98a, .6, 6); l.position.set((Math.random() - .5) * 10, (i % 4 - 1) * FLOOR_H + 1, (Math.random() - .5) * 7); scene.add(l); }}
'''
t = t[:a] + NEW + t[b:]
R = [
    # remove the old lamp loop (now inside NEW) — it sits just before "let mode"; NEW already replaced it
    ("  floors.forEach((g, f) => {{\n", "  Object.entries(floors).forEach(([k, g]) => {{ const f = +k;\n"),
    ("ground.rotation.x = -Math.PI / 2; ground.receiveShadow = true;",
     "ground.rotation.x = -Math.PI / 2; ground.position.y = -FLOOR_H * 1.55 - .3; ground.receiveShadow = true;"),
    ("const ground = new THREE.Mesh(", "const FLOOR_H = 3.2; const ground = new THREE.Mesh("),
    ("<button data-f=\"0\">Ground</button>", "<button data-f=\"-1\">Lower ground</button><button data-f=\"0\">Ground</button>"),
    ("3D layout is illustrative, arranged by floor, not an exact floor plan",
     "Laid out from the house&rsquo;s approved floor plans (Birmingham City Council, ref. 2023/07524/PA)"),
    ("Spin the house, pick a floor, then tap any suite to walk into it and see every photo.",
     "This is the real layout of the house, room by room, from the street front to the garden. Spin it, pick a floor, then tap any suite to walk into it and see every photo."),
    ("<div><b>3</b>floors</div>", "<div><b>4</b>floors</div>"),
    (".labels span{{", ".labels span.x{{background:rgba(184,134,11,.9);color:#fff;font-family:var(--body);font-size:.72rem}}.labels span{{"),
]
missing = [x[:50] for x, _ in R if x not in t]
for x, y in R:
    t = t.replace(x, y)
# FLOOR_H is now declared before the ground, so drop the second declaration in the loader line
t = t.replace("const D = 3.8, C = 1.5, H = 1.35, FLOOR_H = 3.2, LEN = 11.2;", "const D = 3.8, C = 1.5, H = 1.35, LEN = 11.2;")
f.write_text(t, encoding="utf-8")
print("missing:", missing)

t = f.read_text(encoding="utf-8")
for x, y in [("controls.target.set(0, 4.2, 0);", "controls.target.set(0, 2.6, 0);"),
             ("const HOME = new THREE.Vector3(17, 15.5, 17);", "const HOME = new THREE.Vector3(19, 14, 19);"),
             ("const y = mode === \"all\" ? 4.2 :", "const y = mode === \"all\" ? 2.6 :"),
             ("tt: new THREE.Vector3(0, 4.2, 0), done", "tt: new THREE.Vector3(0, 2.6, 0), done")]:
    print(x[:30], x in t); t = t.replace(x, y)
f.write_text(t, encoding="utf-8")
