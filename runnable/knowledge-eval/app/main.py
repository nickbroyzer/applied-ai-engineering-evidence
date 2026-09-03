"""Minimal FastAPI app exposing the knowledge router.

Production's `main.py` mounts sixteen routers, Sentry, CORS and rate limiting.
This package mounts one router, so the endpoint tests exercise the real route
code — tier selection, the 403 on a widened index, the query log — without
dragging in the rest of the platform.
"""
from fastapi import FastAPI

from app.routers import knowledge

app = FastAPI(title="knowledge-eval")
app.include_router(knowledge.router)
