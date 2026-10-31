# lowkey.lore Blender library: shared by every videos\NN-slug\scene.py
# Same look as hole-to-well v3 (Poly Haven PBR textures, strata cutaway at y=0, HDRI sky, lawn + grass blades),
# plus: fast EEVEE settings (see FAST below), smooth clear water, one persistent animation render.
# Coordinates are plain Blender: z up, camera on the -y side looking +y, the cutaway face is y=0.
import bpy, bmesh, math, json, os, sys, random, time
from mathutils import Vector, Matrix

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
ASSETS = os.path.join(ROOT, 'assets'); TEX = os.path.join(ASSETS, 'textures')
W, H, FPS = 1080, 1920, 30
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(name, default=None): return args[args.index(name) + 1] if name in args else default
VDIR = os.path.abspath(arg('--video'))
TL = json.load(open(os.path.join(VDIR, 'timeline.json')))
seg = [(s['start'], s['end']) for s in TL['segments']]
TOTAL = TL['total']; NFRAMES = int(math.ceil(TOTAL * FPS)) + 1
FRAMES_DIR = os.path.abspath(arg('--framesdir') or os.path.join(VDIR, 'frames')); CAMS_DIR = os.path.abspath(arg('--camsdir') or os.path.join(VDIR, 'cams'))

GAP = 0.2
def clamp(x, a=0.0, b=1.0): return min(b, max(a, x))
def ease(x): x = clamp(x); return 4 * x * x * x if x < .5 else 1 - pow(-2 * x + 2, 3) / 2
def eo(x): x = clamp(x); return 1 - pow(1 - x, 3)
def back(x, s=1.7): x = clamp(x); return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2
def lerp(a, b, x): return a + (b - a) * x
def P(i, t, a=0.0, b=1.0):
    s, e = seg[i]; x = (t - s) / (e - s); return clamp((x - a) / (b - a))
def after(i, t, frac=0.0): return t >= seg[i][0] + (seg[i][1] - seg[i][0]) * frac
def inSeg(i, t): return seg[i][0] - GAP <= t < seg[i][1] + GAP
def stagger(p, i, n, width=0.35):
    """progress of item i of n when the whole group runs 0..1 over p"""
    st = (1 - width) * i / max(1, n - 1); return clamp((p - st) / width)

# ================================================================= SCENE / RENDER SETTINGS
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x, scene.render.resolution_y = W, H
scene.render.resolution_percentage = int(arg('--pct', '100'))
scene.render.fps = FPS
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.image_settings.compression = 15
scene.render.use_overwrite = False          # resume: frames already on disk are skipped
scene.render.use_placeholder = True
ee = scene.eevee
# Render speed (RX 6600, 1080x1920). v3 took ~10 s/frame. The cost was not the quality settings: it was
#  1. the sun shadow map re-rendering ~1M-poly Poly Haven trees on every sample -> invisible low-poly shadow
#     proxies stand in for trees (scatter/shadow_proxy), -3.7 s
#  2. point-light shadows (6 cube faces per sample) -> off by default (point_light), -0.7 s
#  3. a fresh bpy.ops.render per frame + hide_render written every frame (full re-sync) -> one persistent
#     animation render, visibility written only on change (run/show)
# With those, v3's own quality settings (16 samples, full-res tracing, fast GI, 2x8 shadow rays) run at
# ~1.1 s/frame, so they stay the default. --fast drops to 10 samples / quarter-res tracing (~0.7 s/frame).
FAST = '--fast' in args
HQ = not FAST and '--v3' not in args   # 31 Oct 2026: owner asked to raise quality in every form; renders may take longer
ee.taa_render_samples = int(arg('--samples', '10' if FAST else ('32' if HQ else '16')))
ee.use_raytracing = True
try:
    ee.ray_tracing_method = 'SCREEN'
    ee.ray_tracing_options.resolution_scale = '4' if FAST else ('1' if HQ else '2')
    ee.ray_tracing_options.use_denoise = True
    ee.ray_tracing_options.trace_max_roughness = 0.35 if FAST else 0.5
except Exception: pass
ee.use_fast_gi = not FAST
try:
    ee.fast_gi_method = 'GLOBAL_ILLUMINATION'; ee.fast_gi_distance = 2.5; ee.fast_gi_quality = 0.5
    ee.horizon_quality = 0.25 if FAST else 0.5
except Exception: pass
ee.use_shadows = True
ee.shadow_ray_count = 1 if FAST else (3 if HQ else 2)
ee.shadow_step_count = 4 if FAST else (12 if HQ else 8)
ee.shadow_resolution_scale = 0.5 if FAST else 1.0
try: ee.volumetric_tile_size = '16'
except Exception: pass
for vt, look in (('AgX', 'AgX - Medium High Contrast'), ('Filmic', 'Medium High Contrast')):
    try:
        scene.view_settings.view_transform = vt
        try: scene.view_settings.look = look
        except Exception: pass
        break
    except Exception: pass
scene.view_settings.exposure = 0.15
if HQ:
    try: ee.fast_gi_quality = 0.8; ee.fast_gi_distance = 4.0; ee.horizon_quality = 0.75
    except Exception: pass
    scene.render.use_motion_blur = True; scene.render.motion_blur_shutter = 0.4
    try: ee.motion_blur_steps = 1
    except Exception: pass
if arg('--set'): exec(arg('--set'))   # benchmarking hook, e.g. --set "ee.use_raytracing=False"

COL = bpy.data.collections.new('Scene'); scene.collection.children.link(COL)
def link(o): COL.objects.link(o); return o

# ================================================================= MATERIALS
_imgs = {}
def img(path, non_color=False):
    key = (path, non_color)
    if key not in _imgs:
        im = bpy.data.images.load(path, check_existing=True)
        if non_color: im.colorspace_settings.name = 'Non-Color'
        _imgs[key] = im
    return _imgs[key]
def texfile(tid, kind):
    for ext in ('jpg', 'png'):
        p = os.path.join(TEX, tid, f'{tid}_{kind}.{ext}')
        if os.path.exists(p): return p
    return None

