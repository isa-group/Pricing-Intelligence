from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from .clients import MCPClientError
from .container import container, lifespan

app = FastAPI(title="H.A.R.V.E.Y. Pricing Assistant API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str
    pricing_url: Optional[HttpUrl] = None
    pricing_urls: Optional[List[HttpUrl]] = None
    pricing_yaml: Optional[str] = None
    pricing_yamls: Optional[List[str]] = None


class ChatResponse(BaseModel):
    answer: str
    plan: Dict[str, Any]
    result: Dict[str, Any]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "UP"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required.")
    pricing_urls: List[str] = []
    if request.pricing_url:
        pricing_urls.append(str(request.pricing_url))
    if request.pricing_urls:
        pricing_urls.extend(str(url) for url in request.pricing_urls)

    pricing_yamls: List[str] = []
    if request.pricing_yaml:
        stripped = request.pricing_yaml.strip()
        if stripped:
            pricing_yamls.append(stripped)
    if request.pricing_yamls:
        pricing_yamls.extend(yaml.strip() for yaml in request.pricing_yamls if yaml and yaml.strip())

    # Deduplicate while preserving order to avoid duplicated contexts when both singular
    # and plural fields are provided or when identical contents are repeated.
    if pricing_urls:
        pricing_urls = list(dict.fromkeys(pricing_urls))
    if pricing_yamls:
        pricing_yamls = list(dict.fromkeys(pricing_yamls))

    try:
        response_payload = await container.agent.handle_question(
            question=question,
            pricing_urls=pricing_urls,
            yaml_contents=pricing_yamls,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MCPClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - network dependent
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ChatResponse(
        answer=response_payload["answer"],
        plan=response_payload["plan"],
        result=response_payload["result"],
    )
