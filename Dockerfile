# =============================================================
# Stage 1 — builder
# =============================================================
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV UV_PROJECT_ENVIRONMENT=$VIRTUAL_ENV
ENV UV_NO_SYNC=1

COPY requirements.txt .
RUN uv venv $VIRTUAL_ENV && \
    uv pip install --python $VIRTUAL_ENV/bin/python -r requirements.txt

# =============================================================
# Stage 2 — runtime
# =============================================================
FROM python:3.12-slim AS runtime

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY . .

RUN mkdir -p /app/out

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=25s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live')"

CMD ["python", "main.py", "serve", "--host", "0.0.0.0", "--port", "8000"]
