# agents/understanding_agent.py
from rich.console import Console

console = Console()

def analyze_topic(topic: str, tone: str, gemini_client):
    """
    Uses Gemini to break down the topic into subtopics and confirm tone.
    """
    console.print(f"[cyan]Analyzing topic: '{topic}' with tone: '{tone}'...[/cyan]")
    if not gemini_client:
        console.print("[bold red]Gemini client not available. Skipping topic analysis.[/bold red]")
        # Provide default structure if Gemini fails
        return {
            'subtopics': ["Introduction", f"Key Aspects of {topic}", "Challenges and Solutions", "Future Trends", "Conclusion"],
            'tone': tone or "informative"
        }

    prompt = f"""
    Analyze the topic: "{topic}".
    Your goal is to act as a blog post planner.

    1.  Break this topic down into 5-7 logical subtopics that would work well as H2 headings in a blog post. List them clearly.
    2.  Based on the topic and the suggested tone '{tone}', confirm the most appropriate writing tone (e.g., informative, educational, technical, creative, formal, beginner-friendly). If the suggested tone seems suitable, use it. Otherwise, suggest a better one.

    Provide the output as:
    Subtopics:
    - Subtopic 1
    - Subtopic 2
    ...
    Tone: Confirmed Tone
    """
    try:
        response = gemini_client.generate_content(prompt)
        text = response.text

        # Basic parsing (can be improved with regex or more robust parsing)
        subtopics = []
        confirmed_tone = tone # Default to original tone if parsing fails
        in_subtopics_section = False
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("Subtopics:"):
                in_subtopics_section = True
                continue
            if in_subtopics_section:
                if line.startswith("- "):
                    subtopics.append(line[2:].strip())
                elif not line.startswith("- ") and subtopics: # Stop if we hit the next section
                     in_subtopics_section = False
            if line.startswith("Tone:"):
                confirmed_tone = line.split(":", 1)[1].strip()
                in_subtopics_section = False # Ensure we stop looking for subtopics

        if not subtopics: # Fallback if parsing failed
             raise ValueError("Could not parse subtopics from Gemini response.")

        console.print(f"[green]Topic analysis complete. Found {len(subtopics)} subtopics.[/green]")
        return {
            'subtopics': subtopics,
            'tone': confirmed_tone
        }
    except Exception as e:
        console.print(f"[bold red]Error during topic analysis with Gemini: {e}[/bold red]")
        # Fallback structure
        return {
            'subtopics': ["Introduction", f"Understanding {topic}", "Key Considerations", "Examples", "Conclusion"],
            'tone': tone or "informative"
        }