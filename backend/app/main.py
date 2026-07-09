import uuid
import os
import json
import shutil
import random
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List

from app.models.schemas import (
    SessionCreate, SessionResponse, FrameResponse, AudioResponse, ReportResponse,
    UserSignup, UserLogin, ForgotPasswordRequest, ResetPasswordRequest, ProfileUpdate
)
from app.services.vision import analyze_frame
from app.services.speech import transcribe_audio
from app.services.scoring import calculate_final_scores
from app.services import db

# Initialize SQLite database on startup
db.init_db()

app = FastAPI(
    title="AI Smart Interview Analyzer API",
    description="Backend processing endpoints for real-time video, audio, and posture scoring.",
    version="1.0.0"
)

# Configure CORS for Flutter development (allows running on local devices/emulators)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load questions and ideal answers from dynamic JSON database file
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
QUESTIONS_DB_PATH = os.path.join(CURRENT_DIR, "services", "questions_db.json")

try:
    with open(QUESTIONS_DB_PATH, "r") as f:
        QUESTIONS_POOL = json.load(f)
except Exception as e:
    print(f"Error loading questions_db.json: {e}")
    QUESTIONS_POOL = {}

# Global in-memory storage for active session metrics
active_sessions: Dict[str, Dict[str, Any]] = {}

# Folder to temporarily save uploaded media chunks
TEMP_MEDIA_DIR = "temp_media"
os.makedirs(TEMP_MEDIA_DIR, exist_ok=True)

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "AI Interview Analyzer API"}

@app.post("/api/session", response_model=SessionResponse)
def create_session(session_data: SessionCreate):
    session_id = str(uuid.uuid4())
    
    # Retrieve count requested, bounded 1 to 20
    count = session_data.question_count or 5
    count = max(1, min(20, count))
    
    if session_data.custom_questions and len(session_data.custom_questions) > 0:
        questions = session_data.custom_questions
        ideal_answers = ["" for _ in questions]
    else:
        # Retrieve question pool for the category (or generic fallback)
        pool = QUESTIONS_POOL.get(session_data.category)
        if not pool:
            # Fallback to General Practice
            pool = QUESTIONS_POOL.get("General Practice", [])
        
        # Ensure we have at least 50 questions in the pool to satisfy the "at least 50 questions in the queue" requirement.
        # If pool size is less than 50, we combine it with General Practice questions to reach at least 50.
        # We copy to prevent mutating the original global dict pool
        pool = list(pool)
        if len(pool) < 50:
            fallback_pool = QUESTIONS_POOL.get("General Practice", [])
            existing_questions = {q["question"] for q in pool}
            for q in fallback_pool:
                if q["question"] not in existing_questions:
                    pool.append(q)
                if len(pool) >= 50:
                    break
        
        # Randomly select requested number of unique questions from the pool
        sampled = random.sample(pool, min(len(pool), count))
        questions = [q["question"] for q in sampled]
        ideal_answers = [q.get("ideal_answer", "") for q in sampled]
    
    active_sessions[session_id] = {
        "category": session_data.category,
        "questions": questions,
        "answers": ["" for _ in range(len(questions))],
        "ideal_answers": ideal_answers,
        "frames": [],
        "speech": [],
        "emotions": [],
        "prev_hand_pos": [],
        "frame_count": 0,
        "user_id": session_data.user_id
    }
    
    # Save session in database if user_id is provided
    if session_data.user_id:
        try:
            db.create_session(session_id, session_data.user_id, session_data.category)
        except Exception as e:
            print(f"Error saving session to DB: {e}")
            
    return {
        "session_id": session_id,
        "category": session_data.category,
        "status": "initialized",
        "questions": questions
    }

@app.post("/api/session/{session_id}/frame", response_model=FrameResponse)
async def upload_frame(session_id: str, file: UploadFile = File(...)):
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    try:
        image_bytes = await file.read()
        session = active_sessions[session_id]
        
        # Analyze frame
        metrics = analyze_frame(image_bytes, session)
        
        # Store frame telemetry
        session["frames"].append(metrics)
        if metrics.get("dominant_emotion"):
            session["emotions"].append(metrics["dominant_emotion"])
            
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process frame: {str(e)}")

