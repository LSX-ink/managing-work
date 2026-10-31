# Detailed railway machines: early steam locomotive (Rocket style), coal wagon, modern high-speed train.
# All roll along +y; wheels turn by distance / radius and are registered for the lint physics check.
import math
from ll import *
from machines import ring, spoked_wheel, roll

def rod(name, thick, mat):
    return box(name, -thick / 2, thick / 2, -thick / 2, thick / 2, -0.5, 0.5, mat)

def rod_between(o, a, b):
    """stretch a unit rod (from rod()) between points a and b (in its parent's space)"""
    a, b = Vector(a), Vector(b); d = b - a
    o.location = (a + b) / 2; o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); o.scale = (1, 1, max(.001, d.length))

def loft(name, prof, stations, mat):
    """loft a closed (x, z) profile along y; stations = [(y, scale_x, scale_z, raise_z)]"""
    bm = bmesh.new(); rings = []
    for y, sx, sz, dz in stations:
        rings.append([bm.verts.new((x * sx, y, z * sz + dz)) for x, z in prof])
    n = len(prof)
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n; bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_obj(name, bm, mat, smooth=True)

def rocket_locomotive(name='Rocket', gauge=0.72, surface=0.0):
    """early steam locomotive in the style of Stephenson's Rocket (1829): yellow barrel boiler with black hoops, tall
    black chimney, copper firebox, inclined cylinders whose piston rods drive crank pins on big spoked driving wheels,
    small trailing wheels, tender with a water barrel. Returns (root, wheels, update(dist))."""
    YEL = flat_mat(f'{name}Yellow', (0.85, 0.62, 0.08), 0.35, metal=0.2, coat=0.6); BLK = flat_mat(f'{name}Black', (0.03, 0.03, 0.03), 0.4, metal=0.5, coat=0.3)
    COP = flat_mat(f'{name}Copper', (0.72, 0.38, 0.2), 0.3, metal=1.0); IRON = flat_mat(f'{name}Iron', (0.25, 0.25, 0.26), 0.35, metal=0.9)
    WOOD = pbr_mat(f'{name}Wood', 'weathered_planks', 1.2, hsv=(0.5, 0.9, 0.75))
    root = empty(name)
    def p(o): o.parent = root; return o
    DR, DY, TR, TY, PIN = 0.72, 1.2, 0.4, -0.4, 0.32
    p(box(f'{name}Frame', -0.62, 0.62, -0.9, 2.0, 0.42, 0.55, WOOD, bevel=0.02))
    boiler = p(cyl(f'{name}Boiler', 0.48, 2.1, YEL, 40, axis='Y')); boiler.location = (0, 0.75, 1.15)
    for y in (0.0, 0.75, 1.5): p(cyl(f'{name}Hoop{y}', 0.49, 0.04, BLK, 40, axis='Y')).location = (0, y, 1.15)
    p(cyl(f'{name}Front', 0.5, 0.08, BLK, 40, axis='Y')).location = (0, 1.82, 1.15)
    ch = p(cyl(f'{name}Chimney', 0.15, 2.2, BLK, 24)); ch.location = (0, 1.7, 2.65)
    crown = p(cyl(f'{name}Crown', 0.22, 0.12, BLK, 24, r2=0.16)); crown.location = (0, 1.7, 3.78)
    p(box(f'{name}Firebox', -0.52, 0.52, -0.75, -0.25, 0.55, 1.75, COP, bevel=0.06))
    p(box(f'{name}Footplate', -0.65, 0.65, -0.95, -0.7, 0.5, 0.56, WOOD))
    wheels, cranks, rods = [], [], []
    for s in (-1, 1):
        w = spoked_wheel(f'{name}Driver{s}', DR, 0.1, YEL, YEL, n=12, hub=0.1); w.parent = root; w.location = (s * gauge, DY, DR)
        fl = ring(f'{name}DFlange{s}', DR + 0.04, DR * 0.92, 0.03, IRON); fl.location = (-s * 0.05, 0, 0); fl.parent = w
        pin = cyl(f'{name}Pin{s}', 0.04, 0.12, IRON, 12, axis='X'); pin.location = (s * 0.08, 0, PIN); pin.parent = w
        wheels.append((w, DR)); cranks.append(s)
        t = spoked_wheel(f'{name}Trail{s}', TR, 0.08, YEL, YEL, n=10, hub=0.07); t.parent = root; t.location = (s * gauge, TY, TR)
        tf = ring(f'{name}TFlange{s}', TR + 0.035, TR * 0.9, 0.03, IRON); tf.location = (-s * 0.045, 0, 0); tf.parent = t
        wheels.append((t, TR))
        cylr = p(cyl(f'{name}Cyl{s}', 0.13, 0.75, BLK, 24)); cylr.location = (s * (gauge + 0.16), -0.15, 1.15); cylr.rotation_euler.x = -0.62
        rods.append(p(rod(f'{name}Rod{s}', 0.05, IRON)))
    p(cyl(f'{name}DAxle', 0.06, gauge * 2 + 0.3, IRON, 12, axis='X')).location = (0, DY, DR)
    p(box(f'{name}TendFrame', -0.62, 0.62, -3.5, -1.2, 0.45, 0.6, WOOD, bevel=0.02))
    barrel = p(cyl(f'{name}Barrel', 0.45, 1.6, WOOD, 32, axis='Y')); barrel.location = (0, -2.35, 1.1)
    for y in (-2.9, -2.35, -1.8): p(cyl(f'{name}BHoop{y}', 0.46, 0.04, BLK, 32, axis='Y')).location = (0, y, 1.1)
    for s in (-1, 1):
        for y in (-3.0, -1.7):
            tw = spoked_wheel(f'{name}TW{s}{y}', 0.42, 0.08, YEL, YEL, n=10, hub=0.07); tw.parent = root; tw.location = (s * gauge, y, 0.42)
            wheels.append((tw, 0.42))
    for w, r in wheels: roller(w, r, 'X', surface)
    def update(dist):
        roll(wheels, dist)
        a = -dist / DR   # driver angle about X
        for s, rd in zip(cranks, rods):   # piston rod: cylinder mouth -> crank pin on the turning wheel
            px = s * (gauge + 0.12)
            pin = (px, DY - PIN * math.sin(a), DR + PIN * math.cos(a))
            rod_between(rd, (px, 0.18, 0.88), pin)
    update(0.0)
    return root, wheels, update

