from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class SessionCreate(BaseModel):
    category: str = Field(..., example="Software Engineer")
    custom_questions: Optional[List[str]] = Field(default=None, example=["Tell me about yourself"])
    user_id: Optional[str] = Field(default=None, example="user-uuid-123")
    question_count: Optional[int] = Field(default=5, example=5)

class UserSignup(BaseModel):
    email: str
    name: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    email: str
    otp: str
    new_password: str

class ProfileUpdate(BaseModel):
    name: str
    education: str
    experience: str
    currentRole: str
    skills: List[str]

class SessionResponse(BaseModel):
    session_id: str
    category: str
    status: str
    questions: List[str]

class QuestionEvaluation(BaseModel):
    question: str = Field(default="", alias="question")
    user_answer: str = Field(default="", alias="user_answer")
    quality_score: int
    feedback: str
    ideal_answer: str = Field(default="", alias="ideal_answer")
    correctness_score: int = Field(default=0, alias="correctness_score")
    correctness_feedback: str = Field(default="", alias="correctness_feedback")

    # Support string types in Pydantic v2
    class Config:
        populate_by_name = True

class FrameResponse(BaseModel):
    face_detected: bool
    eye_contact: bool
    posture_score: int
    hand_fidgeting: bool
    dominant_emotion: str
    head_angle: float
    alert: Optional[str] = None

class AudioResponse(BaseModel):
    text: str
    word_count: int
    wpm: int
    filler_words_count: int
    filler_words_breakdown: Dict[str, int]
    suggestions: List[str]

class FeedbackItem(BaseModel):
    category: str
    status: str
    score: int
    detail: str

class ScoresBreakdown(BaseModel):
    speech_clarity: int
    confidence: int
    eye_contact: int
    engagement: int

class MetricsDetail(BaseModel):
    eye_contact_ratio: float
    average_posture: float
    fidget_ratio: float
    wpm: int
    total_words: int
    filler_words_total: int

class ReportResponse(BaseModel):
    overall_score: int
    scores_breakdown: ScoresBreakdown
    metrics: MetricsDetail
    emotions_timeline: List[str]
    feedback: List[FeedbackItem]
    transcript: str
    question_evaluations: List[QuestionEvaluation]
