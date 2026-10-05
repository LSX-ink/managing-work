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
