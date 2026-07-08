from typing import Dict, Any, List

def calculate_final_scores(session_history: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aggregates all frame and speech records in session_history to compute overall scores
    and generate personalized improvement suggestions.
    """
    frame_records = session_history.get("frames", [])
    speech_records = session_history.get("speech", [])

    # Initialize default scores
    confidence_score = 80
    communication_score = 80
    behavioral_score = 80

    eye_contact_ratio = 1.0
    avg_posture = 100.0
    fidget_ratio = 0.0
    emotion_counts = {"confident": 0, "neutral": 0, "anxious": 0}
    
    # 1. Aggregate Vision Metrics
    if frame_records:
        total_frames = len(frame_records)
        detected_frames = [f for f in frame_records if f.get("face_detected", False)]
        total_detected = len(detected_frames)
        
        eye_contact_frames = sum(1 for f in frame_records if f.get("eye_contact", True))
        
        # Average posture should ONLY average frames where the candidate was actually present
        posture_scores = [f.get("posture_score", 100) for f in detected_frames]
        avg_posture = sum(posture_scores) / total_detected if total_detected > 0 else 100.0
        
        fidget_frames = sum(1 for f in frame_records if f.get("hand_fidgeting", False))
        
        for f in frame_records:
            emo = f.get("dominant_emotion", "neutral")
            emotion_counts[emo] = emotion_counts.get(emo, 0) + 1
            
        eye_contact_ratio = eye_contact_frames / total_frames if total_frames > 0 else 1.0
        fidget_ratio = fidget_frames / total_frames if total_frames > 0 else 0.0

    # 2. Aggregate Speech Metrics
    total_words = 0
    total_fillers = 0
    wpm_list = []
    full_transcript = []
    
    for s in speech_records:
        total_words += s.get("word_count", 0)
        total_fillers += s.get("filler_words_count", 0)
        if s.get("wpm", 0) > 0:
            wpm_list.append(s.get("wpm"))
        if s.get("text"):
            full_transcript.append(s.get("text"))

    avg_wpm = int(sum(wpm_list) / len(wpm_list)) if wpm_list else 0
    filler_ratio = total_fillers / total_words if total_words > 0 else 0.0

    # 3. Calculate Scores (0 - 100 scale)
    # Confidence Score is based on: Eye contact (40%), Posture (30%), Emotion/Fidgeting (30%)
    eye_contact_factor = eye_contact_ratio * 100
    fidget_penalty = fidget_ratio * 50
    anxious_penalty = (emotion_counts.get("anxious", 0) / len(frame_records)) * 40 if frame_records else 0
    
    # If no frames were captured or no face was detected, confidence score is 0
    has_detected_face = any(f.get("face_detected", False) for f in frame_records)
    if not frame_records or not has_detected_face:
        confidence_score = 0
    else:
        confidence_score = int(min(100, max(0, (eye_contact_factor * 0.4) + (avg_posture * 0.3) + (30 - fidget_penalty - anxious_penalty))))
        # If they never looked at the camera once, apply a heavy penalty
        if eye_contact_ratio == 0:
            confidence_score = int(confidence_score * 0.3) # Heavy penalty (reduced by 70%)

    # Communication Score is based on: WPM pacing (50%), Filler word density (50%)
    # If the user barely spoke, we penalize communication heavily.
    if total_words < 2:
        pacing_score = 0
        filler_score = 0
        communication_score = 0
    elif total_words < 6:
        pacing_score = 10
        filler_score = 10
        communication_score = 10
    else:
        # Ideal WPM is 110 - 150.
        if 115 <= avg_wpm <= 145:
            pacing_score = 100
        elif 95 <= avg_wpm < 115 or 145 < avg_wpm <= 165:
            pacing_score = 80
        else:
            pacing_score = 55
            
        # Gentler, realistic filler words scoring penalty capped at 50 minimum
        filler_score = max(50, 100 - (filler_ratio * 300))
        communication_score = int((pacing_score * 0.5) + (filler_score * 0.5))

    # Behavioral Score is based on: Posture correctness (60%), Gesture appropriate stability (40%)
    if not frame_records or not has_detected_face:
        behavioral_score = 0
    else:
        behavioral_score = int(min(100, max(0, (avg_posture * 0.6) + ((1.0 - fidget_ratio) * 40))))

    # Overall Score (average of the three)
    overall_score = int((confidence_score + communication_score + behavioral_score) / 3.0)

    # 4. Generate Personalized Feedback
    feedback = []
    
    # Eye contact feedback
    if not frame_records or not has_detected_face:
        feedback.append({
            "category": "Eye Contact",
            "status": "Not Detected",
            "score": 0,
            "detail": "No face was detected during the session. Please sit directly in front of the camera."
        })
    elif eye_contact_ratio > 0.85:
        feedback.append({
            "category": "Eye Contact",
            "status": "Excellent",
            "score": int(eye_contact_ratio * 100),
            "detail": "You maintained excellent eye contact. This builds strong trust and shows attentiveness."
        })
    elif eye_contact_ratio > 0.6:
        feedback.append({
            "category": "Eye Contact",
            "status": "Moderate",
            "score": int(eye_contact_ratio * 100),
            "detail": "Good, but try to look at the camera more consistently when speaking. Avoid looking around the room."
        })
    else:
        feedback.append({
            "category": "Eye Contact",
            "status": "Needs Improvement",
            "score": int(eye_contact_ratio * 100),
            "detail": "Your gaze drifted away frequently. Look directly at the webcam to engage the interviewer."
        })

    # Posture feedback
    if not frame_records or not has_detected_face or avg_posture == 0:
        feedback.append({
            "category": "Posture",
            "status": "Not Detected",
            "score": 0,
            "detail": "Your body/shoulders were not visible. Adjust your camera so your chest and shoulders are in the frame."
        })
    elif avg_posture > 90:
        feedback.append({
            "category": "Posture",
            "status": "Excellent",
            "score": int(avg_posture),
            "detail": "Your posture was upright and stable. It conveys poise, professionalism, and high confidence."
        })
    elif avg_posture > 75:
        feedback.append({
            "category": "Posture",
            "status": "Good",
            "score": int(avg_posture),
            "detail": "Generally good posture, but watch out for occasional leaning or shoulder slumping."
        })
    else:
        feedback.append({
            "category": "Posture",
            "status": "Needs Improvement",
            "score": int(avg_posture),
            "detail": "You showed significant slumping or uneven shoulders. Try sitting straight to look energetic."
        })

    # Speech pacing feedback
    if total_words < 2:
        feedback.append({
            "category": "Speaking Pace",
            "status": "No Speech Detected",
            "score": 0,
            "detail": "No speech was detected. Please answer the questions audibly."
        })
        feedback.append({
            "category": "Clarity",
            "status": "No Speech Detected",
            "score": 0,
            "detail": "We were unable to evaluate your clarity because no answers were spoken."
        })
    elif total_words < 6:
        feedback.append({
            "category": "Speaking Pace",
            "status": "Insufficient Speech",
            "score": 10,
            "detail": "Your answers were too short. Try to elaborate and speak for at least 30-45 seconds per question."
        })
        feedback.append({
            "category": "Clarity",
            "status": "Insufficient Speech",
            "score": 10,
            "detail": "We need more speech data to accurately analyze your vocabulary and pronunciation clarity."
        })
    else:
        if 110 <= avg_wpm <= 150:
            feedback.append({
                "category": "Speaking Pace",
                "status": "Excellent",
                "score": 95,
                "detail": f"You spoke at an average of {avg_wpm} words per minute, which is the perfect conversational rate."
            })
        elif avg_wpm > 150:
            feedback.append({
                "category": "Speaking Pace",
                "status": "Too Fast",
                "score": 65,
                "detail": f"Your speed was {avg_wpm} WPM. Try slowing down and using intentional pauses for emphasis."
            })
        else:
            feedback.append({
                "category": "Speaking Pace",
                "status": "Too Slow",
                "score": 60,
                "detail": f"Your speed was {avg_wpm} WPM. Try speaking more dynamically to keep interest high."
            })

        # Filler word feedback
        if filler_ratio < 0.03:
            feedback.append({
                "category": "Clarity",
                "status": "Excellent",
                "score": 98,
                "detail": "You spoke clearly with very few filler words, which makes your answers sound polished."
            })
        elif filler_ratio < 0.07:
            feedback.append({
                "category": "Clarity",
                "status": "Moderate",
                "score": 75,
                "detail": f"You had a few filler words ({total_fillers} total). Take pauses instead of filling silence with 'um' or 'like'."
            })
        else:
            feedback.append({
                "category": "Clarity",
                "status": "Needs Work",
                "score": 50,
                "detail": f"Filler words represented {int(filler_ratio*100)}% of your vocabulary. Practice pausing before you speak."
            })

    # Calculate answer content evaluations
    questions = session_history.get("questions", [])
    answers = session_history.get("answers", [])
    evals = evaluate_answers(questions, answers)
    
    # Factor answer quality into communication score (if answers were provided)
    if evals:
        if total_words < 2:
            communication_score = 0
        else:
            avg_quality = sum(e["quality_score"] for e in evals) / len(evals)
            communication_score = int((communication_score * 0.6) + (avg_quality * 0.4))
        # Re-average overall score
        overall_score = int((confidence_score + communication_score + behavioral_score) / 3.0)

    # 4. Generate AI Executive Coach Feedback
    breakdown = {
        "confidence": confidence_score,
        "communication": communication_score,
        "behavioral": behavioral_score
    }
    metrics = {
        "eye_contact_ratio": round(eye_contact_ratio, 2),
        "average_posture": round(avg_posture, 2),
        "fidget_ratio": round(fidget_ratio, 2),
        "wpm": avg_wpm,
        "total_words": total_words,
        "filler_words_total": total_fillers
    }
    full_transcript_str = " ".join(full_transcript)
    
    ai_summary = generate_ai_feedback(
        session_history.get("category", "General"),
        overall_score,
        breakdown,
        metrics,
        full_transcript_str
    )

    # Construct the response
    return {
        "overall_score": overall_score,
        "scores_breakdown": breakdown,
        "metrics": metrics,
        "emotions_timeline": list(session_history.get("emotions", ["confident", "neutral"])),
        "feedback": feedback,
        "transcript": full_transcript_str,
        "question_evaluations": evals,
        "ai_coaching_summary": ai_summary
    }

def generate_ai_feedback(category: str, overall_score: int, breakdown: Dict[str, int], metrics: Dict[str, Any], transcript: str) -> str:
    """
    Generates a personalized executive-level coaching report based on interview performance.
    Attempts OpenAI GPT if API key is present; otherwise falls back to a rules-based NLP generator.
    """
    import os
    import httpx
    
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            prompt = (
                f"You are an expert AI Interview Coach. Provide a constructive, professional feedback report "
                f"for a candidate who completed a mock interview for a '{category}' position.\n\n"
                f"Performance Metrics:\n"
                f"- Overall Rating: {overall_score}/100\n"
                f"- Confidence (Visuals/Gaze): {breakdown.get('confidence')}/100\n"
                f"- Communication (Delivery/Words): {breakdown.get('communication')}/100\n"
                f"- Behavioral (Posture/Body): {breakdown.get('behavioral')}/100\n"
                f"- Speaking Speed: {metrics.get('wpm')} WPM\n"
                f"- Total Words: {metrics.get('total_words')}\n"
                f"- Filler Words Total: {metrics.get('filler_words_total')}\n"
                f"- Eye Contact: {int(metrics.get('eye_contact_ratio', 1.0) * 100)}%\n"
                f"- Posture Score: {int(metrics.get('average_posture', 100))}%\n\n"
                f"Answers Transcript:\n"
                f"\"{transcript}\"\n\n"
                f"Write a concise, professional report structured as:\n"
                f"1. Executive Summary: 2-3 sentences summarizing performance and presence.\n"
                f"2. Core Strengths: 2 bullet points highlighting specific successes.\n"
                f"3. Key Areas to Improve: 2 bullet points with clear, actionable advice.\n"
                f"Ensure the tone is encouraging and focused on growth. Do not include markdown headers other than bold text. Keep it under 250 words."
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
                        {"role": "system", "content": "You are a professional executive interview coach."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 400
                },
                timeout=12.0
            )
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"].strip()
            else:
                print(f"OpenAI feedback request failed (Status {response.status_code}): {response.text}")
        except Exception as e:
            print(f"OpenAI feedback connection error: {str(e)}")

    # Local rules-based high-fidelity fallback generator
    summary_text = ""
    if overall_score >= 82:
        summary_text = f"**Executive Summary:** You delivered a highly confident and structured mock interview for the '{category}' role. Your posture and delivery reflect professional presence and strong capabilities. With a few minor adjustments to expand your technical concepts, you are ready for actual interviews."
    elif overall_score >= 65:
        summary_text = f"**Executive Summary:** You have a solid foundation for the '{category}' role and responded clearly. Improving your eye contact, rolling your shoulders back to maintain an upright posture, and substituting silent pauses for filler words will boost your overall rating."
    else:
        summary_text = f"**Executive Summary:** Consistent practice is highly recommended for this role. Focus on speaking audibly, maintaining steady eye contact with the camera lens, and structuring your answers with industry-specific terms to build a persuasive narrative."

    # Visual Presence
    vis_score = breakdown.get('confidence', 80)
    strengths = []
    improvements = []
    
    if vis_score >= 80:
        strengths.append("• **Consistent Eye Contact:** You did a great job looking at the camera lens, conveying authenticity and engagement.")
    else:
        improvements.append("• **Camera Presence:** Your gaze drifted frequently. Try looking directly at the camera lens rather than looking around the room to formulate your thoughts.")

    # Posture
    posture_score = metrics.get('average_posture', 100)
    if posture_score >= 85:
        strengths.append("• **Professional Posture:** You maintained an upright, open shoulder alignment, which projects energy and confidence.")
    else:
        improvements.append("• **Upright Alignment:** Your shoulders slouched or drifted out of frame. Sit back with your chest open to improve vocal resonance and visual presence.")

    # Verbal
    wpm = metrics.get('wpm', 130)
    fillers = metrics.get('filler_words_total', 0)
    if breakdown.get('communication', 80) >= 80:
        strengths.append(f"• **Excellent Pacing:** You spoke at a highly conversational pace ({wpm} WPM) with minimal verbal pauses.")
    else:
        if wpm > 150:
            improvements.append(f"• **Slow Down Pacing:** You spoke at a rapid {wpm} WPM. Take deep breaths and introduce intentional pauses between key concepts.")
        elif wpm < 95:
            improvements.append(f"• **Project Energy:** Your pace was somewhat slow ({wpm} WPM). Practice dynamic voice modulation to keep the interviewer engaged.")
        
        if fillers > 2:
            improvements.append(f"• **Reduce Filler Words:** You used {fillers} filler words. Practice taking brief silent pauses instead of filling the silence with 'um' or 'like'.")

    # Finalize Strengths and Improvements lists
    if not strengths:
        strengths.append("• **Completion:** You successfully completed the mock session, demonstrating dedication and technical effort.")
    if not improvements:
        improvements.append("• **Technical Depth:** Further expand on your answers with advanced architectural patterns and case studies.")

    strengths_str = "\n".join(strengths[:2])
    improvements_str = "\n".join(improvements[:2])

    local_report = (
        f"{summary_text}\n\n"
        f"**Core Strengths:**\n"
        f"{strengths_str}\n\n"
        f"**Key Areas to Improve:**\n"
        f"{improvements_str}\n\n"
        f"**Actionable Next Steps:**\n"
        f"1. record another mock session focusing on taking structured pauses between ideas.\n"
        f"2. Align your camera directly at eye-level to make natural eye contact.\n"
        f"3. Practice structuring technical answers using key engineering/industry keywords."
    )
    return local_report

# Keywords dictionary matching each question (expanded pool)
QUESTION_KEYWORDS = {
    # Software Engineer
    "Can you explain the difference between a Stateful and Stateless widget in Flutter?": [
        "setState", "mutable", "immutable", "rebuild", "lifecycle", "state"
    ],
    "What is the difference between a REST API and WebSockets, and when would you use each?": [
        "http", "connection", "real-time", "handshake", "persistent", "stateless"
    ],
    "How do you handle state management in a large-scale mobile application?": [
        "provider", "bloc", "riverpod", "redux", "inherited", "architecture"
    ],
    "What is the role of an index in a database, and how does it speed up queries?": [
        "index", "lookup", "speed", "scan", "btree", "performance"
    ],
    "Can you explain the concept of Clean Architecture and why it is useful?": [
        "clean", "decouple", "independent", "layer", "testable", "solid"
    ],
    "What is the difference between synchronous and asynchronous programming, and how do you handle concurrency?": [
        "async", "await", "sync", "thread", "future", "promise", "blocking"
    ],
    "How do you optimize the performance of a slow mobile or web application?": [
        "optimize", "cache", "minify", "rendering", "profile", "lazy"
    ],
    "What are the key differences between SQL and NoSQL databases?": [
        "schema", "relational", "nosql", "document", "scale", "structured"
    ],

    # Product Manager
    "How do you decide what features to prioritize in a product roadmap when multiple stakeholders disagree?": [
        "priority", "data", "alignment", "impact", "effort", "framework"
    ],
    "Can you describe a time when a product launch failed, and what you learned from it?": [
        "learn", "fail", "launch", "metrics", "test", "feedback"
    ],
    "How do you define and measure success for a new feature?": [
        "metrics", "kpi", "conversion", "retention", "adoption", "goal"
    ],
    "How do you conduct user research to identify pain points for a new product?": [
        "research", "interview", "survey", "persona", "journey", "insights"
    ],
    "How would you handle a situation where engineering says a key feature cannot be built on time?": [
        "negotiate", "scope", "compromise", "backlog", "timeline", "phased"
    ],
    "What metrics would you track for a ride-sharing app like Uber to measure passenger retention?": [
        "retention", "mau", "cohort", "frequency", "churn", "engagement"
    ],
    "Can you explain how you would design an MVP (Minimum Viable Product) for a new social media application?": [
        "mvp", "core", "value", "prototype", "validate", "feedback"
    ],
    "How do you balance long-term product vision with short-term business demands?": [
        "balance", "roadmap", "technical debt", "strategy", "revenue", "compromise"
    ],

    # HR Manager
    "How do you handle conflict resolution between two high-performing team members who refuse to collaborate?": [
        "listen", "talk", "mediator", "empathy", "resolution", "collaborate"
    ],
    "What strategies do you use to improve employee retention in a high-turnover industry?": [
        "retention", "culture", "benefits", "growth", "feedback", "engage"
    ],
    "How do you evaluate cultural fit during an interview?": [
        "values", "collaboration", "behavioral", "scenario", "match", "align"
    ],
    "How do you handle a situation where an employee complains about their manager's behavior?": [
        "investigate", "listen", "neutral", "escalate", "confidential", "policy"
    ],
    "What steps would you take to design and implement a new diversity and inclusion program?": [
        "diversity", "inclusion", "training", "metrics", "equity", "hiring"
    ],
    "How do you balance supporting the company's business goals with advocating for employee well-being?": [
        "balance", "wellness", "advocate", "burnout", "productivity", "mental health"
    ],
    "What is your approach to conducting performance reviews and giving constructive feedback?": [
        "feedback", "growth", "performance", "constructive", "goals", "objective"
    ],
    "How do you manage onboarding for a fully remote team to make them feel integrated?": [
        "onboarding", "remote", "communication", "welcome", "buddy", "engagement"
    ],

    # Data Analyst
    "What is the difference between supervised and unsupervised learning, and can you give an example of each?": [
        "labeled", "cluster", "classification", "regression", "unlabeled", "data"
    ],
    "How do you handle missing or noisy data in a dataset before performing analysis?": [
        "impute", "clean", "outliers", "drop", "median", "mean"
    ],
    "Can you explain the difference between a join and a union in SQL?": [
        "join", "union", "columns", "rows", "horizontal", "vertical"
    ],
    "What is the difference between correlation and causation, and why is it important in analysis?": [
        "correlation", "causation", "relation", "cause", "spurious", "variable"
    ],
    "How do you choose between a bar chart, a line chart, and a scatter plot for data visualization?": [
        "visualization", "bar", "line", "scatter", "trend", "distribution"
    ],
    "What are Type I and Type II errors in hypothesis testing?": [
        "hypothesis", "type i", "type ii", "null", "false positive", "false negative"
    ],
    "Can you explain the difference between A/B testing and multivariate testing?": [
        "ab test", "multivariate", "variant", "conversion", "statistically", "significance"
    ],
    "How do you communicate complex technical insights to non-technical business stakeholders?": [
        "visualize", "simplify", "jargon", "storytelling", "business value", "actionable"
    ]
}

def evaluate_answers(questions: list, answers: list) -> list:
    evals = []
    if not questions:
        return evals
        
    for q, ans in zip(questions, answers):
        ans_clean = ans.strip()
        if not ans_clean or len(ans_clean) < 12:
            evals.append({
                "question": q,
                "user_answer": ans_clean if ans_clean else "No answer recorded.",
                "quality_score": 0,
                "feedback": "Answer was too brief or not captured. Try to elaborate on technical details and use industry terminology."
            })
            continue
            
        keywords = QUESTION_KEYWORDS.get(q, ["experience", "project", "work", "team"])
        matched_keys = [k for k in keywords if k.lower() in ans_clean.lower()]
        match_count = len(matched_keys)
        
        if match_count >= 3:
            score = 92
            feedback = f"Excellent technical answer! You discussed key concepts including: {', '.join(matched_keys)}."
        elif match_count >= 1:
            score = 75
            feedback = f"Good answer, but could be more comprehensive. You mentioned {', '.join(matched_keys)}, but try to also elaborate on: {', '.join([k for k in keywords if k not in matched_keys][:2])}."
        else:
            score = 50
            feedback = "Your answer was somewhat generic. Make sure to use specific industry terms and address the technical concepts directly."
            
        evals.append({
            "question": q,
            "user_answer": ans_clean,
            "quality_score": score,
            "feedback": feedback
        })
    return evals
