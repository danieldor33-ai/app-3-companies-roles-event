import streamlit as st
import json
import os
from monitor_engine import run_check

CONFIG_FILE = "sites_config.json"

# Ensure config file exists and is valid
if not os.path.exists(CONFIG_FILE) or os.path.getsize(CONFIG_FILE) == 0:
    # Create empty list config
    with open(CONFIG_FILE, "w") as f:
        json.dump([], f)

# Safe-load config with fallback
try:
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    if not isinstance(config, list):
        raise ValueError("Config is not a list")
except Exception:
    # If invalid → reset to empty list
    config = []
    with open(CONFIG_FILE, "w") as f:
        json.dump([], f)


url = st.text_input("Site URL")
keywords = st.text_input("Keywords (comma-separated)")

if st.button("Add Site"):
    if url.strip() == "":
        st.error("URL cannot be empty")
    else:
        config.append({
            "url": url.strip(),
            "keywords": [k.strip() for k in keywords.split(",") if k.strip()]
        })
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        st.success("Site added successfully!")

st.write("### Sites Being Monitored")
st.json(config)

st.subheader("Manual Check")
if st.button("Run Check Now"):
    results = run_check()
    st.write("### Results")
    st.json(results)
