"""3D for the premium mock-ups (owner, 28 Oct 2026: "make new for all including everything", after asking for 3D).

Over the first screen of any layout: the business's own logo struck on a 3D medallion (their accent colour as the
metal), turning slowly with a full spin as the page opens, and a few glass shapes in their brand colours drifting
round it. It leans toward the pointer (and the phone's tilt is left alone), and fades away once the visitor scrolls
past the first screen, so it never sits on top of the menu, prices or reviews.

Built by the 3D skills: one WebGL context and transform-only motion (auteur), capped pixel ratio, rendering paused
when the first screen is out of view and when the tab is hidden (threejs-errors-performance), IntersectionObserver
instead of scroll listeners (auteur), a single still frame for reduced motion, and nothing at all when WebGL or the
download fails (web3d-integration-patterns). Placed to the side of the words on a computer and small in the top
corner on a phone, so the headline stays clear (impeccable craft-floor: contrast first).

Only pages whose config has "depth3d": true get it, so mock-ups already sent stay exactly as they were."""
import json
from pathlib import Path

THREE = "https://cdn.jsdelivr.net/npm/three@0.160.0/"


def initials(name: str) -> str:
    words = [w for w in name.replace("&", " ").split() if w[:1].isalnum()]
    return "".join(w[0] for w in words[:2]).upper() or "K"


def add(html: str, c: dict, out: Path) -> str:
    if not c.get("depth3d"):
        return html
    col = c["colours"]
    light = c.get("layout") == "editorial" and col.get("paper", "#000000").lower() > "#888888"
    opts = {"gold": col.get("gold", "#c9a227"), "second": col.get("second") or col.get("gold", "#c9a227"),
            "face": col.get("panel", "#141414") if not light else col.get("paper", "#f5f1ea"),
            "logo": "logo.png" if (out / "logo.png").exists() else "", "initials": initials(c.get("short") or c["name"]),
            "layout": c.get("layout", "atelier")}
    block = (
        '<canvas id="d3" aria-hidden="true"></canvas>'
        "<style>#d3{position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:15;opacity:0;"
        "transition:opacity .9s cubic-bezier(.16,1,.3,1)}#d3.on{opacity:1}"
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

// the medallion: their logo (or initials) on the face, their accent colour as the metal
const face = document.createElement('canvas'); face.width = face.height = 512;
const g = face.getContext('2d');
function paintFace(img) {
  g.fillStyle = O.face; g.beginPath(); g.arc(256, 256, 256, 0, Math.PI * 2); g.fill();
  g.strokeStyle = O.gold; g.lineWidth = 14; g.beginPath(); g.arc(256, 256, 236, 0, Math.PI * 2); g.stroke();
  if (img) { const s = Math.min(300 / img.width, 300 / img.height); g.drawImage(img, 256 - img.width * s / 2, 256 - img.height * s / 2, img.width * s, img.height * s); }
  else { g.fillStyle = O.gold; g.font = '700 190px Georgia, serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(O.initials, 256, 270); }
  faceTex.needsUpdate = true;
}
const faceTex = new THREE.CanvasTexture(face); faceTex.colorSpace = THREE.SRGBColorSpace; faceTex.anisotropy = 4;
faceTex.center.set(0.5, 0.5); faceTex.rotation = Math.PI / 2;   // the cylinder's cap lies sideways: turn the logo upright
paintFace(null);
if (O.logo) { const im = new Image(); im.onload = () => paintFace(im); im.src = O.logo; }
const metal = new THREE.MeshPhysicalMaterial({ color: new THREE.Color(O.gold), metalness: 1, roughness: 0.28, clearcoat: 0.6 });
const faceMat = new THREE.MeshPhysicalMaterial({ map: faceTex, metalness: 0.25, roughness: 0.35, clearcoat: 1, clearcoatRoughness: 0.08 });
const coin = new THREE.Mesh(new THREE.CylinderGeometry(1.6, 1.6, 0.22, 96), [metal, faceMat, faceMat]);
coin.rotation.x = Math.PI / 2; const holder = new THREE.Group(); holder.add(coin); scene.add(holder);

// glass shapes in the brand colours, drifting round it
const glass = (c) => new THREE.MeshPhysicalMaterial({ color: new THREE.Color(c), transmission: 0.92, thickness: 1.2, roughness: 0.06, ior: 1.5,
  attenuationColor: new THREE.Color(c), attenuationDistance: 1.6, clearcoat: 1, iridescence: 0.4, transparent: true });
const shapes = [
  [new THREE.TorusGeometry(0.75, 0.16, 20, 80), O.gold, [-2.6, 1.6, -1.5]],
  [new THREE.IcosahedronGeometry(0.6, 0), O.second, [2.4, -1.5, -0.8]],
  [new THREE.OctahedronGeometry(0.45, 0), O.gold, [2.1, 1.9, -2.2]],
  [new THREE.SphereGeometry(0.38, 40, 28), O.second, [-2.2, -1.9, -0.4]],
].map(([geo, c, p], i) => { const m = new THREE.Mesh(geo, glass(c)); m.position.set(...p); m.userData = { p, i }; holder.add(m); return m; });

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
    holder.position.set(halfW - (top ? 1.45 : 1.0), top ? halfH - 3.1 : corner ? halfH - 2.35 : -halfH + 1.1, 0);
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
  const intro = Math.min(1, t / 2.2), ease = 1 - Math.pow(1 - intro, 3);
  coin.rotation.z = -(1 - ease) * Math.PI * 2 + Math.sin(t * 0.5) * 0.35;   // one full spin as the page opens, then a slow sway
  holder.rotation.x = py * 0.35; holder.rotation.y = px * 0.5;
  shapes.forEach((m) => { const { p, i } = m.userData; m.position.y = p[1] + Math.sin(t * 0.7 + i * 1.7) * 0.22;
    m.rotation.x = t * 0.3 + i; m.rotation.y = t * 0.4 + i; });
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
