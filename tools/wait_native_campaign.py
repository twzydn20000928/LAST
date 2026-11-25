"""Resume a native campaign worker when its admission check reports a resource wait."""
import json
import subprocess
import sys
import time


def run(arguments):
    command = [sys.executable, "-m", "last.native_campaign", "run", *arguments]
    while True:
        waiting = False
        with subprocess.Popen(command, stdout=subprocess.PIPE, text=True) as child:
            for line in child.stdout:
                print(line, end="", flush=True)
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if isinstance(event, dict) and event.get("status") == "waiting_resources":
                    waiting = True
            code = child.wait()
        if code or not waiting:
            return code
        time.sleep(60)


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
