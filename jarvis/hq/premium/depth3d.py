"""3D for the premium mock-ups (owner, 28 Oct 2026: "make new for all including everything", then: "why is the 3d the
same for every website thats terrible marketing").

Each mock-up gets its own 3D piece that means something for that business, in their colours: a barber pole turning,
scissors opening and closing, a straight razor folding open, a clipper humming, a comb, a hair-dryer, a paddle brush,
a product bottle. The piece builds itself from its parts as the page opens (the assemble idea studied from igloo.inc,
written here from scratch), glowing at the seams, then comes apart and fades as the visitor scrolls, so it never sits
over the menu, prices or reviews. auto.py picks the piece: the trade's pieces, least used first, so two mock-ups in a
batch never share one.

Built by the 3D skills: one WebGL context and transform-only motion (auteur), capped pixel ratio, drawing paused when
the first screen is out of view or the tab is hidden (threejs-errors-performance), IntersectionObserver instead of
scroll listeners, one still frame for reduced motion, and nothing at all when WebGL or the download fails
(web3d-integration-patterns). Placed per layout so the headline stays clear (impeccable craft-floor).

Only pages whose config has "depth3d": true get it, so mock-ups already sent stay exactly as they were."""
import json
from pathlib import Path

THREE = "https://cdn.jsdelivr.net/npm/three@0.160.0/"
BARBER_PIECES = ["pole", "scissors", "razor", "clipper", "comb", "brush", "bottle", "dryer"]   # best fit first
SALON_PIECES = ["dryer", "brush", "bottle", "scissors", "comb", "clipper", "razor", "pole"]
PIECES = sorted(set(BARBER_PIECES + SALON_PIECES))


def pieces_for(name: str, types=()) -> list[str]:
    """The pieces that fit the trade: barbers get the barber's tools, everyone else the salon's."""
    text = f"{name} {' '.join(types or [])}".lower()
    return BARBER_PIECES if any(w in text for w in ("barber", "grooming", "gents", "fade", "men's", "mens")) else SALON_PIECES


def add(html: str, c: dict, out: Path) -> str:
    if not c.get("depth3d"):
        return html
    col = c["colours"]
    piece = c.get("piece") if c.get("piece") in PIECES else pieces_for(c.get("name", ""))[0]
    opts = {"gold": col.get("gold", "#c9a227"), "second": col.get("second") or col.get("gold", "#c9a227"),
            "dark": col.get("panel", "#141414"), "piece": piece, "layout": c.get("layout", "atelier")}
    block = (
        '<canvas id="d3" aria-hidden="true"></canvas>'
        "<style>#d3{position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:15;opacity:0;"
        "transition:opacity .35s ease-out}#d3.on{opacity:1}"
        "@media (prefers-reduced-transparency:reduce){#d3{display:none}}</style>"
        f'<script type="importmap">{{"imports":{{"three":"{THREE}build/three.module.js","three/addons/":"{THREE}examples/jsm/"}}}}</script>'
        '<script type="module">' + SCENE_JS.replace("__OPTS__", json.dumps(opts)) + "</script>")
    return html.replace("</body>", block + "</body>", 1)


