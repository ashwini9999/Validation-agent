from openai import OpenAI
from dotenv import load_dotenv
import os
import json

load_dotenv()

# ✅ Define OpenAI client here at module level
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def user_interaction_agent(state: dict) -> dict:
    input_text = state["input"]
    website_url = state["website"]  # Use the website URL provided in the API request

    prompt = f"""
    Extract structured test requirements from the user request below.

    User Request:
    {input_text}

    Website URL: {website_url}

    Structured Requirements should include:
    - UI Elements or Components to test
    - Branding guidelines mentioned
    - UX considerations
    - Any special instructions or constraints

    Output as raw JSON only, no explanation or markdown formatting.
    {{
        "website": "{website_url}",
        "components": ["<component 1>", "<component 2>", "..."],
        "branding_guidelines": "<guidelines or 'default'>",
        "ux_considerations": "<specific considerations or 'default'>",
        "special_instructions": "<instructions or 'none'>"
    }}
    """

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You're an expert test analyst extracting structured testing requirements."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    raw_output = response.choices[0].message.content
    if raw_output is None:
        raise ValueError("OpenAI API returned None content")
    raw_output = raw_output.strip()

    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError as e:
        print("❌ JSON decode error in user_interaction_agent")
        print("Raw output was:\n", raw_output)
        raise e

    # Ensure we use the website URL from the API request
    parsed["website"] = website_url

    return {
        "requirements": parsed,
        "website": website_url  # Use the provided website URL
    }
