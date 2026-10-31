# Narration on this PC with Kokoro TTS.
#   python voice.py ..\videos\01-log-cabin
# Reads script.json, writes audio\seg_NN.wav, audio\stem-voice.wav (48 kHz mono) and timeline.json
# (0.35 s lead, 0.2 s gaps, 1.6 s tail for the end title). Every video ends with the spoken OUTRO line,
# 0.35 s after "And that's how X becomes Y."; it is added to script.json if missing.
import json, os, sys
import numpy as np, soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
MODEL = os.path.join(ROOT, 'models', 'kokoro', 'kokoro-v1.0.onnx')
VOICES = os.path.join(ROOT, 'models', 'kokoro', 'voices-v1.0.bin')
VOICE, SPEED, SR = 'am_michael', 1.2, 48000
LEAD, GAP, TAIL = 0.35, 0.2, 1.6
OUTRO = 'Follow for more insight.'

def trim(x, sr, thr_db=-42, pad=0.025):
    env = np.convolve(np.abs(x), np.ones(int(sr * .01)) / int(sr * .01), 'same')
    on = np.where(env > np.max(env) * 10 ** (thr_db / 20))[0]
    if not len(on): return x
    a = max(0, on[0] - int(pad * sr)); b = min(len(x), on[-1] + int(pad * sr))
    y = x[a:b].copy(); f = int(sr * .008)
    y[:f] *= np.linspace(0, 1, f); y[-f:] *= np.linspace(1, 0, f)
    return y

def resample(x, sr0, sr1):
    n = int(round(len(x) * sr1 / sr0))
    X = np.fft.rfft(x); Y = np.zeros(n // 2 + 1, complex); m = min(len(X), len(Y)); Y[:m] = X[:m]
    return np.fft.irfft(Y, n) * (sr1 / sr0)

def run(vdir):
    script = json.load(open(os.path.join(vdir, 'script.json'), encoding='utf-8'))
    assert script[0].lower().startswith('did you know'), 'first words must be "Did you know"'
    if script[-1] != OUTRO:
        script.append(OUTRO); json.dump(script, open(os.path.join(vdir, 'script.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    assert script[-2].lower().startswith("and that's how"), "last step must be: And that's how X becomes Y."
    from kokoro_onnx import Kokoro
    k = Kokoro(MODEL, VOICES)
    ad = os.path.join(vdir, 'audio'); os.makedirs(ad, exist_ok=True)
    segs, pieces, t = [], [np.zeros(int(LEAD * SR))], LEAD
    for i, txt in enumerate(script):
        s, sr = k.create(txt, voice=VOICE, speed=SPEED, lang='en-us')
        y = resample(trim(np.asarray(s, np.float64), sr), sr, SR)
        sf.write(os.path.join(ad, f'seg_{i:02d}.wav'), y.astype(np.float32), SR)
        d = len(y) / SR; segs.append(dict(seg=i, start=round(t, 3), end=round(t + d, 3)))
        pieces.append(y); t += d
        if i < len(script) - 1:
            g = 0.35 if i == len(script) - 2 else GAP
            pieces.append(np.zeros(int(g * SR))); t += g
        print(f'seg {i:2d} {d:5.2f}s  {txt[:60]}', flush=True)
    pieces.append(np.zeros(int(TAIL * SR)))
    v = np.concatenate(pieces); v *= 0.89 / np.max(np.abs(v))
    sf.write(os.path.join(ad, 'stem-voice.wav'), v.astype(np.float32), SR)
    total = round(len(v) / SR, 3)
    json.dump(dict(segments=segs, total=total), open(os.path.join(vdir, 'timeline.json'), 'w'), indent=1)
    print(f'total {total:.1f}s', 'OK' if 70 <= total <= 90 else '!! OUTSIDE 70-90 s')
    return total

if __name__ == '__main__':
    run(os.path.abspath(sys.argv[1]))
