from openai import OpenAI
from dotenv import load_dotenv
import os
import json

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def test_scenario_planning_agent(state: dict) -> dict:
    structured_requirements = state["requirements"]

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

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You're a senior QA engineer creating UI/UX test cases."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    raw_output = response.choices[0].message.content.strip()

    try:
        scenarios = json.loads(raw_output)
    except json.JSONDecodeError:
        print("❌ Failed to parse GPT output in TSPA:\n", raw_output)
        raise

    return {"scenarios": scenarios}
