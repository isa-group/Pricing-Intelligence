# Pricing Intelligence MCP Server

Python-based Model Context Protocol (MCP) server that orchestrates A-MINT transformation APIs and the Analysis API to answer pricing questions.

## Features

- Wraps A-MINT transformation endpoint to obtain pricing YAML models from SaaS web pages.
- Calls the Analysis API to run optimal subscription, subscription enumeration, and validation workflows.
- Exposes MCP tools (`summary`, `subscriptions`, `optimal`) for host LLMs.
- Serves an HTTP facade (`/summary`, `/subscriptions`, `/optimal`) so external services (e.g. HARVEY) can call the workflows without direct access to A-MINT or Analysis.
- Provides caching, observability, and configuration management.

## Local Development

```bash
# Create and activate virtualenv
cd mcp_server
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -e .[dev]

# Run tests
pytest

# Launch MCP server (stdio transport)
python -m pricing_mcp

# Launch HTTP API (websocket/HTTP transport)
python -m pricing_mcp.http_api
```

Client applications must call the MCP HTTP API; direct access to A-MINT or Analysis is reserved for this service. The companion `harvey_api` project consumes these endpoints to power conversational workflows.

## Environment Variables

Copy `.env.example` to `.env` and adjust the service endpoints if needed:

```
cp .env.example .env
```

Key variables:

- `AMINT_BASE_URL` – base URL for the A-MINT transformation API
- `ANALYSIS_BASE_URL` – base URL for the Analysis API
- `CACHE_BACKEND` – `memory` (default) or `redis`
- `LOG_LEVEL` – logging level, e.g. `INFO`
- `HTTP_HOST`, `HTTP_PORT` – bind address and port for the HTTP API

## Docker

Build and run the MCP server and frontend via Docker Compose from the repository root:

```bash
docker compose up --build mcp-server harvey-api
```

Run the dedicated `harvey_api` service to expose the chat endpoint for the frontend.
