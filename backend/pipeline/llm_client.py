import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")
)

MODEL = "meta/llama-3.3-70b-instruct"

def call_model(prompt: str, retries: int = 3, wait: int = 10) -> str:
    """
    Unified model call function.
    All pipeline stages use this — swap model here once for everything.
    """
    import time
    from openai import RateLimitError

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,        # Low temp = more deterministic JSON
                top_p=0.7,
                max_tokens=2048,
            )
            return response.choices[0].message.content

        except RateLimitError as e:
            if attempt < retries - 1:
                import logging
                logging.getLogger(__name__).warning(
                    f"Rate limit hit — waiting {wait}s before retry {attempt + 2}/{retries}"
                )
                time.sleep(wait)
            else:
                raise e