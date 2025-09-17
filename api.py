# api.py

import os
import asyncio
from flask import Flask, request, jsonify
from main import run_blog_agent

app = Flask(__name__)

@app.route('/generate-blog', methods=['POST'])
def generate_blog_endpoint():
    data = request.get_json()
    if not data or 'topic' not in data:
        return jsonify({"error": "Missing required field: 'topic'"}), 400

    topic = data.get('topic')
    tone = data.get('tone', 'informative')
    print(f"API: Received request for topic: '{topic}'")

    try:
        output_dir = "/tmp"
        markdown_content, metadata = asyncio.run(
            run_blog_agent(topic, tone, output_dir, run_mode='api')
        )
        if not markdown_content:
            return jsonify({"error": "Failed to generate blog content."}), 500

        response_data = {
            "status": "success",
            "metadata": metadata,
            "blog_content_markdown": markdown_content
        }
        return jsonify(response_data), 200
    except Exception as e:
        print(f"API: An unexpected error occurred: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, host='0.0.0.0', port=port)