# lowkey.lore quality bot. A video must PASS before it is pushed, sent, or handed over.
#   python qc.py ..\videos\NN-slug                 -> automated checks + dense 4 fps contact sheets + qc\report.md
#   python qc.py ..\videos\NN-slug --approve "..." -> records the visual / real-life review sign-off for THIS exact file
# make.py runs: lint (Blender, before render) -> render -> encode -> pause -> qc; push refuses unless qc\result.json
# says pass AND qc\approval.json matches the current file hash.
#
# Automated checks
#   scene lint (qc\lint.json, from ll.lint): camera snaps, visibility flicker, coplanar faces on the cut plane
#     (z-fighting), transparent objects cutting through solids, wheels/rollers that slide, spin in place or float
#   picture: black frames, frozen stretches, one-frame flicker / pops, hard cuts that are not planned
#   audio: -14 LUFS (+-1), true peak <= -1 dBTP, no silence gaps (except the planned pause hold), narrator >= 8 dB
#     above the sound effects
#   script: opens with "Did you know", ends with "Follow for more insight", pause present with a ~3 s hold + thank you
#   overlay: label anchors on screen, label pills not overlapping each other or the centre caption
#   delivery: 70-90 s (+ pause), 1080x1920 @ 30 fps, phone copy < 30 MB
# Visual review (me, from the 4 fps sheets) uses the real-life checklist in REVIEW_CHECKLIST.
import hashlib, json, os, re, subprocess, sys
import numpy as np, soundfile as sf
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import overlay, audio, pause
W, H, FPS, SR = overlay.W, overlay.H, overlay.FPS, 48000
REVIEW_CHECKLIST = [
    'Every object looks like the real thing from that era (no bare primitives standing in for machines)',
    'Every motion is physically real: wheels/rollers roll forward with matching rotation, nothing floats, slides, pivots or spins in place',
    'No clipping: nothing passes through walls, water, ground or other objects',
    'No pops: things appear/disappear with a build or fade, never blink in or out',
    'Camera moves smoothly, no snaps; every shot frames what the narrator is talking about',
    'Labels point at the right thing and are readable; captions readable',
]

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()[:16]

def frames_gray(path, w=135, h=240):
    ff = overlay.ffmpeg()
    p = subprocess.run([ff, '-v', 'error', '-i', path, '-vf', f'scale={w}:{h},format=gray', '-f', 'rawvideo', '-'], capture_output=True, check=True)
    a = np.frombuffer(p.stdout, np.uint8); return a.reshape(-1, h, w).astype(np.float32)

def video_checks(V, pz):
    F = frames_gray(V.mp4); n = len(F); out = []
    pa, pb = (pz['at'], pz['at'] + pz['length']) if pz else (-1, -1)
    planned_cuts = [pa, pb]
    def near(t, ts, tol): return any(abs(t - x) < tol for x in ts)
    mean = F.reshape(n, -1).mean(1)
    for i in np.where(mean < 6)[0]: out.append(('fail', f'black frame at {i / FPS:.2f}s'))
    d = np.abs(np.diff(F, axis=0)).reshape(n - 1, -1).mean(1)
    run = 0
    for i, x in enumerate(d):
        t = (i + 1) / FPS
        run = run + 1 if x < 0.15 and not (pa - 0.1 <= t <= pb + 0.1) else 0
        if run == 20: out.append(('fail', f'frozen picture from {(i - 19) / FPS:.2f}s'))
    # one-frame flicker: frame t differs from both neighbours while the neighbours agree (blockwise)
    B = 15; bh, bw = H // 8 // B, W // 8 // B
    blk = F[:, :bh * B, :bw * B].reshape(n, bh, B, bw, B).mean((2, 4))
    for i in range(1, n - 1):
        t = i / FPS
        if near(t, planned_cuts, 0.1): continue
        a_, b_, c_ = blk[i - 1], blk[i], blk[i + 1]
        spike = np.minimum(np.abs(b_ - a_), np.abs(c_ - b_)) - np.abs(c_ - a_)
        if spike.max() > 18: out.append(('fail', f'flicker / pop at {t:.2f}s (block jump {spike.max():.0f})'))
    # hard cuts (whole-frame change) that are not planned
    for i, x in enumerate(d):
        t = (i + 1) / FPS
        if x > 28 and not near(t, planned_cuts, 0.1): out.append(('fail', f'unplanned hard cut at {t:.2f}s (mean change {x:.0f})'))
    return out, n

