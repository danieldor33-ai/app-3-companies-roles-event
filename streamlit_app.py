import streamlit as st
import json
import os
from monitor_engine import run_check

CONFIG_FILE = "sites_config.json"

st.title("Website Update Monitor (Basic Version)")

# Load config
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE) as f:
        config = json.load(f)
else:
    config = []

st.subheader("Add New Site to Monitor")

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
