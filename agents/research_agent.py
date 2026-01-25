# agents/research_agent.py
import asyncio
import aiohttp
import os
from utils.api_clients import fetch_news_async, fetch_datamuse_keywords, fetch_quotable_quotes
import logging

async def gather_research(topic: str, subtopics: list, newsdata_api_key: str):
    """
    Gathers research materials (news, keywords, quotes) concurrently.
    """
    logging.info(f"Starting research for topic: '{topic}'...")
    keywords = fetch_datamuse_keywords(topic) # Sync call, benefits from caching

    async with aiohttp.ClientSession() as session:
        # Create tasks for async operations
        news_task = asyncio.create_task(fetch_news_async(session, newsdata_api_key, topic))
        # We can fetch quotes based on the main topic or derived keywords
        quotes_task = asyncio.create_task(asyncio.to_thread(fetch_quotable_quotes, keywords)) # Run sync quote fetch in thread

        # Wait for all async tasks to complete
        news_results, quotes_results = await asyncio.gather(
            news_task,
            quotes_task,
            return_exceptions=True # Prevent one failure from stopping others
        )

    # Handle potential exceptions returned by asyncio.gather
    news = news_results if not isinstance(news_results, Exception) else []
    quotes = quotes_results if not isinstance(quotes_results, Exception) else []

    if isinstance(news_results, Exception):
         logging.warning(f"News fetching task failed: {news_results}")
    if isinstance(quotes_results, Exception):
         logging.warning(f"Quotes fetching task failed: {quotes_results}")


    research_data = {
        'news': news,
        'keywords': keywords,
        'quotes': quotes
    }
    logging.info(f"Research complete. Found {len(news)} news items, {len(keywords)} keywords, {len(quotes)} quotes.")
    return research_data