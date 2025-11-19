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
    OpenAIClientConfig,
    OpenAIClient,
)

logger = get_logger(__name__)
ALLOWED_ACTIONS = {"optimal", "subscriptions", "summary", "iPricing", "validate"}
SPEC_RESOURCE_ID = "resource://pricing/specification"
PLAN_REQUEST_MAX_ATTEMPTS = 3
URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+")

PLAN_RESPONSE_FORMAT_INSTRUCTIONS = """Respond with a single JSON object that matches this schema (JSON order is flexible):
{
    "actions": [...],
    "requires_uploaded_yaml": boolean,
    "use_pricing2yaml_spec": boolean
}
Action entries:
- A string ("summary", "iPricing", "validate") OR
- An object with at least {"name": "subscriptions"|"optimal"|"summary"|"iPricing"|"validate"} and optional keys:
    • "objective": "minimize"|"maximize" (only for optimal)
    • "pricing_url": string (required per action when multiple pricing contexts exist)
    • "filters": FilterCriteria (only include when the specific action needs filtering)
    • "solver": "minizinc"|"choco" (when the specific action needs to pick a solver)
FilterCriteria shape (when used inside an action object):
{
  "minPrice"?: number,
  "maxPrice"?: number,
  "features"?: string[],
  "usageLimits"?: Array<Record<string, number>>
}
Rules:
- Produce valid JSON with double quotes only. Do not wrap the response in Markdown fences or natural language.
- Include "validate" when the user asks to check, test, or confirm a pricing YAML/configuration.
- Only set requires_uploaded_yaml when a user-supplied Pricing2Yaml is mandatory to proceed.
- Set use_pricing2yaml_spec to true whenever the user asks about schema, syntax, or validation details so the agent consults the specification excerpt.
- Put filters inside the specific action(s) that require them (e.g. subscriptions, optimal). Do NOT emit a top-level filters field.
- Price filters: numeric only (no symbols), base currency of the YAML. minPrice = lower bound, maxPrice = upper bound.
- features: exact feature.name values from the YAML (case-sensitive). Include only features that must be present.
- usageLimits: array of single-key objects where key = usageLimit.name and value = minimum threshold (boolean limits use 1).
- No other filter keys are allowed (only minPrice, maxPrice, features, usageLimits).
- If feature / usageLimit names can't be grounded yet (YAML not fetched), include an initial "iPricing" action first; subsequent actions may then include grounded filters.
- Use "minizinc" as the default solver unless the user explicitly asks for "choco". Specify the solver inside each action that needs it.
- When multiple pricing URLs or uploaded YAML aliases are available, set pricing_url per action.
- Leave actions empty only when the answer is directly inferable without tool calls.
Example response:
{"actions":["subscriptions",{"name":"optimal","objective":"minimize","solver":"minizinc","pricing_url":"uploaded://pricing","filters":{"features":["SSO"],"minPrice":10}}],"requires_uploaded_yaml":false,"use_pricing2yaml_spec":false}
"""

