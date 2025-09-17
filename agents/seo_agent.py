# agents/seo_agent.py
import re
import textstat
from rich.console import Console

console = Console()

def generate_seo_metadata(topic: str, content: str, research_data: dict, gemini_client):
    """
    Generates SEO metadata (title, description, tags, slug, reading time, readability).
    """
    console.print("[cyan]Generating SEO metadata...[/cyan]")

    metadata = {
        'title': f"Generated Blog Post on {topic}", # Default title
        'meta_description': "Read this blog post to learn about " + topic, # Default description
        'tags': [],
        'slug': "",
        'reading_time_minutes': 0,
        'readability_score': None # Default to None
    }

    # --- Generate Title & Meta Description with Gemini ---
    if gemini_client:
        content_preview = content[:800] # Use first 800 chars for context
        seo_prompt = f"""
        Analyze the following blog post topic and content preview to generate SEO metadata:
        Topic: "{topic}"
        Content Preview: "{content_preview}..."

        Generate the following, keeping SEO best practices in mind:
        1.  **Title:** An engaging, SEO-friendly title (around 50-60 characters).
        2.  **Meta Description:** A compelling summary (max 160 characters) to encourage clicks.

        Provide the output clearly labeled:
        Title: [Generated Title]
        Meta Description: [Generated Meta Description]
        """
        try:
            response = gemini_client.generate_content(seo_prompt)
            text = response.text
            for line in text.splitlines():
                if line.startswith("Title:"):
                    metadata['title'] = line.split(":", 1)[1].strip()
                elif line.startswith("Meta Description:"):
                    metadata['meta_description'] = line.split(":", 1)[1].strip()[:160] # Ensure max length
        except Exception as e:
            console.print(f"[bold red]Error generating Title/Description with Gemini: {e}[/bold red]")
            # Keep defaults if Gemini fails

    # --- Generate Tags ---
    # Combine research keywords and potentially extract more (simple approach here)
    tags = set(research_data.get('keywords', []))
    # Add topic words as tags
    tags.update(re.findall(r'\b\w+\b', topic.lower()))
    # Basic filtering (remove short words, could be improved)
    metadata['tags'] = sorted([tag for tag in tags if len(tag) > 3])[:15] # Limit to 15 tags

    # --- Create Slug ---
    # Basic slugification: lowercase, replace spaces/special chars with hyphens
    slug = metadata['title'].lower()
    slug = re.sub(r'\s+', '-', slug) # Replace spaces with hyphens
    slug = re.sub(r'[^\w\-]+', '', slug) # Remove non-alphanumeric (except hyphen)
    slug = re.sub(r'\-\-+', '-', slug) # Replace multiple hyphens with single
    slug = slug.strip('-') # Remove leading/trailing hyphens
    metadata['slug'] = slug if slug else "blog-post" # Fallback slug

    # --- Estimate Reading Time ---
    word_count = len(re.findall(r'\w+', content))
    metadata['reading_time_minutes'] = round(word_count / 200) # Avg reading speed 200 WPM

    # --- Calculate Readability Score (Bonus) ---
    try:
        metadata['readability_score'] = textstat.flesch_kincaid_grade(content)
    except Exception as e:
        console.print(f"[yellow]Could not calculate readability score: {e}[/yellow]")
        metadata['readability_score'] = "N/A" # Indicate failure

    console.print("[green]SEO metadata generation complete.[/green]")
    return metadata