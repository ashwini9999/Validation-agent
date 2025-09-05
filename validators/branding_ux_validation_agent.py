# agents/branding_ux_validation_agent.py
from typing import Dict, Any, List
from logging_config import get_agent_logger, log_agent_start, log_agent_thinking, log_agent_complete

logger = get_agent_logger("BUVA")  # Branding/UX Validation Agent

def _add_branding_ux_checks(scenarios: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Light enrichment: attach 'branding_checks' and 'ux_checks' arrays to each scenario.
    Your Playwright runner ignores them for now, but this is where you'd expand later.
    """
    enriched: List[Dict[str, Any]] = []
    for sc in scenarios:
        sc2 = dict(sc)
        sc2["branding_checks"] = [
            "Logo visible and not distorted",
            "Brand colors used correctly",
            "Typography matches brand guidelines"
        ]
        sc2["ux_checks"] = [
            "Interactive elements are keyboard accessible",
            "Visible focus states on all focusable controls",
            "Clear feedback on user actions (toasts/labels)"
        ]
        enriched.append(sc2)
    return enriched

def enrich_with_branding_ux(requirements: Dict[str, Any], scenarios: List[Dict[str, Any]], website: str) -> Dict[str, Any]:
    """
    Enrich scenarios with branding + UX validation checks.
    """
    log_agent_start("BUVA", {
        "website": website,
        "scenarios_in": len(scenarios),
        "has_requirements": bool(requirements),
    })
    log_agent_thinking("BUVA", "Adding branding and UX checks to scenarios")

    enriched = _add_branding_ux_checks(scenarios)
    notes = ["Branding/UX enrichment applied to scenarios."]

    log_agent_complete("BUVA", {
        "scenarios_out": len(enriched),
        "note": notes[0]
    })

    return {
        "enriched_scenarios": enriched,
        "notes": notes
    }
