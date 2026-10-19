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
- Row Level Security protects each student's records.
- Keep attendease_data.json as a backup of your old local data.
"""

from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

import streamlit as st
import os
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

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_PUBLISHABLE_KEY"]
except (KeyError, FileNotFoundError):
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = (
        os.getenv("SUPABASE_PUBLISHABLE_KEY")
        or os.getenv("SUPABASE_KEY")
    )

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


def get_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)


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
                    st.session_state["ae_access_token"] = result.session.access_token
                    st.session_state["ae_refresh_token"] = result.session.refresh_token
                    st.session_state["ae_user_id"] = result.user.id
                    st.session_state["ae_user_email"] = result.user.email or email.strip()
                    st.session_state.pop("app_data", None)
                    st.rerun()
                st.error("Login did not return a session. Confirm your email, then try again.")
            except Exception as exc:
                st.error(f"Could not log in: {exc}")

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
                        st.session_state["ae_access_token"] = result.session.access_token
                        st.session_state["ae_refresh_token"] = result.session.refresh_token
                        st.session_state["ae_user_id"] = result.user.id
                        st.session_state["ae_user_email"] = result.user.email or email.strip()
                        st.success("Account created.")
                        st.rerun()
                    st.success("Account request submitted. Check your email to confirm the account, then log in.")
                except Exception as exc:
                    st.error(f"Could not create account: {exc}")

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
                    st.error(f"Could not request password reset: {exc}")


def current_supabase():
    client = st.session_state.get("supabase")
    if client is None:
        return None
    access = st.session_state.get("ae_access_token")
    refresh = st.session_state.get("ae_refresh_token")
    if access and refresh:
        try:
            client.auth.set_session(access, refresh)
        except Exception:
            st.session_state.pop("ae_access_token", None)
            st.session_state.pop("ae_refresh_token", None)
            st.session_state.pop("ae_user_id", None)
            return None
    return client


def load_data() -> dict[str, Any]:
    """Load only the signed-in user's rows. RLS remains the security boundary."""
    client = current_supabase()
    if client is None or not st.session_state.get("ae_user_id"):
        return starter_data()
    try:
        user_id = st.session_state["ae_user_id"]
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
        st.error(f"Could not load your cloud data: {exc}")
        return starter_data()


def save_data() -> None:
    """Reconcile this user's in-memory data with Supabase. RLS enforces ownership."""
    client = current_supabase()
    user_id = st.session_state.get("ae_user_id")
    if client is None or not user_id:
        st.error("You are not signed in. Your changes were not saved.")
        return
    data = st.session_state["app_data"]
    subjects = data.get("subjects", [])
    try:
        existing_subject_rows = client.table("subjects").select("id").eq("user_id", user_id).execute().data or []
        existing_lecture_rows = client.table("lectures").select("id").eq("user_id", user_id).execute().data or []
        subject_ids = {str(s["id"]) for s in subjects}
        lecture_ids = {str(l["id"]) for s in subjects for l in s.get("lectures", [])}

        # Delete removed lectures first, then removed subjects.
        for row in existing_lecture_rows:
            if str(row["id"]) not in lecture_ids:
                client.table("lectures").delete().eq("id", row["id"]).eq("user_id", user_id).execute()
        for row in existing_subject_rows:
            if str(row["id"]) not in subject_ids:
                client.table("subjects").delete().eq("id", row["id"]).eq("user_id", user_id).execute()

        for subject in subjects:
            client.table("subjects").upsert({
                "id": subject["id"], "user_id": user_id,
                "name": subject["name"], "teacher": subject.get("teacher", ""),
                "color": subject.get("color", "#6D5CE8"),
            }).execute()
            for lecture in subject.get("lectures", []):
                client.table("lectures").upsert({
                    "id": lecture["id"], "user_id": user_id,
                    "subject_id": subject["id"],
                    "lecture_date": lecture.get("date") or date.today().isoformat(),
                    "status": lecture.get("status") if lecture.get("status") in STATUSES else BLANK,
                    "topic": lecture.get("topic", ""),
                    "notes": lecture.get("notes", ""),
                }).execute()
        client.table("user_preferences").upsert({
            "user_id": user_id,
            "attendance_target": int(data.get("settings", {}).get("attendance_target", 75)),
        }).execute()
    except Exception as exc:
        st.error(f"Cloud save failed. Your changes may not have been saved: {exc}")


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
    st.markdown(f'<p class="ae-section-note">{subtitle}</p>', unsafe_allow_html=True)


