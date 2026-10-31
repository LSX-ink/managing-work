# Download extra CC0 Poly Haven textures/models into ../assets (skips files already there).
#   python fetch_assets.py tex:brick_wall_001 tex:asphalt_02:2k model:fir_tree_01:1k
import requests, os, sys, concurrent.futures as cf
H = {'User-Agent': 'lowkey-lore-pipeline/1.0'}
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets')
MAPS = {'Diffuse': 'diff', 'nor_gl': 'nor', 'Rough': 'rough', 'Displacement': 'disp', 'AO': 'ao', 'Metal': 'metal'}
jobs, missing = [], []
def add(url, dst):
    if not os.path.exists(dst): jobs.append((url, dst))
for spec in sys.argv[1:]:
    kind, aid, *r = spec.split(':'); res = r[0] if r else ('2k' if kind == 'tex' else '1k')
    f = requests.get('https://api.polyhaven.com/files/' + aid, headers=H, timeout=60).json()
    if kind == 'tex':
        if 'Diffuse' not in f: missing.append(aid); continue
        for k, s in MAPS.items():
            if k in f and res in f[k]:
                fm = 'jpg' if 'jpg' in f[k][res] else 'png'
                add(f[k][res][fm]['url'], f'{ROOT}/textures/{aid}/{aid}_{s}.{fm}')
    else:
        if 'blend' not in f: missing.append(aid); continue
        b = (f['blend'].get(res) or list(f['blend'].values())[0])['blend']
        add(b['url'], f'{ROOT}/models/{aid}/{aid}.blend')
        for p, v in b.get('include', {}).items(): add(v['url'], f'{ROOT}/models/{aid}/{p}')
def get(j):
    u, d = j; os.makedirs(os.path.dirname(d), exist_ok=True)
    for _ in range(4):
        try:
            r = requests.get(u, headers=H, timeout=300); r.raise_for_status(); open(d, 'wb').write(r.content); return None
        except Exception as e: err = str(e)
    return f'{u}: {err}'
with cf.ThreadPoolExecutor(8) as ex: errs = [e for e in ex.map(get, jobs) if e]
print('downloaded', len(jobs), 'files; missing:', missing, 'errors:', errs)
