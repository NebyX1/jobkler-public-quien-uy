#!/usr/bin/env python3
import argparse
import json
import time
from urllib.error import URLError
from urllib.request import urlopen

parser = argparse.ArgumentParser()
parser.add_argument("url")
parser.add_argument("--ready-json", action="store_true")
parser.add_argument("--timeout", type=int, default=30)
args = parser.parse_args()
deadline = time.monotonic() + args.timeout
last_error = "sin respuesta"
while time.monotonic() < deadline:
    try:
        with urlopen(args.url, timeout=2) as response:
            content = response.read()
            if response.status == 200:
                if args.ready_json:
                    value = json.loads(content)
                    if value.get("status") == "ready":
                        raise SystemExit(0)
                else:
                    raise SystemExit(0)
            last_error = f"HTTP {response.status}"
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as error:
        last_error = str(error)
    time.sleep(0.5)
print(f"No respondió {args.url} antes del tiempo límite ({last_error}).")
raise SystemExit(1)
