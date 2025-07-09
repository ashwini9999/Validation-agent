# main.py

from agents.user_interaction_agent import user_interaction_agent
from agents.test_scenario_planning_agent import test_scenario_planning_agent
from agents.branding_ux_validation_agent import branding_ux_validation_agent
from agents.playwright_execution_agent import playwright_execution_agent
from agents.result_analysis_agent import result_analysis_agent
from agents.reporting_communication_agent import reporting_communication_agent

from langgraph.graph import StateGraph

import asyncio
import logging
from typing import TypedDict, Optional
from logging_config import setup_logging

# Initialize logging
setup_logging(log_level=logging.INFO)

class AgentState(TypedDict):
    input: str
    website: str
    requirements: dict
    scenarios: list
    enriched_scenarios: list
    execution_results: list
    analysed_results: dict
    final_report: str
    auth_config: Optional[dict]  # Add authentication configuration

workflow = StateGraph(AgentState)

# Define nodes
workflow.add_node("UIA", user_interaction_agent)
workflow.add_node("TSPA", test_scenario_planning_agent)
workflow.add_node("BUVA", branding_ux_validation_agent)
workflow.add_node("PMEA", playwright_execution_agent)
workflow.add_node("RAA", result_analysis_agent)
workflow.add_node("RCA", reporting_communication_agent)

# Entry point
workflow.set_entry_point("UIA")

# Define workflow edges (agent sequence)
workflow.add_edge("UIA", "TSPA")
workflow.add_edge("TSPA", "BUVA")
workflow.add_edge("BUVA", "PMEA")
workflow.add_edge("PMEA", "RAA")
workflow.add_edge("RAA", "RCA")

# Finish point (last agent in the chain)
workflow.set_finish_point("RCA")

# Compile into executable LangGraph app
app = workflow.compile()
