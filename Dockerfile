# NLK web image. Pinned to Python 3.12 for broad package compatibility
# (psycopg, Pillow, and later WeasyPrint), independent of the host's Python.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# psycopg[binary] and Pillow ship manylinux wheels, so no build toolchain is
# needed. WeasyPrint (invoice PDFs) needs pango/cairo shared libraries.
RUN apt-get update && apt-get install -y --no-install-recommends \
      libpango-1.0-0 \
      libpangocairo-1.0-0 \
      libpangoft2-1.0-0 \
      libgdk-pixbuf-2.0-0 \
      libcairo2 \
      libffi8 \
      shared-mime-info \
      fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt ./

ARG DEV=false
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && if [ "$DEV" = "true" ]; then pip install -r requirements-dev.txt; fi

COPY . .

# NOTE: dev runs as root to avoid bind-mount permission friction on Windows.
# The production stage (added in Milestone 7) switches to a non-root user.

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
