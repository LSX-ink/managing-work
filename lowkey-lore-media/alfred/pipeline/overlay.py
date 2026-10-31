# Overlay + encode for a pipeline video: captions (one word at a time, key words yellow), label pills,
# arrows, title pill, step flashes. Same look as hole-to-well v3. Everything is read from the video folder:
#   script.json, timeline.json, video.json (title, keywords, labels, arrows), cams\NNNNN.json, frames\NNNNN.png
#   python overlay.py ..\videos\01-log-cabin --still 300,900
#   python overlay.py ..\videos\01-log-cabin --encode --phone --sheet
# video.json:
#   "title": ["HOW A PILE OF LOGS", "BECOMES A LOG CABIN"], "keywords": [...],
#   "labels": [{"s":1,"a":.2,"b":1,"text":"LEAN-TO","at":[x,y,z] | "follow":"name","dx":90,"dy":-160,"col":"#ffcf3a"}],
#   "arrows": [{"s":2,"a":.3,"b":1,"at":[x,y,z],"d":[dx,dy,dz],"scale":.8,"col":"#ffffff"}]   (Blender coordinates)
import json, math, os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
FONT = os.path.join(ROOT, 'blender', 'nunito900.ttf')
W, H, FPS = 1080, 1920, 30
GAP = 0.2

def clamp(x, a=0.0, b=1.0): return min(b, max(a, x))
def eo(x): return 1 - pow(1 - x, 3)
def lerp(a, b, x): return a + (b - a) * x
_fonts = {}
def font(sz):
    sz = max(8, int(round(sz)))
    if sz not in _fonts: _fonts[sz] = ImageFont.truetype(FONT, sz)
    return _fonts[sz]
def hexrgb(h): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

class Video:
    def __init__(self, vdir):
        self.dir = vdir; self.slug = os.path.basename(vdir.rstrip('\\/'))
        TL = json.load(open(os.path.join(vdir, 'timeline.json')))
        self.seg = [(s['start'], s['end']) for s in TL['segments']]; self.total = TL['total']
        self.script = json.load(open(os.path.join(vdir, 'script.json'), encoding='utf-8'))
        self.cfg = json.load(open(os.path.join(vdir, 'video.json'), encoding='utf-8'))
        self.FR = os.path.join(vdir, 'frames'); self.CAMS = os.path.join(vdir, 'cams')
        self.key = {k.lower() for k in self.cfg.get('keywords', [])}
        self.name = self.cfg.get('file', 'lowkey-lore-' + self.slug.split('-', 1)[1])
        od = os.path.join(vdir, 'out'); os.makedirs(od, exist_ok=True)
        self.mp4 = os.path.join(od, self.name + '.mp4'); self.phone = os.path.join(od, self.name + '-phone.mp4')
        self.sheet = os.path.join(od, self.name + '-contact-sheet.jpg')
        self.words = []
        for i, txt in enumerate(self.script):
            ws = [w for w in txt.split() if w]
            wt = [len(re.sub(r"[^\w']", '', w)) + 2.2 + (3 if re.search(r'[,.?]$', w) else 0) for w in ws]
            tot = sum(wt); acc = self.seg[i][0]; dd = self.seg[i][1] - self.seg[i][0]
            for j, w in enumerate(ws):
                dur = dd * wt[j] / tot
                self.words.append(dict(w=re.sub(r"[^\w'’-]", '', w), s=acc, e=acc + dur)); acc += dur
    def P(self, i, t, a=0.0, b=1.0):
        s, e = self.seg[i]; x = (t - s) / (e - s); return clamp((x - a) / (b - a))
    def inSeg(self, i, t): return self.seg[i][0] - GAP <= t < self.seg[i][1] + GAP

