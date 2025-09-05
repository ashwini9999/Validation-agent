from openai import AzureOpenAI

from dotenv import load_dotenv
import os
import json
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from logging_config import (
    log_agent_start, log_agent_thinking, log_llm_prompt, 
    log_llm_response, log_agent_complete, log_agent_error
)

load_dotenv()
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

def test_scenario_planning_agent(state: dict) -> dict:
    log_agent_start("TSPA", {
        "requirements_keys": list(state["requirements"].keys()),
        "components_count": len(state["requirements"].get("components", []))
    })
    
    structured_requirements = state["requirements"]
    
    log_agent_thinking("TSPA", "Analyzing structured requirements to create test scenarios")
    
    components = structured_requirements.get("components", [])
    if components:
        log_agent_thinking("TSPA", f"Will create scenarios for {len(components)} components: {', '.join(components)}")
    
    branding = structured_requirements.get("branding_guidelines", "default")
    if branding != "default":
        log_agent_thinking("TSPA", f"Incorporating branding guidelines: {branding}")
    
    ux = structured_requirements.get("ux_considerations", "default")
    if ux != "default":
        log_agent_thinking("TSPA", f"Incorporating UX considerations: {ux}")

    prompt = f"""
    Based on the following structured requirements, create detailed test scenarios for automated UI/UX testing.

    Requirements:
    {json.dumps(structured_requirements, indent=2)}

    For each test scenario, include:
    - scenario_id (unique identifier)
    - description (short and clear)
    - steps (as a numbered list)
    - expected_result (what should happen)

    Output a JSON array:
    [
      {{
        "scenario_id": "SC001",
        "description": "...",
        "steps": ["Step 1", "Step 2"],
        "expected_result": "..."
      }}
    ]
    """
    
    log_agent_thinking("TSPA", "Preparing to send scenario generation prompt to LLM")
    log_llm_prompt("TSPA", prompt)

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You're a senior QA engineer creating UI/UX test cases."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    raw_output = response.choices[0].message.content
    if raw_output is None:
        error_msg = "OpenAI API returned None content"
        log_agent_error("TSPA", error_msg)
        raise ValueError(error_msg)
    
    raw_output = raw_output.strip()
    log_llm_response("TSPA", raw_output)
    log_agent_thinking("TSPA", "Parsing LLM response to extract test scenarios")

    try:
        scenarios = json.loads(raw_output)
        log_agent_thinking("TSPA", f"Successfully parsed {len(scenarios)} test scenarios")
        
        # Log scenario details
        for i, scenario in enumerate(scenarios):
            log_agent_thinking("TSPA", f"Scenario {i+1}: {scenario.get('scenario_id', 'Unknown')} - {scenario.get('description', 'No description')}")
            
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse GPT output: {str(e)}"
        log_agent_error("TSPA", error_msg)
        log_agent_error("TSPA", f"Raw output was: {raw_output}")
        raise

    result = {"scenarios": scenarios}
    
    log_agent_complete("TSPA", {
        "scenarios_generated": len(scenarios),
        "scenario_ids": [s.get("scenario_id", "Unknown") for s in scenarios]
    })
    
    return result
