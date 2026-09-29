---
title: OfferQuest MCP
emoji: 🎯
colorFrom: indigo
colorTo: purple
sdk: gradio
app_file: app.py
pinned: false
---

# OfferQuest MCP Server

[![offer-quest mcp MCP connector – tool definition quality and endpoint health on Glama](https://glama.ai/mcp/connectors/space.hf.dexter3b-offerquest-mcp/offer-quest-mcp/badges/score.svg)](https://glama.ai/mcp/connectors/space.hf.dexter3b-offerquest-mcp/offer-quest-mcp)

[![Available on Glama](https://img.shields.io/badge/Available%20on-Glama-black.svg)](https://glama.ai/mcp/connectors/space.hf.dexter3b-offerquest-mcp/offer-quest-mcp)

[![offer-quest mcp MCP server](https://glama.ai/mcp/servers/theomatrix/Offer-Quest-MCP-/badges/card.svg)](https://glama.ai/mcp/servers/theomatrix/Offer-Quest-MCP-)

A fast, secure, LLM-friendly [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server for job and internship hunting. It searches live postings on **Indeed** and **LinkedIn**, ranks them against your resume, and tells you which keywords your resume is missing for a specific job.

**Live endpoint (Streamable HTTP):** `https://dexter3b-offerquest-mcp.hf.space/gradio_api/mcp/`

## Tools

| Tool | What it does |
|------|--------------|
| `fetch_and_format_jobs` | Live job/internship search across Indeed + LinkedIn. Returns a deduplicated Markdown report, newest first. |
| `rank_jobs` | Searches fresh jobs for your target roles and **scores each one out of 100** against your resume. |
| `ats_keywords` | ATS keyword-gap report for **one** job vs. your resume: missing must-haves, nice-to-haves, and what you already cover. |

### `fetch_and_format_jobs`

| Argument | Description |
|----------|-------------|
| `job_titles` | Up to 3 comma-separated roles, e.g. `AI Engineer Intern, Python Developer Intern` |
| `locations` | Up to 3 comma-separated cities, e.g. `Delhi, Remote` |
| `country` | `India`, `USA`, `UK`, `Canada`, `Australia` or `Germany` (default `India`) |
| `max_results` | Jobs per site per search, 1–15 (default 5) |
| `hours_old` | Only postings from the last N hours, 1–168 (default 48) |
| `fetch_linkedin_descriptions` | Fetch full LinkedIn descriptions (slower, higher rate-limit risk) |

Each result includes title, company, location, job type, salary (when disclosed), posted date, direct links, a description snippet and a **Job ID** you can pass to `ats_keywords`.

### `rank_jobs`

| Argument | Description |
|----------|-------------|
| `resume_text` | Plain-text resume (20,000 characters max) |
| `target_roles` | Up to 3 comma-separated roles you are targeting |
| `locations` | Up to 3 comma-separated cities |
| `country` | Same list as above |
| `top_n` | How many top matches to return, 1–15 (default 8) |
| `hours_old` | Max posting age in hours, 1–168 (default 72) |
| `fetch_linkedin_descriptions` | Better scoring, but slower |

For every match you get: a score out of 100, matched skills, missing skills, red flags (senior title, years of experience required, no description available), links, and a Job ID. The report also lists the skills most often missing from your resume across the top results.

**How the score works** (pure Python, no ML dependencies):

| Component | Weight |
|-----------|--------|
| Skill overlap with the posting (76-skill curated taxonomy with aliases) | 45 |
| Text similarity between resume and posting (TF-IDF cosine) | 25 |
| Title match against your target roles | 20 |
| Freshness of the posting | 10 |
| Seniority penalty (senior/lead titles, "N+ years" requirements) | up to −40 |

Postings without a usable description are scored mostly on title and flagged as such.

### `ats_keywords`

| Argument | Description |
|----------|-------------|
| `resume_text` | Plain-text resume (20,000 characters max) |
| `job_id_or_description` | Either a Job ID from earlier results (valid ~1 hour) or the full pasted job description |

Returns keyword coverage %, **missing must-haves**, **missing nice-to-haves**, skills already covered, recurring terms in the posting that are absent from your resume, and placement tips.

### Typical workflow

1. `rank_jobs` with your resume and target roles → get the best matches with Job IDs.
2. `ats_keywords` with your resume and a Job ID → see exactly what to add before applying.
3. `fetch_and_format_jobs` for a broader, unranked look at what's out there.

## Security

- **Scraped text is untrusted.** Postings are stripped of HTML, URLs and invisible characters, scanned for prompt-injection phrases (which are removed and flagged), and fenced inside `<untrusted_posting>` tags. Tool output reminds the LLM to treat it as data only.
- **No SSRF.** No tool fetches user-supplied URLs, and only links on `linkedin.com` / `indeed.com` are ever returned.
- **Resumes stay in memory.** They are never logged, cached or echoed back.
- **Bounded inputs.** All inputs are length-capped, and regexes are bounded to avoid ReDoS.
- **Abuse controls.** Per-client and global rate limits, limited concurrent searches, a scrape deadline, and a TTL cache.
- **Masked errors.** Internal errors and stack traces are never returned to the caller.

### Limits

| Limit | Value |
|-------|-------|
| Titles / locations per call | 3 / 3 (max 6 combinations) |
| Search rate limit | 10 per 10 min per client, 60 per 10 min globally |
| `rank_jobs` / `ats_keywords` rate limit | 40 calls per 10 min per client |
| Concurrent searches | 3 |
| Scrape deadline | 55 seconds |
| Search cache | 15 minutes |
| Job ID validity | ~1 hour |

## Installation

Requires Python 3.10+.

```bash
git clone <this-repo>
cd <this-repo>
python3 -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt
```

Core dependencies: `gradio[mcp]`, `python-jobspy`, `pandas`.

## Usage

```bash
python3 app.py
```

- The Gradio UI opens at `http://127.0.0.1:7860` with one tab per tool: **Search**, **Rank**, **ATS Keywords**.
- MCP clients connect to `http://127.0.0.1:7860/gradio_api/mcp/`.

### Connecting an MCP client

For clients that support remote Streamable HTTP servers, use the hosted endpoint:

```
https://dexter3b-offerquest-mcp.hf.space/gradio_api/mcp/
```

For clients that only support stdio, bridge it with [`mcp-remote`](https://www.npmjs.com/package/mcp-remote):

```json
{
  "mcpServers": {
    "offerquest": {
      "command": "npx",
      "args": ["mcp-remote", "https://dexter3b-offerquest-mcp.hf.space/gradio_api/mcp/"]
    }
  }
}
```

## Deployment

The server is stateless and needs no headless browser, so it runs well on Hugging Face Spaces, Docker, Render or a plain VPS.

Notes for Hugging Face Spaces (Gradio SDK):

- Start the app with `demo.launch(...)`. Don't run your own `uvicorn` on port 7860, because the Space already owns it.
- Launch with `ssr_mode=False`. With SSR on, Gradio's Node proxy answers unknown paths with the UI, so custom routes such as `/.well-known/glama.json` never reach Python.
- Custom routes are registered through `launch(app_kwargs={"routes": [...]})` so they are matched before Gradio's own routes.

*Job sites may rate-limit or block cloud IP addresses. When that happens, the tool returns partial results with a warning instead of failing.*

## Disclaimer

Job data comes from third-party sites via [JobSpy](https://github.com/speedyapply/JobSpy). Availability and accuracy depend on those sites. Scores and keyword reports are guidance, not guarantees. Only add keywords for skills you genuinely have.
