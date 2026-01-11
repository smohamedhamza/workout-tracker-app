import streamlit as st
import db_utils
from datetime import datetime

st.set_page_config(page_title="Tracker", page_icon="📝")

if 'username' not in st.session_state:
    st.warning("Please login at Home first.")
    st.stop()

user = st.session_state.username

# --- MET CONSTANTS ---
METS = {
    "Walking (Slow)": 2.5,
    "Walking (Fast)": 4.5,
    "Jogging (Slow)": 7.0,
    "Running (Fast)": 11.0,
    "Sprinting": 15.0
}

# --- PROFILE CHECK ---
profile = db_utils.get_user_profile(user)
if not profile or not profile['weight_kg']:
    st.warning("⚠️ Please update your Weight in 'Profile' page to enable Calorie calculations!")
    weight = 70.0 # Fallback
else:
    weight = profile['weight_kg']

st.title("Log Activity")

type_ = st.radio("Activity Type", ["Cardio", "Strength"], horizontal=True)

with st.form("log_form"):
    c1, c2 = st.columns(2)
    with c1:
        date_ = st.date_input("Date")
    with c2:
        time_ = st.time_input("Time")
        
    activity_name = "Workout"
    cal_est = 0.0
    dist = 0.0
    dur = 0.0
    reps = 0
    
    if type_ == "Cardio":
        mode = st.selectbox("Mode", list(METS.keys()))
        dist = st.number_input("Distance (km)", min_value=0.1)
        dur = st.number_input("Duration (min)", min_value=1.0)
        
        # Calc logic: If duration is given, use it. 
        # Calories = MET * Weight(kg) * Time(hr)
        if dur > 0:
            cal_est = METS[mode] * weight * (dur / 60.0)
        activity_name = mode
        
    else:
        # Load Exercises
        ex_db = db_utils.get_exercises()
        ex_options = list(ex_db.keys()) + ["➕ Add New Exercise..."]
        
        chart_sel = st.selectbox("Exercise", ex_options)
        
        final_name = chart_sel
        cal_per_rep = 0.5
        
        if chart_sel == "➕ Add New Exercise...":
            c1, c2 = st.columns(2)
            with c1:
                new_name = st.text_input("New Exercise Name")
            with c2:
                new_cal = st.number_input("Calories per Rep", min_value=0.01, value=0.5, step=0.1)
            
            if new_name:
                final_name = new_name
                cal_per_rep = new_cal
                # We perform the DB add ONLY on submit to avoid partial saves, 
                # OR we verify here. Let's rely on submit logic or implicit add.
                # Actually, better to save it right away if it doesn't exist?
                # No, let's keep it clean. We'll use these values for the log.
                # But user asked to "store to data set".
                if st.form_submit_button("Save New Exercise to DB (Click before logging)"):
                    if db_utils.add_custom_exercise(new_name, new_cal, user):
                        st.success(f"Added {new_name}!")
                        st.rerun()
                    else:
                        st.error("Exists!")
        else:
            cal_per_rep = ex_db[chart_sel]
            
        reps = st.number_input("Reps", min_value=1, value=10)
        cal_est = reps * cal_per_rep
        activity_name = final_name
        
    st.info(f"🔥 Estimated Burn: **{int(cal_est)} kcal**")
    
    vis = st.checkbox("Post to Public Feed?", value=True)
    
    if st.form_submit_button("Log It"):
        ts = datetime.combine(date_, time_)
        conn = db_utils.sqlite3.connect(db_utils.DB_FILE)
        c = conn.cursor()
        c.execute("""
            INSERT INTO activity_log 
            (username, activity_type, activity_name, reps, distance_km, duration_min, calories, timestamp, is_public)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user, type_, activity_name, reps if type_=="Strength" else None, dist, dur, cal_est, ts, vis))
        conn.commit()
        conn.close()
        st.success("Logged!")
