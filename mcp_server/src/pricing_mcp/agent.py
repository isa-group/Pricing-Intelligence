from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .config import get_settings
from .logging import get_logger
from .workflows.pricing import PricingWorkflow
from .llm_client import DEFAULT_GEMINI_BASE_URL, GeminiClientConfig, GeminiOpenAIClient

logger = get_logger(__name__)
ALLOWED_ACTIONS = {"optimal", "subscriptions", "summary"}


@dataclass
class PlannedAction:
    name: str
    objective: Optional[str] = None
    pricing_url: Optional[str] = None

PLAN_SYSTEM_PROMPT = """You orchestrate pricing intelligence workflows.

Actions you can sequence:
- "subscriptions": calls the analysis service to enumerate every subscription configuration. With no filters it returns the full configuration space; with filters it limits to matching options. The payload always includes "cardinality" so you know the configuration-space size after applying filters.
- "optimal": runs the optimizer over the configuration space. With objective="minimize" (default) it returns the cheapest matching subscription; with objective="maximize" it returns the most expensive. Any filters reduce the search space and the payload still reports the resulting cardinality.
- "summary": produces a textual synopsis of the pricing context or latest tool outputs without performing heavy analysis. Use it to brief the user or when no data-backed action is necessary.

Given the user's request and context, respond with JSON containing:
- actions: ordered list of zero or more actions. Each entry may be a string (e.g. "summary") or an object like {"name": "optimal", "objective": "maximize"}. Use objects when you need to override the default objective or other parameters for a single step. Use an empty list when you can answer directly without tools.
- pricing_url: optional URL inferred from the conversation.
- requires_uploaded_yaml: true only when a user-provided Pricing2Yaml file is mandatory to proceed.
- intent_summary: concise natural-language rationale describing how the plan addresses the request.
- filters: optional JSON object with precise constraints (e.g. {"maxMonthlyPrice": 100, "requiredFeatures": ["standardSupport"]}). Mention how the filters will influence the configuration space.
- objective: fallback objective for optimal steps that do not define their own objective (default "minimize").
- solver: "minizinc" or "choco" (prefer "minizinc" unless the user asks otherwise).
- refresh: true only when a new transformation is required because fresh pricing data (URL or YAML) was provided.
- use_pricing2yaml_spec: boolean indicating whether the answer should consult the Pricing2Yaml specification excerpt provided by the system.

Guidance:
- Consider chaining actions for complex questions (e.g. [{"name": "subscriptions"}, {"name": "optimal", "objective": "maximize"}]).
- Always reference detected pricing URLs in pricing_url; do not invent links.
- Choose empty actions only when existing knowledge or the specification excerpt is sufficient to answer confidently.
- Set requires_uploaded_yaml to true only when the assistant cannot proceed without a local file; otherwise keep it false to avoid blocking the user.
- When the user asks about schema, syntax, or validation details, set use_pricing2yaml_spec to true.
- Keep filters as a JSON object; omit the key when no constraints are required.

Always return strictly valid JSON with double quotes and no trailing text.
"""

ANSWER_SYSTEM_PROMPT = """You are a pricing intelligence assistant.
Use the provided plan, tool payload (which may be empty), and optional Pricing2Yaml excerpt to answer conversationally.
- Explain recommended plans or insights and reference key metrics such as price, objective value, or configuration cardinality when available.
- If use_pricing2yaml_spec is true, consult the supplied specification excerpt for authoritative details.
- When no actions ran, clarify that the response is based on existing context and highlight any assumptions.
- If tooling reported errors or missing inputs, communicate them plainly and request the needed information.
"""


