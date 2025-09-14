# core/orchestrator_agent.py
from typing import Dict, Any, List
from core.action_schema import _classify_intent
from core.requirement_mapping import requirement_mapping
from io_library.output import _generate_validation_agent_feedback
from logging_config import get_agent_logger
from validators.accessibility_agent import playwright_execution_agent
from validators.branding_ux_validation_agent import enrich_with_branding_ux  # can be a no-op in your repo

logger = get_agent_logger("ORCHESTRATOR")

def _build_default_scenarios(requirements: Dict[str, Any], website: str) -> List[Dict[str, Any]]:
    scenarios: List[Dict[str, Any]] = []
    comps = (requirements or {}).get("components", []) or []
    if comps:
        for i, comp in enumerate(comps, 1):
            scenarios.append({
                "scenario_id": f"comp_{i}",
                "description": f"Open {website} and capture state for component: {comp}",
                "component": comp,
            })
    else:
        scenarios.append({
            "scenario_id": "baseline_homepage",
            "description": f"Open {website} homepage and capture screenshot"
        })
    return scenarios

async def orchestrator_run(state: Dict[str, Any]) -> Dict[str, Any]:
    bug_description = (state.get("bug_description") or state.get("input") or "").strip()
    website = (state.get("website") or "").strip()

    logger.info(f"🧭 Classifying intent for: '{bug_description[:100]}...'")
    intent = _classify_intent(bug_description)
    logger.info(f"🧭 Intent → {intent}")

    # 1) Requirements extraction (kept for component awareness)
    try:
        req_out = requirement_mapping({"input": bug_description or state.get("input", ""), "website": website})
        requirements = req_out.get("requirements", {}) if isinstance(req_out, dict) else {}
    except Exception as e:
        logger.error(f"ReqX extraction error: {e}")
        requirements = {}

    # 2) Scenarios
    scenarios = _build_default_scenarios(requirements, website)

    # 🔎 Auto-insert tablist-children roles check WITHOUT requiring the word "group"
    desc = (bug_description or "").lower()
    if "tablist" in desc and ("child" in desc or "children" in desc or "role" in desc or "search" in desc):
        scenarios.insert(0, {
            "scenario_id": "a11y_tablist_children_roles_check_1",
            "kind": "a11y_tablist_children_group_check",  # routes to concrete executor in accessibility_agent
            "description": "Verify the tablist below Search exposes appropriate roles on its direct children"
        })

    # 3) Branding/UX enrichment (optional)
    enriched_scenarios = scenarios
    branding_ux_notes: List[str] = []
    if intent in ("ux", "branding"):
        logger.info("🎨 Routing through Branding/UX enrichment")
        try:
            enriched = enrich_with_branding_ux(requirements=requirements, scenarios=scenarios, website=website)
            enriched_scenarios = enriched.get("enriched_scenarios", scenarios)
            branding_ux_notes = enriched.get("notes", [])
        except Exception as e:
            logger.error(f"Branding/UX enrichment error: {e}")
    else:
        logger.info("♿ Accessibility intent → skipping Branding/UX enrichment")

    # 4) Execute with Playwright
    exec_state = dict(state)
    exec_state["website"] = website
    exec_state["enriched_scenarios"] = enriched_scenarios

    logger.info("➡️ Calling accessibility_agent.playwright_execution_agent with %d scenarios", len(enriched_scenarios))
    try:
        exec_out = await playwright_execution_agent(exec_state)
    except Exception as e:
        logger.error(f"Execution error: {e}")
        exec_out = {"execution_results": []}

    execution_results: List[Dict[str, Any]] = exec_out.get("execution_results", []) or []

    return _generate_validation_agent_feedback(website, bug_description, intent, requirements, enriched_scenarios, branding_ux_notes, execution_results)

