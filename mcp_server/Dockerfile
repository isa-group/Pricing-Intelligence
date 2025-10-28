# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip \
    && pip install .

EXPOSE 8085

CMD ["uvicorn", "pricing_mcp.http:app", "--host", "0.0.0.0", "--port", "8085"]
