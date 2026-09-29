// Tech helper pop-up kinds (techhelp_store.py, techhelp_secure.py).
//   techhelp-steps: a guide or checklist with a progress bar, tick boxes and the current step opened out.
//   techhelp-meter: a password strength meter with the tips. The password itself is never sent to the page.
(() => {
    const kinds = window.jarvisPopupKinds = window.jarvisPopupKinds || {};

    kinds['techhelp-steps'] = (card, body, { el, ask }) => {
        const { steps = [], current = null, done = 0, total = 0 } = card.data || {};
        const bar = el('div', 'th-bar');
        const fill = el('div', 'th-fill');
        fill.style.width = total ? `${Math.round((done / total) * 100)}%` : '0%';
        bar.append(fill);
        body.append(bar, el('div', 'th-count', `${done} of ${total} steps done`));
        const ul = el('ul', 'pop-list th-steps');
        for (const step of steps) {
            const isCurrent = step.n - 1 === current;
            const li = el('li', `${step.done ? 'done' : ''} ${isCurrent ? 'th-current' : ''}`.trim());
            const box = el('input');
            box.type = 'checkbox';
            box.checked = step.done;
            box.setAttribute('aria-label', `Step ${step.n}: ${step.title}`);
            box.addEventListener('change', () => { li.classList.toggle('done', box.checked); ask(step.say); });
            const text = el('div', 'th-text');
            text.append(el('span', 'pop-item', `${step.n}. ${step.title}`));
            if (isCurrent) text.append(el('div', 'th-detail', step.detail));
            li.append(box, text);
            ul.append(li);
        }
        body.append(ul);
        if (current === null && total) body.append(el('div', 'th-finished', 'All done.'));
    };

    // Password strength, measured here in the browser: the password is never sent to Alfred or saved.
    const LEET = { 0: 'o', 1: 'l', 3: 'e', 4: 'a', 5: 's', '@': 'a', $: 's', '!': 'i' };
    const ORDER = 'abcdefghijklmnopqrstuvwxyz0123456789';
    function strength(pw, common, walks) {
        let pool = 0;
        if (/[a-z]/.test(pw)) pool += 26;
        if (/[A-Z]/.test(pw)) pool += 26;
        if (/\d/.test(pw)) pool += 10;
        if (/[ -\/:-@\[-`{-~]/.test(pw)) pool += 33;
        if (/[^\x00-\x7f]/.test(pw)) pool += 100;
        let bits = pw.length * Math.log2(Math.max(pool, 10));
        const low = pw.toLowerCase();
        const plain = [...low].map((c) => LEET[c] || c).join('');
        const stem = low.replace(/[^a-z]+$/, '') || plain;
        const notes = [];
        if ([low, plain, stem, [...stem].map((c) => LEET[c] || c).join('')].some((w) => common.has(w))) {
            bits = Math.min(bits, 10 + 3 * Math.max(0, pw.length - stem.length));
            notes.push("It's a very common password or a common word with tweaks. Attackers try these first.");
        } else if ([...common].some((w) => w.length >= 5 && plain.includes(w))) {
            bits -= 12;
            notes.push('It contains a very common word.');
        }
        let repeats = 0;
        for (let i = 1; i < pw.length; i++) if (pw[i] === pw[i - 1]) repeats++;
        if (repeats) { bits -= 3 * repeats; notes.push('Repeated characters make it easier to guess.'); }
        let runs = 0;
        for (let i = 0; i + 2 < low.length; i++) {
            const a = [0, 1, 2].map((k) => ORDER.indexOf(low[i + k]));
            if (a.every((x) => x >= 0) && a[1] - a[0] === a[2] - a[1] && Math.abs(a[1] - a[0]) === 1) runs++;
        }
        if (runs) { bits -= 6 * runs; notes.push('Runs like abc or 123 are guessed early.'); }
        if (walks.some((w) => low.includes(w))) { bits -= 12; notes.push('Keyboard patterns such as qwerty are well known.'); }
        const years = pw.match(/(?:19|20)\d\d/g) || [];
        if (years.length) { bits -= 5 * years.length; notes.push('Years and birthdays are easy to guess.'); }
        if (new Set(pw).size <= 2 && pw.length > 3) bits = Math.min(bits, 6);
        if (pw.length < 12) notes.push('Make it at least 12 characters; three or four random words joined together works well.');
        return { bits: Math.max(bits, 0), notes };
    }
    const label = (b) => (b < 28 ? 'very weak' : b < 40 ? 'weak' : b < 60 ? 'fair' : b < 80 ? 'strong' : 'very strong');
    function crackTime(bits, rate) {
        const s = 2 ** Math.min(bits, 200) / 2 / rate;
        for (const [size, name] of [[3.15e9, 'centuries'], [3.15e7, 'years'], [86400, 'days'], [3600, 'hours'], [60, 'minutes']]) {
            if (s >= size) {
                const n = s / size;
                return name === 'centuries' && n > 1000 ? 'more than a thousand centuries' : `about ${Math.round(n).toLocaleString()} ${name}`;
            }
        }
        return s < 1 ? 'less than a minute' : `about ${Math.round(s)} seconds`;
    }
    window.jarvisPasswordStrength = strength;

    kinds['techhelp-meter'] = (card, body, { el }) => {
        const { common = [], walks = [], rate = 1e10 } = card.data || {};
        const words = new Set(common);
        const input = el('input', 'th-pw');
        Object.assign(input, { type: 'password', placeholder: 'Type a password to check', autocomplete: 'off' });
        const bar = el('div', 'th-bar th-meter');
        const fill = el('div', 'th-fill');
        bar.append(fill);
        const head = el('div', 'th-label', '');
        const info = el('div', 'th-count', '');
        const ul = el('ul', 'th-tips');
        body.append(input, bar, head, info, ul, el('div', 'th-count', 'Checked in this window only. It is never sent to Alfred or saved.'));
        const update = () => {
            const pw = input.value;
            ul.replaceChildren();
            if (!pw) { fill.style.width = '0'; head.textContent = ''; info.textContent = ''; return; }
            const { bits, notes } = strength(pw, words, walks);
            const name = label(bits);
            fill.className = `th-fill th-${name.replace(/\s+/g, '-')}`;
            fill.style.width = `${Math.max(4, Math.min(100, Math.round(bits / 80 * 100)))}%`;
            head.textContent = `${name} · about ${Math.round(bits)} bits`;
            info.textContent = `${pw.length} characters. A fast attacker could crack it in ${crackTime(bits, rate)}.`;
            for (const tip of [...notes, 'Use a different password for every account, ideally from a password manager.']) ul.append(el('li', '', tip));
        };
        input.addEventListener('input', update);
        setTimeout(() => input.focus(), 50);
    };
})();