class MB:
    """tiny node-tree builder"""
    def __init__(self, name):
        self.m = bpy.data.materials.new(name)
        try: self.m.use_nodes = True
        except Exception: pass
        self.nt = self.m.node_tree; self.N = self.nt.nodes; self.L = self.nt.links; self.N.clear()
        self.out = self.N.new('ShaderNodeOutputMaterial'); self.bsdf = self.N.new('ShaderNodeBsdfPrincipled')
        self.L.new(self.bsdf.outputs[0], self.out.inputs[0])
    def n(self, t, **kw):
        nd = self.N.new(t)
        for k, v in kw.items(): setattr(nd, k, v)
        return nd
    def ln(self, a, b): self.L.new(a, b)
    def val(self, v, label=None):
        nd = self.n('ShaderNodeValue'); nd.outputs[0].default_value = v
        if label: nd.label = label
        return nd
    def math(self, op, a, b=None, clamp_=False):
        nd = self.n('ShaderNodeMath', operation=op, use_clamp=clamp_)
        for i, x in enumerate((a, b)):
            if x is None: continue
            if isinstance(x, (int, float)): nd.inputs[i].default_value = x
            else: self.ln(x, nd.inputs[i])
        return nd.outputs[0]
    def mix(self, fac, a, b, blend='MIX'):
        nd = self.n('ShaderNodeMix', data_type='RGBA', blend_type=blend)
        for sock, x in ((nd.inputs[0], fac), (nd.inputs[6], a), (nd.inputs[7], b)):
            if isinstance(x, (int, float, tuple)): sock.default_value = x
            else: self.ln(x, sock)
        return nd.outputs[2]
    def coords(self, scale=1.0, space='Object', rot=(0, 0, 0)):
        tc = self.n('ShaderNodeTexCoord'); mp = self.n('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = (scale,) * 3 if not isinstance(scale, tuple) else scale
        mp.inputs['Rotation'].default_value = rot
        self.ln(tc.outputs[space], mp.inputs[0]); return mp.outputs[0]
    def tex(self, path, vec, box=True, non_color=False):
        t = self.n('ShaderNodeTexImage'); t.image = img(path, non_color)
        if box: t.projection = 'BOX'; t.projection_blend = 0.25
        self.ln(vec, t.inputs[0]); return t
    def pbr(self, tid, vec, box=True):
        d = self.tex(texfile(tid, 'diff'), vec, box)
        rp = texfile(tid, 'rough'); r = self.tex(rp, vec, box, True).outputs[0] if rp else None
        np_ = texfile(tid, 'nor'); nn = self.tex(np_, vec, box, True).outputs[0] if np_ else None
        return d.outputs[0], r, nn
    def normal(self, ncol, strength=1.0):
        nm = self.n('ShaderNodeNormalMap'); nm.inputs[0].default_value = strength
        self.ln(ncol, nm.inputs[1]); return nm.outputs[0]
    def set(self, name, v):
        s = self.bsdf.inputs[name]
        if isinstance(v, (int, float, tuple)): s.default_value = v
        else: self.ln(v, s)

def pbr_mat(name, tid, scale=1.0, tint=None, tint_fac=0.0, rough_add=0.0, metal=0.0, nstr=1.0,
            box=True, space='Object', hsv=None, bright=1.0, rot=(0, 0, 0), ret_builder=False):
    b = MB(name); vec = b.coords(scale, space, rot)
    c, r, nn = b.pbr(tid, vec, box)
    if hsv:
        h = b.n('ShaderNodeHueSaturation'); h.inputs['Hue'].default_value = hsv[0]
        h.inputs['Saturation'].default_value = hsv[1]; h.inputs['Value'].default_value = hsv[2]
        b.ln(c, h.inputs['Color']); c = h.outputs[0]
    if tint and tint_fac > 0: c = b.mix(tint_fac, c, tint + (1,))
    if bright != 1.0: c = b.mix(1.0, c, (bright, bright, bright, 1), 'MULTIPLY')
    b.set('Base Color', c)
    if r is not None: b.set('Roughness', b.math('ADD', r, rough_add, True) if rough_add else r)
    b.set('Metallic', metal)
    if nn is not None: b.set('Normal', b.normal(nn, nstr))
    b.color = c
    return b if ret_builder else b.m

def flat_mat(name, color, rough=0.5, metal=0.0, emit=None, emit_str=0.0, alpha=1.0, coat=0.0):
    b = MB(name)
    b.set('Base Color', tuple(color) + (1,)); b.set('Roughness', rough); b.set('Metallic', metal)
    if emit: b.set('Emission Color', tuple(emit) + (1,)); b.set('Emission Strength', emit_str)
    if coat: b.set('Coat Weight', coat)
    if alpha < 1: b.set('Alpha', alpha); b.m.surface_render_method = 'BLENDED'
    return b.m

def glass_mat(name, tint=(0.75, 0.85, 0.9), alpha=0.25):
    """clear glass without screen-space refraction (cheap, no blocky artefacts)"""
    b = MB(name); b.set('Base Color', tint + (1,)); b.set('Roughness', 0.02); b.set('Alpha', alpha)
    b.set('Coat Weight', 1.0); b.m.surface_render_method = 'BLENDED'; return b.m

def water_mat(name, color=(0.12, 0.42, 0.62), alpha=0.62, ripple=0.05, spec=0.45, rough=0.07):
    """Smooth, clear water for cutaways. v3 used raytraced refraction through a dithered surface, which at
    half-resolution tracing showed the stones behind as big blue blocks. This one is a blended, non-refractive
    surface: a soft depth gradient, glossy highlights and fine ripples only. Underground water: use a low spec
    (no sky to reflect down there; screen-space misses fall back to the sky and look white). Returns (material, nodes)."""
    b = MB(name)
    rgb = b.n('ShaderNodeRGB'); rgb.outputs[0].default_value = color + (1,); rgb.label = 'WCOL'
    geo = b.n('ShaderNodeNewGeometry'); sep = b.n('ShaderNodeSeparateXYZ'); b.ln(geo.outputs['Position'], sep.inputs[0])
    # deeper (lower world z, relative to TOP) -> darker & more opaque
    top = b.val(0.0, 'WTOP')
    depth = b.math('SUBTRACT', top.outputs[0], sep.outputs[2])
    df = b.math('MINIMUM', b.math('MULTIPLY', depth, 0.35), 1.0)
    df = b.math('MAXIMUM', df, 0.0)
    deep = b.mix(1.0, rgb.outputs[0], (0.35, 0.45, 0.55, 1), 'MULTIPLY')
    col = b.mix(df, rgb.outputs[0], deep)
    col = b.mix(1.0, col, (0.6, 0.6, 0.6, 1), 'MULTIPLY')   # water is dark; the colour comes from depth, not albedo
    b.set('Base Color', col); b.set('Roughness', rough); b.set('Specular IOR Level', spec)
    a = b.val(alpha, 'WALPHA')
    b.set('Alpha', b.math('MINIMUM', b.math('ADD', a.outputs[0], b.math('MULTIPLY', df, 0.25)), 0.95))
    b.set('Emission Color', col); emis = b.val(0.12, 'WEMIT'); b.set('Emission Strength', emis.outputs[0])
    tm = b.val(0.0, 'WTIME')
    nz = b.n('ShaderNodeTexNoise'); nz.noise_dimensions = '4D'; nz.inputs['Scale'].default_value = 7.0
    nz.inputs['Detail'].default_value = 2.0; nz.inputs['Roughness'].default_value = 0.4
    b.ln(geo.outputs['Position'], nz.inputs['Vector']); b.ln(tm.outputs[0], nz.inputs['W'])
    bump = b.n('ShaderNodeBump'); bump.inputs['Strength'].default_value = ripple; bump.inputs['Distance'].default_value = 0.02
    b.ln(nz.outputs[0], bump.inputs['Height']); b.set('Normal', bump.outputs[0])
    b.m.surface_render_method = 'BLENDED'
    try: b.m.use_transparency_overlap = False
    except Exception: pass
    return b.m, dict(color=rgb, top=top, alpha=a, emit=emis, time=tm)

# ================================================================= MESH HELPERS
def mesh_obj(name, bm, mat=None, smooth=False, mats=()):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new(name, me); link(o)
    if mat: me.materials.append(mat)
    for m in mats: me.materials.append(m)
    return o

def box(name, x0, x1, y0, y1, z0, z1, mat=None, bevel=0.0, segs=2):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    sx, sy, sz = x1 - x0, y1 - y0, z1 - z0
    for v in bm.verts: v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz))
    if bevel > 0: bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=segs, affect='EDGES', profile=0.5)
    o = mesh_obj(name, bm, mat, smooth=bevel > 0)
    o.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2); return o

def cyl(name, r, h, mat=None, segs=32, r2=None, smooth=True, caps=True, axis='Z', cap_mat=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, segments=segs, radius1=r, radius2=r if r2 is None else r2, depth=h)
    if cap_mat is not None:
        for f in bm.faces:
            if abs(f.normal.z) > 0.99: f.material_index = 1
    o = mesh_obj(name, bm, mat, smooth, mats=(cap_mat,) if cap_mat is not None else ())
    if smooth and caps:
        for p in o.data.polygons:
            if abs(p.normal.z) > 0.99: p.use_smooth = False
    # the axis turn is baked into the mesh, so the object's own rotation stays free: a wheel made with axis='X'
    # rolls with rotation_euler.x (it used to be an object rotation, and spinning it on X tipped it over: the
    # "roller spinning round" glitch)
    if axis in ('X', 'Y'):
        o.data.transform(Matrix.Rotation(math.pi / 2, 4, 'Y' if axis == 'X' else 'X'))
    return o

