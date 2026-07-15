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

# Load local .env file variables securely
def load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()
        print("Loaded local .env environment variables successfully.")

load_env()

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

def generate_questions_for_custom_role(role: str, count: int = 5) -> list:
    role_clean = role.strip()
    role_lower = role_clean.lower()
    
    if "flutter" in role_lower or "android" in role_lower or "ios" in role_lower or "mobile" in role_lower:
        base_pool = [
            {
                "question": f"Can you explain your experience building mobile applications, and how you manage state and lifecycle events in {role_clean}?",
                "ideal_answer": "An ideal answer should detail specific state management patterns (like BLoC, Riverpod, or Redux), lifecycle states (initState, dispose), and write robust code for platform integrations.",
                "keywords": ["state", "lifecycle", "bloc", "riverpod", "widget", "performance", "async"]
            },
            {
                "question": f"How do you optimize rendering performance, layout layout trees, and build sizes in a {role_clean} project?",
                "ideal_answer": "An ideal answer should cover widget rebuilding optimization, lazy loading (ListView.builder), asset compression, profiling tools (DevTools), and reducing binary footprint.",
                "keywords": ["rendering", "rebuild", "devtools", "optimize", "layout", "performance"]
            },
            {
                "question": "How do you handle local data caching, offline sync, and secure token storage in mobile clients?",
                "ideal_answer": "An ideal answer should outline key-value stores (SharedPreferences, Hive), secure databases (SQLite, Realm), and encrypting sensitive tokens using keystores or keychains.",
                "keywords": ["database", "sqlite", "caching", "secure", "token", "offline", "sync"]
            },
            {
                "question": "Can you describe a challenging platform-specific bug you resolved, and the debugging tools you utilized?",
                "ideal_answer": "An ideal answer should detail a specific crash or memory leak, using Logcat, Xcode Instruments, or Flutter DevTools to inspect heap allocation and isolate the leak.",
                "keywords": ["bug", "leak", "devtools", "crash", "logcat", "xcode", "troubleshoot"]
            },
            {
                "question": "How do you structure writing automated unit tests and integration tests to ensure code quality?",
                "ideal_answer": "An ideal answer should cover writing test cases, mocking API dependencies (Mockito), testing widget interaction, and running automated CI/CD checks.",
                "keywords": ["unit test", "integration", "mock", "test", "coverage", "assertion"]
            }
        ]
    elif "web" in role_lower or "frontend" in role_lower or "react" in role_lower or "vue" in role_lower or "javascript" in role_lower:
        base_pool = [
            {
                "question": f"What is your approach to modern frontend architecture, state management, and component reusability in {role_clean}?",
                "ideal_answer": "An ideal answer should outline separating business logic from components, global stores (Redux, Pinia, Context API), and writing clean reusable UI hooks.",
                "keywords": ["component", "hooks", "redux", "state", "architecture", "reusable"]
            },
            {
                "question": "How do you optimize web application performance, including first contentful paint and layout shifts?",
                "ideal_answer": "An ideal answer should discuss code splitting, lazy loading, image optimization, CDN distribution, and analyzing performance using Lighthouse.",
                "keywords": ["performance", "lighthouse", "lazy", "paint", "cdn", "loading", "split"]
            },
            {
                "question": "How do you secure web clients against common vulnerabilities like cross-site scripting (XSS) and CSRF?",
                "ideal_answer": "An ideal answer should detail sanitizing user inputs, implementing Content Security Policy (CSP) headers, secure HTTP-only cookies, and CSRF tokens.",
                "keywords": ["security", "xss", "csrf", "cookie", "csp", "sanitize", "token"]
            },
            {
                "question": "Can you explain the differences between Client-Side Rendering (CSR), Server-Side Rendering (SSR), and Static Site Generation (SSG)?",
                "ideal_answer": "An ideal answer should compare SEO advantages, initial load speeds, server resource overheads, and when to apply CSR (SPAs) vs SSR/SSG (Next.js/Nuxt).",
                "keywords": ["ssr", "ssg", "csr", "seo", "render", "server", "static"]
            },
            {
                "question": "How do you establish persistent real-time connections, and handle request retries or socket failures?",
                "ideal_answer": "An ideal answer should contrast WebSockets with SSE, detailing socket handshakes, heartbeat keepalives, exponential backoff reconnects, and REST API fallbacks.",
                "keywords": ["websocket", "socket", "sse", "retry", "backoff", "reconnect", "network"]
            }
        ]
    elif "backend" in role_lower or "api" in role_lower or "python" in role_lower or "django" in role_lower or "node" in role_lower:
        base_pool = [
            {
                "question": f"How do you design scalable RESTful APIs, and what strategies do you employ for request throttling and rate limiting in {role_clean}?",
                "ideal_answer": "An ideal answer should cover HTTP methods, status codes, API versioning, token bucket algorithms, and Redis-backed rate limiting middleware.",
                "keywords": ["rest", "api", "throttling", "redis", "rate limit", "scale"]
            },
            {
                "question": "What database query optimization strategies do you utilize when scaling reading and writing operations?",
                "ideal_answer": "An ideal answer should cover adding database indexes, query profiling (EXPLAIN), connection pooling, read replicas, and caching layers like Redis.",
                "keywords": ["index", "query", "optimize", "redis", "replica", "explain", "db"]
            },
            {
                "question": "How do you manage authentication and access control, such as RBAC and OAuth2, across services?",
                "ideal_answer": "An ideal answer should explain JWT payload signing, token verification, role-based access check middleware, and secure secret key rotation.",
                "keywords": ["auth", "jwt", "oauth2", "rbac", "token", "signature", "secret"]
            },
            {
                "question": "Can you detail your experience with microservices architecture, message queues, and async task execution?",
                "ideal_answer": "An ideal answer should cover event-driven triggers, message brokers (RabbitMQ, Kafka), asynchronous workers (Celery), and event consistency patterns.",
                "keywords": ["microservices", "queue", "rabbitmq", "celery", "kafka", "async", "worker"]
            },
            {
                "question": "How do you trace performance bottlenecks, log server errors, and set up continuous monitoring?",
                "ideal_answer": "An ideal answer should discuss distributed tracing (OpenTelemetry), logging levels, aggregation pools (ELK, Datadog), and setting up alerts for HTTP 500 errors.",
                "keywords": ["monitoring", "telemetry", "tracing", "logs", "metrics", "alerts", "bottleneck"]
            }
        ]
    else:
        base_pool = [
            {
                "question": f"What are the core technical competencies and methodologies required to succeed as a {role_clean}?",
                "ideal_answer": f"An ideal answer should detail specific domain skills, design principles, and industry frameworks related directly to working as a {role_clean}.",
                "keywords": ["methodology", "framework", "competency", "standards", "role"]
            },
            {
                "question": f"Can you outline a challenging project or objective you delivered in your capacity as a {role_clean}?",
                "ideal_answer": "An ideal answer should follow the STAR method (Situation, Task, Action, Result), explaining concrete technical challenges and metric-driven results.",
                "keywords": ["challenge", "star", "delivery", "project", "metrics", "result"]
            },
            {
                "question": f"How do you prioritize deliverables, manage stakeholder expectations, and handle scope changes in a {role_clean} role?",
                "ideal_answer": "An ideal answer should cover prioritization frameworks (Eisenhower matrix, MoSCoW), clear communication channels, and agile sprint adjustments.",
                "keywords": ["prioritize", "communication", "stakeholder", "agile", "scope", "planning"]
            },
            {
                "question": f"What tools, diagnostics, or platforms do you rely on daily to maintain high output as a {role_clean}?",
                "ideal_answer": "An ideal answer should list specific industry software, development tools, or testing frameworks, explaining how they increase productivity.",
                "keywords": ["tools", "platform", "software", "efficiency", "workflow", "output"]
            },
            {
                "question": "How do you stay updated with emerging tech trends, standards, and best practices in your field?",
                "ideal_answer": "An ideal answer should cover reading research papers, tech blogs, attending conferences, contributing to open source, or participating in continuous training.",
                "keywords": ["learning", "trends", "standards", "best practices", "research", "blogs"]
            }
        ]
    
    # Check if OpenAI can generate questions dynamically
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            import httpx
            prompt = (
                f"Generate {count} professional, technical interview questions for the role: '{role_clean}'.\n"
                f"For each question, provide:\n"
                f"1. The question text.\n"
                f"2. A 2-3 sentence 'ideal_answer' detailing the concepts the candidate should address.\n"
                f"3. A list of 4-6 specific technical 'keywords' that should be matched.\n\n"
                f"Output exactly in valid JSON array format, where each object is:\n"
                f"{{\n"
                f"  \"question\": \"...\",\n"
                f"  \"ideal_answer\": \"...\",\n"
                f"  \"keywords\": [\"word1\", \"word2\", ...]\n"
                f"}}\n"
                f"Output only the raw JSON array. Do not wrap in markdown or other text."
            )
            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": "You are a professional technical recruiter generating interview questions."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.5,
                    "max_tokens": 1000
                },
                timeout=7.0
            )
            if response.status_code == 200:
                res_data = response.json()["choices"][0]["message"]["content"].strip()
                if res_data.startswith("```"):
                    parts = res_data.split("```")
                    res_data = parts[1]
                    if res_data.startswith("json"):
                        res_data = res_data[4:]
                return json.loads(res_data.strip())
        except Exception as e:
            print(f"OpenAI question generation failed, falling back to local templates: {e}")
            
    import random
    selected = random.sample(base_pool, min(len(base_pool), count))
    return selected

