// J.A.R.V.I.S. frontend: speech in (Web Speech API), speech out (server MP3 or browser voice).
const orb = document.getElementById('orb');
const statusEl = document.getElementById('status');
const transcript = document.getElementById('transcript');
const typeForm = document.getElementById('type-form');
const typeInput = document.getElementById('type-input');
const confirmBox = document.getElementById('confirm');
const confirmSteps = document.getElementById('confirm-steps');
const alertsBox = document.getElementById('alerts');
const alertsList = document.getElementById('alerts-list');

let config = { speechLang: 'en-GB', serverVoice: false, name: 'Jarvis' };

// UI text by language code; anything missing falls back to English.
const STRINGS = {
    en: {
        wake: 'Click the orb to wake {name}.',
        reconnecting: 'Connection lost. Reconnecting…',
        thinking: 'Thinking…',
        listening: 'Listening…',
        listeningWake: 'Say "{name}" to talk to me…',
        paused: 'Paused. Click the orb to resume.',
        micBlocked: 'Microphone blocked. You can still type below.',
        noRecognition: 'Voice input needs Chrome or Edge. Type below instead.',
        noVoice: 'Your browser has no voice for this language. Set ELEVENLABS_API_KEY to hear replies.',
        placeholder: '…or type to {name}',
        you: 'You',
        confirmTitle: '{name} would like to:',
        allow: 'Allow',
        allowAll: 'Allow for this task',
        deny: 'Deny',
        waitingOk: 'Waiting for your OK…',
        notifications: 'Notifications',
        remove: 'Remove',
        email: 'EMAIL',
        timer: 'TIMER',
        call: 'CALL',
        phone: 'PHONE',
        nowPlaying: 'NOW PLAYING',
    },
    af: {
        wake: 'Klik op die bol om {name} wakker te maak.',
        reconnecting: 'Verbinding verloor. Koppel weer…',
        thinking: 'Dink…',
        listening: 'Luister…',
        listeningWake: 'Sê "{name}" om met my te praat…',
        paused: 'Onderbreek. Klik op die bol om voort te gaan.',
        micBlocked: 'Mikrofoon geblokkeer. Jy kan steeds hieronder tik.',
        noRecognition: 'Steminvoer werk net in Chrome of Edge. Tik eerder hieronder.',
        noVoice: 'Jou blaaier het geen Afrikaanse stem nie. Stel ELEVENLABS_API_KEY om antwoorde te hoor.',
        placeholder: '…of tik vir {name}',
        you: 'Jy',
        confirmTitle: '{name} wil graag:',
        allow: 'Laat toe',
        allowAll: 'Laat toe vir hierdie taak',
        deny: 'Weier',
        waitingOk: 'Wag vir jou toestemming…',
        notifications: 'Kennisgewings',
        remove: 'Verwyder',
        email: 'E-POS',
        timer: 'TYDHOUER',
        call: 'OPROEP',
        phone: 'FOON',
        nowPlaying: 'SPEEL NOU',
    },
};

function t(key) {
    const lang = config.speechLang.split('-')[0].toLowerCase();
    const text = (STRINGS[lang] || STRINGS.en)[key] || STRINGS.en[key];
    return text.replace('{name}', config.name);
}

// Best browser voice for the configured language: exact match (en-GB), then same language (en),
// preferring a male voice within each since both butlers are men.
const MALE_VOICE = /\b(male|daniel|george|arthur|ryan|oliver|thomas|guy)\b/i;

function pickVoice() {
    const want = config.speechLang.toLowerCase().replace('_', '-');
    const norm = (v) => v.lang.toLowerCase().replace('_', '-');
    const voices = speechSynthesis.getVoices();
    const exact = voices.filter((v) => norm(v) === want);
    const sameLang = voices.filter((v) => norm(v).split('-')[0] === want.split('-')[0]);
    const male = (list) => list.find((v) => MALE_VOICE.test(v.name) && !/female/i.test(v.name));
    return male(exact) || exact[0] || male(sameLang) || sameLang[0] || null;
}
let ws = null;
let started = false;   // first click wakes Jarvis (and unlocks audio playback)
let paused = false;    // user paused the microphone
let busy = false;      // waiting for the server to finish a turn
let speaking = false;
let currentAudio = null;
const queue = [];

