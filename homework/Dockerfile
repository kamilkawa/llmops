FROM python:3.11-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
COPY homework ./homework
COPY .guardrails ./.guardrails

RUN uv sync --frozen --no-dev

ENV PYTHONUNBUFFERED=1
