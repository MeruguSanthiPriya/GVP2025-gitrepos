import streamlit as st
import pandas as pd

st.title("📘 Definition Evaluator")

# Upload Excel File
uploaded_file = st.file_uploader("Upload the response Excel file", type=["xlsx"])

# Keywords for basic evaluation
precision_keywords = ["true positive", "positive predictions", "precision", "correct positive"]
recall_keywords = ["true positive", "actual positive", "recall", "relevant"]
f1_keywords = ["harmonic mean", "precision", "recall", "f1"]

def check_keywords(text, keywords):
    text = text.lower()
    return any(keyword in text for keyword in keywords)

if uploaded_file:
    df = pd.read_excel(uploaded_file, sheet_name='Form Responses 1')

    # Evaluate definitions
    df["Precision Correct"] = df["In english, describe what is Precision. (do not just describe how to calculate, describe what it means in simple english)"].apply(
        lambda x: check_keywords(str(x), precision_keywords))
    df["Recall Correct"] = df["In english, describe what is Recall. (do not just describe how to calculate, describe what it means in simple english)"].apply(
        lambda x: check_keywords(str(x), recall_keywords))
    df["F1 Score Correct"] = df["In english, describe what is F1 score, and when do you need it?"].apply(
        lambda x: check_keywords(str(x), f1_keywords))

    # Accuracy %
    df["Definition Accuracy (%)"] = (
        df[["Precision Correct", "Recall Correct", "F1 Score Correct"]].sum(axis=1) / 3 * 100
    ).astype(int)

    # Show summary
    st.subheader("📊 Summary")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Students", len(df))
    col2.metric("Precision Correct", df["Precision Correct"].sum())
    col3.metric("Recall Correct", df["Recall Correct"].sum())
    col4.metric("F1 Score Correct", df["F1 Score Correct"].sum())

    # Show results table
    st.subheader("🧑‍🎓 Student Evaluation Results")
    st.dataframe(
        df[[
            "First Name", "Last Name", "Precision Correct", "Recall Correct",
            "F1 Score Correct", "Definition Accuracy (%)"
        ]].sort_values(by="Definition Accuracy (%)", ascending=False),
        use_container_width=True
    )

else:
    st.info("Please upload the Excel file to begin analysis.")