const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let listening = false;
let stopper = null;    // listens for "stop" while Jarvis speaks
let lastSpokeAt = 0;   // when Jarvis last finished speaking (follow-ups need no name)
const FOLLOW_UP_MS = 20000;
const STOP_WORDS = /^(?:(?:ok(?:ay)?|alfred|jarvis) )?(?:stop|quiet|be quiet|shush|hush|enough|that's enough|shut up)(?: (?:alfred|jarvis))?[.!]?$/i;
let wakeOnly = null;   // only answer when called by name; null until /config arrives
try { const w = localStorage.getItem('jarvis-wake'); if (w !== null) wakeOnly = w === 'on'; } catch (e) { /* private window */ }

function setWakeOnly(on) {
    wakeOnly = !!on;
    try { localStorage.setItem('jarvis-wake', wakeOnly ? 'on' : 'off'); } catch (e) { /* private window */ }
    if (listening) setState('listening', t(wakeOnly ? 'listeningWake' : 'listening'));
}

function calledByName(text) {
    const names = [config.name, 'jarvis', 'alfred'].map((n) => n.toLowerCase());
    return names.some((n) => new RegExp(`\\b${n}\\b`, 'i').test(text));
}

function setState(state, text = '') {
    orb.className = state;
    statusEl.textContent = text;
}

function addLine(who, text) {
    const div = document.createElement('div');
    div.className = who;
    div.textContent = `${who === 'user' ? t('you') : config.name}: ${text}`;
    transcript.appendChild(div);
    transcript.scrollTop = transcript.scrollHeight;
}

// Where the chat sits: a corner ("bottom-left" etc.) or the centre column. Remembered in this browser.
const CHAT_CORNERS = ['top-left', 'top-right', 'bottom-left', 'bottom-right'];
function placeChat(corner) {
    if (CHAT_CORNERS.includes(corner)) document.body.dataset.chat = corner;
    else delete document.body.dataset.chat;
    try { localStorage.setItem('jarvis-chat', CHAT_CORNERS.includes(corner) ? corner : 'centre'); } catch (e) { /* private window */ }
    transcript.scrollTop = transcript.scrollHeight;
    window.dispatchEvent(new Event('resize'));  // the folder stars move out of its way
}
try {
    const saved = localStorage.getItem('jarvis-chat');
    if (CHAT_CORNERS.includes(saved)) document.body.dataset.chat = saved;
} catch (e) { /* private window */ }

// ---- WebSocket --------------------------------------------------------------

// A timer's chime: three soft rising beeps, made in the browser (no sound file needed).
function chime() {
    try {
        const audio = new (window.AudioContext || window.webkitAudioContext)();
        [0, 0.35, 0.7].forEach((at, i) => {
            const osc = audio.createOscillator(), gain = audio.createGain();
            osc.frequency.value = 660 + i * 220;
            gain.gain.setValueAtTime(0.0001, audio.currentTime + at);
            gain.gain.exponentialRampToValueAtTime(0.3, audio.currentTime + at + 0.02);
            gain.gain.exponentialRampToValueAtTime(0.0001, audio.currentTime + at + 0.3);
            osc.connect(gain).connect(audio.destination);
            osc.start(audio.currentTime + at);
            osc.stop(audio.currentTime + at + 0.32);
        });
        setTimeout(() => audio.close(), 1500);
    } catch (e) { /* no audio */ }
}

function connect(onOpen) {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${proto}://${location.host}/ws`);
    ws.onopen = onOpen;
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'say') {
            if (!msg.quiet) addLine('jarvis', msg.text);
            queue.push(msg);
            playNext();
        } else if (msg.type === 'alerts') {
            alertsList.replaceChildren();
            msg.items.forEach(addAlert);
        } else if (msg.type === 'alert') {
            addAlert(msg);
        } else if (msg.type === 'dismissed') {
            removeAlert(msg.id);
        } else if (msg.type === 'nowplaying') {
            showNowPlaying(msg);
        } else if (msg.type === 'note') {
            addLine('jarvis', msg.text);  // shown, not spoken
        } else if (msg.type === 'chime') {
            chime();
        } else if (msg.type === 'wakeword') {
            setWakeOnly(msg.on);
        } else if (msg.type === 'chat') {
            placeChat(msg.corner);
        } else if (msg.type === 'memory') {
            document.dispatchEvent(new CustomEvent('jarvis:memory', { detail: msg }));  // memory.js opens the folder
        } else if (msg.type === 'popup') {
            document.dispatchEvent(new CustomEvent('jarvis:popup', { detail: msg.card }));  // popup.js draws it
        } else if (msg.type === 'confirm') {
            showConfirm(msg);
        } else if (msg.type === 'done') {
            busy = false;
            maybeListen();
        }
    };
    ws.onclose = () => {
        busy = false;
        confirmBox.hidden = true;
        setState('idle', t('reconnecting'));
        setTimeout(() => connect(() => { setState('idle', ''); maybeListen(); }), 2000);
    };
}

function send(payload) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    busy = true;
    stopListening();
    setState('thinking', t('thinking'));
    ws.send(JSON.stringify(payload));
}

// ---- Notifications (delivery emails, calls) ---------------------------------

