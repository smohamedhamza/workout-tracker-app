import sqlite3
import hashlib
import pandas as pd
from datetime import datetime

DB_FILE = "repquest.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 1. Users & Profile
    # Added: height, weight, bio
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            height_cm REAL,
            weight_kg REAL,
            bio TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Quests (Legacy + New)
    # MIGRATION: Ensure 'username' exists
    try:
        c.execute("ALTER TABLE quests ADD COLUMN username TEXT")
    except sqlite3.OperationalError:
        pass # Column exists

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

    # 3. Workouts (Quest Specific Logs) - Linked to Activity Feed
    try:
         c.execute("ALTER TABLE workouts ADD COLUMN activity_log_id INTEGER")
    except sqlite3.OperationalError:
         pass 

    try:
         c.execute("ALTER TABLE workouts ADD COLUMN timestamp TIMESTAMP")
    except sqlite3.OperationalError:
         pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quest_id INTEGER,
            reps INTEGER NOT NULL,
            activity_log_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (quest_id) REFERENCES quests(id) ON DELETE CASCADE
        )
    """)
    
    # 4. Activity Log (Feed)
    c.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            activity_type TEXT, 
            activity_name TEXT,
            reps INTEGER,
            distance_km REAL,
            duration_min REAL,
            calories REAL,
            timestamp TIMESTAMP,
            is_public BOOLEAN DEFAULT 0,
            FOREIGN KEY(username) REFERENCES users(username)
        )
    """)

    # 4. Social Graph
    c.execute("""
        CREATE TABLE IF NOT EXISTS follows (
            follower TEXT,
            following TEXT,
            PRIMARY KEY (follower, following)
        )
    """)

    # 5. Posts (Social Feed items explicitly shared)
    # We can query activity_log where is_public=1, but a separate posts table allows for text-only posts too.
    # For now, we'll stick to robust activity_log querying.
    # 6. Exercises Database (System + User Custom)
    c.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            name TEXT PRIMARY KEY,
            calories_per_rep REAL,
            category TEXT DEFAULT 'Strength',
            is_custom BOOLEAN DEFAULT 0,
            created_by TEXT DEFAULT 'system'
        )
    """)
    
    # SEED DATA (Only if empty)
    c.execute("SELECT count(*) FROM exercises")
    if c.fetchone()[0] == 0:
        seed_data = [
            ("Pushups", 0.45, "Strength", 0, "system"),
            ("Squats", 0.60, "Strength", 0, "system"),
            ("Pullups", 1.0, "Strength", 0, "system"),
            ("Situps", 0.3, "Strength", 0, "system"),
            ("Lunges", 0.5, "Strength", 0, "system"),
            ("Burpees", 1.2, "Cardio", 0, "system"),
            ("Plank (sec)", 0.2, "Strength", 0, "system"),
            ("Crunches", 0.25, "Strength", 0, "system"),
            ("Diamond Pushups", 0.6, "Strength", 0, "system"),
        ]
        c.executemany("INSERT INTO exercises VALUES (?,?,?,?,?)", seed_data)

    conn.commit()
    conn.close()

# --- AUTH ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    data = c.fetchone()
    conn.close()
    if data and data[0] == hash_password(password):
        return True
    return False

def get_user_profile(username):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT height_cm, weight_kg, bio FROM users WHERE username = ?", conn, params=(username,))
    conn.close()
    return df.iloc[0].to_dict() if not df.empty else None

def update_profile(username, height, weight, bio):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET height_cm=?, weight_kg=?, bio=? WHERE username=?", (height, weight, bio, username))
    conn.commit()
    conn.close()

# --- EXERCISES ---
def get_exercises():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT name, calories_per_rep FROM exercises ORDER BY name ASC", conn)
    conn.close()
    return dict(zip(df.name, df.calories_per_rep))

def add_custom_exercise(name, cals, user):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO exercises (name, calories_per_rep, is_custom, created_by) VALUES (?, ?, 1, ?)", (name, cals, user))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# --- ACTIVITY HELPERS ---
def delete_activity(activity_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM activity_log WHERE id = ?", (activity_id,))
    conn.commit()
    conn.close()

def get_user_stats(username):
    conn = sqlite3.connect(DB_FILE)
    
    # Weekly & Monthly
    # Simple approach: Fetch all and group by pandas for flexibility
    df = pd.read_sql_query(
        "SELECT calories, timestamp FROM activity_log WHERE username = ?", 
        conn, params=(username,), parse_dates=['timestamp']
    )
    conn.close()
    
    if df.empty:
        return {"total": 0, "weekly": 0, "monthly": 0}
        
    now = datetime.now()
    
    # Week starts Monday
    current_week_mask = (df['timestamp'].dt.year == now.year) & (df['timestamp'].dt.isocalendar().week == now.isocalendar()[1])
    current_month_mask = (df['timestamp'].dt.year == now.year) & (df['timestamp'].dt.month == now.month)
    
    return {
        "total": int(df['calories'].sum()),
        "weekly": int(df[current_week_mask]['calories'].sum()),
        "monthly": int(df[current_month_mask]['calories'].sum())
    }

# --- SOCIAL FUNCTIONS ---
def follow_user(follower, following):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO follows (follower, following) VALUES (?, ?)", (follower, following))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def unfollow_user(follower, following):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM follows WHERE follower = ? AND following = ?", (follower, following))
    conn.commit()
    conn.close()

def get_following(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT following FROM follows WHERE follower = ?", (username,))
    data = [row[0] for row in c.fetchall()]
    conn.close()
    return data

def create_quest(username, name, target, deadline=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT INTO quests (username, name, target_count, deadline) VALUES (?, ?, ?, ?)', (username, name, target, deadline))
    conn.commit()
    conn.close()

def log_quest_workout(user, quest_id, quest_name, reps, timestamp, exercise_name=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 1. Estimate Calories
    cals = 0
    if exercise_name:
        try:
            cals = reps * 0.5 
            row = c.execute("SELECT calories_per_rep FROM exercises WHERE name = ?", (exercise_name,)).fetchone()
            if row:
                cals = reps * row[0]
        except:
            pass
    else:
        cals = reps * 0.45 
        
    # 2. Insert into Activity Log (Feed)
    if not exercise_name:
        exercise_name = "Workout"
        
    c.execute("""
        INSERT INTO activity_log (username, activity_type, activity_name, reps, calories, timestamp, is_public) 
        VALUES (?, 'Quest', ?, ?, ?, ?, 1)
    """, (user, f"{exercise_name} ({quest_name})", reps, cals, timestamp))
    
    activity_id = c.lastrowid
    
    # 3. Insert into Workouts (Quest Tracking)
    c.execute("""
        INSERT INTO workouts (quest_id, reps, activity_log_id, timestamp) 
        VALUES (?, ?, ?, ?)
    """, (quest_id, reps, activity_id, timestamp))
    
    conn.commit()
    conn.close()

def get_quest_logs(quest_id):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT id, reps, timestamp FROM workouts WHERE quest_id = ? ORDER BY timestamp DESC", conn, params=(quest_id,))
    conn.close()
    return df

def delete_quest_workout(workout_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Find linked activity log
    row = c.execute("SELECT activity_log_id FROM workouts WHERE id = ?", (workout_id,)).fetchone()
    if row and row[0]:
        c.execute("DELETE FROM activity_log WHERE id = ?", (row[0],))
        
    c.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))
    conn.commit()
    conn.close()

def delete_entire_quest(quest_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Find all linked activities to clean up feed
    rows = c.execute("SELECT activity_log_id FROM workouts WHERE quest_id = ?", (quest_id,)).fetchall()
    for row in rows:
        if row[0]:
            c.execute("DELETE FROM activity_log WHERE id = ?", (row[0],))
            
    c.execute("DELETE FROM workouts WHERE quest_id = ?", (quest_id,))
    c.execute("DELETE FROM quests WHERE id = ?", (quest_id,))
    conn.commit()
    conn.close()
