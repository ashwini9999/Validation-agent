from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from main import app as langgraph_app, AgentState
import asyncio
import logging
from typing import Optional, Dict, Any
from logging_config import setup_logging, get_agent_logger

# Initialize logging
setup_logging(log_level=logging.INFO)
logger = get_agent_logger("API")

api = FastAPI()

class RunInput(BaseModel):
    input: str
    website: str
    auth_config: Optional[Dict[str, Any]] = None  # New: optional authentication configuration

@api.post("/run")
async def run_agent(payload: RunInput):
    logger.info(f"🚀 API REQUEST RECEIVED")
    logger.info(f"📍 Website: {payload.website}")
    logger.info(f"📝 Input: {payload.input}")
    
    # Log authentication info if provided
    if payload.auth_config:
        auth_type = payload.auth_config.get("type", "unknown")
        logger.info(f"🔐 Authentication: {auth_type}")
    else:
        logger.info(f"🔓 No authentication required")
    
    logger.info(f"🔄 Starting agent workflow...")
    
    try:
        # Pass auth_config through the state dict
        input_data = {
            "input": payload.input,
            "website": payload.website,
            "requirements": {},
            "scenarios": [],
            "enriched_scenarios": [],
            "execution_results": [],
            "analysed_results": {},
            "final_report": "",
        }
        
        # Add auth_config to state if provided
        if payload.auth_config:
            input_data["auth_config"] = payload.auth_config
        
        logger.info(f"🎬 Invoking LangGraph workflow with {len(input_data)} state fields")
        result = await langgraph_app.ainvoke(input_data)
        
        # Log final results
        analysed_results = result.get("analysed_results", {})
        summary = analysed_results.get("summary", {})
        
        logger.info(f"✅ WORKFLOW COMPLETED")
        logger.info(f"📊 Final Result: {summary.get('overall_result', 'Unknown')}")
        logger.info(f"📈 Summary: {summary.get('passed', 0)} passed, {summary.get('failed', 0)} failed out of {summary.get('total_scenarios', 0)} scenarios")
        logger.info(f"🎯 API RESPONSE READY")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ API ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api.on_event("startup")
async def startup_event():
    logger.info("🌟 UI/UX Testing Agent API starting up...")
    logger.info("📋 Available endpoints:")
    logger.info("  POST /run - Execute UI/UX testing workflow")
    logger.info("🎯 API ready to accept requests")

@api.on_event("shutdown")
async def shutdown_event():
    logger.info("🔄 UI/UX Testing Agent API shutting down...")
    logger.info("👋 Goodbye!")
