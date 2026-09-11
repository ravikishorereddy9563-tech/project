"""Vercel-compatible app entry for the AppleSupport support project.

The full interactive dashboard is preserved in streamlit_app.py for local use.
This entry provides the same visual layout and branding on the deployed site.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="AppleSupport Support Agent")


HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AppleSupport AI Agent</title>
    <style>
      :root {
        --bg: #eef2f4;
        --panel: #f3f5f6;
        --sidebar: #e7ebee;
        --border: #d7dfe6;
        --text: #1f2d3d;
        --muted: #5a6979;
        --soft: #edf0f2;
        --primary: #e24d4d;
        --primary-dark: #d63f3f;
        --bar: #dfe8ee;
      }

      * { box-sizing: border-box; }
      html, body {
        margin: 0;
        height: 100%;
        background: var(--bg);
        color: var(--text);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }

      body {
        display: flex;
        min-height: 100vh;
      }

      .sidebar {
        width: 280px;
        background: var(--sidebar);
        border-right: 1px solid var(--border);
        padding: 18px 18px 14px;
      }

      .system {
        font-weight: 700;
        font-size: 18px;
        margin: 8px 0 18px;
      }

      .brand-label {
        font-size: 14px;
        color: var(--text);
        margin-bottom: 8px;
      }

      .brand-select {
        width: 100%;
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 12px 14px;
        background: #f6f8f9;
        font-size: 16px;
        color: var(--text);
      }

      .stats {
        margin-top: 26px;
      }

      .stat {
        margin-top: 18px;
      }

      .stat-label {
        font-size: 15px;
        color: var(--muted);
        display: block;
        margin-bottom: 4px;
      }

      .stat-value {
        font-size: 22px;
        font-weight: 600;
        line-height: 1.2;
      }

      .clear-btn {
        width: 100%;
        margin-top: 22px;
        background: transparent;
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 10px 12px;
        font-size: 15px;
        color: var(--text);
      }

      .note {
        margin-top: 22px;
        color: var(--muted);
        font-size: 13px;
        line-height: 1.6;
      }

      .main {
        flex: 1;
        padding: 28px 40px 40px;
      }

      .topbar {
        display: flex;
        justify-content: flex-end;
        align-items: center;
        margin-bottom: 18px;
      }

      .deploy-btn {
        border: 1px solid var(--border);
        background: rgba(255,255,255,0.15);
        border-radius: 8px;
        padding: 10px 16px;
        color: var(--text);
        font-size: 15px;
      }

      .title {
        text-align: center;
        font-size: clamp(38px, 4vw, 62px);
        font-weight: 800;
        letter-spacing: -0.05em;
        margin: 10px 0 8px;
      }

      .subtitle {
        text-align: center;
        font-size: 18px;
        color: #4b5864;
        margin-bottom: 26px;
      }

      .tabs {
        display: flex;
        justify-content: center;
        gap: 18px;
        border-bottom: 1px solid var(--border);
        margin: 0 auto 24px;
        max-width: 900px;
      }

      .tab {
        position: relative;
        padding: 12px 10px 14px;
        font-size: 16px;
        color: #475563;
        background: none;
        border: none;
        font-weight: 500;
      }

      .tab.active {
        color: var(--text);
      }

      .tab.active::after {
        content: "";
        position: absolute;
        left: 6%;
        right: 6%;
        bottom: -1px;
        height: 3px;
        background: var(--primary);
        border-radius: 2px;
      }

      .panel {
        max-width: 860px;
        margin: 0 auto;
        background: #f4f6f7;
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 18px 22px 16px;
      }

      .form-row {
        margin-bottom: 12px;
      }

      .select, .textarea {
        width: 100%;
        border: 1px solid var(--border);
        border-radius: 8px;
        background: #edf1f3;
        color: var(--text);
        font-size: 16px;
        padding: 14px 16px;
      }

      .textarea {
        min-height: 110px;
        resize: vertical;
      }

      .submit-btn {
        display: block;
        width: 100%;
        background: linear-gradient(#ef4e4e, #e33c3c);
        border: none;
        color: white;
        border-radius: 8px;
        font-weight: 700;
        font-size: 18px;
        padding: 16px 16px;
        cursor: pointer;
      }

      .info-box {
        width: 100%;
        margin-top: 18px;
        background: #dfeaf5;
        border: 1px solid #bfd4ea;
        color: #365678;
        border-radius: 8px;
        padding: 18px 20px;
        text-align: center;
        font-size: 16px;
      }

      @media (max-width: 900px) {
        body { display: block; }
        .sidebar { width: 100%; border-right: none; border-bottom: 1px solid var(--border); }
        .main { padding: 20px 18px 30px; }
        .tabs { flex-wrap: wrap; }
      }
    </style>
  </head>
  <body>
    <aside class="sidebar">
      <div class="system">System</div>
      <div class="brand-label">Brand</div>
      <select class="brand-select" aria-label="Brand selector">
        <option selected>AppleSupport</option>
      </select>

      <div class="stats">
        <div class="stat">
          <span class="stat-label">Historical replies</span>
          <span class="stat-value">15</span>
        </div>
        <div class="stat">
          <span class="stat-label">Supported intents</span>
          <span class="stat-value">10</span>
        </div>
        <div class="stat">
          <span class="stat-label">Session cases</span>
          <span class="stat-value">3</span>
        </div>
      </div>

      <button class="clear-btn">Clear session history</button>

      <div class="note">
        Offline demo using the committed fixture.<br />
        No customer text leaves this app.
      </div>
    </aside>

    <main class="main">
      <div class="topbar">
        <button class="deploy-btn">Deploy</button>
      </div>

      <div class="title">AppleSupport AI Agent</div>
      <div class="subtitle">Classify, ground, and route customer-support messages using historical resolutions.</div>

      <div class="tabs" aria-label="Main navigation">
        <button class="tab active">Agent</button>
        <button class="tab">Overview</button>
        <button class="tab">Case history</button>
        <button class="tab">Evaluation</button>
        <button class="tab">Failure analysis</button>
      </div>

      <section class="panel">
        <div class="form-row">
          <select class="select" aria-label="Message template">
            <option selected>Try an example</option>
          </select>
        </div>
        <div class="form-row">
          <div class="textarea" aria-label="Customer message">Customer message</div>
        </div>
        <div class="form-row">
          <textarea class="textarea" aria-label="Message content">My order was supposed to arrive yesterday but I still have not received it.</textarea>
        </div>
        <button class="submit-btn">Analyze message</button>
        <div class="info-box">Enter a message and select Analyze message to inspect the full decision trace.</div>
      </section>
    </main>
  </body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def root() -> str:
    return HTML_PAGE


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy"}


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard() -> str:
    return HTML_PAGE


application = app
handler = app
