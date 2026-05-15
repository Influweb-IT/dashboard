#!/usr/bin/env bash
set -euo pipefail

mode="${DASHBOARD_MODE:-serve}"

cd /app

case "$mode" in
  export)
    exec python /app/export.py
    ;;

  aggregate)
    exec python /app/DataTreatment.py
    ;;

  serve)
    # Compile gettext .po -> .mo for each locale at startup for localized strings
    find /app/locales -mindepth 1 -maxdepth 1 -type d | while read -r lang_dir; do
      po="$lang_dir/LC_MESSAGES/dashboard.po"
      mo="$lang_dir/LC_MESSAGES/dashboard.mo"
      if [ -f "$po" ]; then
        msgfmt "$po" -o "$mo"
      fi
    done

    exec streamlit run /app/Plotting.py \
      --server.address=0.0.0.0 \
      --server.port=8501
    ;;

  *)
    echo "unknown DASHBOARD_MODE: $mode (expected: export | aggregate | serve)" >&2
    exit 2
    ;;
esac
