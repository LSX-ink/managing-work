# One command per video:  python make.py ..\videos\01-log-cabin [steps]
# steps (default all, in order): voice audio render encode phone sheet caption push
# A new video = a folder videos\NN-slug\ with script.json (14 steps, first words "Did you know", last
# "And that's how X becomes Y."), scene.py (Blender, imports ll.py) and video.json (title, keywords, labels,
# arrows, sfx, topic_tag). Everything else (audio\, frames\, cams\, out\, caption.txt) is generated.
import json, os, subprocess, sys, shutil, tempfile

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
BLENDER = r'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
REPO = r'C:\Users\Thato\managing-work'; BRANCH = 'claude/project-thread-vez681'; MEDIA = 'lowkey-lore-media'
STEPS = ['voice', 'audio', 'lint', 'render', 'encode', 'pause', 'phone', 'sheet', 'caption', 'qc', 'push']   # extra: 'remux'
# Gate: lint must have 0 fails before rendering; push only happens when qc.gate() is true (automatic QC passed
# AND the visual / real-life review approved this exact file). Anything else is sent back to be fixed.
TAGS = '#HowItWorks #Engineering #Science #learnontiktok'

def caption(vdir):
    cfg = json.load(open(os.path.join(vdir, 'video.json'), encoding='utf-8'))
    words = ' '.join(cfg['title']).lower().split()
    title = ' '.join(w if w in ('a', 'of', 'the', 'in', 'into') and i else w.capitalize() for i, w in enumerate(words))
    txt = ' '.join(x for x in (title, cfg.get('emoji', ''), TAGS, cfg.get('topic_tag', '')) if x)   # one line, copy-paste ready
    open(os.path.join(vdir, 'caption.txt'), 'w', encoding='utf-8').write(txt + '\n'); print(txt); return txt

def push(files, msg):
    """temporary worktree of the managing-work repo on BRANCH, copy files into lowkey-lore-media, commit, push"""
    g = lambda *a, cwd=REPO: subprocess.run(['git', *a], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()
    g('fetch', 'origin', BRANCH)
    wt = tempfile.mkdtemp(prefix='llwt_'); shutil.rmtree(wt)
    g('worktree', 'add', '--detach', wt, f'origin/{BRANCH}')
    try:
        os.makedirs(os.path.join(wt, MEDIA), exist_ok=True)
        for f in files: shutil.copy2(f, os.path.join(wt, MEDIA, os.path.basename(f)))
        g('add', *[f'{MEDIA}/{os.path.basename(f)}' for f in files], cwd=wt)
        g('commit', '-m', msg + '\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>', cwd=wt)
        for i in range(5):
            try: g('push', 'origin', f'HEAD:{BRANCH}', cwd=wt); break
            except subprocess.CalledProcessError:
                if i == 4: raise
                import time; time.sleep(2 ** (i + 1))
        h = g('rev-parse', 'HEAD', cwd=wt); print('pushed', h); return h
    finally:
        subprocess.run(['git', 'worktree', 'remove', '--force', wt], cwd=REPO); subprocess.run(['git', 'worktree', 'prune'], cwd=REPO)

def main():
    vdir = os.path.abspath(sys.argv[1]); steps = sys.argv[2:] or STEPS
    import overlay
    if 'voice' in steps: import voice; voice.run(vdir)
    if 'audio' in steps: import audio; audio.run(vdir)
    if 'lint' in steps:
        subprocess.run([BLENDER, '-b', '-P', os.path.join(vdir, 'scene.py'), '--', '--video', vdir, '--lint'], capture_output=True)
        lint = json.load(open(os.path.join(vdir, 'qc', 'lint.json')))
        fails = [m for m in lint if m['severity'] == 'fail']
        for m in fails: print('LINT FAIL', m['kind'], m['t0'], m['t1'], m['objects'], m['note'])
        if fails: sys.exit('scene lint failed: fix the scene before rendering')
    if 'render' in steps:
        # chunks of CHUNK frames, one fresh Blender each: a long persistent EEVEE render crashes (access violation
        # in render_read_result) after ~1000 frames. Continues after frames already on disk; a crash retries the chunk.
        import re; CHUNK = 600; fd = os.path.join(vdir, 'frames'); lp = os.path.join(vdir, 'render_log.txt'); fails = 0
        open(lp, 'w').close()
        while True:
            a = 0
            while os.path.exists(os.path.join(fd, f'{a:05d}.png')): a += 1
            with open(lp, 'a') as log:
                r = subprocess.run([BLENDER, '-b', '-P', os.path.join(vdir, 'scene.py'), '--', '--video', vdir,
                                    '--frames', f'{a}-{a + CHUNK - 1}'], stdout=log, stderr=subprocess.STDOUT)
            if r.returncode:
                fails += 1
                if fails > 3: sys.exit(f'render crashed {fails} times near frame {a}')
                continue
            done = re.findall(r'DONE (\d+)-(\d+)', open(lp).read())
            if not done or int(done[-1][1]) < a + CHUNK - 1: break   # last chunk was shorter: the video is complete
    V = overlay.Video(vdir) if any(s in steps for s in ('encode', 'remux', 'pause', 'phone', 'sheet', 'push')) else None
    if 'encode' in steps: overlay.encode(V)
    if 'remux' in steps: overlay.remux(V.mp4, os.path.join(vdir, 'audio', 'mix.wav'))
    if 'pause' in steps and V.cfg.get('pause_line'): import pause; pause.run(vdir)   # mid-video "follow" pause
    if 'phone' in steps or 'sheet' in steps:
        import pause as _p; dur = _p.duration(V.mp4)
        if 'phone' in steps: overlay.phone(V.mp4, V.phone, dur)
        if 'sheet' in steps: overlay.sheet(V.mp4, V.sheet, dur)
    if 'caption' in steps: caption(vdir)
    if 'qc' in steps:
        import qc
        if not qc.run(vdir): sys.exit('QC failed: sent back to be fixed')
    if 'push' in steps:
        import qc
        if not qc.gate(vdir): sys.exit('not pushed: QC + visual approval required for this exact file')
        cfg = json.load(open(os.path.join(vdir, 'video.json'), encoding='utf-8'))
        import pause as _p
        push([V.phone, V.sheet], f"lowkey.lore: {' '.join(cfg['title']).lower()} ({_p.duration(V.phone):.0f} s), phone copy + contact sheet")

if __name__ == '__main__':
    main()