def audio_checks(V, pz):
    out = []; ff = overlay.ffmpeg(); tmp = os.path.join(V.dir, 'qc', '_a.wav')
    subprocess.run([ff, '-y', '-v', 'error', '-i', V.mp4, '-vn', '-ac', '2', '-ar', str(SR), tmp], check=True)
    a, _ = sf.read(tmp); os.remove(tmp); st = a.T
    L = audio.lufs(st); tp = audio.true_peak(st)
    if abs(L + 14) > 1.0: out.append(('fail', f'loudness {L:.1f} LUFS (target -14)'))
    if tp > -0.9: out.append(('fail', f'true peak {tp:.1f} dBTP (max -1)'))
    if np.max(np.abs(st)) >= 0.999: out.append(('fail', 'clipping'))
    env = np.sqrt(np.convolve(st[0] ** 2, np.ones(int(.05 * SR)) / int(.05 * SR), 'same'))
    quiet = env < 10 ** (-50 / 20); run = 0
    hold = [(pz['at'] + s1, pz['at'] + s2) for s1, s2 in pz.get('gaps', [])] if pz else []
    total = len(env) / SR
    for i in range(0, len(env), int(.05 * SR)):
        t = i / SR
        allowed = any(g0 - .2 <= t <= g1 + .2 for g0, g1 in hold) or t > total - 2.6
        run = run + 1 if quiet[i] and not allowed else 0
        if run == 26: out.append(('fail', f'silence gap > 1.3 s at {t - 1.3:.1f}s'))
    try:
        v, _ = sf.read(os.path.join(V.dir, 'audio', 'stem-voice.wav')); fx, _ = sf.read(os.path.join(V.dir, 'audio', 'stem-sfx.wav'))
        fx = fx[:, 0] if fx.ndim > 1 else fx
        def p95(x):
            e = np.sqrt(np.convolve(x ** 2, np.ones(int(.1 * SR)) / int(.1 * SR), 'same')); return np.percentile(e[e > 1e-5], 95)
        gap = 20 * np.log10(p95(audio.compress(v) / np.max(np.abs(audio.compress(v)))) / max(p95(fx * 1.0), 1e-9))
        if gap < 8: out.append(('fail', f'narrator only {gap:.1f} dB above sound effects (need 8)'))
    except Exception as e: out.append(('warn', f'stems missing for narrator/SFX check: {e}'))
    return out, L, tp

def script_checks(V, pz):
    out = []; s = V.script
    if not s[0].lower().startswith('did you know'): out.append(('fail', 'does not open with "Did you know"'))
    if s[-1].strip().lower() != 'follow for more insight.': out.append(('fail', 'does not end with "Follow for more insight."'))
    if not s[-2].lower().startswith("and that's how"): out.append(('fail', 'missing "And that\'s how X becomes Y."'))
    if not pz: out.append(('fail', 'mid-video follow pause missing'))
    else:
        sp = pz.get('spans', [])
        if len(sp) < 3: out.append(('fail', 'pause needs line + banter + thank you'))
        else:
            hold = sp[2][0] - sp[1][1]
            if not (2.8 <= hold <= 3.4): out.append(('fail', f'pause hold is {hold:.1f}s (need 3 s)'))
            if 'thank' not in sp[2][2].lower(): out.append(('fail', 'pause does not end with a thank you'))
        if not (0.35 <= pz['at'] / pause.duration(V.mp4) <= 0.65): out.append(('fail', 'pause is not near the middle'))
    return out

