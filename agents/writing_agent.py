# agents/writing_agent.py
from rich.console import Console
import random

console = Console()

def generate_blog_post(topic: str, subtopics: list, tone: str, research_data: dict, gemini_client):
    """
    Generates the full blog post content using Gemini.
    """
    console.print("[cyan]Starting content generation...[/cyan]")
    if not gemini_client:
        console.print("[bold red]Gemini client not available. Cannot generate content.[/bold red]")
        return "# Blog Post Generation Failed\n\nCould not connect to the generative AI service."

    full_content = []

    # --- Introduction ---
    console.print("[cyan]Generating introduction...[/cyan]")
    intro_prompt = f"""
    Write an engaging introduction (around 100-150 words) for a blog post about "{topic}".
    The tone should be {tone}.
    Briefly introduce the main concepts and state what the reader will learn.
    Do NOT include a title like "Introduction:". Just write the paragraph.
    """
    try:
        intro_response = gemini_client.generate_content(intro_prompt)
        full_content.append(intro_response.text.strip())
        full_content.append("\n") # Add space after intro
    except Exception as e:
        console.print(f"[bold red]Error generating introduction: {e}[/bold red]")
        full_content.append(f"*[Error generating introduction: {e}]*")


    # --- Body Sections (Subtopics) ---
    console.print(f"[cyan]Generating content for {len(subtopics)} subtopics...[/cyan]")
    for i, subtopic in enumerate(subtopics):
        console.print(f"  - Generating section for: '{subtopic}' ({i+1}/{len(subtopics)})")
        # Prepare context from research (optional, keep it concise)
        context = ""
        if research_data.get('news'):
            news_titles = [n.get('title', 'related news') for n in research_data['news']]
            context += f"Consider mentioning recent developments like: {', '.join(news_titles[:2])}. " # Max 2 news titles
        if research_data.get('keywords'):
             context += f"Relevant keywords to consider: {', '.join(random.sample(research_data['keywords'], min(3, len(research_data['keywords']))))}. " # Max 3 random keywords
        if research_data.get('quotes') and i % 2 == 0: # Add a quote to every other section maybe
             if research_data['quotes']:
                 context += f"You could potentially include a quote like: {random.choice(research_data['quotes'])}. "

        section_prompt = f"""
        Write a section for a blog post on the topic "{topic}".
        This section's heading (H2) is: "{subtopic}".
        The overall blog post tone is {tone}.

        Write around 200-300 words for this section.
        Focus on explaining "{subtopic}" clearly and engagingly.
        Use Markdown formatting for structure (like bullet points *if appropriate*).
        {context}

        Do NOT include the H2 heading itself in your response. Just write the content for this section.
        Ensure the content flows logically from a potential previous section and leads into the next.
        """
        try:
            section_response = gemini_client.generate_content(section_prompt)
            full_content.append(f"## {subtopic}\n") # Add H2 heading
            full_content.append(section_response.text.strip())
            full_content.append("\n") # Add space between sections
        except Exception as e:
            console.print(f"[bold red]Error generating section '{subtopic}': {e}[/bold red]")
            full_content.append(f"## {subtopic}\n\n*[Error generating content for this section: {e}]*\n")


    # --- Conclusion ---
    console.print("[cyan]Generating conclusion...[/cyan]")
    conclusion_prompt = f"""
    Write a strong concluding paragraph (around 100 words) for the blog post about "{topic}".
    The tone should be {tone}.
    Summarize the key takeaways from the post.
    Include a call-to-action (e.g., encourage comments, suggest further reading, ask a question).
    Do NOT include a title like "Conclusion:". Just write the paragraph.
    """
    try:
        conclusion_response = gemini_client.generate_content(conclusion_prompt)
        full_content.append("## Conclusion\n") # Add H2 heading for conclusion
        full_content.append(conclusion_response.text.strip())
    except Exception as e:
        console.print(f"[bold red]Error generating conclusion: {e}[/bold red]")
        full_content.append("\n## Conclusion\n\n*[Error generating conclusion: {e}]*")

    console.print("[green]Content generation complete.[/green]")
    return "\n".join(full_content)