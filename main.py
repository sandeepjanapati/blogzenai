# main.py
# This file contains the core, stateless logic for the AI blog generation agent.
# It is designed to be called by a web server (like api.py) or run directly as a CLI for testing.

import argparse
import os
import asyncio
from dotenv import load_dotenv

# Import agent functions
from agents.understanding_agent import analyze_topic
from agents.research_agent import gather_research
from agents.writing_agent import generate_blog_post
from agents.seo_agent import generate_seo_metadata
from agents.export_agent import export_results

# Import utility functions
from utils.api_clients import get_gemini_client

# --- Main Agent Function ---

async def run_blog_agent(topic: str, tone: str, output_dir: str, run_mode: str = 'cli'):
    """
    Main asynchronous function to run the blog writing agent workflow.
    This function is stateless and designed to be run in any environment.

    Args:
        topic (str): The main topic for the blog post.
        tone (str): Desired writing tone.
        output_dir (str): Directory for conceptual file paths (not for saving in the cloud).
        run_mode (str): 'cli' or 'api'. Controls logging output format.

    Returns:
        tuple: (markdown_content, metadata) if successful, otherwise (None, None).
    """
    # Helper for logging. Use standard print for API, rich console for CLI.
    def log_message(message, is_panel=False):
        if run_mode == 'api':
            print(message)
        else:
            # Lazy import rich only for CLI mode
            from rich.console import Console
            from rich.panel import Panel
            console = Console()
            if is_panel:
                console.print(Panel(message, border_style="blue"))
            else:
                console.print(message)

    log_message(f"🚀 Starting Blog Agent for Topic: '{topic}' | Tone: '{tone}' 🚀", is_panel=True)

    # --- 0. Initialize Clients & Get API Keys from Environment ---
    # In a server environment (like Cloud Run), API keys MUST be set as environment variables.
    # The dotenv library is used here for local development with a .env file.
    load_dotenv()
    newsdata_api_key = os.getenv("NEWSDATA_API_KEY")
    gemini_client = get_gemini_client() # This utility function also uses os.getenv()

    if not newsdata_api_key or not gemini_client:
        error_msg = "[ERROR] API Keys (NEWSDATA_API_KEY or GEMINI_API_KEY) not found in environment variables."
        log_message(error_msg)
        return None, None

    # --- 1. Understand the Topic ---
    log_message("[INFO] Step 1: Analyzing Topic...")
    analysis = analyze_topic(topic, tone, gemini_client)
    if not analysis or not analysis.get('subtopics'):
        error_msg = "[ERROR] Failed to analyze topic or get subtopics."
        log_message(error_msg)
        return None, None
    subtopics = analysis['subtopics']
    confirmed_tone = analysis['tone']
    log_message(f"   - Confirmed Tone: {confirmed_tone}")
    log_message(f"   - Identified Subtopics: {subtopics}")

    # --- 2. Conduct Research (Async) ---
    log_message("[INFO] Step 2: Conducting Research...")
    research_data = await gather_research(topic, subtopics, newsdata_api_key)
    # Basic check for research data
    if not research_data:
        log_message("[WARN] Research step yielded no data, continuing with generation.")

    # --- 3. Generate Content ---
    log_message("[INFO] Step 3: Generating Content...")
    markdown_content = generate_blog_post(topic, subtopics, confirmed_tone, research_data, gemini_client)
    if not markdown_content or len(markdown_content) < 100: # Basic content check
        error_msg = "[ERROR] Content generation failed or produced very short output."
        log_message(error_msg)
        return None, None

    # --- 4. SEO Optimization ---
    log_message("[INFO] Step 4: Optimizing SEO...")
    metadata = generate_seo_metadata(topic, markdown_content, research_data, gemini_client)
    if not metadata or not metadata.get('slug'):
        error_msg = "[ERROR] Failed to generate SEO metadata or slug."
        log_message(error_msg)
        # We can still return the content even if SEO metadata fails
        return markdown_content, None

    log_message(f"   - Generated Title: '{metadata['title']}'")

    # --- 5. Export (Conceptual) ---
    # In API mode, this step just logs the action. The content is returned directly.
    log_message("[INFO] Step 5: Finalizing Results...")
    export_results(markdown_content, metadata, output_dir, metadata['slug'])

    log_message("✅ Blog post generation complete!")
    return markdown_content, metadata
