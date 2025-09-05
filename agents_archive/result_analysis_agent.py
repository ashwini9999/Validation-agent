import json
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from logging_config import (
    log_agent_start, log_agent_thinking, log_agent_complete, log_agent_error
)

def result_analysis_agent(state: dict) -> dict:
    log_agent_start("RAA", {
        "execution_results_count": len(state["execution_results"]),
        "scenario_ids": [r.get("scenario_id", "Unknown") for r in state["execution_results"]]
    })
    
    execution_results = state["execution_results"]
    
    log_agent_thinking("RAA", f"Analyzing results from {len(execution_results)} executed scenarios")

    analysed_results = {
        "summary": {
            "total_scenarios": len(execution_results),
            "passed": 0,
            "failed": 0,
        },
        "details": []
    }
    
    log_agent_thinking("RAA", "Processing individual scenario results")

    for i, result in enumerate(execution_results):
        scenario_id = result.get("scenario_id", "Unknown")
        description = result.get("description", "No description")
        result_status = result.get("result", "Unknown")
        
        log_agent_thinking("RAA", f"Processing scenario {i+1}/{len(execution_results)}: {scenario_id} - {result_status}")
        
        scenario_status = {
            "scenario_id": scenario_id,
            "description": description,
            "result": result_status,
            "issues": [],
            "screenshot_path": result.get("screenshot_path")
        }

        if result_status == "Pass":
            analysed_results["summary"]["passed"] += 1
            log_agent_thinking("RAA", f"Scenario {scenario_id} passed")
        else:
            analysed_results["summary"]["failed"] += 1
            scenario_status["issues"] = result.get("details", [])
            log_agent_thinking("RAA", f"Scenario {scenario_id} failed with {len(scenario_status['issues'])} issues")
            
            # Log the specific issues
            for issue in scenario_status["issues"]:
                log_agent_thinking("RAA", f"  Issue: {issue}")

        analysed_results["details"].append(scenario_status)

    # Determine overall result
    overall_result = "Pass" if analysed_results["summary"]["failed"] == 0 else "Fail"
    analysed_results["summary"]["overall_result"] = overall_result
    
    log_agent_thinking("RAA", f"Analysis complete - Overall result: {overall_result}")
    log_agent_thinking("RAA", f"Summary: {analysed_results['summary']['passed']} passed, {analysed_results['summary']['failed']} failed")
    
    result = {"analysed_results": analysed_results}
    
    log_agent_complete("RAA", {
        "total_scenarios": analysed_results["summary"]["total_scenarios"],
        "passed": analysed_results["summary"]["passed"],
        "failed": analysed_results["summary"]["failed"],
        "overall_result": overall_result
    })
    
    return result

# # Optional: Keep this for local testing
# if __name__ == "__main__":
#     sample_execution_results = [
#         {
#             "scenario_id": "SC001",
#             "description": "Verify homepage logo.",
#             "result": "Pass",
#             "details": ["Logo check passed"],
#             "screenshot_path": "screenshots/SC001.png"
#         },
#         {
#             "scenario_id": "SC002",
#             "description": "Check navigation menu visibility.",
#             "result": "Fail",
#             "details": ["Menu not visible on mobile viewport"],
#             "screenshot_path": "screenshots/SC002.png"
#         }
#     ]

#     result = result_analysis_agent({"execution_results": sample_execution_results})
#     print(json.dumps(result, indent=2))
