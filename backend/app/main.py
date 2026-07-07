

import uuid
import os
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

# Predefined interview questions per category (expanded pool for randomization)
QUESTIONS_DB = {
    "Software Engineer": [
        "Can you explain the difference between a Stateful and Stateless widget in Flutter?",
        "What is the difference between a REST API and WebSockets, and when would you use each?",
        "How do you handle state management in a large-scale mobile application?",
        "What is the role of an index in a database, and how does it speed up queries?",
        "Can you explain the concept of Clean Architecture and why it is useful?",
        "What is the difference between synchronous and asynchronous programming, and how do you handle concurrency?",
        "How do you optimize the performance of a slow mobile or web application?",
        "What are the key differences between SQL and NoSQL databases?"
    ],
    "Product Manager": [
        "How do you decide what features to prioritize in a product roadmap when multiple stakeholders disagree?",
        "Can you describe a time when a product launch failed, and what you learned from it?",
        "How do you define and measure success for a new feature?",
        "How do you conduct user research to identify pain points for a new product?",
        "How would you handle a situation where engineering says a key feature cannot be built on time?",
        "What metrics would you track for a ride-sharing app like Uber to measure passenger retention?",
        "Can you explain how you would design an MVP (Minimum Viable Product) for a new social media application?",
        "How do you balance long-term product vision with short-term business demands?"
    ],
    "HR Manager": [
        "How do you handle conflict resolution between two high-performing team members who refuse to collaborate?",
        "What strategies do you use to improve employee retention in a high-turnover industry?",
        "How do you evaluate cultural fit during an interview?",
        "How do you handle a situation where an employee complains about their manager's behavior?",
        "What steps would you take to design and implement a new diversity and inclusion program?",
        "How do you balance supporting the company's business goals with advocating for employee well-being?",
        "What is your approach to conducting performance reviews and giving constructive feedback?",
        "How do you manage onboarding for a fully remote team to make them feel integrated?"
    ],
    "Data Analyst": [
        "What is the difference between supervised and unsupervised learning, and can you give an example of each?",
        "How do you handle missing or noisy data in a dataset before performing analysis?",
        "Can you explain the difference between a join and a union in SQL?",
        "What is the difference between correlation and causation, and why is it important in analysis?",
        "How do you choose between a bar chart, a line chart, and a scatter plot for data visualization?",
        "What are Type I and Type II errors in hypothesis testing?",
        "Can you explain the difference between A/B testing and multivariate testing?",
        "How do you communicate complex technical insights to non-technical business stakeholders?"
    ],
    "Android Developer": [
        "Can you explain the Android Activity lifecycle and how to handle configuration changes like screen rotation?",
        "What is the difference between a Service, an IntentService, and WorkManager in Android?",
        "How do you optimize memory usage and prevent memory leaks in an Android application?",
        "What is your experience with Jetpack Compose vs. traditional XML layouts?"
    ],
    "Investment Banker": [
        "Can you walk me through the three main financial valuation methodologies and when to use each?",
        "How does a $10 increase in depreciation affect the three financial statements?",
        "What is the difference between WACC and Cost of Equity, and how do you calculate them?",
        "Can you explain the key phases of an M&A sell-side advisory process?"
    ],
    "Sales Representative": [
        "How do you handle a prospect who repeatedly objects to the price of your product?",
        "What is your process for qualifying leads and identifying high-value opportunities?",
        "Can you describe a time you lost a major sales deal, and what you learned from it?",
        "How do you build trust and maintain long-term relationships with key accounts?"
    ],
    "Marketing Specialist": [
        "How do you design and execute a multi-channel digital marketing campaign from scratch?",
        "What metrics do you prioritize to track and evaluate the performance of an email marketing campaign?",
        "Can you explain the difference between SEO and SEM, and how they work together?",
        "How do you conduct competitor analysis to identify gaps in market positioning?"
    ],
    "Nurse": [
        "How do you prioritize patient care when managing a heavy workload under high-pressure conditions?",
        "Can you describe a time you noticed a critical change in a patient's vital signs and what action you took?",
        "How do you handle a situation where a patient or their family member becomes aggressive or uncooperative?",
        "What is your approach to educating patients about post-discharge care and medication compliance?"
    ],
    "Doctor": [
        "Can you walk me through your diagnostic process when a patient presents with vague, non-specific symptoms?",
        "How do you handle delivering difficult or bad news to a patient and their family?",
        "What is your approach to collaborative care when working with multidisciplinary medical teams?",
        "How do you balance patient advocacy with institutional guidelines and resources?"
    ],
    "Research Scientist": [
        "How do you design a robust scientific experiment to minimize bias and control for confounding variables?",
        "Can you explain how you handle experimental failures or results that contradict your hypothesis?",
        "What is your experience with statistical analysis software and interpreting complex datasets?",
        "How do you translate complex scientific findings into clear reports for non-scientific stakeholders?"
    ],
    "Customer Support Specialist": [
        "How do you handle an extremely frustrated customer who is shouting about a product failure?",
        "What steps do you take when you do not know the answer to a customer's technical question?",
        "How do you balance efficiency (speed) with empathy (quality) when resolving customer tickets?",
        "Can you describe a time you turned a negative customer experience into a positive one?"
    ],
    "Project Manager": [
        "How do you manage project scope creep when a client repeatedly requests out-of-scope features?",
        "What methodologies (Agile, Waterfall, Scrum) do you prefer, and how do you choose between them?",
        "How do you handle conflict or performance issues within a cross-functional project team?",
        "What metrics do you track to evaluate project health, budget compliance, and timeline status?"
    ],
    "Teacher / Educator": [
        "How do you differentiate your instruction to meet the diverse learning needs of students in your classroom?",
        "What strategies do you use to establish a positive classroom environment and manage behavior?",
        "How do you handle communication with a parent who is upset about their child's grade or behavior?",
        "What is your approach to using technology to enhance student engagement and learning outcomes?"
    ],
    "Hotel Manager": [
        "How do you handle a situation where the hotel is overbooked and a guest with a reservation arrives?",
        "What strategies do you implement to maximize occupancy rates and RevPAR during low seasons?",
        "How do you motivate and manage diverse hospitality staff to maintain high service standards?",
        "Can you describe how you handle a severe guest complaint regarding room cleanliness or service quality?"
    ]
}

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
    
    if session_data.custom_questions and len(session_data.custom_questions) > 0:
        questions = session_data.custom_questions
    else:
        # Retrieve question pool for the category (or generic fallback)
        question_pool = QUESTIONS_DB.get(
            session_data.category, 
            [
                "Can you tell me about yourself and your background?",
                "What is your greatest professional achievement?",
                "Where do you see yourself in five years?",
                "What are your key strengths and weaknesses?",
                "How do you handle pressure and tight deadlines?"
            ]
        )
        
        # Randomly select 3 unique questions from the pool
        questions = random.sample(question_pool, min(len(question_pool), 3))
    
    active_sessions[session_id] = {
        "category": session_data.category,
        "questions": questions,
        "answers": ["" for _ in range(len(questions))],
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
            # Reconstruct schemas-compliant dict
            # Pydantic v2 requires scores_breakdown and metrics to match schemas
            return {
                "overall_score": saved_report["overall_score"],
                "scores_breakdown": {
                    "confidence": int(saved_report["overall_score"] * 0.95),
                    "communication": saved_report["relevance_score"],
                    "behavioral": saved_report["posture_score"]
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
                "feedback": [
                    {
                        "category": "Eye Contact",
                        "status": "Good" if saved_report["eye_contact_score"] >= 75 else "Needs Improvement",
                        "score": saved_report["eye_contact_score"],
                        "detail": "Maintained steady gaze during the conversation." if saved_report["eye_contact_score"] >= 75 else "Try to look at the camera more frequently."
                    },
                    {
                        "category": "Posture",
                        "status": "Good" if saved_report["posture_score"] >= 80 else "Slouching Warning",
                        "score": saved_report["posture_score"],
                        "detail": "Sat straight with level shoulders." if saved_report["posture_score"] >= 80 else "Align your shoulders to show more confidence."
                    }
                ],
                "transcript": "Report fetched from server-side history.",
                "question_evaluations": []
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
            relevance_score = report.get("scores_breakdown", {}).get("communication", 80)
            
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
                "emotions": emotions_summary
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
