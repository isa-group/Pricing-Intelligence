from __future__ import annotations

import asyncio
import json
import re
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .clients import MCPClientError, MCPWorkflowClient
from .config import get_settings
from .logging import get_logger
from .llm_client import (
    DEFAULT_GEMINI_BASE_URL,
    GeminiClientConfig,
    GeminiOpenAIClient,
)

logger = get_logger(__name__)
ALLOWED_ACTIONS = {"optimal", "subscriptions", "summary", "ipricing"}
SPEC_RESOURCE_ID = "resource://pricing/specification"
PLAN_REQUEST_MAX_ATTEMPTS = 3
URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+")

PLAN_RESPONSE_FORMAT_INSTRUCTIONS = """Respond with a single JSON object that matches this schema (JSON order is flexible):
{
    "actions": [...],
    "pricing_url": string|null,
    "requires_uploaded_yaml": boolean,
    "intent_summary": string,
    "filters": object|null,
    "objective": "minimize"|"maximize",
    "solver": "minizinc"|"choco",
    "refresh": boolean,
    "use_pricing2yaml_spec": boolean
}
Rules:
- Produce valid JSON with double quotes only. Do not wrap the response in Markdown fences or natural language.
- Each entry in "actions" must be either a string ("summary") or an object like {"name": "optimal", "objective": "maximize"}. Use objects when overriding the default objective or URL.
- Only set requires_uploaded_yaml when a user-supplied Pricing2Yaml is mandatory to proceed. Keep it false otherwise to avoid blocking the user.
- Set use_pricing2yaml_spec to true whenever the user asks about schema, syntax, or validation details so the agent consults the specification excerpt.
- Keep filters as an object when present; omit the key when no filters are required.
- You may add extra metadata fields if requested, but never omit the required keys.
- If required actions are provided later in this prompt, include each one exactly once in the given order. You may add other actions before or after only when justified.
- Use "minizinc" as the solver unless the user explicitly asks for another option.
- Prefer the provided pricing URL; fall back to uploaded://pricing when working solely with uploaded YAML content.
- Leave actions empty only when you can confidently answer the question without calling any tools.
- When multiple pricing URLs or uploaded YAML aliases are available, set pricing_url on each action to the specific URL or alias that action should use (e.g. "uploaded://pricing/2").
Example response:
{"actions":["subscriptions",{"name":"optimal","objective":"minimize"},{"name":"optimal","objective":"maximize"}],"pricing_url":"uploaded://pricing","requires_uploaded_yaml":false,"intent_summary":"Explain reasoning here","filters":null,"objective":"minimize","solver":"minizinc","refresh":true,"use_pricing2yaml_spec":false}
"""

DEFAULT_REQUIRED_ACTION_PROMPT = """You decide whether tool calls are required to answer a user's pricing question accurately.

Available tools:
- "summary": accepts a pricing URL or uploaded YAML and returns a JSON payload with per-category counts (e.g. numberOfFeatures, numberOfIntegrationFeatures, numberOfSupportFeatures), plan-level metadata (storage limits, API quotas, seat ranges), and contextual flags describing billing or provisioning notes. The response does not list individual subscriptions, but it gives authoritative counts straight from the Pricing2Yaml model.
- "ipricing": returns the canonical Pricing2Yaml (iPricing) document. It uses the A-MINT pipeline when a pricing URL is supplied and simply returns uploaded YAML when present. Use it whenever the user requests the YAML source, wants to download/export the pricing, or needs to inspect the raw configuration.
- "subscriptions": accepts a pricing URL/YAML, optional filters, solver choice, and refresh flag. It enumerates every subscription configuration that matches the filters and returns an array of entries with `subscription` details (plan name, included features/add-ons) plus pricing fields. The payload always includes a top-level `cardinality` showing how many configurations were found.
- "optimal": accepts the same inputs as `subscriptions` plus an `objective` (minimize or maximize). It runs the optimiser over the configuration space and returns the best matching configuration, including its computed `cost`, `currency`, the chosen `subscription` structure, any selected add-ons, and the analysed `cardinality` for traceability.

Instructions:
- Analyse the question and determine the minimal set of tool invocations needed for a correct, data-backed answer.
- Use "ipricing" whenever the user needs the Pricing2Yaml document itself (e.g. requests the YAML, asks for an iPricing file, or wants to export/download the configuration). Do not rely on textual summaries when the raw document is requested.
- Use "summary" for requests about feature counts, integration availability, plan metadata, or any aggregated statistics that come from the pricing YAML.
- When a question references the number or count of features, integrations, limits, add-ons, or any other catalogue items, always include the "summary" tool—even if a YAML snippet is provided. Do not attempt to count items manually from truncated content.
- Use "subscriptions" when the user asks for the number of subscriptions, configurations, or plan variants.
- Include an optimal step with objective="minimize" when the user requests the best, cheapest, lowest-cost, or most advantageous option.
- Include an optimal step with objective="maximize" when the user asks for the most expensive or highest-priced option.
- Return an empty list only when the question can be answered directly from persistent conversation context without additional tool calls.
- When multiple pricing URLs or uploaded YAML aliases exist, include a pricing_url field on each required action using the specific URL or alias (e.g. "uploaded://pricing/2") so later planning stays unambiguous.

Mandatory rules:
- If the question mentions "how many" or "number of" together with "feature", "integration", "limit", "addon", or similar catalogue terms, the response MUST include "summary" in required_actions.

Respond with strictly valid JSON using this schema:
{
    "required_actions": [...]
}
Each entry must be either a string ("summary") or an object like {"name": "optimal", "objective": "maximize"}."""


