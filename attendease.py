"""
AttendEase — personal attendance tracker
=========================================
Run:
    py -m pip install --upgrade streamlit
    py -m streamlit run attendease.py

A cloud-backed attendance tracker with individual student accounts.

Features
- Dashboard with attendance KPIs and subject overview.
- Add, edit, and delete subjects.
- Record attendance for individual lectures.
- Attendance calculations exclude cancelled and blank lectures.
- Target calculator showing how many future classes are needed.
- Per-subject lecture history and CSV export.
- Supabase email authentication and per-student cloud storage.
- Supabase Row Level Security migration is included for per-student ownership.
- Keep attendease_data.json as a backup of your old local data.
"""

from __future__ import annotations

import calendar as month_calendar
import csv
import copy
import html
import io
import json
import logging
import os
import re
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client


# ---------------------------------------------------------------------------
# 1. PAGE CONFIGURATION AND DESIGN
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AttendEase | Attendance, under control",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_DIR = Path(__file__).resolve().parent
DATA_FILE = APP_DIR / "attendease_data.json"  # Kept as a local backup; cloud data is authoritative.
load_dotenv(APP_DIR / ".env")
logger = logging.getLogger(__name__)

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_PUBLISHABLE_KEY = st.secrets["SUPABASE_PUBLISHABLE_KEY"]
except (KeyError, FileNotFoundError):
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY")

