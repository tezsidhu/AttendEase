"""
AttendEase — personal attendance tracker
=========================================
Run:
    py -m pip install --upgrade streamlit
    py -m streamlit run attendease.py

A polished local-first attendance tracker for students.

Features
- Dashboard with attendance KPIs and subject overview.
- Add, edit, and delete subjects.
- Record attendance for individual lectures.
- Attendance calculations exclude cancelled and blank lectures.
- Target calculator showing how many future classes are needed.
- Per-subject lecture history and CSV export.
- Local JSON persistence in attendease_data.json.

Limitations
- This is a personal prototype, not an official university record.
- Data is stored locally beside this Python file; it is not cloud-synced.
- Keep a backup of attendease_data.json if the records matter to you.
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
DATA_FILE = APP_DIR / "attendease_data.json"

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
# 2. DATA STORAGE AND VALIDATION
# ---------------------------------------------------------------------------
def starter_data() -> dict[str, Any]:
    """Create a fresh, valid data structure for a new installation."""
    return {
        "settings": {"attendance_target": 75},
        "subjects": [],
    }


def load_data() -> dict[str, Any]:
    """Load data from JSON and recover safely if the file is missing or invalid."""
    if not DATA_FILE.exists():
        return starter_data()

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError("The root of the data file must be an object.")

        settings = data.get("settings")
        if not isinstance(settings, dict):
            settings = {}
        try:
            target = int(settings.get("attendance_target", 75))
        except (TypeError, ValueError):
            target = 75
        data["settings"] = {"attendance_target": min(100, max(1, target))}

        subjects = data.get("subjects")
        if not isinstance(subjects, list):
            subjects = []

        # Repair malformed entries instead of letting one record break the app.
        cleaned_subjects = []
        for subject in subjects:
            if not isinstance(subject, dict):
                continue
            subject.setdefault("id", str(uuid.uuid4()))
            subject.setdefault("name", "Untitled subject")
            subject.setdefault("teacher", "")
            subject.setdefault("color", "#6D5CE8")
            subject.setdefault("lectures", [])
            if not isinstance(subject["lectures"], list):
                subject["lectures"] = []
            cleaned_lectures = []
            for lecture in subject["lectures"]:
                if not isinstance(lecture, dict):
                    continue
                if lecture.get("status") not in STATUSES:
                    lecture["status"] = BLANK
                lecture.setdefault("id", str(uuid.uuid4()))
                lecture.setdefault("date", date.today().isoformat())
                lecture.setdefault("topic", "")
                lecture.setdefault("notes", "")
                cleaned_lectures.append(lecture)
            subject["lectures"] = cleaned_lectures
            cleaned_subjects.append(subject)
        data["subjects"] = cleaned_subjects
        return data

    except (OSError, json.JSONDecodeError, ValueError):
        st.error(
            "AttendEase could not read **attendease_data.json**. "
            "Your existing file has not been overwritten. Rename or back it up, "
            "then refresh to start with an empty dataset."
        )
        return starter_data()


def save_data() -> None:
    """Save the current data safely by writing a temporary file before replacing."""
    temporary_file = DATA_FILE.with_suffix(".tmp")
    try:
        with temporary_file.open("w", encoding="utf-8") as file:
            json.dump(st.session_state["app_data"], file, indent=2, ensure_ascii=False)
        temporary_file.replace(DATA_FILE)
    except OSError as exc:
        st.error(f"Could not save your data: {exc}")


def new_id() -> str:
    """Generate a unique ID for each subject or lecture."""
    return str(uuid.uuid4())


def get_subject(subject_id: str) -> dict[str, Any] | None:
    """Find a subject by ID, returning None if it no longer exists."""
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
# 5. INITIALIZE APP STATE
# ---------------------------------------------------------------------------
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
    st.caption("Saved locally on this computer.")


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
    page_heading("Settings", "Set your attendance goal and manage your local data.")

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
    st.subheader("Your local data")
    st.write("AttendEase stores subjects and lecture records in a JSON file beside `attendease.py`.")
    st.code(str(DATA_FILE), language="text")
    st.caption("Back up this file periodically. Do not delete it unless you want to remove your saved records.")

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
        - **Local-first:** records stay in a JSON file on this computer.
        - **Transparent calculations:** only Present and Absent count toward the percentage.
        - **Not cloud-synced:** this prototype does not yet support accounts or sharing across devices.
        - **Not an official record:** compare important totals with your college's official attendance system.
        """
    )


# ---------------------------------------------------------------------------
# 12. FOOTER
# ---------------------------------------------------------------------------
st.divider()
st.caption("AttendEase · Built for clarity, not confusion. Your data is stored locally on this computer.")
