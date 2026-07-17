#!/usr/bin/env python3
import json
import os
import time
import urllib.request


SOURCE_URL = os.environ["SOURCE_URL"]
TARGET_URL = os.environ["TARGET_URL"]
INTERVAL_S = float(os.environ.get("INTERVAL_S", "2.0"))


def fetch_status():
    with urllib.request.urlopen(SOURCE_URL, timeout=1.5) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def post_status(payload):
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        TARGET_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=1.5) as response:
        response.read()


def main():
    print(f"Relaying {SOURCE_URL} -> {TARGET_URL}", flush=True)
    while True:
        try:
            post_status(fetch_status())
            print(f"ok {time.time():.3f}", flush=True)
        except Exception as exc:
            print(f"error {type(exc).__name__}: {exc}", flush=True)
        time.sleep(INTERVAL_S)


if __name__ == "__main__":
    main()
