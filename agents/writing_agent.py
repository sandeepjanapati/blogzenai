# agents/writing_agent.py
import logging 
import random
import time

def generate_blog_post(topic: str, subtopics: list, tone: str, research_data: dict, gemini_client, progress_callback=None):
    """
    Generates the full blog post content using Gemini, with full research context.
    """
    logging.info("Starting content generation...")
    if not gemini_client:
        logging.error("Gemini client not available. Cannot generate content.")
        return "# Blog Post Generation Failed\n\nCould not connect to the generative AI service."

    def emit(message, progress):
        if progress_callback:
            progress_callback("writing", message, "✍️", "active", progress)

    full_content = []

    # --- Introduction ---
    logging.info("Generating introduction...")
    emit("Writing introduction...", 28)
    intro_prompt = f"""
    Write an engaging introduction (around 100-150 words) for a blog post about "{topic}".
    The tone should be {tone}.
    Briefly introduce the main concepts and state what the reader will learn.
    Do NOT include a title like "Introduction:". Just write the paragraph.
    """
    try:
        intro_response = gemini_client.generate_content(intro_prompt)
        full_content.append(intro_response.text.strip())
        full_content.append("\n")
    except Exception as e:
        logging.error(f"Error generating introduction: {e}", exc_info=True)
        full_content.append(f"*[Error generating introduction: {e}]*")

    # --- Body Sections (Subtopics) ---
    logging.info(f"Generating content for {len(subtopics)} subtopics...")
    for i, subtopic in enumerate(subtopics):
        if i > 0:
            time.sleep(1)

        progress_pct = 30 + int((i / len(subtopics)) * 50)  # 30-80%
        emit(f"Writing: {subtopic}... ({i+1}/{len(subtopics)})", progress_pct)
        logging.info(f"  - Generating section for: '{subtopic}' ({i+1}/{len(subtopics)})")
        
        # THIS IS THE CRITICAL PART THAT GIVES THE BLOG "SOUL"
        context = ""
        if research_data.get('news'):
            news_titles = [n.get('title', 'related news') for n in research_data['news']]
            context += f"Consider mentioning recent developments like: {', '.join(news_titles[:2])}. "
        if research_data.get('keywords'):
             context += f"Relevant keywords to consider: {', '.join(random.sample(research_data['keywords'], min(3, len(research_data['keywords']))))}. "
        if research_data.get('quotes') and i % 2 == 0:
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
            full_content.append(f"## {subtopic}\n")
            full_content.append(section_response.text.strip())
            full_content.append("\n")
        except Exception as e:
            logging.error(f"Error generating section '{subtopic}': {e}", exc_info=True)
            full_content.append(f"## {subtopic}\n\n*[Error generating content for this section: {e}]*\n")

    # --- Conclusion ---
    logging.info("Generating conclusion...")
    time.sleep(1)
    emit("Writing conclusion...", 80)
    conclusion_prompt = f"""
    Write a strong concluding paragraph (around 100 words) for the blog post about "{topic}".
    The tone should be {tone}.
    Summarize the key takeaways from the post.
    Include a call-to-action (e.g., encourage comments, suggest further reading, ask a question).
    Do NOT include a title like "Conclusion:". Just write the paragraph.
    """
    try:
        conclusion_response = gemini_client.generate_content(conclusion_prompt)
        full_content.append("## Conclusion\n")
        full_content.append(conclusion_response.text.strip())
    except Exception as e:
        logging.error(f"Error generating conclusion: {e}", exc_info=True)
        full_content.append("\n## Conclusion\n\n*[Error generating conclusion: {e}]*")

    logging.info("Content generation complete.")
    return "\n".join(full_content)