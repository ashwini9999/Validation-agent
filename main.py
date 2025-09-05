# main.py
from typing import TypedDict, List, Dict, Any, Optional
import asyncio
import logging

from logging_config import setup_logging, get_agent_logger
#from agents.orchestrator_agent import orchestrator_run
from core.orchestrator_agent import orchestrator_run

# ----- logging -----
setup_logging(log_level=logging.INFO)
logger = get_agent_logger("MAIN")

# ----- AgentState shape expected by api.py -----
class AgentState(TypedDict, total=False):
    input: str
    website: str
    requirements: Dict[str, Any]
    scenarios: List[Dict[str, Any]]
    enriched_scenarios: List[Dict[str, Any]]
    execution_results: List[Dict[str, Any]]
    analysed_results: Dict[str, Any]
    final_report: str
    auth_config: Dict[str, Any]
    bug_description: str  # optional alias; orchestrator falls back to 'input'

# ----- Simple app wrapper providing .ainvoke(...) -----
class _SimpleLangGraphApp:
    async def ainvoke(self, state: AgentState) -> Dict[str, Any]:
        logger.info("🧩 MAIN: invoking orchestrator")
        # Orchestrator will:
        #  - read state['input'] (or bug_description)
        #  - extract requirements (ReqX)
        #  - build scenarios
        #  - run Playwright (PMEA)
        #  - compute analysed_results.summary
        result = await orchestrator_run(state)
        logger.info("✅ MAIN: orchestrator completed")
        return result

    # (Optional) sync helper if you ever need it
    def invoke(self, state: AgentState) -> Dict[str, Any]:
        return asyncio.run(self.ainvoke(state))

# Exported symbols used by api.py
app = _SimpleLangGraphApp()
