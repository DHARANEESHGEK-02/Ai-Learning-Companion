import streamlit as st
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.api_client import is_logged_in, current_user, api_get, api_post
import httpx
import time

st.set_page_config(page_title="Submit & Evaluate", page_icon="📤", layout="wide")

if not is_logged_in():
    st.warning("Please log in first.")
    st.stop()

user = current_user()
st.title("📤 Submit Answer Sheet & Evaluation")
st.caption("Upload your handwritten or typed answer sheet for AI-powered evaluation")

tab1, tab2 = st.tabs(["📤 Submit Answer Sheet", "📋 My Results"])

# ── Tab 1: Submit ─────────────────────────────────────────────────────────────
with tab1:
    _, exams = api_get("/students/exams")

    if not isinstance(exams, list) or not exams:
        st.info("No exams available for submission.")
        st.stop()

    unsubmitted = [e for e in exams if not e["submitted"]]
    submitted_exams = [e for e in exams if e["submitted"]]

    if not unsubmitted:
        st.success("✅ You have submitted all available exams!")
    else:
        st.subheader("Select an Exam")
        exam_map = {f"{e['title']} — {e['subject']} ({e['total_marks']} marks)": e for e in unsubmitted}
        selected_label = st.selectbox("Available Exams", list(exam_map.keys()))
        selected_exam = exam_map[selected_label]

        st.info(f"📝 **{selected_exam['title']}** · {selected_exam['subject']} · "
                f"{selected_exam['total_marks']} marks · {selected_exam['duration_minutes']} min")

        # ── Question Paper ────────────────────────────────────────────────────
        st.markdown("---")
        st.subheader("Question Paper")

        _, questions = api_get(f"/students/exams/{selected_exam['id']}/questions")

        if not isinstance(questions, list) or not questions:
            st.info("No questions have been added to this exam yet.")
        else:
            total_q_marks = sum(q.get("marks", 0) for q in questions)
            st.caption(f"{len(questions)} question(s) · {total_q_marks} total marks")

            for q in questions:
                qnum = q.get("question_number", "?")
                qtext = q.get("question_text", "")
                qmarks = q.get("marks", 0)
                qarea = q.get("subject_area")

                with st.container(border=True):
                    col_label, col_marks = st.columns([9, 1])
                    with col_label:
                        st.markdown(f"**Q{qnum}**" + (f" — *{qarea}*" if qarea else ""))
                    with col_marks:
                        st.markdown(
                            f"<div style='text-align:right;'>"
                            f"<span style='background:#1f4e79;color:#fff;"
                            f"padding:2px 10px;border-radius:12px;font-size:0.82em;"
                            f"font-weight:600;'>{qmarks} mk{'s' if qmarks != 1 else ''}</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    st.write(qtext)

        # ── Submission Method ─────────────────────────────────────────────────
        st.markdown("---")
        st.subheader("Submission Method")
        upload_mode = st.radio(
            "How would you like to submit your answers?",
            ["📁 Upload File (PDF/Image)", "📷 Capture from Camera", "⌨️ Type Answer Directly"],
            horizontal=True,
        )

        if upload_mode == "📁 Upload File (PDF/Image)":
            st.markdown("#### Upload Answer Sheet")
            st.caption("Supports: PDF, JPG, JPEG, PNG (handwritten or printed)")
            uploaded_file = st.file_uploader(
                "Choose file",
                type=["pdf", "jpg", "jpeg", "png", "bmp"],
                help="Upload a clear scan or photo of your answer sheet",
            )

            if uploaded_file:
                file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
                st.success(f"✅ File selected: **{uploaded_file.name}** ({file_size_mb:.1f} MB)")
                if file_size_mb > 10:
                    st.warning("File is large. Processing may take longer.")

                if st.button("🚀 Submit & Evaluate", type="primary", use_container_width=True):
                    with st.spinner("Uploading and starting evaluation… This may take 1-2 minutes."):
                        token = st.session_state.get("token", "")
                        try:
                            file_bytes = uploaded_file.getvalue()
                            response = httpx.post(
                                "http://localhost:8000/evaluations/upload",
                                headers={"Authorization": f"Bearer {token}"},
                                data={"exam_id": selected_exam["id"]},
                                files={"file": (uploaded_file.name, file_bytes, uploaded_file.type)},
                                timeout=60,
                            )
                            if response.status_code == 200:
                                resp_data = response.json()
                                st.success(f"✅ Submitted! Sheet ID: {resp_data['sheet_id']}")
                                st.info("⏳ Evaluation is running in the background. Check 'My Results' tab in a few minutes.")
                                st.session_state["last_sheet_id"] = resp_data["sheet_id"]
                            else:
                                st.error(response.json().get("detail", "Submission failed"))
                        except Exception as e:
                            st.error(f"Upload error: {e}")

        elif upload_mode == "📷 Capture from Camera":
            st.markdown("#### Capture Answer Sheet from Camera")
            st.caption("Use your device camera to capture a photo of your answer sheet")

            camera_input = st.camera_input(
                "Take a photo of your answer sheet",
                help="Position your answer sheet clearly in the camera frame for best results",
            )

            if camera_input:
                st.success("✅ Photo captured successfully")
                st.image(camera_input, caption="Captured Answer Sheet", use_column_width=True)

                if st.button("🚀 Submit & Evaluate", type="primary", use_container_width=True):
                    with st.spinner("Processing and starting evaluation… This may take 1-2 minutes."):
                        token = st.session_state.get("token", "")
                        try:
                            file_bytes = camera_input.getvalue()
                            response = httpx.post(
                                "http://localhost:8000/evaluations/upload",
                                headers={"Authorization": f"Bearer {token}"},
                                data={"exam_id": selected_exam["id"]},
                                files={"file": ("camera_capture.jpg", file_bytes, "image/jpeg")},
                                timeout=60,
                            )
                            if response.status_code == 200:
                                resp_data = response.json()
                                st.success(f"✅ Submitted! Sheet ID: {resp_data['sheet_id']}")
                                st.info("⏳ Evaluation is running in the background. Check 'My Results' tab in a few minutes.")
                                st.session_state["last_sheet_id"] = resp_data["sheet_id"]
                            else:
                                st.error(response.json().get("detail", "Submission failed"))
                        except Exception as e:
                            st.error(f"Capture error: {e}")

        elif upload_mode == "⌨️ Type Answer Directly":
            st.markdown("#### Type Your Answers")

            # Keep question paper accessible while typing
            if isinstance(questions, list) and questions:
                with st.expander("📄 View Full Question Paper", expanded=False):
                    for q in questions:
                        qnum = q.get("question_number", "?")
                        qtext = q.get("question_text", "")
                        qmarks = q.get("marks", 0)
                        st.markdown(f"**Q{qnum}** *(·{qmarks} marks)*")
                        st.write(qtext)
                        st.markdown("---")

            st.caption("Type your complete answer sheet below. Include question numbers.")
            text_answer = st.text_area(
                "Your Answers",
                height=400,
                placeholder="Q1. [Your answer here]\n\nQ2. [Your answer here]\n\nQ3. [Your answer here]",
            )

            if st.button("🚀 Submit & Evaluate", type="primary",
                          use_container_width=True, disabled=not text_answer):
                with st.spinner("Submitting and starting evaluation…"):
                    token = st.session_state.get("token", "")
                    try:
                        response = httpx.post(
                            "http://localhost:8000/evaluations/upload",
                            headers={"Authorization": f"Bearer {token}"},
                            data={"exam_id": selected_exam["id"], "text_answer": text_answer},
                            timeout=60,
                        )
                        if response.status_code == 200:
                            resp_data = response.json()
                            st.success(f"✅ Submitted! Evaluation started.")
                            st.session_state["last_sheet_id"] = resp_data["sheet_id"]
                            st.info("⏳ Results will appear in 'My Results' tab shortly.")
                        else:
                            st.error(response.json().get("detail", "Submission failed"))
                    except Exception as e:
                        st.error(f"Error: {e}")

# ── Tab 2: Results ─────────────────────────────────────────────────────────────
with tab2:
    st.subheader("My Evaluation Results")
    _, submissions = api_get("/students/my-submissions")

    if not isinstance(submissions, list) or not submissions:
        st.info("No submissions yet. Submit your first answer sheet!")
    else:
        for sheet in submissions:
            status_icon = {
                "evaluated": "✅", "pending": "⏳", "processing": "🔄", "failed": "❌"
            }.get(sheet["status"], "❓")

            with st.expander(
                f"{status_icon} Sheet #{sheet['id']} — Exam ID: {sheet['exam_id']} · {sheet['submitted_at'][:10]}",
                expanded=False
            ):
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Status", sheet["status"].title())
                col2.metric("Score", f"{sheet.get('total_score', '—')}/{sheet.get('max_score', '—')}")
                if sheet.get("total_score") and sheet.get("max_score"):
                    pct = round(sheet["total_score"] / sheet["max_score"] * 100, 1)
                    col3.metric("Percentage", f"{pct}%")
                if sheet.get("plagiarism_score") is not None:
                    plag_pct = round(sheet["plagiarism_score"] * 100, 1)
                    color = "🔴" if plag_pct > 70 else "🟡" if plag_pct > 40 else "🟢"
                    col4.metric("Plagiarism Risk", f"{color} {plag_pct}%")

                if sheet["status"] == "evaluated":
                    _, evals = api_get(f"/students/submissions/{sheet['id']}/evaluations")
                    if isinstance(evals, list) and evals:
                        st.markdown("**Question-wise Breakdown:**")
                        for ev in evals:
                            pct = round(ev["score"] / ev["max_score"] * 100) if ev["max_score"] else 0
                            bar_color = "🟢" if pct >= 75 else "🟡" if pct >= 50 else "🔴"
                            with st.container():
                                st.markdown(f"**Q{ev['question_number']}** {bar_color} — "
                                            f"**{ev['score']}/{ev['max_score']}** ({pct}%)")
                                if ev.get("feedback"):
                                    st.caption(f"💬 {ev['feedback']}")
                                if ev.get("missing_concepts"):
                                    st.caption(f"⚠️ Missing: {', '.join(ev['missing_concepts'][:3])}")
                                if ev.get("strengths"):
                                    st.caption(f"✅ Strengths: {', '.join(ev['strengths'][:3])}")
                                st.progress(pct / 100)

                elif sheet["status"] in ("pending", "processing"):
                    st.info("⏳ Evaluation in progress. Refresh to check.")
                    if st.button("🔄 Refresh", key=f"refresh_{sheet['id']}"):
                        st.rerun()
