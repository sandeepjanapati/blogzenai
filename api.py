# api.py
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from main import run_blog_agent
from utils.database import get_history, get_history_item_by_id

# Initialize the FastAPI application
app = FastAPI(
    title="BlogZenAI API",
    description="An API to generate blog posts using AI agents.",
    version="1.0.0"
)

# --- CORS Configuration ---
# This is CRITICAL for allowing your Firebase website to call the API
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://127.0.0.1:5500",  # <-- ADD THIS LINE FOR VS CODE GO LIVE
    "http://localhost:5500",
    # Add your Firebase hosting URL once you deploy it
    # "https://your-project-id.web.app",
    # "https://your-project-id.firebaseapp.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models for Request/Response validation ---
class BlogRequest(BaseModel):
    topic: str
    tone: str = "informative"

# --- API Endpoints ---
@app.post("/generate-blog")
async def generate_blog_endpoint(request: BlogRequest):
    """
    API endpoint to generate a blog post.
    Saves the result to Firestore history upon success.
    """
    print(f"Received request to generate blog for topic: '{request.topic}'")
    try:
        # Cloud Run provides an ephemeral filesystem at /tmp
        output_dir = "/tmp/output"
        markdown_content, metadata = await run_blog_agent(
            request.topic, request.tone, output_dir, run_mode='api'
        )

        if not markdown_content or not metadata:
            raise HTTPException(status_code=500, detail="Failed to generate blog content. Check server logs.")

        # Saving to history is now handled inside run_blog_agent or should be called here.
        # Let's assume it should be here.
        from utils.database import save_generation_to_history
        history_id = save_generation_to_history(request.topic, request.tone, metadata, markdown_content)
        if not history_id:
            print("Warning: Blog was generated but failed to save to history.")

        response_data = {
            "status": "success",
            "history_id": history_id,
            "topic": request.topic,
            "metadata": metadata,
            "blog_content_markdown": markdown_content
        }
        return response_data
    except Exception as e:
        print(f"An unexpected error occurred in the API endpoint: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@app.get("/history")
async def get_history_list_endpoint(limit: int = Query(20, gt=0, le=100)):
    """
    API endpoint to retrieve a list of recent blog generations.
    """
    try:
        history_data = get_history(limit=limit)
        return history_data
    except Exception as e:
        print(f"An error occurred in the history list endpoint: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@app.get("/history/{history_id}")
async def get_single_history_item_endpoint(history_id: str):
    """
    API endpoint to retrieve a specific blog generation by its Firestore document ID.
    """
    try:
        history_item = get_history_item_by_id(history_id)
        if history_item is None:
            raise HTTPException(status_code=404, detail=f"History item with ID '{history_id}' not found.")
        return history_item
    except Exception as e:
        print(f"An error occurred retrieving history item {history_id}: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

# To run locally for testing: uvicorn api:app --reload