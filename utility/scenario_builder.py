# utility/scenario_builder.py
from typing import Dict, Any, List


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