DEFAULT_REQUIRED_ACTION_PROMPT = """You decide whether tool calls are required to answer a user's pricing question accurately.

Available tools:
- "summary": accepts a pricing URL or uploaded YAML and returns a JSON payload with per-category counts (e.g. numberOfFeatures, numberOfIntegrationFeatures, numberOfSupportFeatures), plan-level metadata (storage limits, API quotas, seat ranges), and contextual flags describing billing or provisioning notes. The response does not list individual subscriptions, but it gives authoritative counts straight from the Pricing2Yaml model.
- "iPricing": returns the canonical Pricing2Yaml (iPricing) document. It uses the A-MINT pipeline when a pricing URL is supplied and simply returns uploaded YAML when present. Use it whenever the user requests the YAML source, wants to download/export the pricing, or needs to inspect the raw configuration.
- "subscriptions": accepts a pricing URL/YAML and optional filters; include a per-action "solver" if you need a solver-specific enumeration. It enumerates every subscription configuration that matches the filters and returns an array of entries with `subscription` details (plan name, included features/add-ons) plus pricing fields. The payload always includes a top-level `cardinality` showing how many configurations were found.
- "optimal": accepts the same inputs as `subscriptions` plus an `objective` (minimize or maximize). It runs the optimiser over the configuration space and returns the best matching configuration, including its computed `cost`, `currency`, the chosen `subscription` structure, any selected add-ons, and the analysed `cardinality` for traceability. Specify the per-action "solver" if needed.
- "validate": accepts a pricing URL or uploaded YAML plus an optional per-action solver. It checks the Pricing2Yaml configuration against the requested engine (MiniZinc or Choco) and returns whether it is valid along with any reported errors.

Instructions:
- Analyse the question and determine the minimal set of tool invocations needed for a correct, data-backed answer.
- Use "iPricing" whenever the user needs the Pricing2Yaml document itself (e.g. requests the YAML, asks for an iPricing file, or wants to export/download the configuration). Do not rely on textual summaries when the raw document is requested.
- Use "summary" for requests about feature counts, integration availability, plan metadata, or any aggregated statistics that come from the pricing YAML.
- Use "validate" whenever the user asks to confirm that a pricing YAML or configuration is valid, compliant, or free of modelling errors for a given solver.
- When a question references the number or count of features, integrations, limits, add-ons, or any other catalogue items, always include the "summary" tool—even if a YAML snippet is provided. Do not attempt to count items manually from truncated content.
- Use "subscriptions" when the user asks for the number of subscriptions, configurations, or plan variants.
- Include an optimal step with objective="minimize" when the user requests the best, cheapest, lowest-cost, or most advantageous option.
- Include an optimal step with objective="maximize" when the user asks for the most expensive or highest-priced option.
- When the user specifies constraints that imply filtering (required features, price bounds, specific usage limits like seats/storage/API quotas), ensure the plan includes a "filters" object in the FilterCriteria shape. Only these keys are allowed: minPrice, maxPrice, features (string[]), usageLimits (Array<Record<string, number>>). If the YAML content is not available to ground feature/limit names, include an initial "iPricing" step to fetch the canonical YAML and then align the filter keys to the exact names.
- Return an empty list only when the question can be answered directly from persistent conversation context without additional tool calls.
- When multiple pricing URLs or uploaded YAML aliases exist, include a pricing_url field on each required action using the specific URL or alias (e.g. "uploaded://pricing/2") so later planning stays unambiguous.

Mandatory rules:
- If the question mentions "how many" or "number of" together with "feature", "integration", "limit", "addon", or similar catalogue terms, the response MUST include "summary" in required_actions.
- If the question explicitly asks to validate, verify, or check the correctness of a pricing YAML/configuration, the response MUST include "validate" in required_actions.

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
    filters: Optional[Dict[str, Any]] = None  # Action-scoped filters (subscriptions/optimal only)
    solver: Optional[str] = None  # Action-scoped solver (subscriptions/optimal/validate)

DEFAULT_PLAN_PROMPT = """You orchestrate pricing intelligence workflows on behalf of H.A.R.V.E.Y., the Holistic Analysis and Regulation Virtual Expert for You.

Available tools:
- "subscriptions": accepts a pricing URL or uploaded YAML plus optional filters. It enumerates every subscription configuration and returns an array of entries describing each `subscription` (plan code, add-ons, included features) along with pricing meta-data. The response always surfaces a top-level `cardinality` representing the configuration-space size after filters.
- "optimal": accepts the same inputs as `subscriptions` and an `objective` argument. It runs the optimiser to produce the cheapest (`objective="minimize"`) or most expensive (`objective="maximize"`) configuration, returning the winning `subscription`, its computed `cost`, currency, selected add-ons, and the evaluated `cardinality`.
- "summary": accepts a pricing URL or uploaded YAML and returns catalogue metrics such as numberOfFeatures, counts per feature category, seat/storage limits, API quotas, and other aggregated insights derived from the Pricing2Yaml document. Use it whenever you need counts or descriptive metadata rather than full optimisation output.
- "iPricing": accepts a pricing URL or uploaded YAML and returns the canonical Pricing2Yaml document, invoking the A-MINT pipeline when a URL is supplied. Use it whenever the user needs to download, inspect, or export the raw YAML configuration.
- "validate": accepts a pricing URL or uploaded YAML and an optional solver argument. It verifies the Pricing2Yaml input against the solver to surface validation success or detailed errors.