@app.post("/api/session/{session_id}/audio", response_model=AudioResponse)
async def upload_audio(
    session_id: str, 
    duration: float = Form(...), 
    question_index: int = Form(default=0),
    file: UploadFile = File(...)
):
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    try:
        # Save audio file temporarily to analyze it
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ".wav"
        temp_file_name = f"{session_id}_{uuid.uuid4()}{file_extension}"
        temp_file_path = os.path.join(TEMP_MEDIA_DIR, temp_file_name)
        
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        session = active_sessions[session_id]
        
        # Analyze audio/speech
        speech_analysis = transcribe_audio(temp_file_path, duration)
        
        # Store speech record
        session["speech"].append(speech_analysis)
        
        # Append transcription chunk to active question answer
        transcribed_text = speech_analysis.get("text", "").strip()
        if transcribed_text and not transcribed_text.startswith("Error"):
            answers = session["answers"]
            if 0 <= question_index < len(answers):
                if answers[question_index]:
                    answers[question_index] += " " + transcribed_text
                else:
                    answers[question_index] = transcribed_text
        
        # Clean up file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
        return speech_analysis
    except Exception as e:
        # Clean up in case of failure
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=f"Failed to process audio: {str(e)}")

@app.get("/api/session/{session_id}/report", response_model=ReportResponse)
def get_session_report(session_id: str):
    # First check if the report already exists in the SQLite database
    try:
        saved_report = db.get_report_by_session(session_id)
        if saved_report:
            # Reconstruct schemas-compliant dict matching ScoresBreakdown (speech_clarity, confidence, eye_contact, engagement)
            speech_clarity = saved_report.get("speech_clarity_score") if saved_report.get("speech_clarity_score") is not None else saved_report["relevance_score"]
            confidence = saved_report.get("confidence_score") if saved_report.get("confidence_score") is not None else saved_report["posture_score"]
            eye_contact = saved_report.get("eye_contact_score") if saved_report.get("eye_contact_score") is not None else 80
            engagement = saved_report.get("engagement_score") if saved_report.get("engagement_score") is not None else saved_report["overall_score"]

            feedback = [
                {
                    "category": "Speech Clarity",
                    "status": "Excellent" if speech_clarity >= 80 else ("Good" if speech_clarity >= 60 else "Needs Improvement"),
                    "score": speech_clarity,
                    "detail": "Spoke clearly with comfortable conversational pacing." if speech_clarity >= 80 else "Practice taking brief pauses to minimize filler word usage."
                },
                {
                    "category": "Confidence",
                    "status": "Excellent" if confidence >= 80 else ("Good" if confidence >= 60 else "Needs Improvement"),
                    "score": confidence,
                    "detail": "Maintained highly stable visual presence and vocal energy." if confidence >= 80 else "Focus on sit upright and project authority."
                },
                {
                    "category": "Eye Contact",
                    "status": "Excellent" if eye_contact >= 80 else ("Good" if eye_contact >= 60 else "Needs Improvement"),
                    "score": eye_contact,
                    "detail": "Excellent eye contact, looked directly at the camera." if eye_contact >= 80 else "Try to look at the webcam lens more consistently."
                },
                {
                    "category": "Engagement",
                    "status": "Excellent" if engagement >= 80 else ("Good" if engagement >= 60 else "Needs Improvement"),
                    "score": engagement,
                    "detail": "Highly interactive response style and keyword coverage." if engagement >= 80 else "Practice structuring answers with more specific technical details."
                }
            ]

            return {
                "overall_score": saved_report["overall_score"],
                "scores_breakdown": {
                    "speech_clarity": speech_clarity,
                    "confidence": confidence,
                    "eye_contact": eye_contact,
                    "engagement": engagement
                },
                "metrics": {
                    "eye_contact_ratio": saved_report["eye_contact_score"] / 100.0,
                    "average_posture": float(saved_report["posture_score"]),
                    "fidget_ratio": 0.05 if saved_report["filler_words_count"] > 5 else 0.0,
                    "wpm": saved_report["speaking_pace_wpm"],
                    "total_words": saved_report["speaking_pace_wpm"] * 2, # rough estimation
                    "filler_words_total": saved_report["filler_words_count"]
                },
                "emotions_timeline": list(saved_report["emotions"].keys()) if saved_report["emotions"] else ["confident"],
                "feedback": feedback,
                "transcript": "Report fetched from server-side history.",
                "question_evaluations": [],
                "ai_coaching_summary": None # summary can be dynamically regenerated if needed or loaded from database tips
            }
    except Exception as e:
        print(f"Error checking saved report: {e}")

    # Fallback to calculate new score
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session = active_sessions[session_id]
    report = calculate_final_scores(session)
    
    # Save the report to SQLite database if user_id is linked to this session
    user_id = session.get("user_id")
    if user_id:
        try:
            # Map calculate_final_scores response to database schema format
            overall_score = report.get("overall_score", 0)
            posture_score = int(report.get("metrics", {}).get("average_posture", 100))
            eye_contact_score = int(report.get("metrics", {}).get("eye_contact_ratio", 1.0) * 100)
            filler_words_count = report.get("metrics", {}).get("filler_words_total", 0)
            speaking_pace_wpm = report.get("metrics", {}).get("wpm", 130)
            relevance_score = report.get("scores_breakdown", {}).get("engagement", 80) # legacy map
            
            tips_list = [f.get("detail", "") for f in report.get("feedback", [])]
            emotions_timeline = report.get("emotions_timeline", [])
            emotions_summary = {}
            for emo in emotions_timeline:
                emotions_summary[emo] = emotions_summary.get(emo, 0) + 1
                
            db.save_report(session_id, user_id, {
                "overall_score": overall_score,
                "posture_score": posture_score,
                "eye_contact_score": eye_contact_score,
                "filler_words_count": filler_words_count,
                "speaking_pace_wpm": speaking_pace_wpm,
                "relevance_score": relevance_score,
                "tips": tips_list,
                "emotions": emotions_summary,
                "speech_clarity_score": report.get("scores_breakdown", {}).get("speech_clarity", 80),
                "confidence_score": report.get("scores_breakdown", {}).get("confidence", 80),
                "engagement_score": report.get("scores_breakdown", {}).get("engagement", 80)
            })
        except Exception as e:
            print(f"Error saving report to DB: {e}")
            
    return report

