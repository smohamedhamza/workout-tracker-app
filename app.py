import streamlit as st
import sqlite3
import time
import math
from datetime import datetime
import pandas as pd

# --- CONFIGURATION & SETUP ---
st.set_page_config(
    page_title="RepQuest",
    page_icon="💪",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- DATABASE FUNCTIONS ---
DB_FILE = "repquest.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Table for the High-Level Goals (Quests)
    try:
        c.execute("ALTER TABLE quests ADD COLUMN username TEXT")
    except sqlite3.OperationalError:
        pass 
    
    try:
        c.execute("ALTER TABLE quests ADD COLUMN deadline TIMESTAMP")
    except sqlite3.OperationalError:
        pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS quests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            name TEXT NOT NULL,
            target_count INTEGER NOT NULL,
            deadline TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Table for individual Workout Logs
    c.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quest_id INTEGER,
            workout_name TEXT DEFAULT 'Workout', 
            reps INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (quest_id) REFERENCES quests(id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()

def get_user_quests(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Filter by username
    c.execute("""
        SELECT q.id, q.name, q.target_count, q.deadline,
               COALESCE(SUM(w.reps), 0) as current_count
        FROM quests q
        LEFT JOIN workouts w ON q.id = w.quest_id
        WHERE q.username = ?
        GROUP BY q.id
        ORDER BY q.created_at DESC
    """, (username,))
    data = c.fetchall()
    conn.close()
    return data

def get_quest_history(quest_id):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        "SELECT id, reps, created_at FROM workouts WHERE quest_id = ? ORDER BY created_at DESC",
        conn,
        params=(quest_id,)
    )
    conn.close()
    return df

def create_quest(username, name, target, deadline=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT INTO quests (username, name, target_count, deadline) VALUES (?, ?, ?, ?)', (username, name, target, deadline))
    conn.commit()
    conn.close()

def add_workout(quest_id, reps, timestamp=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    if timestamp is None:
        timestamp = datetime.now()
        
    c.execute("INSERT INTO workouts (quest_id, workout_name, reps, created_at) VALUES (?, 'Logged Workout', ?, ?)", (quest_id, reps, timestamp))
    conn.commit()
    conn.close()

def delete_workout(workout_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM workouts WHERE id = ?', (workout_id,))
    conn.commit()
    conn.close()

def delete_quest(quest_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM quests WHERE id = ?', (quest_id,))
    c.execute('DELETE FROM workouts WHERE quest_id = ?', (quest_id,))
    conn.commit()
    conn.close()

# --- INITIALIZATION ---
if 'init_done' not in st.session_state:
    init_db()
    st.session_state.init_done = True

# --- CUSTOM CSS (PREMIUM AESTHETICS) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700&display=swap');

    /* Global Reset & Font */
    html, body, [class*="css"]  {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Background Gradient */
    .stApp {
        background-color: #020617;
        background-image: radial-gradient(at 0% 0%, hsla(253,16%,7%,1) 0, transparent 50%), 
                          radial-gradient(at 50% 100%, hsla(225,39%,30%,1) 0, transparent 50%);
        color: #e2e8f0;
    }

    /* Input Fields - PURE BLACK BACKGROUND */
    .stTextInput input, .stNumberInput input, .stDateInput input, .stTimeInput input {
        background-color: #000000 !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        color: white !important;
        border-radius: 12px !important;
        padding: 10px 15px !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #38bdf8 !important; # Sky 400
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.3) !important;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%) !important;
        color: black !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.6rem 2rem !important;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4) !important;
        transition: all 0.2s ease !important;
        width: 100%;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(59, 130, 246, 0.6) !important;
    }
    
    /* Delete Button (Small) */
    button[kind="secondary"] {
        background: transparent !important;
        border: 1px solid #ef4444 !important;
        color: #ef4444 !important;
    }
    
    /* Cards/Containers */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 2rem;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    
    /* Typography */
    h1 {
        font-weight: 700 !important;
        background: linear-gradient(to right, #ffffff, #94a3b8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem !important;
    }
    .kpi {
        font-size: 2.5rem;
        font-weight: 700;
        color: #38bdf8;
        text-shadow: 0 0 20px rgba(56, 189, 248, 0.5);
    }
    .countdown-text {
        font-family: 'Outfit', monospace;
        color: #fb7185; /* Rose */
        font-weight: bold;
    }
    .label {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #94a3b8;
    }
    
    /* Hide Default Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True)

# --- HELPER: CIRCULAR PROGRESS ---
def circular_progress(percentage, size=160, key_suffix=""):
    """Generates an SVG circular progress bar."""
    radius = 70
    circumference = 2 * math.pi * radius
    stroke_dashoffset = circumference - (percentage / 100) * circumference
    
    color = "#38bdf8" # Sky Blue
    if percentage >= 100:
        color = "#22c55e" # Green
        percentage = 100
        stroke_dashoffset = 0

    svg_code = f"""
    <div style="display: flex; justify-content: center; margin-bottom: 1rem;">
        <svg width="{size}" height="{size}" viewBox="0 0 200 200">
            <circle cx="100" cy="100" r="{radius}" stroke="rgba(255,255,255,0.1)" stroke-width="12" fill="none" />
            <circle cx="100" cy="100" r="{radius}" stroke="{color}" stroke-width="12" fill="none" stroke-linecap="round"
                style="stroke-dasharray: {circumference}; stroke-dashoffset: {stroke_dashoffset}; transition: stroke-dashoffset 1s ease-in-out;" />
            <text x="50%" y="50%" text-anchor="middle" dy=".3em" font-size="34" font-family="Outfit" font-weight="bold" fill="white">
                {int(percentage)}%
            </text>
        </svg>
    </div>
    """
    st.markdown(svg_code, unsafe_allow_html=True)

# --- HELPER: TIMEDELTA ---
def format_timedelta(deadline_str):
    if not deadline_str:
        return None
    try:
        deadline = datetime.fromisoformat(deadline_str)
        now = datetime.now()
        remaining = deadline - now
        
        if remaining.total_seconds() <= 0:
            return "Expired"
        
        days = remaining.days
        hours = remaining.seconds // 3600
        return f"{days}d {hours}h remaining"
    except:
        return None

# --- MAIN APP LOGIC ---

def main():
    st.markdown("<h1>REP<span style='color:#38bdf8'>QUEST</span></h1>", unsafe_allow_html=True)
    
    # --- LOGIN SYSTEM ---
    if 'username' not in st.session_state:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.write("### Identity Required")
        user_input = st.text_input("Enter Codename / Username")
        if st.button("Access Dashboard"):
            if user_input:
                st.session_state.username = user_input.strip()
                st.rerun()
            else:
                st.error("Identity required.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # --- LOGGED IN HEADER ---
    st.caption(f"Logged in as: **{st.session_state.username}**  |  [Logout]", unsafe_allow_html=True)
    if st.button("Logout", key="logout_btn", type="secondary"):
        del st.session_state.username
        st.rerun()

    # --- SETUP NEW QUEST (EXPANDER) ---
    with st.expander("➕ Start New Quest", expanded=False):
        with st.form("setup_form", clear_on_submit=True):
            st.write("### Define Your Target")
            name = st.text_input("Quest Name", placeholder="e.g. 5000 Pushups 2026")
            target = st.number_input("Total Target Count", min_value=1, value=1000, step=50)
            
            st.write("### Deadline (Optional)")
            has_deadline = st.checkbox("Set a deadline?")
            c_date, c_time = st.columns(2)
            with c_date:
                deadline_date = st.date_input("Target Date")
            with c_time:
                # step=60 allows minute precision selection
                deadline_time = st.time_input("Target Time", value=datetime.strptime("23:59", "%H:%M").time(), step=60)
            
            submitted = st.form_submit_button("Create Quest")
            
            if submitted:
                if name and target:
                    final_deadline = None
                    if has_deadline:
                        final_deadline = datetime.combine(deadline_date, deadline_time).isoformat()
                    
                    create_quest(st.session_state.username, name, target, final_deadline)
                    st.success(f"Added Quest: '{name}'!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Name and Target are required.")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- DISPLAY QUESTS (FILTERED BY USER) ---
    quests = get_user_quests(st.session_state.username)
    
    if not quests:
        st.info(f"Welcome {st.session_state.username}! You have no active quests. Start one above.")
    
    for quest in quests:
        quest_id, name, target_count, deadline, current_count = quest
        remaining = max(0, target_count - current_count)
        percentage = min(100, (current_count / target_count) * 100)
        
        # Calculate Time Remaining
        time_text = format_timedelta(deadline)
        
        # --- QUEST CARD ---
        container = st.container()
        
        # Header with Time
        header_html = f"""
        <div class="glass-card" style="margin-bottom: 3rem; border-left: 4px solid {'#22c55e' if percentage >= 100 else '#38bdf8'};">
            <h2 style="margin-top:0;">{name}</h2>
        """
        if time_text:
            color = "#fb7185" if "Expired" in time_text else "#cbd5e1"
            header_html += f'<div class="countdown-text" style="color:{color}">⏳ {time_text}</div>'
        
        header_html += "</div>"
        container.markdown(header_html, unsafe_allow_html=True)
        
        c1, c2 = container.columns([1, 1.5])
        
        with c1:
             circular_progress(percentage, size=150, key_suffix=quest_id)
        
        with c2:
            st.markdown(f"""
            <div style="text-align: left; margin-bottom: 20px;">
                <span class="label">PROGRESS</span><br>
                <div style="font-size: 1.2rem; margin-top:5px;">
                    <b style="color:#ffffff">{current_count}</b> <span style="color:#64748b">/ {target_count} reps</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if percentage < 100:
                # LOGGING FORM (WITH BACKDATING)
                with st.form(key=f"log_form_{quest_id}", clear_on_submit=False):
                    reps = st.number_input("Add Reps", min_value=1, value=10, step=1, key=f"reps_{quest_id}")
                    
                    with st.expander("🕒 Backdate / Custom Time"):
                        bd_date = st.date_input("Date", value=datetime.today(), key=f"bd_d_{quest_id}")
                        bd_time = st.time_input("Time", value=datetime.now().time(), step=60, key=f"bd_t_{quest_id}")
                    
                    if st.form_submit_button("Log Workout"):
                        # Construct timestamp
                        custom_timestamp = datetime.combine(bd_date, bd_time)
                        add_workout(quest_id, reps, custom_timestamp)
                        st.success("Logged!")
                        time.sleep(0.5)
                        st.rerun()
            else:
                 st.markdown("✅ **QUEST COMPLETED**", unsafe_allow_html=True)

        # --- MANAGE / HISTORY ---
        with container.expander("⚙️ Manage & History"):

            # HISTORY LOG
            st.markdown("#### 📜 History Log")
            history_df = get_quest_history(quest_id)
            if not history_df.empty:
                # Format for display
                history_df['created_at'] = pd.to_datetime(history_df['created_at'])
                
                # Render each row with a delete button
                for index, row in history_df.iterrows():
                    date_str = row['created_at'].strftime('%Y-%m-%d %H:%M')
                    reps_val = row['reps']
                    wk_id = row['id']
                    
                    hc1, hc2, hc3 = st.columns([2, 1, 0.5])
                    with hc1:
                        st.caption(f"{date_str}")
                    with hc2:
                        st.markdown(f"<span style='color:#38bdf8; font-weight:bold;'>+{reps_val} reps</span>", unsafe_allow_html=True)
                    with hc3:
                        if st.button("🗑️", key=f"del_wk_{wk_id}", help="Delete this entry"):
                            delete_workout(wk_id)
                            st.rerun()
                    st.markdown("<hr style='margin:0; border-color:rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
            else:
                st.write("No workouts logged yet.")
            
            st.markdown("---")
            
            # DELETE SEARCH
            st.markdown("#### ⚠️ Danger Zone")
            if st.button("Delete Entire Quest", key=f"del_quest_{quest_id}", type="secondary"):
                delete_quest(quest_id)
                st.rerun()
        
        container.markdown("---")

if __name__ == "__main__":
    main()
