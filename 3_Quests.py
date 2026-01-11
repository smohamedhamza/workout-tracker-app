import streamlit as st
import db_utils
from datetime import datetime
import time

st.set_page_config(page_title="My Quests", page_icon="🎯")

if 'username' not in st.session_state:
    st.warning("Please login.")
    st.stop()
    
user = st.session_state.username

st.title("🎯 Active Quests")

# --- CREATE QUEST ---
with st.expander("➕ Create New Goal", expanded=False):
    with st.form("new_quest"):
        name = st.text_input("Quest Name (e.g. 1000 Pushups)")
        target = st.number_input("Target Count", min_value=1, value=100)
        
        st.write("### Deadline (Optional)")
        has_deadline = st.checkbox("Set a deadline?")
        c_date, c_time = st.columns(2)
        with c_date:
            deadline_date = st.date_input("Target Date")
        with c_time:
            deadline_time = st.time_input("Target Time", value=datetime.strptime("23:59", "%H:%M").time(), step=60)
            
        # Link to calorie DB for auto-logging
        exercises = db_utils.get_exercises()
        known_exercise = st.selectbox("Link to Exercise Type (for Calorie tracking)", ["(None / Custom)"] + list(exercises.keys()))
        
        if st.form_submit_button("Start Quest"):
            final_deadline = None
            if has_deadline:
                 final_deadline = datetime.combine(deadline_date, deadline_time).isoformat()
                 
            db_utils.create_quest(user, name, target, final_deadline)
            st.success("Quest Created!")
            time.sleep(0.5)
            st.rerun()

# --- VIEW QUESTS ---
conn = db_utils.sqlite3.connect(db_utils.DB_FILE)
quests = conn.execute("SELECT id, name, target_count, deadline FROM quests WHERE username = ? ORDER BY created_at DESC", (user,)).fetchall()
conn.close()

if not quests:
    st.info("No active quests. Create one above!")

for qid, qname, qtarget, qdeadline in quests:
    conn = db_utils.sqlite3.connect(db_utils.DB_FILE)
    # Get current sum
    curr = conn.execute("SELECT COALESCE(SUM(reps), 0) FROM workouts WHERE quest_id = ?", (qid,)).fetchone()[0]
    conn.close()
    
    pct = min(100, int((curr / qtarget) * 100))
    
    
    # Calculate Time Remaining
    time_text = ""
    if qdeadline:
        try:
            deadline_dt = datetime.fromisoformat(qdeadline)
            remaining = deadline_dt - datetime.now()
            if remaining.total_seconds() > 0:
                days = remaining.days
                hours = remaining.seconds // 3600
                time_text = f"⏳ {days}d {hours}h remaining"
            else:
                time_text = "⚠️ Expired"
        except:
            pass

    # UI Card
    st.markdown(f"""
    <div style="background: rgba(255,255,255,0.05); padding: 20px; border-radius: 15px; border-left: 5px solid #38bdf8; margin-bottom: 20px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h3 style="margin:0">{qname}</h3>
            <span style="color:#fb7185; font-weight:bold;">{time_text}</span>
        </div>
        <div style="margin: 15px 0;">
            <div style="background: rgba(255,255,255,0.1); height: 10px; border-radius: 5px; width: 100%;">
                 <div style="background: #38bdf8; height: 100%; border-radius: 5px; width: {pct}%"></div>
            </div>
            <div style="text-align:right; margin-top:5px; color:#94a3b8;">{curr} / {qtarget} reps ({pct}%)</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # --- ACTIONS TAB ---
    tab_log, tab_hist, tab_manage = st.tabs(["📝 Log Progress", "📜 History", "⚙️ Manage"])
    
    with tab_log:
        with st.form(f"qlog_{qid}"):
            c1, c2 = st.columns(2)
            with c1:
                reps = st.number_input("Reps Added", min_value=1, value=10, key=f"r_{qid}")
            with c2:
                # Link exercise for better calorie tracking
                ex_names = list(db_utils.get_exercises().keys())
                ex_linked = st.selectbox("Exercise Type", ["(Generic)"] + ex_names, key=f"ex_{qid}")
            
            with st.expander("🕒 Backdate"):
                log_date = st.date_input("Date", value=datetime.today(), key=f"ld_{qid}")
                log_time = st.time_input("Time", value=datetime.now().time(), key=f"lt_{qid}")
            
            if st.form_submit_button("Log Workout"):
                final_ts = datetime.combine(log_date, log_time)
                ex_name = ex_linked if ex_linked != "(Generic)" else None
                db_utils.log_quest_workout(user, qid, qname, reps, final_ts, ex_name)
                
                st.success("Logged!")
                time.sleep(0.5)
                st.rerun()

    with tab_hist:
        q_logs = db_utils.get_quest_logs(qid)
        if q_logs.empty:
            st.caption("No logs yet.")
        else:
            for _, row in q_logs.iterrows():
                c_a, c_b, c_d = st.columns([2, 3, 1])
                with c_a:
                    st.write(f"**+{row['reps']}**")
                with c_b:
                    st.caption(f"{row['timestamp']}")
                with c_d:
                    if st.button("🗑️", key=f"delq_{row['id']}"):
                        db_utils.delete_quest_workout(row['id'])
                        st.rerun()
                        
    with tab_manage:
        st.write("Danger Zone")
        if st.button("🗑️ Delete Entire Quest", key=f"del_all_{qid}", type="primary"):
            db_utils.delete_entire_quest(qid)
            st.warning(f"Deleted {qname}")
            time.sleep(1)
            st.rerun()
