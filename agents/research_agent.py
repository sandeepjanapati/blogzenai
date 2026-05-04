# agents/research_agent.py
import asyncio
import aiohttp
from utils.api_clients import fetch_news_async, fetch_datamuse_keywords
import logging

async def gather_research(topic: str, subtopics: list, newsdata_api_key: str):
    """
    Gathers research materials (news, keywords) concurrently.
    """
    logging.info(f"Starting research for topic: '{topic}'...")
    keywords = fetch_datamuse_keywords(topic) # Sync call, benefits from caching

    async with aiohttp.ClientSession() as session:
        news_results = await fetch_news_async(session, newsdata_api_key, topic)

    news = news_results if not isinstance(news_results, Exception) else []

    if isinstance(news_results, Exception):
         logging.warning(f"News fetching task failed: {news_results}")

    research_data = {
        'news': news,
        'keywords': keywords,
        'quotes': []
    }
    logging.info(f"Research complete. Found {len(news)} news items, {len(keywords)} keywords.")
    return research_data