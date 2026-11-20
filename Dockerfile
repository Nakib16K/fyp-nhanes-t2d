# Reference recipe for a future build; this file is not an immutable build lock.
# The accepted runtime is recorded separately in docs/RUNTIME_PROVENANCE.json.
# Pin/review base, native packages and wheel inputs before rebuilding; see docs/REPRODUCIBILITY.md.
FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    XDG_CACHE_HOME=/tmp/.cache MPLCONFIGDIR=/tmp/matplotlib NUMBA_CACHE_DIR=/tmp/numba
WORKDIR /opt/fyp
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY deploy/requirements-inference.txt /opt/fyp/deploy/requirements-inference.txt
RUN python -m pip install --no-cache-dir --only-binary=:all: \
    -r /opt/fyp/deploy/requirements-inference.txt
COPY api/ /opt/fyp/api/
COPY src/ /opt/fyp/src/
COPY reports/ /opt/fyp/reports/
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin fyp \
    && chmod -R a+rX /opt/fyp
# Prepare runtime directories for the non-root user.
# Keep application source and verified models read-only.
RUN install -d -o fyp -g fyp -m 0755 \
    /opt/fyp/data \
    /opt/fyp/data/raw \
    /opt/fyp/data/processed \
    /opt/fyp/models \
    /opt/fyp/reports/figures
USER 10001:10001
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