def metric_card(label: str, value: str, note: str = "") -> None:
    """Render a small dashboard KPI card."""
    st.markdown(
        f"""
        <div class="ae-card">
            <div class="ae-card-label">{label}</div>
            <div class="ae-card-value">{value}</div>
            <div class="ae-card-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
        writer.writerow([row[1], row[0], row[2], row[3], row[4]])
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
    st.error("Supabase is not configured. Check SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in your .env file.")
    st.stop()

if not st.session_state.get("ae_user_id"):
    show_auth_screen()
    st.stop()

if "app_data" not in st.session_state:
    st.session_state["app_data"] = load_data()

app_data = st.session_state["app_data"]
subjects = app_data["subjects"]
target = int(app_data["settings"].get("attendance_target", 75))


# ---------------------------------------------------------------------------
# 6. SIDEBAR NAVIGATION
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="ae-brand">Attend<span>Ease</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="ae-subbrand">Your attendance, made simple.</div>', unsafe_allow_html=True)

    nav_options = ["Dashboard", "My Subjects", "Mark Attendance", "Reports", "Settings"]
    if "page_jump" in st.session_state:
        requested_page = st.session_state.pop("page_jump")
        if requested_page in nav_options:
            st.session_state["navigation_page"] = requested_page
    page = st.radio(
        "NAVIGATION",
        nav_options,
        key="navigation_page",
        label_visibility="visible",
    )

    st.divider()
    st.markdown("**Your semester at a glance**")
    all_stats = overall_stats(subjects)
    st.metric("Overall attendance", f'{all_stats["percentage"]:.1f}%')
    st.progress(min(1.0, max(0.0, float(all_stats["percentage"]) / 100)))
    st.caption(f'{len(subjects)} subject(s) · {all_stats["held"]} counted lecture(s)')
    st.caption(f'Signed in: {st.session_state.get("ae_user_email", "student")}')
    if st.button("Log out", use_container_width=True):
        try:
            current_supabase().auth.sign_out()
        except Exception:
            pass
        for key in ("ae_access_token", "ae_refresh_token", "ae_user_id", "ae_user_email", "app_data"):
            st.session_state.pop(key, None)
        st.rerun()
    st.caption("Cloud-saved to your private student account.")


# ---------------------------------------------------------------------------
# 7. DASHBOARD
# ---------------------------------------------------------------------------
if page == "Dashboard":
    today_label = date.today().strftime("%A, %d %B %Y")
    st.markdown(
        f"""
        <div class="ae-hero">
            <div class="ae-eyebrow">{today_label}</div>
            <h1>Stay on top of your attendance.</h1>
            <p>A clear view of your classes, your progress, and what it takes to stay above your target.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    all_stats = overall_stats(subjects)
    target = int(app_data["settings"].get("attendance_target", 75))
    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        metric_card("Overall attendance", f'{all_stats["percentage"]:.1f}%', "Across all counted lectures")
    with c2:
        metric_card("Classes attended", str(all_stats["present"]), "Marked Present")
    with c3:
        metric_card("Classes missed", str(all_stats["absent"]), "Marked Absent")
    with c4:
        metric_card("Active subjects", str(len(subjects)), "Subjects you're tracking")

    st.write("")
    left, right = st.columns([1.55, 1], gap="medium")
    with left:
        st.subheader("Subject overview")
        if not subjects:
            st.info("Your dashboard is ready. Add your first subject to start tracking attendance.")
            if st.button("＋ Add your first subject", type="primary"):
                st.session_state["page_jump"] = "My Subjects"
                st.rerun()
        else:
            for subject in subjects:
                stats = attendance_stats(subject)
                with st.container(border=True):
                    top1, top2 = st.columns([3, 1])
                    with top1:
                        st.markdown(f"**{subject['name']}**")
                        teacher = subject.get("teacher", "").strip()
                        st.caption(teacher if teacher else "No teacher added")
                    with top2:
                        st.markdown(
                            f'<div style="text-align:right;font-weight:800;font-size:1.15rem;color:#5141C9">{stats["percentage"]:.1f}%</div>',
                            unsafe_allow_html=True,
                        )
                    st.progress(min(1.0, float(stats["percentage"]) / 100))
                    st.caption(
                        f'{stats["present"]} present · {stats["absent"]} absent · '
                        f'{stats["held"]} counted lecture(s)'
                    )
                    if stats["held"] == 0:
                        st.caption("Mark a lecture to start calculating attendance.")
                    elif stats["percentage"] < target:
                        needed = classes_needed_to_target(
                            int(stats["present"]), int(stats["held"]), target
                        )
                        st.warning(
                            f"Below your {target}% target. "
                            + (f"Attend the next {needed} consecutive class(es) to recover." if needed >= 0 else "A perfect record is needed to reach this target.")
                        )
                    else:
                        st.success(f"You're at or above your {target}% target.")
    with right:
        st.subheader("Your target")
        st.markdown(
            f'<div class="ae-card"><div class="ae-card-label">Attendance goal</div>'
            f'<div class="ae-card-value">{target}%</div>'
            f'<div class="ae-card-note">Your personal minimum</div></div>',
            unsafe_allow_html=True,
        )
        st.write("")
        if all_stats["held"] == 0:
            st.info("Record your first lecture to unlock your overall attendance insights.")
        elif all_stats["percentage"] >= target:
            st.success("You're meeting your overall attendance target.")
            st.write(f'You have attended {all_stats["present"]} of {all_stats["held"]} counted lectures.')
        else:
            needed = classes_needed_to_target(
                int(all_stats["present"]), int(all_stats["held"]), target
            )
            if needed >= 0:
                st.warning(f"Attend the next **{needed} consecutive class(es)** to bring overall attendance to {target}%.")
            else:
                st.warning("A 100% target cannot be recovered after a missed class.")
        st.subheader("How AttendEase counts")
        st.caption("Present and Absent count as held lectures. Cancelled and Blank records are excluded from the attendance percentage.")

    st.write("")
    st.subheader("Quick actions")
    qa1, qa2, qa3 = st.columns(3)
    with qa1:
        if st.button("＋ Add subject", use_container_width=True):
            st.session_state["page_jump"] = "My Subjects"
            st.rerun()
    with qa2:
        if st.button("✓ Mark attendance", use_container_width=True):
            st.session_state["page_jump"] = "Mark Attendance"
            st.rerun()
    with qa3:
        if st.button("↗ View reports", use_container_width=True):
            st.session_state["page_jump"] = "Reports"
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
                    save_data()
                    st.success(f"Added {cleaned_name}.")
                    st.rerun()

    with manage_tab:
        if not subjects:
            st.info("No subjects yet. Use the Add a subject tab to create one.")
        else:
            for subject in list(subjects):
                with st.expander(
                    f'{subject["name"]}  ·  {len(subject.get("lectures", []))} record(s)',
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
                                save_data()
                                st.success("Subject updated.")
                                st.rerun()

                    st.caption("Deleting a subject also deletes its lecture history.")
                    confirm_key = f'confirm_delete_{subject["id"]}'
                    confirmed = st.checkbox("I understand — delete this subject", key=confirm_key)
                    if st.button("Delete subject", key=f'delete_{subject["id"]}', disabled=not confirmed):
                        st.session_state["app_data"]["subjects"] = [
                            s for s in subjects if s["id"] != subject["id"]
                        ]
                        save_data()
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
            st.markdown(
                f"""
                <div style="background:#FFFFFF;border:1px solid #ECEAF4;border-radius:14px;
                            padding:.8rem 1rem;display:flex;align-items:center;gap:.8rem">
                    <div style="width:42px;height:42px;border-radius:50%;background:#F0EDFF;
                                color:#5947D2;display:flex;align-items:center;justify-content:center;
                                font-weight:800">{initials or "S"}</div>
                    <div>
                        <div style="font-size:1rem;font-weight:700;color:#24223A">{subject["name"]}</div>
                        <div style="font-size:.76rem;color:#77758D">{teacher or "Attendance record"}</div>
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
                    save_data()
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
                                <div style="font-size:.83rem;font-weight:500;color:#24223A">{topic_text}</div>
                                <div style="font-size:.67rem;color:#77758D">{lecture_date_text}</div>
                            </div>
                            <div style="font-size:.78rem;font-weight:700;color:{status_color};white-space:nowrap">
                                {dot} &nbsp; {lecture.get("status", BLANK)}
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
                            save_data()
                            st.rerun()
                        if st.button("Delete lecture", key=f"inline_delete_{lecture['id']}", use_container_width=True):
                            subject["lectures"] = [
                                item for item in subject["lectures"]
                                if item["id"] != lecture["id"]
                            ]
                            save_data()
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
                st.markdown(f'### {selected_subject["name"]}')
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
                file_name=f'attendease_{selected_subject["name"].strip().replace(" ", "_")}.csv',
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
# 11. SETTINGS
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
            save_data()
            st.success(f"Attendance target set to {new_target}%.")
            st.rerun()

    st.divider()
    st.subheader("Your cloud data")
    st.write("Your subjects and lecture records are stored in Supabase and scoped to your signed-in student account.")
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
st.caption("AttendEase · Built for clarity, not confusion. Your records are stored in your private Supabase account.")
