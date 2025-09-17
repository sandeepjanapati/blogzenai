# utils/api_clients.py
import os
import google.generativeai as genai
import requests
import aiohttp
import asyncio
import functools
from rich.console import Console
import streamlit as st # <--- Add Streamlit import
from dotenv import load_dotenv # <--- Add dotenv import

console = Console()

# --- Gemini Client ---
def get_gemini_client():
    """Initializes and returns the Gemini client, checking st.secrets first."""
    api_key = None
    # Try Streamlit secrets first (will only work when deployed)
    try:
        if hasattr(st, 'secrets') and "GEMINI_API_KEY" in st.secrets:
             api_key = st.secrets["GEMINI_API_KEY"]
             # print("Using Gemini key from st.secrets") # Debug print
    except Exception:
        pass # Fail silently if st.secrets not available or key missing

    # If not found via st.secrets, try environment variables (for local .env)
    if not api_key:
        # print("Gemini key not found in st.secrets, trying .env") # Debug print
        load_dotenv() # Load .env file if running locally
        api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        console.print("[bold red]Error: GEMINI_API_KEY not found in st.secrets or environment variables.[/bold red]")
        # Also show error in Streamlit if possible (though this runs before UI usually)
        # Consider raising an exception here instead of returning None for clarity
        return None

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        # print("Gemini client configured successfully.") # Debug print
        return model
    except Exception as e:
        console.print(f"[bold red]Error initializing Gemini client: {e}[/bold red]")
        return None

# --- NewsData.io Client ---
async def fetch_news_async(session, api_key, topic):
    """Fetches news related to the topic asynchronously."""
    # Basic URL encoding for the topic
    query = requests.utils.quote(topic)
    url = f"https://newsdata.io/api/1/news?apikey={api_key}&q={query}&language=en"
    # Add retry logic here later if needed
    try:
        async with session.get(url, timeout=15) as response: # Added timeout
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            data = await response.json()
            # Limit to top 3 relevant articles for context
            return data.get('results', [])[:3]
    except aiohttp.ClientError as e:
        console.print(f"[yellow]NewsData API request failed: {e}[/yellow]")
        return []
    except asyncio.TimeoutError:
        console.print("[yellow]NewsData API request timed out.[/yellow]")
        return []
    except Exception as e:
        console.print(f"[yellow]An unexpected error occurred during NewsData fetch: {e}[/yellow]")
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
        console.print(f"[yellow]Datamuse API request failed: {e}[/yellow]")
        return []
    except Exception as e:
        console.print(f"[yellow]An unexpected error occurred during Datamuse fetch: {e}[/yellow]")
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
        console.print(f"[yellow]Quotable API request failed: {e}[/yellow]")
        return []
    except Exception as e:
        console.print(f"[yellow]An unexpected error occurred during Quotable fetch: {e}[/yellow]")
        return []