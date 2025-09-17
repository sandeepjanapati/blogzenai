# utils/api_clients.py
import os
import google.generativeai as genai
import requests
import aiohttp
import asyncio
import functools

# This file is now clean of any UI (Streamlit) or CLI (Rich, dotenv) dependencies.
# It's designed to run in a server environment where configuration is passed via
# environment variables.

# --- Gemini Client ---
def get_gemini_client():
    """
    Initializes and returns the Gemini client.
    It relies on the GEMINI_API_KEY environment variable, which is securely
    injected by Cloud Run from Secret Manager.
    """
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable not found.")
        # In a server environment, this is a critical configuration error.
        # The application cannot function without it.
        return None

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash') # Updated to a more recent model
        print("Gemini client configured successfully.")
        return model
    except Exception as e:
        print(f"ERROR: Failed to initialize Gemini client: {e}")
        return None

# --- NewsData.io Client ---
async def fetch_news_async(session, api_key, topic):
    """Fetches news related to the topic asynchronously."""
    if not api_key:
        print("WARNING: NewsData API key is missing. Skipping news fetch.")
        return []

    # Basic URL encoding for the topic
    query = requests.utils.quote(topic)
    url = f"https://newsdata.io/api/1/news?apikey={api_key}&q={query}&language=en"

    try:
        async with session.get(url, timeout=15) as response:
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            data = await response.json()
            # Limit to top 3 relevant articles for context
            return data.get('results', [])[:3]
    except aiohttp.ClientError as e:
        print(f"WARNING: NewsData API request failed: {e}")
        return []
    except asyncio.TimeoutError:
        print("WARNING: NewsData API request timed out.")
        return []
    except Exception as e:
        print(f"WARNING: An unexpected error occurred during NewsData fetch: {e}")
        return []


# --- Datamuse Client ---
@functools.lru_cache(maxsize=128) # Cache results for repeated keyword lookups
def fetch_datamuse_keywords(topic):
    """Fetches related keywords from Datamuse."""
    keywords = set()
    try:
        # Means like
        response_ml = requests.get(f"https://api.datamuse.com/words?ml={topic}&max=10")
        response_ml.raise_for_status()
        keywords.update(item['word'] for item in response_ml.json())

        # Related triggers (often good for SEO)
        response_trg = requests.get(f"https://api.datamuse.com/words?rel_trg={topic}&max=10")
        response_trg.raise_for_status()
        keywords.update(item['word'] for item in response_trg.json())

        return list(keywords)[:15] # Limit total keywords
    except requests.exceptions.RequestException as e:
        print(f"WARNING: Datamuse API request failed: {e}")
        return []
    except Exception as e:
        print(f"WARNING: An unexpected error occurred during Datamuse fetch: {e}")
        return []

# --- Quotable.io Client ---
def fetch_quotable_quotes(topic_keywords):
    """Fetches quotes related to topic keywords."""
    quotes = []
    # Try fetching quotes for the first few keywords
    tags = "|".join(topic_keywords[:3]) # Search using OR for first 3 keywords
    if not tags:
        return []
    try:
        response = requests.get(f"https://api.quotable.io/quotes/random?limit=2&tags={tags}", timeout=10)
        response.raise_for_status()
        quotes_data = response.json()
        quotes = [f"\"{q['content']}\" - {q['author']}" for q in quotes_data]
        return quotes
    except requests.exceptions.RequestException as e:
        print(f"WARNING: Quotable API request failed: {e}")
        return []
    except Exception as e:
        print(f"WARNING: An unexpected error occurred during Quotable fetch: {e}")
        return []