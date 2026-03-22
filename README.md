# OfferQuest MCP Server (`mcp_j.py`)

A fast, secure, and LLM-friendly Model Context Protocol (MCP) server that scrapes job listings from major platforms (LinkedIn, Indeed, Google) and converts them into structured Markdown format.

[![offer-quest mcp MCP server](https://glama.ai/mcp/servers/theomatrix/Offer-Quest-MCP-/badges/card.svg)](https://glama.ai/mcp/servers/theomatrix/Offer-Quest-MCP-)

## Features

- **Blazing Fast API Scraping:** Uses `python-jobspy` to pull latest jobs instantly without heavy browser automation overhead.
- **Multi-Search Support:** Automatically handles parallel searching for multiple comma-separated job titles and locations in a single unified run.
- **LLM-Optimized Output:** Jobs are formatted into a clean, easy-to-read Markdown table specifically designed for AI agents and LLMs to parse and understand securely.
- **Strict Security:** 
  - All user inputs are sanitized to drop executable scripts and strange characters (`_sanitize_text`).
  - Limits max input length to prevent denial-of-service (DoS).
  - Internal errors/stack traces are masked from the user to prevent data leakage.
- **Granular Targeting:** 
  - Dynamic **Country** selection explicitly prevents the APIs from serving out-of-bounds global results.
  - "Max Hours Old" filter perfectly isolates ultra-fresh job postings.

## Installation

Ensure you have Python 3.10+ installed.

1. **Clone or navigate** to this project directory.
2. **Create a virtual environment** (Recommended):
   ```bash
   python3 -m venv myenv
   source myenv/bin/activate
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Start the server locally:
```bash
python3 mcp_j.py
```

- The server will boot up a local Gradio interface (usually `http://127.0.0.1:7860`).
- If you are plugging this into an MCP client, the endpoint is exposed at `/gradio_api/mcp/`.

## Deployment

Since the codebase is stateless and doesn't rely on background Playwright Chromium browsers, this script is highly viable for lightweight containerized deployments (Docker, Render, Heroku) or standard VPS setups.

**Security checklist completed for deployment:**
- [x] Catch-all error blocks to hide raw API tracebacks.
- [x] Built-in input sanitization using rigorous Regex.
- [x] Hard limits on payload size (`max_results=25` upper-bound).

*Note: For highest stability on cloud providers, ensure that the IP address you are querying from isn't strictly blacklisted by Indeed/LinkedIn.*