@dataclass
class PlannedAction:
    name: str
    objective: Optional[str] = None
    pricing_url: Optional[str] = None

DEFAULT_PLAN_PROMPT = """You orchestrate pricing intelligence workflows on behalf of H.A.R.V.E.Y., the Holistic Analysis and Regulation Virtual Expert for You.

Available tools:
- "subscriptions": accepts a pricing URL or uploaded YAML plus optional filters. It enumerates every subscription configuration and returns an array of entries describing each `subscription` (plan code, add-ons, included features) along with pricing meta-data. The response always surfaces a top-level `cardinality` representing the configuration-space size after filters.
- "optimal": accepts the same inputs as `subscriptions` and an `objective` argument. It runs the optimiser to produce the cheapest (`objective="minimize"`) or most expensive (`objective="maximize"`) configuration, returning the winning `subscription`, its computed `cost`, currency, selected add-ons, and the evaluated `cardinality`.
- "summary": accepts a pricing URL or uploaded YAML and returns catalogue metrics such as numberOfFeatures, counts per feature category, seat/storage limits, API quotas, and other aggregated insights derived from the Pricing2Yaml document. Use it whenever you need counts or descriptive metadata rather than full optimisation output.
- "ipricing": accepts a pricing URL or uploaded YAML and returns the canonical Pricing2Yaml document, invoking the A-MINT pipeline when a URL is supplied. Use it whenever the user needs to download, inspect, or export the raw YAML configuration.

Planning guidance:
- Think through the user's intent before emitting actions. Use the workflow tools whenever data, optimisation, or configuration counts are required. Only leave actions empty when the answer is already implicit in the conversation or specification excerpt.
- When the user asks for the YAML/iPricing document or needs the raw configuration file, include the "ipricing" tool before providing the answer so the YAML can be offered or referenced directly.
- When the user asks for the number of subscriptions, configurations, or plan variants, include the "subscriptions" tool before any optimisation so you obtain the correct cardinality.
- When the user asks for the number or count of features, integrations, limits, add-ons, or other catalogue elements, include the "summary" tool rather than counting manually—even if a YAML snippet is provided.
- When the user asks for the cheapest or "best" option (unless they explicitly state otherwise), include an optimal step that minimizes cost ({"name": "optimal", "objective": "minimize"}).
- When the user asks for the most expensive option, include an optimal step that maximizes cost ({"name": "optimal", "objective": "maximize"}).
- Set use_pricing2yaml_spec to true when the question involves schema, syntax, or validation details so that the agent consults the Pricing2Yaml reference.
- Prefer "minizinc" as the solver unless the user explicitly selects an alternative.

Follow the response format rules that accompany this prompt.
"""

DEFAULT_ANSWER_PROMPT = """You are H.A.R.V.E.Y., the Holistic Analysis and Regulation Virtual Expert for You.
Use the provided plan, tool payload (which may be empty), and optional Pricing2Yaml excerpt to answer conversationally.
- Explain recommended plans or insights and reference key metrics such as price, objective value, or configuration cardinality when available.
- If use_pricing2yaml_spec is true, consult the supplied specification excerpt for authoritative details.
- When a Pricing2Yaml specification excerpt is provided, describe the concept using the excerpt instead of asking the user for documentation. Only request additional material if the excerpt is explicitly empty.
- When no actions ran, clarify that the response is based on existing context and highlight any assumptions.
- If tooling reported errors or missing inputs, communicate them plainly and request the needed information.
"""


