# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv once so dependency installs are reproducible and fast
RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:${PATH}"

COPY pyproject.toml README.md ./
COPY src ./src

RUN uv pip install --system .

EXPOSE 8085

CMD ["python", "-m", "pricing_mcp.http_api"]
