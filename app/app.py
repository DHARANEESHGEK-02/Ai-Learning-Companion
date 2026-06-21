"""
AI Learning Companion — Main Streamlit Entry Point
University-grade intelligent answer sheet evaluation platform
"""
import streamlit as st
from utils.api_client import login, register, is_logged_in, current_user, logout

st.set_page_config(
    page_title="AI Learning Companion",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar branding ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎓 AI Learning Companion")
    st.caption("University-Grade Evaluation Platform")
    st.markdown("---")

    if is_logged_in():
        user = current_user()
        role_badge = "👨‍🏫 Faculty" if user.get("role") == "faculty" else "👨‍🎓 Student"
        st.markdown(f"**{user.get('name', 'User')}**")
        st.caption(f"{role_badge} · {user.get('email', '')}")
        if user.get("department"):
            st.caption(f"📚 {user.get('department')}")
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            logout()
            st.rerun()

# ── Main content ──────────────────────────────────────────────────────────────
if is_logged_in():
    user = current_user()
    role = user.get("role", "student")

    st.title(f"Welcome back, {user.get('name', 'User')}! 👋")

    if role == "faculty":
        st.info("👨‍🏫 You are logged in as **Faculty**. Use the sidebar to navigate to dashboards, manage exams, and review evaluations.")
        col1, col2, col3 = st.columns(3)
        col1.metric("Role", "Faculty")
        col2.metric("Access", "Full Platform")
        col3.metric("Status", "Active")

        st.markdown("### Quick Navigation")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.page_link("pages/02_Faculty_Dashboard.py", label="📊 Faculty Dashboard", icon="📊")
        with c2:
            st.page_link("pages/05_Analytics.py", label="📈 Analytics", icon="📈")
        with c3:
            st.page_link("pages/06_Reports.py", label="📄 Reports", icon="📄")

    else:
        st.info("👨‍🎓 You are logged in as **Student**. Use the sidebar to navigate to your dashboard, submit assignments, and chat with the AI tutor.")
        col1, col2, col3 = st.columns(3)
        col1.metric("Role", "Student")
        col2.metric("Department", user.get("department", "N/A"))
        col3.metric("Status", "Active")

        st.markdown("### Quick Navigation")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.page_link("pages/01_Student_Dashboard.py", label="📊 My Dashboard", icon="📊")
        with c2:
            st.page_link("pages/03_Upload_Evaluate.py", label="📤 Submit Answer Sheet", icon="📤")
        with c3:
            st.page_link("pages/04_AI_Tutor.py", label="🤖 AI Tutor", icon="🤖")
        with c4:
            st.page_link("pages/06_Reports.py", label="📄 My Reports", icon="📄")

    st.markdown("---")
    st.markdown(
        "**AI Learning Companion** — Powered by Google Gemini · "
        "Built for university-grade evaluation"
    )

else:
    # ── Login / Register ───────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center; padding: 2rem 0 1rem 0;">
        <h1>🎓 AI Learning Companion</h1>
        <p style="font-size:1.1rem; color:#555;">
            University-Grade Intelligent Answer Sheet Evaluation Platform
        </p>
    </div>
    """, unsafe_allow_html=True)

    col_left, col_mid, col_right = st.columns([1, 2, 1])
    with col_mid:
        tab_login, tab_register = st.tabs(["🔐 Login", "📝 Register"])

        with tab_login:
            st.markdown("#### Sign in to your account")
            with st.form("login_form"):
                email = st.text_input("Email address", placeholder="you@university.edu")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

            if submitted:
                if not email or not password:
                    st.error("Please fill in all fields.")
                else:
                    with st.spinner("Signing in…"):
                        success, msg = login(email, password)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        with tab_register:
            st.markdown("#### Create a new account")
            with st.form("register_form"):
                name = st.text_input("Full Name", placeholder="Dr. Jane Smith")
                reg_email = st.text_input("Email", placeholder="you@university.edu")
                role = st.selectbox("Role", ["student", "faculty"])
                department = st.text_input("Department (optional)", placeholder="Computer Science")
                reg_pass = st.text_input("Password", type="password", key="reg_pw")
                confirm_pass = st.text_input("Confirm Password", type="password")
                reg_submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")

            if reg_submitted:
                if not name or not reg_email or not reg_pass:
                    st.error("Please fill in all required fields.")
                elif reg_pass != confirm_pass:
                    st.error("Passwords do not match.")
                else:
                    with st.spinner("Creating account…"):
                        success, msg = register(name, reg_email, reg_pass, role, department)
                    if success:
                        st.success(f"{msg} — Welcome, {name}!")
                        st.rerun()
                    else:
                        st.error(msg)

    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🤖 AI-Powered", "Gemini Vision")
    col2.metric("📝 OCR", "Multi-page PDF")
    col3.metric("📊 Evaluation", "Rubric-Based")
    col4.metric("🎯 Feedback", "Personalized")
