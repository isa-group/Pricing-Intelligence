from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from .container import container, lifespan

app = FastAPI(title="Pricing Intelligence MCP HTTP", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str
    pricing_url: Optional[HttpUrl] = None
    pricing_yaml: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    plan: Dict[str, Any]
    result: Dict[str, Any]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "UP"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    agent = container.agent
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required.")
    yaml_content = request.pricing_yaml.strip() if request.pricing_yaml else None

    try:
        response_payload = await agent.handle_question(
            question=question,
            pricing_url=str(request.pricing_url) if request.pricing_url else None,
            yaml_content=yaml_content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - network dependent
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ChatResponse(
        answer=response_payload["answer"],
        plan=response_payload["plan"],
        result=response_payload["result"],
    )
