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
