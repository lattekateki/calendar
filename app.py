import streamlit as st
import calendar
import datetime
import json
import os
import time
import pymongo

@st.cache_resource
def init_db():
    try:
        if "MONGO_URI" in st.secrets:
            client = pymongo.MongoClient(st.secrets["MONGO_URI"])
            return client.calendar_app.events
    except Exception as e:
        print("DB connection error:", e)
    return None

events_col = init_db()

def t(th, en):
    return th if st.session_state.get("lang", "TH") == "TH" else en

# ══════════════════════════════════════════════════════════════
# Page Configuration
# ══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="📅 My Calendar",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════
# Schedule Data
# ══════════════════════════════════════════════════════════════

EXAM_DATES = {
    datetime.date(2026, 7, 26): {
        "code": "DADS7201",
        "name": "Social Network",
        "type": "Final Exam",
    },
    datetime.date(2026, 8, 1): {
        "code": "DADS7204",
        "name": "Business Forecasting",
        "type": "Final Exam",
    },
}

STUDY_PERIOD = (datetime.date(2026, 7, 25), datetime.date(2026, 7, 31))
HOME_PERIOD = (datetime.date(2026, 8, 2), datetime.date(2026, 8, 7))
SEM1_START = datetime.date(2026, 8, 8)
SEM1_FINAL_PERIOD = (datetime.date(2026, 12, 12), datetime.date(2026, 12, 25))

# Weekday index: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
SUMMER_2026_SCHEDULE = {
    5: [{"code": "DADS8711", "name": "DADS8711", "time": "ยังไม่ระบุเวลา"}],
    6: [{"code": "DADS7201", "name": "Social Network", "time": "ยังไม่ระบุเวลา"}],
}

SEM1_2027_SCHEDULE = {
    1: [
        {"code": "DADS6005", "name": "DADS6005", "time": "10:00 - 12:00"},
        {"code": "DADS7202", "name": "DADS7202", "time": "14:00 - 16:00"},
    ],
    3: [
        {"code": "DADS6004", "name": "DADS6004", "time": "10:00 - 12:00"},
    ],
    5: [
        {"code": "DADS6001", "name": "DADS6001", "time": "14:00 - 16:00"},
    ],
}

MONTHS = [
    "", t("มกราคม", "January"), t("กุมภาพันธ์", "February"), t("มีนาคม", "March"), 
    t("เมษายน", "April"), t("พฤษภาคม", "May"), t("มิถุนายน", "June"), 
    t("กรกฎาคม", "July"), t("สิงหาคม", "August"), t("กันยายน", "September"), 
    t("ตุลาคม", "October"), t("พฤศจิกายน", "November"), t("ธันวาคม", "December")
]
DAYS_SHORT = [t("จ.", "Mon"), t("อ.", "Tue"), t("พ.", "Wed"), t("พฤ.", "Thu"), t("ศ.", "Fri"), t("ส.", "Sat"), t("อา.", "Sun")]
DAYS_FULL = [t("จันทร์", "Monday"), t("อังคาร", "Tuesday"), t("พุธ", "Wednesday"), t("พฤหัสบดี", "Thursday"), t("ศุกร์", "Friday"), t("เสาร์", "Saturday"), t("อาทิตย์", "Sunday")]

# Status constants
EXAM = "exam"
FINAL_PERIOD = "final_period"
STUDY = "study"
HOME = "home"
CLASS = "class"
AVAILABLE = "available"
NO_DATA = "no_data"
PERSONAL = "personal"

# ══════════════════════════════════════════════════════════════
# Helper Functions
# ══════════════════════════════════════════════════════════════

EVENTS_FILE = "my_events.json"

def load_events():
    """Load personal events from MongoDB (fallback to JSON if no DB)."""
    data = {}
    if events_col is not None:
        try:
            for doc in events_col.find():
                data[doc["_id"]] = {"name": doc["name"], "updated_at": doc.get("updated_at", 0)}
            return data
        except Exception:
            pass
            
    # Fallback to local JSON
    if os.path.exists(EVENTS_FILE):
        try:
            with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            for k, v in d.items():
                if isinstance(v, str):
                    data[k] = {"name": v, "updated_at": time.time()}
                else:
                    data[k] = v
        except Exception:
            pass
    return data

