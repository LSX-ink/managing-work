# More detailed machines: centrifugal pump set, diesel generator set.
import math
from ll import *
from machines import ring

def pump_set(name='Pump', scale=1.0, paint=(0.08, 0.3, 0.6)):
    """end-suction centrifugal pump driven by an electric motor on a base frame (as in waterworks / pump stations).
    Origin at the base, pump outlet pointing up at about (0.55, 0, 1.0) * scale. Returns (root, impeller)."""
    PAINT = flat_mat(f'{name}Paint', paint, 0.35, metal=0.4, coat=0.3); MOTOR = flat_mat(f'{name}Motor', (0.2, 0.32, 0.22), 0.4, metal=0.5)
    STEEL = flat_mat(f'{name}Steel', (0.55, 0.56, 0.58), 0.3, metal=0.9); DARK = flat_mat(f'{name}Dark', (0.08, 0.08, 0.09), 0.5, metal=0.5)
    root = empty(name)
    def p(o): o.parent = root; return o
    p(box(f'{name}Base', -0.4, 1.6, -0.35, 0.35, 0.0, 0.12, DARK, bevel=0.02))
    vol = p(cyl(f'{name}Volute', 0.42, 0.32, PAINT, 48, axis='X')); vol.location = (0.55, 0, 0.62)
    p(cyl(f'{name}Inlet', 0.16, 0.45, PAINT, 32, axis='X')).location = (0.15, 0, 0.62)
    p(ring(f'{name}InFlange', 0.24, 0.12, 0.05, STEEL)).location = (-0.07, 0, 0.62)
    out = p(cyl(f'{name}Outlet', 0.13, 0.5, PAINT, 32)); out.location = (0.55, 0, 1.15)
    p(cyl(f'{name}OutFlange', 0.21, 0.05, STEEL, 32)).location = (0.55, 0, 1.4)
    p(box(f'{name}Ped', 0.35, 0.75, -0.2, 0.2, 0.12, 0.3, PAINT))
    p(cyl(f'{name}Guard', 0.13, 0.35, STEEL, 24, axis='X')).location = (0.93, 0, 0.62)
    mot = p(cyl(f'{name}MotorBody', 0.3, 0.75, MOTOR, 48, axis='X')); mot.location = (1.35, 0, 0.62)
    for k in range(10):
        f = pivot_at(box(f'{name}Fin{k}', 1.02, 1.68, -0.012, 0.012, 0.3, 0.36, MOTOR), (0, 0, 0.62)); f.rotation_euler.x = 2 * math.pi * k / 10; f.parent = root
    p(box(f'{name}TermBox', 1.25, 1.45, -0.12, 0.12, 0.9, 1.05, MOTOR, bevel=0.02))
    p(box(f'{name}MotorFeet', 1.1, 1.6, -0.3, 0.3, 0.12, 0.34, MOTOR))
    imp = empty(f'{name}Impeller', (0.55, 0, 0.62)); imp.parent = root
    root.scale = (scale,) * 3
    return root, imp

def generator_set(name='Genset', scale=1.0):
    """diesel generator set: engine block with rocker covers, radiator with grille, alternator, exhaust silencer, skid"""
    YEL = pbr_mat(f'{name}Yellow', 'metal_plate', 0.6, tint=(0.95, 0.62, 0.02), tint_fac=0.85, metal=0.25)
    DARK = flat_mat(f'{name}Dark', (0.07, 0.07, 0.08), 0.5, metal=0.5); STEEL = flat_mat(f'{name}Steel', (0.55, 0.56, 0.58), 0.3, metal=0.9)
    root = empty(name)
    def p(o): o.parent = root; return o
    p(box(f'{name}Skid', -0.15, 2.0, -0.45, 0.45, 0.0, 0.12, DARK))
    p(box(f'{name}Engine', 0.6, 1.5, -0.35, 0.35, 0.12, 0.85, YEL, bevel=0.04))
    p(box(f'{name}Rocker', 0.65, 1.45, -0.2, 0.2, 0.85, 1.0, DARK, bevel=0.03))
    p(box(f'{name}Radiator', 1.5, 1.75, -0.42, 0.42, 0.12, 1.05, YEL, bevel=0.02))
    for k in range(8): p(box(f'{name}Grille{k}', 1.75, 1.77, -0.36, 0.36, 0.2 + k * 0.1, 0.24 + k * 0.1, DARK))
    alt = p(cyl(f'{name}Alternator', 0.32, 0.6, YEL, 40, axis='X')); alt.location = (0.25, 0, 0.5)
    p(box(f'{name}Panel', -0.12, 0.2, -0.3, 0.3, 0.12, 0.9, DARK, bevel=0.02))
    sil = p(cyl(f'{name}Silencer', 0.12, 0.6, STEEL, 24, axis='X')); sil.location = (1.0, 0, 1.15)
    root.scale = (scale,) * 3
    return root

