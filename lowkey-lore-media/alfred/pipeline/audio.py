# Music bed + sound effects + final mix, all synthesised here (no downloads, no licences).
#   python audio.py ..\videos\01-log-cabin
# Bed: slow minor progression on a warm string pad, a low cello drone, sparse felt-piano notes and a soft
# low pulse, through a long hall reverb. Quiet, serious documentary feel. Ducked under the voice.
# SFX: a soft air whoosh on every step change plus the cues in video.json ("sfx": [[seg, frac, kind, gain], ...]).
import json, os, sys
import numpy as np, soundfile as sf

SR = 48000
rng = np.random.default_rng(7)

def spectral(x, f):
    """apply a frequency response f(freqs) to signal x via FFT"""
    X = np.fft.rfft(x); fr = np.fft.rfftfreq(len(x), 1 / SR); return np.fft.irfft(X * f(fr), len(x))
def lp(x, fc, order=2): return spectral(x, lambda fr: 1 / np.sqrt(1 + (fr / fc) ** (2 * order)))
def hp(x, fc, order=2): return spectral(x, lambda fr: 1 / np.sqrt(1 + (fc / np.maximum(fr, 1e-3)) ** (2 * order)))
def bp(x, fc, q=2.0): return spectral(x, lambda fr: 1 / np.sqrt(1 + (q * (fr / fc - fc / np.maximum(fr, 1e-3))) ** 2))
def conv(a, b):
    n = len(a) + len(b) - 1; N = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(a, N) * np.fft.rfft(b, N), N)[:n]
def mtof(m): return 440 * 2 ** ((m - 69) / 12)
def env_adsr(n, a, r):
    e = np.ones(n); na, nr = int(a * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na) ** 1.5; e[-nr:] *= np.linspace(1, 0, nr) ** 1.5; return e

def saw(f, n, det=0.0):
    t = np.arange(n) / SR; ph = (f * (1 + det) * t + rng.random()) % 1; return 2 * ph - 1

def pad_chord(notes, n):
    out = np.zeros(n)
    for m in notes:
        for d in (-0.004, 0.0, 0.0037):
            out += saw(mtof(m), n, d) * 0.33
    # slow vibrato-like movement via a gentle filter sweep: split in two filtered copies crossfaded
    a, b = lp(out, 600), lp(out, 1100)
    w = 0.5 + 0.5 * np.sin(np.linspace(0, np.pi * 2 * rng.uniform(.6, 1.2), n))
    return a * (1 - w * .5) + b * w * .5

def piano(m, dur):
    n = int(dur * SR); t = np.arange(n) / SR; f = mtof(m); y = np.zeros(n)
    for h, (amp, dec) in enumerate([(1, 2.2), (.45, 1.4), (.22, .9), (.12, .6), (.06, .4)], 1):
        y += amp * np.sin(2 * np.pi * f * h * (1 + .0007 * h * h) * t) * np.exp(-t / dec)
    hammer = lp(rng.standard_normal(n) * np.exp(-t / .006), 2500) * .3
    return lp(y + hammer, 2200) * np.minimum(1, t / .004)

def reverb_ir(sec=3.2):
    n = int(sec * SR); t = np.arange(n) / SR
    ir = np.stack([rng.standard_normal(n), rng.standard_normal(n)]) * np.exp(-t / (sec / 6.9))
    ir = np.stack([lp(c, 5000) for c in ir]); ir[:, :int(.02 * SR)] *= np.linspace(0, 1, int(.02 * SR))
    return ir / np.sqrt(np.sum(ir ** 2, axis=1, keepdims=True))

PROG = [  # D minor, slow and unresolved: Dm - Bb - F - C/E - Gm - Bb - A sus - A
    [50, 57, 62, 65], [46, 53, 58, 62], [41, 53, 57, 60], [40, 52, 55, 60],
    [43, 55, 58, 62], [46, 53, 58, 65], [45, 52, 57, 62], [45, 52, 57, 61]]
MEL = [(0, 69), (1.5, 67), (2, 65), (4, 62), (5.5, 65), (6, 64), (8, 62), (10, 65), (12, 67), (13.5, 65), (14, 64)]

