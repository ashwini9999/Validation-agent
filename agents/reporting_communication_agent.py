from datetime import datetime

def reporting_communication_agent(state: dict) -> dict:
    analysed_results = state["analysed_results"]
    website = state["website"]

    report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary = analysed_results["summary"]

    report = f"""
    UI/UX and Branding Test Report
    Website: {website}
    Generated on: {report_time}

    Overall Result: {summary['overall_result']}
    Total Scenarios: {summary['total_scenarios']}
    ✅ Passed: {summary['passed']}
    ❌ Failed: {summary['failed']}

    Detailed Results:
    --------------------------------
    """

    for detail in analysed_results["details"]:
        status_emoji = "✅" if detail["result"] == "Pass" else "❌"
        report += f"""
    Scenario ID: {detail['scenario_id']}
    Description: {detail['description']}
    Result: {status_emoji} {detail['result']}
    Screenshot: {detail['screenshot_path']}
        """

        if detail["issues"]:
            report += "\n    Issues:\n"
            for issue in detail["issues"]:
                report += f"      - {issue}\n"

        report += "\n    --------------------------------"

    return {"final_report": report}
