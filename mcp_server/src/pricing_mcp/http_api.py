from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

from .container import container


_MISSING_PRICING_INPUT_MSG = "pricing_url or pricing_yaml is required"


class SummaryRequest(BaseModel):
    pricing_url: Optional[HttpUrl] = None
    pricing_yaml: Optional[str] = None
    refresh: bool = False


class SubscriptionsRequest(BaseModel):
    pricing_url: Optional[HttpUrl] = None
    pricing_yaml: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    solver: str = "minizinc"
    refresh: bool = False


class OptimalRequest(SubscriptionsRequest):
    objective: str = "minimize"


@asynccontextmanager
async def lifespan(app: FastAPI):  # pragma: no cover - lifecycle glue
    try:
        yield
    finally:
        await container.shutdown()


app = FastAPI(title="Pricing Intelligence MCP API", lifespan=lifespan)


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "UP"}


# @app.post("/summary")
# async def summary_endpoint(payload: SummaryRequest) -> Dict[str, Any]:
#     if not (payload.pricing_url or payload.pricing_yaml):
#         raise HTTPException(status_code=400, detail=_MISSING_PRICING_INPUT_MSG)

#     return await container.workflow.run_summary(
#         url=str(payload.pricing_url) if payload.pricing_url else None,
#         yaml_content=payload.pricing_yaml,
#         refresh=payload.refresh,
#     )


# @app.post("/subscriptions")
# async def subscriptions_endpoint(payload: SubscriptionsRequest) -> Dict[str, Any]:
#     if not (payload.pricing_url or payload.pricing_yaml):
#         raise HTTPException(status_code=400, detail=_MISSING_PRICING_INPUT_MSG)

#     if payload.solver not in {"minizinc", "choco"}:
#         raise HTTPException(status_code=400, detail="solver must be 'minizinc' or 'choco'")

#     return await container.workflow.run_subscriptions(
#         url=str(payload.pricing_url) if payload.pricing_url else "",
#         filters=payload.filters,
#         solver=payload.solver,
#         refresh=payload.refresh,
#         yaml_content=payload.pricing_yaml,
#     )


# @app.post("/optimal")
# async def optimal_endpoint(payload: OptimalRequest) -> Dict[str, Any]:
#     if not (payload.pricing_url or payload.pricing_yaml):
#         raise HTTPException(status_code=400, detail=_MISSING_PRICING_INPUT_MSG)

#     if payload.solver not in {"minizinc", "choco"}:
#         raise HTTPException(status_code=400, detail="solver must be 'minizinc' or 'choco'")

#     if payload.objective not in {"minimize", "maximize"}:
#         raise HTTPException(status_code=400, detail="objective must be 'minimize' or 'maximize'")

#     return await container.workflow.run_optimal(
#         url=str(payload.pricing_url) if payload.pricing_url else "",
#         filters=payload.filters,
#         solver=payload.solver,
#         objective=payload.objective,
#         refresh=payload.refresh,
#         yaml_content=payload.pricing_yaml,
#     )


def main() -> None:  # pragma: no cover - convenience runner
    import uvicorn  # type: ignore[import-not-found]

    settings = container.settings
    uvicorn.run(app, host=settings.http_host, port=settings.http_port)


if __name__ == "__main__":  # pragma: no cover - module entrypoint
    main()