class HarveyAgent:
    def __init__(self, workflow: MCPWorkflowClient) -> None:
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
        self._planning_prompt: Optional[str] = None
        self._answer_prompt: Optional[str] = None
        self._spec_excerpt: Optional[str] = None

    async def handle_question(
        self,
        question: str,
        pricing_urls: Optional[List[str]] = None,
        yaml_contents: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        provided_urls = self._deduplicate(pricing_urls or [])
        provided_yamls = [content for content in (yaml_contents or []) if content]
        detected_urls = self._extract_urls_from_question(question)
        combined_urls = self._deduplicate(provided_urls + detected_urls)
        yaml_alias_map = self._build_yaml_alias_map(provided_yamls)

        plan = await self._generate_plan(
            question,
            pricing_urls=combined_urls,
            yaml_alias_map=yaml_alias_map,
        )
        self._validate_yaml_requirement(plan, provided_yamls)

        actions = self._normalize_actions(plan.get("actions"))
        solver = plan.get("solver", "minizinc")
        objective = plan.get("objective", "minimize")
        filters = self._extract_filters(plan.get("filters"))
        refresh = bool(plan.get("refresh", False))
        default_reference = self._resolve_default_reference(
            plan_reference=plan.get("pricing_url"),
            plan_references=plan.get("pricing_urls"),
            available_urls=combined_urls,
            yaml_aliases=list(yaml_alias_map.keys()),
        )

        results, last_payload = await self._execute_actions(
            actions=actions,
            default_reference=default_reference,
            available_urls=combined_urls,
            refresh=refresh,
            solver=solver,
            filters=filters,
            objective=objective,
            yaml_alias_map=yaml_alias_map,
        )

        payload_for_answer, result_payload = self._compose_results_payload(actions, results, last_payload)
        answer = await self._generate_answer(question, plan, payload_for_answer)

        return {
            "plan": plan,
            "result": result_payload,
            "answer": answer,
        }

    async def _generate_plan(
        self,
        question: str,
        pricing_urls: List[str],
        yaml_alias_map: Dict[str, str],
    ) -> Dict[str, Any]:
        plan_prompt = self._get_planning_prompt()
        required_actions_raw = await self._infer_required_actions(
            question=question,
            pricing_urls=pricing_urls,
            yaml_alias_map=yaml_alias_map,
        )
        spec_excerpt: Optional[str] = None
        if self._should_include_spec(question):
            spec_excerpt = await self._get_spec_excerpt()

        base_messages = self._build_plan_request_messages(
            plan_prompt=plan_prompt,
            question=question,
            pricing_urls=pricing_urls,
            yaml_alias_map=yaml_alias_map,
            spec_excerpt=spec_excerpt,
            required_actions=required_actions_raw,
        )

        attempt_errors: List[str] = []
        for _ in range(PLAN_REQUEST_MAX_ATTEMPTS):
            attempt_messages = list(base_messages)
            if attempt_errors:
                attempt_messages.append(
                    "Previous attempt issues: " + attempt_errors[-1]
                )
                attempt_messages.append(
                    "Return a corrected JSON plan that satisfies all requirements."
                )

            try:
                text = await asyncio.to_thread(
                    self._llm.make_full_request,
                    "\n".join(attempt_messages),
                    json_output=True,
                )
            except ValueError as exc:
                attempt_errors.append(f"LLM response was not valid JSON: {exc}")
                continue

            try:
                plan = self._parse_plan_text(
                    text=text,
                    question=question,
                    pricing_urls=pricing_urls,
                    yaml_alias_map=yaml_alias_map,
                    allow_fallback=False,
                )
            except ValueError as exc:
                attempt_errors.append(str(exc))
                continue

            if self._actions_satisfy_requirements(plan.get("actions"), required_actions_raw):
                return plan

            attempt_errors.append(
                self._describe_required_action_mismatch(
                    plan.get("actions"), required_actions_raw
                )
            )

        raise ValueError(
            "Failed to obtain a planning response that satisfies tool requirements. "
            + (attempt_errors[-1] if attempt_errors else "")
        )

    async def _infer_required_actions(
        self,
        *,
        question: str,
        pricing_urls: List[str],
        yaml_alias_map: Dict[str, str],
    ) -> List[Any]:
        lowered = (question or "").lower().strip()
        if not lowered:
            return []

        try:
            classified = await self._classify_required_actions(
                question=question,
                pricing_urls=pricing_urls,
                yaml_alias_map=yaml_alias_map,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("harvey.agent.required_actions.classifier_failed", error=str(exc))
            classified = None

        if classified is not None:
            return classified

        logger.info("harvey.agent.required_actions.fallback", question=question)
        return self._collect_inferred_actions(lowered)

    def _build_plan_request_messages(
        self,
        *,
        plan_prompt: str,
        question: str,
        pricing_urls: List[str],
        yaml_alias_map: Dict[str, str],
        spec_excerpt: Optional[str],
        required_actions: List[Any],
    ) -> List[str]:
        messages: List[str] = [plan_prompt, PLAN_RESPONSE_FORMAT_INSTRUCTIONS]
        messages.append(f"Question: {question}")
        if pricing_urls:
            messages.append("Pricing URLs detected/provided (use as-is when planning):")
            for index, url in enumerate(pricing_urls, start=1):
                messages.append(f"{index}. {url}")
        else:
            messages.append("Pricing URLs detected/provided: None")

        if yaml_alias_map:
            messages.append("Uploaded Pricing2Yaml aliases (use the alias when referencing uploads):")
            for alias, content in yaml_alias_map.items():
                snippet = content[:500]
                messages.append(f"{alias}: {snippet}")
        else:
            messages.append("Uploaded Pricing2Yaml aliases: None")

        if required_actions:
            messages.append(
                "Required actions (include each exactly once in plan.actions in this order):"
            )
            messages.append(json.dumps(required_actions, ensure_ascii=False))
            requirement_notes = self._explain_required_actions(
                self._normalize_requirements(required_actions)
            )
            if requirement_notes:
                messages.append("Rationale for required actions:")
                messages.append(requirement_notes)

        if spec_excerpt:
            messages.append("Pricing2Yaml specification:")
            messages.append(spec_excerpt)

        return messages

    async def _classify_required_actions(
        self,
        *,
        question: str,
        pricing_urls: List[str],
        yaml_alias_map: Dict[str, str],
    ) -> Optional[List[Any]]:
        messages: List[str] = [DEFAULT_REQUIRED_ACTION_PROMPT]
        messages.append(f"Question: {question}")
        if pricing_urls:
            messages.append("Pricing URLs detected/provided:")
            messages.append(", ".join(pricing_urls))
        else:
            messages.append("Pricing URLs detected/provided: None")

        if yaml_alias_map:
            messages.append("Uploaded Pricing2Yaml aliases:")
            messages.append(", ".join(yaml_alias_map.keys()))
        else:
            messages.append("Uploaded Pricing2Yaml aliases: None")

        try:
            text = await asyncio.to_thread(
                self._llm.make_full_request,
                "\n".join(messages),
                json_output=True,
            )
        except ValueError as exc:
            logger.warning(
                "harvey.agent.required_actions.invalid_json",
                question=question,
                error=str(exc),
            )
            return None

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.warning(
                "harvey.agent.required_actions.parse_error",
                question=question,
                error=str(exc),
            )
            return None

        if isinstance(parsed, list):
            candidate = parsed
        elif isinstance(parsed, dict):
            candidate = parsed.get("required_actions") or parsed.get("actions")
        else:
            logger.warning(
                "harvey.agent.required_actions.unexpected_payload",
                question=question,
                payload_type=type(parsed).__name__,
            )
            return None

        if candidate is None:
            return []
        if not isinstance(candidate, list):
            logger.warning(
                "harvey.agent.required_actions.not_list",
                question=question,
                payload_type=type(candidate).__name__,
            )
            return None

        return candidate

    def _actions_satisfy_requirements(
        self, plan_actions: Any, required_actions: List[Any]
    ) -> bool:
        if not required_actions:
            return True
        normalized_plan = self._normalize_actions(plan_actions)
        normalized_requirements = self._normalize_requirements(required_actions)
        if not normalized_requirements:
            return True

        required_index = 0
        for action in normalized_plan:
            required_action = normalized_requirements[required_index]
            if action.name != required_action.name:
                continue
            if required_action.name == "optimal" and required_action.objective:
                candidate_objective = action.objective or "minimize"
                if candidate_objective != required_action.objective:
                    continue
            required_index += 1
            if required_index == len(normalized_requirements):
                return True

        return False

    def _normalize_requirements(self, requirements: List[Any]) -> List[PlannedAction]:
        normalized: List[PlannedAction] = []
        for entry in requirements:
            planned = self._parse_action_entry(entry, silent=True)
            if planned:
                normalized.append(planned)
        return normalized

    def _describe_required_action_mismatch(
        self, plan_actions: Any, required_actions: List[Any]
    ) -> str:
        normalized_plan = self._normalize_actions(plan_actions)
        normalized_requirements = self._normalize_requirements(required_actions)
        if not normalized_requirements:
            return "Plan.actions satisfied requirements."

        expected = [self._format_action_descriptor(action) for action in normalized_requirements]
        actual = [self._format_action_descriptor(action) for action in normalized_plan]
        if not normalized_plan:
            return "Plan.actions was empty but required steps were expected: " + ", ".join(expected)

        return (
            "Plan.actions must include the required sequence "
            + ", ".join(expected)
            + " (in order). Actual sequence: "
            + ", ".join(actual)
        )

    def _format_action_descriptor(self, action: PlannedAction) -> str:
        if action.name == "optimal":
            objective = action.objective or "minimize"
            return f"optimal({objective})"
        return action.name

    def _explain_required_actions(self, requirements: List[PlannedAction]) -> str:
        if not requirements:
            return ""

        notes: List[str] = []
        for action in requirements:
            if action.name == "subscriptions":
                notes.append(
                    "- subscriptions: needed to compute configuration-space cardinality requested by the user."
                )
            elif action.name == "ipricing":
                notes.append(
                    "- ipricing: user requested the Pricing2Yaml document, so fetch the canonical YAML via A-MINT."
                )
            elif action.name == "optimal":
                objective = action.objective or "minimize"
                if objective == "maximize":
                    notes.append(
                        "- optimal (maximize): user asked for the most expensive option, so run the optimizer with objective=maximize."
                    )
                else:
                    notes.append(
                        "- optimal (minimize): user asked for the best or cheapest option, so run the optimizer with the minimizing objective."
                    )
            elif action.name == "summary":
                notes.append(
                    "- summary: user requested a high-level narrative without additional computations."
                )

        return "\n".join(notes)

    async def _generate_answer(
        self, question: str, plan: Dict[str, Any], payload: Dict[str, Any]
    ) -> str:
        answer_prompt = self._get_answer_prompt()
        messages = [answer_prompt]
        messages.append(f"Question: {question}")
        messages.append(f"Plan: {json.dumps(plan, ensure_ascii=False)}")
        payload_summary = self._summarize_tool_payload(payload)
        if payload_summary:
            messages.append(
                f"Tool payload summary: {json.dumps(payload_summary, ensure_ascii=False)}"
            )

        payload_chunks = self._serialise_payload_chunks(payload)
        total_chunks = len(payload_chunks)
        for index, chunk in enumerate(payload_chunks, start=1):
            messages.append(f"Tool payload chunk {index}/{total_chunks}:")
            messages.append(chunk)
        if self._should_include_spec(question, plan):
            spec_excerpt = await self._get_spec_excerpt()
            if spec_excerpt:
                messages.append("Pricing2Yaml specification:")
                messages.append(spec_excerpt)

        response = await asyncio.to_thread(
            self._llm.make_full_request,
            "\n".join(messages),
            json_output=False,
        )
        return response or "No answer could be generated."

    def _parse_plan_text(
        self,
        *,
        text: str,
        question: str,
        pricing_urls: List[str],
        yaml_alias_map: Dict[str, str],
        allow_fallback: bool = True,
    ) -> Dict[str, Any]:
        cleaned = text.strip()
        if not cleaned:
            logger.error("harvey.agent.plan_empty", question=question)
            raise ValueError(
                "H.A.R.V.E.Y. returned an empty planning response. Please retry your question."
            )

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        extracted = self._extract_first_json_block(cleaned)
        if extracted is not None:
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                logger.warning(
                    "harvey.agent.plan_partial_json_failed",
                    question=question,
                    fragment=extracted[:500],
                )

        if allow_fallback:
            inferred = self._derive_plan_from_text(
                cleaned,
                question,
                pricing_urls,
                yaml_alias_map,
            )
            if inferred is not None:
                logger.info(
                    "harvey.agent.plan_inferred", question=question, plan=inferred
                )
                return inferred

        logger.error("harvey.agent.plan_unparsed", question=question, raw=cleaned[:1000])
        raise ValueError("Failed to interpret H.A.R.V.E.Y.'s plan. Please rephrase your request.")

    def _derive_plan_from_text(
        self,
        text: str,
        question: Optional[str],
        pricing_urls: List[str],
        yaml_alias_map: Dict[str, str],
    ) -> Optional[Dict[str, Any]]:
        contexts: List[str] = []
        contexts.extend(pricing_urls)
        contexts.extend(yaml_alias_map.keys())
        if not contexts:
            return None

        combined = f"{(question or '').lower()}\n{text.lower()}"
        actions = self._collect_inferred_actions(combined)
        if not actions:
            return None

        default_reference: Optional[str] = None
        if len(contexts) == 1:
            default_reference = contexts[0]

        return {
            "actions": actions,
            "pricing_url": default_reference,
            "requires_uploaded_yaml": False,
            "intent_summary": self._build_intent_summary(question),
            "objective": "minimize",
            "solver": "minizinc",
            "filters": None,
            "refresh": bool(yaml_alias_map),
            "use_pricing2yaml_spec": False,
        }

    def _collect_inferred_actions(self, combined: str) -> List[Any]:
        actions: List[Any] = []

        def contains_any(keywords: List[str]) -> bool:
            return any(keyword in combined for keyword in keywords)

        if contains_any(["summary", "summarise", "summarize", "synopsis", "overview"]):
            actions.append("summary")

        if contains_any(
            [
                "ipricing",
                "i-pricing",
                "pricing yaml",
                "pricing2yaml",
                "pricing 2 yaml",
                "yaml file",
                "download yaml",
                "export yaml",
                "raw yaml",
                "yaml output",
            ]
        ):
            actions.append("ipricing")

        if contains_any(
            [
                "subscriptions(",
                "subscriptions tool",
                "call the subscriptions",
                "number of different subscription",
                "number of different subscriptions",
                "number of subscriptions",
                "how many subscriptions",
                "how many subscription",
                "subscription count",
                "count of subscriptions",
                "total subscriptions",
                "total number of subscription",
                "enumerate the subscription",
                "number of plans",
                "how many plans",
                "plan count",
                "configuration count",
            ]
        ):
            actions.append("subscriptions")

        if contains_any(
            [
                "best subscription",
                "best plan",
                "best option",
                "cheapest",
                "cheapest plan",
                "least expensive",
                "optimal",
                "minimize",
                "minimise",
                "optimal(",
                "lowest cost",
                "lowest price",
                "minimum price",
                "most affordable",
                "best value",
            ]
        ):
            actions.append({"name": "optimal", "objective": "minimize"})

        if contains_any(
            [
                "most expensive",
                "most expensive plan",
                "priciest",
                "highest priced",
                "highest cost",
                "maximize",
                "maximise",
                "maximize objective",
                "maximum price",
                "premium plan",
            ]
        ):
            actions.append({"name": "optimal", "objective": "maximize"})

        deduped: List[Any] = []
        seen: Set[str] = set()
        for action in actions:
            key = json.dumps(action, sort_keys=True) if isinstance(action, dict) else str(action)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(action)

        return deduped

    def _build_intent_summary(self, question: Optional[str]) -> str:
        if not question:
            return "Plan inferred from non-JSON planning response."
        shortened = question if len(question) <= 160 else f"{question[:157]}..."
        return f"Plan inferred for question: {shortened}"

    def _serialise_payload_chunks(self, payload: Dict[str, Any], chunk_size: int = 4000) -> List[str]:
        if not payload:
            return ["{}"]
        payload_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if len(payload_text) <= chunk_size:
            return [payload_text]
        return [payload_text[i : i + chunk_size] for i in range(0, len(payload_text), chunk_size)]

    def _summarize_tool_payload(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not payload:
            return None

        summary: Dict[str, Any] = {}
        cardinalities = self._collect_field_values(payload, "cardinality")
        last_cardinality = self._select_last_int(cardinalities)
        if last_cardinality is not None:
            summary["cardinality"] = last_cardinality

        pricing_yaml_values = [
            value for value in self._collect_field_values(payload, "pricing_yaml") if isinstance(value, str)
        ]
        if pricing_yaml_values:
            summary["pricingYamlLength"] = len(pricing_yaml_values[-1])

        subscriptions = self._extract_subscriptions_list(payload)
        if subscriptions is not None:
            summary["subscriptionCount"] = len(subscriptions)
            missing_cost_plans = [
                entry.get("subscription", {}).get("plan")
                for entry in subscriptions
                if not self._is_numeric_cost(entry.get("cost"))
            ]
            if missing_cost_plans:
                summary["nonNumericCostPlans"] = [plan for plan in missing_cost_plans if plan]

        optimal_entry = self._extract_optimal_entry(payload)
        if optimal_entry:
            summary["bestPlan"] = optimal_entry

        return summary or None

    def _collect_field_values(self, node: Any, key: str) -> List[Any]:
        collected: List[Any] = []

        def visit(current: Any) -> None:
            if isinstance(current, dict):
                if key in current:
                    collected.append(current[key])
                for value in current.values():
                    visit(value)
            elif isinstance(current, list):
                for item in current:
                    visit(item)

        visit(node)
        return collected

    def _select_last_int(self, values: List[Any]) -> Optional[int]:
        for value in reversed(values):
            if isinstance(value, int):
                return value
            if isinstance(value, str):
                try:
                    return int(value)
                except ValueError:
                    continue
        return None

    def _extract_subscriptions_list(self, payload: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        for value in self._collect_field_values(payload, "subscriptions"):
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return None

    def _extract_optimal_entry(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for value in reversed(self._collect_field_values(payload, "optimal")):
            if isinstance(value, dict):
                subscription = value.get("subscription")
                plan = None
                add_ons: Optional[List[str]] = None
                if isinstance(subscription, dict):
                    plan = subscription.get("plan")
                    add_ons_value = subscription.get("addOns")
                    if isinstance(add_ons_value, list):
                        add_ons = [str(item) for item in add_ons_value]
                return {
                    "plan": plan,
                    "cost": value.get("cost"),
                    "addOns": add_ons,
                }
        return None

    def _is_numeric_cost(self, cost: Any) -> bool:
        if cost is None:
            return False
        if isinstance(cost, (int, float)):
            return True
        if isinstance(cost, str):
            stripped = cost.replace("€", "").replace("$", "").replace(",", "").strip()
            try:
                float(stripped)
            except ValueError:
                return False
            return True
        return False

    def _validate_yaml_requirement(self, plan: Dict[str, Any], yaml_contents: List[str]) -> None:
        if plan.get("requires_uploaded_yaml") and not yaml_contents:
            raise ValueError(
                "H.A.R.V.E.Y. needs a Pricing2Yaml file to proceed. Please upload one and retry."
            )

    def _normalize_actions(self, raw_actions: Any) -> List[PlannedAction]:
        normalized: List[PlannedAction] = []
        if raw_actions in (None, []):
            return normalized
        if not isinstance(raw_actions, list):
            logger.warning("harvey.agent.invalid_actions", requested=raw_actions)
            return normalized

        for entry in raw_actions:
            planned_action = self._parse_action_entry(entry)
            if planned_action:
                normalized.append(planned_action)

        return normalized

    def _parse_action_entry(self, entry: Any, *, silent: bool = False) -> Optional[PlannedAction]:
        def warn(event: str, **kwargs: Any) -> None:
            if not silent:
                logger.warning(event, **kwargs)

        if isinstance(entry, str):
            if entry in ALLOWED_ACTIONS:
                return PlannedAction(name=entry)
            warn("harvey.agent.unsupported_action", requested=entry)
            return None

        if not isinstance(entry, dict):
            warn("harvey.agent.unrecognized_action_entry", entry=entry)
            return None

        name = entry.get("name")
        if not isinstance(name, str) or name not in ALLOWED_ACTIONS:
            warn("harvey.agent.invalid_action_object", requested=entry)
            return None

        objective = entry.get("objective")
        if objective not in (None, "minimize", "maximize"):
            warn("harvey.agent.invalid_objective", action=name, objective=objective)
            objective = None

        pricing_url = entry.get("pricing_url") or entry.get("url")
        if pricing_url is not None and not isinstance(pricing_url, str):
            warn("harvey.agent.invalid_pricing_url", action=name, pricing_url=pricing_url)
            pricing_url = None

        return PlannedAction(name=name, objective=objective, pricing_url=pricing_url)

    def _extract_filters(self, raw_filters: Any) -> Optional[Dict[str, Any]]:
        if raw_filters is None or raw_filters == {}:
            return None
        if isinstance(raw_filters, dict):
            return raw_filters
        logger.warning("harvey.agent.invalid_filters", provided=raw_filters)
        return None

    def _resolve_default_reference(
        self,
        *,
        plan_reference: Any,
        plan_references: Any,
        available_urls: List[str],
        yaml_aliases: List[str],
    ) -> Optional[str]:
        references: List[str] = []

        def _append(value: Any) -> None:
            if isinstance(value, str) and value.strip():
                references.append(value.strip())
            elif isinstance(value, list):
                for item in value:
                    _append(item)

        _append(plan_reference)
        _append(plan_references)

        for reference in references:
            return reference

        total_contexts = len(available_urls) + len(yaml_aliases)
        if total_contexts == 1:
            if available_urls:
                return available_urls[0]
            return yaml_aliases[0]
        return None

    async def _execute_actions(
        self,
        *,
        actions: List[PlannedAction],
        default_reference: Optional[str],
        available_urls: List[str],
        refresh: bool,
        solver: str,
        filters: Optional[Dict[str, Any]],
        objective: str,
        yaml_alias_map: Dict[str, str],
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        if not actions:
            return [], None

        self._ensure_pricing_context(
            actions,
            default_reference=default_reference,
            available_urls=available_urls,
            yaml_alias_map=yaml_alias_map,
        )

        results: List[Dict[str, Any]] = []
        transformed_urls: Set[str] = set()
        last_payload: Optional[Dict[str, Any]] = None
        refresh_requested = bool(refresh)

        for index, action in enumerate(actions):
            action_url, effective_refresh, action_yaml, context_reference = self._prepare_action_inputs(
                action=action,
                default_reference=default_reference,
                available_urls=available_urls,
                yaml_alias_map=yaml_alias_map,
                refresh_requested=refresh_requested,
                transformed_urls=transformed_urls,
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
            if context_reference:
                step_record["pricingContext"] = context_reference
            results.append(step_record)
            last_payload = payload

        return results, last_payload

    def _ensure_pricing_context(
        self,
        actions: List[PlannedAction],
        default_reference: Optional[str],
        available_urls: List[str],
        yaml_alias_map: Dict[str, str],
    ) -> None:
        total_contexts = len(available_urls) + len(yaml_alias_map)
        required_actions = {"subscriptions", "optimal", "summary", "ipricing"}
        for action in actions:
            reference = action.pricing_url or default_reference
            if reference and not self._is_known_reference(reference, available_urls, yaml_alias_map):
                raise ValueError(
                    f"Unknown pricing context '{reference}'. Use one of: {available_urls + list(yaml_alias_map.keys())}."
                )

            if action.name in required_actions:
                self._assert_context_available(
                    reference,
                    total_contexts,
                )

    def _prepare_action_inputs(
        self,
        *,
        action: PlannedAction,
        default_reference: Optional[str],
        available_urls: List[str],
        yaml_alias_map: Dict[str, str],
        refresh_requested: bool,
        transformed_urls: Set[str],
    ) -> Tuple[Optional[str], bool, Optional[str], Optional[str]]:
        reference = self._determine_reference(
            action,
            default_reference,
            available_urls,
            yaml_alias_map,
        )
        action_url: Optional[str] = None
        action_yaml: Optional[str] = None

        if reference:
            if reference in yaml_alias_map:
                action_yaml = yaml_alias_map[reference]
            else:
                action_url = reference

        effective_refresh = False
        if refresh_requested and action_url:
            effective_refresh = action_url not in transformed_urls

        return action_url, effective_refresh, action_yaml, reference

    def _determine_reference(
        self,
        action: PlannedAction,
        default_reference: Optional[str],
        available_urls: List[str],
        yaml_alias_map: Dict[str, str],
    ) -> Optional[str]:
        reference = action.pricing_url or default_reference
        if reference:
            return reference

        total_contexts = len(available_urls) + len(yaml_alias_map)
        if total_contexts == 0:
            return None
        if total_contexts == 1:
            if available_urls:
                return available_urls[0]
            return next(iter(yaml_alias_map))

        raise ValueError(
            "Multiple pricing contexts detected. Each action must specify pricing_url to choose which pricing to analyse."
        )

    def _assert_context_available(
        self,
        reference: Optional[str],
        total_contexts: int,
    ) -> None:
        if total_contexts == 0:
            raise ValueError(
                "Provide at least one pricing URL or Pricing2Yaml upload before calling tooling."
            )
        if reference is None and total_contexts > 1:
            raise ValueError(
                "Multiple pricing contexts detected. Set pricing_url on each action to choose the correct pricing source."
            )

    def _is_known_reference(
        self,
        reference: str,
        available_urls: List[str],
        yaml_alias_map: Dict[str, str],
    ) -> bool:
        return (
            reference in yaml_alias_map
            or reference in available_urls
            or self._looks_like_url(reference)
        )

    def _looks_like_url(self, value: str) -> bool:
        return bool(URL_PATTERN.match(value))

    def _deduplicate(self, values: List[str]) -> List[str]:
        seen: Set[str] = set()
        result: List[str] = []
        for value in values:
            if not value or value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result

    def _extract_urls_from_question(self, question: str) -> List[str]:
        if not question:
            return []
        matches = URL_PATTERN.findall(question)
        return self._deduplicate(matches)

    def _build_yaml_alias_map(self, yaml_contents: List[str]) -> Dict[str, str]:
        alias_map: "OrderedDict[str, str]" = OrderedDict()
        # Avoid duplicating a single upload with two aliases. If only one pricing
        # is provided, expose a single canonical alias: "uploaded://pricing".
        # For multiple uploads, keep numbered aliases to disambiguate.
        if len(yaml_contents) == 1:
            if yaml_contents[0]:
                alias_map["uploaded://pricing"] = yaml_contents[0]
        else:
            for index, content in enumerate(yaml_contents):
                if not content:
                    continue
                alias = f"uploaded://pricing/{index + 1}"
                alias_map[alias] = content
        return dict(alias_map)

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
        if action.name == "ipricing":
            return await self._workflow.run_ipricing(
                url=url,
                yaml_content=yaml_content,
                refresh=refresh,
            )
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

    def _get_planning_prompt(self) -> str:
        if self._planning_prompt is None:
            self._planning_prompt = DEFAULT_PLAN_PROMPT
        return self._planning_prompt

    def _get_answer_prompt(self) -> str:
        if self._answer_prompt is None:
            self._answer_prompt = DEFAULT_ANSWER_PROMPT
        return self._answer_prompt

    @staticmethod
    def _extract_first_json_block(text: str) -> Optional[str]:
        decoder = json.JSONDecoder()
        for index, char in enumerate(text):
            if char not in "{[":
                continue
            try:
                _, offset = decoder.raw_decode(text[index:])
            except json.JSONDecodeError:
                continue
            end = index + offset
            return text[index:end]
        return None

    async def _get_spec_excerpt(self) -> str:
        if self._spec_excerpt is None:
            text: Optional[str] = None
            try:
                text = await self._workflow.read_resource_text(SPEC_RESOURCE_ID)
            except MCPClientError as exc:
                logger.warning("harvey.agent.spec_resource_fallback", error=str(exc))
            if not text:
                logger.warning("harvey.agent.spec_resource_empty")
            self._spec_excerpt = text
        if not self._spec_excerpt:
            raise ValueError(
                "Pricing2Yaml specification is unavailable. Ensure resource://pricing/specification is "
                "exposed or the local specification file is present."
            )
        return self._spec_excerpt

    def _should_include_spec(self, question: str, plan: Optional[Dict[str, Any]] = None) -> bool:
        if plan and plan.get("use_pricing2yaml_spec"):
            return True
        lowered = question.lower()
        keywords = ["pricing2yaml", "pricing 2 yaml", "yaml spec", "schema", "syntax", "ipricing"]
        return any(keyword in lowered for keyword in keywords)