def music(total, bpm=64):
    beat = 60 / bpm; bar = beat * 4; n = int((total + 3) * SR)
    pad = np.zeros(n); drone = np.zeros(n); keys = np.zeros(n); pulse = np.zeros(n)
    k = 0; t0 = 0.0
    while t0 < total + 2:
        ch = PROG[k % len(PROG)]; a = int(t0 * SR); L = int(bar * 2 * SR) + int(1.5 * SR); b = min(n, a + L)
        seg = pad_chord(ch[1:], L) * env_adsr(L, 1.4, 1.6); pad[a:b] += seg[:b - a]
        d = (np.sin(2 * np.pi * mtof(ch[0] - 12) * np.arange(L) / SR) + .35 * saw(mtof(ch[0] - 12), L)) * env_adsr(L, 1.0, 1.5)
        drone[a:b] += lp(d, 260)[:b - a]
        t0 += bar * 2; k += 1
    # felt piano motif, every 16 bars, from bar 2
    for start in np.arange(bar * 2, total, bar * 8):
        for (bt, m) in MEL:
            tt = start + bt * beat
            if tt > total - 1: break
            p = piano(m, 3.0); a = int(tt * SR); b = min(n, a + len(p)); keys[a:b] += p[:b - a] * rng.uniform(.75, 1)
    # soft low pulse on beats 1 and 3 after the intro, like a slow heartbeat
    hb = np.arange(int(.35 * SR)) / SR
    thump = np.sin(2 * np.pi * (52 - 20 * hb) * hb) * np.exp(-hb / .09)
    for tt in np.arange(bar * 4, total - 1, beat * 2):
        a = int(tt * SR); pulse[a:a + len(thump)] += thump[:n - a]
    dry = pad * .16 + drone * .2 + keys * .2 + pulse * .22
    ir = reverb_ir()
    wet = np.stack([conv(dry, ir[c])[:n] for c in (0, 1)])
    st = np.stack([dry * .55, dry * .55]) + wet * .9
    st = np.stack([hp(c, 35) for c in st])
    fade = np.ones(n); fi = int(1.5 * SR); fade[:fi] = np.linspace(0, 1, fi)
    fo = int(2.5 * SR); end = int(total * SR); fade[end - fo:end] *= np.linspace(1, 0, fo); fade[end:] = 0
    st *= fade
    return st / np.max(np.abs(st)), n

