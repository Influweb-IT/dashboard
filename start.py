"""
Dashboard entry point.

Imports _data (and all its heavy dependencies: numpy, pandas, geopandas,
scipy, matplotlib) and pre-renders figures before starting Streamlit
"""

import sys
import time
import threading

sys.path.insert(0, "/app")

t0 = time.time()
print("[start] pre-rendering figures...", flush=True)

import _data

# Poll until gcsfuse serves the sentinel since gcsfuse sidecar may not be ready at container start
_deadline = t0 + 30
mtime = 0.0
_attempt = 0
while time.time() < _deadline:
    mtime = _data.ready_mtime()
    print(f"[start] ready_mtime attempt {_attempt}: {mtime}", flush=True)
    if mtime > 0:
        break
    _attempt += 1
    time.sleep(1)

if mtime > 0:
    print(f"[start] prewarming with mtime={mtime} (after {_attempt} retries, {time.time()-t0:.1f}s elapsed)", flush=True)
    try:
        _data.load_figures(mtime, "it")
        _data.load_figures(mtime, "en")
        print(f"[start] prewarm complete in {time.time() - t0:.1f}s", flush=True)
    except Exception as e:
        print(f"[start] prewarm failed ({e}) — starting without warm cache", flush=True)
else:
    print("[start] .READY not found after 30s — starting without warm cache", flush=True)


def _prewarm_watcher(interval: int = 60) -> None:
    last = _data.ready_mtime()
    print(f"[watcher] initialized with last_mtime={last}", flush=True)
    while True:
        time.sleep(interval)
        current = _data.ready_mtime()
        if current != last:
            print(f"[watcher] sentinel changed (mtime={current}), rewarming...", flush=True)
            t = time.time()
            try:
                _data.load_figures(current, "it")
                _data.load_figures(current, "en")
                print(f"[watcher] rewarm complete in {time.time() - t:.1f}s", flush=True)
                last = current
            except Exception as e:
                print(f"[watcher] rewarm failed ({e}) — will retry next tick", flush=True)


threading.Thread(target=_prewarm_watcher, daemon=True, name="prewarm-watcher").start()

print("[start] starting Streamlit...", flush=True)
from streamlit.web import bootstrap

bootstrap.run(
    "/app/Plotting.py",
    False,
    [],
    {"server.address": "0.0.0.0", "server.port": 8501},
)
