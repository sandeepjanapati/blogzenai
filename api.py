# api.py
import os, json, logging, firebase_admin
from firebase_admin import credentials, auth
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from main import run_blog_agent
from utils.database import get_history, get_history_item_by_id, save_generation_to_history, save_user_generation_to_history
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Application startup: Initializing Firebase Admin SDK...")
    try:
        firebase_creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
        if firebase_creds_json:
            cred_dict = json.loads(firebase_creds_json)
            cred = credentials.Certificate(cred_dict)
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)
                logging.info("Firebase Admin SDK initialized successfully within lifespan event.")
        else: 
            logging.error("FATAL (lifespan): FIREBASE_CREDENTIALS_JSON env var not found.")
    except Exception as e:
        logging.error(f"FATAL (lifespan): Firebase Admin SDK init failed: {e}", exc_info=True)
    
    yield
    logging.info("Application shutdown.")

app = FastAPI(title="BlogZenAI API", version="1.0.0", lifespan=lifespan)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    if not firebase_admin._apps: 
        raise HTTPException(status_code=500, detail="Auth service not configured on the server.")
    try: 
        return auth.verify_id_token(token, check_revoked=True)
    except Exception as e:
        logging.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid auth credentials")

origins = ["https://bolgzenai.web.app", "https://bolgzenai.firebaseapp.com", "http://localhost:5500", "http://127.0.0.1:5500"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
class BlogRequest(BaseModel): topic: str; tone: str = "informative"
@app.post("/generate-blog-free")
async def generate_blog_free_endpoint(request: BlogRequest):
    logging.info(f"FREE generation request for topic: {request.topic}")
    try:
        markdown_content, metadata = await run_blog_agent(request.topic, request.tone, "/tmp/output", run_mode='api')
        if not markdown_content or not metadata: raise HTTPException(status_code=500, detail="Failed to generate content.")
        history_id = save_generation_to_history(request.topic, request.tone, metadata, markdown_content)
        return {"status": "success", "history_id": history_id, "topic": request.topic, "metadata": metadata, "blog_content_markdown": markdown_content}
    except Exception as e:
        logging.error(f"FREE API endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")
@app.post("/generate-blog")
async def generate_blog_endpoint(request: BlogRequest, user: dict = Depends(get_current_user)):
    logging.info(f"Authenticated request from user: {user.get('uid')}")
    try:
        markdown_content, metadata = await run_blog_agent(request.topic, request.tone, "/tmp/output", run_mode='api')
        if not markdown_content or not metadata: raise HTTPException(status_code=500, detail="Failed to generate content.")
        user_info = {'uid': user.get('uid'), 'name': user.get('name'), 'email': user.get('email')}
        history_id = save_user_generation_to_history(user_info, request.topic, request.tone, metadata, markdown_content)
        return {"status": "success", "history_id": history_id, "topic": request.topic, "metadata": metadata, "blog_content_markdown": markdown_content}
    except Exception as e:
        logging.error(f"API endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")
@app.get("/history", dependencies=[Depends(get_current_user)])
async def get_history_list_endpoint(user: dict = Depends(get_current_user), limit: int = Query(20, gt=0, le=100)):
    try: return get_history(user_id=user['uid'], limit=limit)
    except Exception as e: raise HTTPException(status_code=500, detail="Internal server error.")
@app.get("/history/{history_id}", dependencies=[Depends(get_current_user)])
async def get_single_history_item_endpoint(history_id: str, user: dict = Depends(get_current_user)):
    try:
        history_item = get_history_item_by_id(history_id)
        if history_item is None or history_item.get('userId') != user['uid']:
            raise HTTPException(status_code=404, detail="History item not found or you do not have permission.")
        return history_item
    except Exception as e: raise HTTPException(status_code=500, detail="Internal server error.")