class Cam:
    def __init__(self, path):
        self.d = json.load(open(path)); self.P = self.d['P']
    def proj(self, p):
        x, y, z = p; M = self.P
        v = [M[i][0] * x + M[i][1] * y + M[i][2] * z + M[i][3] for i in range(4)]
        if v[3] <= 1e-6: return None
        return ((v[0] / v[3] + 1) / 2 * W, (1 - v[1] / v[3]) / 2 * H)

def draw_label(V, d, L, t, cam):
    s = L['s']; e_ = L.get('until', s)
    if not (V.seg[s][0] <= t < V.seg[e_][1] + .15): return
    k = V.P(s, t, L.get('a', 0), L.get('a', 0) + .08)
    if k <= 0 or (e_ == s and V.P(s, t) > L.get('b', 1)): return
    at = L.get('at')
    if 'follow' in L:
        f = cam.d.get('follow', {}).get(L['follow'])
        if f is None: return
        off = L.get('off', [0, 0, 0]); at = [f[i] + off[i] for i in range(3)]
    p = cam.proj(at)
    if not p: return
    x, y = p; e = eo(k); tx, ty = x + L.get('dx', 90), y + L.get('dy', -160)
    a = int(255 * e); col = hexrgb(L.get('col', '#ffcf3a'))
    _f = font(38); _w = d.textlength(L['text'], font=_f) + 44
    tx = min(max(tx, _w / 2 + 28), W - _w / 2 - 28); ty = min(max(ty, 31 + 90), H - 31 - 90)
    d.line([(x, y), (lerp(x, tx, e), lerp(y, ty, e))], fill=(255, 255, 255, a), width=4)
    d.ellipse([x - 10, y - 10, x + 10, y + 10], fill=(255, 255, 255, a))
    d.ellipse([x - 5.5, y - 5.5, x + 5.5, y + 5.5], fill=col + (a,))
    sc = .7 + .3 * e; f = font(38 * sc)
    tw = d.textlength(L['text'], font=f); w = tw + 44 * sc; h = 62 * sc
    tx = min(max(tx, w / 2 + 28), W - w / 2 - 28); ty = min(max(ty, h / 2 + 90), H - h / 2 - 90)
    bx, by = tx - w / 2, ty - h / 2
    d.rounded_rectangle([bx, by, bx + w, by + h], radius=18 * sc, fill=(12, 16, 24, int(210 * e)))
    d.rounded_rectangle([bx, by, bx + 12 * sc, by + h], radius=6 * sc, fill=col + (a,))
    d.text((tx + 6 * sc, ty + 1), L['text'], font=f, fill=(255, 255, 255, a), anchor='mm')

