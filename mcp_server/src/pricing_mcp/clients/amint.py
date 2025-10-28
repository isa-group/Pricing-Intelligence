from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from ..config import get_settings
from ..logging import get_logger

logger = get_logger(__name__)


class AMintError(Exception):
    """Raised when A-MINT transformation fails."""


@dataclass(slots=True)
class TransformOptions:
    url: str
    model: str = "gemini-2.5-flash"
    temperature: float = 0.7
    better_model: str = "gemini-2.5-pro"
    max_tries: int = 50
    base_url_override: Optional[str] = None


class AMintClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or str(settings.amint_base_url)).rstrip("/")
        self._api_key = api_key or settings.amint_api_key
        self._timeout = timeout_seconds or settings.http_timeout_seconds
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            headers=self._build_headers(),
        )

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json, application/x-yaml",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def aclose(self) -> None:
        await self._client.aclose()

    async def transform(
        self,
        options: TransformOptions,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: float = 1800.0,
    ) -> str:
        payload: dict[str, Any] = {
            "url": options.url,
            "model": options.model,
            "temperature": options.temperature,
            "better_model": options.better_model,
            "max_tries": options.max_tries,
        }
        if options.base_url_override:
            payload["base_url"] = options.base_url_override

        logger.info("amint.transform.request", url=options.url)

        response = await self._client.post("/api/v1/transform", json=payload)
        response.raise_for_status()
        task_id = response.json()["task_id"]

        logger.info("amint.transform.accepted", task_id=task_id)

        return await self._poll_transform(task_id, poll_interval_seconds, max_wait_seconds)

    async def _poll_transform(
        self,
        task_id: str,
        poll_interval_seconds: float,
        max_wait_seconds: float,
    ) -> str:
        elapsed = 0.0
        status_path = f"/api/v1/transform/status/{task_id}"
        while elapsed < max_wait_seconds:
            response = await self._client.get(status_path)

            content_type = response.headers.get("content-type", "")
            if "application/x-yaml" in content_type or "text/yaml" in content_type:
                logger.info("amint.transform.completed", task_id=task_id)
                return response.text

            data = response.json()
            status = data.get("status")
            if status == "failed":
                error = data.get("error") or "unknown error"
                logger.error("amint.transform.failed", task_id=task_id, error=error)
                raise AMintError(f"Transformation failed: {error}")

            if status in {"completed", "success"} and data.get("result_file"):
                # Some deployments may respond with metadata before streaming file
                download_response = await self._client.get(data["result_file"])
                download_response.raise_for_status()
                return download_response.text

            await asyncio.sleep(poll_interval_seconds)
            elapsed += poll_interval_seconds

        logger.error("amint.transform.timeout", task_id=task_id)
        raise AMintError("Timed out waiting for transformation result")
