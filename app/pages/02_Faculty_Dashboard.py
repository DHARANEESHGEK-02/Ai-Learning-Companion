import streamlit as st
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.api_client import is_logged_in, is_faculty, current_user, api_get, api_post

st.set_page_config(page_title="Faculty Dashboard", page_icon="👨‍🏫", layout="wide")

if not is_logged_in():
    st.warning("Please log in first.")
    st.stop()

if not is_faculty():
    st.error("This page is for faculty only.")
    st.stop()

user = current_user()
st.title("👨‍🏫 Faculty Dashboard")
st.caption(f"Welcome, {user.get('name')} · {user.get('department', '')}")

with st.spinner("Loading…"):
    _, stats = api_get("/faculty/dashboard-stats")
    _, subjects = api_get("/faculty/subjects")
    _, exams = api_get("/faculty/exams")
    _, submissions = api_get("/faculty/submissions")

# ── Metrics ───────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("📋 Total Exams", stats.get("total_exams", 0))
c2.metric("📨 Submissions", stats.get("total_submissions", 0))
c3.metric("✅ Evaluated", stats.get("evaluated", 0))
c4.metric("📈 Avg Score", f"{stats.get('avg_score_percent', 0)}%")

st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["📝 Manage Exams", "📊 Submissions", "➕ Create Exam", "📚 Subjects"])

# ── Tab 1: Manage Exams ────────────────────────────────────────────────────────
with tab1:
    st.subheader("Your Exams")
    if isinstance(exams, list) and exams:
        import pandas as pd
        df = pd.DataFrame(exams)
        st.dataframe(df[["title", "subject", "total_marks", "question_count",
                          "submission_count", "evaluated_count", "created_at"]],
                     use_container_width=True)

        st.subheader("Add Questions to an Exam")
        exam_options = {f"{e['title']} (ID:{e['id']})": e["id"] for e in exams}
        selected_exam = st.selectbox("Select Exam", list(exam_options.keys()))
        exam_id = exam_options[selected_exam]

        _, questions = api_get(f"/faculty/exams/{exam_id}/questions")
        if isinstance(questions, list) and questions:
            st.markdown(f"**Existing Questions ({len(questions)}):**")
            for q in questions:
                st.markdown(f"- **Q{q['question_number']}** ({q['marks']} marks): {q['question_text'][:100]}")

        with st.form("add_question_form"):
            st.markdown("**Add New Question:**")
            q_num = st.number_input("Question Number", min_value=1, value=len(questions) + 1 if isinstance(questions, list) else 1)
            q_text = st.text_area("Question Text", height=100)
            model_ans = st.text_area("Model Answer", height=150)
            marks = st.number_input("Marks", min_value=1, value=10)
            subject_area = st.selectbox("Subject Area", ["CS", "Physics", "Chemistry", "Biology", "Maths", "Other"])
            rubric_text = st.text_area("Rubric Criteria (optional, one per line format: criterion|weight)", height=80,
                                        placeholder="Correct formula|3\nStep-by-step solution|4\nFinal answer|3")
            add_q = st.form_submit_button("Add Question", type="primary")

        if add_q and q_text and model_ans:
            rubric = []
            if rubric_text:
                for line in rubric_text.strip().split("\n"):
                    parts = line.split("|")
                    if len(parts) == 2:
                        try:
                            rubric.append({"criterion": parts[0].strip(), "weight": float(parts[1].strip())})
                        except ValueError:
                            pass
            payload = {
                "question_number": int(q_num),
                "question_text": q_text,
                "model_answer": model_ans,
                "marks": int(marks),
                "subject_area": subject_area,
                "rubric": rubric or None,
            }
            status, resp = api_post(f"/faculty/exams/{exam_id}/questions", json=payload)
            if status == 200:
                st.success("Question added successfully!")
                st.rerun()
            else:
                st.error(resp.get("detail", "Failed to add question"))
    else:
        st.info("No exams yet. Create one in the 'Create Exam' tab.")

# ── Tab 2: Submissions ─────────────────────────────────────────────────────────
with tab2:
    st.subheader("All Submissions")
    if isinstance(submissions, list) and submissions:
        import pandas as pd
        df = pd.DataFrame(submissions)

        col_filter, col_sort = st.columns(2)
        with col_filter:
            status_filter = st.multiselect("Filter by Status",
                options=["pending", "processing", "evaluated", "failed"],
                default=["pending", "processing", "evaluated", "failed"])
        with col_sort:
            sort_by = st.selectbox("Sort by", ["submitted_at", "total_score", "student_name"])

        filtered = df[df["status"].isin(status_filter)] if status_filter else df
        st.dataframe(
            filtered.sort_values(sort_by, ascending=False)[
                ["student_name", "student_email", "exam_title", "status",
                 "total_score", "max_score", "plagiarism_score", "submitted_at"]
            ],
            use_container_width=True,
        )

        pending_count = len([s for s in submissions if s["status"] == "pending"])
        if pending_count > 0:
            if st.button(f"🚀 Batch Evaluate {pending_count} Pending Submissions", type="primary"):
                with st.spinner("Queuing evaluations…"):
                    status, resp = api_post("/faculty/batch-evaluate")
                if status == 200:
                    st.success(resp.get("message", "Evaluation started!"))
                    st.rerun()
                else:
                    st.error("Failed to start batch evaluation")
    else:
        st.info("No submissions yet.")

# ── Tab 3: Create Exam ─────────────────────────────────────────────────────────
with tab3:
    st.subheader("Create New Exam")
    if not isinstance(subjects, list) or not subjects:
        st.warning("Create a subject first in the 'Subjects' tab.")
    else:
        with st.form("create_exam_form"):
            title = st.text_input("Exam Title", placeholder="Mid-Semester Examination — CS301")
            subject_map = {f"{s['name']} ({s['code']})": s["id"] for s in subjects}
            selected_subject = st.selectbox("Subject", list(subject_map.keys()))
            total_marks = st.number_input("Total Marks", min_value=10, value=100)
            duration = st.number_input("Duration (minutes)", min_value=30, value=180)
            instructions = st.text_area("Instructions (optional)")
            create_exam = st.form_submit_button("Create Exam", type="primary")

        if create_exam and title:
            payload = {
                "title": title,
                "subject_id": subject_map[selected_subject],
                "total_marks": int(total_marks),
                "duration_minutes": int(duration),
                "instructions": instructions or None,
            }
            status, resp = api_post("/faculty/exams", json=payload)
            if status == 200:
                st.success(f"Exam '{title}' created successfully!")
                st.rerun()
            else:
                st.error(resp.get("detail", "Failed to create exam"))

# ── Tab 4: Subjects ────────────────────────────────────────────────────────────
with tab4:
    st.subheader("Manage Subjects")
    if isinstance(subjects, list) and subjects:
        import pandas as pd
        st.dataframe(pd.DataFrame(subjects)[["id", "name", "code", "description"]],
                     use_container_width=True)

    with st.form("create_subject_form"):
        st.markdown("**Create New Subject:**")
        subj_name = st.text_input("Subject Name", placeholder="Data Structures & Algorithms")
        subj_code = st.text_input("Subject Code", placeholder="CS301")
        subj_desc = st.text_area("Description (optional)")
        create_subj = st.form_submit_button("Create Subject", type="primary")

    if create_subj and subj_name and subj_code:
        status, resp = api_post("/faculty/subjects",
                                 json={"name": subj_name, "code": subj_code, "description": subj_desc or None})
        if status == 200:
            st.success(f"Subject '{subj_name}' created!")
            st.rerun()
        else:
            st.error(resp.get("detail", "Failed to create subject"))