def draw_arrow(V, d, A, t, cam):
    s = A['s']; e_ = A.get('until', s)
    if not (V.seg[s][0] - GAP <= t < V.seg[e_][1] + GAP): return
    if t < V.seg[s][0] + (V.seg[s][1] - V.seg[s][0]) * A.get('a', 0): return
    if e_ == s and V.P(s, t) > A.get('b', 1) + .02: return
    u = (t * A.get('speed', 1.1) + A.get('phase', 0)) % 1
    p = tuple(A['at'][i] + A['d'][i] * u for i in range(3))
    q = tuple(p[i] + A['d'][i] * 0.05 for i in range(3))
    sp, sq = cam.proj(p), cam.proj(q)
    if not sp or not sq: return
    ang = math.atan2(sq[1] - sp[1], sq[0] - sp[0])
    L = 78 * A.get('scale', .8); a = int(255 * math.sin(u * math.pi))
    shape = [(L * .5, 0), (L * .1, -L * .35), (L * .1, -L * .13), (-L * .5, -L * .13), (-L * .5, L * .13), (L * .1, L * .13), (L * .1, L * .35)]
    ca, sa = math.cos(ang), math.sin(ang)
    pts = [(sp[0] + x * ca - y * sa, sp[1] + x * sa + y * ca) for x, y in shape]
    d.polygon([(x + 3, y + 4) for x, y in pts], fill=(0, 0, 0, a // 3))
    d.polygon(pts, fill=hexrgb(A.get('col', '#ffffff')) + (a,), outline=(20, 20, 20, a // 2))

def draw_caption(V, img, t):
    cur = next((w for w in V.words if w['s'] <= t < w['e'] + .06), None)
    if not cur or not cur['w']: return
    k = clamp((t - cur['s']) / .09); sc = .82 + .18 * eo(k) + .05 * math.sin(k * 3.14)
    txt = cur['w'][0].upper() + cur['w'][1:]
    key = cur['w'].lower().strip("'’") in V.key
    f = font(100 * sc)
    while d_len(txt, f) > W - 120 and f.size > 40: f = font(f.size - 6)
    cx, cy = W / 2, H * .5
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
    sd.text((cx, cy + 7), txt, font=f, fill=(0, 0, 0, 120), anchor='mm', stroke_width=int(16 * sc), stroke_fill=(0, 0, 0, 120))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(9)))
    d = ImageDraw.Draw(img)
    d.text((cx, cy), txt, font=f, fill=(255, 210, 58, 255) if key else (255, 255, 255, 255), anchor='mm',
           stroke_width=int(13 * sc), stroke_fill=(16, 16, 16, 255))
_dl = ImageDraw.Draw(Image.new('RGBA', (8, 8)))
def d_len(txt, f): return _dl.textlength(txt, font=f)

def draw_title(V, img, t):
    lines = V.cfg['title']
    def big(a, b, sub):
        if t < a or t > b: return
        k = eo(clamp((t - a) / .35)) * clamp((b - t) / .3)
        if k <= 0: return
        layer = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
        sc = .8 + .2 * k; fs = 74
        while max(d.textlength(l, font=font(fs)) for l in lines) > 900 and fs > 40: fs -= 2
        f = font(fs * sc); lh = fs * 1.12 * sc
        w = max(d.textlength(l, font=f) for l in lines) + 80 * sc; h = lh * len(lines) + 44 * sc
        cx, cy = W / 2, 250
        d.rounded_rectangle([cx - w / 2 + 4, cy - h / 2 + 8, cx + w / 2 + 4, cy + h / 2 + 8], radius=30 * sc, fill=(0, 0, 0, 70))
        d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], radius=30 * sc, fill=(255, 210, 58, 255))
        for i, l in enumerate(lines):
            d.text((cx, cy - lh * (len(lines) - 1) / 2 + i * lh + 3), l, font=f, fill=(20, 22, 26, 255), anchor='mm')
        if sub:
            d.text((cx, cy + h / 2 + 50 * sc), sub, font=font(42 * sc), fill=(255, 255, 255, 255), anchor='mm', stroke_width=int(9 * sc), stroke_fill=(17, 17, 17, 255))
        if k < 1: layer.putalpha(layer.getchannel('A').point(lambda v: int(v * k)))
        img.alpha_composite(layer)
    big(0.0, V.seg[0][1], V.cfg.get('subtitle', 'how it actually works'))
    big(V.seg[-2][0], V.total + 2, 'Follow for more insight')   # last step + spoken outro

_GRADE = None
def grade(img):
    """light colour grade: +6% saturation, gentle S-curve, soft vignette"""
    global _GRADE
    from PIL import ImageEnhance
    if _GRADE is None:
        import numpy as _np
        yy, xx = _np.mgrid[0:H, 0:W]; r = _np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        v = 1 - 0.22 * _np.clip(r - 0.55, 0, 1) ** 1.6
        _GRADE = Image.fromarray((v * 255).astype('uint8'), 'L').convert('RGB')
        _GRADE.lut = [min(255, max(0, int(255 * (i / 255 + 0.08 * math.sin(2 * math.pi * i / 255) * 0.5)))) for i in range(256)] * 3
    rgb = ImageEnhance.Color(img.convert('RGB')).enhance(1.06).point(_GRADE.lut)
    from PIL import ImageChops
    return ImageChops.multiply(rgb, _GRADE).convert('RGBA')