class PricingAgent:
    def __init__(self, workflow: PricingWorkflow) -> None:
        self._workflow = workflow
        settings = get_settings()
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required for natural language orchestration")
        client_config = GeminiClientConfig(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            base_url=settings.gemini_base_url or DEFAULT_GEMINI_BASE_URL,
            better_model=settings.gemini_better_model,
        )
        self._llm = GeminiOpenAIClient(client_config)
        self._spec_excerpt = self._load_pricing2yaml_spec_excerpt()

    async def handle_question(
        self,
        question: str,
        pricing_url: Optional[str],
        yaml_content: Optional[str],
    ) -> Dict[str, Any]:
        plan = await self._generate_plan(question, pricing_url, yaml_content)
        self._validate_yaml_requirement(plan, yaml_content)

        actions = self._normalize_actions(plan.get("actions"))
        solver = plan.get("solver", "minizinc")
        objective = plan.get("objective", "minimize")
        filters = self._extract_filters(plan.get("filters"))
        refresh = bool(plan.get("refresh", False))
        url = self._resolve_pricing_reference(plan.get("pricing_url"), pricing_url, yaml_content)

        results, last_payload = await self._execute_actions(
            actions=actions,
            url=url,
            refresh=refresh,
            solver=solver,
            filters=filters,
            objective=objective,
            yaml_content=yaml_content,
        )

        payload_for_answer, result_payload = self._compose_results_payload(actions, results, last_payload)
        answer = await self._generate_answer(question, plan, payload_for_answer)

        return {
            "plan": plan,
            "result": result_payload,
            "answer": answer,
        }

    async def _generate_plan(
        self, question: str, pricing_url: Optional[str], yaml_content: Optional[str]
    ) -> Dict[str, Any]:
        messages = [PLAN_SYSTEM_PROMPT]
        messages.append(f"Question: {question}")
        if pricing_url:
            messages.append(f"Candidate pricing URL: {pricing_url}")
        if yaml_content:
            snippet = yaml_content[:2000]
            messages.append("User provided YAML snippet (truncated to 2000 characters):")
            messages.append(snippet)
        else:
            messages.append("User provided YAML: False")
        if self._should_include_spec(question) and self._spec_excerpt:
            messages.append("Pricing2Yaml specification excerpt (truncated):")
            messages.append(self._spec_excerpt)

        text = await asyncio.to_thread(
            self._llm.make_full_request,
            "\n".join(messages),
            5,
            json_output=True,
        )
        try:
            plan = json.loads(text)
        except json.JSONDecodeError as exc:  # pragma: no cover - unexpected LLM response
            logger.error("pricing.agent.plan_parse_error", raw=text, error=str(exc))
            raise ValueError("Failed to interpret assistant plan. Please rephrase your request.")

        return plan

    async def _generate_answer(
        self, question: str, plan: Dict[str, Any], payload: Dict[str, Any]
    ) -> str:
        result_snippet = json.dumps(payload, ensure_ascii=False)[:4000]
        messages = [ANSWER_SYSTEM_PROMPT]
        messages.append(f"Question: {question}")
        messages.append(f"Plan: {json.dumps(plan, ensure_ascii=False)}")
        messages.append(f"Tool payload: {result_snippet}")
        if self._should_include_spec(question, plan) and self._spec_excerpt:
            messages.append("Pricing2Yaml specification excerpt (truncated):")
            messages.append(self._spec_excerpt)

        response = await asyncio.to_thread(
            self._llm.make_full_request,
            "\n".join(messages),
            5,
            json_output=False,
        )
        return response or "No answer could be generated."

    def _validate_yaml_requirement(self, plan: Dict[str, Any], yaml_content: Optional[str]) -> None:
        if plan.get("requires_uploaded_yaml") and not yaml_content:
            raise ValueError(
                "The assistant needs a YAML pricing file to proceed. Please upload one and retry."
            )

    def _normalize_actions(self, raw_actions: Any) -> List[PlannedAction]:
        normalized: List[PlannedAction] = []
        if raw_actions in (None, []):
            return normalized
        if not isinstance(raw_actions, list):
            logger.warning("pricing.agent.invalid_actions", requested=raw_actions)
            return normalized

        for entry in raw_actions:
            planned_action = self._parse_action_entry(entry)
            if planned_action:
                normalized.append(planned_action)

        return normalized

    def _parse_action_entry(self, entry: Any) -> Optional[PlannedAction]:
        if isinstance(entry, str):
            if entry in ALLOWED_ACTIONS:
                return PlannedAction(name=entry)
            logger.warning("pricing.agent.unsupported_action", requested=entry)
            return None

        if isinstance(entry, dict):
            name = entry.get("name")
            if not isinstance(name, str) or name not in ALLOWED_ACTIONS:
                logger.warning("pricing.agent.invalid_action_object", requested=entry)
                return None
            objective = entry.get("objective")
            if objective not in (None, "minimize", "maximize"):
                logger.warning("pricing.agent.invalid_objective", action=name, objective=objective)
                objective = None
            pricing_url = entry.get("pricing_url") or entry.get("url")
            if pricing_url is not None and not isinstance(pricing_url, str):
                logger.warning("pricing.agent.invalid_pricing_url", action=name, pricing_url=pricing_url)
                pricing_url = None
            return PlannedAction(name=name, objective=objective, pricing_url=pricing_url)

        logger.warning("pricing.agent.unrecognized_action_entry", entry=entry)
        return None

    def _extract_filters(self, raw_filters: Any) -> Optional[Dict[str, Any]]:
        if raw_filters is None or raw_filters == {}:
            return None
        if isinstance(raw_filters, dict):
            return raw_filters
        logger.warning("pricing.agent.invalid_filters", provided=raw_filters)
        return None

    def _resolve_pricing_reference(
        self,
        plan_url: Optional[str],
        incoming_url: Optional[str],
        yaml_content: Optional[str],
    ) -> Optional[str]:
        resolved_plan_url: Optional[str] = None
        if isinstance(plan_url, str):
            resolved_plan_url = plan_url
        elif isinstance(plan_url, list):
            resolved_plan_url = plan_url[0] if plan_url else None
        elif plan_url is not None:
            logger.warning("pricing.agent.unexpected_pricing_url", plan_url=plan_url)

        url = resolved_plan_url or incoming_url
        if yaml_content and not url:
            return "uploaded://pricing"
        return url

    async def _execute_actions(
        self,
        *,
        actions: List[PlannedAction],
        url: Optional[str],
        refresh: bool,
        solver: str,
        filters: Optional[Dict[str, Any]],
        objective: str,
        yaml_content: Optional[str],
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        if not actions:
            return [], None

        self._ensure_pricing_context(actions, url, yaml_content)

        results: List[Dict[str, Any]] = []
        transformed_urls: Set[str] = set()
        last_payload: Optional[Dict[str, Any]] = None
        refresh_requested = bool(refresh)

        for index, action in enumerate(actions):
            action_url, effective_refresh, action_yaml = self._prepare_action_inputs(
                action=action,
                default_url=url,
                refresh_requested=refresh_requested,
                transformed_urls=transformed_urls,
                yaml_content=yaml_content,
            )

            payload = await self._run_single_action(
                action=action,
                url=action_url,
                refresh=effective_refresh,
                solver=solver,
                filters=filters,
                objective=objective,
                yaml_content=action_yaml,
            )

            if effective_refresh and action_url:
                transformed_urls.add(action_url)

            step_record: Dict[str, Any] = {
                "index": index,
                "action": action.name,
                "payload": payload,
            }
            if action.name == "optimal":
                step_record["objective"] = action.objective or objective
            if action_url:
                step_record["url"] = action_url
            results.append(step_record)
            last_payload = payload

        return results, last_payload

    def _ensure_pricing_context(
        self,
        actions: List[PlannedAction],
        url: Optional[str],
        yaml_content: Optional[str],
    ) -> None:
        for action in actions:
            action_url = action.pricing_url or url
            if action.name in {"subscriptions", "optimal"} and not (action_url or yaml_content):
                raise ValueError(
                    "Running subscriptions or optimal analysis requires a pricing URL or an uploaded Pricing2Yaml file."
                )
            if action.name == "summary" and not (action_url or yaml_content):
                raise ValueError(
                    "A summary requires pricing context. Provide a pricing URL or Pricing2Yaml upload before running it."
                )

    def _prepare_action_inputs(
        self,
        *,
        action: PlannedAction,
        default_url: Optional[str],
        refresh_requested: bool,
        transformed_urls: Set[str],
        yaml_content: Optional[str],
    ) -> Tuple[Optional[str], bool, Optional[str]]:
        action_url = action.pricing_url or default_url
        effective_refresh = False
        if refresh_requested and action_url:
            effective_refresh = action_url not in transformed_urls
        action_yaml = yaml_content if action_url is None or action_url == default_url else None
        return action_url, effective_refresh, action_yaml

    async def _run_single_action(
        self,
        *,
        action: PlannedAction,
        url: Optional[str],
        refresh: bool,
        solver: str,
        filters: Optional[Dict[str, Any]],
        objective: str,
        yaml_content: Optional[str],
    ) -> Dict[str, Any]:
        resolved_objective = action.objective or objective
        if action.name == "summary":
            return await self._workflow.run_summary(url=url, yaml_content=yaml_content, refresh=refresh)
        if action.name == "subscriptions":
            return await self._workflow.run_subscriptions(
                url=url or "",
                filters=filters,
                solver=solver,
                refresh=refresh,
                yaml_content=yaml_content,
            )
        return await self._workflow.run_optimal(
            url=url or "",
            filters=filters,
            solver=solver,
            objective=resolved_objective,
            refresh=refresh,
            yaml_content=yaml_content,
        )

    def _compose_results_payload(
        self,
        actions: List[PlannedAction],
        results: List[Dict[str, Any]],
        last_payload: Optional[Dict[str, Any]],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if not results:
            empty_payload: Dict[str, Any] = {"steps": []}
            return empty_payload, empty_payload

        if len(results) == 1:
            step_record = results[0]
            payload = step_record.get("payload")
            if payload is None:
                payload = last_payload or {}
            return payload, step_record

        combined: Dict[str, Any] = {
            "actions": [action.name for action in actions],
            "steps": results,
        }
        if last_payload is not None:
            combined["lastPayload"] = last_payload
        return combined, combined

    def _load_pricing2yaml_spec_excerpt(self, max_chars: int = 6000) -> str:
        spec_path = Path(__file__).resolve().parent / "docs" / "pricing2YamlSpecification.md"
        try:
            content = spec_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning("pricing.agent.spec_missing", path=str(spec_path))
            return ""
        return content[:max_chars]

    def _should_include_spec(self, question: str, plan: Optional[Dict[str, Any]] = None) -> bool:
        if plan and plan.get("use_pricing2yaml_spec"):
            return True
        lowered = question.lower()
        keywords = ["pricing2yaml", "pricing 2 yaml", "yaml spec", "schema", "syntax", "ipricing"]
        return any(keyword in lowered for keyword in keywords)