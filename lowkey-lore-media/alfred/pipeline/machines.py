# Detailed, era-correct machines for lowkey.lore scenes (no bare primitives standing in for real machines).
# Every machine is built around an empty that faces +y (forward) at z=0 (ground contact). Rolling parts are returned
# so the scene can drive them with roll(), which turns them by exactly distance / radius, and they are registered
# with ll.roller() for the physics check in lint.
import math
from ll import *

def _m(name, color, rough=0.5, metal=0.0, coat=0.0):
    return flat_mat(name, color, rough, metal=metal, coat=coat)

def ring(name, r_out, r_in, width, mat, segs=48):
    """hollow ring (thick rim / tyre) spinning about local X: outer + inner surfaces and annulus side faces"""
    bm = bmesh.new(); loops = []
    for rr in (r_out, r_in):
        for x in (-width / 2, width / 2):
            loops.append([bm.verts.new((x, rr * math.cos(2 * math.pi * i / segs), rr * math.sin(2 * math.pi * i / segs))) for i in range(segs)])
    oa, ob, ia, ib = loops
    for i in range(segs):
        j = (i + 1) % segs
        bm.faces.new((oa[i], oa[j], ob[j], ob[i])); bm.faces.new((ia[j], ia[i], ib[i], ib[j]))
        bm.faces.new((oa[j], oa[i], ia[i], ia[j])); bm.faces.new((ob[i], ob[j], ib[j], ib[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_obj(name, bm, mat, smooth=True)

def spoked_wheel(name, r, width, mat_rim, mat_spoke, n=12, hub=0.12, tyre=None, axle='X'):
    """open wheel spinning about local X: thick rim ring, spokes you can see between, hub (+ optional rubber tyre)"""
    w = empty(name)
    rim = ring(f'{name}Rim', r, r * 0.88, width, mat_rim); rim.parent = w
    if tyre is not None:
        ty = ring(f'{name}Tyre', r * 1.06, r * 0.99, width * 1.04, tyre); ty.parent = w
    for k in range(n):
        a = 2 * math.pi * k / n
        sp = pivot_at(box(f'{name}Sp{k}', -width * 0.15, width * 0.15, -0.028, 0.028, hub * 0.8, r * 0.9, mat_spoke)); sp.rotation_euler.x = a; sp.parent = w
    hb = cyl(f'{name}Hub', hub, width * 1.3, mat_spoke, 24, axis='X'); hb.parent = w
    return w

def roll(wheels, dist):
    """turn wheels (spinning about local X, moving along +y) for a travelled distance"""
    for w, r in wheels: w.rotation_euler.x = -dist / r

def steam_roller(name='SteamRoller', surface=0.0):
    """Aveling & Porter style steam road roller (1870s-1930s): split front roll in a fork headstock, horizontal boiler,
    smokebox + chimney, cylinder block and flywheel, big spoked rear driving wheels, cab canopy."""
    GREEN = _m(f'{name}Green', (0.05, 0.22, 0.1), 0.35, 0.3, 0.6); BLACK = _m(f'{name}Black', (0.03, 0.03, 0.03), 0.4, 0.6, 0.3)
    RED = _m(f'{name}Red', (0.55, 0.06, 0.04), 0.35, 0.3, 0.5); IRON = _m(f'{name}Iron', (0.22, 0.22, 0.23), 0.35, 0.9)
    BRASS = _m(f'{name}Brass', (0.85, 0.65, 0.2), 0.25, 1.0); ROOF = _m(f'{name}Roof', (0.06, 0.07, 0.07), 0.5, 0.5)
    root = empty(name)
    def p(o): o.parent = root; return o
    # front split roll in the fork
    FR, FZ, FY = 0.72, 0.72, 2.25
    front = empty(f'{name}FrontRoll', (0, FY, FZ)); front.parent = root
    for x in (-0.36, 0.36):
        d = cyl(f'{name}Roll{x}', FR, 0.62, IRON, 56, axis='X'); d.location = (x, 0, 0); d.parent = front
        for s in (-1, 1):
            ring = cyl(f'{name}RollEdge{x}{s}', FR + 0.02, 0.04, BLACK, 56, axis='X'); ring.location = (x + s * 0.29, 0, 0); ring.parent = front
    p(cyl(f'{name}FrontAxle', 0.07, 1.6, IRON, 16, axis='X')).location = (0, FY, FZ)
    for x in (-0.8, 0.8):
        p(box(f'{name}Fork{x}', x - 0.05, x + 0.05, FY - 0.45, FY + 0.45, FZ - 0.1, FZ + 0.85, GREEN, bevel=0.02))
    p(box(f'{name}ForkTop', -0.85, 0.85, FY - 0.25, FY + 0.25, FZ + 0.75, FZ + 0.92, GREEN, bevel=0.02))
    hs = p(cyl(f'{name}Headstock', 0.16, 0.9, GREEN, 24)); hs.location = (0, FY, FZ + 1.3)
    # boiler, smokebox, chimney
    boiler = p(cyl(f'{name}Boiler', 0.52, 2.5, GREEN, 40, axis='Y')); boiler.location = (0, 1.0, 1.75)
    for y in (0.1, 0.9, 1.7):
        p(cyl(f'{name}Band{y}', 0.535, 0.05, BRASS, 40, axis='Y')).location = (0, y, 1.75)
    sb = p(cyl(f'{name}Smokebox', 0.56, 0.55, BLACK, 40, axis='Y')); sb.location = (0, 2.45, 1.75)
    door = p(cyl(f'{name}SmokeDoor', 0.5, 0.06, BLACK, 40, axis='Y')); door.location = (0, 2.74, 1.75)
    chim = p(cyl(f'{name}Chimney', 0.13, 1.25, BLACK, 24, r2=0.17)); chim.location = (0, 2.4, 2.85)
    p(cyl(f'{name}ChimCap', 0.2, 0.08, BRASS, 24)).location = (0, 2.4, 3.5)
    # cylinder block, flywheel, governor
    p(box(f'{name}CylBlock', -0.32, 0.32, 1.6, 2.35, 2.2, 2.55, GREEN, bevel=0.03))
    fw = spoked_wheel(f'{name}Flywheel', 0.5, 0.1, BLACK, BLACK, n=6, hub=0.08); fw.parent = root; fw.location = (0.72, 1.25, 2.05)
    p(cyl(f'{name}Crank', 0.05, 1.5, IRON, 12, axis='X')).location = (0, 1.25, 2.05)
    # firebox, tender, rear wheels
    p(box(f'{name}Firebox', -0.6, 0.6, -0.75, 0.0, 0.75, 2.2, GREEN, bevel=0.03))
    p(box(f'{name}Tender', -0.9, 0.9, -1.55, -0.65, 0.6, 1.55, GREEN, bevel=0.03))
    p(box(f'{name}Coal', -0.75, 0.75, -1.5, -0.8, 1.55, 1.7, _m(f'{name}CoalM', (0.02, 0.02, 0.02), 0.95)))
    RR, RY = 0.88, -0.45
    rear = []
    for x in (-1.08, 1.08):
        w = spoked_wheel(f'{name}Rear{x}', RR, 0.42, RED, RED, n=14, hub=0.15); w.parent = root; w.location = (x, RY, RR)
        for k in range(14):   # cast cleats across the tread
            a = 2 * math.pi * k / 14
            c = pivot_at(box(f'{name}Cleat{x}{k}', -0.2, 0.2, -0.03, 0.03, RR - 0.02, RR + 0.03, IRON)); c.rotation_euler.x = a; c.parent = w
        rear.append(w)
    p(cyl(f'{name}RearAxle', 0.08, 2.2, IRON, 16, axis='X')).location = (0, RY, RR)
    # canopy
    for (x, y) in ((-0.8, -1.5), (0.8, -1.5), (-0.8, 1.1), (0.8, 1.1)):
        p(cyl(f'{name}Post{x}{y}', 0.035, 1.6, IRON, 10)).location = (x, y, 2.95)
    p(box(f'{name}Canopy', -1.0, 1.0, -1.75, 1.35, 3.72, 3.8, ROOF, bevel=0.02))
    p(box(f'{name}Plate', -0.35, 0.35, 2.78, 2.8, 1.2, 1.5, BRASS))
    for w, r in ((front, FR), (rear[0], RR), (rear[1], RR)): roller(w, r, 'X', surface)
    return root, [(front, FR), (rear[0], RR), (rear[1], RR)], fw

def vibratory_roller(name='VibRoller', surface=0.0):
    """modern single-drum vibratory soil compactor: smooth steel drum in a yoke frame, articulated rear chassis with
    engine, cab with roll-over frame, big rubber rear tyres"""
    YEL = pbr_mat(f'{name}Yellow', 'metal_plate', 0.6, tint=(0.95, 0.62, 0.02), tint_fac=0.85, metal=0.25)
    DRUM = _m(f'{name}Drum', (0.32, 0.32, 0.34), 0.3, 0.9); DARK = _m(f'{name}Dark', (0.05, 0.05, 0.055), 0.5, 0.4)
    TYRE = _m(f'{name}Tyre', (0.03, 0.03, 0.03), 0.85); GLASS = _m(f'{name}Glass', (0.06, 0.09, 0.11), 0.05, coat=1.0)
    root = empty(name)
    def p(o): o.parent = root; return o
    DR, DY = 0.78, 1.75
    drum = empty(f'{name}DrumRoll', (0, DY, DR)); drum.parent = root
    d = cyl(f'{name}DrumShell', DR, 2.13, DRUM, 64, axis='X'); d.parent = drum
    for s in (-1, 1):
        cap = cyl(f'{name}DrumCap{s}', DR * 0.6, 0.04, DARK, 32, axis='X'); cap.location = (s * 1.08, 0, 0); cap.parent = drum
    for s in (-1, 1):
        p(box(f'{name}Yoke{s}', s * 1.12 - 0.07, s * 1.12 + 0.07, DY - 0.55, DY + 0.55, 0.35, 1.75, YEL, bevel=0.03))
    p(box(f'{name}YokeTop', -1.2, 1.2, DY - 0.35, DY + 0.75, 1.62, 1.85, YEL, bevel=0.04))
    p(box(f'{name}Scraper', -1.05, 1.05, DY + 0.78, DY + 0.84, 0.25, 0.9, DARK))
    p(box(f'{name}Hitch', -0.35, 0.35, 0.55, 1.2, 0.85, 1.25, DARK, bevel=0.03))
    p(box(f'{name}Chassis', -1.0, 1.0, -2.1, 0.6, 0.65, 1.55, YEL, bevel=0.06))
    p(box(f'{name}Engine', -0.95, 0.95, -2.35, -0.6, 1.55, 2.15, YEL, bevel=0.08))
    for k in range(6): p(box(f'{name}Grille{k}', -0.8, 0.8, -2.36, -2.35, 1.65 + k * 0.08, 1.69 + k * 0.08, DARK))
    ex = p(cyl(f'{name}Exhaust', 0.06, 0.7, DARK, 12)); ex.location = (-0.6, -1.0, 2.45)
    p(box(f'{name}CabFloor', -0.85, 0.85, -0.6, 0.6, 1.55, 1.65, DARK))
    for (x, y) in ((-0.8, -0.55), (0.8, -0.55), (-0.8, 0.55), (0.8, 0.55)):
        p(box(f'{name}ROPS{x}{y}', x - 0.05, x + 0.05, y - 0.05, y + 0.05, 1.65, 3.25, YEL))
    p(box(f'{name}Roof', -0.95, 0.95, -0.7, 0.7, 3.2, 3.32, YEL, bevel=0.03))
    for (x0, x1, y0, y1) in ((-0.78, 0.78, 0.52, 0.55), (-0.78, 0.78, -0.55, -0.52), (-0.8, -0.77, -0.5, 0.5), (0.77, 0.8, -0.5, 0.5)):
        p(box(f'{name}Glass{x0}{y0}', x0, x1, y0, y1, 1.9, 3.15, GLASS))
    p(box(f'{name}Seat', -0.3, 0.3, -0.35, 0.15, 1.65, 2.2, DARK, bevel=0.04))
    TR, TY = 0.78, -1.35
    rear = []
    for x in (-0.82, 0.82):
        w = empty(f'{name}Wheel{x}', (x, TY, TR)); w.parent = root
        t = cyl(f'{name}Tyre{x}', TR, 0.62, TYRE, 48, axis='X'); t.parent = w
        for k in range(16):   # tractor tread lugs
            a = 2 * math.pi * k / 16
            lug = pivot_at(box(f'{name}Lug{x}{k}', -0.3, 0.3, -0.05, 0.05, TR - 0.02, TR + 0.05, TYRE)); lug.rotation_euler.x = a; lug.parent = w
        rim = cyl(f'{name}Rim{x}', TR * 0.55, 0.64, YEL, 32, axis='X'); rim.parent = w
        rear.append(w)
    for w, r in ((drum, DR), (rear[0], TR), (rear[1], TR)): roller(w, r, 'X', surface)
    return root, [(drum, DR), (rear[0], TR), (rear[1], TR)]

def car(name, paint, kind='sedan', surface=0.0):
    """modern car: shaped body (bevelled lower body + tapered glasshouse), wheel arches, tyres with alloy rims,
    head/tail lights. Faces +y. Returns (root, wheels)."""
    BODY = flat_mat(f'{name}Paint', paint, 0.18, metal=0.6, coat=1.0)
    GLASS = flat_mat(f'{name}Glass', (0.04, 0.06, 0.08), 0.03, coat=1.0)
    TYRE = flat_mat(f'{name}Tyre', (0.03, 0.03, 0.03), 0.85); RIM = flat_mat(f'{name}Rim', (0.75, 0.76, 0.78), 0.2, metal=1.0)
    HEAD = flat_mat(f'{name}Head', (1, 1, 0.95), 0.1, emit=(1, 0.97, 0.9), emit_str=3); TAIL = flat_mat(f'{name}Tail', (0.6, 0.02, 0.02), 0.2, emit=(1, 0.05, 0.03), emit_str=2)
    L, Wd = (2.35, 0.92) if kind == 'sedan' else (2.5, 0.98)
    root = empty(name)
    def p(o): o.parent = root; return o
    p(box(f'{name}Lower', -Wd, Wd, -L, L, 0.28, 0.85, BODY, bevel=0.14, segs=4))
    bm = bmesh.new()   # glasshouse: tapered prism, raked windscreen and rear window
    t, b = 0.68, 0.9
    pts = [(-Wd * 0.92, -L * 0.62, 0.85), (Wd * 0.92, -L * 0.62, 0.85), (Wd * 0.92, L * 0.38, 0.85), (-Wd * 0.92, L * 0.38, 0.85),
           (-Wd * 0.78, -L * 0.42, 1.38), (Wd * 0.78, -L * 0.42, 1.38), (Wd * 0.78, L * 0.08, 1.38), (-Wd * 0.78, L * 0.08, 1.38)]
    v = [bm.verts.new(q) for q in pts]
    for f in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)): bm.faces.new([v[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    p(mesh_obj(f'{name}Cabin', bm, GLASS))
    p(box(f'{name}Roof', -Wd * 0.8, Wd * 0.8, -L * 0.44, L * 0.1, 1.36, 1.42, BODY, bevel=0.03))
    for x in (-Wd * 0.62, Wd * 0.62):
        p(box(f'{name}HL{x}', x - 0.2, x + 0.2, L - 0.04, L + 0.01, 0.62, 0.72, HEAD))
        p(box(f'{name}TL{x}', x - 0.22, x + 0.22, -L - 0.01, -L + 0.04, 0.66, 0.76, TAIL))
    wheels = []
    for (x, y) in ((-Wd + 0.08, L * 0.62), (Wd - 0.08, L * 0.62), (-Wd + 0.08, -L * 0.62), (Wd - 0.08, -L * 0.62)):
        w = empty(f'{name}W{x}{y}', (x, y, 0.33)); w.parent = root
        ty = cyl(f'{name}Ty{x}{y}', 0.33, 0.24, TYRE, 32, axis='X'); ty.parent = w
        rm = cyl(f'{name}Rm{x}{y}', 0.21, 0.25, RIM, 10, axis='X'); rm.parent = w
        wheels.append((w, 0.33)); roller(w, 0.33, 'X', surface)
    return root, wheels
