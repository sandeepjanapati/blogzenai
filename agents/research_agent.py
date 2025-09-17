# agents/research_agent.py
import asyncio
import aiohttp
import os
from utils.api_clients import fetch_news_async, fetch_datamuse_keywords, fetch_quotable_quotes
from rich.console import Console

console = Console()

async def gather_research(topic: str, subtopics: list, newsdata_api_key: str):
    """
    Gathers research materials (news, keywords, quotes) concurrently.
    """
    console.print(f"[cyan]Starting research for topic: '{topic}'...[/cyan]")
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
         console.print(f"[yellow]News fetching task failed: {news_results}[/yellow]")
    if isinstance(quotes_results, Exception):
         console.print(f"[yellow]Quotes fetching task failed: {quotes_results}[/yellow]")


    research_data = {
        'news': news,
        'keywords': keywords,
        'quotes': quotes
    }
    console.print(f"[green]Research complete. Found {len(news)} news items, {len(keywords)} keywords, {len(quotes)} quotes.[/green]")
    return research_data