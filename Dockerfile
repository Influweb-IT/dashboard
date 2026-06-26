FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

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

RUN chmod +x /app/entrypoint.sh

EXPOSE 8501

ENTRYPOINT ["/app/entrypoint.sh"]
