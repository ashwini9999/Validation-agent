from openai import AzureOpenAI
import os
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from dotenv import load_dotenv

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

def _get_response_from_azure_openAI(system_message, user_message, model="gpt-4", temperature=0.2):
    """
    Sends system and user messages to the LLM and returns structured testing requirements.

    Args:
        system_message (str): The system role message (instructions for context).
        user_message (str): The user input prompt.
        client: The initialized OpenAI client instance.
        model (str, optional): Model name (default: "gpt-4").
        temperature (float, optional): Sampling temperature (default: 0.2).

    Returns:
        str: The text content of the LLM's response.
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ],
        temperature=temperature
    )

    return response.choices[0].message.content
