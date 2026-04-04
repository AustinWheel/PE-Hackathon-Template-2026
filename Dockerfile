FROM python:3.13-slim

WORKDIR /app

# psycopg2 needs libpq
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 5001

CMD ["uv", "run", "gunicorn", "run:app", "--bind", "0.0.0.0:5001", "--workers", "4", "--timeout", "30", "--preload"]