def overlay_checks(V):
    out = []; seen = set()
    from PIL import ImageDraw
    d = ImageDraw.Draw(Image.new('RGB', (8, 8)))
    for f in range(0, len(os.listdir(V.CAMS)), 3):
        t = f / FPS; cp = os.path.join(V.CAMS, f'{f:05d}.json')
        if not os.path.exists(cp): continue
        cam = overlay.Cam(cp); rects = []
        for L in V.cfg.get('labels', []):
            s = L['s']; e_ = L.get('until', s)
            if not (V.seg[s][0] <= t < V.seg[e_][1]): continue
            if V.P(s, t, L.get('a', 0), L.get('a', 0) + .08) < 1 or (e_ == s and V.P(s, t) > L.get('b', 1)): continue
            at = L.get('at')
            if 'follow' in L:
                fo = cam.d.get('follow', {}).get(L['follow'])
                if fo is None: continue
                at = [fo[i] + L.get('off', [0, 0, 0])[i] for i in range(3)]
            p = cam.proj(at)
            if not p or not (0 <= p[0] <= W and 0 <= p[1] <= H):
                k = ('anchor', L['text'])
                if k not in seen: out.append(('fail', f'label "{L["text"]}" points off-screen at {t:.1f}s')); seen.add(k)
                continue
            w = d.textlength(L['text'], font=overlay.font(38)) + 44; h = 62
            tx = min(max(p[0] + L.get('dx', 90), w / 2 + 28), W - w / 2 - 28); ty = min(max(p[1] + L.get('dy', -160), h / 2 + 90), H - h / 2 - 90)
            r = (tx - w / 2, ty - h / 2, tx + w / 2, ty + h / 2); rects.append((L['text'], r))
            if abs(ty - H * .5) < 95:
                k = ('cap', L['text'])
                if k not in seen: out.append(('warn', f'label "{L["text"]}" sits on the caption line at {t:.1f}s')); seen.add(k)
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                (a, ra), (b, rb) = rects[i], rects[j]
                if min(ra[2], rb[2]) - max(ra[0], rb[0]) > 4 and min(ra[3], rb[3]) - max(ra[1], rb[1]) > 4:
                    k = ('ovl', a, b)
                    if k not in seen: out.append(('fail', f'labels "{a}" and "{b}" overlap at {t:.1f}s')); seen.add(k)
    return out

