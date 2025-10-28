from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from .container import container

settings = container.settings
mcp = FastMCP(settings.mcp_server_name)


@mcp.tool()
async def answer_pricing_question(
    question: str,
    pricing_url: Optional[str] = None,
    pricing_yaml: Optional[str] = None,
    hints: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run pricing analysis workflows using LLM-guided orchestration."""

    cleaned_question = question.strip()
    if not cleaned_question:
        raise ValueError("Question is required.")

    agent = container.agent
    response_payload = await agent.handle_question(
        question=cleaned_question,
        pricing_url=pricing_url,
        yaml_content=pricing_yaml,
    )

    return {
        "answer": response_payload["answer"],
        "question": cleaned_question,
        "plan": response_payload["plan"],
        "result": response_payload["result"],
        "hints": hints or {},
    }


def main() -> None:
    mcp.run(transport=settings.mcp_transport)


if __name__ == "__main__":
    main()
