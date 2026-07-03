import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.core.config import settings
from app.core.database import engine, Base
from app.api import auth, documents, workflows, dashboard

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sebi_copilot")

# Ensure required directories exist
os.makedirs("./uploads", exist_ok=True)
os.makedirs("./evidence", exist_ok=True)
os.makedirs("./reports", exist_ok=True)

# Auto-generate DB schema tables on startup (perfect for local SQLite testing)
try:
    logger.info("Initializing database schemas...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database schemas successfully created.")
except Exception as e:
    logger.error(f"Error creating database tables: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount files for retrieval
app.mount("/uploads", StaticFiles(directory="./uploads"), name="uploads")
app.mount("/evidence", StaticFiles(directory="./evidence"), name="evidence")
app.mount("/reports", StaticFiles(directory="./reports"), name="reports")

# Include Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(documents.router, prefix=settings.API_V1_STR)
app.include_router(workflows.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "SEBI CoPilot Compliance OS API",
        "version": settings.VERSION
    }
