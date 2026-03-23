import gradio as gr
from jobspy import scrape_jobs
import pandas as pd
import sys
import re
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Helpers ──────────────────────────────────────────────────────────────────

MAX_TITLE_LEN = 100
MAX_LOCATION_LEN = 100
DESC_SNIPPET_LEN = 500        # Characters of description to show

_UNSAFE_PATTERN = re.compile(r"[^\w\s\-.,/()&+#]", re.UNICODE)


def _sanitize_text(text: str, max_len: int) -> str:
    """Strip, truncate, and remove suspicious characters from user input."""
    text = str(text).strip()
    text = _UNSAFE_PATTERN.sub("", text)
    return text[:max_len]


def _parse_multi_input(text: str) -> list[str]:
    """Split comma-separated input into a list of stripped, non-empty values."""
    s = str(text).strip()
    return [v.strip() for v in s.split(",") if v.strip()]


def _clean_value(value, fallback: str = "N/A") -> str:
    """Return a clean string for any DataFrame value, replacing NaN/None."""
    if value is None or pd.isna(value):
        return fallback
    s = str(value).strip()
    return s if s else fallback


# ── Core Function ────────────────────────────────────────────────────────────

def fetch_and_format_jobs(
    job_titles: str, 
    locations: str, 
    country: str = "India", 
    max_results: int = 5, 
    hours_old: int = 48
) -> str:
    """
    Search for the latest jobs and internships and return them as a structured,
    LLM-ready Markdown report. Supports multiple titles and locations.

    Args:
        job_titles: The roles you are looking for (e.g., 'Python Developer Intern').
        locations: Cities or locations (e.g., 'Delhi, Remote').
        country: The target country for the search.
        max_results: Number of jobs to fetch per source per combo (1-10).
        hours_old: Only show jobs posted within this many hours (default 48, max 168).
    """
    # ── 1. Input parsing & validation ────────────────────────────────────
    titles = _parse_multi_input(_sanitize_text(job_titles, MAX_TITLE_LEN))
    locs = _parse_multi_input(_sanitize_text(locations, MAX_LOCATION_LEN))

    if not titles:
        return "**Invalid input:** Please provide at least one job title."
    if not locs:
        return "**Invalid input:** Please provide at least one location (or 'Remote')."

    # Clamp to Gradio UI ranges as a safety net
    max_results = int(max(1, min(max_results, 25)))
    hours_old = int(max(1, min(hours_old, 168)))

    combos = [(t, l) for t in titles for l in locs]
    print(f"[Engine] {len(combos)} search combo(s): {combos} in {country}")

    all_jobs = []

    try:
        # ── 2. Parallel Scraping Engine ──────────────────────────────────
        with ThreadPoolExecutor(max_workers=4) as pool:
            future_map = {}
            for (t, l) in combos:
                search_loc = f"{l}, {country}" if not l.lower().endswith(country.lower()) else l
                future_map[pool.submit(
                    scrape_jobs,
                    site_name=["indeed", "linkedin", "google"],
                    search_term=t,
                    location=search_loc,
                    results_wanted=max_results,
                    hours_old=hours_old,
                    country_indeed=country.lower(),
                )] = (t, l)

            for future in as_completed(future_map):
                combo_tag = future_map[future]
                try:
                    jobs_df = future.result()
                    if not jobs_df.empty:
                        # Enforce the results cap per combo (scrapers can over-return)
                        jobs_df = jobs_df.head(max_results)
                        all_jobs.extend(jobs_df.to_dict(orient="records"))
                except Exception as exc:
                    print(f"[ERROR] Combo {combo_tag} failed: {exc}", file=sys.stderr)

        if not all_jobs:
            return (
                f"No jobs found for the given search(es) posted in the last {hours_old} hours.\n\n"
                "*Try broadening your search terms, locations, or increasing the hours window.*"
            )

        # ── 3. Combine and Deduplicate ───────────────────────────────────
        seen = set()
        unique_jobs = []
        for job in all_jobs:
            source = _clean_value(job.get("site"), "Unknown Source")
            title = _clean_value(job.get("title"), "Unknown Title")
            company = _clean_value(job.get("company"), "Unknown Company")
            
            key = (title.lower(), company.lower(), source.lower())
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)

        jobs_list = sorted(unique_jobs, key=lambda x: _clean_value(x.get("title")))

        # ── 4. Build structured Markdown report ─────────────────────────
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        md = []
        md.append(f"## Job Search Results\n")
        md.append(f"| Field | Value |")
        md.append(f"|-------|-------|")
        md.append(f"| **Queries** | {', '.join(titles)} |")
        md.append(f"| **Locations** | {', '.join(locs)} ({country}) |")
        md.append(f"| **Freshness** | <= {hours_old} hours |")
        md.append(f"| **Total Results** | {len(jobs_list)} (Filtered & Deduplicated) |")
        md.append(f"| **Fetched at** | {now_utc} |")
        md.append("")

        for i, job in enumerate(jobs_list, start=1):
            title = _clean_value(job.get("title"), "Unknown Title")
            company = _clean_value(job.get("company"), "Unknown Company")
            source = _clean_value(job.get("site"), "Unknown Source")
            job_loc = _clean_value(job.get("location"), "Unknown Location")
            job_type = _clean_value(job.get("job_type"), "Not specified")
            date_posted = _clean_value(job.get("date_posted"), "Not available")
            url = _clean_value(job.get("job_url"), "#")
            source = _clean_value(job.get("site"), "Unknown Source")

            # Salary handling
            min_sal = job.get("min_amount")
            max_sal = job.get("max_amount")
            currency = _clean_value(job.get("currency"), "INR")

            if min_sal is not None and not pd.isna(min_sal):
                if max_sal is not None and not pd.isna(max_sal):
                    salary_str = f"{currency} {min_sal:,.0f} – {max_sal:,.0f}"
                else:
                    salary_str = f"{currency} {min_sal:,.0f}+"
            else:
                salary_str = "Not disclosed"

            # Description — longer snippet for better LLM context
            desc = _clean_value(job.get("description"), "No description provided.")
            if len(desc) > DESC_SNIPPET_LEN:
                desc = desc[:DESC_SNIPPET_LEN] + "…"

            md.append(f"### {i}. {title} — {company}\n")
            md.append(f"| Detail | Info |")
            md.append(f"|--------|------|")
            md.append(f"| Source | {source} |")
            md.append(f"| Location | {job_loc} |")
            md.append(f"| Type | {job_type} |")
            md.append(f"| Compensation | {salary_str} |")
            md.append(f"| Posted | {date_posted} |")
            md.append(f"| Link | [Apply Here]({url}) |")
            md.append(f"\n**Description:**\n{desc}\n")
            md.append("---\n")

        return "\n".join(md)

    except Exception as exc:
        # Log full error for the server operator; return safe message to user
        print(f"[ERROR] fetch_and_format_jobs failed: {exc}", file=sys.stderr)
        return (
            "**Something went wrong** while fetching jobs. "
            "Please try again in a moment or adjust your search terms."
        )


