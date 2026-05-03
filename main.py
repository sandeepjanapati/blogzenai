# main.py
import asyncio
from agents.understanding_agent import analyze_topic
from agents.research_agent import gather_research
from agents.writing_agent import generate_blog_post
from agents.seo_agent import generate_seo_metadata
from agents.export_agent import export_results
from utils.api_clients import get_gemini_client
from utils.runtime_config import get_runtime_value


async def run_blog_agent(topic: str, tone: str, output_dir: str, run_mode: str = 'cli', progress_callback=None):
    def log_message(message, is_panel=False):
        if run_mode == 'api': print(message)
        else:
            from rich.console import Console
            from rich.panel import Panel
            console = Console(); console.print(Panel(message, border_style="blue") if is_panel else message)

    def emit(step, message, icon, status, progress):
        if progress_callback:
            progress_callback(step, message, icon, status, progress)

    log_message(f"🚀 Starting Blog Agent for Topic: '{topic}' | Tone: '{tone}' 🚀", is_panel=True)

    newsdata_api_key = get_runtime_value("NEWSDATA_API_KEY", allow_local_dev_default=False)
    gemini_client = get_gemini_client()

    if not newsdata_api_key:
        error_msg = "[ERROR] Required environment variable NEWSDATA_API_KEY is missing."
        log_message(error_msg)
        return None, None
    if not gemini_client:
        error_msg = "[ERROR] Gemini client failed to initialize. For local dev, ensure your Google auth can access the bolgzenai project."
        log_message(error_msg)
        return None, None

    log_message("[INFO] Step 1: Analyzing Topic...")
    emit("analyzing", "Analyzing your topic...", "🧠", "active", 5)
    analysis = await asyncio.to_thread(analyze_topic, topic, tone, gemini_client)
    if not analysis or not analysis.get('subtopics'):
        emit("analyzing", "Topic analysis failed", "🧠", "error", 5)
        return None, None
    subtopics, confirmed_tone = analysis['subtopics'], analysis['tone']
    emit("analyzing", "Topic analyzed", "🧠", "done", 15)
    log_message(f"   - Confirmed Tone: {confirmed_tone}\n   - Identified Subtopics: {subtopics}")

    log_message("[INFO] Step 2: Conducting Research...")
    emit("researching", "Researching latest news and trends...", "📰", "active", 18)
    research_data = await gather_research(topic, subtopics, newsdata_api_key)
    emit("researching", "Research complete", "📰", "done", 25)

    log_message("[INFO] Step 3: Generating Content...")
    emit("writing", "Writing introduction...", "✍️", "active", 28)
    markdown_content = await asyncio.to_thread(
        generate_blog_post, topic, subtopics, confirmed_tone, research_data, gemini_client,
        progress_callback=progress_callback
    )
    if not markdown_content or len(markdown_content) < 100:
        emit("writing", "Content generation failed", "✍️", "error", 28)
        return None, None
    emit("writing", "Content written", "✍️", "done", 82)

    log_message("[INFO] Step 4: Optimizing SEO...")
    emit("seo", "Optimizing for SEO...", "🔧", "active", 85)
    metadata = await asyncio.to_thread(
        generate_seo_metadata, topic, markdown_content, research_data, gemini_client
    )
    if not metadata or not metadata.get('slug'):
        emit("seo", "SEO optimization failed", "🔧", "error", 85)
        return markdown_content, None
    emit("seo", "SEO optimized", "🔧", "done", 95)
    log_message(f"   - Generated Title: '{metadata['title']}'")

    log_message("[INFO] Step 5: Finalizing Results...")
    emit("finalizing", "Finalizing your blog post...", "✅", "active", 97)
    await asyncio.to_thread(export_results, markdown_content, metadata, output_dir, metadata['slug'])
    emit("finalizing", "Complete!", "✅", "done", 100)

    log_message("✅ Blog post generation complete!")
    return markdown_content, metadata