SCENE_JS = r"""
import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
const O = __OPTS__;
const cv = document.getElementById('d3');
let renderer;
try { renderer = new THREE.WebGLRenderer({ canvas: cv, antialias: true, alpha: true, powerPreference: 'low-power' }); }
catch (e) { cv.remove(); throw e; }
const phone = matchMedia('(max-width: 760px)').matches, still = matchMedia('(prefers-reduced-motion: reduce)').matches;
renderer.setPixelRatio(Math.min(devicePixelRatio, phone ? 1.5 : 1.75));
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.outputColorSpace = THREE.SRGBColorSpace;
const scene = new THREE.Scene(), pm = new THREE.PMREMGenerator(renderer);
scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture; pm.dispose();
const cam = new THREE.PerspectiveCamera(35, 1, 0.1, 100); cam.position.set(0, 0, 14);
const key = new THREE.DirectionalLight(0xffffff, 2.2); key.position.set(-4, 5, 8); scene.add(key);
const tint = new THREE.PointLight(new THREE.Color(O.gold), 40, 30); tint.position.set(4, -2, 6); scene.add(tint);

// materials in their colours: the accent as polished metal (its seams glow while it assembles), chrome, a dark handle
const accent = new THREE.MeshPhysicalMaterial({ color: new THREE.Color(O.gold), metalness: 1, roughness: 0.25, clearcoat: 0.6,
  emissive: new THREE.Color(O.gold), emissiveIntensity: 0 });
const chrome = new THREE.MeshPhysicalMaterial({ color: 0xf2f5f8, metalness: 0.8, roughness: 0.2, clearcoat: 1, envMapIntensity: 1.8 });   // bright enough to read as steel on a dark page
const dark = new THREE.MeshPhysicalMaterial({ color: new THREE.Color(O.dark).lerp(new THREE.Color(0x000000), 0.2), metalness: 0.2, roughness: 0.45, clearcoat: 0.8 });
const second = new THREE.MeshPhysicalMaterial({ color: new THREE.Color(O.second), metalness: 0.3, roughness: 0.35, clearcoat: 0.8 });
const glass = new THREE.MeshPhysicalMaterial({ color: 0xffffff, transmission: 0.95, thickness: 0.6, roughness: 0.04, ior: 1.5, clearcoat: 1, transparent: true });

const piece = new THREE.Group(), parts = [];
function part(geo, mat, x = 0, y = 0, z = 0, parent = piece) {   // every part flies in from its own direction
  const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); parent.add(m);
  const r = 1.6 + Math.random() * 2.4, a = Math.random() * Math.PI * 2;
  m.userData = { home: m.position.clone(), homeR: m.rotation.clone(), delay: Math.random() * 0.6,
                 off: new THREE.Vector3(Math.cos(a) * r, (Math.random() - .5) * 3.5, Math.sin(a) * r),
                 spin: new THREE.Vector3((Math.random() - .5) * 5, (Math.random() - .5) * 5, (Math.random() - .5) * 5) };
  parts.push(m); return m;
}
const settle = (m) => { m.userData.home.copy(m.position); m.userData.homeR.copy(m.rotation); return m; };
let idle = () => {};

const P = {
  pole() {   // the barber's pole: stripes in their colours turning inside a glass sleeve, polished caps
    const c = document.createElement('canvas'); c.width = 64; c.height = 256; const g = c.getContext('2d');
    g.fillStyle = '#ffffff'; g.fillRect(0, 0, 64, 256);
    [O.gold, O.second].forEach((col, i) => { g.fillStyle = col; for (let y = -64; y < 320; y += 64) {
      g.beginPath(); g.moveTo(0, y + i * 32); g.lineTo(64, y + i * 32 - 40); g.lineTo(64, y + i * 32 - 24); g.lineTo(0, y + i * 32 + 16); g.fill(); } });
    const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace; tex.wrapS = tex.wrapT = THREE.RepeatWrapping; tex.repeat.set(2, 2);
    const core = part(new THREE.CylinderGeometry(0.38, 0.38, 3.4, 48), new THREE.MeshPhysicalMaterial({ map: tex, roughness: 0.3, clearcoat: 1 }));
    part(new THREE.CylinderGeometry(0.47, 0.47, 3.4, 48, 1, true), glass);
    part(new THREE.CylinderGeometry(0.55, 0.55, 0.22, 48), accent, 0, 1.82); part(new THREE.CylinderGeometry(0.55, 0.55, 0.22, 48), accent, 0, -1.82);
    part(new THREE.SphereGeometry(0.42, 40, 24), accent, 0, 2.2); part(new THREE.SphereGeometry(0.3, 32, 20), accent, 0, -2.15);
    idle = (t) => { tex.offset.y = -t * 0.35; piece.rotation.y = Math.sin(t * 0.4) * 0.3; };
  },
  scissors() {   // two blades on a pivot, opening and closing
    const blade = new THREE.Shape(); blade.moveTo(0, 0); blade.lineTo(0.2, 0.15); blade.quadraticCurveTo(0.12, 1.6, 0.02, 2.7); blade.lineTo(-0.04, 2.7); blade.quadraticCurveTo(-0.02, 1.4, -0.08, 0.1); blade.lineTo(0, 0);
    const bgeo = new THREE.ExtrudeGeometry(blade, { depth: 0.06, bevelEnabled: true, bevelThickness: 0.02, bevelSize: 0.02, bevelSegments: 2 });
    const halves = [-1, 1].map((s) => { const h = new THREE.Group(); piece.add(h);
      const b = part(bgeo, chrome, 0, 0, s * 0.04, h); b.scale.x = s; settle(b);
      part(new THREE.CylinderGeometry(0.07, 0.07, 1.0, 12), s < 0 ? accent : dark, s * 0.18, -0.55, s * 0.04, h);
      const ring = part(new THREE.TorusGeometry(0.34, 0.08, 16, 48), s < 0 ? accent : dark, s * 0.34, -1.25, s * 0.04, h); return h; });
    part(new THREE.CylinderGeometry(0.1, 0.1, 0.22, 24), accent, 0, 0, 0).rotation.x = Math.PI / 2; settle(parts[parts.length - 1]);
    piece.position.y = -0.4;
    idle = (t) => { const a = 0.12 + 0.18 * (0.5 + 0.5 * Math.sin(t * 2.2)); halves[0].rotation.z = a; halves[1].rotation.z = -a; piece.rotation.y = Math.sin(t * 0.5) * 0.4; };
  },
  razor() {   // a straight razor folding open from its handle
    const handle = part(new THREE.BoxGeometry(0.34, 2.8, 0.16), dark, 0, -1.2); handle.geometry.translate(0, 0, 0);
    part(new THREE.CylinderGeometry(0.1, 0.1, 0.24, 20), accent, 0, 0.18).rotation.x = Math.PI / 2; settle(parts[parts.length - 1]);
    [-0.9, -2.3].forEach((y) => part(new THREE.CylinderGeometry(0.06, 0.06, 0.2, 12), accent, 0, y).rotation.x = Math.PI / 2);
    parts.slice(-2).forEach(settle);
    const arm = new THREE.Group(); arm.position.set(0, 0.18, 0); piece.add(arm);
    const blade = new THREE.Shape(); blade.moveTo(0, 0); blade.lineTo(0.42, 0); blade.lineTo(0.5, 2.2); blade.quadraticCurveTo(0.2, 2.5, -0.05, 2.2); blade.lineTo(0, 0);
    part(new THREE.ExtrudeGeometry(blade, { depth: 0.04, bevelEnabled: true, bevelThickness: 0.015, bevelSize: 0.015 }), chrome, -0.22, 0, -0.02, arm);
    piece.position.y = 0.3;
    idle = (t) => { arm.rotation.z = -Math.PI * (0.55 + 0.4 * (0.5 + 0.5 * Math.sin(t * 0.9))); piece.rotation.y = Math.sin(t * 0.45) * 0.45; };
  },
  clipper() {   // a pair of clippers, humming
    part(new THREE.CapsuleGeometry(0.52, 2.2, 8, 32), dark, 0, -0.4);
    part(new THREE.CylinderGeometry(0.56, 0.56, 0.3, 32), accent, 0, 0.55);
    part(new THREE.BoxGeometry(0.18, 0.5, 0.12), accent, 0, -0.1, 0.5);
    part(new THREE.BoxGeometry(1.25, 0.32, 0.42), chrome, 0, 1.15);
    const teeth = [];
    for (let i = 0; i < 11; i++) teeth.push(part(new THREE.BoxGeometry(0.06, 0.22, 0.1), chrome, -0.55 + i * 0.11, 1.4, 0.1));
    idle = (t) => { piece.position.x = Math.sin(t * 90) * 0.012; teeth.forEach((m, i) => { m.position.x = m.userData.home.x + Math.sin(t * 40) * 0.025; });
      piece.rotation.z = -0.35 + Math.sin(t * 0.5) * 0.12; piece.rotation.y = Math.sin(t * 0.4) * 0.5; };
  },
  comb() {   // a comb whose teeth fly in one by one
    part(new THREE.BoxGeometry(3.4, 0.5, 0.14), accent, 0, 0.6);
    for (let i = 0; i < 24; i++) { const fine = i > 11; part(new THREE.BoxGeometry(fine ? 0.06 : 0.08, fine ? 1.0 : 1.25, 0.1), i % 2 ? accent : second,
      -1.55 + i * 0.135, fine ? -0.15 : -0.27); }
    idle = (t) => { piece.rotation.z = -0.25 + Math.sin(t * 0.6) * 0.12; piece.rotation.y = Math.sin(t * 0.45) * 0.5; };
  },
  dryer() {   // a hair-dryer with warm air rings drifting out of it
    part(new THREE.CylinderGeometry(0.62, 0.62, 1.9, 40), second, 0, 0.6).rotation.z = Math.PI / 2;
    part(new THREE.CylinderGeometry(0.42, 0.6, 0.6, 40), accent, 1.2, 0.6).rotation.z = Math.PI / 2;
    part(new THREE.TorusGeometry(0.62, 0.06, 12, 40), accent, -0.95, 0.6).rotation.y = Math.PI / 2;
    part(new THREE.CapsuleGeometry(0.24, 1.6, 6, 20), dark, -0.25, -0.75).rotation.z = 0.25;
    part(new THREE.BoxGeometry(0.1, 0.3, 0.12), accent, -0.12, -0.3, 0.24);
    parts.forEach(settle);
    const air = [0, 1, 2].map(() => { const r = new THREE.Mesh(new THREE.TorusGeometry(0.4, 0.025, 8, 40),
      new THREE.MeshBasicMaterial({ color: new THREE.Color(O.gold), transparent: true, opacity: 0 })); r.rotation.y = Math.PI / 2; piece.add(r); return r; });
    idle = (t) => { air.forEach((r, i) => { const k = ((t * 0.6 + i / 3) % 1); r.position.set(1.6 + k * 2.2, 0.6, 0); r.scale.setScalar(1 + k * 1.6); r.material.opacity = 0.7 * (1 - k); });
      piece.rotation.y = -0.4 + Math.sin(t * 0.5) * 0.3; };
  },
  brush() {   // a paddle brush, bristles landing one by one
    part(new THREE.CylinderGeometry(0.95, 0.95, 0.16, 48), dark, 0, 0.9).rotation.x = Math.PI / 2;
    part(new THREE.CylinderGeometry(0.82, 0.82, 0.1, 48), second, 0, 0.9, 0.1).rotation.x = Math.PI / 2;
    parts.forEach(settle);
    for (let i = 0; i < 37; i++) { const a = i * 2.4, r = Math.sqrt(i / 37) * 0.72;
      const b = part(new THREE.CylinderGeometry(0.025, 0.025, 0.28, 8), accent, Math.cos(a) * r, 0.9 + Math.sin(a) * r, 0.28); b.rotation.x = Math.PI / 2; settle(b); }
    part(new THREE.CapsuleGeometry(0.2, 1.9, 6, 20), dark, 0, -1.25);
    idle = (t) => { piece.rotation.y = Math.sin(t * 0.5) * 0.6; piece.rotation.z = Math.sin(t * 0.35) * 0.1; };
  },
  bottle() {   // a glass product bottle with their colour inside and a polished pump
    const pts = [[0, -1.5], [0.75, -1.5], [0.82, -1.3], [0.82, 0.7], [0.5, 1.1], [0.28, 1.25], [0.28, 1.5]].map(([x, y]) => new THREE.Vector2(x, y));
    part(new THREE.LatheGeometry(pts, 48), glass);
    part(new THREE.LatheGeometry([[0, -1.42], [0.72, -1.42], [0.74, -1.3], [0.74, 0.3], [0, 0.3]].map(([x, y]) => new THREE.Vector2(x, y)), 48),
      new THREE.MeshPhysicalMaterial({ color: new THREE.Color(O.second).offsetHSL(0, 0.15, 0.05), roughness: 0.25, clearcoat: 1, emissive: new THREE.Color(O.second), emissiveIntensity: 0.15 }));
    part(new THREE.CylinderGeometry(0.34, 0.34, 0.36, 32), accent, 0, 1.68);
    part(new THREE.CylinderGeometry(0.09, 0.09, 0.5, 16), accent, 0, 2.05);
    part(new THREE.BoxGeometry(0.7, 0.16, 0.2), accent, 0.22, 2.3);
    idle = (t) => { piece.rotation.y = t * 0.35; };
  },
};
(P[O.piece] || P.scissors)();
const holder = new THREE.Group(); holder.add(piece); scene.add(holder);
const ease = (x) => 1 - Math.pow(1 - Math.min(1, Math.max(0, x)), 3);

function place() {
  const w = innerWidth, h = innerHeight; renderer.setSize(w, h, false); cam.aspect = w / h; cam.updateProjectionMatrix();
  // where each layout leaves room, so the headline stays clear: over the photo where there is one, otherwise beside
  // the words on a computer and in a free corner on a phone
  const halfW = Math.tan(THREE.MathUtils.degToRad(cam.fov / 2)) * cam.position.z * cam.aspect;
  const halfH = Math.tan(THREE.MathUtils.degToRad(cam.fov / 2)) * cam.position.z;
  const L = O.layout;
  if (w < 760) {
    const top = L === 'split' || L === 'bold';            // the photo sits at the top of the phone screen
    const corner = L === 'cinema';                        // its buttons fill the bottom: use the corner under the menu
    holder.scale.setScalar(top ? 0.42 : 0.3);
    holder.position.set(halfW - (top ? 1.45 : 1.0), top ? halfH - 3.1 : corner ? halfH - 2.35 : -halfH + 1.4, 0);
  } else {
    holder.scale.setScalar(Math.min(1, w / 1500));
    holder.position.set(L === 'split' ? -halfW * 0.5 : halfW * (L === 'atelier' ? 0.74 : L === 'cinema' ? 0.68 : 0.52), 0.2, 0);
  }
}
addEventListener('resize', place); place();

let px = 0, py = 0;
addEventListener('pointermove', (e) => { px = e.clientX / innerWidth - .5; py = e.clientY / innerHeight - .5; }, { passive: true });
const clock = new THREE.Clock();
function frame(t) {
  const sc = still ? 0 : Math.min(1, scrollY / (innerHeight * 0.75));   // read once per drawn frame, no scroll listener
  let apart = 0;
  parts.forEach((m) => {
    const { home, homeR, off, spin, delay } = m.userData;
    const k = (1 - ease((t - 0.2 - delay) / 1.8)) + sc * 0.85;            // flies in, locks, then comes apart on scroll
    m.position.copy(home).addScaledVector(off, k);
    m.rotation.set(homeR.x + spin.x * k, homeR.y + spin.y * k, homeR.z + spin.z * k);
    apart = Math.max(apart, k);
  });
  accent.emissiveIntensity = Math.min(1.2, apart * 1.4) + (apart < 0.02 ? 0.25 * Math.max(0, 1 - (t - 2.4)) : 0);   // seams glow
  if (apart < 0.05) idle(t);   // its own movement once it's whole
  cv.style.opacity = inView ? Math.max(0, 1 - sc * 1.25).toFixed(3) : '0';   // gone before the next section's words arrive
  holder.rotation.x = py * 0.3; holder.rotation.y = px * 0.45;
  renderer.render(scene, cam);
}
let raf = 0, inView = true;
function loop() { frame(clock.getElapsedTime()); raf = requestAnimationFrame(loop); }
function run() { if (still) { frame(9); return; } if (!raf && inView && !document.hidden) loop(); }
function stop() { cancelAnimationFrame(raf); raf = 0; }
document.addEventListener('visibilitychange', () => (document.hidden ? stop() : run()));
// shown only over the first screen: fades out (and stops drawing) once the visitor scrolls past it
const marker = document.createElement('div');
marker.style.cssText = 'position:absolute;top:0;left:0;width:1px;height:70vh;pointer-events:none';
document.body.prepend(marker);
new IntersectionObserver(([e]) => { inView = e.isIntersecting; cv.classList.toggle('on', inView); inView ? run() : setTimeout(() => { if (!inView) stop(); }, 900); })
  .observe(marker);
requestAnimationFrame(() => cv.classList.add('on')); run();
"""
