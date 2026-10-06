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
        willSend: 'Reconnecting… I\'ll answer that as soon as I\'m back.',
        thinking: 'Thinking…',
        listening: 'Listening…',
        listeningWake: 'Say "{name}" to talk to me…',
        paused: 'Paused. Click the orb to resume.',
        micBlocked: 'Microphone blocked. You can still type below.',
        heardNoName: 'Heard "{text}". Say "{name}" first to talk to me.',
        yes: 'Yes? I\'m listening…',
        waitName: 'I\'ll only answer when you say "{name}".',
        listenAll: 'Listening to everything again.',
        volume: 'Volume',
        speed: 'Speaking speed',
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
        helper: 'HELPER',
        call: 'CALL',
        phone: 'PHONE',
        nowPlaying: 'NOW PLAYING',
    },
    af: {
        wake: 'Klik op die bol om {name} wakker te maak.',
        reconnecting: 'Verbinding verloor. Koppel weer…',
        willSend: 'Koppel weer… Ek antwoord sodra ek terug is.',
        thinking: 'Dink…',
        listening: 'Luister…',
        listeningWake: 'Sê "{name}" om met my te praat…',
        paused: 'Onderbreek. Klik op die bol om voort te gaan.',
        micBlocked: 'Mikrofoon geblokkeer. Jy kan steeds hieronder tik.',
        heardNoName: 'Gehoor "{text}". Sê eers "{name}" om met my te praat.',
        yes: 'Ja? Ek luister…',
        waitName: 'Ek antwoord net as jy "{name}" sê.',
        listenAll: 'Ek luister weer na alles.',
        volume: 'Volume',
        speed: 'Praatspoed',
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
        helper: 'HELPER',
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

// Best browser voice for the configured language. A voice the user picked (voice.js saves its name) wins;
// otherwise natural-sounding voices come first (Edge's "Online (Natural)" voices, then Google's), then a
// male voice since both butlers are men, then an exact language match (en-GB before other English).
const MALE_VOICE = /\b(male|daniel|george|arthur|ryan|oliver|thomas|guy|brian|william|liam|andrew|christopher|eric|roger|steffan)\b/i;
const NATURAL_VOICE = /natural|neural|online|premium|enhanced/i;
// Deep, serious British men's voices, best first: Edge's Ryan and Thomas, Windows' George, Chrome's UK male.
const SOLDIER_VOICE = /\b(ryan|thomas|george|arthur|daniel|uk english male)\b/i;
// Unless changed in the voice picker, Alfred speaks a touch slower and lower: calm and serious.
const VOICE_STYLE = { rate: 0.92, pitch: 0.8 };

function voicePrefs() {
    let saved = {};
    try { saved = JSON.parse(localStorage.getItem('alfred-voice') || '{}') || {}; } catch { /* private window */ }
    return { ...VOICE_STYLE, ...saved };
}

function rankVoices(voices, lang) {
    const want = lang.toLowerCase().replace('_', '-');
    const norm = (v) => v.lang.toLowerCase().replace('_', '-');
    const score = (v) => (NATURAL_VOICE.test(v.name) ? 100 : 0) + (/google/i.test(v.name) ? 50 : 0)
        + (MALE_VOICE.test(v.name) && !/female/i.test(v.name) ? 10 : 0) + (norm(v) === want ? 5 : 0)
        + (norm(v) === 'en-gb' ? 20 : 0) + (norm(v) === 'en-gb' && SOLDIER_VOICE.test(v.name) ? 15 : 0);
    return voices.filter((v) => norm(v).split('-')[0] === want.split('-')[0])
        .map((v) => ({ v, s: score(v) })).sort((a, b) => b.s - a.s).map((x) => x.v);
}

function pickVoice() {
    const voices = speechSynthesis.getVoices();
    const chosen = voicePrefs().name;
    return (chosen && voices.find((v) => v.name === chosen)) || rankVoices(voices, config.speechLang)[0] || null;
}
window.jarvisVoice = { rank: rankVoices, pick: pickVoice, prefs: voicePrefs, lang: () => config.speechLang,
                       natural: (v) => NATURAL_VOICE.test(v.name) || /google/i.test(v.name) };

// Long replies are spoken a few sentences at a time: some browser voices (Chrome's Google ones) stop
// part-way through a long utterance.
function speechChunks(text) {
    const parts = String(text).match(/[^.!?\n]+[.!?]*[\s]*|[\n]+/g) || [String(text)];
    const out = [];
    let cur = '';
    for (const p of parts) {
        if (cur && (cur + p).length > 220) { out.push(cur.trim()); cur = ''; }
        cur += p;
    }
    if (cur.trim()) out.push(cur.trim());
    return out.length ? out : [String(text)];
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
let stopper = null;
let nowSaying = '';    // what Alfred is saying now, lower case without punctuation (see the stop listener)    // listens for "stop" while Jarvis speaks
let lastSpokeAt = 0;   // when Jarvis last finished speaking (follow-ups need no name)
const FOLLOW_UP_MS = 20000;
const STOP_WORDS = /^(?:(?:ok(?:ay)?|alfred|jarvis|hey alfred|hey jarvis),? )?(?:stop|stop talking|quiet|be quiet|shush|hush|enough|that's enough|shut up|hold on|wait|wait a (?:sec|second|moment)|pause|cancel|never ?mind|ok(?:ay)? thanks|thanks that's (?:it|all)|got it)(?:,? (?:alfred|jarvis))?[.!]?$/i;
// Listening carries on through short pauses, so a long request isn't cut off mid-thought; it ends after this
// much silence. Phones keep the browser's own short sessions (their long sessions repeat words).
const LONG_LISTEN = !/iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
const END_SILENCE_MS = 1100;
let wakeOnly = null;   // only answer when called by name; null until /config arrives
try { const w = localStorage.getItem('jarvis-wake'); if (w !== null) wakeOnly = w === 'on'; } catch (e) { /* private window */ }

function setWakeOnly(on) {
    wakeOnly = !!on;
    try { localStorage.setItem('jarvis-wake', wakeOnly ? 'on' : 'off'); } catch (e) { /* private window */ }
    if (listening) setState('listening', t(wakeOnly ? 'listeningWake' : 'listening'));
}

// What speech recognition often writes when you say his name.
const NAME_SOUNDALIKES = ['alfred', 'alfie', 'alf', 'al fred', 'alfred\'s', 'elfred', 'alford', 'offred',
    'jarvis', 'jervis', 'jarvas', 'travis', 'service'];
function namePattern() {
    const names = [config.name.toLowerCase(), ...NAME_SOUNDALIKES].map((n) => n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    return new RegExp(`\\b(?:hey |ok |okay )?(?:${names.join('|')})\\b`, 'i');
}
function calledByName(text) {
    // "travis" and "service" only count at the very start, where you'd say his name
    const p = namePattern();
    const m = text.match(p);
    if (!m) return false;
    return !/^(?:travis|service)$/i.test(m[0].replace(/^(?:hey|ok|okay) /i, '')) || m.index === 0;
}
// Just his name and nothing else ("Alfred?"): he answers at once with a soft tone and listens.
// "Alfred, what about tomorrow?" while he's talking: starts with his name and asks something new.
function isBargeIn(said) {
    const m = said.match(namePattern());
    if (!m || m.index !== 0) return false;
    const rest = said.slice(m[0].length).replace(/^[\s,]+/, '');
    if (rest.split(/\s+/).filter(Boolean).length < 2) return false;
    return !nowSaying.includes(said.toLowerCase().replace(/[.!?,]/g, ''));   // not his own voice coming back
}

function onlyName(text) {
    const rest = text.replace(namePattern(), '').replace(/[\s.,!?]+/g, '');
    return calledByName(text) && rest === '';
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
    document.dispatchEvent(new CustomEvent('jarvis:line', { detail: { who, text } }));  // access.js: captions, screen reader
}

// The next sentence of a streamed answer goes on the same line as the first.
function joinLine(text) {
    const last = transcript.lastElementChild;
    if (!last || last.className !== 'jarvis') { addLine('jarvis', text); return; }
    last.textContent += ` ${text}`;
    transcript.scrollTop = transcript.scrollHeight;
    document.dispatchEvent(new CustomEvent('jarvis:line', { detail: { who: 'jarvis', text, joined: true } }));
}

// Where the chat sits: a corner ("bottom-left" etc.) or the centre column. Remembered in this browser.
// It starts docked small on the left, minimised to a CHAT tab that opens with a click (or Alt+C).
const CHAT_CORNERS = ['top-left', 'top-right', 'bottom-left', 'bottom-right'];
const chatToggle = document.getElementById('chat-toggle');
const chatPreview = document.getElementById('chat-preview');
function placeChat(corner) {
    if (CHAT_CORNERS.includes(corner)) document.body.dataset.chat = corner;
    else delete document.body.dataset.chat;
    try { localStorage.setItem('jarvis-chat-place', CHAT_CORNERS.includes(corner) ? corner : 'centre'); } catch (e) { /* private window */ }
    transcript.scrollTop = transcript.scrollHeight;
    window.dispatchEvent(new Event('resize'));  // the folder stars move out of its way
}
function minimiseChat(min) {
    if (min) document.body.dataset.chatMin = '';
    else {
        delete document.body.dataset.chatMin;
        chatToggle.classList.remove('unread');
        transcript.scrollTop = transcript.scrollHeight;
    }
    chatToggle.setAttribute('aria-expanded', String(!min));
    try { localStorage.setItem('jarvis-chat-min', min ? '1' : '0'); } catch (e) { /* private window */ }
    window.dispatchEvent(new Event('resize'));
}
chatToggle.addEventListener('click', () => {
    const opening = 'chatMin' in document.body.dataset;
    minimiseChat(!opening);
    if (opening) typeInput.focus();
});
addEventListener('keydown', (e) => {
    if (e.altKey && (e.key === 'c' || e.key === 'C')) { e.preventDefault(); chatToggle.click(); }
});
document.addEventListener('jarvis:line', (e) => {
    chatPreview.textContent = e.detail.text.length > 60 ? `${e.detail.text.slice(0, 60)}…` : e.detail.text;
    if ('chatMin' in document.body.dataset && e.detail.who !== 'user') chatToggle.classList.add('unread');
});
{
    let place = 'bottom-left', min = true;
    try {
        place = localStorage.getItem('jarvis-chat-place') || 'bottom-left';
        min = localStorage.getItem('jarvis-chat-min') !== '0';
    } catch (e) { /* private window */ }
    if (CHAT_CORNERS.includes(place)) document.body.dataset.chat = place;
    if (min) document.body.dataset.chatMin = '';
    chatToggle.setAttribute('aria-expanded', String(!min));
}

// A soft rising tone: "yes, I'm listening".
function readyTone() {
    try {
        const audio = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audio.createOscillator(), gain = audio.createGain();
        osc.frequency.setValueAtTime(520, audio.currentTime);
        osc.frequency.exponentialRampToValueAtTime(880, audio.currentTime + 0.15);
        gain.gain.setValueAtTime(0.0001, audio.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.2, audio.currentTime + 0.03);
        gain.gain.exponentialRampToValueAtTime(0.0001, audio.currentTime + 0.25);
        osc.connect(gain).connect(audio.destination);
        osc.start();
        osc.stop(audio.currentTime + 0.27);
        setTimeout(() => audio.close(), 600);
    } catch (e) { /* no audio */ }
}

// Keep the screen on while Alfred is awake: a sleeping screen (above all on a phone) stops the microphone.
let wakeLock = null;
async function keepScreenOn() {
    if (!('wakeLock' in navigator) || document.hidden || wakeLock) return;
    try {
        wakeLock = await navigator.wakeLock.request('screen');
        wakeLock.addEventListener('release', () => { wakeLock = null; });
    } catch (e) { /* not allowed (battery saver): carry on */ }
}
document.addEventListener('visibilitychange', () => {
    if (document.hidden || !started) return;
    keepScreenOn();
    if (!ws || ws.readyState === WebSocket.CLOSED) reconnectNow();
    else maybeListen();   // back on the page: listen again straight away
});

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

// If a turn's "done" never arrives (a lost message), listen again rather than stay deaf for good.
const BUSY_LIMIT_MS = 90000;
let busySince = 0;
setInterval(() => {
    if (busy && confirmBox.hidden && !speaking && !queue.length && Date.now() - busySince > BUSY_LIMIT_MS) {
        busy = false;
        maybeListen();
    }
}, 5000);

function connect(onOpen) {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${proto}://${location.host}/ws`);
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        awaitingPong = false;
        if (msg.type === 'pong') return;   // only proves the line is alive
        busySince = Date.now();   // still working on it
        if (msg.type === 'say') {
            if (msg.join || msg.part) lastAnswer.push(msg);
            else lastAnswer = [msg];
            if (msg.join) joinLine(msg.text);
            else if (!msg.quiet) addLine('jarvis', msg.text);
            queue.push(msg);
            playNext();
        } else if (msg.type === 'alerts') {
            checkBuild(msg.build);
            alertsList.replaceChildren();
            msg.items.forEach(addAlert);
        } else if (msg.type === 'alert') {
            addAlert(msg);
        } else if (msg.type === 'dismissed') {
            removeAlert(msg.id);
        } else if (msg.type === 'nowplaying') {
            showNowPlaying(msg);
        } else if (msg.type === 'status') {
            if (busy && !speaking && !queue.length) setState('thinking', msg.text);   // what he's doing right now
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
            if (bargeText) {   // the old job is over: now ask what you said over him
                const text = bargeText;
                bargeText = '';
                heard(text);
                return;
            }
            maybeListen();
        }
    };
    ws.onopen = () => {
        reconnectDelay = 1000;
        awaitingPong = false;
        // Anything said while the line was down goes now, so it isn't lost.
        const waiting = unsent.splice(0);
        waiting.forEach(send);
        onOpen && onOpen();
    };
    ws.onclose = lostConnection;
}

// After an update (git pull, then Alfred restarted) the page reloads itself, so it never runs old code.
let pageBuild = '';
function checkBuild(build) {
    if (!build) return;
    if (!pageBuild) {
        pageBuild = build;
        return;
    }
    if (build === pageBuild) return;
    const reloadWhenFree = () => {
        if (busy || speaking || queue.length) {
            setTimeout(reloadWhenFree, 2000);   // never cut off an answer
            return;
        }
        try { if (started) sessionStorage.setItem('jarvis-resume', '1'); } catch { /* private window */ }
        location.reload();
    };
    reloadWhenFree();
}

function lostConnection() {
    busy = false;
    if (bargeText) {   // what you said over him goes when the line is back
        addLine('user', bargeText);
        unsent.push({ text: bargeText });
        bargeText = '';
    }
    confirmBox.hidden = true;
    if (started) setState('idle', t('reconnecting'));
    // Try again quickly at first, then less often, so a PC that's restarting Alfred isn't hammered.
    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(reconnectNow, reconnectDelay);
    reconnectDelay = Math.min(15000, reconnectDelay * 2);
}

// A phone that changes Wi-Fi or mobile signal can leave the line looking open while nothing gets through.
// Check it every 20 seconds; if the last check got no answer, drop it and reconnect at once.
const PING_EVERY_MS = 20000;
let awaitingPong = false;
setInterval(() => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    if (awaitingPong) {
        const dead = ws;
        dead.onclose = null;
        dead.onmessage = null;
        try { dead.close(); } catch (_) { /* already gone */ }
        ws = null;
        reconnectDelay = 1000;
        lostConnection();
        return;
    }
    awaitingPong = true;
    ws.send(JSON.stringify({ type: 'ping' }));
}, PING_EVERY_MS);

// What you said while the connection was down (at most a few things), sent when it comes back.
const unsent = [];

let reconnectDelay = 1000;
let reconnectTimer = null;
function reconnectNow() {
    clearTimeout(reconnectTimer);
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;
    connect(() => { if (started && !busy) setState('idle', ''); maybeListen(); });
}
addEventListener('online', () => { if (started) reconnectNow(); });
// Connect as soon as the page opens, so the first tap on the orb is answered without waiting for a connection.
setTimeout(() => { if (!started && !ws) connect(null); }, 300);   // the network is back: don't wait

function send(payload) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        if (payload.text) {
            unsent.push(payload);
            if (unsent.length > 3) unsent.shift();
            statusEl.textContent = t('willSend');
            reconnectNow();
        }
        return;
    }
    busy = true;
    busySince = Date.now();
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
    minimiseChat(false);  // an approval never hides in a closed chat
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

