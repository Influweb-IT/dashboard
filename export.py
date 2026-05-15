"""Fetches intake (full history) and weekly (current season only) survey
CSVs from the management API and writes them under <RAW_DIR>/<iso-week>/.

Required env:
  MGMT_API_URL      base URL of the management API (e.g. http://management-api:3232)
  ADMIN_EMAIL       login email for the export bot user
  ADMIN_PASSWORD    matching password
  INSTANCE_ID       study instance ID (e.g. "italy")
  STUDY_KEY         study key on the management API

Optional env:
  RAW_DIR           output root (default /data/raw)
  INTAKE_SURVEY_KEY default "intake"
  WEEKLY_SURVEY_KEY default "weekly"
  EXPORT_TIMEOUT_SECONDS default 1800
"""

from __future__ import annotations

import datetime as dt
import os
import sys
from typing import Optional
from urllib.parse import urlencode

import requests

from season_window import iso_week_dir_label, season_start_unix


def _env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise RuntimeError(f"missing required env var: {name}")
    return v


def login(base_url: str, email: str, password: str, instance_id: str) -> str:
    r = requests.post(
        f"{base_url}/v1/auth/login-with-email",
        json={"email": email, "password": password, "instanceId": instance_id},
        timeout=60,
    )
    r.raise_for_status()
    body = r.json()
    token = (body.get("token") or {}).get("accessToken") or body.get("accessToken")
    if not token:
        raise RuntimeError("login response did not contain an access token")
    return token


def export_survey(
    base_url: str,
    token: str,
    study_key: str,
    survey_key: str,
    dest_path: str,
    *,
    from_ts: Optional[int] = None,
    timeout: int = 1800,
) -> int:
    params = {"sep": ".", "shortKeys": "false"}
    if from_ts is not None:
        params["from"] = str(from_ts)
    url = f"{base_url}/v1/data/{study_key}/survey/{survey_key}/response?{urlencode(params)}"

    bytes_written = 0
    with requests.get(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "text/csv"},
        stream=True,
        timeout=timeout,
    ) as r:
        if r.status_code == 500:
            # Management API returns 500 when the study service has no responses.
            # Write an empty file so downstream aggregation can proceed safely.
            print(f"  {survey_key}: no responses (500), writing empty file", flush=True)
            open(dest_path, "wb").close()
            return 0
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 16):
                if chunk:
                    f.write(chunk)
                    bytes_written += len(chunk)
    return bytes_written


def main() -> int:
    base_url = _env("MGMT_API_URL").rstrip("/")
    email = _env("ADMIN_EMAIL")
    password = _env("ADMIN_PASSWORD")
    instance_id = _env("INSTANCE_ID")
    study_key = _env("STUDY_KEY")

    raw_dir = os.environ.get("RAW_DIR", "/data/raw")
    intake_key = os.environ.get("INTAKE_SURVEY_KEY", "intake")
    weekly_key = os.environ.get("WEEKLY_SURVEY_KEY", "weekly")
    timeout = int(os.environ.get("EXPORT_TIMEOUT_SECONDS", "1800"))

    out_dir = os.path.join(raw_dir, iso_week_dir_label())
    os.makedirs(out_dir, exist_ok=True)

    token = login(base_url, email, password, instance_id)

    intake_bytes = export_survey(
        base_url, token, study_key, intake_key,
        os.path.join(out_dir, "intake.csv"),
        timeout=timeout,
    )
    weekly_bytes = export_survey(
        base_url, token, study_key, weekly_key,
        os.path.join(out_dir, "weekly.csv"),
        from_ts=season_start_unix,
        timeout=timeout,
    )

    with open(os.path.join(out_dir, ".READY"), "w") as f:
        f.write(dt.datetime.now(dt.timezone.utc).isoformat() + "\n")

    print(
        f"exported to {out_dir}: "
        f"intake={intake_bytes} bytes, weekly={weekly_bytes} bytes "
        f"(weekly from={season_start_unix})",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
