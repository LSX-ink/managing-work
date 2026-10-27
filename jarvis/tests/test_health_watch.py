import httpx

import health


async def test_down_dashboard_is_restarted_first_and_only_reported_if_it_stays_down():
    up = {"hq": False}
    restarted = []

    def handler(request):
        return httpx.Response(200 if up["hq"] else 503)

    def restart(script):
        restarted.append(script)
        up["hq"] = True  # the restart worked
        return True

    sites = {"hq": ("The Kinetic HQ dashboard", "http://hq.test/", "HQ.vbs")}
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        assert await health.problems(http, {}, sites, restart, wait=0) == {} and restarted == ["HQ.vbs"]
        up["hq"] = False
        found = await health.problems(http, {}, sites, lambda s: False, wait=0)
    assert found == {"hq": "The Kinetic HQ dashboard isn't answering even after a restart"}


def test_each_problem_is_said_once_then_again_later_and_all_clear_when_fixed():
    said = {}
    assert health.health_news({"disk": "the drive is nearly full"}, said, 1000) == \
        "Sir, a health check: the drive is nearly full."
    assert health.health_news({"disk": "the drive is nearly full"}, said, 1600) == ""  # not again so soon
    assert "drive" in health.health_news({"disk": "the drive is nearly full"}, said, 1000 + health.HEALTH_REPEAT)
    assert health.health_news({}, said, 99999) == "All clear, sir: that's fixed now."
    assert health.health_news({}, said, 99999) == ""