// The news bulletin player waits for this before it starts.
// The speed multiplier from the accessibility settings (access.js); 1 when unset.
const speechRate = () => (window.jarvisAccess ? window.jarvisAccess.speechRate() : 1);
window.jarvisIsSpeaking = () => speaking || queue.length > 0;
window.jarvisLastSpokeAt = () => lastSpokeAt;

function playNext() {
    if (speaking) return;
    const msg = queue.shift();
    if (!msg) {
        maybeListen();
        return;
    }
    speaking = true;
    nowSaying = String(msg.speak || msg.text || '').toLowerCase().replace(/[.!,]/g, '');
    // access.js: captions. Later parts of one answer were already captioned with the first part.
    if (!msg.part) document.dispatchEvent(new CustomEvent('jarvis:speak', { detail: { text: msg.text || '' } }));
    stopListening();
    setState('speaking');
    startStopper();
    // The "stop" listener keeps running between parts of one answer, so the mic isn't switched off and on.
    const finish = () => { speaking = false; lastSpokeAt = Date.now(); if (!queue.length) stopStopper(); playNext(); };

    if (msg.audio) {
        const bytes = Uint8Array.from(atob(msg.audio), (c) => c.charCodeAt(0));
        const url = URL.createObjectURL(new Blob([bytes], { type: 'audio/mpeg' }));
        const audio = new Audio(url);
        audio.playbackRate = Math.min(2, Math.max(0.5, speechRate() * savedRate()));   // "talk faster" works on every voice
        audio.volume = voiceVolume();
        currentAudio = audio;
        audio.onended = audio.onerror = () => { URL.revokeObjectURL(url); finish(); };
        audio.play().catch(finish);
    } else if ('speechSynthesis' in window) {
        const voice = pickVoice();
        const prefs = voicePrefs();
        if (!voice && speechSynthesis.getVoices().length) statusEl.textContent = t('noVoice');
        const chunks = speechChunks(msg.speak || msg.text);
        let done = false;
        const once = () => { if (!done) { done = true; finish(); } };
        chunks.forEach((part, i) => {
            const utterance = new SpeechSynthesisUtterance(part);
            utterance.lang = config.speechLang;
            if (voice) utterance.voice = voice;
            utterance.rate = Math.min(2, Math.max(0.3, (Number(prefs.rate) || 1) * speechRate()));
            utterance.pitch = Number(prefs.pitch) || 1;
            utterance.volume = voiceVolume();
            if (i === chunks.length - 1) utterance.onend = once;
            utterance.onerror = (e) => {
                if (e.error === 'interrupted' || e.error === 'canceled') return;  // "stop" handles its own state
                speechSynthesis.cancel();
                once();
            };
            speechSynthesis.speak(utterance);
        });
    } else {
        finish();
    }
}

