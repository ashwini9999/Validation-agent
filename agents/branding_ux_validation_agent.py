from openai import OpenAI
from dotenv import load_dotenv
import os
import json

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def branding_ux_validation_agent(state: dict) -> dict:
    test_scenarios = state["scenarios"]

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

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You're a UX and branding QA assistant adding validation checks to test cases."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    raw_output = response.choices[0].message.content.strip()

    try:
        enriched_checks = json.loads(raw_output)
    except json.JSONDecodeError:
        print("❌ Failed to parse GPT output in BUVA:\n", raw_output)
        raise

    # Merge checks back into the original scenarios
    scenario_dict = {s["scenario_id"]: s for s in test_scenarios}

    for enriched in enriched_checks:
        sid = enriched["scenario_id"]
        if sid in scenario_dict:
            scenario_dict[sid]["branding_checks"] = enriched.get("branding_checks", [])
            scenario_dict[sid]["ux_checks"] = enriched.get("ux_checks", [])

    return {"enriched_scenarios": list(scenario_dict.values())}