# ---------------------------------------------------------------- sfx
def sfx(kind, gain=1.0):
    def T(d): return np.arange(int(d * SR)) / SR
    if kind == 'whoosh':
        t = T(.7); e = np.sin(np.pi * np.clip(t / .7, 0, 1)) ** 2
        y = bp(rng.standard_normal(len(t)), 900, .7) * e
        y = y * .5 + lp(rng.standard_normal(len(t)), 400) * e * .5
    elif kind == 'thud':
        t = T(.6); y = np.sin(2 * np.pi * (70 - 35 * t) * t) * np.exp(-t / .12) + lp(rng.standard_normal(len(t)), 300) * np.exp(-t / .05) * .6
    elif kind == 'knock':  # wood on wood
        t = T(.35); y = sum(np.sin(2 * np.pi * f * t) * np.exp(-t / d) * a for f, d, a in ((420, .06, 1), (910, .03, .5), (1560, .015, .3)))
        y += bp(rng.standard_normal(len(t)), 1800, 2) * np.exp(-t / .008) * .6
    elif kind == 'stone':
        t = T(.4); y = bp(rng.standard_normal(len(t)), 2400, 1.5) * np.exp(-t / .02) + np.sin(2 * np.pi * 180 * t) * np.exp(-t / .05) * .5
    elif kind == 'splash':
        t = T(1.0); y = bp(rng.standard_normal(len(t)), 1500, .8) * np.exp(-t / .25)
        for _ in range(10):
            a = int(rng.uniform(0, .6) * SR); f = rng.uniform(500, 1400); bt = T(.06)
            bub = np.sin(2 * np.pi * f * (1 + 3 * bt) * bt) * np.exp(-bt / .02); y[a:a + len(bub)] += bub[:len(y) - a] * .5
    elif kind == 'water':  # gentle running water bed, 3 s
        t = T(3.0); y = bp(rng.standard_normal(len(t)), 1100, .6) * (0.6 + 0.4 * np.sin(t * 9)) * np.sin(np.pi * t / 3) * .6
    elif kind == 'rain':
        t = T(4.0); y = hp(rng.standard_normal(len(t)), 2500) * .35 * np.sin(np.pi * t / 4)
        for _ in range(140):
            a = int(rng.uniform(0, 3.9) * SR); bt = T(.012); y[a:a + len(bt)] += rng.standard_normal(len(bt)) * np.exp(-bt / .002) * .6
    elif kind == 'wind':
        t = T(3.0); y = bp(rng.standard_normal(len(t)), 500, 1.5) * (0.5 + 0.5 * np.sin(t * 2.1)) * np.sin(np.pi * t / 3)
    elif kind == 'machine':
        t = T(3.0); y = (lp(rng.standard_normal(len(t)), 180) * 1.5 + .4 * np.sign(np.sin(2 * np.pi * 47 * t)) * .3) * np.sin(np.pi * t / 3) ** .5
        y = lp(y, 900)
    elif kind == 'fire':
        t = T(3.0); y = lp(rng.standard_normal(len(t)), 700) * .4 * np.sin(np.pi * t / 3)
        for _ in range(60):
            a = int(rng.uniform(0, 2.9) * SR); bt = T(.01); y[a:a + len(bt)] += rng.standard_normal(len(bt)) * np.exp(-bt / .0015)
    elif kind == 'metal':
        t = T(1.2); y = sum(np.sin(2 * np.pi * f * t) * np.exp(-t / d) for f, d in ((523, .5), (1187, .3), (2290, .15))) * .5
        y += bp(rng.standard_normal(len(t)), 3000, 2) * np.exp(-t / .01)
    elif kind == 'pop':
        t = T(.15); y = np.sin(2 * np.pi * (900 - 2500 * t) * t) * np.exp(-t / .03)
    elif kind == 'truck':
        t = T(3.5); y = lp(rng.standard_normal(len(t)), 120) * 2 + .3 * np.sin(2 * np.pi * 38 * t)
        y = lp(y, 500) * np.minimum(1, t / .6) * np.minimum(1, (3.5 - t) / .8)
    else:
        raise ValueError(kind)
    y = y / (np.max(np.abs(y)) + 1e-9)
    return y * gain

# ---------------------------------------------------------------- mastering
# The narrator always sits clearly on top: voice compressed, music ducked well under it, sound effects
# 12 dB lower than the first mixes, then loudness-normalised to -14 LUFS integrated (TikTok) with a
# -1 dBTP true-peak ceiling.
BED_GAIN, FX_GAIN = 0.075, 0.22 * 10 ** (-12 / 20)
TARGET_LUFS, CEIL_DBTP = -14.0, -1.0
def env(x, sec):
    w = max(1, int(sec * SR)); return np.sqrt(np.convolve(x * x, np.ones(w) / w, 'same') + 1e-12)
def compress(v, thr_db=-24, ratio=3.0):
    e = env(v, .04); thr = 10 ** (thr_db / 20) * np.max(np.abs(v))
    g = np.where(e > thr, (e / thr) ** (1 / ratio - 1), 1.0)
    w = int(.01 * SR); g = np.convolve(g, np.ones(w) / w, 'same'); return v * g
def kweight(x):
    """ITU-R BS.1770 K-weighting (high-pass ~38 Hz + +4 dB high shelf ~1.7 kHz), applied in the frequency domain"""
    def f(fr):
        hpf = 1 / np.sqrt(1 + (38.0 / np.maximum(fr, 1e-3)) ** 4)
        shelf = 10 ** ((4.0 / 20) * (1 / (1 + (1681.0 / np.maximum(fr, 1e-3)) ** 2)))
        return hpf * shelf
    return spectral(x, f)
def lufs(st):
    """integrated loudness (gated, 400 ms blocks, 75% overlap) of a (2, n) signal"""
    k = np.stack([kweight(c) for c in st]); blk, hop = int(.4 * SR), int(.1 * SR)
    pw = np.array([np.sum(np.mean(k[:, i:i + blk] ** 2, axis=1)) for i in range(0, k.shape[1] - blk, hop)])
    L = -0.691 + 10 * np.log10(pw + 1e-12); g = pw[L > -70]
    rel = -0.691 + 10 * np.log10(np.mean(g)) - 10; g = pw[(L > -70) & (L > rel)]
    return -0.691 + 10 * np.log10(np.mean(g))
