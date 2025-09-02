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

def branding_ux_validation_agent(state: dict) -> dict:
    log_agent_start("BUVA", {
        "scenarios_count": len(state["scenarios"]),
        "scenario_ids": [s.get("scenario_id", "Unknown") for s in state["scenarios"]]
    })
    
    test_scenarios = state["scenarios"]
    
    log_agent_thinking("BUVA", f"Enriching {len(test_scenarios)} test scenarios with branding and UX validation checks")
    
    # Log what scenarios we're working with
    for scenario in test_scenarios:
        log_agent_thinking("BUVA", f"Processing scenario: {scenario.get('scenario_id', 'Unknown')} - {scenario.get('description', 'No description')}")

    prompt = f"""
    You are given detailed UI test scenarios. Enrich each scenario with:
    - branding_checks: specific visual/verbal identity elements (e.g. logo size, colour palette, font usage)
    - ux_checks: layout, spacing, responsiveness, visibility, accessibility

    Input:
    {json.dumps(test_scenarios, indent=2)}

    Respond with a JSON array like:
    [
      {{
        "scenario_id": "SC001",
        "branding_checks": ["Check logo placement", "Primary colours used"],
        "ux_checks": ["Button is visible", "Text contrast is high"]
      }},
      ...
    ]
    """
    
    log_agent_thinking("BUVA", "Preparing to send validation enrichment prompt to LLM")
    log_llm_prompt("BUVA", prompt)

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You're a UX and branding QA assistant adding validation checks to test cases."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    raw_output = response.choices[0].message.content
    if raw_output is None:
        error_msg = "OpenAI API returned None content"
        log_agent_error("BUVA", error_msg)
        raise ValueError(error_msg)
    
    raw_output = raw_output.strip()
    log_llm_response("BUVA", raw_output)
    log_agent_thinking("BUVA", "Parsing LLM response to extract validation checks")

    try:
        enriched_checks = json.loads(raw_output)
        log_agent_thinking("BUVA", f"Successfully parsed validation checks for {len(enriched_checks)} scenarios")
        
        # Log what checks were added
        for check in enriched_checks:
            scenario_id = check.get("scenario_id", "Unknown")
            branding_count = len(check.get("branding_checks", []))
            ux_count = len(check.get("ux_checks", []))
            log_agent_thinking("BUVA", f"Scenario {scenario_id}: Added {branding_count} branding checks, {ux_count} UX checks")
            
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse GPT output: {str(e)}"
        log_agent_error("BUVA", error_msg)
        log_agent_error("BUVA", f"Raw output was: {raw_output}")
        raise

    log_agent_thinking("BUVA", "Merging validation checks back into original scenarios")
    
    # Merge checks back into the original scenarios
    scenario_dict = {s["scenario_id"]: s for s in test_scenarios}

    for enriched in enriched_checks:
        sid = enriched["scenario_id"]
        if sid in scenario_dict:
            branding_checks = enriched.get("branding_checks", [])
            ux_checks = enriched.get("ux_checks", [])
            
            scenario_dict[sid]["branding_checks"] = branding_checks
            scenario_dict[sid]["ux_checks"] = ux_checks
            
            log_agent_thinking("BUVA", f"Merged checks for {sid}: {len(branding_checks)} branding + {len(ux_checks)} UX checks")
        else:
            log_agent_error("BUVA", f"Scenario ID {sid} not found in original scenarios")

    enriched_scenarios = list(scenario_dict.values())
    
    result = {"enriched_scenarios": enriched_scenarios}
    
    log_agent_complete("BUVA", {
        "enriched_scenarios_count": len(enriched_scenarios),
        "total_branding_checks": sum(len(s.get("branding_checks", [])) for s in enriched_scenarios),
        "total_ux_checks": sum(len(s.get("ux_checks", [])) for s in enriched_scenarios)
    })
    
    return result