Planning guidance:
- Think through the user's intent before emitting actions. Use the workflow tools whenever data, optimisation, or configuration counts are required. Only leave actions empty when the answer is already implicit in the conversation or specification excerpt.
- When the user asks for the YAML/iPricing document or needs the raw configuration file, include the "iPricing" tool before providing the answer so the YAML can be offered or referenced directly.
- When the user asks for the number of subscriptions, configurations, or plan variants, include the "subscriptions" tool before any optimisation so you obtain the correct cardinality.
- When the user asks for the number or count of features, integrations, limits, add-ons, or other catalogue elements, include the "summary" tool rather than counting manually—even if a YAML snippet is provided.
- When the user needs to confirm that a pricing model is valid, runs without solver errors, or complies with the specification, include the "validate" tool.
- When the user asks for the cheapest or "best" option (unless they explicitly state otherwise), include an optimal step that minimizes cost ({"name": "optimal", "objective": "minimize"}).
- When the user asks for the most expensive option, include an optimal step that maximizes cost ({"name": "optimal", "objective": "maximize"}).
- Set use_pricing2yaml_spec to true when the question involves schema, syntax, or validation details so that the agent consults the Pricing2Yaml reference.
- Prefer "minizinc" as the default solver unless the user explicitly selects an alternative or the invoked tool is "validate" where "choco" is preferred, and specify it inside each action when needed.

 Filter inference policy:
 - Translate the user's natural-language constraints into a concrete FilterCriteria object when using "subscriptions" (with filters) or "optimal".
     FilterCriteria schema and semantics:
     {
         "minPrice"?: number,       // lower bound in YAML's base currency (no symbols)
         "maxPrice"?: number,       // upper bound in YAML's base currency (no symbols)
         "features"?: string[],     // exact feature names (= feature.name in YAML), case-sensitive
         "usageLimits"?: Array<Record<string, number>> // each object has a single key: the exact usageLimit.name, value is a minimum threshold; for boolean usage limits use 1 to require true
     }
 - Ground all filter keys and values in the iPricing YAML. If needed, add an initial "iPricing" step (using the provided URL or uploaded alias) to read feature.name and usageLimit.name and align filters accordingly.
 - Mapping guidance:
     • “with SSO” → features: ["SSO"] (match exactly the YAML feature name)
     • “at least 200 seats” → usageLimits: [{"Seats": 200}]
     • “under $100” → maxPrice: 100
     • “API requests ≥ 10k/day” → usageLimits: [{"API requests per day": 10000}] # match the unit to the YAML usageLimit.name.unit. You may need to make some assumptions or conversions here.
     • Boolean usage limits (e.g., “Audit logs enabled”) → usageLimits: [{"Audit logs": 1}]
     • If a requirement refers to an add-on, express it through the features/limits it brings (no direct add-on filter key exists).
 - Provide filters inside each action that requires them (subscriptions / optimal). Do not use a top-level filters field.
 - Do not invent new keys or structures in filters; only use the allowed schema.

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
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for natural language orchestration")
        client_config = OpenAIClientConfig(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )
        self._llm = OpenAIClient(client_config)
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
        objective = self._resolve_default_objective(plan)
        self._apply_legacy_fields(plan, actions)
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
            # filters now action-scoped; legacy top-level filters already distributed.
            objective=objective,
            yaml_alias_map=yaml_alias_map,
        )

        payload_for_answer, result_payload = self._compose_results_payload(actions, results, last_payload)
        answer = await self._generate_answer(question, plan, payload_for_answer)

        self._strip_deprecated_plan_fields(plan)
        return {"plan": plan, "result": result_payload, "answer": answer}

    def _resolve_default_objective(self, plan: Dict[str, Any]) -> str:
        legacy_objective = plan.get("objective")
        return legacy_objective if legacy_objective in ("minimize", "maximize") else "minimize"

    def _apply_legacy_fields(self, plan: Dict[str, Any], actions: List[PlannedAction]) -> None:
        """Distribute legacy top-level fields to per-action when needed (backward compatibility)."""
        # Legacy top-level filters
        legacy_filters = self._extract_filters(plan.get("filters"))
        if legacy_filters:
            for action in actions:
                if action.name in ("subscriptions", "optimal") and action.filters is None:
                    action.filters = legacy_filters

        # Legacy top-level solver
        legacy_solver = plan.get("solver")
        if legacy_solver in ("minizinc", "choco"):
            for action in actions:
                if action.name in ("subscriptions", "optimal", "validate") and action.solver is None:
                    action.solver = legacy_solver

    def _strip_deprecated_plan_fields(self, plan: Dict[str, Any]) -> None:
        for deprecated in ["intent_summary", "filters", "objective", "pricing_url", "solver", "refresh"]:
            plan.pop(deprecated, None)

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
        self._append_pricing_urls_message(messages, pricing_urls)
        self._append_yaml_alias_messages(messages, yaml_alias_map)
        self._append_required_actions_message(messages, required_actions)
        self._append_spec_excerpt_message(messages, spec_excerpt)
        return messages

    def _append_pricing_urls_message(self, messages: List[str], pricing_urls: List[str]) -> None:
        if pricing_urls:
            messages.append("Pricing URLs detected/provided (use as-is when planning):")
            for index, url in enumerate(pricing_urls, start=1):
                messages.append(f"{index}. {url}")
            return
        messages.append("Pricing URLs detected/provided: None")

    def _append_yaml_alias_messages(
        self,
        messages: List[str],
        yaml_alias_map: Dict[str, str],
        chunk_size: int = 4000,
    ) -> None:
        if not yaml_alias_map:
            messages.append("Uploaded Pricing2Yaml aliases: None")
            return

        messages.append(
            "Uploaded Pricing2Yaml content (full, chunked). Use exact feature.name and usageLimit.name from these documents when constructing filters:"
        )
        for alias, content in yaml_alias_map.items():
            total_len = len(content or "")
            if not content:
                messages.append(f"{alias}: <empty content>")
                continue
            chunks = [content[i : i + chunk_size] for i in range(0, total_len, chunk_size)]
            total_chunks = len(chunks)
            messages.append(f"{alias}: length={total_len} chars; chunks={total_chunks}")
            for idx, chunk in enumerate(chunks, start=1):
                messages.append(f"YAML[{alias}] chunk {idx}/{total_chunks}:")
                messages.append(chunk)

    def _append_required_actions_message(
        self,
        messages: List[str],
        required_actions: List[Any],
    ) -> None:
        if not required_actions:
            return

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

    def _append_spec_excerpt_message(
        self,
        messages: List[str],
        spec_excerpt: Optional[str],
    ) -> None:
        if not spec_excerpt:
            return
        messages.append("Pricing2Yaml specification:")
        messages.append(spec_excerpt)

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
            elif action.name == "iPricing":
                notes.append(
                    "- iPricing: user requested the Pricing2Yaml document, so fetch the canonical YAML via A-MINT."
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
            elif action.name == "validate":
                notes.append(
                    "- validate: user needs to confirm the Pricing2Yaml passes solver validation and to surface any modelling errors."
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
            "filters": None,
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
                "iPricing",
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
            actions.append("iPricing")

        if contains_any(
            [
                "validate",
                "validation",
                "is it valid",
                "check validity",
                "verify yaml",
                "lint yaml",
                "any errors",
                "error in pricing",
                "solver error",
            ]
        ):
            actions.append("validate")

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

        validation_states = self._collect_field_values(payload, "valid")
        last_validation = self._select_last_bool(validation_states)
        if last_validation is not None:
            summary["valid"] = last_validation

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

    def _select_last_bool(self, values: List[Any]) -> Optional[bool]:
        for value in reversed(values):
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"true", "false"}:
                    return lowered == "true"
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
        """Convert a raw action entry into a PlannedAction with minimal branching.
        Accepts either a string (action name) or an object containing name plus optional fields.
        Invalid inputs return None and optionally log a warning.
        """
        def warn(event: str, **kwargs: Any) -> None:
            if not silent:
                logger.warning(event, **kwargs)

        # Fast path: simple string action
        if isinstance(entry, str):
            return PlannedAction(name=entry) if entry in ALLOWED_ACTIONS else None

        # Must be a dict from here
        if not isinstance(entry, dict):
            warn("harvey.agent.unrecognized_action_entry", entry=entry)
            return None

        name = entry.get("name")
        if name not in ALLOWED_ACTIONS:
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

        raw_filters = entry.get("filters")
        action_filters = self._extract_filters(raw_filters) if raw_filters is not None else None
        if raw_filters is not None and action_filters is None:
            warn("harvey.agent.invalid_action_filters", action=name, filters=raw_filters)

        solver = entry.get("solver")
        if solver not in (None, "minizinc", "choco"):
            warn("harvey.agent.invalid_solver", action=name, solver=solver)
            solver = None

        return PlannedAction(
            name=name,
            objective=objective,
            pricing_url=pricing_url,
            filters=action_filters,
            solver=solver,
        )

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
        last_payload: Optional[Dict[str, Any]] = None

        for index, action in enumerate(actions):
            action_url, action_yaml, context_reference = self._prepare_action_inputs(
                action=action,
                default_reference=default_reference,
                available_urls=available_urls,
                yaml_alias_map=yaml_alias_map,
            )

            payload = await self._run_single_action(
                action=action,
                url=action_url,
                objective=objective,
                yaml_content=action_yaml,
            )

            step_record: Dict[str, Any] = {
                "index": index,
                "action": action.name,
                "payload": payload,
            }
            if action.name == "optimal":
                step_record["objective"] = action.objective or objective
            if action.filters is not None and action.name in ("subscriptions", "optimal"):
                step_record["filters"] = action.filters
            if action.solver:
                step_record["solver"] = action.solver
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
        required_actions = {"subscriptions", "optimal", "summary", "iPricing", "validate"}
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
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
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

        return action_url, action_yaml, reference

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
        objective: str,
        yaml_content: Optional[str],
    ) -> Dict[str, Any]:
        resolved_objective = action.objective or objective
        effective_solver = action.solver or "minizinc"
        if action.name == "summary":
            return await self._workflow.run_summary(url=url, yaml_content=yaml_content, refresh=False)
        if action.name == "iPricing":
            return await self._workflow.run_ipricing(
                url=url,
                yaml_content=yaml_content,
                refresh=False,
            )
        if action.name == "subscriptions":
            return await self._workflow.run_subscriptions(
                url=url or "",
                filters=action.filters,
                solver=effective_solver,
                refresh=False,
                yaml_content=yaml_content,
            )
        if action.name == "validate":
            return await self._workflow.run_validate(
                url=url,
                yaml_content=yaml_content,
                solver=effective_solver,
                refresh=False,
            )
        return await self._workflow.run_optimal(
            url=url or "",
            filters=action.filters,
            solver=effective_solver,
            objective=resolved_objective,
            refresh=False,
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
        keywords = [
            "pricing2yaml",
            "pricing 2 yaml",
            "yaml spec",
            "schema",
            "syntax",
            "ipricing",
            "validate",
            "validation",
            "valid",
            "invalid",
            "error",
        ]
        return any(keyword in lowered for keyword in keywords)

