import uuid
import os
import shutil
import random
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List

from app.models.schemas import (
    SessionCreate, SessionResponse, FrameResponse, AudioResponse, ReportResponse
)
from app.services.vision import analyze_frame
from app.services.speech import transcribe_audio
from app.services.scoring import calculate_final_scores

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
        "frame_count": 0
    }
    
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
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session = active_sessions[session_id]
    
    # Calculate scores
    report = calculate_final_scores(session)
    return report

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
