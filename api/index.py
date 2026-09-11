from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="AppleSupport Support Agent")


@app.get("/")
async def root() -> dict:
    return {
        "status": "ok",
        "message": "AppleSupport support agent API is running.",
        "note": "This Vercel entry is a compatibility wrapper. Use local Streamlit for the actual dashboard.",
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy"}


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard() -> str:
    return """
    <html>
      <head>
        <title>AppleSupport Support Agent</title>
        <style>
          body { font-family: Arial, sans-serif; padding: 2rem; }
          code { background: #f4f4f4; padding: 0.2rem 0.4rem; }
        </style>
      </head>
      <body>
        <h1>AppleSupport Support Agent</h1>
        <p>This is the Vercel-compatible wrapper for the project.</p>
        <p>For the full interactive dashboard, run <code>streamlit run app.py</code> locally.</p>
      </body>
    </html>
    """