def half_tube(name, r_out, r_in, z0, z1, mat, segs=48, a0=0.0, a1=math.pi):
    """half (or partial) tube on the back side of the cut plane (y>=0), axis z. r_in=0 -> solid half cylinder"""
    bm = bmesh.new()
    def ring(r, z): return [bm.verts.new((r * math.cos(a0 + (a1 - a0) * i / segs), r * math.sin(a0 + (a1 - a0) * i / segs), z)) for i in range(segs + 1)]
    if r_in > 0:
        ob, ot, ib, it = ring(r_out, z0), ring(r_out, z1), ring(r_in, z0), ring(r_in, z1)
        for i in range(segs):
            bm.faces.new((ob[i], ob[i + 1], ot[i + 1], ot[i])); bm.faces.new((ib[i + 1], ib[i], it[i], it[i + 1]))
            bm.faces.new((ot[i], ot[i + 1], it[i + 1], it[i])); bm.faces.new((ob[i + 1], ob[i], ib[i], ib[i + 1]))
        bm.faces.new((ob[0], ib[0], it[0], ot[0])); bm.faces.new((ib[segs], ob[segs], ot[segs], it[segs]))
    else:
        ob, ot = ring(r_out, z0), ring(r_out, z1); cb, ct = bm.verts.new((0, 0, z0)), bm.verts.new((0, 0, z1))
        for i in range(segs):
            bm.faces.new((ob[i], ob[i + 1], ot[i + 1], ot[i])); bm.faces.new((ct, ot[i], ot[i + 1])); bm.faces.new((cb, ob[i + 1], ob[i]))
        bm.faces.new((ob[0], ot[0], ct, cb)); bm.faces.new((cb, ct, ot[segs], ob[segs]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_obj(name, bm, mat)

def profile_tube(name, prof, y0, y1, mat, thick=0.0, cap=True):
    """extrude a closed 2D profile [(x,z),...] along +y from y0 to y1 (tunnels, pipes in section).
    thick>0 makes a hollow wall of that thickness (profile is the inside edge)."""
    bm = bmesh.new(); n = len(prof)
    def ctr():
        cx = sum(p[0] for p in prof) / n; cz = sum(p[1] for p in prof) / n; return cx, cz
    cx, cz = ctr()
    def scaled(s):
        out = []
        for x, z in prof:
            dx, dz = x - cx, z - cz; L = math.hypot(dx, dz) or 1
            out.append((x + dx / L * s, z + dz / L * s))
        return out
    if thick > 0:
        inn, outr = prof, scaled(thick)
        rings = {}
        for key, pr in (('i', inn), ('o', outr)):
            rings[key] = ([bm.verts.new((x, y0, z)) for x, z in pr], [bm.verts.new((x, y1, z)) for x, z in pr])
        for i in range(n):
            j = (i + 1) % n
            ia, ib = rings['i']; oa, ob = rings['o']
            bm.faces.new((ia[j], ia[i], ib[i], ib[j])); bm.faces.new((oa[i], oa[j], ob[j], ob[i]))
            bm.faces.new((oa[j], oa[i], ia[i], ia[j])); bm.faces.new((ob[i], ob[j], ib[j], ib[i]))
    else:
        a = [bm.verts.new((x, y0, z)) for x, z in prof]; b = [bm.verts.new((x, y1, z)) for x, z in prof]
        for i in range(n):
            j = (i + 1) % n; bm.faces.new((a[i], a[j], b[j], b[i]))
        if cap: bm.faces.new(a[::-1]); bm.faces.new(b)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_obj(name, bm, mat)

def curve_tube(name, pts, r, mat, bevel_res=4):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    cu.bevel_depth = r; cu.bevel_resolution = bevel_res; cu.use_fill_caps = True
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts): sp.points[i].co = (p[0], p[1], p[2], 1)
    o = bpy.data.objects.new(name, cu); link(o); cu.materials.append(mat); return o

def bend_path(pts, rad=0.25, n=6):
    out = [Vector(pts[0])]
    for i in range(1, len(pts) - 1):
        a, b, c = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[i + 1])
        d1, d2 = (b - a).normalized(), (c - b).normalized()
        r = min(rad, (b - a).length / 2, (c - b).length / 2); p0, p2 = b - d1 * r, b + d2 * r
        for k in range(n + 1):
            u = k / n; out.append((1 - u) ** 2 * p0 + 2 * (1 - u) * u * b + u * u * p2)
    out.append(Vector(pts[-1])); return out
def poly_len(pts): return sum((pts[i + 1] - pts[i]).length for i in range(len(pts) - 1))
def poly_at(pts, u):
    L = poly_len(pts) * clamp(u); acc = 0
    for i in range(len(pts) - 1):
        l = (pts[i + 1] - pts[i]).length
        if acc + l >= L and l > 0: return pts[i].lerp(pts[i + 1], (L - acc) / l)
        acc += l
    return pts[-1].copy()

def lumpy(name, r, mat, seed=1, squash=0.45, subdiv=3, amp=0.18):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=r); rnd = random.Random(seed)
    for v in bm.verts:
        n = v.co.normalized()
        v.co += n * r * amp * (math.sin(v.co.x * 3.1 + seed) * math.cos(v.co.y * 2.7) + rnd.uniform(-.5, .5)); v.co.z *= squash
    return mesh_obj(name, bm, mat, smooth=True)

def pivot_at(o, p=(0.0, 0.0, 0.0)):
    """move an object's origin to point p (in its parent space) without moving its geometry, so rotations turn it
    about p (spokes and paddles must turn about the axle, not about their own middles)"""
    off = o.location - Vector(p)
    o.data.transform(Matrix.Translation(off)); o.location = Vector(p); return o

SPAN = {}
def span(o, y0, y1):
    """show an object that runs along +y only between y0 and y1 (progressive laying / digging along a road or track)"""
    if o.name not in SPAN:
        bpy.context.view_layer.update(); SPAN[o.name] = (o.dimensions.y if o.dimensions.y > 0 else 1.0)
    l0 = SPAN[o.name]; ln = max(0.0, y1 - y0)
    if ln < 1e-3:
        show(o, False); return
    show(o, True); o.scale.y = ln / l0; o.location.y = (y0 + y1) / 2

def empty(name, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None); e.location = loc; link(e); return e
def parent(children, p):
    for c in children: c.parent = p
    return p

def show(o, v):
    # only write on change: toggling visibility forces EEVEE to re-sync, so never touch it needlessly
    if o.hide_render == v: o.hide_render = not v
    if o.hide_viewport == v: o.hide_viewport = not v
    for c in o.children: show(c, v)

def append_collection(model, prefer=('_LOD0', '')):
    path = os.path.join(ASSETS, 'models', model, model + '.blend')
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        names = [model + s for s in prefer if model + s in src.collections] or list(src.collections)[:1]
        dst.collections = names[:1]
    return dst.collections[0]
def place_collection(coll, loc, rot_z=0.0, scale=1.0, name=None):
    e = bpy.data.objects.new(name or coll.name + '_inst', None)
    e.instance_type = 'COLLECTION'; e.instance_collection = coll
    e.location = loc; e.rotation_euler = (0, 0, rot_z); e.scale = (scale,) * 3; link(e); return e
