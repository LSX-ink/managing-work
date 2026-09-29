import inspect

import tools


def test_every_ability_takes_the_arguments_alfred_passes():
    for module in tools.ABILITIES:
        inspect.signature(module.run_tool).bind("name", {}, None, None)  # name, args, settings, http