PRESENT = "Present"
ABSENT = "Absent"
CANCELLED = "Lecture cancelled"
BLANK = "Blank"
STATUSES = [PRESENT, ABSENT, CANCELLED, BLANK]
COUNTED_STATUSES = {PRESENT, ABSENT}

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');

    :root {
        --ae-purple: #6D5CE8;
        --ae-purple-dark: #5141C9;
        --ae-ink: #24223A;
        --ae-muted: #77758D;
        --ae-border: #ECEAF4;
        --ae-surface: #FFFFFF;
        --ae-bg: #F7F7FC;
    }
    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }
    .stApp { background: var(--ae-bg); }
    [data-testid="stHeader"] { background: rgba(247,247,252,0.92); }
    [data-testid="stSidebar"] {
        background: #FFFFFF;
        border-right: 1px solid var(--ae-border);
    }
    [data-testid="stSidebar"] > div { padding-top: 1.05rem; }
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        padding: 0.35rem 0.55rem;
        border-radius: 9px;
        font-size: 0.88rem;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
        background: #F0EDFF;
        color: #5947D2;
        font-weight: 700;
    }
    h1, h2, h3 {
        font-family: 'Manrope', sans-serif !important;
        color: var(--ae-ink);
        letter-spacing: -0.035em;
    }
    h1 { font-weight: 700 !important; font-size: clamp(1.75rem, 2.5vw, 2.25rem) !important; }
    h2 { font-size: 1.45rem !important; font-weight: 700 !important; }
    h3 { font-size: 1.08rem !important; font-weight: 700 !important; }
    p, label, .stMarkdown { color: #45435B; }
    [data-testid="stAppViewContainer"] .main .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2.25rem;
        max-width: 1500px;
    }
    .ae-brand {
        font-family: 'Manrope', sans-serif;
        font-size: 1.55rem;
        font-weight: 800;
        color: var(--ae-ink);
        letter-spacing: -0.06em;
        margin-bottom: 0.1rem;
    }
    .ae-brand span { color: var(--ae-purple); }
    .ae-subbrand {
        font-size: 0.78rem;
        color: var(--ae-muted);
        margin-bottom: 1.4rem;
    }
    .ae-eyebrow {
        text-transform: uppercase;
        font-size: 0.70rem;
        letter-spacing: 0.12em;
        font-weight: 700;
        color: var(--ae-muted);
        margin-bottom: 0.25rem;
    }
    .ae-hero {
        background: #FFFFFF;
        border: 1px solid var(--ae-border);
        border-radius: 15px;
        padding: 1.25rem 1.45rem;
        margin: 0.3rem 0 1rem 0;
    }
    .ae-hero h1 { font-size: clamp(1.65rem, 2.4vw, 2.1rem); margin: 0.1rem 0 0.35rem 0; }
    .ae-hero p { color: #77758D; margin: 0; max-width: 680px; }
    .ae-card {
        background: var(--ae-surface);
        border: 1px solid var(--ae-border);
        border-radius: 14px;
        padding: 0.9rem 1rem;
        min-height: 96px;
        box-shadow: none;
    }
    .ae-card-label { color: var(--ae-muted); font-size: 0.82rem; font-weight: 600; }
    .ae-card-value {
        color: var(--ae-ink);
        font-family: 'Manrope', sans-serif;
        font-size: 1.65rem;
        font-weight: 800;
        letter-spacing: -0.055em;
        margin-top: 0.32rem;
    }
    .ae-card-note { color: var(--ae-muted); font-size: 0.73rem; margin-top: 0.15rem; }
    .stAlert { border-radius: 10px; }
    .ae-section-note { color: var(--ae-muted); font-size: 0.88rem; margin-top: -0.5rem; }
    .ae-topbar {
        background: rgba(255,255,255,.9);
        border: 1px solid var(--ae-border);
        border-radius: 14px;
        padding: .45rem .7rem;
        margin-bottom: 1rem;
    }
    .ae-date-chip, .ae-profile-chip {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 2.55rem;
        border: 1px solid var(--ae-border);
        border-radius: 10px;
        background: #fff;
        color: var(--ae-ink);
        font-size: .76rem;
        font-weight: 700;
        padding: .35rem .65rem;
        white-space: nowrap;
    }
    .ae-profile-chip { gap: .5rem; justify-content: flex-start; }
    .ae-avatar {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 1.7rem;
        height: 1.7rem;
        border-radius: 50%;
        background: #EEEAFE;
        color: #5947D2;
        font-size: .72rem;
        font-weight: 800;
    }
    .ae-greeting { margin: .1rem 0 .15rem; color: var(--ae-ink); font-weight: 800; }
    .ae-greeting-note { color: var(--ae-muted); font-size: .86rem; margin-bottom: .85rem; }
    .ae-panel {
        background: #fff;
        border: 1px solid var(--ae-border);
        border-radius: 14px;
        padding: 1rem;
        min-height: 100%;
    }
    .ae-panel-title { color: var(--ae-ink); font-size: .98rem; font-weight: 800; margin: 0 0 .75rem; }
    .ae-overall-card {
        min-height: 155px;
        background: #fff;
        border: 1px solid var(--ae-border);
        border-radius: 14px;
        padding: .8rem;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: .55rem;
        text-align: center;
    }
    .ae-overall-label { align-self: flex-start; color: var(--ae-ink); font-size: .78rem; font-weight: 800; }
    .ae-donut {
        width: 88px;
        height: 88px;
        border-radius: 50%;
        display: grid;
        place-items: center;
        background: conic-gradient(#6D5CE8 var(--ae-pct), #ECEAF4 0);
    }
    .ae-donut-center {
        width: 70px;
        height: 70px;
        border-radius: 50%;
        background: #fff;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: var(--ae-ink);
        line-height: 1.05;
    }
    .ae-donut-value { font-family: 'Manrope', sans-serif; font-size: 1.15rem; font-weight: 800; }
    .ae-donut-note { color: var(--ae-muted); font-size: .54rem; margin-top: .2rem; }
    .ae-status-card {
        min-height: 155px;
        border: 1px solid var(--ae-border);
        border-radius: 14px;
        padding: .9rem;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .ae-status-label { color: var(--ae-muted); font-size: .78rem; font-weight: 700; }
    .ae-status-value { color: var(--ae-ink); font-family: 'Manrope', sans-serif; font-size: 1.65rem; font-weight: 800; margin-top: .55rem; }
    .ae-status-note { color: var(--ae-muted); font-size: .7rem; margin-top: .05rem; }
    .ae-status-present { background: #F0FAF6; border-color: #E0F2E9; }
    .ae-status-absent { background: #FFF3F2; border-color: #F6E4E2; }
    .ae-status-cancelled { background: #FFF8EE; border-color: #F5EAD8; }
    .ae-status-blank { background: #F3F6FF; border-color: #E2E8FA; }
    .ae-subject-line { margin-bottom: .8rem; }
    .ae-subject-name { color: var(--ae-ink); font-size: .8rem; font-weight: 700; }
    .ae-subject-percentage { color: var(--ae-ink); font-size: .74rem; font-weight: 800; text-align: right; }
    .ae-subject-track { height: 7px; margin-top: .35rem; border-radius: 99px; background: #ECEEF5; overflow: hidden; }
    .ae-subject-fill { height: 100%; border-radius: inherit; }
    .ae-low-alert {
        background: #FFF8F0;
        border: 1px solid #F5E8D8;
        border-radius: 12px;
        padding: .8rem 1rem;
        color: #6B5137;
        font-size: .82rem;
        margin: .9rem 0;
    }
    .ae-history-row {
        display: flex;
        align-items: center;
        gap: .8rem;
        background: #FBFBFE;
        border: 1px solid var(--ae-border);
        border-radius: 10px;
        padding: .65rem .75rem;
        margin-bottom: .4rem;
    }
    .ae-history-index { color: var(--ae-muted); font-size: .72rem; font-weight: 800; min-width: 24px; }
    .ae-history-main { flex: 1; min-width: 0; }
    .ae-history-title { color: var(--ae-ink); font-size: .8rem; font-weight: 700; overflow-wrap: anywhere; }
    .ae-history-subtitle { color: var(--ae-muted); font-size: .68rem; margin-top: .1rem; }
    .ae-history-status { font-size: .7rem; font-weight: 800; white-space: nowrap; }
    .ae-status-text-present { color: #168260; }
    .ae-status-text-absent { color: #C65358; }
    .ae-status-text-cancelled { color: #9B6B28; }
    .ae-status-text-blank { color: #77758D; }
    .ae-calendar-day {
        min-height: 76px;
        border: 1px solid var(--ae-border);
        border-radius: 9px;
        background: #fff;
        padding: .38rem;
        color: var(--ae-ink);
        font-size: .76rem;
    }
    .ae-calendar-muted { background: #F8F8FB; color: #AAA8B7; }
    .ae-calendar-count { color: #5947D2; font-size: .63rem; font-weight: 700; margin-top: .3rem; }
    .ae-calendar-empty { color: #A3A1AE; font-size: .63rem; margin-top: .3rem; }
    .ae-pill {
        display: inline-block; border-radius: 999px; padding: 0.22rem 0.62rem;
        background: #F0EDFF; color: #5947D2; font-size: 0.75rem; font-weight: 700;
    }
    div.stButton > button, div.stDownloadButton > button {
        border-radius: 11px;
        border: 1px solid #DED9FB;
        font-weight: 700;
        min-height: 2.65rem;
    }
    div.stButton > button[kind="primary"] {
        background: var(--ae-purple);
        border-color: var(--ae-purple);
        color: white;
    }
    div.stButton > button[kind="primary"]:hover {
        background: var(--ae-purple-dark);
        border-color: var(--ae-purple-dark);
        color: white;
    }
    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid var(--ae-border);
        border-radius: 15px;
        padding: 0.8rem 1rem;
    }
    div[data-testid="stProgressBar"] > div > div {
        background: var(--ae-purple);
    }
    .stTabs [data-baseweb="tab-list"] { gap: 0.4rem; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 9px 9px 0 0;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    hr { border-color: var(--ae-border); }
    @media (max-width: 700px) {
        .ae-hero { padding: 1.15rem; border-radius: 16px; }
        .ae-card { padding: 0.85rem; }
        .ae-card-value { font-size: 1.5rem; }
        .ae-status-card, .ae-overall-card { min-height: 125px; }
        .ae-calendar-day { min-height: 59px; padding: .25rem; font-size: .69rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# 2. AUTHENTICATION AND CLOUD DATA STORAGE
# ---------------------------------------------------------------------------
def starter_data() -> dict[str, Any]:
    return {"settings": {"attendance_target": 75}, "subjects": []}


class CloudDataLoadError(Exception):
    """Raised when the account's cloud data could not be loaded safely."""


def get_supabase():
    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)


def set_authenticated_user(user: Any, access_token: str, refresh_token: str, email: str) -> bool:
    """Keep pending session data only when the same account signs back in."""
    user_id = str(user.id)
    previous_owner = st.session_state.get("app_data_owner_id")
    if st.session_state.get("save_pending") and previous_owner not in (None, user_id):
        try:
            st.session_state["supabase"].auth.sign_out({"scope": "local"})
        except Exception as exc:
            logger.warning("Supabase sign-out after account mismatch failed (%s)", type(exc).__name__)
        st.error("Unsaved changes belong to another account. Sign back into that account and retry the save first.")
        return False
    if st.session_state.get("app_data_owner_id") != user_id:
        for key in ("app_data", "app_data_baseline", "save_pending"):
            st.session_state.pop(key, None)
    elif not st.session_state.get("save_pending"):
        st.session_state.pop("app_data", None)
        st.session_state.pop("app_data_baseline", None)
    st.session_state["ae_access_token"] = access_token
    st.session_state["ae_refresh_token"] = refresh_token
    st.session_state["ae_user_id"] = user_id
    st.session_state["ae_user_email"] = email
    st.session_state["app_data_owner_id"] = user_id
    return True


def show_auth_screen() -> None:
    st.markdown('<div class="ae-brand">Attend<span>Ease</span></div>', unsafe_allow_html=True)
    st.title("Your attendance. Your account.")
    st.write("Sign in to access your personal attendance records from your own account.")
    login_tab, signup_tab, reset_tab = st.tabs(["Log in", "Create account", "Reset password"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email address", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submit = st.form_submit_button("Log in", type="primary", use_container_width=True)
        if submit:
            try:
                result = st.session_state["supabase"].auth.sign_in_with_password(
                    {"email": email.strip(), "password": password}
                )
                if result.session:
                    authenticated = set_authenticated_user(
                        result.user,
                        result.session.access_token,
                        result.session.refresh_token,
                        result.user.email or email.strip(),
                    )
                    if authenticated:
                        st.rerun()
                else:
                    st.error("Login did not return a session. Confirm your email, then try again.")
            except Exception as exc:
                logger.warning("Supabase login failed (%s)", type(exc).__name__)
                st.error("Could not log in. Check your details and try again.")

    with signup_tab:
        with st.form("signup_form"):
            email = st.text_input("Email address", key="signup_email")
            password = st.text_input("Password (at least 8 characters)", type="password", key="signup_password")
            confirm = st.text_input("Confirm password", type="password", key="signup_confirm")
            submit = st.form_submit_button("Create account", type="primary", use_container_width=True)
        if submit:
            if not email.strip() or "@" not in email:
                st.error("Enter a valid email address.")
            elif len(password) < 8:
                st.error("Use a password with at least 8 characters.")
            elif password != confirm:
                st.error("The passwords do not match.")
            else:
                try:
                    result = st.session_state["supabase"].auth.sign_up(
                        {"email": email.strip(), "password": password}
                    )
                    if result.session and result.user:
                        authenticated = set_authenticated_user(
                            result.user,
                            result.session.access_token,
                            result.session.refresh_token,
                            result.user.email or email.strip(),
                        )
                        if authenticated:
                            st.success("Account created.")
                            st.rerun()
                    else:
                        st.success("Account request submitted. Check your email to confirm the account, then log in.")
                except Exception as exc:
                    logger.warning("Supabase sign-up failed (%s)", type(exc).__name__)
                    st.error("Could not create the account. Check the details and try again.")

    with reset_tab:
        with st.form("reset_password_form"):
            email = st.text_input("Account email", key="reset_email")
            submit = st.form_submit_button("Send reset link", use_container_width=True)
        if submit:
            if not email.strip():
                st.error("Enter your account email.")
            else:
                try:
                    st.session_state["supabase"].auth.reset_password_email(email.strip())
                    st.success("If the address is registered, a password-reset email will be sent.")
                except Exception as exc:
                    logger.warning("Supabase password reset request failed (%s)", type(exc).__name__)
                    st.error("Could not request a password reset. Try again later.")


def current_supabase():
    client = st.session_state.get("supabase")
    if client is None:
        return None
    access = st.session_state.get("ae_access_token")
    refresh = st.session_state.get("ae_refresh_token")
    if not access or not refresh or not st.session_state.get("ae_user_id"):
        for key in ("ae_access_token", "ae_refresh_token", "ae_user_id", "ae_user_email"):
            st.session_state.pop(key, None)
        return None
    try:
        # get_session refreshes expired tokens and keeps the rotated refresh token.
        # Restore from Streamlit state only when this client has no live session.
        session = client.auth.get_session()
        if session is None:
            auth_response = client.auth.set_session(access, refresh)
            session = getattr(auth_response, "session", None)
        session_user_id = getattr(getattr(session, "user", None), "id", None)
        if (
            session is None
            or not getattr(session, "access_token", None)
            or not getattr(session, "refresh_token", None)
            or str(session_user_id) != str(st.session_state["ae_user_id"])
        ):
            raise RuntimeError("Supabase session is missing or belongs to another account")
        st.session_state["ae_access_token"] = session.access_token
        st.session_state["ae_refresh_token"] = session.refresh_token
    except Exception as exc:
        logger.warning("Supabase session restoration failed (%s)", type(exc).__name__)
        for key in ("ae_access_token", "ae_refresh_token", "ae_user_id", "ae_user_email"):
            st.session_state.pop(key, None)
        return None
    return client


def load_data() -> dict[str, Any]:
    """Load only the signed-in user's rows. RLS remains the security boundary."""
    client = current_supabase()
    user_id = st.session_state.get("ae_user_id")
    if client is None or not user_id:
        raise CloudDataLoadError("A valid authenticated session is required.")
    try:
        subject_rows = client.table("subjects").select("*").eq("user_id", user_id).execute().data or []
        lecture_rows = client.table("lectures").select("*").eq("user_id", user_id).execute().data or []
        lectures_by_subject: dict[str, list[dict[str, Any]]] = {}
        for row in lecture_rows:
            lectures_by_subject.setdefault(str(row["subject_id"]), []).append({
                "id": str(row["id"]),
                "date": str(row.get("lecture_date") or date.today().isoformat()),
                "status": row.get("status") if row.get("status") in STATUSES else BLANK,
                "topic": row.get("topic") or "",
                "notes": row.get("notes") or "",
            })
        subjects = []
        for row in subject_rows:
            sid = str(row["id"])
            subjects.append({
                "id": sid,
                "name": row.get("name") or "Untitled subject",
                "teacher": row.get("teacher") or "",
                "color": row.get("color") or "#6D5CE8",
                "lectures": lectures_by_subject.get(sid, []),
            })
        prefs = client.table("user_preferences").select("attendance_target").eq("user_id", user_id).maybe_single().execute().data
        try:
            target = int((prefs or {}).get("attendance_target", 75))
        except (TypeError, ValueError):
            target = 75
        return {"settings": {"attendance_target": min(100, max(1, target))}, "subjects": subjects}
    except Exception as exc:
        logger.warning("Supabase data load failed (%s)", type(exc).__name__)
        raise CloudDataLoadError("Cloud data could not be loaded.") from None


def _subject_values(subject: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": subject["id"],
        "name": subject["name"],
        "teacher": subject.get("teacher", ""),
        "color": subject.get("color", "#6D5CE8"),
    }


def _lecture_values(subject_id: str, lecture: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": lecture["id"],
        "subject_id": subject_id,
        "lecture_date": lecture.get("date") or date.today().isoformat(),
        "status": lecture.get("status") if lecture.get("status") in STATUSES else BLANK,
        "topic": lecture.get("topic", ""),
        "notes": lecture.get("notes", ""),
    }


def _index_subjects(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(subject["id"]): subject for subject in data.get("subjects", [])}


def _index_lectures(data: dict[str, Any]) -> dict[str, tuple[str, dict[str, Any]]]:
    return {
        str(lecture["id"]): (str(subject["id"]), lecture)
        for subject in data.get("subjects", [])
        for lecture in subject.get("lectures", [])
    }


def save_data() -> bool:
    """Persist only edits made since this session's last successful cloud load/save."""
    client = current_supabase()
    user_id = st.session_state.get("ae_user_id")
    if client is None or not user_id:
        st.session_state["save_pending"] = True
        st.error("Your session expired. Sign in again before saving these changes.")
        return False
    baseline = st.session_state.get("app_data_baseline")
    if baseline is None:
        st.session_state["save_pending"] = True
        st.error("Your cloud data was not loaded safely. Reload the page before making changes.")
        return False

    data = st.session_state["app_data"]
    try:
        old_subjects = _index_subjects(baseline)
        new_subjects = _index_subjects(data)
        old_lectures = _index_lectures(baseline)
        new_lectures = _index_lectures(data)

        # Delete only rows this session previously loaded and the user explicitly removed.
        removed_subject_ids = old_subjects.keys() - new_subjects.keys()
        removed_lecture_ids = old_lectures.keys() - new_lectures.keys()
        for lecture_id in removed_lecture_ids:
            client.table("lectures").delete().eq("id", lecture_id).eq("user_id", user_id).execute()
        for subject_id in removed_subject_ids:
            # Include any lectures added in another tab since this session loaded the subject.
            client.table("lectures").delete().eq("subject_id", subject_id).eq("user_id", user_id).execute()
            client.table("subjects").delete().eq("id", subject_id).eq("user_id", user_id).execute()

        for subject_id, subject in new_subjects.items():
            values = _subject_values(subject)
            old_subject = old_subjects.get(subject_id)
            if old_subject is None or _subject_values(old_subject) != values:
                client.table("subjects").upsert({**values, "user_id": user_id}).execute()

        for lecture_id, (subject_id, lecture) in new_lectures.items():
            values = _lecture_values(subject_id, lecture)
            old_lecture = old_lectures.get(lecture_id)
            if old_lecture is None or (
                old_lecture[0] != subject_id
                or _lecture_values(old_lecture[0], old_lecture[1]) != values
            ):
                client.table("lectures").upsert({**values, "user_id": user_id}).execute()

        old_target = int(baseline.get("settings", {}).get("attendance_target", 75))
        new_target = int(data.get("settings", {}).get("attendance_target", 75))
        if old_target != new_target:
            client.table("user_preferences").upsert({
                "user_id": user_id,
                "attendance_target": new_target,
            }).execute()

        st.session_state["app_data_baseline"] = copy.deepcopy(data)
        st.session_state.pop("save_pending", None)
        return True
    except Exception as exc:
        logger.warning("Supabase data save failed (%s)", type(exc).__name__)
        st.session_state["save_pending"] = True
        st.error("Cloud save failed. Your changes are still in this session; retry the save before leaving.")
        return False


def new_id() -> str:
    """Generate a unique ID for each subject or lecture."""
    return str(uuid.uuid4())


def get_subject(subject_id: str) -> dict[str, Any] | None:
    return next(
        (s for s in st.session_state["app_data"]["subjects"] if s["id"] == subject_id),
        None,
    )


# ---------------------------------------------------------------------------
# 3. ATTENDANCE CALCULATIONS
# ---------------------------------------------------------------------------
def lecture_counts(subject: dict[str, Any]) -> dict[str, int]:
    """Count each attendance status for one subject."""
    counts = {status: 0 for status in STATUSES}
    for lecture in subject.get("lectures", []):
        status = lecture.get("status", BLANK)
        if status in counts:
            counts[status] += 1
    return counts


def attendance_stats(subject: dict[str, Any]) -> dict[str, float | int]:
    """
    Calculate attendance using only Present and Absent records as the denominator.
    Cancelled and Blank lectures do not affect the percentage.
    """
    counts = lecture_counts(subject)
    held = counts[PRESENT] + counts[ABSENT]
    percentage = (counts[PRESENT] / held * 100) if held else 0.0
    return {
        "present": counts[PRESENT],
        "absent": counts[ABSENT],
        "cancelled": counts[CANCELLED],
        "blank": counts[BLANK],
        "held": held,
        "percentage": percentage,
    }


def overall_stats(subjects: list[dict[str, Any]]) -> dict[str, float | int]:
    """Calculate overall attendance weighted by lectures, not by subject averages."""
    present = 0
    absent = 0
    cancelled = 0
    blank = 0
    for subject in subjects:
        stats = attendance_stats(subject)
        present += int(stats["present"])
        absent += int(stats["absent"])
        cancelled += int(stats["cancelled"])
        blank += int(stats["blank"])
    held = present + absent
    return {
        "present": present,
        "absent": absent,
        "cancelled": cancelled,
        "blank": blank,
        "held": held,
        "percentage": (present / held * 100) if held else 0.0,
    }


def weekly_attendance_trend(
    subjects: list[dict[str, Any]], week_count: int = 5, today: date | None = None
) -> pd.DataFrame:
    """Return a small, weighted attendance trend for the most recent full weeks."""
    today = today or date.today()
    this_week = today - timedelta(days=today.weekday())
    first_week = this_week - timedelta(weeks=week_count - 1)
    totals = [{"present": 0, "absent": 0} for _ in range(week_count)]

    for subject in subjects:
        for lecture in subject.get("lectures", []):
            status = lecture.get("status", BLANK)
            if status not in COUNTED_STATUSES:
                continue
            try:
                lecture_date = date.fromisoformat(str(lecture.get("date", "")))
            except ValueError:
                continue
            if lecture_date > today or lecture_date < first_week:
                continue
            week_index = (lecture_date - first_week).days // 7
            if 0 <= week_index < week_count:
                totals[week_index][status.casefold()] += 1

    percentages = []
    for bucket in totals:
        held = bucket["present"] + bucket["absent"]
        percentages.append((bucket["present"] / held * 100) if held else 0.0)
    labels = [f"Week {index + 1}" for index in range(week_count)]
    return pd.DataFrame({"Attendance": percentages}, index=labels)


def display_name_from_email(email: Any) -> str:
    """Use a readable first name from the signed-in email without rendering markup."""
    local_part = str(email or "").split("@", 1)[0]
    name_parts = [part for part in re.split(r"[._+-]+", local_part) if part.isalpha()]
    return name_parts[0].capitalize()[:24] if name_parts else "there"


def classes_needed_to_target(present: int, held: int, target: int) -> int:
    """Return future consecutive attended classes needed to reach a target percentage."""
    if held == 0:
        return 0 if target <= 0 else (1 if target <= 100 else 0)
    current = present / held * 100
    if current >= target:
        return 0
    # (present + n) / (held + n) >= target / 100
    numerator = target * held - 100 * present
    denominator = 100 - target
    if denominator <= 0:
        return -1  # A 100% target cannot be recovered after an absence.
    return max(0, (numerator + denominator - 1) // denominator)


def can_miss_more(present: int, held: int, target: int) -> int:
    """Return the maximum future absences possible while staying at/above target."""
    if held == 0:
        return 0
    allowed = (100 * present) // target - held if target > 0 else 0
    return max(0, allowed)


# ---------------------------------------------------------------------------
# 4. REUSABLE UI HELPERS
# ---------------------------------------------------------------------------
def page_heading(title: str, subtitle: str) -> None:
    """Render a consistent page title and supporting description."""
    st.title(title)
    st.markdown(
        f'<p class="ae-section-note">{html.escape(str(subtitle), quote=True)}</p>',
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, note: str = "") -> None:
    """Render a small dashboard KPI card."""
    safe_label = html.escape(str(label), quote=True)
    safe_value = html.escape(str(value), quote=True)
    safe_note = html.escape(str(note), quote=True)
    st.markdown(
        f"""
        <div class="ae-card">
            <div class="ae-card-label">{safe_label}</div>
            <div class="ae-card-value">{safe_value}</div>
            <div class="ae-card-note">{safe_note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def escape_markdown_text(value: Any) -> str:
    """Render user-provided labels as text instead of Markdown syntax."""
    escaped = html.escape(str(value), quote=False)
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|<>])", r"\\\1", escaped)


def safe_filename_component(value: Any) -> str:
    """Remove path and control characters from user-derived download names."""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(value)).strip(" .")
    return (cleaned[:80] or "subject")


def safe_csv_cell(value: Any) -> str:
    """Keep exported text from being interpreted as a spreadsheet formula."""
    text_value = "" if value is None else str(value)
    if text_value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + text_value
    return text_value


def make_csv(subject: dict[str, Any] | None = None) -> str:
    """Build a CSV export in memory for either one subject or all lecture records."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Subject", "Date", "Status", "Topic", "Notes"])
    subjects = [subject] if subject else st.session_state["app_data"]["subjects"]
    rows = []
    for item in subjects:
        for lecture in item.get("lectures", []):
            rows.append(
                (
                    lecture.get("date", ""),
                    item.get("name", ""),
                    lecture.get("status", BLANK),
                    lecture.get("topic", ""),
                    lecture.get("notes", ""),
                )
            )
    for row in sorted(rows):
        writer.writerow([safe_csv_cell(value) for value in (row[1], row[0], row[2], row[3], row[4])])
    return output.getvalue()


def subject_label(subject: dict[str, Any]) -> str:
    """Make a readable selectbox label with the subject attendance percentage."""
    stats = attendance_stats(subject)
    return f'{subject["name"]}  ·  {stats["percentage"]:.0f}%'


# ---------------------------------------------------------------------------
# 5. INITIALIZE APP STATE AND AUTHENTICATION
# ---------------------------------------------------------------------------
if "supabase" not in st.session_state:
    st.session_state["supabase"] = get_supabase()

if st.session_state["supabase"] is None:
    st.error("Supabase is not configured. Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in Streamlit secrets or .env.")
    st.stop()

if not st.session_state.get("ae_user_id"):
    if st.session_state.get("save_pending"):
        st.warning("Unsaved changes are held for the account that created them. Sign back into that account to retry.")
    show_auth_screen()
    st.stop()

if st.session_state.get("app_data_owner_id") not in (None, st.session_state["ae_user_id"]):
    for key in ("app_data", "app_data_baseline", "save_pending"):
        st.session_state.pop(key, None)

if "app_data" not in st.session_state:
    try:
        loaded_data = load_data()
    except CloudDataLoadError:
        st.error("Your cloud data could not be loaded. No changes are enabled until you reconnect and reload.")
        if st.button("Retry loading cloud data", key="retry_cloud_load"):
            st.rerun()
        st.stop()
    st.session_state["app_data"] = loaded_data
    st.session_state["app_data_baseline"] = copy.deepcopy(loaded_data)
    st.session_state["app_data_owner_id"] = st.session_state["ae_user_id"]
elif "app_data_baseline" not in st.session_state:
    st.session_state["app_data_baseline"] = copy.deepcopy(st.session_state["app_data"])
    st.session_state["app_data_owner_id"] = st.session_state["ae_user_id"]

if st.session_state.get("save_pending"):
    st.warning("Some changes have not been confirmed in Supabase. Retry the save before leaving this session.")
    if st.button("Retry saving pending changes", key="retry_pending_save"):
        if save_data():
            st.rerun()

app_data = st.session_state["app_data"]
subjects = app_data["subjects"]
target = int(app_data["settings"].get("attendance_target", 75))


# ---------------------------------------------------------------------------
# 6. SIDEBAR NAVIGATION
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="ae-brand">Attend<span>Ease</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="ae-subbrand">Your attendance, made simple.</div>', unsafe_allow_html=True)

    nav_options = ["Dashboard", "My Subjects", "Mark Attendance", "Reports", "Calendar", "Settings"]
    nav_labels = {
        "Dashboard": "⌂  Dashboard",
        "My Subjects": "▦  Subjects",
        "Mark Attendance": "◷  Attendance History",
        "Reports": "▤  Analytics",
        "Calendar": "▣  Calendar",
        "Settings": "⚙  Settings",
    }
    if "page_jump" in st.session_state:
        requested_page = st.session_state.pop("page_jump")
        if requested_page in nav_options:
            st.session_state["navigation_page"] = requested_page
    page = st.radio(
        "Navigation",
        nav_options,
        key="navigation_page",
        format_func=lambda value: nav_labels[value],
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown("**Your semester at a glance**")
    all_stats = overall_stats(subjects)
    st.metric("Overall attendance", f'{all_stats["percentage"]:.1f}%')
    st.progress(min(1.0, max(0.0, float(all_stats["percentage"]) / 100)))
    st.caption(f'{len(subjects)} subject(s) · {all_stats["held"]} counted lecture(s)')
    st.caption(f'Signed in: {escape_markdown_text(st.session_state.get("ae_user_email", "student"))}')
    if st.button("Log out", use_container_width=True):
        if st.session_state.get("save_pending"):
            st.error("Retry the pending save before logging out so you do not lose this session's changes.")
        else:
            try:
                client = current_supabase()
                if client is not None:
                    client.auth.sign_out({"scope": "local"})
            except Exception as exc:
                logger.warning("Supabase sign-out failed (%s)", type(exc).__name__)
            for key in (
                "ae_access_token", "ae_refresh_token", "ae_user_id", "ae_user_email",
                "app_data", "app_data_baseline", "app_data_owner_id", "save_pending",
            ):
                st.session_state.pop(key, None)
            st.rerun()
    st.caption("Saved to Supabase for this signed-in account.")


# ---------------------------------------------------------------------------
# 7. DASHBOARD
# ---------------------------------------------------------------------------
if page == "Dashboard":
    today = date.today()
    email = st.session_state.get("ae_user_email", "")
    display_name = display_name_from_email(email)
    initials = "".join(part[0] for part in re.split(r"[._+-]+", str(email).split("@", 1)[0]) if part)[:2].upper()
    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else ("Good afternoon" if hour < 18 else "Good evening")

    search_col, date_col, profile_col = st.columns([5, 1.4, 1.8], vertical_alignment="center")
    with search_col:
        dashboard_search = st.text_input(
            "Search subjects or lectures",
            placeholder="Search subjects, lectures...",
            label_visibility="collapsed",
            key="dashboard_search",
        ).strip().casefold()
    with date_col:
        st.markdown(
            f'<div class="ae-date-chip">▣ &nbsp; {html.escape(today.strftime("%a, %d %b %Y"), quote=True)}</div>',
            unsafe_allow_html=True,
        )
    with profile_col:
        st.markdown(
            f'<div class="ae-profile-chip"><span class="ae-avatar">{html.escape(initials or "S", quote=True)}</span>'
            f'<span>{html.escape(display_name, quote=True)}<br><small style="color:#77758D;font-weight:500">Student</small></span></div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        f'<h1 class="ae-greeting">{greeting}, {html.escape(display_name, quote=True)}!</h1>'
        "<div class=\"ae-greeting-note\">Here's your attendance overview.</div>",
        unsafe_allow_html=True,
    )

    all_stats = overall_stats(subjects)
    target = int(app_data["settings"].get("attendance_target", 75))
    c1, c2, c3, c4, c5 = st.columns([1.2, 1, 1, 1, 1], gap="small")
    pct = min(100.0, max(0.0, float(all_stats["percentage"])))
    with c1:
        st.markdown(
            f'<div class="ae-overall-card"><div class="ae-overall-label">Overall attendance</div>'
            f'<div class="ae-donut" style="--ae-pct:{pct:.1f}%"><div class="ae-donut-center">'
            f'<span class="ae-donut-value">{pct:.1f}%</span><span class="ae-donut-note">of counted lectures</span>'
            '</div></div></div>',
            unsafe_allow_html=True,
        )
    card_data = [
        (c2, "present", "Present", int(all_stats["present"])),
        (c3, "absent", "Absent", int(all_stats["absent"])),
        (c4, "cancelled", "Cancelled", int(all_stats["cancelled"])),
        (c5, "blank", "Unmarked", int(all_stats["blank"])),
    ]
    for column, style, label, value in card_data:
        with column:
            st.markdown(
                f'<div class="ae-status-card ae-status-{style}"><div class="ae-status-label">{label}</div>'
                f'<div class="ae-status-value">{value}</div><div class="ae-status-note">lectures</div></div>',
                unsafe_allow_html=True,
            )

    trend_col, subjects_col = st.columns([1.55, 1], gap="medium")
    with trend_col:
        with st.container(border=True):
            st.markdown('<div class="ae-panel-title">Attendance trend</div>', unsafe_allow_html=True)
            st.caption("Weekly attendance over the last five weeks")
            if all_stats["held"]:
                st.line_chart(weekly_attendance_trend(subjects), color="#6D5CE8", height=225)
            else:
                st.info("Your trend will appear after you mark a lecture as present or absent.")
    with subjects_col:
        with st.container(border=True):
            title_col, view_col = st.columns([2.5, 1], vertical_alignment="center")
            with title_col:
                st.markdown('<div class="ae-panel-title">Subject overview</div>', unsafe_allow_html=True)
            with view_col:
                if st.button("View all", key="dashboard_view_all_subjects"):
                    st.session_state["page_jump"] = "My Subjects"
                    st.rerun()
            matching_subjects = [
                subject for subject in subjects
                if not dashboard_search
                or dashboard_search in str(subject.get("name", "")).casefold()
                or any(dashboard_search in str(lecture.get("topic", "")).casefold() for lecture in subject.get("lectures", []))
            ]
            if not matching_subjects:
                st.info("No subjects or lectures match your search." if subjects else "Add a subject to start tracking.")
            for subject in matching_subjects[:6]:
                stats = attendance_stats(subject)
                subject_name = html.escape(str(subject.get("name", "Untitled subject")), quote=True)
                subject_pct = min(100.0, max(0.0, float(stats["percentage"])))
                raw_color = str(subject.get("color", "#6D5CE8"))
                accent = raw_color if re.fullmatch(r"#[0-9A-Fa-f]{6}", raw_color) else "#6D5CE8"
                st.markdown(
                    f'<div class="ae-subject-line"><div style="display:flex;justify-content:space-between;gap:.5rem">'
                    f'<span class="ae-subject-name">{subject_name}</span><span class="ae-subject-percentage">{subject_pct:.0f}%</span></div>'
                    f'<div class="ae-subject-track"><div class="ae-subject-fill" style="width:{subject_pct:.1f}%;background:{accent}"></div></div>'
                    f'<div class="ae-history-subtitle">{int(stats["present"])} present · {int(stats["held"])} counted</div></div>',
                    unsafe_allow_html=True,
                )
            if not subjects and st.button("＋ Add your first subject", type="primary", key="dashboard_add_first_subject"):
                st.session_state["page_jump"] = "My Subjects"
                st.rerun()

    below_target = [
        subject for subject in subjects
        if attendance_stats(subject)["held"] and attendance_stats(subject)["percentage"] < target
    ]
    if below_target:
        alert_col, action_col = st.columns([5, 1.25], vertical_alignment="center")
        with alert_col:
            st.markdown(
                f'<div class="ae-low-alert"><strong>{len(below_target)} subject(s) below your {target}% target</strong><br>'
                'Consider attending upcoming lectures to improve your record.</div>',
                unsafe_allow_html=True,
            )
        with action_col:
            if st.button("View subjects", key="dashboard_low_subjects"):
                st.session_state["page_jump"] = "My Subjects"
                st.rerun()

    with st.container(border=True):
        st.markdown('<div class="ae-panel-title">Lecture attendance</div>', unsafe_allow_html=True)
        st.caption("Latest records. Use Attendance History to add, update, or remove lectures.")
        lecture_rows = []
        for subject in subjects:
            subject_name = str(subject.get("name", "Untitled subject"))
            for lecture in subject.get("lectures", []):
                topic = str(lecture.get("topic", "")).strip()
                if dashboard_search and dashboard_search not in subject_name.casefold() and dashboard_search not in topic.casefold():
                    continue
                lecture_rows.append((str(lecture.get("date", "")), subject, lecture))
        lecture_rows.sort(key=lambda item: (item[0], str(item[2].get("id", ""))), reverse=True)
        status_styles = {
            PRESENT: ("present", "Present"),
            ABSENT: ("absent", "Absent"),
            CANCELLED: ("cancelled", "Cancelled"),
            BLANK: ("blank", "Unmarked"),
        }
        if not lecture_rows:
            st.info("No lecture records match your search. Add one from Attendance History.")
        for index, (date_value, subject, lecture) in enumerate(lecture_rows[:5], start=1):
            status_class, status_label = status_styles.get(lecture.get("status", BLANK), status_styles[BLANK])
            try:
                display_date = date.fromisoformat(date_value).strftime("%a, %d %b %Y")
            except ValueError:
                display_date = date_value or "Date not set"
            safe_subject = html.escape(str(subject.get("name", "Untitled subject")), quote=True)
            safe_topic = html.escape(str(lecture.get("topic", "")).strip() or f"Lecture {index:02d}", quote=True)
            safe_date = html.escape(display_date, quote=True)
            st.markdown(
                f'<div class="ae-history-row"><span class="ae-history-index">{index:02d}</span>'
                f'<div class="ae-history-main"><div class="ae-history-title">{safe_topic}</div>'
                f'<div class="ae-history-subtitle">{safe_subject} · {safe_date}</div></div>'
                f'<span class="ae-history-status ae-status-text-{status_class}">● &nbsp; {status_label}</span></div>',
                unsafe_allow_html=True,
            )
        if lecture_rows and st.button("Open attendance history", key="dashboard_open_history"):
            st.session_state["page_jump"] = "Mark Attendance"
            st.rerun()


# ---------------------------------------------------------------------------
# 8. SUBJECT MANAGEMENT
# ---------------------------------------------------------------------------
elif page == "My Subjects":
    page_heading("My Subjects", "Create and manage the subjects you want to track.")

    add_tab, manage_tab = st.tabs(["＋ Add a subject", "Manage subjects"])

    with add_tab:
        with st.form("add_subject_form", clear_on_submit=True):
            st.markdown("#### Subject details")
            name = st.text_input("Subject name *", placeholder="e.g. Data Structures")
            teacher = st.text_input("Teacher (optional)", placeholder="e.g. Dr. Sharma")
            color = st.selectbox(
                "Subject colour",
                ["Purple", "Blue", "Teal", "Orange", "Pink"],
                index=0,
            )
            color_map = {
                "Purple": "#6D5CE8",
                "Blue": "#3478F6",
                "Teal": "#169C91",
                "Orange": "#E58A35",
                "Pink": "#D9579A",
            }
            submitted = st.form_submit_button("Create subject", type="primary", use_container_width=True)
            if submitted:
                cleaned_name = name.strip()
                if not cleaned_name:
                    st.error("Enter a subject name first.")
                elif any(s["name"].strip().casefold() == cleaned_name.casefold() for s in subjects):
                    st.error("A subject with that name already exists.")
                else:
                    subjects.append(
                        {
                            "id": new_id(),
                            "name": cleaned_name,
                            "teacher": teacher.strip(),
                            "color": color_map[color],
                            "lectures": [],
                        }
                    )
                    if save_data():
                        st.success("Subject added.")
                        st.rerun()

    with manage_tab:
        if not subjects:
            st.info("No subjects yet. Use the Add a subject tab to create one.")
        else:
            for subject in list(subjects):
                with st.expander(
                    f'{escape_markdown_text(subject["name"])}  ·  {len(subject.get("lectures", []))} record(s)',
                    expanded=False,
                ):
                    with st.form(f'edit_subject_{subject["id"]}'):
                        edited_name = st.text_input("Subject name", value=subject["name"])
                        edited_teacher = st.text_input("Teacher", value=subject.get("teacher", ""))
                        save_subject = st.form_submit_button("Save changes", type="primary")
                        if save_subject:
                            cleaned_name = edited_name.strip()
                            duplicate = any(
                                s["id"] != subject["id"]
                                and s["name"].strip().casefold() == cleaned_name.casefold()
                                for s in subjects
                            )
                            if not cleaned_name:
                                st.error("Subject name cannot be empty.")
                            elif duplicate:
                                st.error("Another subject already uses that name.")
                            else:
                                subject["name"] = cleaned_name
                                subject["teacher"] = edited_teacher.strip()
                                if save_data():
                                    st.success("Subject updated.")
                                    st.rerun()

                    st.caption("Deleting a subject also deletes its lecture history.")
                    confirm_key = f'confirm_delete_{subject["id"]}'
                    confirmed = st.checkbox("I understand — delete this subject", key=confirm_key)
                    if st.button("Delete subject", key=f'delete_{subject["id"]}', disabled=not confirmed):
                        st.session_state["app_data"]["subjects"] = [
                            s for s in subjects if s["id"] != subject["id"]
                        ]
                        if save_data():
                            st.success("Subject and its records deleted.")
                            st.rerun()


# ---------------------------------------------------------------------------
# 9. MARK ATTENDANCE — DETAIL VIEW INSPIRED BY THE PROVIDED REFERENCE
# ---------------------------------------------------------------------------
elif page == "Mark Attendance":
    # This page intentionally uses a compact, record-oriented layout:
    # student/subject header, KPI cards, then lecture rows with inline status.
    st.markdown(
        """
        <div style="font-size:.78rem;color:#77758D;margin-bottom:1.15rem">
            My Subjects &nbsp; › &nbsp; Attendance
        </div>
        <div style="margin-bottom:1.1rem">
            <div style="font-size:1.8rem;font-weight:700;letter-spacing:-.04em;color:#24223A">
                Total lecture attendance
            </div>
            <div style="font-size:.84rem;color:#77758D;margin-top:.2rem">
                Track lecture attendance with a simple Present / Absent marker.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not subjects:
        st.info("Create a subject first. It will appear here as an attendance tracker.")
        if st.button("＋ Create your first subject", type="primary"):
            st.session_state["page_jump"] = "My Subjects"
            st.rerun()
    else:
        # Subject identity and subject picker share one compact header row.
        picker_col, identity_col = st.columns([1.0, 2.8], vertical_alignment="center")
        subject_options = {s["id"]: s for s in subjects}
        with picker_col:
            selected_id = st.selectbox(
                "Subject",
                options=list(subject_options.keys()),
                format_func=lambda key: subject_options[key]["name"],
                label_visibility="collapsed",
                key="attendance_subject_picker",
            )
        subject = subject_options[selected_id]
        with identity_col:
            initials = "".join(part[0] for part in subject["name"].split()[:2]).upper()
            teacher = subject.get("teacher", "").strip()
            safe_initials = html.escape(initials or "S", quote=True)
            safe_subject_name = html.escape(str(subject["name"]), quote=True)
            safe_teacher = html.escape(teacher or "Attendance record", quote=True)
            st.markdown(
                f"""
                <div style="background:#FFFFFF;border:1px solid #ECEAF4;border-radius:14px;
                            padding:.8rem 1rem;display:flex;align-items:center;gap:.8rem">
                    <div style="width:42px;height:42px;border-radius:50%;background:#F0EDFF;
                                color:#5947D2;display:flex;align-items:center;justify-content:center;
                                font-weight:800">{safe_initials}</div>
                    <div>
                        <div style="font-size:1rem;font-weight:700;color:#24223A">{safe_subject_name}</div>
                        <div style="font-size:.76rem;color:#77758D">{safe_teacher}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        stats = attendance_stats(subject)
        total_records = len(subject.get("lectures", []))
        st.write("")
        k1, k2, k3, k4 = st.columns(4, gap="small")
        with k1:
            st.markdown(
                f"""<div class="ae-card" style="background:#F0EDFF;border-color:#E1DBFF">
                <div class="ae-card-label" style="color:#5947D2">Total attendance rate</div>
                <div class="ae-card-value" style="color:#5947D2">{stats["percentage"]:.1f}%</div>
                <div class="ae-card-note">of counted lectures</div></div>""",
                unsafe_allow_html=True,
            )
        with k2:
            metric_card("Present", str(stats["present"]), "lecture(s)")
        with k3:
            metric_card("Absent", str(stats["absent"]), "lecture(s)")
        with k4:
            metric_card("Total lectures", str(total_records), "tracked")

        st.write("")
        st.markdown(
            """
            <div style="background:#FFFFFF;border:1px solid #ECEAF4;border-radius:15px;
                        padding:1rem 1rem .65rem 1rem">
                <div style="font-size:1.02rem;font-weight:700;color:#24223A">
                    Lecture attendance marker
                </div>
                <div style="font-size:.75rem;color:#77758D;margin-top:.2rem">
                    Present / Absent count toward attendance. Cancelled and blank lectures
                    are excluded from the total percentage.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Add lecture controls live above the list, but keep the record rows compact.
        with st.expander("＋ Add a lecture", expanded=total_records == 0):
            with st.form("quick_add_lecture_form", clear_on_submit=True):
                add_col1, add_col2, add_col3 = st.columns([1, 1.2, 2])
                with add_col1:
                    new_lecture_date = st.date_input("Date", value=date.today())
                with add_col2:
                    new_lecture_status = st.selectbox("Status", STATUSES, index=3)
                with add_col3:
                    new_lecture_topic = st.text_input("Lecture name / topic", placeholder="e.g. Lecture 01 · Arrays")
                new_lecture_notes = st.text_input("Notes (optional)")
                add_lecture_submit = st.form_submit_button("Add lecture", type="primary", use_container_width=True)
                if add_lecture_submit:
                    subject["lectures"].append(
                        {
                            "id": new_id(),
                            "date": new_lecture_date.isoformat(),
                            "status": new_lecture_status,
                            "topic": new_lecture_topic.strip(),
                            "notes": new_lecture_notes.strip(),
                            "created_at": datetime.now().isoformat(timespec="seconds"),
                        }
                    )
                    if save_data():
                        st.rerun()

        lectures = sorted(
            subject.get("lectures", []),
            key=lambda item: (item.get("date", ""), item.get("id", "")),
        )
        if not lectures:
            st.info("No lecture rows yet. Use “Add a lecture” to create the first one.")
        else:
            status_style = {
                PRESENT: ("#F0EDFF", "#5947D2", "●"),
                ABSENT: ("#FCEFED", "#C75B52", "●"),
                CANCELLED: ("#F7F8FB", "#7C8294", "●"),
                BLANK: ("#FFFFFF", "#77758D", "●"),
            }
            for index, lecture in enumerate(lectures, start=1):
                row_bg, status_color, dot = status_style.get(lecture.get("status", BLANK), status_style[BLANK])
                topic_text = lecture.get("topic", "").strip() or f"Lecture {index:02d}"
                lecture_date_text = lecture.get("date", "")
                safe_topic_text = html.escape(str(topic_text), quote=True)
                safe_lecture_date_text = html.escape(str(lecture_date_text), quote=True)
                safe_status_text = html.escape(str(lecture.get("status", BLANK)), quote=True)
                row_col, edit_col = st.columns([5.2, 1.2], vertical_alignment="center")
                with row_col:
                    st.markdown(
                        f"""
                        <div style="background:{row_bg};border:1px solid #E8E6F1;border-radius:11px;
                                    padding:.62rem .8rem;display:flex;align-items:center;gap:.8rem;
                                    min-height:42px">
                            <div style="font-size:.76rem;font-weight:700;color:#24223A;min-width:28px">
                                {index:02d}
                            </div>
                            <div style="flex:1">
                                <div style="font-size:.83rem;font-weight:500;color:#24223A">{safe_topic_text}</div>
                                <div style="font-size:.67rem;color:#77758D">{safe_lecture_date_text}</div>
                            </div>
                            <div style="font-size:.78rem;font-weight:700;color:{status_color};white-space:nowrap">
                                {dot} &nbsp; {safe_status_text}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with edit_col:
                    with st.popover("Edit status", use_container_width=True):
                        updated_status = st.selectbox(
                            "Attendance status",
                            STATUSES,
                            index=STATUSES.index(lecture.get("status", BLANK)),
                            key=f"inline_status_{lecture['id']}",
                        )
                        updated_date = st.date_input(
                            "Lecture date",
                            value=date.fromisoformat(lecture_date_text)
                            if lecture_date_text else date.today(),
                            key=f"inline_date_{lecture['id']}",
                        )
                        updated_topic = st.text_input(
                            "Lecture name",
                            value=lecture.get("topic", ""),
                            key=f"inline_topic_{lecture['id']}",
                        )
                        updated_notes = st.text_input(
                            "Notes",
                            value=lecture.get("notes", ""),
                            key=f"inline_notes_{lecture['id']}",
                        )
                        if st.button("Save changes", key=f"inline_save_{lecture['id']}", type="primary", use_container_width=True):
                            lecture.update(
                                {
                                    "status": updated_status,
                                    "date": updated_date.isoformat(),
                                    "topic": updated_topic.strip(),
                                    "notes": updated_notes.strip(),
                                }
                            )
                            if save_data():
                                st.rerun()
                        if st.button("Delete lecture", key=f"inline_delete_{lecture['id']}", use_container_width=True):
                            subject["lectures"] = [
                                item for item in subject["lectures"]
                                if item["id"] != lecture["id"]
                            ]
                            if save_data():
                                st.rerun()

        st.markdown(
            """
            <div style="border-top:1px solid #ECEAF4;margin-top:.8rem;padding-top:.7rem;
                        font-size:.73rem;color:#77758D">
                ⓘ Each lecture can be marked Present, Absent, Lecture cancelled, or left Blank.
            </div>
            """,
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# 10. REPORTS AND TARGET CALCULATOR
# ---------------------------------------------------------------------------
elif page == "Reports":
    page_heading("Reports & insights", "Understand your attendance and export your records.")

    if not subjects:
        st.info("Add subjects and record lectures to create your first report.")
    else:
        overall = overall_stats(subjects)
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Overall attendance", f'{overall["percentage"]:.1f}%')
        r2.metric("Present", int(overall["present"]))
        r3.metric("Absent", int(overall["absent"]))
        r4.metric("Counted lectures", int(overall["held"]))

        st.subheader("Subject comparison")
        report_rows = []
        for subject in subjects:
            stats = attendance_stats(subject)
            report_rows.append(
                {
                    "Subject": subject["name"],
                    "Teacher": subject.get("teacher", ""),
                    "Attendance": f'{stats["percentage"]:.1f}%',
                    "Present": stats["present"],
                    "Absent": stats["absent"],
                    "Cancelled": stats["cancelled"],
                    "Blank": stats["blank"],
                    "Counted lectures": stats["held"],
                }
            )
        st.dataframe(report_rows, use_container_width=True, hide_index=True)

        st.subheader("Subject report")
        selected_subject_id = st.selectbox(
            "Select a subject for detailed insights",
            options=[s["id"] for s in subjects],
            format_func=lambda key: get_subject(key)["name"] if get_subject(key) else "Deleted subject",
            key="report_subject",
        )
        selected_subject = get_subject(selected_subject_id)
        if selected_subject:
            stats = attendance_stats(selected_subject)
            left, right = st.columns(2, gap="large")
            with left:
                st.markdown(f'### {escape_markdown_text(selected_subject["name"])}')
                st.metric("Attendance percentage", f'{stats["percentage"]:.1f}%')
                st.progress(min(1.0, float(stats["percentage"]) / 100))
                st.caption(f'{stats["present"]} present out of {stats["held"]} counted lectures.')
                target = int(app_data["settings"].get("attendance_target", 75))
                if stats["held"] == 0:
                    st.info("No counted lectures yet.")
                elif stats["percentage"] >= target:
                    st.success(f"At or above your {target}% target.")
                else:
                    needed = classes_needed_to_target(
                        int(stats["present"]), int(stats["held"]), target
                    )
                    st.warning(
                        f"Attend the next {needed} consecutive class(es) to reach {target}%."
                        if needed >= 0
                        else "A perfect record is needed to reach a 100% target."
                    )
            with right:
                st.markdown("### Record counts")
                st.write(f'**Present:** {stats["present"]}')
                st.write(f'**Absent:** {stats["absent"]}')
                st.write(f'**Lecture cancelled:** {stats["cancelled"]}')
                st.write(f'**Blank:** {stats["blank"]}')

            st.download_button(
                "Download this subject's CSV",
                data=make_csv(selected_subject),
                file_name=f'attendease_{safe_filename_component(selected_subject["name"])}.csv',
                mime="text/csv",
                use_container_width=True,
            )

        st.divider()
        st.download_button(
            "Download all attendance records (CSV)",
            data=make_csv(),
            file_name=f'attendease_attendance_{date.today().isoformat()}.csv',
            mime="text/csv",
            type="primary",
            use_container_width=True,
        )

        st.caption("CSV files can be opened in Excel, Google Sheets, or LibreOffice Calc.")


# ---------------------------------------------------------------------------
# 11. CALENDAR
# ---------------------------------------------------------------------------
elif page == "Calendar":
    page_heading("Calendar", "Browse lecture dates and attendance status by month.")

    today = date.today()
    month_options = []
    for offset in range(-6, 7):
        month_index = today.year * 12 + (today.month - 1) + offset
        year, month_zero_based = divmod(month_index, 12)
        month_options.append(date(year, month_zero_based + 1, 1))
    selected_month = st.selectbox(
        "Month",
        month_options,
        index=6,
        format_func=lambda value: value.strftime("%B %Y"),
        key="calendar_month",
    )

    lectures_by_date: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for subject in subjects:
        for lecture in subject.get("lectures", []):
            try:
                lecture_day = date.fromisoformat(str(lecture.get("date", "")))
            except ValueError:
                continue
            lectures_by_date.setdefault(lecture_day.isoformat(), []).append((subject, lecture))

    month_stats = {status: 0 for status in STATUSES}
    month_records = []
    for day_key, day_records in lectures_by_date.items():
        if day_key.startswith(f"{selected_month.year:04d}-{selected_month.month:02d}-"):
            month_records.extend((day_key, subject, lecture) for subject, lecture in day_records)
            for _, lecture in day_records:
                status = lecture.get("status", BLANK)
                if status in month_stats:
                    month_stats[status] += 1

    month_cols = st.columns(4)
    month_cols[0].metric("Lectures this month", len(month_records))
    month_cols[1].metric("Present", month_stats[PRESENT])
    month_cols[2].metric("Absent", month_stats[ABSENT])
    month_cols[3].metric("Unmarked", month_stats[BLANK])

    weekday_cols = st.columns(7, gap="small")
    for column, weekday in zip(weekday_cols, ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")):
        with column:
            st.caption(weekday)

    for week in month_calendar.Calendar(firstweekday=0).monthdatescalendar(selected_month.year, selected_month.month):
        day_cols = st.columns(7, gap="small")
        for column, calendar_day in zip(day_cols, week):
            with column:
                is_current_month = calendar_day.month == selected_month.month
                day_records = lectures_by_date.get(calendar_day.isoformat(), []) if is_current_month else []
                cell_class = "ae-calendar-day" if is_current_month else "ae-calendar-day ae-calendar-muted"
                event_count = len(day_records)
                event_label = f'{event_count} lecture(s)' if event_count else "No lectures"
                event_class = "ae-calendar-count" if event_count else "ae-calendar-empty"
                st.markdown(
                    f'<div class="{cell_class}"><strong>{calendar_day.day}</strong>'
                    f'<div class="{event_class}">{event_label}</div></div>',
                    unsafe_allow_html=True,
                )

    st.subheader("Lectures this month")
    if not month_records:
        st.info("No lectures are recorded for this month. Add one from Attendance History.")
    else:
        month_records.sort(key=lambda item: (item[0], str(item[2].get("id", ""))))
        for day_key, subject, lecture in month_records:
            status_class, status_label = {
                PRESENT: ("present", "Present"),
                ABSENT: ("absent", "Absent"),
                CANCELLED: ("cancelled", "Cancelled"),
                BLANK: ("blank", "Unmarked"),
            }.get(lecture.get("status", BLANK), ("blank", "Unmarked"))
            safe_subject = html.escape(str(subject.get("name", "Untitled subject")), quote=True)
            topic = str(lecture.get("topic", "")).strip() or "Lecture"
            safe_topic = html.escape(topic, quote=True)
            safe_day = html.escape(date.fromisoformat(day_key).strftime("%A, %d %B"), quote=True)
            st.markdown(
                f'<div class="ae-history-row"><div class="ae-history-main">'
                f'<div class="ae-history-title">{safe_topic}</div>'
                f'<div class="ae-history-subtitle">{safe_subject} · {safe_day}</div></div>'
                f'<span class="ae-history-status ae-status-text-{status_class}">{status_label}</span></div>',
                unsafe_allow_html=True,
            )
        if st.button("Open attendance history", key="calendar_open_history"):
            st.session_state["page_jump"] = "Mark Attendance"
            st.rerun()


# 12. SETTINGS
# ---------------------------------------------------------------------------
elif page == "Settings":
    page_heading("Settings", "Set your attendance goal and manage your account data.")

    current_target = int(app_data["settings"].get("attendance_target", 75))
    st.subheader("Attendance target")
    st.write("Choose the minimum attendance percentage you want to maintain.")
    with st.form("target_settings_form"):
        new_target = st.slider(
            "Target percentage",
            min_value=1,
            max_value=100,
            value=current_target,
            step=1,
            format="%d%%",
        )
        save_target = st.form_submit_button("Save target", type="primary", use_container_width=True)
        if save_target:
            app_data["settings"]["attendance_target"] = int(new_target)
            if save_data():
                st.success(f"Attendance target set to {new_target}%.")
                st.rerun()

    st.divider()
    st.subheader("Your cloud data")
    st.write("Your subjects and lecture records are stored in Supabase. Database row policies must be applied to enforce account isolation.")
    st.caption("The old attendease_data.json file is not used as the live database. Keep it as a backup until you have verified your cloud records.")

    all_stats = overall_stats(subjects)
    st.subheader("Data summary")
    d1, d2, d3 = st.columns(3)
    d1.metric("Subjects", len(subjects))
    d2.metric("Lecture records", sum(len(s.get("lectures", [])) for s in subjects))
    d3.metric("Counted lectures", int(all_stats["held"]))

    st.divider()
    st.subheader("About AttendEase")
    st.markdown(
        """
        - **Individual accounts:** email authentication is handled by Supabase.
        - **Private records:** database Row Level Security should restrict records to their owner.
        - **Transparent calculations:** only Present and Absent count toward the percentage.
        - **Not an official record:** compare important totals with your college's official attendance system.
        """
    )


# ---------------------------------------------------------------------------
# 12. FOOTER
# ---------------------------------------------------------------------------
st.divider()
st.caption("AttendEase · Built for clarity, not confusion. Your records are stored in Supabase.")

