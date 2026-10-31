# Mid-video "you haven't followed yet" pause, done in the edit/mix step (no re-render).
#   python pause.py ..\videos\09-footpath-to-highway
# At the step boundary nearest the middle, the picture freezes: the paused frame shrinks to the centre over a
# blurred copy of itself, a pause icon appears, the narrator says video.json "pause_line" (captioned word by word),
# then stalling banter, a 3 s hold, a playful "thank you", then the video carries on. The un-paused encode is kept as <name>-nopause.mp4.
import json, os, re, subprocess, sys
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import overlay, voice, audio
W, H, FPS, SR = overlay.W, overlay.H, overlay.FPS, 48000
LEAD, HOLD = 0.35, 3.0   # 3 s hold before the thank-you

def duration(path):
    out = subprocess.run([overlay.ffmpeg(), '-i', path], capture_output=True, text=True).stderr
    h, m, s = re.search(r'Duration: (\d+):(\d+):([\d.]+)', out).groups(); return int(h) * 3600 + int(m) * 60 + float(s)

class _Cap:   # minimal stand-in for overlay.Video so overlay.draw_caption can be reused
    def __init__(self, words): self.words = words; self.key = {'follow', 'wait', 'waiting', 'paused', 'pause', 'thank', 'thanks', 'free'}

def card(base, k):
    """paused look: blurred dark background + the frame shrunk to the centre with a white border and shadow"""
    bg = base.filter(ImageFilter.GaussianBlur(22)).point(lambda v: int(v * 0.42))
    s = 1.0 - 0.2 * overlay.eo(k); w, h = int(W * s), int(H * s)
    fr = base.resize((w, h), Image.LANCZOS)
    x, y = (W - w) // 2, (H - h) // 2
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle([x + 10, y + 18, x + w + 10, y + h + 18], 40, fill=(0, 0, 0, 150))
    out = bg.convert('RGBA'); out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(20)))
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w, h], int(40 * overlay.eo(k)) + 1, fill=255)
    border = Image.new('RGBA', (w + 16, h + 16), (0, 0, 0, 0)); ImageDraw.Draw(border).rounded_rectangle([0, 0, w + 15, h + 15], 46, fill=(255, 255, 255, int(255 * overlay.eo(k))))
    out.alpha_composite(border, (x - 8, y - 8)); out.paste(fr, (x, y), m)
    # pause icon
    a = int(255 * overlay.eo(k)); d = ImageDraw.Draw(out); cx, cy = W // 2, 250
    d.ellipse([cx - 70, cy - 70, cx + 70, cy + 70], fill=(15, 18, 24, int(a * .85)), outline=(255, 210, 58, a), width=6)
    d.rounded_rectangle([cx - 30, cy - 36, cx - 10, cy + 36], 6, fill=(255, 255, 255, a)); d.rounded_rectangle([cx + 10, cy - 36, cx + 30, cy + 36], 6, fill=(255, 255, 255, a))
    return out

