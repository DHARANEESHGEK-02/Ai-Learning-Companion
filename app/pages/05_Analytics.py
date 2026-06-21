import streamlit as st
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.api_client import is_logged_in, current_user, api_get, is_faculty
import pandas as pd

st.set_page_config(page_title="Analytics", page_icon="📈", layout="wide")

if not is_logged_in():
    st.warning("Please log in first.")
    st.stop()

st.title("📈 Analytics Dashboard")

with st.spinner("Loading analytics…"):
    _, dashboard = api_get("/analytics/dashboard")

if not isinstance(dashboard, dict):
    st.error("Could not load analytics data.")
    st.stop()

# ── Top metrics ───────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("👨‍🎓 Students", dashboard.get("total_students", 0))
c2.metric("📝 Exams", dashboard.get("total_exams", 0))
c3.metric("✅ Evaluated", dashboard.get("total_evaluations", 0))
c4.metric("📈 Avg Score", f"{dashboard.get('avg_score_percent', 0)}%")
c5.metric("⏳ Pending", dashboard.get("pending_evaluations", 0))

st.markdown("---")

col_left, col_right = st.columns(2)

# ── Score Distribution ─────────────────────────────────────────────────────────
with col_left:
    st.subheader("📊 Score Distribution")
    dist = dashboard.get("score_distribution", [])
    if dist:
        df_dist = pd.DataFrame(dist)
        st.bar_chart(df_dist.set_index("range")["count"])
        pass_count = sum(d["count"] for d in dist if d["range"] not in ("0-40",))
        fail_count = sum(d["count"] for d in dist if d["range"] == "0-40")
        total = pass_count + fail_count
        if total > 0:
            st.metric("Pass Rate", f"{round(pass_count/total*100, 1)}%",
                      delta=f"{pass_count} passed / {fail_count} failed")
    else:
        st.info("No evaluation data yet.")

# ── Subject Performance ────────────────────────────────────────────────────────
with col_right:
    st.subheader("📚 Subject Performance")
    subject_stats = dashboard.get("subject_stats", [])
    if subject_stats:
        df_subj = pd.DataFrame(subject_stats)
        st.bar_chart(df_subj.set_index("subject")["avg_score"])
        st.dataframe(df_subj[["subject", "code", "submissions", "avg_score"]], use_container_width=True)
    else:
        st.info("No subject data yet.")

st.markdown("---")

# ── Recent Activity ───────────────────────────────────────────────────────────
st.subheader("🕐 Recent Activity")
recent = dashboard.get("recent_activity", [])
if recent:
    df_recent = pd.DataFrame(recent)
    st.dataframe(df_recent[["student", "exam", "status", "score", "submitted_at"]],
                 use_container_width=True)
else:
    st.info("No recent activity.")

# ── Subject-level deep dive (faculty only) ─────────────────────────────────────
if is_faculty():
    st.markdown("---")
    st.subheader("🔍 Subject Deep-Dive")
    _, subjects = api_get("/faculty/subjects")
    if isinstance(subjects, list) and subjects:
        subject_map = {f"{s['name']} ({s['code']})": s["id"] for s in subjects}
        selected = st.selectbox("Select Subject", list(subject_map.keys()))
        subj_id = subject_map[selected]

        _, subj_data = api_get(f"/analytics/subject/{subj_id}")
        if isinstance(subj_data, dict) and "top_missing_concepts" in subj_data:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Submissions", subj_data.get("total_submissions", 0))
            with col2:
                st.markdown("**Most Missed Concepts:**")
                for item in subj_data.get("top_missing_concepts", [])[:8]:
                    st.markdown(f"- **{item['concept']}** — missed by {item['count']} student(s)")
