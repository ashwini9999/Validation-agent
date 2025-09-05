from openai import AzureOpenAI
from dotenv import load_dotenv
import os
import json
import sys
import os
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

def user_interaction_agent(state: dict) -> dict:
    # Use 'ReqX' to avoid confusion with the UIA classifier/router
    log_agent_start("ReqX", {
        "input_length": len(state["input"]),
        "website": state["website"]
    })
    
    input_text = state["input"]
    website_url = state["website"]  # Use the website URL provided in the API request

    log_agent_thinking("ReqX", "Analyzing user input to extract structured requirements")
    log_agent_thinking("ReqX", f"User wants to test: {input_text[:100]}...")
    log_agent_thinking("ReqX", f"Target website: {website_url}")

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

    log_agent_thinking("ReqX", "Preparing to send requirements extraction prompt to LLM")
    log_llm_prompt("ReqX", prompt)

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
        error_msg = "OpenAI API returned None content"
        log_agent_error("ReqX", error_msg)
        raise ValueError(error_msg)
    
    log_llm_response("ReqX", raw_output)
    log_agent_thinking("ReqX", "Parsing LLM response into structured format")
    
    raw_output = raw_output.strip()

    try:
        parsed = json.loads(raw_output)
        log_agent_thinking("ReqX", f"Successfully parsed requirements: {len(parsed.get('components', []))} components identified")
        
        # Log what was extracted
        components = parsed.get('components', [])
        if components:
            log_agent_thinking("ReqX", f"Components to test: {', '.join(components)}")
        
        branding = parsed.get('branding_guidelines', 'default')
        if branding != 'default':
            log_agent_thinking("ReqX", f"Branding guidelines: {branding}")
        
        ux = parsed.get('ux_considerations', 'default')
        if ux != 'default':
            log_agent_thinking("ReqX", f"UX considerations: {ux}")
            
    except json.JSONDecodeError as e:
        error_msg = f"JSON decode error: {str(e)}"
        log_agent_error("ReqX", error_msg)
        log_agent_error("ReqX", f"Raw output was: {raw_output}")
        raise e

    # Ensure we use the website URL from the API request
    parsed["website"] = website_url

    result = {
        "requirements": parsed,
        "website": website_url  # Use the provided website URL
    }
    
    log_agent_complete("ReqX", {
        "components_count": len(parsed.get('components', [])),
        "has_branding_guidelines": parsed.get('branding_guidelines', 'default') != 'default',
        "has_ux_considerations": parsed.get('ux_considerations', 'default') != 'default',
        "website": website_url
    })
    
    return result