function addAlert(item) {
    const li = document.createElement('li');
    li.dataset.id = item.id;
    const part = (cls, text) => {
        const span = document.createElement('span');
        span.className = cls;
        span.textContent = text;
        return span;
    };
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.textContent = '×';
    remove.title = t('remove');
    remove.setAttribute('aria-label', `${t('remove')}: ${item.text}`);
    remove.addEventListener('click', () => {
        removeAlert(item.id);
        if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'dismiss', id: item.id }));
    });
    li.append(part('kind', STRINGS.en[item.kind] ? t(item.kind) : item.kind), part('text', item.text), part('at', item.at || ''), remove);
    alertsList.prepend(li);   // newest at the top
    alertsList.scrollTop = 0;
    alertHold = ALERT_HOLD_TICKS;
    alertsBox.hidden = false;
}

function removeAlert(id) {
    const li = alertsList.querySelector(`li[data-id="${Number(id)}"]`);
    if (li) li.remove();
    alertsBox.hidden = !alertsList.children.length;
}

// Scroll slowly down through the notifications, rest at each end, then start again from the top.
// Pauses while the mouse or keyboard is on the list, and stays still for people who prefer less motion.
const ALERT_HOLD_TICKS = 60;   // 3 seconds at 50 ms per tick
let alertHold = ALERT_HOLD_TICKS;
let alertsPaused = false;
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
alertsList.addEventListener('mouseenter', () => { alertsPaused = true; });
alertsList.addEventListener('mouseleave', () => { alertsPaused = false; });
alertsList.addEventListener('focusin', () => { alertsPaused = true; });
alertsList.addEventListener('focusout', () => { alertsPaused = false; });
setInterval(() => {
    const max = alertsList.scrollHeight - alertsList.clientHeight;
    if (alertsPaused || reduceMotion || max <= 0) return;
    if (alertHold > 0) { alertHold--; return; }
    if (alertsList.scrollTop >= max - 1) {
        alertsList.scrollTop = 0;
        alertHold = ALERT_HOLD_TICKS;
        return;
    }
    alertsList.scrollTop += 1;   // about 20 pixels a second
    if (alertsList.scrollTop >= max - 1) alertHold = ALERT_HOLD_TICKS;
}, 50);

// ---- Now playing pop-up ------------------------------------------------------

const NOW_PLAYING_MS = 8000;   // how long the card stays before sliding away
let nowPlayingTimer = null;

function showNowPlaying(song) {
    const box = document.getElementById('np-popup');
    const art = document.getElementById('np-art');
    document.getElementById('np-label').textContent = t('nowPlaying');
    document.getElementById('np-title').textContent = song.title;
    document.getElementById('np-artist').textContent = [song.artist, song.album].filter(Boolean).join(' · ');
    art.hidden = !song.art;
    if (song.art) art.src = song.art;
    box.hidden = false;
    clearTimeout(nowPlayingTimer);
    nowPlayingTimer = setTimeout(() => { box.hidden = true; }, NOW_PLAYING_MS);
}

// ---- Approving mouse/keyboard actions ---------------------------------------

function showConfirm(msg) {
    stopListening();
    document.getElementById('confirm-title').textContent = t('confirmTitle');
    document.getElementById('confirm-allow').textContent = t('allow');
    document.getElementById('confirm-allow-all').textContent = t('allowAll');
    document.getElementById('confirm-deny').textContent = t('deny');
    confirmSteps.replaceChildren(...msg.steps.map((step) => {
        const li = document.createElement('li');
        li.textContent = step;
        return li;
    }));
    confirmBox.dataset.id = msg.id;
    confirmBox.hidden = false;
    setState('thinking', t('waitingOk'));
}

confirmBox.addEventListener('click', (event) => {
    const answer = event.target.dataset && event.target.dataset.answer;
    if (!answer || !ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: 'confirm_reply', id: Number(confirmBox.dataset.id), answer }));
    confirmBox.hidden = true;
    setState('thinking', t('thinking'));
});

// ---- Speech output ----------------------------------------------------------

function playNext() {
    if (speaking) return;
    const msg = queue.shift();
    if (!msg) {
        maybeListen();
        return;
    }
    speaking = true;
    stopListening();
    setState('speaking');
    startStopper();
    const finish = () => { speaking = false; lastSpokeAt = Date.now(); stopStopper(); playNext(); };

    if (msg.audio) {
        const bytes = Uint8Array.from(atob(msg.audio), (c) => c.charCodeAt(0));
        const url = URL.createObjectURL(new Blob([bytes], { type: 'audio/mpeg' }));
        const audio = new Audio(url);
        currentAudio = audio;
        audio.onended = audio.onerror = () => { URL.revokeObjectURL(url); finish(); };
        audio.play().catch(finish);
    } else if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(msg.text);
        utterance.lang = config.speechLang;
        const voice = pickVoice();
        if (voice) {
            utterance.voice = voice;
        } else if (speechSynthesis.getVoices().length) {
            statusEl.textContent = t('noVoice');
        }
        utterance.onend = utterance.onerror = finish;
        speechSynthesis.speak(utterance);
    } else {
        finish();
    }
}

