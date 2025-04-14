import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import plotly.express as px
import time
import re
import numpy as np
from threading import Lock

# Streamlit configuration
st.set_page_config(page_title="Profile Analysis Dashboard", layout="wide")
st.title("Profile Analysis Dashboard")
st.markdown("Upload your spreadsheet to analyze GitHub profiles.")

# Cache for duplicate IDs/URLs (user-specific)
cache = {}
cache_lock = Lock()

# Function to scrape GitHub using web scraping (restored to original working state)
def scrape_github(github_id):
    if not github_id or pd.isna(github_id) or str(github_id).strip().lower() == "none" or not str(github_id).strip():
        return {"error": "No GitHub ID provided", "count": 0, "repos": []}
    try:
        github_id = github_id.strip()
        if not re.match(r'^[a-zA-Z0-9\-]+$', github_id):
            return {"error": "Invalid GitHub ID format", "count": 0, "repos": []}
        
        url = f"https://github.com/{github_id}?tab=repositories"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        repo_list = soup.find("div", id="user-repositories-list")
        if not repo_list:
            return {"error": "No repositories found", "count": 0, "repos": []}

        repos = repo_list.find_all("li", class_="source")
        repo_data = []
        for repo in repos:
            name_elem = repo.find("a", itemprop="name codeRepository")
            name = name_elem.get_text().strip() if name_elem else "Unknown"
            link = f"https://github.com/{github_id}/{name}" if name != "Unknown" else ""
            language_elem = repo.find("span", itemprop="programmingLanguage")
            language = language_elem.get_text().strip() if language_elem else "Unknown"
            description_elem = repo.find("p", itemprop="description")
            description = description_elem.get_text().strip() if description_elem else ""
            repo_data.append({"name": name, "link": link, "language": language, "description": description})

        return {"repos": repo_data, "count": len(repo_data)}
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error: {str(e)}", "count": 0, "repos": []}
    except Exception as e:
        return {"error": f"Scraping error: {str(e)}", "count": 0, "repos": []}

# Function to process a single row
def process_row(row, user_key):
    with cache_lock:
        cache.clear()  # Reset cache per user
    github_result = scrape_github(row["GitHub ID"])
    return {
        "github": github_result
    }

# File uploader
uploaded_file = st.file_uploader("Upload Excel/CSV", type=["xlsx", "csv"])
if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith("xlsx") else pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"Failed to read file: {str(e)}")
        st.stop()

    # Validate columns
    required_cols = ["First Name", "Last Name", "This is my GitHub ID"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"Missing columns: {', '.join(missing_cols)}")
        st.stop()

    # Rename columns
    df = df.rename(columns={
        "This is my GitHub ID": "GitHub ID"
    })

    # Clean dataframe
    df = df[["First Name", "Last Name", "GitHub ID"]].copy()
    df.fillna("", inplace=True)

    st.success(f"Loaded {len(df)} rows.")
    st.dataframe(df, use_container_width=True)

    # Tabs
    tabs = st.tabs(["Summary", "GitHub"])

    # Process data
    results = []
    errors = []
    progress_bar = st.progress(0)
    total_rows = len(df)

    try:
        for i, row in df.iterrows():
            user_key = f"{row['First Name']}_{row['Last Name']}"
            try:
                result = process_row(row, user_key)
                github_result = result["github"]
                if github_result.get("error") and "No GitHub ID provided" in github_result["error"]:
                    errors.append(f"Row {i+1} ({user_key}): No GitHub ID provided")
                elif github_result.get("error") and "Invalid GitHub ID format" in github_result["error"]:
                    errors.append(f"Row {i+1} ({user_key}): Invalid GitHub ID format - {row['GitHub ID']}")
                results.append(result)
            except Exception as e:
                errors.append(f"Row {i+1} ({user_key}): Processing error - {str(e)}")
                results.append({
                    "github": {"error": "Processing error", "count": 0, "repos": []}
                })
            progress_bar.progress((i + 1) / total_rows)
    finally:
        pass

    # Summary Tab
    with tabs[0]:
        st.header("Summary")
        valid_github = sum(1 for r in results if not r["github"].get("error"))
        summary_data = {
            "Total Users": len(df),
            "Valid GitHub IDs": valid_github,
            "Average GitHub Repos": round(np.mean([r["github"]["count"] for r in results if not r["github"].get("error")] or [0]), 2)
        }
        st.dataframe(pd.DataFrame([summary_data]), use_container_width=True)
        if errors:
            with st.expander("View Errors"):
                st.write("\n".join(errors))

    # GitHub Tab
    with tabs[1]:
        for i, row in df.iterrows():
            user_key = f"{row['First Name']}_{row['Last Name']}"
            st.subheader(f"{row['First Name']} {row['Last Name']} (GitHub: {row['GitHub ID'] or 'None'})")
            result = results[i]["github"]
            if result.get("error"):
                st.warning(result["error"])
            else:
                st.metric("Total Repositories", result["count"])
                if result["repos"]:
                    st.dataframe(pd.DataFrame(result["repos"]), use_container_width=True)
                    langs = [repo["language"] for repo in result["repos"] if repo["language"] != "Unknown"]
                    if langs:
                        lang_counts = pd.Series(langs).value_counts()
                        fig = px.bar(x=lang_counts.index, y=lang_counts.values, labels={"x": "Language", "y": "Count"}, title="Repository Languages")
                        st.plotly_chart(fig, use_container_width=True, key=f"github_chart_{i}")
                else:
                    st.info("No repositories found.")

    # Download results
    results_df = pd.DataFrame([
        {
            "First Name": row["First Name"],
            "Last Name": row["Last Name"],
            "GitHub ID": row["GitHub ID"] or "None",
            "GitHub Repos": results[i]["github"]["count"] if not results[i]["github"].get("error") else results[i]["github"].get("error")
        }
        for i, row in df.iterrows()
    ])
    csv = results_df.to_csv(index=False)
    st.download_button("Download Results", csv, "profile_results.csv", "text/csv", use_container_width=True)