def save_event(date_str, evt_data):
    """Save event to DB (or local JSON fallback)."""
    if events_col is not None:
        try:
            events_col.update_one(
                {"_id": date_str},
                {"$set": {"name": evt_data["name"], "updated_at": evt_data["updated_at"]}},
                upsert=True
            )
        except Exception:
            pass
    else:
        try:
            with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        data[date_str] = evt_data
        with open(EVENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def delete_event(date_str):
    """Delete event from DB (or local JSON fallback)."""
    if events_col is not None:
        try:
            events_col.delete_one({"_id": date_str})
        except Exception:
            pass
    else:
        try:
            with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if date_str in data:
                del data[date_str]
                with open(EVENTS_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

def get_semester(date):
    """Return which semester a date falls in."""
    if date < SEM1_START:
        return "summer_2026"
    return "sem1_2027"


def get_semester_label(date):
    """Return a human-readable semester label."""
    if date.month < 8:
        return t("Year 1 / Semester 3 — Summer 2026", "Year 1 / Semester 3 — Summer 2026")
    return t("Year 2 / Semester 1 — 2027", "Year 2 / Semester 1 — 2027")


def get_schedule(date):
    """Return the list of classes for a given date."""
    sem = get_semester(date)
    wd = date.weekday()
    if sem == "summer_2026":
        return SUMMER_2026_SCHEDULE.get(wd, [])
    return SEM1_2027_SCHEDULE.get(wd, [])


def get_status(date):
    """Determine the availability status for a date (priority ordered)."""
    if date > SEM1_FINAL_PERIOD[1]:
        return NO_DATA
    if date in EXAM_DATES:
        return EXAM
    if STUDY_PERIOD[0] <= date <= STUDY_PERIOD[1]:
        return STUDY
    if HOME_PERIOD[0] <= date <= HOME_PERIOD[1]:
        return HOME
    if SEM1_FINAL_PERIOD[0] <= date <= SEM1_FINAL_PERIOD[1]:
        return FINAL_PERIOD
        
    # Check if there is a personal event
    date_str = date.strftime("%Y-%m-%d")
    if date_str in st.session_state.get("personal_events", {}):
        return PERSONAL

    if get_schedule(date):
        return CLASS
    return AVAILABLE


STATUS_META = {
    EXAM:         {"label": t("📝 วันสอบ", "📝 Exam"),         "color": "#ef4444", "bg": "#fef2f2"},
    FINAL_PERIOD: {"label": t("📝 ช่วงสอบ Final", "📝 Final Period"),  "color": "#dc2626", "bg": "#fef2f2"},
    STUDY:        {"label": t("📖 อ่านหนังสือสอบ", "📖 Study"),    "color": "#f59e0b", "bg": "#fffbeb"},
    HOME:         {"label": t("🏠 กลับบ้าน", "🏠 Home"),      "color": "#8b5cf6", "bg": "#f5f3ff"},
    CLASS:        {"label": t("📚 มีเรียน", "📚 Class"),        "color": "#3b82f6", "bg": "#eff6ff"},
    PERSONAL:     {"label": t("📌 นัดส่วนตัว", "📌 Personal"),   "color": "#db2777", "bg": "#fdf2f8"},
    AVAILABLE:    {"label": t("✅ ยืดหยุ่นได้", "✅ Flexible"),           "color": "#10b981", "bg": "#ecfdf5"},
    NO_DATA:      {"label": "—",                 "color": "#94a3b8", "bg": "#f8fafc"},
}


def get_month_stats(year, month):
    """Count days by status for a given month."""
    cal = calendar.Calendar(firstweekday=0)
    stats = {AVAILABLE: 0, CLASS: 0, EXAM: 0, FINAL_PERIOD: 0, STUDY: 0, HOME: 0, PERSONAL: 0, NO_DATA: 0}
    for day in cal.itermonthdays(year, month):
        if day == 0:
            continue
        status = get_status(datetime.date(year, month, day))
        stats[status] += 1
    return stats


# ══════════════════════════════════════════════════════════════
# Custom CSS
# ══════════════════════════════════════════════════════════════

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@200;300;400;500;600;700&display=swap');

    /* ── Global ── */
    html, body, .stApp, .stMarkdown, p, li, td, th, label {
        font-family: 'Kanit', sans-serif !important;
    }
    
    /* Fix for Streamlit icons */
    .stIcon, .material-symbols-rounded {
        font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
    }


    /* ── Navigation Buttons ── */
    .stButton > button {
        height: 3.5rem !important;
        border-radius: 10px !important;
        transition: all 0.2s ease;
    }
    .stButton > button p {
        font-size: 1.5rem !important;
        font-weight: 600 !important;
    }

    /* ── Header ── */
    .main-header {
        text-align: center;
        padding: 1rem 0 0.5rem;
    }
    .main-header h1 {
        font-weight: 700;
        font-size: 2.8rem;
        color: var(--text-color);
        margin: 0;
        letter-spacing: -0.5px;
    }
    .main-header p {
        color: var(--text-color);
        opacity: 0.7;
        font-size: 1.15rem;
        font-weight: 400;
        margin: 0.25rem 0 0;
    }

    /* ── Month title ── */
    .month-title {
        font-size: 1.8rem;
        font-weight: 600;
        color: var(--text-color);
        text-align: center;
        line-height: 2;
    }

    /* ── Calendar table ── */
    .cal-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 5px;
        table-layout: fixed;
        max-width: 1200px;
        margin: 0 auto;
    }
    .cal-table th {
        padding: 12px 4px;
        text-align: center;
        font-weight: 500;
        font-size: 1.1rem;
        color: var(--text-color);
        opacity: 0.7;
    }
    .cal-cell {
        padding: 15px 10px;
        border-radius: 10px;
        min-height: 110px;
        vertical-align: top;
        transition: all 0.2s ease;
    }
    .cal-cell:not(.empty):hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 14px rgba(0,0,0,0.08);
    }
    .cal-cell.empty { background: transparent; }
    .cal-cell .day-num {
        font-weight: 600;
        font-size: 1.4rem;
        margin-bottom: 5px;
    }
    .cal-cell .day-label {
        font-size: 0.95rem;
        font-weight: 400;
        line-height: 1.3;
    }

    /* Status colours */
    .cal-cell.available { background: #ecfdf5; }
    .cal-cell.available .day-num  { color: #065f46; }
    .cal-cell.available .day-label { color: #10b981; }

    .cal-cell.class { background: #eff6ff; }
    .cal-cell.class .day-num  { color: #1e40af; }
    .cal-cell.class .day-label { color: #3b82f6; }

    .cal-cell.study { background: #fffbeb; }
    .cal-cell.study .day-num  { color: #92400e; }
    .cal-cell.study .day-label { color: #d97706; }

    .cal-cell.exam { background: #fef2f2; }
    .cal-cell.exam .day-num  { color: #991b1b; }
    .cal-cell.exam .day-label { color: #ef4444; }

    .cal-cell.final_period { background: #fef2f2; }
    .cal-cell.final_period .day-num  { color: #991b1b; }
    .cal-cell.final_period .day-label { color: #dc2626; }

    .cal-cell.home { background: #f5f3ff; }
    .cal-cell.home .day-num  { color: #5b21b6; }
    .cal-cell.home .day-label { color: #8b5cf6; }

    .cal-cell.personal { background: #fdf2f8; }
    .cal-cell.personal .day-num  { color: #be185d; }
    .cal-cell.personal .day-label { color: #db2777; }

    .cal-cell.no_data { background: #f8fafc; }
    .cal-cell.no_data .day-num  { color: #94a3b8; }
    .cal-cell.no_data .day-label { color: #cbd5e1; }

    .cal-cell.today {
        box-shadow: 0 0 0 2.5px #0ea5e9, 0 2px 8px rgba(14,165,233,0.18);
    }
    .cal-cell.past { opacity: 0.5; }

    /* ── Responsive Mobile ── */
    @media (max-width: 768px) {
        .cal-table th { font-size: 0.9rem; padding: 8px 2px; }
        .cal-cell { padding: 8px 4px; min-height: 80px; }
        .cal-cell .day-num { font-size: 1.1rem; }
        .cal-cell .day-label { font-size: 0.75rem; }
        .main-header h1 { font-size: 2.2rem; }
        .month-title { font-size: 1.4rem; }
        .stat-card { min-width: 75px; padding: 8px 10px; }
        .stat-card .stat-num { font-size: 1.3rem; }
    }

    /* ── Stats cards ── */
    .stats-row {
        display: flex;
        gap: 10px;
        justify-content: center;
        flex-wrap: wrap;
        margin: 0.8rem 0 0.6rem;
    }
    .stat-card {
        background: var(--background-color);
        border-radius: 10px;
        padding: 10px 20px;
        text-align: center;
        border: 1px solid var(--secondary-background-color);
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        min-width: 100px;
    }
    .stat-card .stat-num {
        font-size: 1.6rem;
        font-weight: 600;
    }
    .stat-card .stat-label {
        font-size: 0.72rem;
        color: var(--text-color);
        opacity: 0.7;
        font-weight: 300;
    }

    /* ── Detail card ── */
    .detail-card {
        background: var(--secondary-background-color);
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin: 0.75rem 0;
        border: none;
    }
    .detail-card h3 {
        margin: 0 0 0.5rem;
        color: var(--text-color);
        font-weight: 500;
        font-size: 1.05rem;
    }
    .detail-card p {
        margin: 0.2rem 0;
        color: var(--text-color);
        opacity: 0.8;
        font-size: 0.9rem;
        font-weight: 300;
    }

    /* ── Sidebar ── */
    .sidebar-title {
        font-weight: 500;
        font-size: 0.92rem;
        color: var(--text-color);
        opacity: 0.9;
        margin-bottom: 0.4rem;
        padding-bottom: 0.25rem;
        border-bottom: 1px solid var(--secondary-background-color);
    }
    .legend-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 5px 0;
        font-size: 0.82rem;
        font-weight: 300;
    }
    .legend-dot {
        width: 13px;
        height: 13px;
        border-radius: 4px;
        flex-shrink: 0;
    }
    .schedule-tbl {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.78rem;
    }
    .schedule-tbl th {
        padding: 5px 6px;
        text-align: left;
        color: var(--text-color);
        opacity: 0.8;
        font-weight: 400;
        border-bottom: 1px solid var(--secondary-background-color);
    }
    .schedule-tbl td {
        padding: 5px 6px;
        color: var(--text-color);
        opacity: 0.7;
        border-bottom: 1px solid var(--secondary-background-color);
        font-weight: 300;
    }

    .section-divider {
        border: none;
        border-top: 1px solid var(--secondary-background-color);
        margin: 1.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# Calendar HTML Builder
# ══════════════════════════════════════════════════════════════

def build_calendar_html(year, month):
    """Generate an HTML calendar grid for the given month."""
    today = datetime.date.today()
    cal = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdayscalendar(year, month)

    rows = ""
    for week in weeks:
        cells = ""
        for day in week:
            if day == 0:
                cells += '<td class="cal-cell empty"></td>'
                continue

            date = datetime.date(year, month, day)
            status = get_status(date)

            css_classes = [status]
            if date == today:
                css_classes.append("today")
            elif date < today:
                css_classes.append("past")

            # Build label text
            if status == EXAM:
                label = f'📝 {t("สอบ", "Exam:")} {EXAM_DATES[date]["code"]}'
            elif status == FINAL_PERIOD:
                label = t("📝 ช่วงสอบ Final", "📝 Final Period")
            elif status == STUDY:
                label = t("📖 อ่านหนังสือสอบ", "📖 Study")
            elif status == HOME:
                label = t("🏠 กลับบ้าน", "🏠 Home")
            elif status == PERSONAL:
                evt_data = st.session_state.personal_events.get(date.strftime("%Y-%m-%d"), {})
                evt_name = evt_data.get("name", "") if isinstance(evt_data, dict) else evt_data
                label = f"📌 {evt_name}"
            elif status == CLASS:
                codes = [c["code"] for c in get_schedule(date)]
                label = "📚 " + ", ".join(codes)
            elif status == NO_DATA or status == AVAILABLE:
                label = ""

            cls_str = " ".join(css_classes)
            cells += (
                f'<td class="cal-cell {cls_str}">'
                f'<div class="day-num">{day}</div>'
                f'<div class="day-label">{label}</div>'
                f"</td>"
            )
        rows += f"<tr>{cells}</tr>"

    header = "".join(f"<th>{d}</th>" for d in DAYS_SHORT)
    return f'<div style="overflow-x:auto;"><table class="cal-table"><tr>{header}</tr>{rows}</table></div>'


# ══════════════════════════════════════════════════════════════
# Session State
# ══════════════════════════════════════════════════════════════

if "cal_year" not in st.session_state:
    st.session_state.cal_year = datetime.date.today().year
if "cal_month" not in st.session_state:
    st.session_state.cal_month = datetime.date.today().month
if "personal_events" not in st.session_state:
    st.session_state.personal_events = load_events()
if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False

MIN_MONTH, MIN_YEAR = 7, 2026
MAX_MONTH, MAX_YEAR = 12, 2026

# Enforce bounds if state is out of sync
if (st.session_state.cal_year, st.session_state.cal_month) < (MIN_YEAR, MIN_MONTH):
    st.session_state.cal_year, st.session_state.cal_month = MIN_YEAR, MIN_MONTH
if (st.session_state.cal_year, st.session_state.cal_month) > (MAX_YEAR, MAX_MONTH):
    st.session_state.cal_year, st.session_state.cal_month = MAX_YEAR, MAX_MONTH


# ══════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════

with st.sidebar:
    st.radio(
        "🌐 Language / ภาษา",
        ["TH", "EN"],
        horizontal=True,
        key="lang",
    )
    st.divider()

    # ── Semester info ──
    st.markdown(f'<div class="sidebar-title">🎓 {t("ภาคเรียนปัจจุบัน", "Current Semester")}</div>', unsafe_allow_html=True)
    ref_date = datetime.date(st.session_state.cal_year, st.session_state.cal_month, 15)
    st.info(get_semester_label(ref_date))

    st.divider()

    # ── Weekly schedule ──
    st.markdown(f'<div class="sidebar-title">📖 {t("ตารางเรียนประจำสัปดาห์", "Weekly Class Schedule")}</div>', unsafe_allow_html=True)

    sem_choice = st.radio(
        t("เลือกเทอม", "Select Term"),
        ["Summer 2026", "Semester 1/2027"],
        horizontal=True,
        label_visibility="collapsed",
    )

    sched = SUMMER_2026_SCHEDULE if sem_choice == "Summer 2026" else SEM1_2027_SCHEDULE

    tbl_rows = ""
    for wd in sorted(sched.keys()):
        for cls in sched[wd]:
            time_text = t(cls["time"], "TBD") if cls["time"] == "ยังไม่ระบุเวลา" else cls["time"]
            tbl_rows += (
                f'<tr><td>{DAYS_FULL[wd]}</td>'
                f'<td>{cls["code"]}</td>'
                f'<td>{time_text}</td></tr>'
            )
    st.markdown(
        f'<table class="schedule-tbl">'
        f'<tr><th>{t("วัน", "Day")}</th><th>{t("วิชา", "Class")}</th><th>{t("เวลา", "Time")}</th></tr>'
        f"{tbl_rows}</table>",
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown(f'<div class="sidebar-title">📌 {t("วันสำคัญ", "Important Dates")}</div>', unsafe_allow_html=True)
    dates_text = t(
        """
- 📝 **26 ก.ค.** — สอบ Social Network
- 📖 **25–31 ก.ค.** — อ่านหนังสือสอบ
- 📝 **1 ส.ค.** — สอบ Business Forecasting
- 🏠 **2–7 ส.ค.** — กลับบ้าน
- 🎓 **8 ส.ค.** — เปิดเทอม Sem 1/2027
- 📝 **12–25 ธ.ค.** — สอบ Final Sem 1/2027
""",
        """
- 📝 **Jul 26** — Exam: Social Network
- 📖 **Jul 25–31** — Study Period
- 📝 **Aug 1** — Exam: Business Forecasting
- 🏠 **Aug 2–7** — Home
- 🎓 **Aug 8** — Semester 1/2027 Starts
- 📝 **Dec 12–25** — Final Exams Sem 1/2027
"""
    )
    st.markdown(dates_text)

    st.divider()

    st.markdown(f'<div class="sidebar-title">📰 {t("อัปเดตล่าสุด (News)", "Recent Updates (News)")}</div>', unsafe_allow_html=True)
    
    events_list = []
    for date_str, evt in st.session_state.personal_events.items():
        if isinstance(evt, dict):
            events_list.append({"date": date_str, "name": evt.get("name", ""), "updated_at": evt.get("updated_at", 0)})
        else:
            events_list.append({"date": date_str, "name": evt, "updated_at": 0})
            
    events_list.sort(key=lambda x: x["updated_at"], reverse=True)
    recent_events = events_list[:3]
    
    if recent_events:
        for ev in recent_events:
            date_obj = datetime.datetime.strptime(ev["date"], "%Y-%m-%d")
            m_name = MONTHS[date_obj.month]
            
            # Format time if recently updated
            updated = ev["updated_at"]
            if updated == 0:
                time_ago = t("ก่อนหน้านี้", "Earlier")
            else:
                diff = time.time() - updated
                if diff < 60:
                    time_ago = t("เมื่อกี้", "Just now")
                elif diff < 3600:
                    time_ago = t(f"{int(diff/60)} นาทีที่แล้ว", f"{int(diff/60)} mins ago")
                elif diff < 86400:
                    time_ago = t(f"{int(diff/3600)} ชั่วโมงที่แล้ว", f"{int(diff/3600)} hrs ago")
                else:
                    time_ago = t(f"{int(diff/86400)} วันที่แล้ว", f"{int(diff/86400)} days ago")
                    
            if st.session_state.get("lang", "TH") == "TH":
                date_text = f"{date_obj.day} {m_name}"
            else:
                date_text = f"{m_name} {date_obj.day}"
                
            st.markdown(f'<div style="font-size:0.9rem; margin-bottom:10px; line-height:1.4;">'
                        f'🔹 <strong>{ev["name"]}</strong> ({date_text})<br>'
                        f'<span style="color:#64748b; font-size:0.8rem;">🕒 {time_ago}</span>'
                        f'</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="color:#94a3b8; font-size:0.9rem;">{t("ยังไม่มีการอัปเดต", "No recent updates")}</div>', unsafe_allow_html=True)
    with st.expander(t("🔑 จัดการปฏิทิน (Admin)", "🔑 Manage (Admin)"), expanded=False):
        if st.session_state.admin_mode:
            st.success(t("เข้าสู่ระบบแอดมินแล้ว", "Admin mode active"))
            if st.button(t("ออกจากระบบ", "Logout"), use_container_width=True):
                st.session_state.admin_mode = False
                st.rerun()
        else:
            pwd = st.text_input(t("รหัสผ่าน", "Password"), type="password")
            if st.button(t("เข้าสู่ระบบ", "Login"), use_container_width=True):
                if pwd == "Taetae_14341":  
                    st.session_state.admin_mode = True
                    st.rerun()
                else:
                    st.error(t("รหัสผ่านไม่ถูกต้อง", "Incorrect password"))


# ══════════════════════════════════════════════════════════════
# Main Content
# ══════════════════════════════════════════════════════════════

# ── Header ──
st.markdown(
    '<div class="main-header">'
    "<h1>My Calendar</h1>"
    f"<p>{t('ตารางเรียนและเวลาที่ยืดหยุ่นได้', 'Class Schedule & Flexible Time')}</p>"
    "</div>",
    unsafe_allow_html=True,
)

# ── Month navigation ──

nav = st.columns([1.2, 0.5, 2.5, 0.5, 1.2])

with nav[1]:
    can_prev = (st.session_state.cal_year, st.session_state.cal_month) > (MIN_YEAR, MIN_MONTH)
    if st.button("◀", use_container_width=True, key="prev", disabled=not can_prev):
        m, y = st.session_state.cal_month, st.session_state.cal_year
        st.session_state.cal_month = 12 if m == 1 else m - 1
        st.session_state.cal_year = y - 1 if m == 1 else y
        st.rerun()

with nav[2]:
    st.markdown(
        f'<div class="month-title">'
        f'{MONTHS[st.session_state.cal_month]} {st.session_state.cal_year}'
        f"</div>",
        unsafe_allow_html=True,
    )

with nav[3]:
    can_next = (st.session_state.cal_year, st.session_state.cal_month) < (MAX_YEAR, MAX_MONTH)
    if st.button("▶", use_container_width=True, key="next", disabled=not can_next):
        m, y = st.session_state.cal_month, st.session_state.cal_year
        st.session_state.cal_month = 1 if m == 12 else m + 1
        st.session_state.cal_year = y + 1 if m == 12 else y
        st.rerun()

# ── Stats row ──
stats = get_month_stats(st.session_state.cal_year, st.session_state.cal_month)
cards_html = '<div class="stats-row">'
for key, label, color in [
    (AVAILABLE, t("วันที่", "Days"), "#10b981"),
    (CLASS, t("วันเรียน", "Classes"), "#3b82f6"),
    (EXAM, t("วันสอบ", "Exams"), "#ef4444"),
    (FINAL_PERIOD, t("ช่วงสอบ Final", "Final Period"), "#dc2626"),
    (STUDY, t("อ่านหนังสือสอบ", "Study"), "#f59e0b"),
    (HOME, t("กลับบ้าน", "Home"), "#8b5cf6"),
]:
    if stats[key] > 0:
        cards_html += (
            f'<div class="stat-card">'
            f'<div class="stat-num" style="color:{color}">{stats[key]}</div>'
            f'<div class="stat-label">{label}</div>'
            f"</div>"
        )
cards_html += "</div>"
st.markdown(cards_html, unsafe_allow_html=True)

# ── Calendar grid ──
st.markdown(
    build_calendar_html(st.session_state.cal_year, st.session_state.cal_month),
    unsafe_allow_html=True,
)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ── Date detail ──
st.markdown(f'### {t("ดูรายละเอียดวันที่", "Date Details")}')

selected = st.date_input(
    t("เลือกวันที่", "Select Date"),
    value=datetime.date.today(),
    label_visibility="collapsed",
)

if selected:
    status = get_status(selected)
    meta = STATUS_META[status]
    day_name = DAYS_FULL[selected.weekday()]
    month_name = MONTHS[selected.month]
    
    if st.session_state.get("lang", "TH") == "TH":
        header_text = f"{meta['label']} — {day_name}ที่ {selected.day} {month_name} {selected.year}"
    else:
        header_text = f"{meta['label']} — {day_name}, {month_name} {selected.day}, {selected.year}"

    body = ""
    if status == EXAM:
        info = EXAM_DATES[selected]
        body += f'<p>📝 <strong>{t("สอบ", "Exam:")} {info["type"]}</strong></p>'
        body += f'<p>{t("วิชา:", "Class:")} {info["code"]} — {info["name"]}</p>'
        body += f'<p style="color:#ef4444">❌ {t("ไม่ว่างตลอดวัน", "Not Available")}</p>'

    elif status == FINAL_PERIOD:
        body += f'<p>📝 {t("ช่วงสอบ Final — Semester 1/2027", "Final Exams — Semester 1/2027")}</p>'
        body += f'<p>{t("ช่วงวันที่ 12–25 ธันวาคม 2026", "Dec 12–25, 2026")}</p>'
        body += f'<p style="color:#ef4444">❌ {t("ไม่ว่าง", "Not Available")}</p>'

    elif status == STUDY:
        body += f'<p>📖 {t("ช่วงอ่านหนังสือสอบ", "Study Period")}</p>'
        body += f'<p>{t("เตรียมสอบ: DADS7204 Business Forecasting (1 ส.ค.)", "For: DADS7204 Business Forecasting (Aug 1)")}</p>'
        body += f'<p style="color:#d97706">❌ {t("ไม่ว่าง", "Not Available")}</p>'

    elif status == HOME:
        body += f'<p>🏠 {t("ช่วงกลับบ้าน", "Home Visit")}</p>'
        body += f'<p style="color:#8b5cf6">{t("ไม่อยู่ในพื้นที่", "Out of town")}</p>'

    elif status == CLASS:
        classes = get_schedule(selected)
        body += f'<p>📚 {t(f"มีเรียน {len(classes)} วิชา:", f"Have {len(classes)} class(es):")}</p>'
        for c in classes:
            time_text = t(c["time"], "TBD") if c["time"] == "ยังไม่ระบุเวลา" else c["time"]
            body += f'<p style="margin-left:1rem">• {c["code"]} — {t("เวลา", "Time")} {time_text}</p>'

        sem = get_semester(selected)
        if sem == "sem1_2027":
            body += (
                '<p style="color:#10b981;margin-top:8px">'
                f'✅ {t("ยืดหยุ่นได้ช่วงนอกเวลาเรียน", "Flexible outside class hours")}'
                "</p>"
            )
        else:
            body += (
                '<p style="color:#d97706;margin-top:8px">'
                f'⚠️ {t("เวลาเรียนยังไม่ระบุ", "Class time TBD")}'
                "</p>"
            )

    elif status == AVAILABLE:
        body += (
            '<p style="color:#10b981;font-size:1.05rem">'
            f'✅ <strong>{t("ยืดหยุ่นได้ตลอดวัน", "Flexible all day")}</strong>'
            "</p>"
        )

    elif status == PERSONAL:
        evt_data = st.session_state.personal_events.get(selected.strftime("%Y-%m-%d"), {})
        evt_name = evt_data.get("name", "") if isinstance(evt_data, dict) else evt_data
        body += f'<p style="color:#be185d;font-size:1.05rem">📌 <strong>{evt_name}</strong></p>'
        body += f'<p style="color:#db2777">❌ {t("ไม่ว่าง", "Not Available")}</p>'

    elif status == NO_DATA:
        body += f'<p style="color:#94a3b8">{t("ยังไม่มีข้อมูลตารางเรียนในช่วงนี้", "No schedule data available for this period")}</p>'

    st.markdown(
        f'<div class="detail-card"><h3>{header_text}</h3>{body}</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.admin_mode:
        st.markdown(f"#### {t('จัดการกิจกรรมส่วนตัว (Admin)', 'Manage Personal Event (Admin)')}")
        date_str = selected.strftime("%Y-%m-%d")
        
        with st.form("event_form"):
            evt_data = st.session_state.personal_events.get(date_str, {})
            evt_name_val = evt_data.get("name", "") if isinstance(evt_data, dict) else evt_data
            
            evt_name = st.text_input(
                t("ชื่อนัดหมาย/กิจกรรม", "Event Name"),
                value=evt_name_val
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button(t("💾 บันทึก", "💾 Save"), use_container_width=True):
                    if evt_name.strip():
                        st.session_state.personal_events[date_str] = {
                            "name": evt_name.strip(),
                            "updated_at": time.time()
                        }
                        save_event(date_str, st.session_state.personal_events[date_str])
                        st.success(t("บันทึกเรียบร้อย!", "Saved successfully!"))
                        st.rerun()
                    else:
                        st.error(t("กรุณากรอกชื่อกิจกรรม", "Please enter event name"))
            with col2:
                if date_str in st.session_state.personal_events:
                    if st.form_submit_button(t("🗑️ ลบกิจกรรมนี้", "🗑️ Delete"), use_container_width=True):
                        del st.session_state.personal_events[date_str]
                        delete_event(date_str)
                        st.success(t("ลบเรียบร้อย!", "Deleted successfully!"))
                        st.rerun()

# ── Footer ──
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
