"""FastAPI router module for health endpoints."""
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/health", tags=["health"])
