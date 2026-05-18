"""
Dashboard entry point.

Imports _data (and all its heavy dependencies: numpy, pandas, geopandas,
scipy, matplotlib) and pre-renders figures before starting Streamlit
"""

import sys
import time

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

print("[start] starting Streamlit...", flush=True)
from streamlit.web import bootstrap

bootstrap.run(
    "/app/Plotting.py",
    False,
    [],
    {"server.address": "0.0.0.0", "server.port": 8501},
)
