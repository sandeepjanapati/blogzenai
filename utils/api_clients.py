# utils/api_clients.py
import logging
import os
import requests
import aiohttp
import functools
import vertexai
from vertexai.generative_models import GenerativeModel

from utils.runtime_config import get_google_credentials, get_runtime_value

def get_gemini_client():
    """
    Initializes the Gemini client using the Vertex AI SDK. This is the correct method.
    """
    try:
        gcp_project_id = get_runtime_value("GCP_PROJECT", allow_local_dev_default=False)
        gcp_region = "us-central1"
        google_credentials = get_google_credentials()

        if not gcp_project_id:
            logging.error("GCP_PROJECT could not be resolved. Cannot init Vertex AI.")
            return None

        vertexai.init(
            project=gcp_project_id,
            location=gcp_region,
            credentials=google_credentials,
        )

        model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash-lite")
        model = GenerativeModel(model_name)

        logging.info(f"Vertex AI client initialized successfully for project '{gcp_project_id}' with model '{model_name}'.")
        return model
    except Exception as e:
        logging.error(f"FATAL: Failed to initialize Vertex AI client: {e}", exc_info=True)
        return None

async def fetch_news_async(session, api_key, topic):
    if not api_key: return []
    query = requests.utils.quote(topic)
    url = f"https://newsdata.io/api/1/news?apikey={api_key}&q={query}&language=en"
    try:
        async with session.get(url, timeout=15) as response:
            response.raise_for_status()
            data = await response.json()
            return data.get('results', [])[:3]
    except Exception as e: logging.warning(f"NewsData API request failed: {e}"); return []

@functools.lru_cache(maxsize=128)
def fetch_datamuse_keywords(topic):
    keywords = set()
    try:
        response_ml = requests.get(f"https://api.datamuse.com/words?ml={topic}&max=10")
        response_ml.raise_for_status()
        keywords.update(item['word'] for item in response_ml.json())
        response_trg = requests.get(f"https://api.datamuse.com/words?rel_trg={topic}&max=10")
        response_trg.raise_for_status()
        keywords.update(item['word'] for item in response_trg.json())
        return list(keywords)[:15]
    except Exception as e: logging.warning(f"Datamuse API request failed: {e}"); return []

