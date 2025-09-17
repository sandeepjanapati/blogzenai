# api.py
import os
import asyncio
from flask import Flask, request, jsonify
from main import run_blog_agent
# Import all necessary database functions
from utils.database import save_generation_to_history, get_history, get_history_item_by_id

# Initialize the Flask application
app = Flask(__name__)

@app.route('/generate-blog', methods=['POST'])
def generate_blog_endpoint():
    """
    API endpoint to generate a blog post.
    Expects a JSON payload with 'topic' and an optional 'tone'.
    Saves the result to Firestore history upon success.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    topic = data.get('topic')
    tone = data.get('tone', 'informative') # Default tone if not provided

    if not topic:
        return jsonify({"error": "Missing required field: 'topic'"}), 400

    print(f"Received request to generate blog for topic: '{topic}'")

    try:
        # Use a temporary directory in the cloud environment's memory
        output_dir = "/tmp/output"
        markdown_content, metadata = asyncio.run(
            run_blog_agent(topic, tone, output_dir, run_mode='api')
        )

        if not markdown_content:
            # The agent should have logged the specific error.
            return jsonify({"error": "Failed to generate blog content. Check server logs for details."}), 500

        # --- Save to History ---
        # After successful generation, save the result to Firestore.
        history_id = save_generation_to_history(topic, tone, metadata, markdown_content)
        if not history_id:
            # Log a warning but still return the content to the user
            print("Warning: Blog was generated but failed to save to history.")

        # --- Prepare and Return Response ---
        response_data = {
            "status": "success",
            "history_id": history_id, # Include the new ID in the response
            "topic": topic,
            "metadata": metadata,
            "blog_content_markdown": markdown_content
        }
        return jsonify(response_data), 200

    except Exception as e:
        print(f"An unexpected error occurred in the API endpoint: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

@app.route('/history', methods=['GET'])
def get_history_list_endpoint():
    """
    API endpoint to retrieve a list of recent blog generations.
    Supports a 'limit' query parameter (e.g., /history?limit=10).
    """
    try:
        limit = request.args.get('limit', default=20, type=int)
        history_data = get_history(limit=limit)
        return jsonify(history_data), 200
    except Exception as e:
        print(f"An error occurred in the history list endpoint: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

# --- NEW ENDPOINT TO GET A SINGLE HISTORY ITEM ---
@app.route('/history/<string:history_id>', methods=['GET'])
def get_single_history_item_endpoint(history_id):
    """
    API endpoint to retrieve a specific blog generation by its Firestore document ID.
    """
    try:
        history_item = get_history_item_by_id(history_id)

        if history_item is None:
            return jsonify({"error": f"History item with ID '{history_id}' not found."}), 404

        return jsonify(history_item), 200
    except Exception as e:
        print(f"An error occurred retrieving history item {history_id}: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500
# --- END NEW ENDPOINT ---

# This block is for local development testing and is not used by Gunicorn in production.
if __name__ == "__main__":
    # Cloud Run provides the PORT env var, but we default to 8080 for local runs.
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, host='0.0.0.0', port=port)