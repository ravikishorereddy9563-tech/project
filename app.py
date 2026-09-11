"""Vercel-compatible app entry for the AppleSupport support project.

The full interactive Streamlit dashboard remains in streamlit_app.py for local use.
This file provides the app object required by Vercel's Python runtime.
"""
from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="AppleSupport Support Agent")


@app.get("/")
async def root() -> dict:
    return {
        "status": "ok",
        "message": "AppleSupport support agent API is running.",
        "note": "Use streamlit_app.py locally for the full dashboard experience.",
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy"}


@app.get("/dashboard")
async def dashboard() -> dict:
    return {
        "title": "AppleSupport Support Agent",
        "status": "ready",
        "local_streamlit": "streamlit run streamlit_app.py"
    }


application = app
handler = app