def warm(img, k):
    """golden-hour grade (matches the warm drone footage): lift reds, trim blues"""
    if k <= 0: return img
    r, g, b, *a = img.split()
    r = r.point(lambda v: min(255, int(v * (1 + 0.07 * k) + 4 * k))); b = b.point(lambda v: int(v * (1 - 0.12 * k)))
    g = g.point(lambda v: min(255, int(v * (1 + 0.02 * k))))
    return Image.merge(img.mode, (r, g, b, *a))

def intro_frame(V, f):
    """optional live-action / AI drone intro (video.json "intro": {"frames": dir, "until": s, "fade": s})"""
    it = V.cfg.get('intro')
    if not it: return None, 0.0
    t = f / FPS; until, fade = it['until'], it.get('fade', 0.8)
    if t >= until: return None, 0.0
    fs = sorted(os.listdir(os.path.join(V.dir, it['frames'])))
    im = Image.open(os.path.join(V.dir, it['frames'], fs[min(len(fs) - 1, int(t * FPS))])).convert('RGBA').resize((W, H), Image.LANCZOS)
    a = 1.0 if t < until - fade else (until - t) / fade
    return im, eo(clamp(a))

def draw_gauge(V, d, t, cam):
    """optional depth gauge (video.json "gauge": {s0, s1, key, max, feet}) on the left edge"""
    g = V.cfg.get('gauge')
    if not g or not (V.seg[g['s0']][0] <= t < V.seg[g['s1']][1]): return
    a = clamp((t - V.seg[g['s0']][0]) / .4) * (clamp((V.seg[g['s1']][1] - t) / .4) if t > V.seg[g['s1']][1] - .4 else 1)
    A = lambda v: int(v * a)
    x, y0, h = 70, 330, 900
    d.rounded_rectangle([x - 30, y0 - 80, x + 120, y0 + h + 60], radius=24, fill=(12, 16, 24, A(190)))
    d.text((x + 45, y0 - 42), 'DEPTH', font=font(30), fill=(255, 255, 255, A(255)), anchor='mm')
    d.line([(x, y0), (x, y0 + h)], fill=(255, 255, 255, A(255)), width=4)
    for i in range(7):
        yy = y0 + h * i / 6
        d.line([(x, yy), (x + 18, yy)], fill=(255, 255, 255, A(255)), width=4)
        d.text((x + 26, yy), f"{i * g['feet'] // 6} ft", font=font(24), fill=(255, 255, 255, A(255)), anchor='lm')
    fr = clamp(cam.d.get(g['key'], 0.0) / g['max'])
    d.rectangle([x - 6, y0, x + 6, y0 + h * fr], fill=(255, 207, 58, A(255)))
    yy = y0 + h * fr
    d.polygon([(x - 8, yy), (x - 30, yy - 16), (x - 30, yy + 16)], fill=(255, 207, 58, A(255)))
    d.text((x + 45, y0 + h + 30), f"{round(fr * g['feet'])} FT", font=font(34), fill=(255, 207, 58, A(255)), anchor='mm')

def compose(V, f):
    t = f / FPS
    base = warm(grade(Image.open(os.path.join(V.FR, f'{f:05d}.png'))), V.cfg.get('warm', 0.0))
    intro, ia = intro_frame(V, f)
    if intro is not None:
        base = Image.blend(base, intro, ia) if ia < 1 else intro
    cam = Cam(os.path.join(V.CAMS, f'{f:05d}.json'))
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    if intro is None:   # no labels/arrows over live-action footage
        for A in V.cfg.get('arrows', []): draw_arrow(V, d, A, t, cam)
        for L in V.cfg.get('labels', []): draw_label(V, d, L, t, cam)
        draw_gauge(V, d, t, cam)
    base.alpha_composite(ov)
    draw_title(V, base, t)
    draw_caption(V, base, t)
    for s in V.seg[1:-1]:   # no flash on the outro line
        dt = t - s[0]
        if 0 <= dt < .12:
            base.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(255 * .18 * (1 - dt / .12)))))
    return base.convert('RGB')

