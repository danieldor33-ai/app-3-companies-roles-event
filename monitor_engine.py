"""
monitor_engine.py
-----------------

This module performs the core functionality of the website monitoring bot:

1. Loads the list of sites + keywords from sites_config.json
2. Downloads page HTML
3. Extracts readable text
4. Compares page content against the last saved snapshot
5. Detects keyword-triggered changes
6. Saves updated snapshots
7. Writes all events to snapshots/log.txt

It is designed to be called from a Streamlit app or a daily scheduled script.
"""

import os
import json
import time
import requests
from bs4 import BeautifulSoup
from hashlib import md5
from datetime import datetime

# ------------------------------------------------------
# Resolve paths based on the current file's real location
# ------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # /mount/src/app-3-companies-roles-event
SNAPSHOT_DIR = os.path.join(BASE_DIR, "snapshots")      # /mount/src/app-3-companies-roles-event/snapshots
LOG_FILE = os.path.join(SNAPSHOT_DIR, "log.txt")

# Create directory if missing
os.makedirs(SNAPSHOT_DIR, exist_ok=True)


# Absolute path to your app directory
APP_DIR = os.path.join(os.getcwd(), "app-3-companies-roles-event")

# Snapshot + log directories INSIDE your app folder
SNAPSHOT_DIR = os.path.join(APP_DIR, "snapshots")
LOG_FILE = os.path.join(SNAPSHOT_DIR, "log.txt")

# Ensure folder exists
os.makedirs(SNAPSHOT_DIR, exist_ok=True)


# -------------------------------
# Utility: Logging
# -------------------------------

def write_log(message):
    """
    Appends a log entry to snapshots/log.txt

    Args:
        message (str): The text to write to the log.
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


# -------------------------------
# Utility: Fetch & Extract Text
# -------------------------------

def fetch_html(url):
    """
    Fetches the raw HTML of a webpage.

    Args:
        url (str): Website URL to fetch.

    Returns:
        str: The HTML content OR an "ERROR_FETCHING" message.
    """
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"ERROR_FETCHING: {e}"


def extract_text(html):
    """
    Extracts readable text from HTML using BeautifulSoup.

    Args:
        html (str): Raw HTML string.

    Returns:
        str: Clean extracted text.
    """
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n", strip=True)


# -------------------------------
# Snapshot Handling
# -------------------------------

def snapshot_path(url):
    """
    Generates a consistent file path for storing a snapshot of a given URL.

    Args:
        url (str): URL to hash for filename.

    Returns:
        str: Path of snapshot file.
    """
    hashed = md5(url.encode()).hexdigest()
    return f"{SNAPSHOT_DIR}/{hashed}.json"


def load_snapshot(url):
    """
    Loads the saved snapshot for a URL if it exists.

    Args:
        url (str): The monitored website URL.

    Returns:
        dict | None: Snapshot content or None if missing.
    """
    path = snapshot_path(url)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def save_snapshot(url, text):
    """
    Saves the latest content of a webpage to a JSON snapshot file.

    Args:
        url (str): Website URL.
        text (str): Clean extracted page text.
    """
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
    """
    Checks which keywords appear in the given text.

    Args:
        text (str): Extracted page text.
        keywords (list[str]): Words to search for.

    Returns:
        list[str]: The matched keywords.
    """
    text_lower = text.lower()
    return [k for k in keywords if k.lower() in text_lower]


# -------------------------------
# MAIN ENGINE: run_check()
# -------------------------------

def run_check():
    """
    Executes one full monitoring cycle:
    - Loads the list of sites to monitor
    - Checks each site's content
    - Compares with previous snapshot
    - Logs results
    - Returns a summary list (for Streamlit)

    Returns:
        list[dict]: Summary of results for each URL.
    """

    # Load configuration file
    if not os.path.exists(CONFIG_FILE):
        write_log("ERROR: sites_config.json missing.")
        return []

    with open(CONFIG_FILE) as f:
        sites = json.load(f)

    results = []

    # Iterate through configured sites
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

        # Extract text
        text = extract_text(html)

        # Load previous snapshot
        previous = load_snapshot(url)

        # First-time initialization
        if previous is None:
            save_snapshot(url, text)
            msg = f"INIT | {url}"
            write_log(msg)
            results.append({"url": url, "status": "initialized"})
            continue

        # No change detected
        if text == previous["text"]:
            msg = f"NO CHANGE | {url}"
            write_log(msg)
            results.append({"url": url, "status": "no-change"})
            continue

        # Changes detected → check for keyword matches
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
