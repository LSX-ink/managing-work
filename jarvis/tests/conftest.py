import os

# Tests must not reach ntfy.sh or write the phone address file.
os.environ["JARVIS_CALL_ALERTS"] = "false"
