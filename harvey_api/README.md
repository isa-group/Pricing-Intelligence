# H.A.R.V.E.Y. Pricing Assistant API

FastAPI service that hosts H.A.R.V.E.Y. (Holistic Analysis and Regulation Virtual Expert for You).
The service connects to the Pricing MCP HTTP API (`pricing_mcp.http_api`) to execute pricing
workflows and exposes an HTTP `/chat` endpoint consumed by the frontend.

## Local Development

```bash
cd harvey_api
uv venv
source .venv/bin/activate
uv pip install -e .[dev]
uvicorn harvey_api.app:app --reload --port 8086
```

Set `MCP_BASE_URL` to the URL where the MCP HTTP API is reachable (defaults to
`http://localhost:8085`). Other environment variables mirror those used by the MCP
server (copy `.env.example` from `mcp_server` if needed). The service exposes:

- `GET /health` – health probe
- `POST /chat` – conversational endpoint for H.A.R.V.E.Y.

## Docker

Build and run the H.A.R.V.E.Y. API container:

```bash
docker build -f harvey_api/Dockerfile -t harvey-api .
docker run --env-file mcp_server/.env -p 8086:8086 harvey-api
```
