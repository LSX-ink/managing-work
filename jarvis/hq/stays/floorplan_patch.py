"""Turn the stays page's 3D house into a real 3D floor plan (owner, 24 Oct 2026: "more like a floor plan but more 3D,
everything placed inside the floor plan, not it being an image"): solid walls with door gaps and windows, oak / tile /
deck floors, and furniture modelled in every room by its type (bedroom, twin, apartment, living, bathroom, pool,
garden). Tapping a room still opens its real photos. Run once on stays_page.py (idempotent)."""
from pathlib import Path

f = Path(__file__).with_name("stays_page.py")
t = f.read_text(encoding="utf-8")
if "function furnish(" in t:
    print("already patched"); raise SystemExit

JS = r'''
// ---- a real 3D floor plan: solid walls, floors and furniture modelled in every room
const mat = (c, o = {}) => new THREE.MeshStandardMaterial({color: c, roughness: .75, ...o});
function planks(c1, c2, tile) {
  const cv = document.createElement("canvas"); cv.width = cv.height = 256; const x = cv.getContext("2d");
  x.fillStyle = c1; x.fillRect(0, 0, 256, 256); x.strokeStyle = c2; x.lineWidth = 2;
  if (tile) for (let i = 0; i <= 256; i += 64) { x.beginPath(); x.moveTo(i, 0); x.lineTo(i, 256); x.moveTo(0, i); x.lineTo(256, i); x.stroke(); }
  else for (let i = 0; i < 256; i += 32) { x.beginPath(); x.moveTo(0, i); x.lineTo(256, i); x.stroke();
    for (let j = (i / 32 % 2) * 64; j < 256; j += 128) { x.beginPath(); x.moveTo(j, i); x.lineTo(j, i + 32); x.stroke(); } }
  const tx = new THREE.CanvasTexture(cv); tx.wrapS = tx.wrapT = THREE.RepeatWrapping; tx.colorSpace = THREE.SRGBColorSpace; return tx;
}
const FLOORTEX = {oak: planks("#cfa97f", "#b48d64"), tile: planks("#e6e3de", "#cdc8c0", 1), deck: planks("#ad855c", "#8e6b47")};
function floorMat(kind, w, d) {
  const tx = FLOORTEX[kind === "bath" ? "tile" : kind === "pool" || kind === "outdoor" ? "deck" : "oak"].clone();
  tx.needsUpdate = true; tx.repeat.set(w / 1.6, d / 1.6); return new THREE.MeshStandardMaterial({map: tx, roughness: .8});
}
function kindOf(r) {
  const n = r.name.toLowerCase(), t = n + " " + (r.summary || "").toLowerCase();
  if (/pool/.test(n) && !/suite|room|studio/.test(n)) return "pool";
  if (/garden|park|terrace|deck|grounds|view/.test(n) && !/suite|room|studio/.test(n)) return "outdoor";
  if (/en-suite|bathroom/.test(n)) return "bath";
  if (/dining|kitchen/.test(n) && !/lounge|living/.test(n)) return "dining";
  if (/lounge|kitchen|dining|breakfast|living|reception/.test(n)) return "living";
  if (/villa|apartment|cottage/.test(n)) return "apartment";
  if (/family|twin/.test(t)) return "twin";
  return "suite";
}
function walls(g, x, z, W, D, s, trim, open) {   // white walls with a door to the corridor and a window to the outside
  if (open) { box(W, .08, .08, trim, x, .04, z - s * D / 2, g); return; }
  const Hh = 1.05, T = .12, wm = mat(0xf6f3ee, {roughness: .9});
  const seg = (a, b, pz) => { if (b - a > .05) { box(b - a, Hh, T, wm, (a + b) / 2, Hh / 2, pz, g); box(b - a + .01, .05, T + .02, trim, (a + b) / 2, Hh, pz, g); } };
  for (const px of [x - W / 2, x + W / 2]) { box(T, Hh, D, wm, px, Hh / 2, z, g); box(T + .02, .05, D + .01, trim, px, Hh, z, g); }
  const L = x - W / 2, R = x + W / 2, cz = z - s * D / 2, oz = z + s * D / 2, door = x + W / 2 - 1.0, win = x + W * .15, ww = W * .35;
  seg(L, door - .48, cz); seg(door + .48, R, cz);
  seg(L, win - ww / 2, oz); seg(win + ww / 2, R, oz);
  box(ww, .45, T, wm, win, .225, oz, g); box(ww, .6, .04, mat(0xcfe8f2, {transparent: true, opacity: .45, roughness: .05}), win, .75, oz, g);
}
function furnish(kind, g, x, z, W, D, s, accent) {
  const P = (lx, lz) => [x + lx, z + s * lz];   // lz grows towards the outside wall
  const put = (w, h, d, m, lx, y, lz) => { const [px, pz] = P(lx, lz); return box(w, h, d, m, px, y, pz, g); };
  const wood = mat(0x8a6a4a), white = mat(0xf8f6f2), linen = mat(0xece6dc), fab = mat(accent.getHex(), {roughness: .95}),
        dark = mat(0x34302c), water = mat(0x5ec8e0, {roughness: .1, emissive: 0x2aa6d6, emissiveIntensity: .3}), green = mat(0x58864f, {roughness: 1});
  const rug = (lx, lz, w, d, c = 0xdcd0bb) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), mat(c, {roughness: 1}));
    m.rotation.x = -Math.PI / 2; const [px, pz] = P(lx, lz); m.position.set(px, .03, pz); m.receiveShadow = true; g.add(m); };
  const bed = (lx, wide) => { const bw = wide ? 1.8 : .95, lz = D / 2 - 1.2;
    put(bw + .1, .32, 2.1, wood, lx, .16, lz); put(bw, .16, 2.0, white, lx, .4, lz); put(bw + .02, .07, 1.25, fab, lx, .51, lz - .35);
    put(bw + .2, .9, .08, dark, lx, .45, lz + 1.06);
    for (const o of wide ? [-.45, .45] : [0]) put(.6, .12, .32, linen, lx + o, .54, lz + .78);
    for (const o of [-(bw / 2 + .32), bw / 2 + .32]) { put(.42, .45, .4, wood, lx + o, .225, lz + .8); put(.14, .3, .14, linen, lx + o, .6, lz + .8); }
  };
  const sofa = (lx, lz, w = 2) => { put(w, .4, .85, fab, lx, .2, lz); put(w, .45, .2, fab, lx, .52, lz + .33);
    put(.18, .55, .85, fab, lx - w / 2, .28, lz); put(.18, .55, .85, fab, lx + w / 2, .28, lz); };
  const table = (lx, lz) => { put(1.2, .06, .8, wood, lx, .74, lz); put(.1, .72, .1, wood, lx, .36, lz);
    for (const [a, b] of [[-.4, .55], [.4, .55], [-.4, -.55], [.4, -.55]]) { put(.42, .45, .42, white, lx + a, .225, lz + b); put(.42, .4, .06, white, lx + a, .65, lz + b + Math.sign(b) * .18); } };
  const tv = (lx) => { put(1.3, .5, .4, wood, lx, .25, -D / 2 + .3); put(1.1, .62, .05, dark, lx, .95, -D / 2 + .2); };
  const plant = (lx, lz) => { put(.3, .35, .3, dark, lx, .17, lz); const m = new THREE.Mesh(new THREE.SphereGeometry(.3, 12, 10), green); const [px, pz] = P(lx, lz); m.position.set(px, .62, pz); m.castShadow = true; g.add(m); };
  const ensuite = (lx, lz) => {   // a bathroom in the corridor-side corner: partition, bath, basin, toilet
    put(.1, 1.0, 1.8, white, lx + .9, .5, lz); put(1.8, 1.0, .1, white, lx, .5, lz + .9);
    put(1.5, .5, .7, white, lx, .25, lz - .45); put(1.3, .05, .52, water, lx, .48, lz - .45);
    put(.5, .8, .4, white, lx - .55, .4, lz + .55); put(.36, .38, .5, white, lx + .45, .19, lz + .5);
  };
  if (kind === "suite" || kind === "twin" || kind === "apartment" || kind === "bedroom") {
    if (kind === "twin") { bed(-W / 2 + 1.0, 0); bed(-W / 2 + 2.4, 0); } else bed(-W / 2 + 1.35, 1);
    rug(-W / 2 + 1.5, D / 2 - 2.3, 2.4, 1.2);
    if (kind !== "bedroom") ensuite(-W / 2 + 1.0, -D / 2 + 1.0);
    tv(.25);
    if (kind === "apartment") sofa(W / 2 - 1.25, D / 2 - .6, 1.7); else { put(.75, .45, .75, fab, W / 2 - .9, .22, D / 2 - .8); put(.75, .4, .15, fab, W / 2 - .9, .6, D / 2 - .5); }
    plant(W / 2 - .35, -D / 2 + .35 + 1.1);
  } else if (kind === "living") {
    sofa(-W / 4, D / 2 - .65, 2.2); put(1.0, .38, .6, wood, -W / 4, .19, D / 2 - 1.65); rug(-W / 4, D / 2 - 1.45, 2.6, 1.8);
    tv(-W / 4); table(W / 4, -.1);
    put(2.4, .9, .6, white, W / 2 - 1.4, .45, D / 2 - .35); put(2.42, .04, .62, dark, W / 2 - 1.4, .92, D / 2 - .35);
    plant(-W / 2 + .4, -D / 2 + .4);
  } else if (kind === "dining") {
    table(-W / 4, 0); put(2.6, .9, .6, white, W / 4, .45, D / 2 - .35); put(2.62, .04, .62, dark, W / 4, .92, D / 2 - .35);
    put(1.6, .9, .8, white, W / 4, .45, -.2); put(1.62, .04, .82, dark, W / 4, .92, -.2); plant(-W / 2 + .4, -D / 2 + .4);
  } else if (kind === "bath") {
    put(1.7, .55, .8, white, -W / 4, .27, D / 2 - .55); put(1.5, .05, .6, water, -W / 4, .52, D / 2 - .55);
    put(1.6, 2.0, .05, mat(0xd9eef5, {transparent: true, opacity: .35, roughness: .05}), W / 4, 1, D / 2 - 1.35); put(1.6, .04, 1.2, mat(0xcfcac2), W / 4, .03, D / 2 - .75);
    put(1.2, .8, .5, white, -.3, .4, -D / 2 + .35); put(.4, .4, .55, white, W / 2 - .5, .2, -D / 2 + .5); plant(-W / 2 + .4, -D / 2 + .4);
  } else {
    if (kind === "pool") put(W * .55, .08, D * .5, water, -W * .12, .04, -.1);
    else for (const [a, b] of [[-W / 3, D / 4], [W / 5, -D / 4]]) { put(.14, .9, .14, wood, a, .45, b); const m = new THREE.Mesh(new THREE.SphereGeometry(.6, 14, 10), green); const [px, pz] = P(a, b); m.position.set(px, 1.2, pz); m.castShadow = true; g.add(m); }
    for (const o of [-.75, .75]) { put(.62, .18, 1.6, white, W / 2 - 1.3 + o, .2, D / 2 - 1.1); put(.62, .4, .1, white, W / 2 - 1.3 + o, .38, D / 2 - .35); }
    put(.05, 1.8, .05, wood, W / 2 - 1.3, .9, D / 2 - 1.1); const u = new THREE.Mesh(new THREE.ConeGeometry(1.0, .4, 16), linen); const [ux, uz] = P(W / 2 - 1.3, D / 2 - 1.1); u.position.set(ux, 1.9, uz); u.castShadow = true; g.add(u);
  }
}
'''
OLD = '''    const tex = loader.load(r.cover); tex.colorSpace = THREE.SRGBColorSpace;
    const floorMesh = new THREE.Mesh(new THREE.PlaneGeometry(W, D), new THREE.MeshStandardMaterial({{map: tex, roughness: .55, emissive: 0xffffff, emissiveMap: tex, emissiveIntensity: .35}}));
    floorMesh.rotation.x = -Math.PI / 2; floorMesh.position.set(x, .02, z); floorMesh.receiveShadow = true; g.add(floorMesh);
    const wallMat = glass(), trimMat = new THREE.MeshStandardMaterial({{color: 0xc8960f, roughness: .35, metalness: .5, emissive: 0xe0b84a, emissiveIntensity: .0}});
    [[0, -D / 2, W, .12], [0, D / 2, W, .12], [-W / 2, 0, .12, D], [W / 2, 0, .12, D]].forEach(([wx, wz, ww, wd], n) => {{
      const h = H;   // glass walls with gold trims, so the room inside shows from any angle
      const wall = new THREE.Mesh(new THREE.BoxGeometry(ww, h, wd), wallMat); wall.position.set(wx, h / 2, wz); walls.add(wall);
      const trim = new THREE.Mesh(new THREE.BoxGeometry(ww + .01, .07, wd + .01), trimMat); trim.position.set(wx, h, wz); walls.add(trim);
    }});
'''
if OLD not in t:  # the current version (after plan_patch) uses box() directly
    OLD = '''    const tex = loader.load(r.cover); tex.colorSpace = THREE.SRGBColorSpace;
    const floorMesh = new THREE.Mesh(new THREE.PlaneGeometry(W, D), new THREE.MeshStandardMaterial({{map: tex, roughness: .55, emissive: 0xffffff, emissiveMap: tex, emissiveIntensity: .35}}));
    floorMesh.rotation.x = -Math.PI / 2; floorMesh.position.set(x, .02, z); floorMesh.receiveShadow = true; g.add(floorMesh);
    const wallMat = glass(), trimMat = new THREE.MeshStandardMaterial({{color: 0xc8960f, roughness: .35, metalness: .5, emissive: 0xe0b84a, emissiveIntensity: 0}});
    [[0, -D / 2, W, .12], [0, D / 2, W, .12], [-W / 2, 0, .12, D], [W / 2, 0, .12, D]].forEach(([wx, wz, ww, wd]) => {{
      box(ww, H, wd, wallMat, x + wx, H / 2, z + wz, g);
      box(ww + .01, .07, wd + .01, trimMat, x + wx, H, z + wz, g);
    }});
'''
NEW = '''    const kind = kindOf(r);
    const floorMesh = new THREE.Mesh(new THREE.PlaneGeometry(W, D), floorMat(kind, W, D));
    floorMesh.rotation.x = -Math.PI / 2; floorMesh.position.set(x, .02, z); floorMesh.receiveShadow = true; g.add(floorMesh);
    const wallMat = mat(0xf6f3ee), trimMat = new THREE.MeshStandardMaterial({{color: 0x3a342e, roughness: .5, emissive: 0xe0b84a, emissiveIntensity: 0}});
    walls(g, x, z, W, D, p.s, trimMat, kind === "pool" || kind === "outdoor");
    furnish(kind, g, x, z, W, D, p.s, new THREE.Color(r.accent || "#c9a77a"));
'''
assert OLD in t, "room block not found"
t = t.replace(OLD, NEW)
anchor = "function level(f) {{"
t = t.replace(anchor, JS.replace("{", "{{").replace("}", "}}") + anchor, 1)
f.write_text(t, encoding="utf-8")
print("patched")
