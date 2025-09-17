# agents/export_agent.py
import os
import json
from pathlib import Path
from rich.console import Console

console = Console()

def export_results(markdown_content: str, metadata: dict, output_dir: str, slug: str):
    """
    Exports the blog post (Markdown) and metadata (JSON) to files.
    """
    console.print(f"[cyan]Exporting results to directory: '{output_dir}'...[/cyan]")
    try:
        # Create the main output directory if it doesn't exist
        base_output_path = Path(output_dir)
        base_output_path.mkdir(parents=True, exist_ok=True)

        # Create a subdirectory based on the slug for organization
        post_output_path = base_output_path / slug
        post_output_path.mkdir(parents=True, exist_ok=True)


        # Define file paths
        md_filename = f"{slug}.md"
        json_filename = "metadata.json"
        md_filepath = post_output_path / md_filename
        json_filepath = post_output_path / json_filename

        # Save Markdown file
        with open(md_filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        console.print(f"  - Markdown file saved: [bold magenta]{md_filepath}[/bold magenta]")

        # Save Metadata JSON file
        # Convert Path objects to strings for JSON serialization if needed
        serializable_metadata = metadata.copy()
        # (No Path objects in current metadata, but good practice if they were added)

        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(serializable_metadata, f, indent=4)
        console.print(f"  - Metadata JSON file saved: [bold magenta]{json_filepath}[/bold magenta]")

        console.print("[green]Export complete.[/green]")
        return str(md_filepath), str(json_filepath) # Return paths as strings

    except IOError as e:
        console.print(f"[bold red]Error saving files: {e}[/bold red]")
        return None, None
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred during export: {e}[/bold red]")
        return None, None