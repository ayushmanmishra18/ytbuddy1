from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routes import analyze, ask
import os
from dotenv import load_dotenv
import logging
from pathlib import Path

load_dotenv()

# Create logs directory if not exists
Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/server.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://ytbuddy1-1.onrender.com"  # Add your production frontend URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Verify environment variables
assert os.getenv('GEMINI_API_KEY'), "GEMINI_API_KEY missing"
# Add this to main.py before app startup
print("=== STARTING SERVER ===")
print(f"Gemini Key Loaded: {bool(os.getenv('GEMINI_API_KEY'))}")
# Include routes
app.include_router(analyze.router, prefix="/api", tags=["analyze"])
app.include_router(ask.router, prefix="/api", tags=["ask"])

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")
    logger.debug(f"Headers: {dict(request.headers)}")
    
    try:
        if request.method == "POST":
            body = await request.body()
            logger.debug(f"Request body: {body.decode()}")
    except Exception as e:
        logger.warning(f"Could not log request body: {str(e)}")
    
    response = await call_next(request)
    return response

@app.get("/health")
async def health_check():
    return {"status": "ok"}