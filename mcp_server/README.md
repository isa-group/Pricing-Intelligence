# Pricing Intelligence MCP Server

Python-based Model Context Protocol (MCP) server that orchestrates A-MINT transformation APIs and the Analysis API to answer pricing questions.

## Features

- Wraps A-MINT transformation endpoint to obtain pricing YAML models from SaaS web pages.
- Calls the Analysis API to run optimal subscription, subscription enumeration, and validation workflows.
- Exposes MCP tools (`summary`, `subscriptions`, `optimal`, `validate`, `iPricing`) for host LLMs.
- Provides caching, observability, and configuration management.

## MCP compliance overview

This server is implemented with the official Python MCP library and follows the 2025‑06‑18 revision of the MCP spec:

- Server primitives: tools and resources, per the Server Overview.
- Resources: declares a static resource `resource://pricing/specification` that returns the Pricing2Yaml spec excerpt. It is exposed via the MCP Resources feature and is readable with `resources/read`.
- Tools: all tool results are returned as JSON content blocks so clients don’t need to parse text.
- Transport: stdio transport by default, as recommended for local MCP servers. WebSocket/HTTP facade can be enabled separately.

Notes:
- Resource subscriptions and resource template URIs are not currently advertised; they are optional per the spec and can be added later if needed.
- Errors raised from tool handlers are surfaced by the MCP runtime as JSON‑RPC errors. Inputs are validated early with clear messages.

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

# Optional HTTP facade
# The FastAPI app exposes /health; workflow endpoints are currently disabled.
# Enable them if you need a non‑MCP HTTP integration.
# python -m pricing_mcp.http_api
```

The companion `harvey_api` project launches this MCP server via stdio and calls the MCP tools directly; no API keys are shared with clients.

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