def sheets(V, fps=4, per=60, cols=12):
    ff = overlay.ffmpeg(); od = os.path.join(V.dir, 'qc', 'frames'); os.makedirs(od, exist_ok=True)
    for f_ in os.listdir(od): os.remove(os.path.join(od, f_))
    subprocess.run([ff, '-v', 'error', '-i', V.mp4, '-vf', f'fps={fps},scale=180:320', os.path.join(od, 'f_%04d.jpg')], check=True)
    fs = sorted(os.listdir(od)); paths = []
    for s0 in range(0, len(fs), per):
        chunk = fs[s0:s0 + per]; rows = (len(chunk) + cols - 1) // cols
        S = Image.new('RGB', (cols * 180, rows * 320))
        for i, f_ in enumerate(chunk): S.paste(Image.open(os.path.join(od, f_)), ((i % cols) * 180, (i // cols) * 320))
        p = os.path.join(V.dir, 'qc', f'sheet_{s0 // per + 1:02d}_{s0 / fps:05.1f}s.jpg'); S.save(p, quality=82); paths.append(p)
    return paths

def run(vdir):
    V = overlay.Video(vdir); qd = os.path.join(vdir, 'qc'); os.makedirs(qd, exist_ok=True)
    pzp = os.path.join(vdir, 'pause.json'); pz = json.load(open(pzp)) if os.path.exists(pzp) else None
    if pz and pz.get('spans'):
        sp = pz['spans']; pz['gaps'] = [(sp[i][1], sp[i + 1][0]) for i in range(len(sp) - 1)] + [(0, sp[0][0]), (sp[-1][1], pz['length'])]
    res = []
    lp = os.path.join(qd, 'lint.json')
    if os.path.exists(lp):
        for m in json.load(open(lp)):
            res.append((m['severity'] if m['severity'] == 'fail' else 'review', f"[scene] {m['kind']} {m['t0']}-{m['t1']}s {m['objects']}: {m['note']}"))
    else: res.append(('fail', 'scene lint was not run'))
    v, n = video_checks(V, pz); res += v
    a, L, tp = audio_checks(V, pz); res += a
    res += script_checks(V, pz); res += overlay_checks(V)
    dur = pause.duration(V.mp4); base = dur - (pz['length'] if pz else 0)
    if not (70 <= base <= 90.5): res.append(('fail', f'length without pause {base:.1f}s (need 70-90)'))
    if os.path.exists(V.phone) and os.path.getsize(V.phone) >= 30e6: res.append(('fail', 'phone copy is 30 MB or more'))
    sh = sheets(V)
    fails = [m for s, m in res if s == 'fail']
    ok = not fails
    result = dict(file=os.path.basename(V.mp4), sha=sha(V.mp4), passed_automatic=ok, fails=fails,
                  warnings=[m for s, m in res if s == 'warn'], review=[m for s, m in res if s == 'review'],
                  loudness=round(L, 1), true_peak=round(tp, 1), duration=round(dur, 1), sheets=[os.path.basename(p) for p in sh])
    json.dump(result, open(os.path.join(qd, 'result.json'), 'w'), indent=1)
    rep = [f"# QC report: {V.name}", '', f"file {result['file']}  sha {result['sha']}  {dur:.1f}s  {L:.1f} LUFS  {tp:.1f} dBTP", '',
           f"## Automatic: {'PASS' if ok else 'FAIL'}"] + [f'- FAIL {m}' for m in fails] + [f'- warn {m}' for m in result['warnings']] + \
          ['', '## Needs review'] + [f'- {m}' for m in result['review'][:40]] + ['', '## Visual / real-life checklist (sign off with --approve)'] + [f'- [ ] {c}' for c in REVIEW_CHECKLIST]
    open(os.path.join(qd, 'report.md'), 'w', encoding='utf-8').write('\n'.join(rep) + '\n')
    print(f"QC {'PASS' if ok else 'FAIL'} {V.name}: {len(fails)} fails, {len(result['warnings'])} warnings, {len(result['review'])} to review")
    for m in fails[:25]: print('  FAIL', m)
    return ok

def approve(vdir, notes):
    V = overlay.Video(vdir); r = json.load(open(os.path.join(vdir, 'qc', 'result.json')))
    assert r['passed_automatic'], 'automatic QC has not passed'
    assert r['sha'] == sha(V.mp4), 'the video changed since QC ran: run qc again'
    json.dump(dict(sha=r['sha'], notes=notes, checklist=REVIEW_CHECKLIST), open(os.path.join(vdir, 'qc', 'approval.json'), 'w'), indent=1)
    print('approved', V.name, r['sha'])

def gate(vdir):
    """True only when automatic QC passed and the visual review approved this exact file."""
    V = overlay.Video(vdir); qd = os.path.join(vdir, 'qc')
    try:
        r = json.load(open(os.path.join(qd, 'result.json'))); a = json.load(open(os.path.join(qd, 'approval.json')))
    except FileNotFoundError: return False
    h = sha(V.mp4)
    return r['passed_automatic'] and r['sha'] == h and a['sha'] == h

if __name__ == '__main__':
    vd = os.path.abspath(sys.argv[1])
    if '--approve' in sys.argv: approve(vd, sys.argv[sys.argv.index('--approve') + 1])
    else: sys.exit(0 if run(vd) else 1)
