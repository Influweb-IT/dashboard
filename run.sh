#!/bin/bash

# Generates mo files
find locales -mindepth 1 -maxdepth 1 -type d | while read lang_dir; do
  msgfmt "$lang_dir/LC_MESSAGES/dashboard.po" -o "$lang_dir/LC_MESSAGES/dashboard.mo"
done

# For local developement: read CSVs from ./data/dashboard rather than the container
# default of /data/dashboard. Override by setting DASHBOARD_DATA_DIR.
export DASHBOARD_DATA_DIR="${DASHBOARD_DATA_DIR:-$(pwd)/data/dashboard}"

streamlit run Plotting.py
