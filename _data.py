"""
Process-level data and figure cache.

Stored as plain module globals so sys.modules guarantees a single shared
instance across all Streamlit sessions. start.py imports this module and
pre-renders figures before Streamlit accepts any connections, so every
user session hits a warm cache.
"""

import io
import os
import gettext
import threading

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from scipy.stats import beta

_INPUT_DIR = os.environ.get('DASHBOARD_DATA_DIR', '/data/dashboard')
_SENTINEL = os.path.join(_INPUT_DIR, '.READY')
_LOCALE_DIR = os.path.join(os.path.dirname(__file__), 'locales')
_DOMAIN = 'dashboard'
_lock = threading.Lock()


def ready_mtime() -> float:
    try:
        return os.path.getmtime(_SENTINEL)
    except FileNotFoundError:
        return 0.0


# ── data ──────────────────────────────────────────────────────────────────────

_series_mtime = None
_series_data = None
_gdf_mtime = None
_gdf_data = None


def load_series(mtime):
    global _series_mtime, _series_data
    if _series_mtime != mtime:
        with _lock:
            if _series_mtime != mtime:
                print(f"[_data] loading series (mtime={mtime})", flush=True)
                r = lambda f: pd.read_csv(
                    os.path.join(_INPUT_DIR, f), index_col=0, header=0
                ).iloc[:, 0]
                _series_data = {
                    "ILI_incidence": r("ILI_incidence.csv"),
                    "ARI_incidence": r("ARI_incidence.csv"),
                    "active_users":  r("active_users.csv"),
                    "gender":        r("gender.csv"),
                    "education":     r("education.csv"),
                    "occupation":    r("occupation.csv"),
                    "age":           r("age.csv"),
                }
                _series_mtime = mtime
                print("[_data] series loaded", flush=True)
    return _series_data


def load_gdf(mtime):
    global _gdf_mtime, _gdf_data
    if _gdf_mtime != mtime:
        with _lock:
            if _gdf_mtime != mtime:
                print(f"[_data] loading gdf (mtime={mtime})", flush=True)
                df = gpd.read_file(
                    os.path.join(_INPUT_DIR, "reg_map.csv"), ignore_geometry=True
                )
                df["geometry"] = gpd.GeoSeries.from_wkt(df["geometry"])
                df["count"] = df["count"].astype(float)
                df["ar"] = df["ar"].astype(float)
                _gdf_data = gpd.GeoDataFrame(df)
                _gdf_mtime = mtime
                print("[_data] gdf loaded", flush=True)
    return _gdf_data


# ── figures ───────────────────────────────────────────────────────────────────
# Keyed by language; invalidated when mtime changes.

_fig_mtime = None
_fig_cache = {}  # language -> (fig1, fig2, fig3, fig4, fig5)


def load_figures(mtime, language):
    global _fig_mtime, _fig_cache
    with _lock:
        if _fig_mtime != mtime:
            print(f"[_data] cache invalidated: old_mtime={_fig_mtime} new_mtime={mtime}", flush=True)
            _fig_cache = {}
            _fig_mtime = mtime
        if language in _fig_cache:
            print(f"[_data] figures cache hit (lang={language})", flush=True)
            return _fig_cache[language]
    # build outside the lock so inner load_series/load_gdf can acquire it
    print(f"[_data] building figures (mtime={mtime}, lang={language})", flush=True)
    figs = _build_figures(mtime, language)
    print(f"[_data] figures ready (lang={language})", flush=True)
    with _lock:
        if language not in _fig_cache:
            _fig_cache[language] = figs
    return _fig_cache[language]


def _t(language: str):
    return gettext.translation(_DOMAIN, localedir=_LOCALE_DIR, languages=[language]).gettext


def _clopper_pearson(p, n):
    alpha = 0.05
    k = p * n
    ci_u, ci_o = {}, {}
    for season in p.keys():
        kk, nn = k[season], n[season]
        lo, hi = beta.ppf([alpha / 2, 1 - alpha / 2], [kk, kk + 1], [nn - kk + 1, nn - kk])
        ci_u[season] = p[season] - (0.0 if np.isnan(lo) else lo)
        ci_o[season] = (1.0 if np.isnan(hi) else hi) - p[season]
    return pd.DataFrame.from_dict([ci_u, ci_o])


