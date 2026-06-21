import streamlit as st
import sys
import os
import uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.api_client import is_logged_in, current_user, api_post, api_get

st.set_page_config(page_title="AI Tutor", page_icon="🤖", layout="wide")

if not is_logged_in():
    st.warning("Please log in first.")
    st.stop()

st.title("🤖 AI Tutor")
st.caption("Ask anything — powered by Gemini with RAG-enhanced context")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "chat_session_id" not in st.session_state:
    st.session_state.chat_session_id = str(uuid.uuid4())

# ── Sidebar controls ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🤖 Tutor Settings")
    _, subjects_resp = api_get("/faculty/subjects")
    subject_options = ["General"] + ([s["name"] for s in subjects_resp] if isinstance(subjects_resp, list) else [])
    selected_subject = st.selectbox("Subject Focus", subject_options)
    subject_val = None if selected_subject == "General" else selected_subject

    st.markdown("---")
    st.markdown("**Suggested Questions:**")
    suggestions = {
        "CS": ["Explain Big-O notation with examples", "What is dynamic programming?", "Compare sorting algorithms"],
        "Physics": ["Explain Newton's laws of motion", "What is quantum entanglement?", "Derive kinetic energy formula"],
        "Chemistry": ["Explain ionic vs covalent bonds", "What is Le Chatelier's principle?", "Explain electrochemistry"],
        "Biology": ["Explain DNA replication", "What is the difference between mitosis and meiosis?", "Explain enzyme kinetics"],
        "Maths": ["Explain the fundamental theorem of calculus", "What are eigenvalues and eigenvectors?", "Explain Bayes theorem"],
        "General": ["How do I improve my exam scores?", "What is the best study technique?", "Explain the Pomodoro technique"],
    }
    key = selected_subject if selected_subject in suggestions else "General"
    for suggestion in suggestions[key]:
        if st.button(f"💡 {suggestion[:40]}…" if len(suggestion) > 40 else f"💡 {suggestion}",
                     use_container_width=True, key=f"sug_{suggestion[:20]}"):
            st.session_state.pending_message = suggestion

    st.markdown("---")
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.chat_session_id = str(uuid.uuid4())
        st.rerun()

# ── Chat display ─────────────────────────────────────────────────────────────
st.markdown(f"**Session:** `{st.session_state.chat_session_id[:8]}…` · Subject: **{selected_subject}**")

chat_container = st.container(height=500)
with chat_container:
    if not st.session_state.chat_history:
        st.markdown(
            """
            <div style="text-align:center; padding:2rem; color:#888;">
                <h3>👋 Hello! I'm your AI Tutor</h3>
                <p>Ask me anything about your subjects, concepts, or how to improve your answers.</p>
                <p>I can help with CS, Physics, Chemistry, Biology, Maths, and more!</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.write(msg["content"])
            else:
                with st.chat_message("assistant", avatar="🤖"):
                    st.write(msg["content"])

# ── Input ─────────────────────────────────────────────────────────────────────
pending = st.session_state.pop("pending_message", None)
user_input = st.chat_input("Ask me anything…", key="chat_input")

message_to_send = pending or user_input

if message_to_send:
    st.session_state.chat_history.append({"role": "user", "content": message_to_send})

    with st.spinner("Thinking…"):
        status, resp = api_post("/students/chat", json={
            "message": message_to_send,
            "subject": subject_val,
            "session_id": st.session_state.chat_session_id,
        })

    if status == 200:
        ai_response = resp.get("response", "Sorry, I couldn't generate a response.")
        st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
    else:
        err = resp.get("detail", "Failed to get response.")
        st.session_state.chat_history.append({"role": "assistant", "content": f"⚠️ {err}"})

    st.rerun()
