from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from openai import OpenAI

DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

logger = logging.getLogger(__name__)


@dataclass
class GeminiClientConfig:
    api_key: str
    model: str
    base_url: str = DEFAULT_GEMINI_BASE_URL
    temperature: float = 0.7
    better_model: str | None = "gemini-2.5-pro"


class GeminiOpenAIClient:
    """Minimal OpenAI-compatible client tailored for Gemini models."""

    def __init__(self, config: GeminiClientConfig) -> None:
        self._config = config
        self._client = OpenAI(api_key=config.api_key, base_url=config.base_url)

    def make_full_request(
        self,
        initial_prompt: str,
        max_tries: int = 5,
        *,
        json_output: bool = True,
    ) -> str:
        state = _LLMGenerationState(prompt=initial_prompt, model=self._config.model)

        for attempt in range(1, max_tries + 1):
            state = self._step_generation(state)
            maybe_result = self._try_finalize(state, json_output)
            if maybe_result is not None:
                return maybe_result

            if attempt == max_tries:
                break

            state = self._prepare_retry(state, initial_prompt)

        raise ValueError("Could not obtain a complete response from the LLM.")

    def _send_prompt(self, prompt: str, model: str) -> tuple[str, str]:
        completion = self._client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self._config.temperature,
            reasoning_effort="high",
        )

        message = completion.choices[0].message
        content = message.content or ""
        finish_reason = completion.choices[0].finish_reason or ""
        return content, finish_reason

    def _step_generation(self, state: "_LLMGenerationState") -> "_LLMGenerationState":
        response_text, finish_reason = self._send_prompt(state.prompt, state.model)
        cleaned = self._normalize_response(response_text)
        accumulated = state.accumulated + cleaned
        return _LLMGenerationState(
            prompt=state.prompt,
            model=state.model,
            accumulated=accumulated,
            finish_reason=finish_reason,
            use_better_model=state.use_better_model,
        )

    def _try_finalize(self, state: "_LLMGenerationState", json_output: bool) -> str | None:
        if json_output:
            try:
                parsed = json.loads(state.accumulated)
            except json.JSONDecodeError:
                return None
            return json.dumps(parsed)

        if state.finish_reason != "length":
            return state.accumulated
        return None

    def _prepare_retry(self, state: "_LLMGenerationState", initial_prompt: str) -> "_LLMGenerationState":
        if self._config.better_model and not state.use_better_model:
            return _LLMGenerationState(
                prompt=initial_prompt,
                model=self._config.better_model,
                accumulated="",
                finish_reason="",
                use_better_model=True,
            )

        continue_prompt = self._build_continue_prompt(initial_prompt, state.accumulated)
        return _LLMGenerationState(
            prompt=continue_prompt,
            model=state.model,
            accumulated=state.accumulated,
            finish_reason="",
            use_better_model=state.use_better_model,
        )

    @staticmethod
    def _normalize_response(response: str) -> str:
        stripped = response.strip()
        if stripped.startswith("```") and stripped.endswith("```"):
            lines = stripped.splitlines()
            # Remove opening and closing code fences.
            return "\n".join(lines[1:-1]).strip()
        return stripped

    @staticmethod
    def _build_continue_prompt(initial_prompt: str, accumulated: str) -> str:
        return (
            "The previous response was truncated. Resume exactly where it stopped.\n"
            "<initial_prompt>\n"
            f"{initial_prompt}\n"
            "</initial_prompt>\n"
            "<partial_response>\n"
            f"{accumulated}\n"
            "</partial_response>"
        )


@dataclass
class _LLMGenerationState:
    prompt: str
    model: str
    accumulated: str = ""
    finish_reason: str = ""
    use_better_model: bool = False