def ffmpeg():
    import imageio_ffmpeg; return imageio_ffmpeg.get_ffmpeg_exe()

def nframes(V): return len([n for n in os.listdir(V.FR) if n.endswith('.png')])

def encode(V):
    ff = ffmpeg(); n = nframes(V)
    cmd = [ff, '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
           '-i', os.path.join(V.dir, 'audio', 'mix.wav'), '-map', '0:v', '-map', '1:a', '-shortest',
           '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
           '-c:a', 'aac', '-b:a', '256k', V.mp4]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    for f in range(n):
        p.stdin.write(compose(V, f).tobytes())
        if f % 300 == 0: print('encoded', f, '/', n, flush=True)
    p.stdin.close(); p.wait(); print('wrote', V.mp4, os.path.getsize(V.mp4))

def remux(mp4, wav):
    """swap in a new audio mix without re-encoding the picture"""
    ff = ffmpeg(); tmp = mp4 + '.tmp.mp4'
    subprocess.run([ff, '-y', '-i', mp4, '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                    '-shortest', '-movflags', '+faststart', tmp], check=True, stderr=subprocess.DEVNULL)
    os.replace(tmp, mp4); print('remuxed', mp4)

def phone(src, dst, total, limit_mb=28.5):
    """two-pass x264 sized to land under 30 MB"""
    ff = ffmpeg(); kbps = int(limit_mb * 8 * 1024 / total - 128)
    log = dst + '.pass'
    base = [ff, '-y', '-i', src, '-c:v', 'libx264', '-preset', 'slow', '-b:v', f'{kbps}k', '-maxrate', f'{int(kbps * 1.6)}k',
            '-bufsize', f'{kbps * 3}k', '-pix_fmt', 'yuv420p', '-passlogfile', log]
    subprocess.run(base + ['-pass', '1', '-an', '-f', 'mp4', os.devnull], check=True, stderr=subprocess.DEVNULL)
    subprocess.run(base + ['-pass', '2', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', dst], check=True, stderr=subprocess.DEVNULL)
    for fn in os.listdir(os.path.dirname(dst)):
        if fn.startswith(os.path.basename(log)): os.remove(os.path.join(os.path.dirname(dst), fn))
    mb = os.path.getsize(dst) / 2 ** 20; print(f'phone copy {mb:.1f} MB'); assert mb < 30
    return mb

def sheet(src, dst, total, step=3.5):
    ff = ffmpeg(); tiles = []; t = 0.0; tmp = dst + '.png'
    while t < total:
        subprocess.run([ff, '-y', '-loglevel', 'error', '-ss', f'{t:.2f}', '-i', src, '-frames:v', '1', tmp], check=True)
        tiles.append(Image.open(tmp).convert('RGB').resize((270, 480))); t += step
    os.remove(tmp)
    cols = 8; rows = (len(tiles) + cols - 1) // cols
    S = Image.new('RGB', (cols * 270, rows * 480))
    for i, im in enumerate(tiles): S.paste(im, ((i % cols) * 270, (i // cols) * 480))
    S.save(dst, quality=88); print('sheet', len(tiles), dst)

if __name__ == '__main__':
    V = Video(os.path.abspath(sys.argv[1])); a = sys.argv[2:]
    if '--still' in a:
        od = os.path.join(V.dir, 'tests'); os.makedirs(od, exist_ok=True)
        for s in a[a.index('--still') + 1].split(','):
            compose(V, int(s)).save(os.path.join(od, f'ov_{int(s):05d}.png'))
    if '--encode' in a: encode(V)
    if '--remux' in a: remux(V.mp4, os.path.join(V.dir, 'audio', 'mix.wav'))
    if '--phone' in a: phone(V.mp4, V.phone, V.total)
    if '--sheet' in a: sheet(V.mp4, V.sheet, V.total)
