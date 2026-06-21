import streamlit as st
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.api_client import is_logged_in, current_user, api_get, is_faculty, is_student

st.set_page_config(page_title="Reports", page_icon="📄", layout="wide")

if not is_logged_in():
    st.warning("Please log in first.")
    st.stop()

user = current_user()
st.title("📄 Reports")
st.caption("Download PDF and Excel evaluation reports")

if is_student():
    st.subheader("📋 My Evaluation Reports")
    _, submissions = api_get("/students/my-submissions")
    evaluated = [s for s in (submissions or []) if s.get("status") == "evaluated"]

    if not evaluated:
        st.info("No evaluated submissions yet. Submit an answer sheet first.")
        st.stop()

    for sheet in evaluated:
        with st.expander(f"📄 Sheet #{sheet['id']} — Exam #{sheet['exam_id']} · {sheet['submitted_at'][:10]}"):
            col1, col2 = st.columns(2)
            col1.metric("Score", f"{sheet.get('total_score', 0)}/{sheet.get('max_score', 100)}")
            if sheet.get("total_score") and sheet.get("max_score"):
                pct = round(sheet["total_score"] / sheet["max_score"] * 100, 1)
                col2.metric("Percentage", f"{pct}%")

            _, evals = api_get(f"/students/submissions/{sheet['id']}/evaluations")
            _, plan = api_get("/students/learning-plan")

            col_pdf, col_excel = st.columns(2)
            with col_pdf:
                if st.button(f"📥 Download PDF Report", key=f"pdf_{sheet['id']}"):
                    try:
                        import sys
                        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        from modules.report_generator import generate_pdf_report

                        report_data = {
                            "student_name": user.get("name", ""),
                            "exam_title": f"Exam #{sheet['exam_id']}",
                            "total_score": sheet.get("total_score", 0),
                            "max_score": sheet.get("max_score", 100),
                            "plagiarism_score": sheet.get("plagiarism_score"),
                            "evaluations": evals if isinstance(evals, list) else [],
                            "learning_plan": plan[0] if isinstance(plan, list) and plan else None,
                        }
                        pdf_bytes = generate_pdf_report(report_data)
                        st.download_button(
                            "⬇️ Save PDF",
                            pdf_bytes,
                            file_name=f"evaluation_report_{sheet['id']}.pdf",
                            mime="application/pdf",
                            key=f"dl_pdf_{sheet['id']}",
                        )
                    except Exception as e:
                        st.error(f"PDF generation error: {e}")

elif is_faculty():
    st.subheader("📊 Batch Evaluation Reports")
    _, submissions = api_get("/faculty/submissions")

    if not isinstance(submissions, list) or not submissions:
        st.info("No submissions yet.")
        st.stop()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Submissions", len(submissions))
    evaluated = [s for s in submissions if s.get("status") == "evaluated"]
    col2.metric("Evaluated", len(evaluated))
    pending = [s for s in submissions if s.get("status") in ("pending", "processing")]
    col3.metric("Pending", len(pending))

    st.markdown("---")
    filter_status = st.multiselect(
        "Filter by Status",
        ["evaluated", "pending", "processing", "failed"],
        default=["evaluated"],
    )
    filtered = [s for s in submissions if s.get("status") in filter_status]
    st.info(f"{len(filtered)} submissions selected for report")

    col_pdf, col_excel = st.columns(2)

    with col_pdf:
        if st.button("📥 Generate PDF Batch Report", type="primary", use_container_width=True):
            if not filtered:
                st.warning("No submissions match the filter.")
            else:
                with st.spinner("Generating PDF…"):
                    try:
                        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        from modules.report_generator import generate_pdf_report

                        report_data = {
                            "student_name": "Batch Report",
                            "exam_title": "All Exams",
                            "total_score": 0,
                            "max_score": 100,
                            "evaluations": [],
                            "learning_plan": None,
                        }
                        pdf_bytes = generate_pdf_report(report_data)
                        st.download_button(
                            "⬇️ Save PDF",
                            pdf_bytes,
                            file_name="batch_evaluation_report.pdf",
                            mime="application/pdf",
                        )
                    except Exception as e:
                        st.error(f"PDF error: {e}")

    with col_excel:
        if st.button("📊 Generate Excel Report", type="primary", use_container_width=True):
            with st.spinner("Generating Excel…"):
                try:
                    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    from modules.report_generator import generate_excel_report

                    excel_data = [
                        {
                            "student_name": s.get("student_name", ""),
                            "email": s.get("student_email", ""),
                            "exam_title": s.get("exam_title", ""),
                            "total_score": s.get("total_score"),
                            "max_score": s.get("max_score"),
                            "plagiarism_score": s.get("plagiarism_score"),
                            "status": s.get("status", ""),
                            "submitted_at": s.get("submitted_at", ""),
                        }
                        for s in filtered
                    ]
                    excel_bytes = generate_excel_report(excel_data)
                    st.download_button(
                        "⬇️ Save Excel",
                        excel_bytes,
                        file_name="evaluation_report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                    st.success("Excel report ready!")
                except Exception as e:
                    st.error(f"Excel error: {e}")

    if filtered:
        st.subheader("Preview")
        import pandas as pd
        st.dataframe(
            pd.DataFrame(filtered)[
                ["student_name", "exam_title", "status", "total_score", "max_score", "submitted_at"]
            ],
            use_container_width=True,
        )