_colls = {}
def try_coll(m, prefer=('_LOD0', '')):
    if m not in _colls:
        try: _colls[m] = append_collection(m, prefer)
        except Exception as e: print('asset fail', m, e); _colls[m] = None
    return _colls[m]
def append_object(model, objname=None):
    path = os.path.join(ASSETS, 'models', model, model + '.blend')
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if (objname is None or n == objname)]
    objs = [o for o in dst.objects if o]
    for o in objs: link(o)
    return objs

# ================================================================= WORLD
def world(hdri='kloofendal_48d_partly_cloudy_puresky_4k.hdr', rot=200, strength=1.0):
    w = bpy.data.worlds.new('Sky'); scene.world = w
    try: w.use_nodes = True
    except Exception: pass
    wn = w.node_tree.nodes; wl = w.node_tree.links; wn.clear()
    env = wn.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(os.path.join(ASSETS, 'hdri', hdri))
    mp = wn.new('ShaderNodeMapping'); tc = wn.new('ShaderNodeTexCoord'); mp.inputs['Rotation'].default_value = (0, 0, math.radians(rot))
    wl.new(tc.outputs['Generated'], mp.inputs[0]); wl.new(mp.outputs[0], env.inputs[0])
    tint = wn.new('ShaderNodeMix'); tint.data_type = 'RGBA'; tint.blend_type = 'MULTIPLY'; tint.inputs[0].default_value = 1.0
    tint.inputs[7].default_value = (1, 1, 1, 1)
    wl.new(env.outputs[0], tint.inputs[6])
    bg = wn.new('ShaderNodeBackground'); bg.inputs[1].default_value = strength
    wo = wn.new('ShaderNodeOutputWorld'); wl.new(tint.outputs[2], bg.inputs[0]); wl.new(bg.outputs[0], wo.inputs[0])
    return dict(bg=bg, tint=tint)

def sun(frm=(14, -18, 26), to=(8, 4, -4), energy=4.2, color=(1.0, 0.95, 0.87), angle=2.5):
    d = bpy.data.lights.new('Sun', 'SUN'); d.energy = energy; d.angle = math.radians(angle); d.color = color
    o = bpy.data.objects.new('Sun', d); link(o)
    o.rotation_euler = (Vector(frm) - Vector(to)).normalized().to_track_quat('Z', 'Y').to_euler(); return o

def point_light(name, loc, energy=200, color=(1, .6, .3), radius=0.2, shadow=False):
    """shadow off by default: a point-light shadow re-renders the scene into 6 cube faces every sample (~0.7 s/frame)"""
    d = bpy.data.lights.new(name, 'POINT'); d.energy = energy; d.color = color; d.shadow_soft_size = radius; d.use_shadow = shadow
    o = bpy.data.objects.new(name, d); o.location = loc; link(o); return o

# ================================================================= GROUND (strata cutaway + lawn)
DEFAULT_LAYERS = [  # top z, texture, scale, hsv
    (0.0, 'excavated_soil_wall', 0.38, (0.5, 1.0, 0.8)),
    (-2.6, 'excavated_soil_wall', 0.3, (0.485, 1.15, 1.15)),
    (-5.2, 'rocky_gravel', 0.55, (0.5, 0.75, 0.8)),
    (-8.6, 'cliff_side', 0.22, (0.5, 0.55, 0.8)),
    (-13.5, 'rock_wall_10', 0.3, (0.5, 0.6, 0.75)),
    (-17.0, 'rock_face_03', 0.18, (0.5, 0.5, 0.6))]

