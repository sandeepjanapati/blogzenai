# agents/export_agent.py
import logging

def export_results(markdown_content: str, metadata: dict, output_dir: str, slug: str):
    """
    Finalizes the blog generation pipeline.
    In cloud mode, content is persisted to Firestore by the API layer,
    so this step only logs completion.
    """
    logging.info(f"[Export Agent] Finalized blog post: '{slug}' ({len(markdown_content)} chars)")