# --- AUTHENTICATION & PROFILE ENDPOINTS ---

@app.post("/api/auth/signup")
def signup(user: UserSignup):
    res = db.create_user(user.email, user.name, user.password)
    if res["status"] == "error":
        raise HTTPException(status_code=400, detail=res["message"])
    return res

@app.post("/api/auth/login")
def login(user: UserLogin):
    res = db.authenticate_user(user.email, user.password)
    if res is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return res

@app.post("/api/auth/forgot-password")
def forgot_password(req: ForgotPasswordRequest):
    # Check if user exists
    conn = db.get_db_connection()
    user = conn.execute("SELECT id FROM users WHERE email = ?", (req.email.lower().strip(),)).fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found with this email")
        
    # Generate random 6-digit OTP
    otp = str(random.randint(100000, 999999))
    db.save_otp(req.email, otp)
    
    print(f"\n==========================================")
    print(f" OTP GENERATED FOR {req.email}: {otp}")
    print(f"==========================================\n")
    
    return {"status": "success", "message": "OTP generated successfully", "otp": otp}

@app.post("/api/auth/reset-password")
def reset_password(req: ResetPasswordRequest):
    verified = db.verify_otp(req.email, req.otp)
    if not verified:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        
    updated = db.update_password(req.email, req.new_password)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to reset password")
        
    db.delete_otp(req.email)
    return {"status": "success", "message": "Password updated successfully"}

@app.get("/api/auth/profile/{user_id}")
def get_profile(user_id: str):
    res = db.get_user_by_id(user_id)
    if not res:
        raise HTTPException(status_code=404, detail="User profile not found")
    return res

@app.post("/api/auth/profile/{user_id}")
def update_profile(user_id: str, profile: ProfileUpdate):
    updated = db.update_user_profile(user_id, profile.dict())
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update profile")
    return {"status": "success"}

@app.get("/api/history/{user_id}")
def get_history(user_id: str):
    history = db.get_user_history(user_id)
    return history

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
