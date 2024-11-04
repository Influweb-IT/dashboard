#!/bin/bash

# Generates mo files
find locales -mindepth 1 -maxdepth 1 -type d | while read lang_dir; do
  msgfmt "$lang_dir/LC_MESSAGES/dashboard.po" -o "$lang_dir/LC_MESSAGES/dashboard.mo"
done

# Run streamlit
streamlit run --client.showSidebarNavigation=False Plotting.py