@app.post("/api/session", response_model=SessionResponse)
def create_session(session_data: SessionCreate):
    session_id = str(uuid.uuid4())
    
    # Retrieve count requested, bounded 1 to 20
    count = session_data.question_count or 5
    count = max(1, min(20, count))
    
    if session_data.custom_questions and len(session_data.custom_questions) > 0:
        questions = session_data.custom_questions
        ideal_answers = ["" for _ in questions]
        custom_keywords = {}
    else:
        # Retrieve question pool for the category
        pool = QUESTIONS_POOL.get(session_data.category)
        is_custom = False
        if not pool:
            is_custom = True
            # Dynamically generate questions specifically for this custom category/role!
            pool = generate_questions_for_custom_role(session_data.category, 10)
            QUESTIONS_POOL[session_data.category] = pool
        
        # Ensure we have at least 50 questions in the pool to satisfy the queue requirement
        if not is_custom:
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
        custom_keywords = {q["question"]: q.get("keywords", []) for q in sampled if "question" in q}
    
    active_sessions[session_id] = {
        "category": session_data.category,
        "questions": questions,
        "answers": ["" for _ in range(len(questions))],
        "ideal_answers": ideal_answers,
        "custom_keywords": custom_keywords,
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
                "question_evaluations": saved_report.get("question_evaluations", []),
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
                "engagement_score": report.get("scores_breakdown", {}).get("engagement", 80),
                "question_evaluations": report.get("question_evaluations", [])
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
    
    # Import email services
    from app.services.email import send_otp_email
    
    # Attempt to dispatch SMTP email
    email_sent = send_otp_email(req.email, otp)
    
    if email_sent:
        return {"status": "success", "message": "OTP sent to your Gmail address successfully", "otp": "sent"}
    else:
        return {
            "status": "success",
            "message": "OTP generated. (Gmail SMTP not configured. OTP printed in backend console)",
            "otp": otp
        }

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
