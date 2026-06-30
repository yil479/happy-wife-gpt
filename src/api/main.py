"""
FastAPI app entry point.
Run with: uvicorn src.api.main:app --reload
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from src.api.routes import router

app = FastAPI(title="rag-to-riches", version="0.1.0")
app.include_router(router)