// ---- Speech input -----------------------------------------------------------

if (Recognition) {
    recognition = new Recognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.onresult = (event) => {
        const result = event.results[event.results.length - 1];
        const text = result[0].transcript.trim();
        if (result.isFinal && text && wakeOnly && !calledByName(text) && Date.now() - lastSpokeAt > FOLLOW_UP_MS) {
            return;  // not for Jarvis: he waits to be called by name
        }
        if (result.isFinal && text) {
            addLine('user', text);
            send({ text });
        }
    };
    recognition.onend = () => {
        listening = false;
        setTimeout(maybeListen, 250);
    };
    recognition.onerror = (event) => {
        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
            paused = true;
            setState('idle', t('micBlocked'));
        }
    };
}

function maybeListen() {
    if (!started || paused || busy || speaking || queue.length || listening) return;
    if (!recognition) {
        setState('idle', t('noRecognition'));
        return;
    }
    try {
        recognition.lang = config.speechLang;
        recognition.start();
        listening = true;
        setState('listening', t(wakeOnly ? 'listeningWake' : 'listening'));
    } catch (e) { /* already started */ }
}

// While Jarvis speaks, a second recogniser listens only for "stop", "quiet", "that's enough"…
function startStopper() {
    if (!Recognition || paused || !started) return;
    if (!stopper) {
        stopper = new Recognition();
        stopper.continuous = true;
        stopper.interimResults = true;
        stopper.onresult = (event) => {
            for (let i = event.resultIndex; i < event.results.length; i++) {
                if (STOP_WORDS.test(event.results[i][0].transcript.trim())) {
                    skipSpeech();
                    return;
                }
            }
        };
        stopper.onend = () => { stopper.running = false; if (speaking) setTimeout(startStopper, 200); };
        stopper.onerror = () => {};
    }
    if (stopper.running) return;
    try {
        stopper.lang = config.speechLang;
        stopper.start();
        stopper.running = true;
    } catch (e) { /* already started */ }
}

function stopStopper() {
    if (stopper && stopper.running) stopper.abort();
    if (stopper) stopper.running = false;
}

// Stop talking now and drop anything still queued.
function skipSpeech() {
    queue.length = 0;
    if ('speechSynthesis' in window) speechSynthesis.cancel();
    if (currentAudio) currentAudio.pause();
    speaking = false;
    lastSpokeAt = Date.now();
    stopStopper();
    maybeListen();
}

function stopListening() {
    if (listening && recognition) recognition.abort();
    listening = false;
}

// ---- Controls ---------------------------------------------------------------

orb.addEventListener('click', () => {
    if (!started) {
        started = true;
        connect(() => send({ type: 'activate' }));
        return;
    }
    if (speaking) {
        skipSpeech();  // tap while speaking: skip the rest of what Jarvis is saying
        return;
    }
    paused = !paused;
    if (paused) {
        stopListening();
        setState('idle', t('paused'));
    } else {
        maybeListen();
    }
});

// Pop-up buttons and list items send their line to Alfred as if typed.
window.jarvisAsk = (text) => {
    if (!started) {
        started = true;
        connect(() => { addLine('user', text); send({ text }); });
        return;
    }
    addLine('user', text);
    send({ text });
};

typeForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const text = typeInput.value.trim();
    if (!text) return;
    typeInput.value = '';
    if (!started) {
        started = true;
        connect(() => { addLine('user', text); send({ text }); });
        return;
    }
    addLine('user', text);
    send({ text });
});

function applyLanguage() {
    document.documentElement.lang = config.speechLang;
    document.title = config.name === 'Jarvis' ? 'J.A.R.V.I.S.' : config.name;
    typeInput.placeholder = t('placeholder');
    document.getElementById('alerts-title').textContent = t('notifications');
    typeInput.setAttribute('aria-label', `Message to ${config.name}`);
    if (!started) statusEl.textContent = t('wake');
}

fetch('/config').then((r) => r.json()).then((c) => {
    config = c;
    if (wakeOnly === null) wakeOnly = !!config.wakeWord;
    applyLanguage();
    // "hud" or a colour variant such as "hud-gold": both classes go on the page
    if (config.theme && config.theme.startsWith('hud')) document.body.classList.add('hud', config.theme);
    document.dispatchEvent(new CustomEvent('jarvis:config', { detail: config }));
}).catch(() => {});
// Chrome loads its voice list asynchronously; touching it early starts the load.
if ('speechSynthesis' in window) speechSynthesis.getVoices();