// ---- Speech input -----------------------------------------------------------

// Only one recogniser may hold the microphone at a time: the main one, or the "stop" listener while Alfred
// speaks. Each starts only after the other has fully ended, otherwise Chrome cuts one off and the mic seems dead.
let recActive = false;      // main recogniser started and not yet ended
let heardSomething = false; // this listening session heard speech
let quickEnds = 0;          // sessions in a row that ended at once with nothing heard: back off, don't spin
let netFails = 0;           // "network" errors in a row: the browser's listening service is unreachable
let startedAt = 0;
let heardText = '';         // the finished words of what you're saying now
let discardHeard = false;   // listening was cut off on purpose (Alfred started talking, you typed)
let endTimer = null;

// Volume and speed by voice, done here at once without asking Claude: "louder", "quieter", "talk faster"...
// Speed you chose ("talk faster", the voice picker); ElevenLabs voices start at their natural pace.
function savedRate() {
    try { return Number((JSON.parse(localStorage.getItem('alfred-voice') || '{}') || {}).rate) || 1; } catch { return 1; }
}
function voiceVolume() {
    try { const v = Number(localStorage.getItem('alfred-volume')); return v > 0 && v <= 1 ? v : 1; } catch { return 1; }
}
const QUICK = [
    [/^(?:louder|speak up|volume up|turn (?:it |yourself )?up|a bit louder|louder please)$/, 'volume', 0.2],
    [/^(?:quieter|softer|volume down|turn (?:it |yourself )?down|a bit quieter|quieter please|not so loud)$/, 'volume', -0.2],
    [/^(?:talk|speak) (?:a bit )?faster$|^speed up$|^faster$/, 'rate', 0.1],
    [/^(?:talk|speak) (?:a bit )?slower$|^slow down$|^slower$/, 'rate', -0.1],
    [/^(?:go to sleep|wait for (?:your|my) name|only (?:listen|answer) (?:for|to|when i say) your name|only when i say your name|name only)$/, 'wake', 1],
    [/^(?:wake up|listen to everything|answer everything|always listen|you don't need your name|no name needed)$/, 'wake', -1],
    [/^(?:stop listening|mic off|microphone off|mute (?:the )?mic(?:rophone)?|turn (?:the |your )?mic(?:rophone)? off)$/, 'mic', -1],
];
function quickCommand(text) {
    const said = text.toLowerCase().replace(/^(?:(?:hey |ok |okay )?(?:alfred|alfie|jarvis),? )/, '').replace(/[.!?,]+$/g, '').trim();
    const hit = QUICK.find(([re]) => re.test(said));
    if (!hit) return false;
    const [, what, step] = hit;
    if (what === 'mic') {
        stopListening();
        paused = true;
        setState('idle', t('paused'));   // a tap on the orb turns it back on
        readyTone();
        return true;
    }
    if (what === 'wake') {
        setWakeOnly(step > 0);
        statusEl.textContent = t(step > 0 ? 'waitName' : 'listenAll');
        lastSpokeAt = step > 0 ? 0 : Date.now();   // from now on, the name is needed straight away
        readyTone();
        return true;
    }
    if (what === 'volume') {
        const v = Math.min(1, Math.max(0.2, +(voiceVolume() + step).toFixed(2)));
        try { localStorage.setItem('alfred-volume', String(v)); } catch { /* private window */ }
        statusEl.textContent = `${t('volume')} ${Math.round(v * 100)}%`;
    } else {
        const prefs = voicePrefs();
        let saved = {};
        try { saved = JSON.parse(localStorage.getItem('alfred-voice') || '{}') || {}; } catch { /* private window */ }
        saved.rate = Math.min(1.6, Math.max(0.6, +((Number(prefs.rate) || 1) + step).toFixed(2)));
        try { localStorage.setItem('alfred-voice', JSON.stringify(saved)); } catch { /* private window */ }
        statusEl.textContent = `${t('speed')} ${Math.round(saved.rate * 100)}%`;
    }
    lastSpokeAt = Date.now();   // follow-ups ("louder") still need no name
    readyTone();
    return true;
}

// "Say that again": replay Alfred's last answer straight away, without asking Claude.
let lastAnswer = [];
const REPEAT = /^(?:(?:hey |ok |okay )?(?:alfred|alfie|jarvis),? )?(?:say that again|repeat that|repeat|can you repeat that|what did you say|pardon|come again|sorry what|say again)(?:,? (?:alfred|jarvis|please))*[.?!]?$/i;
function repeatLast() {
    if (!lastAnswer.length) return false;
    lastAnswer.forEach((m) => queue.push({ ...m, part: true }));   // no new captions or transcript lines
    playNext();
    return true;
}

// One whole thing you said: send it to Alfred, unless he waits for his name and it wasn't used.
function heard(text) {
    const recent = Date.now() - lastSpokeAt < FOLLOW_UP_MS;
    const forMe = recent || !wakeOnly || calledByName(text);
    if (REPEAT.test(text.trim()) && forMe && repeatLast()) return;
    if (forMe && quickCommand(text)) return;
    if (onlyName(text)) {
        lastSpokeAt = Date.now();          // the next thing you say needs no name
        readyTone();
        statusEl.textContent = t('yes');
        return;
    }
    if (wakeOnly && !calledByName(text) && Date.now() - lastSpokeAt > FOLLOW_UP_MS) {
        // Not for Jarvis. Show what was heard so the mic clearly works.
        statusEl.textContent = t('heardNoName').replace('{text}', text.length > 40 ? `${text.slice(0, 40)}…` : text);
        return;
    }
    addLine('user', text);
    send({ text });
}

if (Recognition) {
    recognition = new Recognition();
    recognition.continuous = LONG_LISTEN;
    recognition.interimResults = true;   // show the words as you say them
    recognition.onresult = (event) => {
        let interim = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const r = event.results[i];
            if (r.isFinal) heardText = `${heardText} ${r[0].transcript}`.trim();
            else interim += r[0].transcript;
        }
        heardSomething = true;
        netFails = 0;
        const live = `${heardText} ${interim}`.trim();
        if (live) statusEl.textContent = `“${live.length > 70 ? `…${live.slice(-70)}` : live}”`;
        clearTimeout(endTimer);
        // Still mid-word: give a little longer before deciding you've finished.
        if (LONG_LISTEN) endTimer = setTimeout(() => { try { recognition.stop(); } catch (e) { /* ended */ } }, interim ? END_SILENCE_MS * 1.6 : END_SILENCE_MS);
    };
    recognition.onend = () => {
        recActive = false;
        listening = false;
        clearTimeout(endTimer);
        const text = discardHeard ? '' : heardText.trim();
        heardText = '';
        discardHeard = false;
        if (text) heard(text);
        if (speaking) { startStopper(); return; }
        // Ended almost at once without hearing anything: wait longer each time instead of flickering.
        quickEnds = !heardSomething && Date.now() - startedAt < 1500 ? quickEnds + 1 : 0;
        setTimeout(maybeListen, quickEnds > 2 ? Math.min(8000, 500 * 2 ** (quickEnds - 2)) : 150);
    };
    recognition.onerror = (event) => {
        const err = event.error;
        if (err === 'no-speech' || err === 'aborted') return;   // normal: silence, or we stopped it
        if (err === 'network' && ++netFails < 3) return;        // a blip: try again (onend backs off)
        // The microphone is blocked, missing, busy, or the listening service is unreachable: say how to fix it.
        paused = true;
        setState('idle', t('micBlocked'));
        document.dispatchEvent(new CustomEvent('jarvis:mic-blocked', { detail: { error: err } }));   // mic-help.js says how to fix it
    };
}

function maybeListen() {
    if (!started || paused || busy || speaking || queue.length || listening) return;
    if (!recognition) {
        setState('idle', t('noRecognition'));
        return;
    }
    if (recActive || (stopper && stopper.running)) return;   // the other one's onend calls back here
    try {
        recognition.lang = config.speechLang;
        recognition.start();
        recActive = true;
        listening = true;
        heardSomething = false;
        startedAt = Date.now();
        setState('listening', t(wakeOnly ? 'listeningWake' : 'listening'));
    } catch (e) { /* already started */ }
}

// While Jarvis speaks, a second recogniser listens only for "stop", "quiet", "that's enough"…
function startStopper() {
    if (!Recognition || paused || !started || !speaking) return;
    if (recActive) return;   // the main recogniser is still letting go of the mic; its onend calls back here
    if (!stopper) {
        stopper = new Recognition();
        stopper.continuous = true;
        stopper.interimResults = true;
        stopper.onresult = (event) => {
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const said = event.results[i][0].transcript.trim();
                // The mic can hear Alfred's own voice: "Got it." in his answer must not cut him off.
                if (STOP_WORDS.test(said) && !nowSaying.includes(said.toLowerCase().replace(/[.!,]/g, ''))) {
                    skipSpeech();
                    return;
                }
                if (event.results[i].isFinal && isBargeIn(said)) {
                    interruptWith(said);
                    return;
                }
            }
        };
        stopper.onend = () => {
            stopper.running = false;
            if (speaking) setTimeout(startStopper, 200);
            else maybeListen();   // Alfred finished while it was letting go: listen now
        };
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
    // running stays true until onend, so the main recogniser waits for the mic to be free
    if (stopper && stopper.running) stopper.abort();
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
    if (listening && recognition) { discardHeard = true; recognition.abort(); }
    listening = false;
}

// ---- Controls ---------------------------------------------------------------

// Reloaded after an update while awake: carry on listening, without the greeting.
try {
    if (sessionStorage.getItem('jarvis-resume')) {
        sessionStorage.removeItem('jarvis-resume');
        setTimeout(() => {
            if (started) return;
            started = true;
            keepScreenOn();
            const go = () => { setState('idle', ''); maybeListen(); };
            if (ws && ws.readyState === WebSocket.OPEN) go();   // the page already connected on its own
            else if (ws && ws.readyState === WebSocket.CONNECTING) ws.addEventListener('open', go, { once: true });
            else connect(go);
        }, 400);
    }
} catch { /* private window */ }

orb.addEventListener('click', () => {
    if (!started) {
        started = true;
        keepScreenOn();
        if (ws && ws.readyState === WebSocket.OPEN) send({ type: 'activate' });   // already connected: no wait
        else if (ws && ws.readyState === WebSocket.CONNECTING) ws.addEventListener('open', () => send({ type: 'activate' }), { once: true });
        else connect(() => send({ type: 'activate' }));
        return;
    }
    if (speaking) {
        skipSpeech();  // tap while speaking: skip the rest of what Jarvis is saying
        return;
    }
    if (busy) {
        cancelTurn();  // tap while thinking: stop working on it
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

// Stop what Alfred is working on (tap the orb while he thinks, or press Esc). He says "Cancelled." and listens.
// Cut Alfred off and ask the new thing; if he's still working on the old one, cancel it first.
let bargeText = '';
function interruptWith(text) {
    skipSpeech();
    if (busy) {
        bargeText = text;
        cancelTurn();
        return;
    }
    heard(text);
}

function cancelTurn() {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: 'cancel' }));
    confirmBox.hidden = true;
    queue.length = 0;
    if (speaking) skipSpeech();
}
addEventListener('keydown', (e) => {
    if (e.key !== 'Escape' || !started) return;
    if (speaking) skipSpeech();
    else if (busy) cancelTurn();
});

// mic-help.js "TRY AGAIN": listen again once the microphone has been fixed.
document.addEventListener('jarvis:mic-retry', () => {
    paused = false;
    netFails = 0;
    quickEnds = 0;
    if (started) maybeListen();
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
    // Scripts lower in the page (the planets, the HUD extras) may still be loading when /config answers,
    // so hold the event until every script has run; otherwise they never hear it and quietly stay off.
    const tell = () => document.dispatchEvent(new CustomEvent('jarvis:config', { detail: config }));
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', tell, { once: true });
    else tell();
}).catch(() => {});
// Chrome loads its voice list asynchronously; touching it early starts the load.
if ('speechSynthesis' in window) speechSynthesis.getVoices();
