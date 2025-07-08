import json

def result_analysis_agent(state: dict) -> dict:
    execution_results = state["execution_results"]

    analysed_results = {
        "summary": {
            "total_scenarios": len(execution_results),
            "passed": 0,
            "failed": 0,
        },
        "details": []
    }

    for result in execution_results:
        scenario_status = {
            "scenario_id": result["scenario_id"],
            "description": result["description"],
            "result": result["result"],
            "issues": [],
            "screenshot_path": result["screenshot_path"]
        }

        if result["result"] == "Pass":
            analysed_results["summary"]["passed"] += 1
        else:
            analysed_results["summary"]["failed"] += 1
            scenario_status["issues"] = result["details"]

        analysed_results["details"].append(scenario_status)

    analysed_results["summary"]["overall_result"] = (
        "Pass" if analysed_results["summary"]["failed"] == 0 else "Fail"
    )

    return {"analysed_results": analysed_results}

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
