import streamlit as st
import requests
import pandas as pd
import json

def get_leetcode_stats(username):
    url = "https://leetcode.com/graphql"
    query = {
        "query": """
        query getUserProfile($username: String!) {
            matchedUser(username: $username) {
                submitStats {
                    acSubmissionNum {
                        difficulty
                        count
                    }
                }
            }
        }
        """,
        "variables": {
            "username": username
        }
    }

    res = requests.post(url, json=query)
    if res.status_code != 200:
        return None

    data = res.json()

    try:
        submissions = data["data"]["matchedUser"]["submitStats"]["acSubmissionNum"]
        stats = {entry["difficulty"]: entry["count"] for entry in submissions}
        return stats
    except:
        return None

# Streamlit UI
st.title("📊 LeetCode Stats from Excel")

uploaded_file = st.file_uploader("Upload Excel file with LeetCode profile links", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    
    col_name = 'Paste your Leetcode profile link'
    if col_name not in df.columns:
        st.error(f"Excel must have a column named '{col_name}'")
    else:
        results = []
        for url in df[col_name]:
            if isinstance(url, str) and "leetcode.com/" in url:
                username = url.rstrip("/").split("/")[-1]
                stats = get_leetcode_stats(username)
                results.append({
                    "username": username,
                    "stats": stats if stats else "Failed to fetch"
                })
            else:
                results.append({
                    "username": "Invalid URL",
                    "stats": "Skipped"
                })

        # 🔽 Show Download Button First
        json_data = json.dumps(results, indent=2)
        st.download_button(
            label="📥 Download LeetCode Stats as JSON",
            data=json_data,
            file_name="leetcode_stats.json",
            mime="application/json"
        )

        # 📤 Then Show the JSON Output in the App
        st.subheader("📄 Stats Preview")
        st.json(results)