def coal_wagon(name='CoalWagon', gauge=0.72, surface=0.0, wood_wheels=True):
    """early chaldron-style coal wagon: tapered plank body heaped with coal, spoked wheels with inner flanges"""
    WOOD = pbr_mat(f'{name}Wood', 'weathered_planks', 0.9, hsv=(0.5, 1.0, 0.62)); IRON = flat_mat(f'{name}Iron', (0.2, 0.2, 0.21), 0.4, metal=0.9)
    COAL = flat_mat(f'{name}Coal', (0.02, 0.02, 0.02), 0.95)
    root = empty(name)
    def p(o): o.parent = root; return o
    body = p(loft(f'{name}Body', [(-0.62, 0), (0.62, 0), (0.62, 0.85), (-0.62, 0.85)], [(-1.0, 0.85, 1, 0.55), (1.0, 0.85, 1, 0.55)], WOOD))
    p(loft(f'{name}Flare', [(-0.62, 0), (0.62, 0), (0.85, 0.45), (-0.85, 0.45)], [(-1.15, 1, 1, 1.4), (1.15, 1, 1, 1.4)], WOOD))
    for y in (-0.9, 0.0, 0.9): p(box(f'{name}Strap{y}', -0.64, 0.64, y - 0.04, y + 0.04, 0.55, 1.85, IRON))
    coal = p(lumpy(f'{name}Coal', 1.0, COAL, 3, 0.35, 3, 0.35)); coal.scale = (0.8, 1.1, 0.5); coal.location = (0, 0, 1.85)
    wheels = []
    for y in (-0.65, 0.65):
        for s in (-1, 1):
            w = spoked_wheel(f'{name}W{y}{s}', 0.34, 0.08, WOOD if wood_wheels else IRON, IRON, n=8, hub=0.06); w.parent = root; w.location = (s * gauge, y, 0.34)
            fl = ring(f'{name}F{y}{s}', 0.39, 0.3, 0.025, IRON); fl.location = (-s * 0.05, 0, 0); fl.parent = w
            wheels.append((w, 0.34)); roller(w, 0.34, 'X', surface)
    p(cyl(f'{name}Axle1', 0.04, gauge * 2 + 0.2, IRON, 10, axis='X')).location = (0, -0.65, 0.34)
    p(cyl(f'{name}Axle2', 0.04, gauge * 2 + 0.2, IRON, 10, axis='X')).location = (0, 0.65, 0.34)
    return root, wheels

