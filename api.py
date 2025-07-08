from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from main import app as langgraph_app, AgentState
import asyncio

api = FastAPI()  # <-- Rename from 'app' to 'api'

class RunInput(BaseModel):
    input: str
    website: str

@api.post("/run")
async def run_agent(payload: RunInput):
    try:
        input_data: AgentState = {
            "input": payload.input,
            "website": payload.website,
            "requirements": {},
            "scenarios": [],
            "enriched_scenarios": [],
            "execution_results": [],
            "analysed_results": {},
            "final_report": ""
        }
        result = await langgraph_app.ainvoke(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
