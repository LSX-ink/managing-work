// TikTok studio pop-up (creator.py): every account with its Connect link, and each video Alfred made, with a
// player, its caption, and one-tap tick (posts it, or saves it ready to upload by hand), X (rejects it and Alfred
// makes a better one) and Download.
(() => {
    const kinds = window.jarvisPopupKinds = window.jarvisPopupKinds || {};
    const WORD = { making: 'Being made', ready: 'Waiting for you', approved: 'Approved', posted: 'Sent to TikTok',
                   failed: "Couldn't finish", failed_post: "Didn't post", rejected: 'Rejected' };

    async function act(id, action, note) {
        note.textContent = action === 'approve' ? 'Posting...' : 'Rejecting, and making a better one...';
        try {
            const res = await fetch(`/creator/videos/${encodeURIComponent(id)}/${action}`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
            const answer = await res.json().catch(() => ({ ok: false, said: 'Something went wrong.' }));
            if (!res.ok || !answer.ok) { note.textContent = answer.said; return; }
            const { said, card } = answer;
            card.data.notice = said;
            document.dispatchEvent(new CustomEvent('jarvis:popup', { detail: card }));
        } catch (e) {
            note.textContent = "Alfred isn't answering. Is he running?";
        }
    }

    function copyButton(el, label, text) {
        const b = el('button', 'pop-action', label);
        b.addEventListener('click', async () => {
            try { await navigator.clipboard.writeText(text); b.textContent = 'Copied'; }
            catch (e) { b.textContent = "Couldn't copy"; }
            setTimeout(() => { b.textContent = label; }, 1500);
        });
        return b;
    }

    kinds['creator-studio'] = (card, body, { el, ask }) => {
        const { accounts = [], videos = [], configured, setup, notice, making, paused } = card.data || {};
        if (notice) body.append(el('div', 'cr-notice', notice));
        if (paused) body.append(el('div', 'cr-notice', 'Content making is paused. Say "resume content" to start again.'));
        const acc = el('div', 'cr-accounts');
        for (const a of accounts) {
            const row = el('div', 'cr-account');
            row.append(el('b', '', `@${a.name}`), el('span', 'cr-dim', `${a.style} · ${a.per_day} a day`));
            if (a.format !== 'clips') {
                const bible = el('button', 'pop-action cr-small', 'Story bible');
                bible.addEventListener('click', () => ask(`Show the story bible for ${a.name}.`));
                const works = el('button', 'pop-action cr-small', "What's working");
                works.addEventListener('click', () => ask(`What's working on ${a.name}?`));
                row.append(bible, works);
            }
            if (a.connected) row.append(el('span', 'cr-ok', 'Connected'));
            else if (configured) {
                const link = el('a', 'cr-link', 'Connect');
                link.href = `/tiktok/connect?account=${encodeURIComponent(a.name)}`;
                link.target = '_blank';
                link.rel = 'noopener';
                row.append(link);
            }
            acc.append(row);
        }
        body.append(acc);
        if (!configured) body.append(el('div', 'cr-dim', setup));
        if (making) body.append(el('div', 'cr-dim', 'Alfred is making a video right now...'));
        const list = el('div', 'cr-videos');
        for (const v of [...videos].reverse()) {
            const item = el('div', `cr-video cr-${v.status}`);
            const head = el('div', 'cr-head');
            head.append(el('b', '', v.title + (v.part > 1 ? ` (part ${v.part})` : '')),
                        el('span', 'cr-dim', `@${v.account} · ${WORD[v.status] || v.status}${v.views ? ` · ${Number(v.views).toLocaleString()} views` : ''}`));
            item.append(head);
            if (v.src) {
                const player = el('video', 'cr-player');
                player.src = v.src;
                player.controls = true;
                player.preload = 'metadata';
                player.playsInline = true;
                item.append(player);
            }
            const facts = [v.score ? `Editor ${v.score}/10` : '', v.hook_score ? `Hook ${v.hook_score}/10` : '',
                           v.mood ? `Mood: ${v.mood}` : ''].filter(Boolean);
            if (facts.length) item.append(el('div', 'cr-facts', facts.join(' · ')));
            if (v.caption) item.append(el('div', 'cr-caption', `${v.caption} ${v.hashtags || ''}`));
            if (v.sound) item.append(el('div', 'cr-dim', `Sound to add: ${v.sound}`));
            if (v.pinned_comment) item.append(el('div', 'cr-dim', `Pin this comment: ${v.pinned_comment}`));
            if (v.error) item.append(el('div', 'cr-error', v.error));
            const note = el('div', 'cr-dim');
            const buttons = el('div', 'cr-buttons');
            if (['ready', 'failed_post'].includes(v.status)) {
                const ok = el('button', 'pop-action cr-approve', '✓ Post');
                ok.addEventListener('click', () => act(v.id, 'approve', note));
                const no = el('button', 'pop-action', '✕ Reject');
                no.addEventListener('click', () => act(v.id, 'reject', note));
                buttons.append(ok, no);
            }
            if (v.caption) buttons.append(copyButton(el, 'Copy caption', `${v.caption} ${v.hashtags || ''}`.trim()));
            if (v.pinned_comment) buttons.append(copyButton(el, 'Copy comment', v.pinned_comment));
            if (v.src) {
                const get = el('a', 'pop-action cr-link', 'Download');
                get.href = `${v.src}&download=1`;
                get.download = '';
                buttons.append(get);
            }
            item.append(buttons, note);
            list.append(item);
        }
        if (!videos.length) list.append(el('div', 'pop-empty', 'No videos yet. Say "make a TikTok video now".'));
        body.append(list);
    };
})();