def ground_material(layers=DEFAULT_LAYERS, top_tex='leafy_grass', top_color=(0.055, 0.16, 0.018), stripes=True,
                    top_mode='lawn', wet_bands=()):
    """strata by world z with wavy seams; up-facing surfaces at z~0 get the lawn (or a texture when top_mode='tex').
    wet_bands: [(z_top, z_bot)] -> returns value nodes to tint those bands blue (groundwater)."""
    G = MB('Ground')
    geo = G.n('ShaderNodeNewGeometry'); POS = geo.outputs['Position']
    sep = G.n('ShaderNodeSeparateXYZ'); G.ln(POS, sep.inputs[0])
    nz = G.n('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.35; nz.inputs['Detail'].default_value = 4
    G.ln(POS, nz.inputs['Vector'])
    zz = G.math('ADD', sep.outputs[2], G.math('MULTIPLY', G.math('SUBTRACT', nz.outputs[0], 0.5), 0.9))
    col = rough = nor = None
    for i, (top, tid, sc, hsv) in enumerate(layers):
        mp = G.n('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (sc,) * 3
        mp.inputs['Location'].default_value = (i * 3.7, i * 1.3, 0); G.ln(POS, mp.inputs[0])
        c, r, nn = G.pbr(tid, mp.outputs[0])
        h = G.n('ShaderNodeHueSaturation'); h.inputs['Hue'].default_value = hsv[0]
        h.inputs['Saturation'].default_value = hsv[1]; h.inputs['Value'].default_value = hsv[2]; G.ln(c, h.inputs['Color']); c = h.outputs[0]
        if col is None: col, rough, nor = c, r, nn
        else:
            f = G.math('LESS_THAN', zz, top); col = G.mix(f, col, c); rough = G.mix(f, rough, r); nor = G.mix(f, nor, nn)
    seam = None
    for top, *_ in layers[1:]:
        s_ = G.math('LESS_THAN', G.math('ABSOLUTE', G.math('SUBTRACT', zz, top)), 0.06)
        seam = s_ if seam is None else G.math('MAXIMUM', seam, s_)
    if seam is not None: col = G.mix(G.math('MULTIPLY', seam, 0.35), col, (0.08, 0.06, 0.05, 1))
    col = G.mix(G.math('MULTIPLY', G.math('GREATER_THAN', sep.outputs[2], -0.45), 0.55), col, (0.07, 0.05, 0.035, 1), 'MULTIPLY')
    wets = []
    for (zt, zb) in wet_bands:
        v = G.val(0.0, 'WET'); wets.append(v)
        inb = G.math('MULTIPLY', G.math('LESS_THAN', zz, zt), G.math('GREATER_THAN', zz, zb))
        wf = G.math('MULTIPLY', inb, v.outputs[0])
        col = G.mix(G.math('MULTIPLY', wf, 0.7), col, (0.45, 0.55, 0.68, 1), 'MULTIPLY')
        col = G.mix(G.math('MULTIPLY', wf, 0.14), col, (0.12, 0.32, 0.7, 1))
        rough = G.mix(wf, rough, (0.18, 0.18, 0.18, 1))
    # generic stain field: STAIN value * mask(distance to STAINPOS < STAINR) tints soil brown-green
    stain_v = G.val(0.0, 'STAIN'); sp = G.n('ShaderNodeCombineXYZ'); sp.label = 'STAINPOS'
    dist = G.n('ShaderNodeVectorMath', operation='DISTANCE'); G.ln(POS, dist.inputs[0]); G.ln(sp.outputs[0], dist.inputs[1])
    sr = G.val(1.0, 'STAINR')
    sm = G.math('MULTIPLY', G.math('LESS_THAN', G.math('ADD', dist.outputs['Value'], G.math('MULTIPLY', nz.outputs[0], 1.2)), sr.outputs[0]), stain_v.outputs[0])
    col = G.mix(G.math('MULTIPLY', sm, 0.75), col, (0.16, 0.13, 0.04, 1), 'MULTIPLY')
    # top surface
    mpg = G.n('ShaderNodeMapping'); mpg.inputs['Scale'].default_value = (0.9, 0.9, 0.9); G.ln(POS, mpg.inputs[0])
    gc, gr, gn = G.pbr(top_tex, mpg.outputs[0], box=False)
    if top_mode == 'lawn':
        bwn = G.n('ShaderNodeRGBToBW'); G.ln(gc, bwn.inputs[0])
        gdet = G.math('MINIMUM', G.math('MULTIPLY', bwn.outputs[0], 1.7), 1.1)
        gc = G.mix(0.0, top_color + (1,), (1, 1, 1, 1)); gc = G.mix(1.0, gc, gdet, 'MULTIPLY')
        gnz = G.n('ShaderNodeTexNoise'); gnz.inputs['Scale'].default_value = 0.08; G.ln(POS, gnz.inputs['Vector'])
        gc = G.mix(G.math('MULTIPLY', gnz.outputs[0], 0.25), gc, (0.1, 0.17, 0.03, 1))
        if stripes:
            stripe = G.math('GREATER_THAN', G.math('SINE', G.math('MULTIPLY', sep.outputs[0], math.pi / 1.6)), 0.0)
            gc = G.mix(stripe, gc, (1.18, 1.22, 1.0, 1), 'MULTIPLY')
            gc = G.mix(G.math('SUBTRACT', 1.0, stripe), gc, (0.82, 0.86, 0.8, 1), 'MULTIPLY')
    sepn = G.n('ShaderNodeSeparateXYZ'); G.ln(geo.outputs['Normal'], sepn.inputs[0])
    is_top = G.math('MULTIPLY', G.math('GREATER_THAN', sepn.outputs[2], 0.7), G.math('GREATER_THAN', sep.outputs[2], -0.05))
    is_floor = G.math('MULTIPLY', G.math('GREATER_THAN', sepn.outputs[2], 0.7), G.math('LESS_THAN', sep.outputs[2], -0.05))
    col = G.mix(G.math('MULTIPLY', is_floor, 0.6), col, (0.12, 0.08, 0.05, 1), 'MULTIPLY')
    G.set('Base Color', G.mix(is_top, col, gc)); G.set('Roughness', G.mix(is_top, rough, gr)); G.set('Normal', G.normal(G.mix(is_top, nor, gn), 1.6))
    G.wets = wets; G.stain = dict(v=stain_v, pos=sp, r=sr)
    return G

class Ground:
    """ground block x0..x1, y 0..y1 (cut face at y=0), z zb..0 with boolean cutters (a collection)"""
    def __init__(self, mat, x0=-16, x1=34, y1=34, zb=-40, far=True):
        self.x0, self.x1, self.y1 = x0, x1, y1
        self.obj = box('Ground', x0, x1, 0.0, y1, zb, 0.0, mat)
        self.cutters = bpy.data.collections.new('Cutters'); scene.collection.children.link(self.cutters)
        self.cutters.hide_render = True
        m = self.obj.modifiers.new('cuts', 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.operand_type = 'COLLECTION'
        m.collection = self.cutters
        m.solver = 'MANIFOLD' if 'MANIFOLD' in [i.identifier for i in m.bl_rna.properties['solver'].enum_items] else 'EXACT'
        if far:
            box('FarLawn', -400, 400, y1, 400, -0.6, -0.02, mat)
            box('LawnL', -400, x0, 0.0, y1, -0.6, -0.02, mat); box('LawnR', x1, 400, 0.0, y1, -0.6, -0.02, mat)
    def cutter(self, o):
        for c in o.users_collection: c.objects.unlink(o)
        self.cutters.objects.link(o); o.display_type = 'WIRE'; return o
    def cut_box(self, name, x0, x1, y0, y1, z0, z1): return self.cutter(box(name, x0, x1, y0, y1, z0, z1))
    def cut_cyl(self, name, r, segs=64): return self.cutter(cyl(name, r, 1.0, segs=segs, smooth=False))

def set_cut_depth(o, depth, top=1.0):
    """z-axis cylinder/box cutter of unit height: from z=top down to -depth (hidden when ~0)"""
    if depth <= 0.01: o.scale = (0.001, 0.001, 0.001); o.location.z = 50; return
    h = depth + top; o.scale = (o.scale.x if o.scale.x > .01 else 1, o.scale.y if o.scale.y > .01 else 1, h); o.location.z = top - h / 2

def grass_blades(x0, x1, excluded=lambda x, y: False, bands=((0.0, 1.2, 2600), (1.2, 4.0, 1100), (4.0, 10.0, 260)), seed=11):
    if '--nograss' in args: return None
    rnd = random.Random(seed); verts, faces, cols = [], [], []
    for y0, y1, dens in bands:
        for _ in range(int((x1 - x0) * (y1 - y0) * dens)):
            x = rnd.uniform(x0 + 0.05, x1 - 0.05); y = rnd.uniform(y0 + 0.01, y1)
            if excluded(x, y): continue
            hgt = rnd.uniform(0.035, 0.085); w = rnd.uniform(0.004, 0.008)
            a = rnd.uniform(0, math.pi * 2); ca, sa = math.cos(a), math.sin(a)
            lean = rnd.uniform(0.0, 0.035); la = rnd.uniform(0, math.pi * 2); i = len(verts)
            verts += [(x - ca * w, y - sa * w, 0.0), (x + ca * w, y + sa * w, 0.0), (x + math.cos(la) * lean, y + math.sin(la) * lean, hgt)]
            faces.append((i, i + 1, i + 2)); v = rnd.uniform(0.75, 1.15); cols.append((0.16 * v, 0.33 * v, 0.07 * v, 1))
    me = bpy.data.meshes.new('GrassBlades'); me.from_pydata(verts, [], faces)
    ca_ = me.color_attributes.new('gcol', 'FLOAT_COLOR', 'CORNER'); flat = []
    for c in cols: flat += c * 3
    ca_.data.foreach_set('color', flat)
    o = bpy.data.objects.new('GrassBlades', me); link(o)
    gm = MB('GrassBlade'); at = gm.n('ShaderNodeAttribute'); at.attribute_name = 'gcol'
    gm.set('Base Color', at.outputs['Color']); gm.set('Roughness', 0.55)
    tr = gm.n('ShaderNodeBsdfTranslucent'); gm.ln(at.outputs['Color'], tr.inputs[0])
    mx = gm.n('ShaderNodeMixShader'); mx.inputs[0].default_value = 0.3
    gm.ln(gm.bsdf.outputs[0], mx.inputs[1]); gm.ln(tr.outputs[0], mx.inputs[2]); gm.ln(mx.outputs[0], gm.out.inputs[0])
    me.materials.append(gm.m); return o

TREES = ('tree_', 'fir_', 'jacaranda', 'island_tree')
_bounds = {}
def coll_bounds(c):
    if c.name not in _bounds:
        pts = [o.matrix_world @ Vector(b) for o in c.all_objects if o.type == 'MESH' for b in o.bound_box]
        lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        _bounds[c.name] = (lo, hi)
    return _bounds[c.name]
M_PROXY = None
def shadow_proxy(c, loc, s, seed):
    """Speed: a full Poly Haven tree is ~1M polygons and EEVEE re-renders the sun shadow map every sample, which
    cost ~3 s/frame. The real tree stays on camera; this invisible low-poly trunk + canopy casts its shadow."""
    global M_PROXY
    if M_PROXY is None: M_PROXY = flat_mat('ShadowProxy', (0.2, 0.2, 0.2), 1.0)
    lo, hi = coll_bounds(c); h = (hi.z - lo.z) * s; w = max(hi.x - lo.x, hi.y - lo.y) * s
    tr = cyl('ProxyTrunk', 0.05 * h ** .5, h * 0.55, M_PROXY, segs=8); tr.location = (loc[0], loc[1], h * 0.275)
    cn = lumpy('ProxyCanopy', 1.0, M_PROXY, seed, 1.0, 2, 0.25); cn.scale = (w * .42, w * .42, h * .3)
    cn.location = (loc[0], loc[1], lo.z * s + h * 0.68)
    for o in (tr, cn):
        o.visible_camera = False; o.visible_diffuse = False; o.visible_glossy = False
        o.visible_transmission = False; o.visible_volume_scatter = False
def scatter(models, spots):
    """spots: [(model, x, y, scale, rot)]; trees get shadow proxies (see shadow_proxy)"""
    for i, (m, x, y, s, r) in enumerate(spots):
        c = try_coll(m) if m not in ('garden_gnome', 'watering_can_metal_01') else try_coll(m, ('',))
        if not c: continue
        place_collection(c, (x, y, 0), r, s)
        if m.startswith(TREES) and '--realtreeshadows' not in args:
            for o in c.all_objects: o.visible_shadow = False
            shadow_proxy(c, (x, y), s, i + 1)

def neighbour(x, y, w, d, col, roofmat, win_mat, shutter_mat=None, floors=2):
    hgt = 3.1 * floors
    box(f'NB{x}', x, x + w, y, y + d, 0, hgt, pbr_mat(f'NBW{x}', 'painted_plaster_wall', 0.4, tint=col, tint_fac=0.6))
    for k in range(4):
        for fl in range(floors):
            wx = x + 0.9 + k * (w - 1.8) / 3.0
            box(f'NBwin{x}{k}{fl}', wx - .5, wx + .5, y - .03, y, 1.0 + fl * 3, 2.4 + fl * 3, win_mat)
            if shutter_mat:
                box(f'NBsa{x}{k}{fl}', wx - .95, wx - .55, y - .05, y, 1.0 + fl * 3, 2.4 + fl * 3, shutter_mat)
                box(f'NBsb{x}{k}{fl}', wx + .55, wx + .95, y - .05, y, 1.0 + fl * 3, 2.4 + fl * 3, shutter_mat)
    bm = bmesh.new(); ov = .4
    pts = [(x - ov, y - ov, hgt), (x + w + ov, y - ov, hgt), (x + w + ov, y + d + ov, hgt), (x - ov, y + d + ov, hgt), (x + 1, y + d / 2, hgt + 2.4), (x + w - 1, y + d / 2, hgt + 2.4)]
    v = [bm.verts.new(p) for p in pts]
    bm.faces.new((v[0], v[1], v[5], v[4])); bm.faces.new((v[2], v[3], v[4], v[5])); bm.faces.new((v[1], v[2], v[5])); bm.faces.new((v[3], v[0], v[4]))
    mesh_obj(f'NBroof{x}', bm, roofmat)

# ================================================================= PARTICLE-ISH HELPERS
def streaks(name, n, x0, x1, y0, y1, z0, z1, length, width, mat, seed=3):
    """one mesh of n thin vertical quads (rain / snow / drips); animate the object location"""
    rnd = random.Random(seed); verts, faces = [], []
    for _ in range(n):
        x, y, z = rnd.uniform(x0, x1), rnd.uniform(y0, y1), rnd.uniform(z0, z1); i = len(verts)
        verts += [(x - width, y, z), (x + width, y, z), (x + width, y, z + length), (x - width, y, z + length)]
        faces.append((i, i + 1, i + 2, i + 3))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.materials.append(mat)
    o = bpy.data.objects.new(name, me); link(o); return o

def flakes(name, n, x0, x1, y0, y1, z0, z1, r, mat, seed=4):
    rnd = random.Random(seed); bm = bmesh.new()
    for _ in range(n):
        g = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r * rnd.uniform(.6, 1.2))
        off = Vector((rnd.uniform(x0, x1), rnd.uniform(y0, y1), rnd.uniform(z0, z1)))
        bmesh.ops.translate(bm, verts=g['verts'], vec=off)
    return mesh_obj(name, bm, mat, smooth=True)

class Beads:
    """glowing beads that flow along a polyline (water / waste flow)"""
    def __init__(self, name, n, r, mat, path):
        self.path = [Vector(p) for p in path]; self.objs = []
        for i in range(n):
            bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=r)
            self.objs.append(mesh_obj(f'{name}{i}', bm, mat, True))
    def set(self, head, t, speed=.25, vis=True):
        for i, m in enumerate(self.objs):
            u = ((i / len(self.objs)) + t * speed) % 1
            v = vis and head > 0 and u <= head
            if m.hide_render == v: m.hide_render = not v
            if v: m.location = poly_at(self.path, u)

# ================================================================= CAMERA
class Camera:
    """keys: one (pos, target) per segment; glides between them like v3"""
    def __init__(self, keys, fov=46, fstop=2.8):
        d = bpy.data.cameras.new('Cam'); d.sensor_fit = 'VERTICAL'; d.sensor_height = 24.0
        d.angle_y = math.radians(fov); d.clip_start = 0.05; d.clip_end = 900
        d.dof.use_dof = True; d.dof.aperture_fstop = float(arg('--fstop', str(fstop))); d.dof.aperture_blades = 7
        if '--nodof' in args: d.dof.use_dof = False
        self.d = d; self.o = bpy.data.objects.new('Cam', d); link(self.o); scene.camera = self.o
        self.keys = [(Vector(p), Vector(q)) for p, q in keys]
        self.drift = 0.6; self.push = 1.1
        self.seg_drift = {}   # step index -> (drift, push) overrides
        self.min_dur = {}     # step index -> minimum transition time (e.g. when leaving a shot that follows a moving machine)
    def at(self, t):
        i = 0
        for k in range(len(seg)):
            if t >= seg[k][0] - .25: i = k
        ka, kb = self.keys[max(0, i - 1)], self.keys[min(i, len(self.keys) - 1)]
        tr = self.tr(i, t)
        # Each step's slow drift keeps running and is blended into the next step's over the same eased transition.
        # (It used to restart at 0 on every step change, which made the camera jump ~1 m: a visible snap.)
        pos = (ka[0] + self.drift_at(max(0, i - 1), t)).lerp(kb[0] + self.drift_at(i, t), tr)
        tgt = ka[1].lerp(kb[1], tr)
        return pos, tgt, i
    def tr(self, i, t):
        """eased blend from key i-1 to key i; long moves take longer (0.9 s .. 2.4 s) so the camera never whips"""
        if i == 0: return 1.0
        ka, kb = self.keys[max(0, i - 1)], self.keys[min(i, len(self.keys) - 1)]
        d = max((ka[0] - kb[0]).length, (ka[1] - kb[1]).length * 0.7)
        va, vb = (ka[1] - ka[0]), (kb[1] - kb[0])
        ang = math.degrees(va.angle(vb)) if va.length and vb.length else 0.0
        dur = max(min(2.4, max(0.9, 0.9 + d / 18.0)), 0.6 + ang / 45.0, self.min_dur.get(i, 0.0))   # turning is limited too
        return ease(clamp((t - (seg[i][0] - .25)) / dur))
    def drift_at(self, i, t):
        d, p = self.seg_drift.get(i, (self.drift, self.push))
        local = clamp((t - seg[i][0]) / (seg[i][1] - seg[i][0] + .4))
        return Vector((math.sin(local * 1.2) * d, local * p, 0.0))
    def apply(self, pos, tgt):
        self.o.location = pos
        self.o.rotation_euler = (tgt - pos).to_track_quat('-Z', 'Y').to_euler()
        self.d.dof.focus_distance = (tgt - pos).length

# ================================================================= RENDER DRIVER
def frame_time(f): return f / FPS
_cam = {}
def export_cam(f, extra):
    cam = scene.camera
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    Pm = cam.calc_matrix_camera(dg, x=W, y=H) @ cam.matrix_world.inverted()
    os.makedirs(CAMS_DIR, exist_ok=True)
    json.dump(dict(t=frame_time(f), P=[list(r) for r in Pm], **extra), open(os.path.join(CAMS_DIR, f'{f:05d}.json'), 'w'))

ROLLERS = []
def roller(o, radius, axle='X', surface=None, name=None):
    """register a wheel / drum / roller for the physics check: it must roll (rotation x radius = distance travelled),
    never spin in place or pivot, and (if surface z is given) sit on it. axle = its local spin axis."""
    ROLLERS.append(dict(o=o, r=radius, axle=Vector({'X': (1, 0, 0), 'Y': (0, 1, 0), 'Z': (0, 0, 1)}[axle]), surface=surface, name=name or o.name))
    return o
def _world(o):
    m = o.matrix_basis.copy(); p = o.parent
    while p: m = p.matrix_basis @ m; p = p.parent
    return m
def _roll_check(hist, R):
    issues = []
    for k in range(1, len(hist)):
        (f0, m0, v0), (f1, m1, v1) = hist[k - 1], hist[k]
        if not (v0 and v1) or f1 != f0 + 1: continue
        c0, c1 = m0.to_translation(), m1.to_translation(); ax = (m1.to_3x3() @ R['axle']).normalized()
        mv = c1 - c0; mv.z = 0.0   # rolling distance is horizontal; being lifted onto a new surface is not rolling
        along = mv - ax * mv.dot(ax); dist = along.length
        q = m0.to_quaternion().rotation_difference(m1.to_quaternion()); ang = q.angle; ang = min(ang, 2 * math.pi - ang)
        ax0 = (m0.to_3x3() @ R['axle']).normalized(); turn = math.degrees(ax0.angle(ax)) if ax0.length else 0
        t = round(frame_time(f1), 2)
        if dist > 0.004 and abs(ang * R['r'] - dist) > 0.25 * dist + 0.01:
            issues.append((t, 'wheel-slides', f"{R['name']} travelled {dist * 100:.1f} cm but turned {ang * R['r'] * 100:.1f} cm"))
        if dist < 0.002 and ang > 0.05:
            issues.append((t, 'wheel-spins-in-place', f"{R['name']} spins {math.degrees(ang):.0f} deg without moving"))
        if turn > 2.0:
            issues.append((t, 'wheel-pivots', f"{R['name']} axle swung {turn:.1f} deg in one frame"))
        if R['surface'] is not None:
            sz = R['surface'](frame_time(f1)) if callable(R['surface']) else R['surface']
            gap = c1.z - R['r'] - sz
            if abs(gap) > 0.04: issues.append((t, 'wheel-floats' if gap > 0 else 'wheel-sinks', f"{R['name']} is {gap * 100:+.0f} cm off its surface"))
    return issues

LINT_SKIP = ('Ground', 'FarLawn', 'LawnL', 'LawnR', 'GrassBlades', 'Proxy', 'Hill', 'Rain', 'Snow', 'Fallout', 'Bubbles', 'FoamStreaks')
def _is_blended(o):
    try: return any(sl.material and sl.material.surface_render_method == 'BLENDED' for sl in o.material_slots)
    except Exception: return False
def _visible_meshes():
    out = []
    for o in scene.objects:
        if o.type not in ('MESH', 'CURVE') or o.hide_render or o.name.startswith(LINT_SKIP): continue
        if any(c.hide_render for c in o.users_collection): continue
        p = o.parent; hidden = False
        while p:
            if p.hide_render: hidden = True
            p = p.parent
        if hidden: continue
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        lo = Vector((min(q.x for q in pts), min(q.y for q in pts), min(q.z for q in pts)))
        hi = Vector((max(q.x for q in pts), max(q.y for q in pts), max(q.z for q in pts)))
        out.append((o, lo, hi, _is_blended(o)))
    return out

def inset_transparent(eps=0.012):
    """Anti z-fighting: transparent objects whose front face lies on the cut plane (y=0) are moved 1.2 cm back,
    so they never share that plane with solids or the cut ground (that caused the flickering water/dam glitch)."""
    bpy.context.view_layer.update(); n = 0
    for o in scene.objects:
        if o.type not in ('MESH', 'CURVE') or not _is_blended(o): continue
        lo = min((o.matrix_world @ Vector(c)).y for c in o.bound_box)
        if abs(lo) < 0.006: o.delta_location.y += eps; n += 1
    print('inset', n, 'transparent objects off the cut plane', flush=True)

def lint(apply_state, every=10):
    """Pre-render QC: camera snaps, visibility flicker, coplanar faces on the cut plane (z-fighting),
    transparent objects cutting through solid ones. Writes <video>/qc/lint.json."""
    issues = []; vis_hist = {}; cams = []; rh = {id(R['o']): [] for R in ROLLERS}
    from bpy_extras.object_utils import world_to_camera_view
    try: labels = json.load(open(os.path.join(VDIR, 'video.json'), encoding='utf-8')).get('labels', [])
    except Exception: labels = []
    def label_on(L, t):
        s = L['s']; e_ = L.get('until', s)
        if not (seg[s][0] <= t < seg[e_][1]): return False
        a = seg[s][0] + (seg[s][1] - seg[s][0]) * (L.get('a', 0) + 0.08)
        return t >= a and (e_ != s or t <= seg[s][0] + (seg[s][1] - seg[s][0]) * L.get('b', 1))
    for f in range(NFRAMES):
        ex = apply_state(frame_time(f)) or {}
        if f % 3 == 0:
            t = frame_time(f); bpy.context.view_layer.update()
            for L in labels:
                if not label_on(L, t): continue
                at = L.get('at')
                if 'follow' in L:
                    fo = ex.get('follow', {}).get(L['follow'])
                    if fo is None: continue
                    at = [fo[i] + L.get('off', [0, 0, 0])[i] for i in range(3)]
                v = world_to_camera_view(scene, scene.camera, Vector(at))
                if v.z <= 0 or not (0.05 <= v.x <= 0.95 and 0.06 <= v.y <= 0.94):
                    issues.append(dict(t=round(t, 2), kind='label-off-screen', severity='fail', objects=[L['text']],
                                       note=f'label anchor at {at} is outside the frame ({v.x:.2f}, {v.y:.2f})'))
        c = scene.camera; cams.append((Vector(c.location), c.rotation_euler.to_quaternion()))
        for R in ROLLERS:
            o = R['o']; vis = not o.hide_render; p = o.parent
            while p:
                vis = vis and not p.hide_render; p = p.parent
            rh[id(o)].append((f, _world(o), vis))
        for o in scene.objects:
            if o.type in ('MESH', 'CURVE', 'EMPTY'): vis_hist.setdefault(o.name, []).append(not o.hide_render)
        if f % every: continue
        bpy.context.view_layer.update()
        vm = _visible_meshes(); t = round(frame_time(f), 2)
        front = [(o, lo, hi, b) for o, lo, hi, b in vm if abs(lo.y) < 0.006]
        def face_rects(o):
            # the object's real faces lying on the cut plane and facing the camera (x/z rectangles)
            if o.type != 'MESH': return None
            mw = o.matrix_world; out = []
            for poly in o.data.polygons:
                vs = [mw @ o.data.vertices[v].co for v in poly.vertices]
                if all(abs(v.y) < 0.006 for v in vs):
                    out.append((min(v.x for v in vs), max(v.x for v in vs), min(v.z for v in vs), max(v.z for v in vs)))
            return out
        rects = {f[0].name: face_rects(f[0]) for f in front}
        def rect_overlap(ra, rb):
            if ra is None or rb is None: return None
            best = (0, 0)
            for a in ra:
                for b in rb:
                    ox = min(a[1], b[1]) - max(a[0], b[0]); oz = min(a[3], b[3]) - max(a[2], b[2])
                    if ox > 0.03 and oz > 0.03 and ox * oz > best[0] * best[1]: best = (ox, oz)
            return best
        for i in range(len(front)):
            for j in range(i + 1, len(front)):
                a, b_ = front[i], front[j]
                if a[0].parent == b_[0] or b_[0].parent == a[0] or (a[0].parent and a[0].parent == b_[0].parent): continue
                ro = rect_overlap(rects[a[0].name], rects[b_[0].name])
                if ro is not None: ox, oz = ro
                else: ox = min(a[2].x, b_[2].x) - max(a[1].x, b_[1].x); oz = min(a[2].z, b_[2].z) - max(a[1].z, b_[1].z)
                if ox > 0.03 and oz > 0.03:
                    issues.append(dict(t=t, kind='coplanar-cut-face', severity='fail', objects=[a[0].name, b_[0].name],
                                       note=f'both faces sit on y=0 and overlap {ox:.2f} x {oz:.2f} m: z-fighting'))
        for o, lo, hi, bl in vm:
            if not bl: continue
            vol = max(1e-9, (hi - lo).x * (hi - lo).y * (hi - lo).z)
            for o2, lo2, hi2, bl2 in vm:
                if bl2 or o2 == o or o2.parent == o or o.parent == o2: continue
                d = [min(hi[k], hi2[k]) - max(lo[k], lo2[k]) for k in range(3)]
                if min(d) <= 0.02: continue
                v2 = max(1e-9, (hi2 - lo2).x * (hi2 - lo2).y * (hi2 - lo2).z); inter = d[0] * d[1] * d[2]
                inside = all(lo2[k] >= lo[k] - 0.01 and hi2[k] <= hi[k] + 0.01 for k in range(3))
                if inter > 0.25 * v2 and not inside and v2 > 0.05:
                    issues.append(dict(t=t, kind='transparent-cuts-solid', severity='review', objects=[o.name, o2.name],
                                       note=f'{inter / v2 * 100:.0f}% of the solid is inside the transparent object'))
    # camera snaps: one-frame jumps far above the neighbouring motion
    for f in range(1, len(cams) - 1):
        d = (cams[f][0] - cams[f - 1][0]).length; dn = (cams[f + 1][0] - cams[f][0]).length; dp = (cams[f - 1][0] - cams[f - 2][0]).length if f > 1 else dn
        ang = math.degrees(cams[f][1].rotation_difference(cams[f - 1][1]).angle)
        if (d > 0.12 and d > 4 * max(dn, dp, 0.01)) or ang > 4.0:
            issues.append(dict(t=round(frame_time(f), 2), kind='camera-snap', severity='fail', objects=['Cam'], note=f'moved {d:.2f} m / {ang:.1f} deg in one frame'))
    # visibility flicker: hidden-visible-hidden (or the reverse) within 4 frames
    for name, h in vis_hist.items():
        f = 1
        while f < len(h) - 1:
            if h[f] != h[f - 1]:
                g = f
                while g < len(h) and h[g] == h[f]: g += 1
                if g < len(h) and g - f < 4:
                    issues.append(dict(t=round(frame_time(f), 2), kind='visibility-flicker', severity='fail', objects=[name], note=f'{"shown" if h[f] else "hidden"} for only {g - f} frame(s)'))
                f = g
            else: f += 1
    for R in ROLLERS:
        for t, kind, note in _roll_check(rh[id(R['o'])], R):
            issues.append(dict(t=t, kind=kind, severity='fail', objects=[R['name']], note=note))
    # merge repeats of the same issue into time ranges
    merged = {}
    for it in issues:
        k = (it['kind'], tuple(sorted(it['objects'])))
        m = merged.setdefault(k, dict(it, t0=it['t'], t1=it['t'], count=0)); m['t1'] = it['t']; m['count'] += 1
    out = sorted(merged.values(), key=lambda m: (m['severity'] != 'fail', m['t0']))
    for m in out: m.pop('t', None)
    od = os.path.join(VDIR, 'qc'); os.makedirs(od, exist_ok=True)
    json.dump(out, open(os.path.join(od, 'lint.json'), 'w'), indent=1)
    print(f'LINT {sum(1 for m in out if m["severity"] == "fail")} fail, {sum(1 for m in out if m["severity"] == "review")} review', flush=True)

def run(apply_state):
    """apply_state(t) -> dict of extras for the overlay (e.g. {'follow': {'truck': [x,y,z]}})"""
    if arg('--post'): exec(arg('--post'))   # benchmarking hook run after the scene is built
    inset_transparent()
    if '--lint' in args: lint(apply_state); return
    def state(f):
        extra = apply_state(frame_time(f)) or {}
        export_cam(f, extra)
    if '--save' in args:
        state(int(float(arg('--t', '2')) * FPS)); bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(arg('--save')))
    if '--stills' in args:
        od = os.path.join(VDIR, 'tests'); os.makedirs(od, exist_ok=True); tag = arg('--tag', 'a')
        for s in arg('--stills').split(','):
            t0 = time.time(); f = int(round(float(s) * FPS)); scene.frame_set(f); state(f)
            scene.render.filepath = os.path.join(od, f'{tag}_{float(s):05.1f}.png'); bpy.ops.render.render(write_still=True)
            print(f'STILL {s}s took {time.time() - t0:.1f}s', flush=True)
    if '--frames' in args:
        a, b = [int(x) for x in arg('--frames').split('-')]; b = min(b, NFRAMES - 1)
        os.makedirs(FRAMES_DIR, exist_ok=True)
        # one persistent animation render: EEVEE keeps shaders, textures and static geometry on the GPU
        # between frames. State is applied before each frame; the camera matrix is exported after the
        # depsgraph has evaluated it (no separate pass, no extra scene updates).
        tick = {'t': time.time()}; extras = {}
        def pre(sc, *_):
            # motion blur evaluates sub-frames: drive the scene at the exact sub-frame time so moving parts blur
            ex = apply_state(frame_time(sc.frame_current + sc.frame_subframe)) or {}
            if abs(sc.frame_subframe) < 1e-6: extras[sc.frame_current] = ex
        def post_eval(sc, dg=None, *_):
            f = sc.frame_current; cam = sc.camera; dg = dg or bpy.context.evaluated_depsgraph_get()
            Pm = cam.calc_matrix_camera(dg, x=W, y=H) @ cam.evaluated_get(dg).matrix_world.inverted()
            os.makedirs(CAMS_DIR, exist_ok=True)
            json.dump(dict(t=frame_time(f), P=[list(r) for r in Pm], **extras.pop(f, {})), open(os.path.join(CAMS_DIR, f'{f:05d}.json'), 'w'))
        def post(sc, *_):
            now = time.time(); print(f'FRAME {sc.frame_current} {now - tick["t"]:.2f}s', flush=True); tick['t'] = now
        bpy.app.handlers.frame_change_post.append(post_eval)
        bpy.app.handlers.frame_change_pre.append(pre)
        bpy.app.handlers.render_post.append(post)
        scene.frame_start, scene.frame_end = a, b
        scene.render.filepath = os.path.join(FRAMES_DIR, '#####')
        t_all = time.time(); bpy.ops.render.render(animation=True)
        print(f'DONE {a}-{b} in {time.time() - t_all:.0f}s', flush=True)