def hs_train(name='HSTrain', cars=3, gauge=0.72, surface=0.0):
    """modern high-speed electric train: lofted rounded body, long tapered nose, window band, livery stripe, skirts,
    bogies with rolling wheels, diamond pantograph. Nose at +y. Returns (root, wheels)."""
    WHITE = flat_mat(f'{name}White', (0.93, 0.94, 0.95), 0.18, metal=0.3, coat=1.0); RED = flat_mat(f'{name}Red', (0.75, 0.05, 0.04), 0.25, metal=0.2, coat=1.0)
    WIN = flat_mat(f'{name}Win', (0.03, 0.05, 0.07), 0.04, coat=1.0); GREY = flat_mat(f'{name}Grey', (0.25, 0.26, 0.28), 0.4, metal=0.7)
    STEEL = flat_mat(f'{name}Steel', (0.6, 0.6, 0.62), 0.25, metal=1.0)
    prof = [(1.45 * math.cos(a), 1.55 + 1.35 * math.sin(a) * (0.85 if math.sin(a) > 0 else 0.55)) for a in [2 * math.pi * i / 40 for i in range(40)]]
    root = empty(name); wheels = []
    def p(o): o.parent = root; return o
    CL = 13.0
    for c in range(cars):
        y1 = -c * (CL + 0.4); y0 = y1 - CL
        st = [(y0, 1, 1, 0), (y1 - 5.0, 1, 1, 0), (y1 - 2.8, 0.95, 0.86, -0.08), (y1 - 1.2, 0.72, 0.6, -0.32), (y1 - 0.3, 0.38, 0.32, -0.62), (y1, 0.08, 0.08, -0.85)] if c == 0 else [(y0, 1, 1, 0), (y1, 1, 1, 0)]
        p(loft(f'{name}Body{c}', prof, st, WHITE))
        p(box(f'{name}Band{c}', -1.47, 1.47, y0 + 0.6, y1 - (5.5 if c == 0 else 0.6), 2.15, 2.75, WIN))
        if c == 0:   # cab windscreen follows the nose surface
            p(loft(f'{name}Screen', [(-0.9, 0), (0.9, 0), (0.75, 0.35), (-0.75, 0.35)], [(y1 - 4.9, 1.02, 1, 2.4), (y1 - 3.0, 0.96, 1, 2.22)], WIN))
        p(box(f'{name}Stripe{c}', -1.47, 1.47, y0 + 0.2, y1 - (4.0 if c == 0 else 0.2), 1.25, 1.45, RED))
        p(box(f'{name}Skirt{c}', -1.3, 1.3, y0 + 0.3, y1 - (2.0 if c == 0 else 0.3), 0.55, 0.85, GREY))
        for by in (y0 + 2.2, y1 - (4.0 if c == 0 else 2.2)):
            p(box(f'{name}Bogie{c}{by:.1f}', -1.0, 1.0, by - 1.3, by + 1.3, 0.35, 0.62, GREY))
            for dy in (-0.85, 0.85):
                for s in (-1, 1):
                    w = empty(f'{name}W{c}{by:.1f}{dy}{s}', (s * gauge, by + dy, 0.46)); w.parent = root
                    t_ = cyl(f'{name}Wh{c}{by:.1f}{dy}{s}', 0.46, 0.12, STEEL, 32, axis='X'); t_.parent = w
                    mk = pivot_at(box(f'{name}Mk{c}{by:.1f}{dy}{s}', -0.065, 0.065, -0.03, 0.03, 0.1, 0.4, GREY)); mk.parent = w
                    wheels.append((w, 0.46)); roller(w, 0.46, 'X', surface)
    py = -6.0
    p(box(f'{name}PBase', -0.5, 0.5, py - 0.4, py + 0.4, 3.0, 3.1, GREY))
    for k, (a, b) in enumerate((((0, py - 0.35, 3.1), (0, py + 0.35, 3.9)), ((0, py + 0.35, 3.9), (0, py - 0.2, 4.75)),
                                ((0, py + 0.35, 3.1), (0, py - 0.35, 3.9)), ((0, py - 0.35, 3.9), (0, py + 0.2, 4.75)))):
        r_ = p(rod(f'{name}PArm{k}', 0.045, STEEL)); rod_between(r_, a, b)
    p(box(f'{name}PHead', -0.8, 0.8, py - 0.05, py + 0.05, 4.73, 4.8, STEEL))
    return root, wheels
