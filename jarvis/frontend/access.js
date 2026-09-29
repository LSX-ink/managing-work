// Accessibility (see access.py, docs/accessibility.md): big text, high contrast, reduced motion, captions, keyboard
// shortcuts, screen reader announcements, dyslexia-friendly font, speech speed and colour-blind colours.
// Settings are saved in this browser (per device) and applied as classes on <html> straight away, before first paint.
// access.css draws the classes; the "access-set" pop-up (from the voice tool or the ACCESS button) changes them.
(() => {
    const KEY = 'alfred-a11y';
    const DEFAULTS = { size: 'normal', contrast: false, motion: null, captions: false, dyslexia: false, cb: false, speech: 1 };
    const SIZES = ['normal', 'large', 'xl'];
    const SIZE_LABEL = { normal: 'Normal', large: 'Large', xl: 'Extra large' };
    const os = matchMedia('(prefers-reduced-motion: reduce)');
    const root = document.documentElement;
    const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));

    let settings = { ...DEFAULTS };
    try { settings = { ...DEFAULTS, ...(JSON.parse(localStorage.getItem(KEY) || '{}') || {}) }; } catch { /* private window */ }
    if (!SIZES.includes(settings.size)) settings.size = 'normal';
    settings.speech = clamp(Number(settings.speech) || 1, 0.5, 2);

    const motionOn = () => (settings.motion === null || settings.motion === undefined ? os.matches : !!settings.motion);

    function apply() {
        const c = root.classList;
        c.toggle('a11y-big', settings.size === 'large');
        c.toggle('a11y-xl', settings.size === 'xl');
        c.toggle('a11y-contrast', !!settings.contrast);
        c.toggle('a11y-motion', motionOn());
        c.toggle('a11y-captions', !!settings.captions);
        c.toggle('a11y-dyslexia', !!settings.dyslexia);
        c.toggle('a11y-cb', !!settings.cb);
        document.dispatchEvent(new Event('jarvis:motion'));   // hud.js stops the radar sweep and wolf streaming
        document.dispatchEvent(new Event('jarvis:theme'));    // and re-reads the colours
        window.dispatchEvent(new Event('resize'));            // folder stars move out of the way of bigger text
        requestAnimationFrame(() => document.querySelectorAll('#popups .popup').forEach((win) => {   // wider windows step back on screen
            const over = win.offsetLeft + win.offsetWidth - (innerWidth - 8);
            if (over > 0) win.style.left = `${Math.max(8, win.offsetLeft - over)}px`;
        }));
    }
    function save() { try { localStorage.setItem(KEY, JSON.stringify(settings)); } catch { /* private window */ } }
    apply();
    os.addEventListener('change', () => { if (settings.motion === null) apply(); });

    // ---- changing a setting ---------------------------------------------------------------------------------------

    const FLAGS = { high_contrast: 'contrast', reduce_motion: 'motion', captions: 'captions', dyslexia_font: 'dyslexia', colour_blind: 'cb' };

    function set(key, value) {
        settings[key] = value;
        save();
        apply();
    }
    function flag(action, mode) {
        const key = FLAGS[action];
        const now = key === 'motion' ? motionOn() : !!settings[key];
        set(key, mode === 'toggle' ? !now : mode !== 'off');
    }
    function bump(dir) {
        set('size', SIZES[clamp(SIZES.indexOf(settings.size) + dir, 0, SIZES.length - 1)]);
    }
    function setSpeed(value) {
        const step = 0.15;
        let rate = settings.speech;
        if (value === 'slower') rate -= step;
        else if (value === 'faster') rate += step;
        else if (value === 'normal') rate = 1;
        else if (Number(value)) rate = Number(value);
        set('speech', +clamp(rate, 0.5, 2).toFixed(2));
    }
    function reset() {
        settings = { ...DEFAULTS };
        save();
        apply();
    }
    function run(data) {   // one action from the voice tool
        const { action, value } = data || {};
        if (action === 'big_text') {
            if (value === 'bigger') bump(1);
            else if (value === 'smaller') bump(-1);
            else set('size', SIZES.includes(value) ? value : 'normal');
        } else if (FLAGS[action]) flag(action, value);
        else if (action === 'speech_speed') setSpeed(value);
        else if (action === 'reset') reset();
    }

    // ---- pop-ups: the settings window and the shortcuts list --------------------------------------------------------

    const openWindow = (card) => { if (window.jarvisPopup) window.jarvisPopup(card); };
    const openSettings = () => openWindow({ kind: 'access-set', id: 'access-settings', title: 'Accessibility', buttons: [], data: { action: 'show_settings' } });

    const SHORTCUTS = [
        ['Tab / Shift+Tab', 'Move to the next / previous button, link or pop-up control'],
        ['Enter or Space', 'Press the focused button'],
        ['Escape', 'Close the top pop-up window'],
        ['Alt+M or Ctrl+/', 'Turn the microphone on or off (pauses listening; skips what Alfred is saying)'],
        ['Alt+T', 'Jump to the typing box'],
        ['Alt+W', 'Jump into the top pop-up window'],
        ['Alt+A', 'Open the accessibility settings'],
        ['?', 'Show this list'],
    ];
    const openShortcuts = () => openWindow({ kind: 'table', id: 'access-shortcuts', title: 'Keyboard shortcuts', buttons: [],
                                            columns: ['Keys', 'What it does'], rows: SHORTCUTS });

    function panel(body, el) {
        const wrap = el('div', 'ax');
        const check = (label, on, change, note) => {
            const row = el('label', 'ax-row');
            const box = el('input');
            box.type = 'checkbox';
            box.checked = on;
            box.id = `ax-${label.toLowerCase().replace(/[^a-z]+/g, '-')}`;
            box.addEventListener('change', () => { change(box.checked); redraw(); });
            const text = el('span', 'ax-text', label);
            if (note) text.append(el('small', 'ax-note', note));
            row.append(box, text);
            return row;
        };
        const redraw = () => { const keep = document.activeElement && document.activeElement.id; body.replaceChildren(); panel(body, el); if (keep) { const again = body.querySelector(`#${keep}`); if (again) again.focus(); } };

        const size = el('fieldset', 'ax-size');
        size.append(el('legend', '', 'Text size'));
        SIZES.forEach((s) => {
            const label = el('label', 'ax-choice');
            const radio = el('input');
            Object.assign(radio, { type: 'radio', name: 'ax-size', id: `ax-size-${s}`, checked: settings.size === s });
            radio.addEventListener('change', () => { set('size', s); redraw(); });
            label.append(radio, el('span', '', SIZE_LABEL[s]));
            size.append(label);
        });
        wrap.append(size);

        const follows = settings.motion === null && os.matches ? 'On because your device asks for less motion' : '';
        wrap.append(
            check('High contrast', !!settings.contrast, (v) => set('contrast', v), 'Pure black and white, thicker borders'),
            check('Reduce motion', motionOn(), (v) => set('motion', v), follows || 'Stops the twinkling stars, the wolf and radar animation'),
            check('Captions', !!settings.captions, (v) => set('captions', v), 'Shows what Alfred says, and what you say, as text'),
            check('Dyslexia-friendly font', !!settings.dyslexia, (v) => set('dyslexia', v), 'Verdana-style letters with wider spacing'),
            check('Colour-blind safe colours', !!settings.cb, (v) => set('cb', v), 'Blue and orange instead of red and green'),
        );

        const speed = el('label', 'ax-speed');
        const range = el('input');
        Object.assign(range, { type: 'range', min: 0.5, max: 2, step: 0.05, value: settings.speech, id: 'ax-speech' });
        const out = el('output', 'ax-val', `${settings.speech.toFixed(2)}×`);
        range.addEventListener('input', () => { out.textContent = `${Number(range.value).toFixed(2)}×`; });
        range.addEventListener('change', () => { set('speech', Number(range.value)); });
        speed.append(el('span', '', "How fast Alfred speaks"), range, out);
        wrap.append(speed);

        const row = el('div', 'ax-buttons');
        const btn = (label, fn) => { const b = el('button', 'pop-action', label); b.type = 'button'; b.addEventListener('click', fn); return b; };
        row.append(btn('Hear Alfred', hear), btn('Keyboard shortcuts', openShortcuts), btn('Reset all', () => { reset(); redraw(); }));
        wrap.append(row);
        body.append(wrap);
    }

    function hear() {
        if (!('speechSynthesis' in window)) return;
        speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance('This is how fast I will speak.');
        const voice = window.jarvisVoice ? window.jarvisVoice.pick() : null;
        if (voice) { u.voice = voice; u.lang = voice.lang; }
        const prefs = window.jarvisVoice ? window.jarvisVoice.prefs() : {};
        u.rate = clamp((Number(prefs.rate) || 1) * settings.speech, 0.3, 2);
        u.pitch = Number(prefs.pitch) || 1;
        speechSynthesis.speak(u);
    }

    window.jarvisPopupKinds = window.jarvisPopupKinds || {};
    window.jarvisPopupKinds['access-set'] = (card, body, { el }) => {
        const data = card.data || {};
        if (data.action !== 'show_settings') run(data);
        if (data.action === 'show_shortcuts') openShortcuts();
        panel(body, el);
    };

    // ---- captions and screen reader announcements -----------------------------------------------------------------

    let bar, userLine, alfredLine, live, holdUntil = 0, name = 'Alfred';

    function announce(text) {
        if (!live || !text) return;
        const item = document.createElement('div');
        item.textContent = text;
        live.append(item);
        while (live.children.length > 6) live.firstChild.remove();
        setTimeout(() => item.remove(), 15000);
    }

    function caption(who, text) {
        if (!bar) return;
        if (who === 'user') { userLine.textContent = `You: ${text}`; alfredLine.textContent = ''; }
        else alfredLine.textContent = text;
        bar.classList.add('on');
        alfredLine.scrollTop = alfredLine.scrollHeight;
        holdUntil = Date.now() + Math.max(5000, text.length * 70);
    }

    function build() {
        live = document.createElement('div');
        live.id = 'a11y-live';
        live.className = 'ax-sr';
        live.setAttribute('role', 'log');
        live.setAttribute('aria-live', 'polite');
        live.setAttribute('aria-relevant', 'additions');
        bar = document.createElement('div');
        bar.id = 'a11y-captions';
        bar.setAttribute('aria-hidden', 'true');   // the live region already reads everything out
        userLine = document.createElement('div');
        userLine.className = 'cap-user';
        alfredLine = document.createElement('div');
        alfredLine.className = 'cap-alfred';
        bar.append(userLine, alfredLine);

        const fab = document.createElement('button');   // plain screens have no top bar, so they get a small button
        fab.id = 'access-fab';
        fab.type = 'button';
        fab.hidden = true;
        fab.textContent = 'ACCESS';
        fab.setAttribute('aria-label', 'Accessibility settings');
        fab.setAttribute('aria-haspopup', 'dialog');
        document.body.append(live, bar, fab);
        fab.addEventListener('click', openSettings);
        const chip = document.getElementById('hud-access');
        if (chip) chip.addEventListener('click', openSettings);
        document.addEventListener('jarvis:config', (e) => {
            fab.hidden = document.body.classList.contains('hud');
            if (e.detail && e.detail.name) name = e.detail.name;
        });

        document.addEventListener('jarvis:line', (e) => {
            const { who, text } = e.detail;
            if (who === 'user') caption('user', text);
            else if (!(window.jarvisIsSpeaking && window.jarvisIsSpeaking())) caption('alfred', text);
            if (who !== 'user') announce(`${name}: ${text}`);
        });
        document.addEventListener('jarvis:speak', (e) => { if (e.detail.text) caption('alfred', e.detail.text); });
        document.addEventListener('jarvis:popup', (e) => {
            const card = e.detail || {};
            if (card.kind !== 'close' && card.title) announce(`Window opened: ${card.title}.`);
        });
        setInterval(() => {
            const busy = window.jarvisIsSpeaking && window.jarvisIsSpeaking();
            if (bar.classList.contains('on') && !busy && Date.now() > holdUntil) bar.classList.remove('on');
        }, 500);
    }

    // ---- keyboard ---------------------------------------------------------------------------------------------------

    function keys(e) {
        const typing = e.target.closest && e.target.closest('input:not([type=checkbox],[type=radio],[type=range],[type=button]), textarea, select, [contenteditable=""], [contenteditable="true"]');
        if ((e.altKey && e.code === 'KeyM') || (e.ctrlKey && !e.altKey && e.code === 'Slash')) {
            e.preventDefault();
            const orb = document.getElementById('orb');
            if (orb) orb.click();
        } else if (e.altKey && e.code === 'KeyA') {
            e.preventDefault();
            openSettings();
        } else if (e.altKey && e.code === 'KeyT') {
            e.preventDefault();
            const box = document.getElementById('type-input');
            if (box) box.focus();
        } else if (e.altKey && e.code === 'KeyW') {
            e.preventDefault();
            const wins = [...document.querySelectorAll('#popups .popup')].sort((a, b) => b.style.zIndex - a.style.zIndex);
            if (wins[0]) wins[0].focus();
        } else if (e.key === '?' && !e.defaultPrevented && !typing && !e.ctrlKey && !e.altKey && !e.metaKey) {   // the HUD's own list (hudplus.js) takes it when present
            e.preventDefault();
            openShortcuts();
        }
    }

    window.jarvisAccess = {
        get: () => ({ ...settings }),
        speechRate: () => settings.speech,
        run, reset, openSettings, openShortcuts,
    };
    addEventListener('keydown', keys);
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', build);
    else build();
})();
