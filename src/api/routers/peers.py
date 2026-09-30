"""FastAPI router module for peers endpoints."""
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/peers", tags=["peers"])
