#!/usr/bin/env python3
"""
Auto-update README.md for awesome-ai.

Usage:
    python scripts/update_readme.py

Optional:
    GITHUB_TOKEN=ghp_xxx python scripts/update_readme.py

The script searches GitHub repositories, filters candidates, groups them
into AI-related categories, and rewrites README.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import sys
import time
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

README_PATH = Path("README.md")
DATA_DIR = Path("data")
DATA_PATH = DATA_DIR / "github_repos.json"
SEED_SOURCES_PATH = Path("data/seed_sources.txt")
CONFIG_PATH = Path("api_keys.json")

def load_config() -> dict[str, str]:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as exc:
            print(f"Warning: Failed to parse {CONFIG_PATH}: {exc}", file=sys.stderr)
    return {}

CONFIG = load_config()

def get_api_key(service: str) -> str | None:
    token = os.getenv(service)
    if token:
        return token
    return CONFIG.get(service)

GITHUB_API = "https://api.github.com"

GITHUB_REPO_RE = re.compile(
    r"https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)"
)

CATEGORIES: dict[str, list[str]] = {
    "Large Language Models (LLMs)": [
        'large language model stars:>500 fork:false archived:false',
        'llm framework stars:>500 fork:false archived:false',
    ],
    "Computer Vision": [
        'computer vision stars:>500 fork:false archived:false',
        'object detection stars:>500 fork:false archived:false',
    ],
    "Audio & Speech Processing": [
        'speech recognition stars:>500 fork:false archived:false',
        'text to speech stars:>500 fork:false archived:false',
    ],
    "Generative Art & Video": [
        'stable diffusion stars:>500 fork:false archived:false',
        'generative video stars:>500 fork:false archived:false',
    ],
    "AI Agents & Frameworks": [
        'autonomous agents stars:>500 fork:false archived:false',
        'ai agent framework stars:>500 fork:false archived:false',
    ],
    "MLOps & Data Engineering": [
        'mlops stars:>500 fork:false archived:false',
        'model deployment stars:>500 fork:false archived:false',
    ],
    "Datasets & Training Data": [
        'machine learning dataset stars:>500 fork:false archived:false',
    ],
    "Reinforcement Learning": [
        'reinforcement learning stars:>500 fork:false archived:false',
    ],
    "Machine Learning Frameworks": [
        'machine learning framework stars:>1000 fork:false archived:false',
        'deep learning library stars:>1000 fork:false archived:false',
    ],
    "Ethics, Safety & Alignment": [
        'ai alignment stars:>100 fork:false archived:false',
        'ai safety stars:>100 fork:false archived:false',
    ],
    "Edge AI & Quantization": [
        'model quantization stars:>100 fork:false archived:false',
        'edge ai stars:>100 fork:false archived:false',
    ]
}

NEGATIVE_KEYWORDS = {
    "get rich",
    "course",
    "tutorial",
    "awesome-",
}

CATEGORY_LIMIT = 10
QUERY_RESULT_LIMIT = 10
MIN_STARS = 100

def github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Awesome-AI-Curator",
    }
    token = get_api_key("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    return headers

def fetch_github_repo_info(owner: str, name: str) -> dict[str, Any] | None:
    url = f"{GITHUB_API}/repos/{owner}/{name}"
    resp = requests.get(url, headers=github_headers())
    if resp.status_code == 200:
        return resp.json()
    elif resp.status_code in (403, 429):
        print(f"GitHub API rate limit exceeded when fetching {owner}/{name}.")
        return None
    return None

def search_github(query: str, limit: int = QUERY_RESULT_LIMIT) -> list[dict[str, Any]]:
    url = f"{GITHUB_API}/search/repositories"
    params = {"q": query, "sort": "stars", "order": "desc", "per_page": limit}
    resp = requests.get(url, headers=github_headers(), params=params)
    if resp.status_code == 200:
        return resp.json().get("items", [])
    elif resp.status_code in (403, 429):
        print(f"GitHub API rate limit exceeded on search: {query}")
        return []
    return []

def load_local_data() -> dict[str, Any]:
    if DATA_PATH.exists():
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}

def save_local_data(data: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def is_valid_repo(repo_info: dict[str, Any]) -> bool:
    if not repo_info:
        return False
    if repo_info.get("stargazers_count", 0) < MIN_STARS:
        return False
    desc = (repo_info.get("description") or "").lower()
    name = (repo_info.get("name") or "").lower()
    for kw in NEGATIVE_KEYWORDS:
        if kw in desc or kw in name:
            return False
    return True

def generate_markdown(categories_data: dict[str, list[dict[str, Any]]]) -> str:
    tz = dt.timezone.utc
    today = dt.datetime.now(tz).strftime('%Y-%m-%d')
    
    md = [
        "# Awesome AI",
        "",
        "A curated list of advanced Artificial Intelligence research, frameworks, and datasets.",
        "",
        f"> Last Updated: {today} (UTC)",
        "",
        "## Contents",
        ""
    ]
    
    for cat in CATEGORIES.keys():
        anchor = cat.lower().replace(' & ', '-').replace(' ', '-').replace('(', '').replace(')', '')
        md.append(f"- [{cat}](#{anchor})")
    
    md.append("")
    
    for cat, repos in categories_data.items():
        md.append(f"## {cat}\n")
        if not repos:
            md.append("_No repositories found in this update._\n")
            continue
            
        for repo in sorted(repos, key=lambda x: x.get("stargazers_count", 0), reverse=True):
            name = repo.get("full_name")
            url = repo.get("html_url")
            desc = (repo.get("description") or "No description").strip()
            lang = repo.get("language") or "N/A"
            stars = repo.get("stargazers_count", 0)
            forks = repo.get("forks_count", 0)
            pushed_at = repo.get("pushed_at", "")[:10] if repo.get("pushed_at") else "Unknown"
            
            license_info = repo.get("license")
            lic = license_info.get("spdx_id") if license_info else "N/A"
            
            md.append(f"- [{name}]({url}) — {desc} `{lang}` · ⭐ {stars:,} · forks {forks:,} · updated {pushed_at} · license {lic}")
        md.append("")
        
    md.append("---")
    md.append("*This repository is automatically updated daily via GitHub Actions.*")
    
    return "\n".join(md)

def main():
    print("Starting Awesome-AI update...")
    local_data = load_local_data()
    
    # Process seed sources
    if SEED_SOURCES_PATH.exists():
        with open(SEED_SOURCES_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                match = GITHUB_REPO_RE.search(line)
                if match:
                    owner, name = match.groups()
                    full_name = f"{owner}/{name}"
                    if full_name not in local_data:
                        print(f"Fetching seed repo: {full_name}")
                        info = fetch_github_repo_info(owner, name)
                        if info:
                            local_data[full_name] = info
                        time.sleep(1) # Rate limit padding

    # Search categories
    categories_data = {k: [] for k in CATEGORIES.keys()}
    
    for cat, queries in CATEGORIES.items():
        print(f"Processing category: {cat}")
        cat_repos = []
        for query in queries:
            results = search_github(query)
            for r in results:
                full_name = r["full_name"]
                local_data[full_name] = r
                if is_valid_repo(r) and full_name not in [x["full_name"] for x in cat_repos]:
                    cat_repos.append(r)
            time.sleep(2) # Rate limit padding
        
        # Deduplicate and sort
        categories_data[cat] = cat_repos[:CATEGORY_LIMIT]
    
    save_local_data(local_data)
    
    md_content = generate_markdown(categories_data)
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    print("Updated README.md successfully.")

if __name__ == "__main__":
    main()
