import streamlit as st
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.api_client import is_logged_in, current_user, is_student, api_get

st.set_page_config(page_title="Student Dashboard", page_icon="📊", layout="wide")

if not is_logged_in():
    st.warning("Please log in first.")
    st.page_link("app.py", label="Go to Login")
    st.stop()

if not is_student():
    st.error("This page is for students only.")
    st.stop()

user = current_user()
st.title(f"📊 Student Dashboard")
st.caption(f"Welcome, {user.get('name')} · {user.get('department', '')}")

with st.spinner("Loading your data…"):
    status, stats = api_get("/students/dashboard-stats")
    status2, exams = api_get("/students/exams")
    status3, plan = api_get("/students/learning-plan")

if status != 200:
    st.error(f"Could not load dashboard: {stats.get('detail', 'Unknown error')}")
    st.stop()

# ── Key Metrics ───────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("📋 Submissions", stats.get("total_submissions", 0))
col2.metric("✅ Evaluated", stats.get("evaluated", 0))
col3.metric("⏳ Pending", stats.get("pending", 0))
col4.metric("📈 Avg Score", f"{stats.get('avg_score', 0)}%")

st.markdown("---")

col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader("📚 Available Exams")
    if status2 == 200 and exams:
        for exam in exams:
            with st.expander(f"📝 {exam['title']} — {exam['subject']}", expanded=False):
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Marks", exam["total_marks"])
                c2.metric("Duration", f"{exam['duration_minutes']} min")
                c3.metric("Status", exam["status"].replace("_", " ").title())
                if exam["submitted"]:
                    if exam["score"] is not None:
                        pct = round(exam["score"] / exam["total_marks"] * 100, 1) if exam["total_marks"] else 0
                        st.success(f"✅ Score: **{exam['score']}/{exam['total_marks']}** ({pct}%)")
                    else:
                        st.info("⏳ Under evaluation…")
                else:
                    st.page_link("pages/03_Upload_Evaluate.py", label="📤 Submit Answer Sheet")
    else:
        st.info("No exams available yet. Check back soon.")

with col_right:
    st.subheader("📈 Score History")
    history = stats.get("score_history", [])
    if history:
        import pandas as pd
        df = pd.DataFrame(history)
        df["percentage"] = df.apply(
            lambda r: round(r["score"] / r["max"] * 100, 1) if r["max"] else 0, axis=1
        )
        st.bar_chart(df.set_index("exam")["percentage"])
    else:
        st.info("No scores yet. Submit your first answer sheet!")

    if stats.get("best_score", 0) > 0:
        st.success(f"🏆 Best score: **{stats.get('best_score')}%**")

st.markdown("---")
st.subheader("🎯 Your Learning Plan")
if status3 == 200 and plan:
    for p in plan[:3]:
        with st.expander(f"📘 {p['subject']} — {p['created_at'][:10]}", expanded=len(plan) == 1):
            if p.get("weak_areas"):
                st.warning(f"**Weak Areas:** {', '.join(p['weak_areas'][:5])}")
            if p.get("recommendations"):
                st.markdown("**Recommendations:**")
                for rec in p["recommendations"]:
                    st.markdown(f"- {rec}")
            if p.get("resources"):
                st.markdown("**Resources:**")
                for res in p["resources"][:4]:
                    st.markdown(f"- 📖 **{res.get('title', '')}** ({res.get('type', '')})")
else:
    st.info("Your personalized learning plan will appear here after your first evaluation.")
