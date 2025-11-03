# H.A.R.V.E.Y. Pricing Assistant API

FastAPI service that hosts H.A.R.V.E.Y. (Holistic Analysis and Regulation Virtual Expert for You).
The service launches the Pricing MCP server module via stdio and calls its MCP tools to execute pricing
workflows, then exposes a single HTTP `/chat` endpoint consumed by the frontend. No LLM or upstream API
keys are required in the MCP server when used this way, aligning with MCP’s client‑mediated access model.

## Local Development

```bash
cd harvey_api
uv venv
source .venv/bin/activate
uv pip install -e .[dev]
uvicorn harvey_api.app:app --reload --port 8086
```

Key settings (via environment variables) mirror those used by the MCP server. In particular:

- `MCP_SERVER_MODULE` (default: `pricing_mcp.mcp_server`) – Python module to launch via `-m`.
- `MCP_PYTHON_EXECUTABLE` (optional) – path to the Python binary to start the MCP server.
- `MCP_EXTRA_PYTHON_PATHS` (optional) – extra paths appended to PYTHONPATH for the server.

The service exposes:

- `GET /health` – health probe
- `POST /chat` – conversational endpoint for H.A.R.V.E.Y.

## Docker

Build and run the H.A.R.V.E.Y. API container:

```bash
docker build -f harvey_api/Dockerfile -t harvey-api .
docker run --env-file mcp_server/.env -p 8086:8086 harvey-api

## MCP compliance overview

HARVEY acts as an MCP client and follows the 2025‑06‑18 spec:

- Calls server tools with structured JSON arguments and expects JSON content blocks in responses.
- Reads server resources using `resources/read` (e.g. `resource://pricing/specification`).
- Does not advertise optional client capabilities for roots, sampling, or elicitation; these can be
	enabled in a future iteration if servers require them. Planning and LLM usage happen client‑side.
```
