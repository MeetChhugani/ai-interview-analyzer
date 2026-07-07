import sqlite3
import hashlib
import uuid
import time
import json
import os
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            education TEXT,
            experience TEXT,
            current_role TEXT,
            skills TEXT,
            created_at TEXT
        )
    """)
    
    # 2. Create otps table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS otps (
            email TEXT PRIMARY KEY,
            otp TEXT NOT NULL,
            expires_at INTEGER NOT NULL
        )
    """)
    
    # 3. Create sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            category TEXT,
            created_at TEXT,
            is_completed INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # 4. Create reports table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            session_id TEXT PRIMARY KEY,
            user_id TEXT,
            overall_score INTEGER,
            posture_score INTEGER,
            eye_contact_score INTEGER,
            filler_words_count INTEGER,
            speaking_pace_wpm INTEGER,
            relevance_score INTEGER,
            tips TEXT,
            emotion_summary TEXT,
            created_at TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("SQLite database successfully initialized.")

def hash_password(password: str, salt: str = "ai_interview_salt_99") -> str:
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

def create_user(email: str, name: str, password: str) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    user_id = str(uuid.uuid4())
    pw_hash = hash_password(password)
    created_at = time.strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        cursor.execute(
            "INSERT INTO users (id, email, name, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, email.lower().strip(), name.strip(), pw_hash, created_at)
        )
        conn.commit()
        return {"id": user_id, "email": email, "name": name, "status": "success"}
    except sqlite3.IntegrityError:
        return {"status": "error", "message": "Email already exists"}
    finally:
        conn.close()

def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    pw_hash = hash_password(password)
    
    cursor.execute(
        "SELECT id, email, name, education, experience, current_role, skills FROM users WHERE email = ? AND password_hash = ?",
        (email.lower().strip(), pw_hash)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row["id"],
            "email": row["email"],
            "name": row["name"],
            "education": row["education"],
            "experience": row["experience"],
            "current_role": row["current_role"],
            "skills": json.loads(row["skills"]) if row["skills"] else []
        }
    return None

def update_user_profile(user_id: str, profile_data: Dict[str, Any]) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    skills_json = json.dumps(profile_data.get("skills", []))
    
    cursor.execute(
        """UPDATE users SET 
           name = ?, education = ?, experience = ?, current_role = ?, skills = ? 
           WHERE id = ?""",
        (
            profile_data.get("name", ""),
            profile_data.get("education", ""),
            profile_data.get("experience", ""),
            profile_data.get("currentRole", ""),
            skills_json,
            user_id
        )
    )
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_affected > 0

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, email, name, education, experience, current_role, skills FROM users WHERE id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row["id"],
            "email": row["email"],
            "name": row["name"],
            "education": row["education"],
            "experience": row["experience"],
            "current_role": row["current_role"],
            "skills": json.loads(row["skills"]) if row["skills"] else []
        }
    return None

def save_otp(email: str, otp: str, duration_sec: int = 300) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    expires_at = int(time.time()) + duration_sec
    
    cursor.execute(
        "INSERT OR REPLACE INTO otps (email, otp, expires_at) VALUES (?, ?, ?)",
        (email.lower().strip(), otp, expires_at)
    )
    conn.commit()
    conn.close()

def verify_otp(email: str, otp: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = int(time.time())
    
    cursor.execute(
        "SELECT otp FROM otps WHERE email = ? AND otp = ? AND expires_at > ?",
        (email.lower().strip(), otp.strip(), current_time)
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None

def delete_otp(email: str) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM otps WHERE email = ?", (email.lower().strip(),))
    conn.commit()
    conn.close()

def update_password(email: str, password: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    pw_hash = hash_password(password)
    
    cursor.execute(
        "UPDATE users SET password_hash = ? WHERE email = ?",
        (pw_hash, email.lower().strip())
    )
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_affected > 0

def create_session(session_id: str, user_id: str, category: str) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    created_at = time.strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute(
        "INSERT INTO sessions (id, user_id, category, created_at, is_completed) VALUES (?, ?, ?, ?, 0)",
        (session_id, user_id, category, created_at)
    )
    conn.commit()
    conn.close()

def save_report(session_id: str, user_id: str, report_data: Dict[str, Any]) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    created_at = time.strftime('%Y-%m-%d %H:%M:%S')
    
    # Serialize json elements
    tips_json = json.dumps(report_data.get("tips", []))
    emotions_json = json.dumps(report_data.get("emotions", {}))
    
    cursor.execute(
        """INSERT OR REPLACE INTO reports (
            session_id, user_id, overall_score, posture_score, eye_contact_score, 
            filler_words_count, speaking_pace_wpm, relevance_score, tips, 
            emotion_summary, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            session_id,
            user_id,
            report_data.get("overall_score", 0),
            report_data.get("posture_score", 0),
            report_data.get("eye_contact_score", 0),
            report_data.get("filler_words_count", 0),
            report_data.get("speaking_pace_wpm", 0),
            report_data.get("relevance_score", 0),
            tips_json,
            emotions_json,
            created_at
        )
    )
    
    cursor.execute("UPDATE sessions SET is_completed = 1 WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()

def get_report_by_session(session_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT r.session_id, r.user_id, r.overall_score, r.posture_score, r.eye_contact_score, 
                  r.filler_words_count, r.speaking_pace_wpm, r.relevance_score, r.tips, 
                  r.emotion_summary, r.created_at, s.category
           FROM reports r
           JOIN sessions s ON r.session_id = s.id
           WHERE r.session_id = ?""",
        (session_id,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "session_id": row["session_id"],
            "user_id": row["user_id"],
            "category": row["category"],
            "overall_score": row["overall_score"],
            "posture_score": row["posture_score"],
            "eye_contact_score": row["eye_contact_score"],
            "filler_words_count": row["filler_words_count"],
            "speaking_pace_wpm": row["speaking_pace_wpm"],
            "relevance_score": row["relevance_score"],
            "tips": json.loads(row["tips"]) if row["tips"] else [],
            "emotions": json.loads(row["emotion_summary"]) if row["emotion_summary"] else {},
            "created_at": row["created_at"]
        }
    return None

def get_user_history(user_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT r.session_id, r.user_id, r.overall_score, r.posture_score, r.eye_contact_score, 
                  r.filler_words_count, r.speaking_pace_wpm, r.relevance_score, r.tips, 
                  r.emotion_summary, r.created_at, s.category
           FROM reports r
           JOIN sessions s ON r.session_id = s.id
           WHERE r.user_id = ?
           ORDER BY r.created_at DESC""",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            "session_id": row["session_id"],
            "user_id": row["user_id"],
            "category": row["category"],
            "overall_score": row["overall_score"],
            "posture_score": row["posture_score"],
            "eye_contact_score": row["eye_contact_score"],
            "filler_words_count": row["filler_words_count"],
            "speaking_pace_wpm": row["speaking_pace_wpm"],
            "relevance_score": row["relevance_score"],
            "tips": json.loads(row["tips"]) if row["tips"] else [],
            "emotions": json.loads(row["emotion_summary"]) if row["emotion_summary"] else {},
            "created_at": row["created_at"]
        })
    return history
