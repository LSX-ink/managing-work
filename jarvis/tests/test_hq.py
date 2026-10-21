"""Kinetic HQ: the shared brain and the agents' schedules."""
from datetime import datetime, timedelta

from hq.agents import Agent, roster
from hq.brain import Brain


def test_brain_logs_facts_and_journal(tmp_path):
    b = Brain(tmp_path / "brain.db", journal_dir=tmp_path / "Journal")
    seen = []
    b.listen(seen.append)
    b.log("scout", "found 3 new leads", "win", {"new": 3})
    b.log("closer", "drafted", "nonsense-kind")
    b.set("leads.total", 3)
    assert b.get("leads.total") == 3 and b.get("missing", "x") == "x"
    ev = b.events()
    assert [e["agent"] for e in ev] == ["scout", "closer"] and ev[0]["data"] == {"new": 3}
    assert ev[1]["kind"] == "info"  # unknown kinds fall back to info
    assert b.count_today("scout", "win") == 1 and len(seen) == 2
    assert b.search("3 new")[0]["agent"] == "scout"
    journal = next((tmp_path / "Journal").glob("*.md")).read_text(encoding="utf-8")
    assert "**scout**: found 3 new leads" in journal


def test_runs_and_interval_schedule(tmp_path):
    b = Brain(tmp_path / "brain.db")
    a = Agent("guardian", "Sentinel", "Guardian", "x", "#fff", "job", every=5)
    now = datetime.now()
    assert a.due(b, now)
    rid = b.run_started("guardian")
    b.run_finished(rid, True, "ok")
    assert not a.due(b, now) and a.due(b, now + timedelta(minutes=6))
    assert b.runs_today("guardian") == 1 and b.last_run("guardian")["result"] == "ok"


def test_time_slots_run_once_per_slot(tmp_path):
    b = Brain(tmp_path / "brain.db")
    a = Agent("closer", "Blade", "Closer", "x", "#fff", "job", times=("09:05", "13:05"))
    day = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    assert not a.due(b, day)  # before the first slot
    nine = day.replace(hour=9, minute=10)
    assert a.due(b, nine)
    b.run_finished(b.run_started("closer"), True, "done")
    assert not a.due(b, datetime.now()) or datetime.now() >= day.replace(hour=13, minute=5)


def test_roster_has_seven_distinct_agents():
    keys = [a.key for a in roster()]
    assert len(keys) == len(set(keys)) == 7 and "closer" in keys and all(a.run for a in roster())
