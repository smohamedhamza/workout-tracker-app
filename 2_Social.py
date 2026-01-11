import streamlit as st
import db_utils
import pandas as pd

st.set_page_config(page_title="Community", page_icon="🌍")

if 'username' not in st.session_state:
    st.stop()
    
user = st.session_state.username

st.title("Profile & Community")

# --- PROFILE EDITOR ---
with st.expander("👤 Edit My Profile", expanded=True):
    curr = db_utils.get_user_profile(user)
    with st.form("prof_form"):
        h = st.number_input("Height (cm)", value=curr['height_cm'] if curr and curr['height_cm'] else 170.0)
        w = st.number_input("Weight (kg)", value=curr['weight_kg'] if curr and curr['weight_kg'] else 70.0)
        b = st.text_area("Bio", value=curr['bio'] if curr and curr['bio'] else "Ready to run!")
        
        if st.form_submit_button("Save Profile"):
            db_utils.update_profile(user, h, w, b)
            st.success("Updated!")

# --- SEARCH USERS ---
st.markdown("### Find Athletes")
conn = db_utils.sqlite3.connect(db_utils.DB_FILE)
all_users = pd.read_sql_query("SELECT username, bio FROM users WHERE username != ?", conn, params=(user,))
conn.close()

# Get who I am already following
following_list = db_utils.get_following(user)

for _, u in all_users.iterrows():
    target_user = u['username']
    is_following = target_user in following_list
    
    col_ratio = [3, 1]
    c1, c2 = st.columns(col_ratio)
    
    with c1:
        st.markdown(f"**{target_user}**")
        st.caption(u['bio'])
    with c2:
        if is_following:
            if st.button("Unfollow", key=f"unf_{target_user}"):
                db_utils.unfollow_user(user, target_user)
                st.rerun()
        else:
            if st.button("Follow", key=f"f_{target_user}"):
                db_utils.follow_user(user, target_user)
                st.rerun()
    st.divider()