def oversample(x, f=4):
    n = len(x); X = np.fft.rfft(x); Y = np.zeros(n * f // 2 + 1, complex); Y[:len(X)] = X
    return np.fft.irfft(Y, n * f) * f
def true_peak(st): return 20 * np.log10(max(np.max(np.abs(oversample(c))) for c in st))
def limit(st, ceil_db):
    """look-ahead peak limiter on the 4x-oversampled peaks (true peak), 1.5 ms attack, 60 ms release"""
    c = 10 ** (ceil_db / 20); pk = np.max(np.stack([np.abs(oversample(x)).reshape(-1, 4).max(1) for x in st]), 0)
    need = np.minimum(1.0, c / np.maximum(pk, 1e-9))
    a = int(.0015 * SR); r = int(.06 * SR)
    from scipy.ndimage import minimum_filter1d, uniform_filter1d
    # min over the look-ahead/release window, then average over the release window: every averaged value is
    # <= the gain needed at that sample, so peaks stay under the ceiling, and recovery is smooth
    g = minimum_filter1d(need, 2 * a + 1)
    out = uniform_filter1d(minimum_filter1d(need, 2 * r + 1), r)
    return st * np.minimum(out, g)
def master(voice, bed, fx):
    """voice: mono; bed, fx: (2, n) already at their mix gains. Returns the (2, n) master."""
    v = compress(voice); v /= np.max(np.abs(v))
    ev = env(v, .25); k = np.minimum(1, ev / (np.max(ev) * .3))
    n = len(v); bed = bed[:, :n]; fx = fx[:, :n]
    m = np.stack([v, v]) + bed * (1 - .55 * k) + fx * (1 - .5 * k)
    for _ in range(4):
        m *= 10 ** ((TARGET_LUFS - lufs(m)) / 20)
        m = limit(m, CEIL_DBTP - 0.8)   # margin for AAC overshoot
    print(f'master: {lufs(m):.1f} LUFS, true peak {true_peak(m):.1f} dBTP')
    return m

def place(buf, y, t, pan=0.0):
    a = int(t * SR); b = min(buf.shape[1], a + len(y))
    if a >= buf.shape[1] or b <= a: return
    buf[0, a:b] += y[:b - a] * (1 - max(0, pan)); buf[1, a:b] += y[:b - a] * (1 + min(0, pan))

def run(vdir):
    TL = json.load(open(os.path.join(vdir, 'timeline.json')))
    cfg = json.load(open(os.path.join(vdir, 'video.json'), encoding='utf-8'))
    seg = [(s['start'], s['end']) for s in TL['segments']]; total = TL['total']
    ad = os.path.join(vdir, 'audio')
    voice, sr = sf.read(os.path.join(ad, 'stem-voice.wav')); assert sr == SR
    bed, n = music(total)
    n = len(voice); bed = bed[:, :n]
    fx = np.zeros((2, n))
    for i, (s, e) in enumerate(seg[1:], 1): place(fx, sfx('whoosh', .35), s - .35, .3 if i % 2 else -.3)
    for c in cfg.get('sfx', []):
        si, frac, kind = c[0], c[1], c[2]; g = c[3] if len(c) > 3 else .6
        s, e = seg[si]; place(fx, sfx(kind, g), s + (e - s) * frac, rng.uniform(-.25, .25))
    fx = np.stack([lp(c, 9000) for c in fx])
    bed = bed * BED_GAIN; fx = fx * FX_GAIN
    m = master(voice, bed, fx)
    sf.write(os.path.join(ad, 'stem-music.wav'), bed.T.astype(np.float32), SR)
    sf.write(os.path.join(ad, 'stem-sfx.wav'), fx.T.astype(np.float32), SR)
    sf.write(os.path.join(ad, 'mix.wav'), m.T.astype(np.float32), SR, subtype='PCM_16')
    print('mix', round(n / SR, 2), 's')

if __name__ == '__main__':
    run(os.path.abspath(sys.argv[1]))
