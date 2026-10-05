"""How the page decides you're talking to Alfred (frontend/main.js), checked with node."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

MAIN = Path(__file__).resolve().parent.parent / "frontend" / "main.js"

SCRIPT = """
const src = require('fs').readFileSync(process.argv[1], 'utf8');
const a = src.indexOf('const NAME_SOUNDALIKES'), b = src.indexOf('function onlyName');
const config = { name: 'Alfred' };
eval(src.slice(a, src.indexOf('\\n}\\n', b) + 3) + ';globalThis.f = { calledByName, onlyName };');
const out = {};
for (const t of JSON.parse(process.argv[2])) out[t] = [f.calledByName(t), f.onlyName(t)];
console.log(JSON.stringify(out));
"""


@pytest.mark.skipif(not shutil.which("node"), reason="needs node")
def test_his_name_is_heard_even_when_misheard():
    cases = {
        "Alfred": [True, True],
        "Hey Alfred.": [True, True],
        "alfie what time is it": [True, False],
        "Alfred, what time is it?": [True, False],
        "travis set a timer": [True, False],      # a common mishearing, at the start
        "call customer service": [False, False],  # but not in the middle of a sentence
        "what is the weather": [False, False],
    }
    run = subprocess.run(["node", "-e", SCRIPT, str(MAIN), json.dumps(list(cases))],
                         capture_output=True, text=True, check=True)
    assert json.loads(run.stdout) == cases


REPEAT_SCRIPT = """
const src = require('fs').readFileSync(process.argv[1], 'utf8');
const line = src.split('\\n').find((l) => l.startsWith('const REPEAT = '));
eval(line.replace('const REPEAT', 'globalThis.REPEAT'));
console.log(JSON.stringify(JSON.parse(process.argv[2]).map((t) => REPEAT.test(t))));
"""


@pytest.mark.skipif(not shutil.which("node"), reason="needs node")
def test_say_that_again_is_recognised():
    texts = ["Say that again", "Alfred, repeat that please", "what did you say?", "pardon",
             "repeat my last order", "say hello to mum"]
    run = subprocess.run(["node", "-e", REPEAT_SCRIPT, str(MAIN), json.dumps(texts)],
                         capture_output=True, text=True, check=True)
    assert json.loads(run.stdout) == [True, True, True, True, False, False]


QUICK_SCRIPT = """
const src = require('fs').readFileSync(process.argv[1], 'utf8');
const a = src.indexOf('const QUICK = ['), b = src.indexOf('];', a) + 2;
eval(src.slice(a, b).replace('const QUICK', 'globalThis.QUICK'));
const kind = (t) => { const said = t.toLowerCase().replace(/^(?:(?:hey |ok |okay )?(?:alfred|alfie|jarvis),? )/, '').replace(/[.!?,]+$/g, '').trim();
                      const hit = QUICK.find(([re]) => re.test(said)); return hit ? hit[1] + (hit[2] > 0 ? '+' : '-') : null; };
console.log(JSON.stringify(JSON.parse(process.argv[2]).map(kind)));
"""


@pytest.mark.skipif(not shutil.which("node"), reason="needs node")
def test_volume_and_speed_by_voice_are_instant():
    texts = ["Louder", "Alfred, quieter please.", "talk faster", "slow down", "turn it up",
             "turn on the lights", "louder music in the kitchen"]
    run = subprocess.run(["node", "-e", QUICK_SCRIPT, str(MAIN), json.dumps(texts)],
                         capture_output=True, text=True, check=True)
    assert json.loads(run.stdout) == ["volume+", "volume-", "rate+", "rate-", "volume+", None, None]


LINE_SCRIPT = """
const src = require('fs').readFileSync(process.argv[1], 'utf8');
const a = src.indexOf('function connect(onOpen)'), b = src.indexOf('function send(payload)');
const code = src.slice(a, src.indexOf('\\n}\\n', b) + 3);
const sockets = [];
class WebSocket {
    constructor(url) { this.url = url; this.readyState = 0; this.sent = []; sockets.push(this); }
    send(data) { this.sent.push(JSON.parse(data)); }
    close() { this.readyState = 3; }
    open() { this.readyState = 1; this.onopen(); }
    reply(msg) { this.onmessage({ data: JSON.stringify(msg) }); }
}
Object.assign(WebSocket, { CONNECTING: 0, OPEN: 1, CLOSING: 2, CLOSED: 3 });
let ticks = [], timers = [];
const setInterval = (fn) => ticks.push(fn);
const setTimeout = (fn) => { timers.push(fn); return timers.length; };
const clearTimeout = () => {};
const addEventListener = () => {};
const location = { protocol: 'http:', host: 'pc:8340' };
const statusEl = {}, confirmBox = { hidden: true };
let ws = null, busy = false, started = true, speaking = false, queue = [], lastAnswer = [];
const t = (k) => k, setState = (s, text) => { statusEl.textContent = text; };
const stopListening = () => {}, maybeListen = () => {};
eval(code);
const out = {};
// Said while the line is down: held, then sent the moment it reconnects.
send({ text: 'what time is it' });
out.held = statusEl.textContent;
sockets[0].open();
out.sentOnOpen = [...sockets[0].sent];
// A line that looks open but answers nothing is dropped and redialled.
const check = ticks[ticks.length - 1];
check();
out.pinged = sockets[0].sent.at(-1).type;
sockets[0].reply({ type: 'pong' });
check();
out.aliveAfterPong = ws === sockets[0];
check();
out.droppedWhenSilent = ws === null && statusEl.textContent === 'reconnecting';
timers.at(-1)();
out.redialled = sockets.length;
console.log(JSON.stringify(out));
"""


@pytest.mark.skipif(not shutil.which("node"), reason="needs node")
def test_words_survive_a_dropped_line_and_dead_lines_are_redialled():
    run = subprocess.run(["node", "-e", LINE_SCRIPT, str(MAIN)], capture_output=True, text=True, check=True)
    assert json.loads(run.stdout) == {
        "held": "willSend",
        "sentOnOpen": [{"text": "what time is it"}],
        "pinged": "ping",
        "aliveAfterPong": True,
        "droppedWhenSilent": True,
        "redialled": 2,
    }
