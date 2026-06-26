FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/app \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Run as a non-root user
RUN useradd --uid 10001 --user-group --no-create-home --home-dir /app appuser

# gettext (msgfmt) compiles locale .po -> .mo at container start.
# libgomp1 is needed by numpy/scipy/pandas wheels at runtime.
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
       gettext \
       libgomp1 \
       libexpat1 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
# Upgrade build tooling first to pull in security fixes for pip/setuptools/wheel
# (and jaraco.context, vendored via setuptools).
RUN pip install --upgrade pip setuptools wheel \
  && pip install -r /app/requirements.txt

COPY . /app/

# entrypoint compiles locale .mo files and Streamlit writes under $HOME (=/app)
# at runtime so the non-root user must own /app.
RUN chmod +x /app/entrypoint.sh \
  && chown -R 10001:10001 /app

USER 10001

EXPOSE 8501

ENTRYPOINT ["/app/entrypoint.sh"]
