# Pricing Intelligence MCP Server

Python-based Model Context Protocol (MCP) server that orchestrates A-MINT transformation APIs and the Analysis API to answer pricing questions.

## Features

- Wraps A-MINT transformation endpoint to obtain pricing YAML models from SaaS web pages.
- Calls the Analysis API to run optimal subscription, subscription enumeration, and validation workflows.
- Exposes MCP tools for host LLMs and an HTTP interface for the frontend chat experience.
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

# Launch server (stdio transport)
python -m pricing_mcp
```

Use `uvicorn pricing_mcp.http:app --reload` to expose the HTTP API for the frontend integration.

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

## Docker

Build and run the MCP server and frontend via Docker Compose from the repository root:

```bash
docker compose up --build mcp-server mcp-frontend
```

The MCP HTTP API will be available at `http://localhost:8085`, and the chat frontend at `http://localhost:8086`.
