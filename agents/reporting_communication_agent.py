from datetime import datetime
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from logging_config import (
    log_agent_start, log_agent_thinking, log_agent_complete, log_agent_error
)

def reporting_communication_agent(state: dict) -> dict:
    log_agent_start("RCA", {
        "website": state["website"],
        "analysed_results_summary": state["analysed_results"].get("summary", {})
    })
    
    analysed_results = state["analysed_results"]
    website = state["website"]
    
    log_agent_thinking("RCA", f"Generating comprehensive report for {website}")
    
    report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary = analysed_results["summary"]
    
    log_agent_thinking("RCA", f"Report timestamp: {report_time}")
    log_agent_thinking("RCA", f"Overall result: {summary.get('overall_result', 'Unknown')}")
    log_agent_thinking("RCA", f"Total scenarios: {summary.get('total_scenarios', 0)}")
    log_agent_thinking("RCA", f"Passed: {summary.get('passed', 0)}, Failed: {summary.get('failed', 0)}")

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
    
    log_agent_thinking("RCA", "Building detailed results section")
    
    details = analysed_results.get("details", [])
    log_agent_thinking("RCA", f"Processing {len(details)} detailed results")

    for i, detail in enumerate(details):
        scenario_id = detail.get("scenario_id", "Unknown")
        description = detail.get("description", "No description")
        result = detail.get("result", "Unknown")
        screenshot_path = detail.get("screenshot_path", "No screenshot")
        
        log_agent_thinking("RCA", f"Adding detail {i+1}/{len(details)}: {scenario_id} - {result}")
        
        status_emoji = "✅" if result == "Pass" else "❌"
        report += f"""
    Scenario ID: {scenario_id}
    Description: {description}
    Result: {status_emoji} {result}
    Screenshot: {screenshot_path}
        """

        issues = detail.get("issues", [])
        if issues:
            log_agent_thinking("RCA", f"Adding {len(issues)} issues for scenario {scenario_id}")
            report += "\n    Issues:\n"
            for issue in issues:
                report += f"      - {issue}\n"

        report += "\n    --------------------------------"
    
    log_agent_thinking("RCA", "Report generation complete")
    log_agent_thinking("RCA", f"Final report length: {len(report)} characters")
    
    result = {"final_report": report}
    
    log_agent_complete("RCA", {
        "report_length": len(report),
        "website": website,
        "report_time": report_time,
        "overall_result": summary.get('overall_result', 'Unknown')
    })
    
    return result
