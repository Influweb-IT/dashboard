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

mtime = _data.ready_mtime()
try:
    _data.load_figures(mtime, "it")
    _data.load_figures(mtime, "en")
    print(f"[start] prewarm complete in {time.time() - t0:.1f}s", flush=True)
except Exception as e:
    print(f"[start] prewarm failed ({e}) — starting without warm cache", flush=True)


def _prewarm_watcher(interval: int = 60) -> None:
    last = _data.ready_mtime()
    while True:
        time.sleep(interval)
        current = _data.ready_mtime()
        if current != last:
            last = current
            print(f"[watcher] sentinel changed (mtime={current}), rewarming...", flush=True)
            t = time.time()
            try:
                _data.load_figures(current, "it")
                _data.load_figures(current, "en")
                print(f"[watcher] rewarm complete in {time.time() - t:.1f}s", flush=True)
            except Exception as e:
                print(f"[watcher] rewarm failed ({e})", flush=True)


threading.Thread(target=_prewarm_watcher, daemon=True, name="prewarm-watcher").start()

print("[start] starting Streamlit...", flush=True)
from streamlit.web import bootstrap

bootstrap.run(
    "/app/Plotting.py",
    False,
    [],
    {"server.address": "0.0.0.0", "server.port": 8501},
)
