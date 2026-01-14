import streamlit as st
import db_utils
from datetime import datetime
import pandas as pd
import time

# --- CONFIG ---
st.set_page_config(
    page_title="RepQuest Social",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize DB
if 'db_init' not in st.session_state:
    db_utils.init_db()
    st.session_state.db_init = True

# --- CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700&display=swap');
    html, body, [class*="css"]  { font-family: 'Outfit', sans-serif; }
    .stApp {
        background-color: #020617;
        color: #e2e8f0;
    }
    .kpi-card {
        background: rgba(255,255,255,0.05);
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .feed-item {
        background: rgba(30, 41, 59, 0.7);
        border-left: 4px solid #38bdf8;
        padding: 15px;
        margin-bottom: 10px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- AUTH FLOW ---
if 'username' not in st.session_state:
    st.title("🔥 RepQuest 2.0")
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        u = st.text_input("Username", key="l_u")
        p = st.text_input("Password", type="password", key="l_p")
        if st.button("Login"):
            if db_utils.login_user(u, p):
                st.session_state.username = u
                st.rerun()
            else:
                st.error("Invalid")
                
    with tab2:
        nu = st.text_input("New Username", key="r_u")
        np = st.text_input("New Password", type="password", key="r_p")
        if st.button("Sign Up"):
            if db_utils.register_user(nu, np):
                st.success("Created! Login now.")
            else:
                st.error("Taken!")
    st.stop()

# --- MAIN DASHBOARD ---
user = st.session_state.username
st.sidebar.title(f"Hi, {user} 👋")
if st.sidebar.button("Logout"):
    del st.session_state.username
    st.rerun()

# --- DASHBOARD STATS ---
stats = db_utils.get_user_stats(user)
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"<div class='kpi-card'><div style='font-size:2rem; font-weight:bold; color:#facc15'>🔥 {stats['weekly']}</div><div style='color:#94a3b8'>Weekly Calories</div></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='kpi-card'><div style='font-size:2rem; font-weight:bold; color:#f472b6'>📅 {stats['monthly']}</div><div style='color:#94a3b8'>Monthly Calories</div></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='kpi-card'><div style='font-size:2rem; font-weight:bold; color:#38bdf8'>⚡ {stats['total']}</div><div style='color:#94a3b8'>All Time Burn</div></div>", unsafe_allow_html=True)


st.markdown("<br>", unsafe_allow_html=True)

# --- ACTIVE QUESTS PREVIEW ---
conn = db_utils.sqlite3.connect(db_utils.DB_FILE)
my_quests = conn.execute("""
    SELECT q.name, q.target_count, COALESCE(SUM(w.reps), 0) as current
    FROM quests q
    LEFT JOIN workouts w ON q.id = w.quest_id
    WHERE q.username = ?
    GROUP BY q.id
""", (user,)).fetchall()
conn.close()

if my_quests:
    st.subheader("🎯 Active Quests")
    c_quests = st.columns(len(my_quests)) if len(my_quests) <= 3 else st.columns(3)
    
    for i, (qname, qtarget, qcurr) in enumerate(my_quests):
        pct = int((qcurr / qtarget) * 100)
        # Use a cycle for columns or list them? Let's use a horizontal scroller or just stack if too many.
        # Simple stack for now or simplified card.
        col = c_quests[i % 3] 
        with col:
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.05); padding:15px; border-radius:10px; border:1px solid rgba(255,255,255,0.1);">
                <div style="font-weight:bold; font-size:1.1rem;">{qname}</div>
                <div style="color:#38bdf8; font-size:0.9rem;">{qcurr} / {qtarget} ({pct}%)</div>
                <div style="height:4px; background:rgba(255,255,255,0.2); margin-top:5px; border-radius:2px;">
                    <div style="height:100%; width:{min(100, pct)}%; background:#22c55e; border-radius:2px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

st.title("Your Feed")

# Fetch Feed
conn = db_utils.sqlite3.connect(db_utils.DB_FILE)
# Need ID to delete
feed_df = pd.read_sql_query("""
    SELECT id, username, activity_type, activity_name, calories, timestamp, reps, distance_km 
    FROM activity_log 
    WHERE is_public = 1 OR username = ? 
    ORDER BY timestamp DESC LIMIT 20
""", conn, params=(user,))
conn.close()

if feed_df.empty:
    st.info("No activity yet. Go to 'Tracker' to log something!")
else:
    for _, row in feed_df.iterrows():
        is_me = row['username'] == user
        color = "#38bdf8" if is_me else "#a5b4fc"
        icon = "🏃" if row['activity_type'] == 'Cardio' else "💪"
        
        detail = ""
        if row['reps']: detail += f"{row['reps']} reps"
        if row['distance_km']: detail += f"{row['distance_km']} km"
        
        with st.container():
            # Use columns to put delete button on right
            if is_me:
                c_main, c_del = st.columns([6,1])
                with c_del:
                    if st.button("🗑️", key=f"del_{row['id']}", help="Delete Activity"):
                        db_utils.delete_activity(row['id'])
                        st.rerun()
            else:
                c_main = st.container()
                
            with c_main:
                st.markdown(f"""
                <div class="feed-item" style="border-color: {color}">
                    <div style="display:flex; justify-content:space-between;">
                        <small style="color:#94a3b8">{row['timestamp']} • {row['username']}</small>
                    </div>
                    <div style="font-size:1.1rem; font-weight:bold; margin-top:5px;">{icon} {row['activity_name']}</div>
                    <div style="display:flex; justify-content:space-between; margin-top:5px;">
                        <span>{detail}</span>
                        <span style="color:#fb7185; font-weight:bold;">{int(row['calories'])} kcal</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