# ── Gradio Interface ─────────────────────────────────────────────────────────

demo = gr.Interface(
    fn=fetch_and_format_jobs,
    inputs=[
        gr.Textbox(
            label="Job Titles (comma-separated)", 
            placeholder="e.g., Python Developer Intern, Data Analyst"
        ),
        gr.Textbox(
            label="Locations (comma-separated)", 
            placeholder="e.g., Delhi, Bangalore, Remote"
        ),
        gr.Dropdown(
            label="Country",
            choices=["India", "USA", "UK", "Canada", "Australia", "Germany"],
            value="India"
        ),
        gr.Number(label="Results Wanted", value=5, minimum=1, maximum=25),
        gr.Number(label="Hours Old (max age of postings)", value=48, minimum=1, maximum=168),
    ],
    outputs=gr.Markdown(label="Job Matches"),
    title="OfferQuest MCP Server",
    description="Fetches live job postings and returns LLM-ready Markdown. Default: last 48 hours.",
)


if __name__ == "__main__":
    import os
    
    # Check if the environment explicitly requests Stdio (terminal) mode.
    if os.getenv("GRADIO_MCP_TRANSPORT") == "stdio":
        print("🚀 OfferQuest: Starting in Stdio mode (Terminal)...", file=sys.stderr)
        gr.run(demo, transport="stdio")
    else:
        # This starts the full Web UI + the SSE MCP endpoint.
        print("🌐 OfferQuest: Starting in Web/SSE mode...", file=sys.stderr)
        demo.launch(mcp_server=True)