def run(vdir):
    V = overlay.Video(vdir); cfg = V.cfg
    # the pause bit: cheeky line, stalling banter, a 3 s hold, then "thank you" and the video carries on
    parts = [(cfg['pause_line'], 0.45), (cfg['pause_banter'], HOLD), (cfg['pause_thanks'], 0.35)]
    nopause = V.mp4.replace('.mp4', '-nopause.mp4')
    if not os.path.exists(nopause): os.replace(V.mp4, nopause)
    seg = V.seg; mid = V.total / 2
    k = min(range(4, len(seg) - 3), key=lambda i: abs(seg[i][0] - mid))
    fp = int(round((seg[k - 1][1] + 0.1) * FPS)); tp = fp / FPS
    # ---- pause narration, loudness-matched to the narration around it
    from kokoro_onnx import Kokoro
    kk = Kokoro(voice.MODEL, voice.VOICES)
    mix, _ = sf.read(os.path.join(vdir, 'audio', 'mix.wav')); mix = mix.T
    ref = mix[0, int(seg[k - 1][0] * SR):int(seg[k - 1][1] * SR)]
    pieces = [np.zeros(int(LEAD * SR))]; words = []; acc = LEAD; spans = []
    for text, gap in parts:
        y, sr = kk.create(text, voice=voice.VOICE, speed=voice.SPEED, lang='en-us')
        y = voice.resample(voice.trim(np.asarray(y, np.float64), sr), sr, SR)
        y *= np.sqrt(np.mean(ref ** 2)) / np.sqrt(np.mean(y ** 2))
        dur = len(y) / SR; spans.append((round(acc, 3), round(acc + dur, 3), text))
        ws = [w for w in text.split() if w]
        wt = [len(re.sub(r"[^\w']", '', w)) + 2.2 + (3 if re.search(r'[,.?!]$', w) else 0) for w in ws]
        a0 = acc
        for j, w in enumerate(ws):
            d = dur * wt[j] / sum(wt); words.append(dict(w=re.sub(r"[^\w'’-]", '', w), s=a0, e=a0 + d)); a0 += d
        pieces += [y, np.zeros(int(gap * SR))]; acc += dur + gap
    pz = np.concatenate(pieces); stop = audio.sfx('pop', 0.25) * 0.5; pz[:len(stop)] += stop
    D = len(pz) / SR
    a = int(tp * SR); f = int(.02 * SR)
    A = mix[:, :a].copy(); A[:, -f:] *= np.linspace(1, 0, f); B = mix[:, a:].copy(); B[:, :f] *= np.linspace(0, 1, f)
    full = np.concatenate([A, np.stack([pz, pz]), B], axis=1)
    full = audio.limit(full, audio.CEIL_DBTP - 0.8)
    wav = os.path.join(vdir, 'audio', 'mix-paused.wav'); sf.write(wav, full.T.astype(np.float32), SR, subtype='PCM_16')
    print(f'pause at {tp:.2f}s (before step {k}), {D:.2f}s long; master {audio.lufs(full):.1f} LUFS, {audio.true_peak(full):.1f} dBTP')
    # ---- pause frames
    ff = overlay.ffmpeg(); tmp = os.path.join(vdir, 'out', '_freeze.png')
    subprocess.run([ff, '-y', '-loglevel', 'error', '-ss', f'{(fp - 1) / FPS:.4f}', '-i', nopause, '-frames:v', '1', tmp], check=True)
    base = Image.open(tmp).convert('RGB'); os.remove(tmp)
    cap = _Cap(words); n = int(round(D * FPS)); clip = os.path.join(vdir, 'out', '_pause.mp4')
    p = subprocess.Popen([ff, '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', clip], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    for i in range(n):
        t = i / FPS; img = card(base, min(1, t / .25))
        overlay.draw_caption(cap, img, t); p.stdin.write(img.convert('RGB').tobytes())
    p.stdin.close(); p.wait()
    # ---- splice: frames [0, fp) + pause + frames [fp, end], with the new audio
    fc = (f'[0:v]trim=end_frame={fp},setpts=PTS-STARTPTS[a];[0:v]trim=start_frame={fp},setpts=PTS-STARTPTS[b];'
          f'[a][1:v][b]concat=n=3:v=1:a=0[v]')
    subprocess.run([ff, '-y', '-i', nopause, '-i', clip, '-i', wav, '-filter_complex', fc, '-map', '[v]', '-map', '2:a',
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
                    '-movflags', '+faststart', '-shortest', V.mp4], check=True, stderr=subprocess.DEVNULL)
    os.remove(clip)
    json.dump(dict(at=tp, before_step=k, length=D, spans=spans, hold=HOLD, total=duration(V.mp4)), open(os.path.join(vdir, 'pause.json'), 'w'), indent=1)
    print('paused video', V.mp4, f'{duration(V.mp4):.1f}s')

if __name__ == '__main__':
    run(os.path.abspath(sys.argv[1]))
