// Alfred's voice picker (voice.py): lists this browser's voices, most natural first, with Try and Use buttons,
// plus speed and pitch sliders. The choice is saved in this browser; main.js reads it when Alfred speaks.
(() => {
    window.jarvisPopupKinds = window.jarvisPopupKinds || {};
    const SAMPLE = 'Good evening, sir. Standing by for orders.';
    const load = () => (window.jarvisVoice ? window.jarvisVoice.prefs() : {});
    const save = (prefs) => { try { localStorage.setItem('alfred-voice', JSON.stringify(prefs)); } catch { /* private window */ } };
    const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));

    function sayWith(voice, prefs) {
        if (!('speechSynthesis' in window)) return;
        speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(SAMPLE);
        if (voice) { u.voice = voice; u.lang = voice.lang; }
        u.rate = Number(prefs.rate) || 1;
        u.pitch = Number(prefs.pitch) || 1;
        speechSynthesis.speak(u);
    }

    function adjust(action) {
        const prefs = load();
        const rate = Number(prefs.rate) || 1, pitch = Number(prefs.pitch) || 1;
        if (action === 'faster') prefs.rate = clamp(+(rate + 0.1).toFixed(2), 0.6, 1.6);
        if (action === 'slower') prefs.rate = clamp(+(rate - 0.1).toFixed(2), 0.6, 1.6);
        if (action === 'deeper') prefs.pitch = clamp(+(pitch - 0.1).toFixed(2), 0.5, 1.5);
        if (action === 'higher') prefs.pitch = clamp(+(pitch + 0.1).toFixed(2), 0.5, 1.5);
        if (action === 'reset') { delete prefs.rate; delete prefs.pitch; }
        if (action === 'soldier') { delete prefs.name; delete prefs.rate; delete prefs.pitch; }  // back to the deep British default
        save(prefs);
    }

    window.jarvisPopupKinds['voice-picker'] = (card, body, { el }) => {
        const data = card.data || {};
        if (data.action && data.action !== 'choose') adjust(data.action);
        const prefs = load();
        const wrap = el('div', 'vp');
        body.append(wrap);
        if (data.server_voice) {
            wrap.append(el('p', 'vp-note', 'Alfred is speaking with the ElevenLabs voice. These browser voices are only used without ElevenLabs.'));
        }
        if (!('speechSynthesis' in window)) {
            wrap.append(el('p', 'vp-note', 'This browser has no built-in voices.'));
            return;
        }

        const sliders = el('div', 'vp-sliders');
        const slider = (label, key, min, max) => {
            const row = el('label', 'vp-slider');
            const input = el('input');
            Object.assign(input, { type: 'range', min, max, step: 0.05, value: Number(prefs[key]) || 1 });
            const out = el('span', 'vp-val', (Number(prefs[key]) || 1).toFixed(2));
            input.addEventListener('input', () => { out.textContent = Number(input.value).toFixed(2); });
            input.addEventListener('change', () => { const p = load(); p[key] = Number(input.value); save(p); });
            row.append(el('span', '', label), input, out);
            return row;
        };
        sliders.append(slider('Speed', 'rate', 0.6, 1.6), slider('Pitch', 'pitch', 0.5, 1.5));
        wrap.append(sliders);

        const tip = el('p', 'vp-note', 'Voices marked NATURAL sound the most human. For the best free ones, open Alfred in Microsoft Edge.');
        const list = el('ul', 'vp-list');
        const allBox = el('label', 'vp-all');
        const all = el('input');
        all.type = 'checkbox';
        allBox.append(all, el('span', '', ' Show every language'));
        wrap.append(tip, allBox, list);

        function draw() {
            if (!body.isConnected && list.childNodes.length) return;
            const voices = speechSynthesis.getVoices();
            const lang = window.jarvisVoice ? window.jarvisVoice.lang() : 'en-GB';
            const ranked = window.jarvisVoice ? window.jarvisVoice.rank(voices, lang) : voices;
            const shown = all.checked ? ranked.concat(voices.filter((v) => !ranked.includes(v))) : ranked;
            const current = window.jarvisVoice ? window.jarvisVoice.pick() : null;
            list.replaceChildren();
            if (!shown.length) { list.append(el('li', 'vp-note', 'Loading voices…')); return; }
            for (const v of shown) {
                const li = el('li', 'vp-row' + (current && current.name === v.name ? ' vp-current' : ''));
                const name = el('span', 'vp-name', v.name);
                const meta = el('span', 'vp-meta', v.lang + (window.jarvisVoice && window.jarvisVoice.natural(v) ? ' · NATURAL' : ''));
                const tryBtn = el('button', 'vp-btn', 'Try');
                tryBtn.type = 'button';
                tryBtn.addEventListener('click', () => sayWith(v, load()));
                const use = el('button', 'vp-btn', current && current.name === v.name ? 'In use' : 'Use');
                use.type = 'button';
                use.addEventListener('click', () => { const p = load(); p.name = v.name; save(p); sayWith(v, p); draw(); });
                li.append(el('span', 'vp-text'), tryBtn, use);
                li.firstChild.append(name, meta);
                list.append(li);
            }
        }
        all.addEventListener('change', draw);
        draw();
        // Chrome fills the voice list a moment after the page loads.
        if ('onvoiceschanged' in speechSynthesis) speechSynthesis.addEventListener('voiceschanged', draw, { once: true });
        if (data.action && data.action !== 'choose') sayWith(window.jarvisVoice && window.jarvisVoice.pick(), prefs);
    };
})();
