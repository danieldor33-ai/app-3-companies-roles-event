import json
import os
import requests
from bs4 import BeautifulSoup
from hashlib import md5
from datetime import datetime

SNAPSHOT_DIR = "snapshots"
CONFIG_FILE = "sites_config.json"

os.makedirs(SNAPSHOT_DIR, exist_ok=True)

def fetch_html(url):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"ERROR_FETCHING: {e}"

def extract_text(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def snapshot_path(url):
    hashed = md5(url.encode()).hexdigest()
    return f"{SNAPSHOT_DIR}/{hashed}.json"

def load_snapshot(url):
    path = snapshot_path(url)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None

def save_snapshot(url, text):
    path = snapshot_path(url)
    with open(path, "w") as f:
        json.dump({"timestamp": datetime.now().isoformat(), "text": text}, f, indent=2)

def keyword_match(text, keywords):
    text_lower = text.lower()
    return [k for k in keywords if k.lower() in text_lower]

def run_check():
    if not os.path.exists(CONFIG_FILE):
        return []

    with open(CONFIG_FILE) as f:
        sites = json.load(f)

    results = []

    for site in sites:
        url = site["url"]
        keywords = site.get("keywords", [])

        html = fetch_html(url)
        if html.startswith("ERROR_FETCHING"):
            results.append({"url": url, "status": "error", "details": html})
            continue

        text = extract_text(html)
        previous = load_snapshot(url)

        # First time checking
        if previous is None:
            save_snapshot(url, text)
            results.append({"url": url, "status": "initialized"})
            continue

        # If no change → skip
        if text == previous["text"]:
            results.append({"url": url, "status": "no-change"})
            continue

        # If changed → check keywords
        matched = keyword_match(text, keywords)

        if matched:
            results.append({
                "url": url,
                "status": "keyword-change",
                "matched_keywords": matched
            })
        else:
            results.append({
                "url": url,
                "status": "changed-but-no-keywords"
            })

        # Save new snapshot every time
        save_snapshot(url, text)

    return results