def vacuum_truck(name='VacTruck', surface=0.0):
    """septic vacuum tanker truck: cab with windscreen/side glass, chassis rails, cylindrical tank with domed ends,
    hose reel, dual rear wheels, mudguards, lights. Faces +y. Returns (root, wheels, hose_anchor)."""
    from machines import spoked_wheel
    WHITE = flat_mat(f'{name}Cab', (0.88, 0.89, 0.9), 0.25, metal=0.3, coat=0.8); TANK = flat_mat(f'{name}Tank', (0.62, 0.64, 0.66), 0.25, metal=0.85)
    DARK = flat_mat(f'{name}Dark', (0.05, 0.05, 0.055), 0.5, metal=0.4); GLASS = flat_mat(f'{name}Glass', (0.04, 0.06, 0.08), 0.03, coat=1.0)
    TYRE = flat_mat(f'{name}Tyre', (0.03, 0.03, 0.03), 0.85); RIM = flat_mat(f'{name}Rim', (0.7, 0.7, 0.72), 0.25, metal=1.0)
    HOSE = flat_mat(f'{name}Hose', (0.05, 0.05, 0.05), 0.6); LIGHT = flat_mat(f'{name}Light', (1, 0.95, 0.8), 0.1, emit=(1, 0.95, 0.8), emit_str=2)
    root = empty(name)
    def p(o): o.parent = root; return o
    for x in (-0.45, 0.45): p(box(f'{name}Rail{x}', x - 0.06, x + 0.06, -3.6, 2.6, 0.55, 0.8, DARK))
    p(box(f'{name}CabLow', -1.15, 1.15, 1.35, 2.75, 0.75, 1.75, WHITE, bevel=0.08))
    p(box(f'{name}CabTop', -1.1, 1.1, 1.45, 2.45, 1.75, 2.75, WHITE, bevel=0.1))
    p(box(f'{name}Screen', -0.95, 0.95, 2.44, 2.47, 1.85, 2.6, GLASS))
    for x in (-1.11, 1.11): p(box(f'{name}Side{x}', x - 0.015, x + 0.015, 1.65, 2.3, 1.85, 2.55, GLASS))
    p(box(f'{name}Grille', -0.8, 0.8, 2.74, 2.78, 0.85, 1.55, DARK))
    for x in (-0.85, 0.85): p(box(f'{name}Head{x}', x - 0.15, x + 0.15, 2.76, 2.8, 1.0, 1.15, LIGHT))
    p(box(f'{name}Bumper', -1.2, 1.2, 2.72, 2.95, 0.6, 0.8, DARK))
    tank = p(cyl(f'{name}TankBody', 0.95, 4.2, TANK, 48, axis='Y')); tank.location = (0, -1.35, 1.85)
    for y, s in ((0.75, 1), (-3.45, -1)):
        d = p(lumpy(f'{name}Dome{s}', 0.95, TANK, 3, 1.0, 3, 0.0)); d.scale = (1, 0.28, 1); d.location = (0, y, 1.85)
    for y in (-2.6, -1.35, -0.1): p(ring_y := cyl(f'{name}Band{y}', 0.97, 0.06, DARK, 48, axis='Y')).location = (0, y, 1.85)
    reel = p(cyl(f'{name}Reel', 0.45, 0.5, DARK, 32, axis='X')); reel.location = (0, -3.75, 1.2)
    p(cyl(f'{name}Valve', 0.12, 0.4, DARK, 16, axis='Y')).location = (0.6, -3.65, 1.0)
    wheels = []
    for y, dual in ((2.0, False), (-2.1, True), (-3.1, True)):
        for s in (-1, 1):
            w = empty(f'{name}W{y}{s}', (s * (1.05 if not dual else 1.0), y, 0.52)); w.parent = root
            for k, dx in enumerate((0.0, -s * 0.32) if dual else (0.0,)):
                ty = cyl(f'{name}Ty{y}{s}{k}', 0.52, 0.3, TYRE, 40, axis='X'); ty.location = (dx, 0, 0); ty.parent = w
                rm = cyl(f'{name}Rm{y}{s}{k}', 0.3, 0.31, RIM, 10, axis='X'); rm.location = (dx, 0, 0); rm.parent = w
            wheels.append((w, 0.52)); roller(w, 0.52, 'X', surface)
        p(box(f'{name}Guard{y}', -1.3, 1.3, y - 0.65, y + 0.65, 1.05, 1.12, DARK))
    anchor = empty(f'{name}HoseAnchor', (0.6, -3.65, 1.0)); anchor.parent = root
    return root, wheels, anchor
