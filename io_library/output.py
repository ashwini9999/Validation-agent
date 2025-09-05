# io_library/output.py
from typing import Dict, Any, List

def _compute_summary(execution_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(execution_results)
    failed = sum(1 for r in execution_results if (r or {}).get("result") == "Fail")
    passed = total - failed if total else 0
    overall = "Unknown"
    if total:
        overall = "Pass" if failed == 0 else "Fail"
    return {
        "total_scenarios": total,
        "passed": passed,
        "failed": failed,
        "overall_result": overall,
    }

def _generate_validation_agent_feedback(
    website: str,
    bug_description: str,
    intent: str,
    requirements: dict,
    enriched_scenarios: list,
    branding_ux_notes: list,
    execution_results: list
) -> dict:
    
    analysed_results = {"summary": _compute_summary(execution_results)}

    workflow_results = {
        "requirements": requirements,
        "enriched_scenarios": enriched_scenarios,
        "branding_ux_notes": branding_ux_notes,
        "execution_results": execution_results,
    }

    # Minimal RCA-like notes
    fail_count = analysed_results["summary"]["failed"]
    rca = {
        "summary": {
            "fail_count": fail_count,
            "has_failures": fail_count > 0,
        },
        "possible_root_causes": (
            ["Scenario execution failures detected; review selectors, auth, and page timing."]
            if fail_count > 0 else
            ["No failures observed in executed scenarios."]
        ),
        "notes": f"RCA for: {bug_description[:120]}..."
    }

    return {
        "website": website,
        "bug_description": bug_description,
        "intent": intent,
        "workflow_results": workflow_results,
        "rca": rca,
        "analysed_results": analysed_results,
    }