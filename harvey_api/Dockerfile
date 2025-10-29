# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:${PATH}"

# Install Pricing MCP server into the same environment
COPY mcp_server/pyproject.toml ./mcp_server/pyproject.toml
COPY mcp_server/README.md ./mcp_server/README.md
COPY mcp_server/src ./mcp_server/src
COPY mcp_server/.env.example ./mcp_server/.env
RUN uv pip install --system ./mcp_server

# Copy H.A.R.V.E.Y. API sources
COPY harvey_api/pyproject.toml ./pyproject.toml
COPY harvey_api/README.md ./README.md
COPY harvey_api/src ./src

# Install H.A.R.V.E.Y. API
RUN uv pip install --system .

EXPOSE 8086

CMD ["uvicorn", "harvey_api.app:app", "--host", "0.0.0.0", "--port", "8086"]