def _build_figures(mtime: float, language: str) -> tuple:
    _ = _t(language)
    series = load_series(mtime)
    gdf = load_gdf(mtime)

    # incidence
    rescaling = 1000
    incidence = series["ILI_incidence"]
    incidence_ARI = series["ARI_incidence"]
    wau = series["active_users"]
    y_label = _("incidence (‰)")
    x_label = _("onset week")

    fig1, ax1 = plt.subplots(figsize=(12, 4))
    pd.Series(incidence).plot(
        color="#118AB2", marker="o", ls="-", markersize=4, alpha=0.8, ax=ax1, label=_("ILI")
    )
    ILI_down = pd.Series(incidence) - (_clopper_pearson(pd.Series(incidence) / rescaling, wau) * rescaling).T[0]
    ILI_up   = pd.Series(incidence) + (_clopper_pearson(pd.Series(incidence) / rescaling, wau) * rescaling).T[1]
    ax1.fill_between(pd.Series(incidence).index, ILI_down, ILI_up, alpha=0.3, color="#118AB2")
    ax1.set_ylabel(y_label)
    ax1.set_xlabel(x_label)
    ax1.spines[["right", "top"]].set_visible(False)

    fig2, ax2 = plt.subplots(figsize=(12, 4))
    pd.Series(incidence_ARI).plot(
        color="#073B4C", marker="o", ls="-", markersize=4, alpha=0.8, ax=ax2, label=_("ARI")
    )
    ARI_down = pd.Series(incidence_ARI) - (_clopper_pearson(pd.Series(incidence_ARI) / rescaling, wau) * rescaling).T[0]
    ARI_up   = pd.Series(incidence_ARI) + (_clopper_pearson(pd.Series(incidence_ARI) / rescaling, wau) * rescaling).T[1]
    ax2.fill_between(pd.Series(incidence_ARI).index, ARI_down, ARI_up, alpha=0.3, color="#073B4C")
    ax2.set_ylabel(y_label)
    ax2.set_xlabel(x_label)
    ax2.spines[["right", "top"]].set_visible(False)

    # demographic
    gender = series["gender"].rename({"Male": _("Male"), "Female": _("Female"), "Other": _("Other")})
    occupation = series["occupation"].rename({
        "full_time": _("Full time"), "retired": _("Retired"), "self-employed": _("Self-employed"),
        "student": _("Student"), "part_time": _("Part-time"), "homemaker": _("Homemaker"),
        "unemployed": _("Unemployed"), "other": _("Other"), "on leave": _("On leave"),
    })
    education = series["education"].rename({
        "master_phd": _("Master or PhD"), "high_school": _("High school"), "bachelor": _("Bachelor"),
        "int_school": _("Intermediate school"), "none": _("None"), "student": _("Student"),
    })
    age = series["age"].reindex(["<18", "18-40", "41-65", ">65"])

    fig3, ax3 = plt.subplots(figsize=(10, 7), nrows=2, ncols=2)
    gender.plot.bar(ax=ax3[0, 0], color="#621708", rot=0)
    ax3[0, 0].set_title(_("Gender")); ax3[0, 0].set_xlabel(""); ax3[0, 0].spines[["right", "top"]].set_visible(False)
    age.plot.bar(ax=ax3[0, 1], color="#F6AA1C", rot=0)
    ax3[0, 1].set_title(_("Age")); ax3[0, 1].set_xlabel(""); ax3[0, 1].spines[["right", "top"]].set_visible(False)
    education.plot.bar(ax=ax3[1, 0], color="#BC3908")
    ax3[1, 0].set_title(_("Education")); ax3[1, 0].set_xlabel(""); ax3[1, 0].spines[["right", "top"]].set_visible(False)
    occupation.plot.bar(ax=ax3[1, 1], color="#941B0C")
    ax3[1, 1].set_title(_("Occupation")); ax3[1, 1].set_xlabel(""); ax3[1, 1].spines[["right", "top"]].set_visible(False)
    fig3.text(0.0, 0.6, _("Number of participants in the 2023-2024 season"), va="center", rotation="vertical")
    fig3.tight_layout()

    # geo
    fig4, ax4 = plt.subplots(figsize=(6, 6))
    gdf.plot(ax=ax4, cmap="Blues", column="ar", legend=True, edgecolor="w", linewidth=0.3,
             legend_kwds={"label": _("Attack rate per 100,000 inhabitants in the 2023-2024 season"),
                          "orientation": "vertical", "shrink": 0.6})
    ax4.axis("off")

    fig5, ax5 = plt.subplots(figsize=(6, 6))
    gdf.plot(ax=ax5, cmap="Reds", column="count", legend=True, edgecolor="w", linewidth=0.3,
             legend_kwds={"label": _("Participants per 100,000 inhabitants in the 2023-2024 season"),
                          "orientation": "vertical", "shrink": 0.6})
    ax5.axis("off")

    return _to_png(fig1), _to_png(fig2), _to_png(fig3), _to_png(fig4), _to_png(fig5)


def _to_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    plt.close(fig)
    return buf.getvalue()
