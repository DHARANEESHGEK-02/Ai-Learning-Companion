"""
API client for Streamlit → FastAPI communication.
All calls are server-side (Streamlit backend → FastAPI backend).
"""
import httpx
import streamlit as st
from typing import Any

BASE_URL = "http://localhost:8000"
TIMEOUT = 30.0


def get_headers() -> dict:
    token = st.session_state.get("token", "")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def api_get(path: str, params: dict | None = None) -> tuple[int, Any]:
    try:
        r = httpx.get(f"{BASE_URL}{path}", headers=get_headers(), params=params, timeout=TIMEOUT)
        return r.status_code, r.json() if r.content else {}
    except Exception as e:
        return 503, {"detail": str(e)}


def api_post(path: str, json: dict | None = None, data: dict | None = None, files: dict | None = None) -> tuple[int, Any]:
    try:
        r = httpx.post(
            f"{BASE_URL}{path}",
            headers=get_headers() if not files else {k: v for k, v in get_headers().items()},
            json=json,
            data=data,
            files=files,
            timeout=60.0,
        )
        return r.status_code, r.json() if r.content else {}
    except Exception as e:
        return 503, {"detail": str(e)}


def login(email: str, password: str) -> tuple[bool, str]:
    status, data = api_post("/auth/login", json={"email": email, "password": password})
    if status == 200:
        st.session_state["token"] = data["access_token"]
        st.session_state["user"] = data["user"]
        return True, "Login successful"
    return False, data.get("detail", "Login failed")


def register(name: str, email: str, password: str, role: str, department: str = "") -> tuple[bool, str]:
    payload = {"name": name, "email": email, "password": password, "role": role}
    if department:
        payload["department"] = department
    status, data = api_post("/auth/register", json=payload)
    if status == 200:
        st.session_state["token"] = data["access_token"]
        st.session_state["user"] = data["user"]
        return True, "Registration successful"
    return False, data.get("detail", "Registration failed")


def logout():
    for key in ["token", "user", "chat_session_id"]:
        st.session_state.pop(key, None)


def is_logged_in() -> bool:
    return "token" in st.session_state and "user" in st.session_state


def current_user() -> dict:
    return st.session_state.get("user", {})


def is_faculty() -> bool:
    return current_user().get("role") == "faculty"


def is_student() -> bool:
    return current_user().get("role") == "student"
