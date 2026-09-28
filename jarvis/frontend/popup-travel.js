// Travel pop-up kind (travel_guide.py): a phrasebook table with a Speak button on every row. Speak uses the
// browser's own voice for that language when it has one, otherwise it asks Alfred to say the phrase.
(() => {
    const kinds = window.jarvisPopupKinds = window.jarvisPopupKinds || {};

    function voiceFor(lang) {
        if (!('speechSynthesis' in window)) return null;
        const voices = speechSynthesis.getVoices();
        const short = lang.split('-')[0].toLowerCase();
        return voices.find((v) => v.lang === lang) || voices.find((v) => v.lang.toLowerCase().startsWith(short)) || null;
    }

    kinds['travel-phrases'] = (card, body, { el, ask }) => {
        const { lang = '', rows = [] } = card.data || {};
        if (!rows.length) { body.append(el('div', 'pop-empty', 'No phrases.')); return; }
        const wrap = el('div', 'pop-table tr-phrases');
        const table = el('table');
        const head = el('tr');
        ['English', 'Phrase', ''].forEach((c) => head.append(el('th', '', c)));
        const thead = el('thead');
        thead.append(head);
        const tbody = el('tbody');
        for (const row of rows) {
            const tr = el('tr');
            tr.append(el('td', 'tr-en', row.en));
            const cell = el('td', 'tr-phrase');
            cell.append(el('div', '', row.phrase));
            if (row.sound) cell.append(el('div', 'tr-sound', row.sound));
            const speak = el('button', 'tr-speak', 'Speak');
            speak.type = 'button';
            speak.title = `Hear "${row.en}"`;
            speak.addEventListener('click', () => {
                const voice = voiceFor(lang);
                if (!voice) { ask(row.say); return; }
                speechSynthesis.cancel();
                const u = new SpeechSynthesisUtterance(row.phrase);
                u.lang = lang;
                u.voice = voice;
                u.rate = 0.85;
                speechSynthesis.speak(u);
            });
            const act = el('td');
            act.append(speak);
            tr.append(cell, act);
            tbody.append(tr);
        }
        table.append(thead, tbody);
        wrap.append(table);
        body.append(wrap);
    };
})();
