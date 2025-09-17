# main.py
import argparse
import os
import asyncio
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
import streamlit as st 

# Import agent functions
from agents.understanding_agent import analyze_topic
from agents.research_agent import gather_research
from agents.writing_agent import generate_blog_post
from agents.seo_agent import generate_seo_metadata
from agents.export_agent import export_results

# Import utility functions
from utils.api_clients import get_gemini_client

# Initialize Rich Console (for CLI mode)
console = Console()

# MODIFIED FUNCTION SIGNATURE AND LOGIC
async def run_blog_agent(topic: str, tone: str, output_dir: str, run_mode: str = 'cli'):
    """
    Main asynchronous function to run the blog writing agent workflow.

    Args:
        topic (str): The main topic for the blog post.
        tone (str): Desired writing tone.
        output_dir (str): Directory to save the generated files.
        run_mode (str): 'cli' or 'streamlit'. Controls console output.

    Returns:
        tuple: (markdown_content, metadata) if successful, otherwise (None, None)
               Returns results needed for Streamlit display.
    """
    # Use console only in CLI mode
    def print_cli(*args, **kwargs):
        if run_mode == 'cli':
            console.print(*args, **kwargs)
        # Optionally use st.write or st.info for streamlit mode updates
        # elif run_mode == 'streamlit':
        #    st.write(args[0]) # Basic example, might need better formatting

    print_cli(Panel(f"🚀 Starting Blog Agent for Topic: '[bold cyan]{topic}[/bold cyan]' | Tone: '[italic yellow]{tone}[/italic yellow]' 🚀", title="Blog Agent Initializing", border_style="blue"))

    # --- 0. Load Environment Variables & Initialize Clients ---
    # Ensure dotenv is loaded (might be loaded by Streamlit app already, but safe to call again)
    load_dotenv()
    newsdata_api_key = None
    gemini_api_key_present = False # Flag to check if Gemini key is potentially available

    # Try Streamlit secrets first
    try:
        if hasattr(st, 'secrets'):
            if "NEWSDATA_API_KEY" in st.secrets:
                newsdata_api_key = st.secrets["NEWSDATA_API_KEY"]
            if "GEMINI_API_KEY" in st.secrets:
                gemini_api_key_present = bool(st.secrets["GEMINI_API_KEY"])
    except Exception:
        pass # Fail silently

    # Fallback to environment variables (.env) if not found or not in streamlit context
    if not newsdata_api_key or not gemini_api_key_present:
        load_dotenv() # Load .env for local execution
        if not newsdata_api_key:
            newsdata_api_key = os.getenv("NEWSDATA_API_KEY")
        if not gemini_api_key_present:
             gemini_api_key_present = bool(os.getenv("GEMINI_API_KEY"))


    # Check if keys are *still* missing after trying both methods
    if not newsdata_api_key or not gemini_api_key_present:
        error_msg = "Error: API Keys (NEWSDATA_API_KEY or GEMINI_API_KEY) not found in Streamlit secrets or .env file."
        print_cli(f"[bold red]{error_msg}[/bold red]")
        if run_mode == 'streamlit':
            st.error(error_msg) # Show error in Streamlit UI
        return None, None # Return None if keys are missing

    # Now initialize Gemini client (it will perform its own key check using the updated logic)
    gemini_client = get_gemini_client()
    if not gemini_client:
         error_msg = "Error: Failed to initialize Gemini client. Check API Key source (secrets or .env) and validity."
         print_cli(f"[bold red]{error_msg}[/bold red]")
         if run_mode == 'streamlit':
             st.error(error_msg)
         return None, None

    # --- 1. Understand the Topic ---
    print_cli("[cyan]Step 1: Analyzing Topic...[/cyan]")
    analysis = analyze_topic(topic, tone, gemini_client)
    if not analysis or not analysis.get('subtopics'):
         error_msg = "Error: Failed to analyze topic or get subtopics."
         print_cli(f"[bold red]{error_msg}[/bold red]")
         if run_mode == 'streamlit':
             st.error(error_msg)
         return None, None
    subtopics = analysis['subtopics']
    confirmed_tone = analysis['tone']
    print_cli(f"   - Confirmed Tone: [italic yellow]{confirmed_tone}[/italic yellow]")
    print_cli(f"   - Identified Subtopics: {subtopics}")

    # --- 2. Conduct Research (Async) ---
    print_cli("[cyan]Step 2: Conducting Research...[/cyan]")
    # Ensure newsdata_api_key is not None before passing
    if not newsdata_api_key:
         st.error("Newsdata API Key is missing, cannot conduct research.")
         return None, None
    research_data = await gather_research(topic, subtopics, newsdata_api_key)
    # Add basic check for research data if needed

    # --- 3. Generate Content ---
    print_cli("[cyan]Step 3: Generating Content...[/cyan]")
    markdown_content = generate_blog_post(topic, subtopics, confirmed_tone, research_data, gemini_client)
    if not markdown_content or len(markdown_content) < 100: # Basic check
         error_msg = "Error: Content generation failed or produced very short output."
         print_cli(f"[bold red]{error_msg}[/bold red]")
         if run_mode == 'streamlit':
             st.error(error_msg)
         # Optionally return partial content if desired, otherwise fail
         return None, None

    # --- 4. SEO Optimization ---
    print_cli("[cyan]Step 4: Optimizing SEO...[/cyan]")
    metadata = generate_seo_metadata(topic, markdown_content, research_data, gemini_client)
    if not metadata or not metadata.get('slug'):
         error_msg = "Error: Failed to generate SEO metadata or slug."
         print_cli(f"[bold red]{error_msg}[/bold red]")
         if run_mode == 'streamlit':
             st.error(error_msg)
         return markdown_content, None # Return content even if metadata fails? Or fail completely?

    print_cli(f"   - Generated Title: [bold green]'{metadata['title']}'[/bold green]")
    # Add other metadata prints for CLI if desired

    # --- 5. Export and Summarize ---
    print_cli("[cyan]Step 5: Exporting Results...[/cyan]")
    md_path, json_path = export_results(markdown_content, metadata, output_dir, metadata['slug'])

    # --- Final Summary (CLI Mode Only) ---
    if run_mode == 'cli':
        if md_path and json_path:
            summary_panel = Panel(
                f"✅ Blog post generation complete!\n\n"
                f"   - Topic: [bold cyan]{topic}[/bold cyan]\n"
                f"   - Output Directory: [bold magenta]{os.path.abspath(output_dir)}/{metadata['slug']}[/bold magenta]\n"
                f"   - Markdown File: [bold magenta]{md_path}[/bold magenta]\n"
                f"   - Metadata File: [bold magenta]{json_path}[/bold magenta]",
                title="Execution Summary",
                border_style="green"
            )
            console.print(summary_panel)
        else:
            console.print(Panel("❌ Blog post generation failed during export.", title="Execution Summary", border_style="red"))

    # --- Return results for Streamlit ---
    if md_path and json_path: # Check if export was successful before returning
         return markdown_content, metadata
    else:
         # Export failed, indicate this
         if run_mode == 'streamlit':
              st.error("Content generated and metadata created, but failed to save files.")
         return markdown_content, metadata # Still return generated data? Or None, None? Let's return data for display.


# Keep the CLI execution block
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous Python Blog Writing Agent - CLI Mode")
    parser.add_argument("--topic", type=str, required=True, help="The main topic for the blog post.")
    parser.add_argument("--tone", type=str, default="informative", help="Desired writing tone (e.g., informative, educational, creative, formal).")
    parser.add_argument("--output-dir", type=str, default="output", help="Directory to save the generated files.")

    args = parser.parse_args()

    # Run the main async function using asyncio.run for CLI
    try:
        # Pass run_mode='cli' explicitly
        asyncio.run(run_blog_agent(args.topic, args.tone, args.output_dir, run_mode='cli'))
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred in the main CLI execution: {e}[/bold red]")