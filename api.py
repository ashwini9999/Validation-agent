from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from main import app as langgraph_app, AgentState
import asyncio
import logging
from typing import Optional, Dict, Any
from logging_config import setup_logging, get_agent_logger
import os  # <-- added

# Initialize logging
setup_logging(log_level=logging.INFO)
logger = get_agent_logger("API")

api = FastAPI()

class RunInput(BaseModel):
    input: str
    website: str
    auth_config: Optional[Dict[str, Any]] = None  # optional authentication configuration


@api.post("/run")
async def run_agent(payload: RunInput):
    logger.info(f"🚀 API REQUEST RECEIVED")
    logger.info(f"📍 Website: {payload.website}")
    logger.info(f"📝 Input: {payload.input}")
    
    # --- Build state ---
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

    # --- Step 1: Use auth_config from request if provided ---
    if payload.auth_config:
        input_data["auth_config"] = payload.auth_config
        auth_type = payload.auth_config.get("type", "unknown")
        logger.info(f"🔐 Authentication (from request): {auth_type}")
    else:
        # --- Step 2: Fallback to .env ---
        auth_type = os.getenv("AUTH_TYPE", "none").lower()
        if auth_type != "none":
            input_data["auth_config"] = {
                "type": auth_type,
                "login_url": os.getenv("AUTH_LOGIN_URL", ""),
                "username": os.getenv("AUTH_USERNAME"),
                "password": os.getenv("AUTH_PASSWORD"),
            }
            logger.info(f"🔐 Authentication (from .env): {auth_type}")
        else:
            logger.info(f"🔓 No authentication configured")

    logger.info(f"🔄 Starting agent workflow...")
    logger.info(f"AUTH_CONFIG passed to agent: {input_data.get('auth_config')}")

    try:
        result = await langgraph_app.ainvoke(input_data)

        # Prefer orchestrator’s analysed_results if present
        analysed_results = result.get("analysed_results", {}) or {}
        summary = analysed_results.get("summary", {}) or {}

        logger.info(f"✅ WORKFLOW COMPLETED")
        logger.info(f"📊 Final Result: {summary.get('overall_result', 'Unknown')}")
        logger.info(
            f"📈 Summary: {summary.get('passed', 0)} passed, "
            f"{summary.get('failed', 0)} failed out of {summary.get('total_scenarios', 0)} scenarios"
        )
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
