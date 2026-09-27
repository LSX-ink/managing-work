// HUD memory folders: the MEMORY button labels the wolf's six parts as folders.
// Click a part to open that folder: rename it, read or delete what's in it, save a note or add files.
// The folders are real folders on the PC (jarvis/memory), and Alfred can save notes into them too.
window.HudMemory = (() => {
    const $ = (id) => document.getElementById(id);
    const state = { open: false, hover: -1, folders: [], current: -1 };

    const kb = (n) => (n < 1024 ? `${n} B` : n < 1048576 ? `${Math.round(n / 1024)} KB` : `${(n / 1048576).toFixed(1)} MB`);
    const say = (text) => { $('memory-msg').textContent = text; };

    async function load() {
        try {
            state.folders = (await (await fetch('/memory')).json()).folders || [];
        } catch (e) { /* keep the last listing */ }
        if (state.current >= 0) showFolder(state.current);
    }

    async function call(method, url, body, raw = false) {
        const res = await fetch(url, {
            method,
            headers: raw ? {} : { 'Content-Type': 'application/json' },
            body: raw ? body : JSON.stringify(body),
        });
        if (!res.ok) throw new Error((await res.text()) || 'That didn’t work.');
        return res.json();
    }

    function showFolder(i) {
        const folder = state.folders[i];
        if (!folder) return;
        state.current = i;
        $('memory-panel').hidden = false;
        if (document.activeElement !== $('memory-name')) $('memory-name').value = folder.name;
        const list = $('memory-items');
        list.replaceChildren();
        for (const sub of folder.folders || []) {           // folders made inside this one ("Work/Invoices")
            const li = document.createElement('li');
            li.className = 'mem-folder';
            const open = document.createElement('button');
            open.type = 'button';
            open.textContent = `▸ ${sub.name}/`;
            open.title = 'Open in File Explorer';
            open.addEventListener('click', async () => {
                try { await call('POST', `/memory/${i}/open`, { folder: sub.name }); say(`Opened ${sub.name} on the PC.`); } catch (e) { say(e.message); }
            });
            const size = document.createElement('span');
            size.className = 'size';
            size.textContent = `${sub.count} item${sub.count === 1 ? '' : 's'}`;
            li.append(open, size);
            list.append(li);
        }
        if (!folder.items.length && !(folder.folders || []).length) {
            const li = document.createElement('li');
            li.className = 'mem-empty';
            li.textContent = 'Nothing saved here yet.';
            list.append(li);
        }
        for (const item of folder.items) {
            const li = document.createElement('li');
            const link = document.createElement('a');
            link.href = `/memory/${i}/files/${encodeURIComponent(item.name)}`;
            link.target = '_blank';
            link.rel = 'noopener';
            link.textContent = item.name;
            const size = document.createElement('span');
            size.className = 'size';
            size.textContent = kb(item.size);
            const del = document.createElement('button');
            del.type = 'button';
            del.textContent = '×';
            del.setAttribute('aria-label', `Delete ${item.name}`);
            del.addEventListener('click', async () => {
                try { await call('DELETE', link.href); await load(); say(`Deleted ${item.name}.`); } catch (e) { say(e.message); }
            });
            li.append(link, size, del);
            list.append(li);
        }
    }

    function closeFolder() {
        state.current = -1;
        $('memory-panel').hidden = true;
        say('');
    }

    function setOpen(open) {
        state.open = open;
        $('hud-memory').setAttribute('aria-pressed', String(open));
        $('orb-wrap').classList.toggle('memory', open);
        if (open) load(); else closeFolder();
    }

    function start() {
        if (!document.body.classList.contains('hud')) return;
        const wrap = $('orb-wrap'), canvas = $('hud-sphere');
        $('hud-memory').addEventListener('click', () => setOpen(!state.open));
        wrap.addEventListener('mousemove', (e) => {
            state.hover = state.open ? window.HudWolf.partAtPoint(canvas, e.clientX, e.clientY) : -1;
            wrap.classList.toggle('over', state.hover >= 0);
        });
        wrap.addEventListener('mouseleave', () => { state.hover = -1; wrap.classList.remove('over'); });
        wrap.addEventListener('click', (e) => {
            if (!state.open) return;
            const part = window.HudWolf.partAtPoint(canvas, e.clientX, e.clientY);
            if (part >= 0) { say(''); showFolder(part); }
        });
        $('memory-close').addEventListener('click', closeFolder);
        document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && state.current >= 0) closeFolder(); });

        const rename = async () => {
            const i = state.current, name = $('memory-name').value.trim();
            if (i < 0 || !name || name === state.folders[i].name) return;
            try { await call('POST', `/memory/${i}/rename`, { name }); $('memory-name').blur(); await load(); say(`Renamed to ${state.folders[i].name}.`); } catch (e) { say(e.message); }
        };
        $('memory-rename').addEventListener('click', rename);
        $('memory-name').addEventListener('keydown', (e) => { if (e.key === 'Enter') rename(); });

        $('memory-save').addEventListener('click', async () => {
            const text = $('memory-text').value.trim();
            const title = $('memory-title').value.trim() || text.split('\n')[0].slice(0, 40) || 'Note';
            if (!text) { say('Write something first.'); return; }
            try {
                const saved = await call('POST', `/memory/${state.current}/note`, { title, text });
                $('memory-text').value = ''; $('memory-title').value = '';
                await load(); say(`Saved ${saved.name}.`);
            } catch (e) { say(e.message); }
        });

        $('memory-file').addEventListener('change', async (e) => {
            const i = state.current;
            for (const file of e.target.files) {
                try { await call('PUT', `/memory/${i}/files/${encodeURIComponent(file.name)}`, file, true); say(`Added ${file.name}.`); } catch (err) { say(err.message); }
            }
            e.target.value = '';
            await load();
        });

        // "Alfred, open my Ideas folder": show the labels and open that folder's panel.
        document.addEventListener('jarvis:memory', async (e) => {
            if (!state.open) setOpen(true);
            await load();
            const i = state.folders.findIndex((f) => f.name === e.detail.open);
            if (i >= 0) { say(''); showFolder(i); }
        });

        // Alfred may have saved something while thinking: refresh when a reply finishes.
        const orb = $('orb');
        let wasThinking = false;
        new MutationObserver(() => {
            const thinking = orb.classList.contains('thinking');
            if (wasThinking && !thinking && state.open) load();
            wasThinking = thinking;
        }).observe(orb, { attributes: true, attributeFilter: ['class'] });
    }

    document.addEventListener('jarvis:config', start);

    return {
        get open() { return state.open; },
        get hover() { return state.hover; },
        labels: () => state.folders.map((f) => `${f.name.toUpperCase()} · ${f.items.length}`),
    };
})();
