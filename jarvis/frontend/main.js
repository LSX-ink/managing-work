// J.A.R.V.I.S. frontend: speech in (Web Speech API), speech out (server MP3 or browser voice).
const orb = document.getElementById('orb');
const statusEl = document.getElementById('status');
const transcript = document.getElementById('transcript');
const typeForm = document.getElementById('type-form');
const typeInput = document.getElementById('type-input');

let config = { speechLang: 'en-GB', serverVoice: false };

// UI text by language code; anything missing falls back to English.
const STRINGS = {
    en: {
        wake: 'Click the orb to wake Jarvis.',
        reconnecting: 'Connection lost. Reconnecting…',
        thinking: 'Thinking…',
        listening: 'Listening…',
        paused: 'Paused. Click the orb to resume.',
        micBlocked: 'Microphone blocked. You can still type below.',
        noRecognition: 'Voice input needs Chrome or Edge. Type below instead.',
        noVoice: 'Your browser has no voice for this language. Set ELEVENLABS_API_KEY to hear replies.',
        placeholder: '…or type to Jarvis',
        you: 'You',
    },
    af: {
        wake: 'Klik op die bol om Jarvis wakker te maak.',
        reconnecting: 'Verbinding verloor. Koppel weer…',
        thinking: 'Dink…',
        listening: 'Luister…',
        paused: 'Onderbreek. Klik op die bol om voort te gaan.',
        micBlocked: 'Mikrofoon geblokkeer. Jy kan steeds hieronder tik.',
        noRecognition: 'Steminvoer werk net in Chrome of Edge. Tik eerder hieronder.',
        noVoice: 'Jou blaaier het geen Afrikaanse stem nie. Stel ELEVENLABS_API_KEY om antwoorde te hoor.',
        placeholder: '…of tik vir Jarvis',
        you: 'Jy',
    },
};

function t(key) {
    const lang = config.speechLang.split('-')[0].toLowerCase();
    return (STRINGS[lang] || STRINGS.en)[key] || STRINGS.en[key];
}

// Best browser voice for the configured language: exact match (af-ZA), then same language (af).
function pickVoice() {
    const want = config.speechLang.toLowerCase().replace('_', '-');
    const voices = speechSynthesis.getVoices();
    const norm = (v) => v.lang.toLowerCase().replace('_', '-');
    return voices.find((v) => norm(v) === want)
        || voices.find((v) => norm(v).split('-')[0] === want.split('-')[0])
        || null;
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

function setState(state, text = '') {
    orb.className = state;
    statusEl.textContent = text;
}

function addLine(who, text) {
    const div = document.createElement('div');
    div.className = who;
    div.textContent = `${who === 'user' ? t('you') : 'Jarvis'}: ${text}`;
    transcript.appendChild(div);
    transcript.scrollTop = transcript.scrollHeight;
}

// ---- WebSocket --------------------------------------------------------------

function connect(onOpen) {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${proto}://${location.host}/ws`);
    ws.onopen = onOpen;
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'say') {
            addLine('jarvis', msg.text);
            queue.push(msg);
            playNext();
        } else if (msg.type === 'done') {
            busy = false;
            maybeListen();
        }
    };
    ws.onclose = () => {
        busy = false;
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
    const finish = () => { speaking = false; playNext(); };

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
        setState('listening', t('listening'));
    } catch (e) { /* already started */ }
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
        // Tap while speaking: skip the rest of what Jarvis is saying.
        queue.length = 0;
        if ('speechSynthesis' in window) speechSynthesis.cancel();
        if (currentAudio) currentAudio.pause();
        speaking = false;
        maybeListen();
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
    typeInput.placeholder = t('placeholder');
    if (!started) statusEl.textContent = t('wake');
}

fetch('/config').then((r) => r.json()).then((c) => { config = c; applyLanguage(); }).catch(() => {});
// Chrome loads its voice list asynchronously; touching it early starts the load.
if ('speechSynthesis' in window) speechSynthesis.getVoices();
