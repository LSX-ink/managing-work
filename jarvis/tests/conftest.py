import os
import tempfile

# Tests must not reach ntfy.sh or write the phone address file.
os.environ["JARVIS_CALL_ALERTS"] = "false"
os.environ["JARVIS_PHONE_PUSH"] = "false"
# Nor make TikTok videos in the background.
os.environ["JARVIS_CREATOR_DAILY"] = "false"
# Nor start Alfred's Claude Mem worker.
os.environ["JARVIS_ALFRED_MEM"] = "false"
# Nor record Kinetic mock-up videos with a real browser (the video tests switch it on with fakes).
os.environ["JARVIS_KINETIC_VIDEO"] = "false"
# Nor touch the real memory folder (saved conversation, facts, reminders).
os.environ["JARVIS_MEMORY_DIR"] = tempfile.mkdtemp(prefix="jarvis-test-memory-")


import shutil  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_memory_folder():
    """Each test starts with an empty default memory folder."""
    shutil.rmtree(os.environ["JARVIS_MEMORY_DIR"], ignore_errors=True)
    os.makedirs(os.environ["JARVIS_MEMORY_DIR"])
    yield
