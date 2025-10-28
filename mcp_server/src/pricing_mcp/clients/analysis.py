from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from ..config import get_settings
from ..logging import get_logger

logger = get_logger(__name__)


class AnalysisError(Exception):
    """Raised when Analysis API calls fail."""


@dataclass(slots=True)
class AnalysisJobOptions:
    yaml_content: str
    operation: str
    solver: str = "minizinc"
    filters: Optional[Dict[str, Any]] = None
    objective: Optional[str] = None


class AnalysisClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or str(settings.analysis_base_url)).rstrip("/")
        self._api_key = api_key or settings.analysis_api_key
        self._timeout = timeout_seconds or settings.http_timeout_seconds
        headers = self._build_headers()
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout, headers=headers)

    def _build_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def aclose(self) -> None:
        await self._client.aclose()

    async def submit_job(
        self,
        options: AnalysisJobOptions,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: float = 120.0,
    ) -> dict[str, Any]:
        files = {
            "pricingFile": ("pricing.yaml", options.yaml_content, "application/x-yaml"),
        }
        data: dict[str, Any] = {
            "operation": options.operation,
            "solver": options.solver,
        }
        if options.filters is not None:
            data["filters"] = json.dumps(options.filters)
        if options.objective is not None:
            data["objective"] = options.objective

        logger.info("analysis.job.submit", operation=options.operation, solver=options.solver)

        response = await self._client.post("/api/v1/pricing/analysis", data=data, files=files)
        response.raise_for_status()
        payload = response.json()
        job_id = payload["jobId"]
        logger.info("analysis.job.accepted", job_id=job_id)
        return await self._poll_job(job_id, poll_interval_seconds, max_wait_seconds)

    async def _poll_job(
        self,
        job_id: str,
        poll_interval_seconds: float,
        max_wait_seconds: float,
    ) -> dict[str, Any]:
        elapsed = 0.0
        status_path = f"/api/v1/pricing/analysis/{job_id}"
        while elapsed < max_wait_seconds:
            response = await self._client.get(status_path)
            response.raise_for_status()
            payload = response.json()
            status = payload.get("status")
            if status == "COMPLETED":
                logger.info("analysis.job.completed", job_id=job_id)
                return payload.get("result", {})
            if status == "FAILED":
                error = payload.get("error")
                logger.error("analysis.job.failed", job_id=job_id, error=error)
                raise AnalysisError(f"Analysis job failed: {error}")

            await asyncio.sleep(poll_interval_seconds)
            elapsed += poll_interval_seconds

        logger.error("analysis.job.timeout", job_id=job_id)
        raise AnalysisError("Timed out waiting for analysis result")

    async def get_summary(self, yaml_content: str) -> dict[str, Any]:
        files = {
            "pricingFile": ("pricing.yaml", yaml_content, "application/x-yaml"),
        }
        response = await self._client.post("/api/v1/pricing/summary", files=files)
        response.raise_for_status()
        return response.json()
