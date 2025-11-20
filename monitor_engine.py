"""
monitor_engine.py
-----------------

Core engine for monitoring websites:
- Loads sites_config.json
- Downloads pages
- Extracts text
- Compares with snapshots
- Logs changes
- Stores snapshots in /snapshots/
"""

import os
import json
import time
import requests
from bs4 import BeautifulSoup
from hashlib import md5
from datetime import datetime

# ------------------------------------------------------
# Correct, stable paths based on this file's location
# ------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))           # /mount/src/app folder
SNAPSHOT_DIR = os.path.join(BASE_DIR, "snapshots")              # /mount/src/app/snapshots
CONFIG_FILE = os.path.join(BASE_DIR, "sites_config.json")       # /mount/src/app/sites_config.json
LOG_FILE = os.path.join(SNAPSHOT_DIR, "log.txt")                # /mount/src/app/snapshots/log.txt

# Ensure snapshot folder exists
os.makedirs(SNAPSHOT_DIR, exist_ok=True)


# -------------------------------
# Utility: Logging
# -------------------------------

def write_log(message):
    """
    Append a log entry to snapshots/log.txt
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


# -------------------------------
# Utility: Fetch & Extract Text
# -------------------------------

def fetch_html(url):
    """
    Downloads a webpage and returns HTML or error.
    """
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"ERROR_FETCHING: {e}"


def extract_text(html):
    """
    Extract readable text only
    """
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n", strip=True)


# -------------------------------
# Snapshot Handling
# -------------------------------

def snapshot_path(url):
    """
    Snapshot file path using MD5 hash of URL
    """
    hashed = md5(url.encode()).hexdigest()
    return os.path.join(SNAPSHOT_DIR, f"{hashed}.json")


def load_snapshot(url):
    path = snapshot_path(url)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def save_snapshot(url, text):
    path = snapshot_path(url)
    with open(path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "text": text
        }, f, indent=2)


# -------------------------------
# Keyword Matching
# -------------------------------

def keyword_match(text, keywords):
    text_lower = text.lower()
    return [k for k in keywords if k.lower() in text_lower]


# -------------------------------
# MAIN ENGINE
# -------------------------------

def run_check():
    """
    Performs full monitoring cycle and returns a results list.
    """

    # ---------------------------
    # 1. Ensure config file exists
    # ---------------------------
    if not os.path.exists(CONFIG_FILE) or os.path.getsize(CONFIG_FILE) == 0:
        with open(CONFIG_FILE, "w") as f:
            json.dump([], f)

    # ---------------------------
    # 2. Load config safely
    # ---------------------------
    try:
        with open(CONFIG_FILE) as f:
            sites = json.load(f)
        if not isinstance(sites, list):
            raise ValueError("Config must be a list")
    except Exception:
        sites = []
        with open(CONFIG_FILE, "w") as f:
            json.dump([], f)

    results = []

    # ---------------------------
    # 3. Process each site
    # ---------------------------
    for site in sites:
        url = site["url"]
        keywords = site.get("keywords", [])

        # Fetch HTML
        html = fetch_html(url)
        if html.startswith("ERROR_FETCHING"):
            msg = f"ERROR | {url} | {html}"
            write_log(msg)
            results.append({"url": url, "status": "error", "details": html})
            continue

        text = extract_text(html)
        previous = load_snapshot(url)

        # First time
        if previous is None:
            save_snapshot(url, text)
            msg = f"INIT | {url}"
            write_log(msg)
            results.append({"url": url, "status": "initialized"})
            continue

        # No change
        if text == previous["text"]:
            msg = f"NO CHANGE | {url}"
            write_log(msg)
            results.append({"url": url, "status": "no-change"})
            continue

        # Changed → check keywords
        matched = keyword_match(text, keywords)

        if matched:
            msg = f"KEYWORD CHANGE | {url} | keywords: {matched}"
            write_log(msg)
            results.append({
                "url": url,
                "status": "keyword-change",
                "matched_keywords": matched
            })
        else:
            msg = f"CHANGE BUT NO KEYWORDS | {url}"
            write_log(msg)
            results.append({
                "url": url,
                "status": "changed-but-no-keywords"
            })

        # Save updated snapshot
        save_snapshot(url, text)

    return results
