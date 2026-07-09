from typing import Dict, Any, List
import os
import json

# Load questions and ideal answers from dynamic JSON database file inside scoring.py
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
QUESTIONS_DB_PATH = os.path.join(CURRENT_DIR, "questions_db.json")

try:
    with open(QUESTIONS_DB_PATH, "r") as f:
        QUESTIONS_POOL = json.load(f)
except Exception as e:
    print(f"Error loading questions_db.json in scoring.py: {e}")
    QUESTIONS_POOL = {}

def calculate_final_scores(session_history: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aggregates all frame and speech records in session_history to compute overall scores
    using a robust, explainable, and deterministic formula.
    """
    frame_records = session_history.get("frames", [])
    speech_records = session_history.get("speech", [])

    total_frames = len(frame_records)
    face_detected_frames = sum(1 for f in frame_records if f.get("face_detected", False))
    face_detection_ratio = face_detected_frames / total_frames if total_frames > 0 else 0.0

    eye_contact_frames = sum(1 for f in frame_records if f.get("eye_contact", True))
    eye_contact_ratio = eye_contact_frames / total_frames if total_frames > 0 else 0.0

    posture_scores = [f.get("posture_score", 100) for f in frame_records if f.get("face_detected", False)]
    avg_posture = sum(posture_scores) / len(posture_scores) if posture_scores else 100.0

    fidget_frames = sum(1 for f in frame_records if f.get("hand_fidgeting", False))
    fidget_ratio = fidget_frames / total_frames if total_frames > 0 else 0.0

    head_angles = [f.get("head_angle", 0.0) for f in frame_records if f.get("face_detected", False)]
    avg_head_angle = sum(head_angles) / len(head_angles) if head_angles else 0.0

    # Aggregate speech metrics
    total_words = 0
    total_fillers = 0
    wpm_list = []
    full_transcript = []
    
    rms_list = []
    rms_std_list = []

    for s in speech_records:
        total_words += s.get("word_count", 0)
        total_fillers += s.get("filler_words_count", 0)
        if s.get("wpm", 0) > 0:
            wpm_list.append(s.get("wpm"))
        if s.get("text"):
            full_transcript.append(s.get("text"))
        
        # Audio metrics
        if "audio_metrics" in s:
            rms_list.append(s["audio_metrics"].get("rms", 0.05))
            rms_std_list.append(s["audio_metrics"].get("rms_std", 0.03))

    avg_wpm = int(sum(wpm_list) / len(wpm_list)) if wpm_list else 0
    filler_ratio = total_fillers / total_words if total_words > 0 else 0.0
    avg_rms = sum(rms_list) / len(rms_list) if rms_list else 0.05
    avg_rms_std = sum(rms_std_list) / len(rms_std_list) if rms_std_list else 0.03
    full_transcript_str = " ".join(full_transcript)

    # 1. Parameter: Speech Clarity
    if total_words < 5:
        pacing_score = 0
        pause_score = 0
        filler_score = 0
    else:
        # Pacing
        if 110 <= avg_wpm <= 150:
            pacing_score = 100
        elif avg_wpm < 110:
            pacing_score = max(0, 100 - (110 - avg_wpm))
        else:
            pacing_score = max(0, 100 - (avg_wpm - 150) * 2)

        # Pauses based on punctuation density
        punctuation_count = sum(full_transcript_str.count(p) for p in [".", ",", "?", "!", ";"])
        pause_ratio = punctuation_count / total_words if total_words > 0 else 0.0
        if 0.05 <= pause_ratio <= 0.15:
            pause_score = 100
        elif pause_ratio < 0.05:
            pause_score = max(0, 100 - int((0.05 - pause_ratio) * 2000))
        else:
            pause_score = max(0, 100 - int((pause_ratio - 0.15) * 1000))

        # Filler words
        if filler_ratio < 0.02:
            filler_score = 100
        elif filler_ratio <= 0.12:
            filler_score = max(0, 100 - int((filler_ratio - 0.02) * 1000))
        else:
            filler_score = 0

    speech_clarity_score = int(0.4 * pacing_score + 0.3 * pause_score + 0.3 * filler_score)

    # 2. Parameter: Confidence (Voice tone + Facial stability)
    if not frame_records or face_detection_ratio < 0.1:
        facial_stability_score = 10
    else:
        if avg_head_angle <= 8.0:
            facial_stability_score = 100
        else:
            facial_stability_score = max(0, 100 - int((avg_head_angle - 8.0) * 5.0))

    if total_words < 5 or avg_rms < 0.01:
        voice_tone_score = 10 if total_words < 5 else 0
    else:
        if 0.04 <= avg_rms_std <= 0.15:
            voice_tone_score = 100
        elif avg_rms_std < 0.04:
            voice_tone_score = max(0, 100 - int((0.04 - avg_rms_std) * 1250))
        else:
            voice_tone_score = max(0, 100 - int((avg_rms_std - 0.15) * 500))

    confidence_score = int(0.5 * voice_tone_score + 0.5 * facial_stability_score)

    # 3. Parameter: Eye Contact
    eye_contact_score = int(eye_contact_ratio * 100)

    questions = session_history.get("questions", [])
    answers = session_history.get("answers", [])
    ideal_answers = session_history.get("ideal_answers", [])
    evals = evaluate_answers(questions, answers, ideal_answers)
    avg_quality = sum(e["quality_score"] for e in evals) / len(evals) if evals else 80.0

    gesture_score = int((1.0 - fidget_ratio) * 100)
    speech_density_score = min(100, max(20, int((total_words / 150.0) * 100))) if total_words > 0 else 0
    engagement_score = int(0.5 * avg_quality + 0.3 * gesture_score + 0.2 * speech_density_score)

    # Apply Rule-based corrections
    # Correct Confidence if eye contact is very low
    if eye_contact_score < 30:
        confidence_score = int(confidence_score * 0.6)

    # Standard formula
    overall_score = int(0.3 * confidence_score + 0.3 * speech_clarity_score + 0.2 * eye_contact_score + 0.2 * engagement_score)

    # Cap overall score if speech clarity is poor
    if speech_clarity_score < 50:
        overall_score = min(overall_score, 55)

    # Cap overall score if face detection is extremely low (no camera presence)
    if face_detection_ratio < 0.1:
        confidence_score = 10
        eye_contact_score = 0
        engagement_score = min(engagement_score, 20)
        overall_score = 10

    # Build feedback statements
    feedback = []
    
    # Speech Clarity Feedback
    if total_words < 5:
        feedback.append({
            "category": "Speech Clarity",
            "status": "Needs Improvement",
            "score": speech_clarity_score,
            "detail": "No substantial speech was detected. Please answer the questions clearly and audibly."
        })
    elif speech_clarity_score >= 80:
        feedback.append({
            "category": "Speech Clarity",
            "status": "Excellent",
            "score": speech_clarity_score,
            "detail": f"Excellent speech patterns! You spoke at {avg_wpm} WPM with clean pauses and very few filler words."
        })
    elif speech_clarity_score >= 60:
        feedback.append({
            "category": "Speech Clarity",
            "status": "Good",
            "score": speech_clarity_score,
            "detail": f"Good clarity ({avg_wpm} WPM). Try to further minimize vocal fillers and utilize structured pauses."
        })
    else:
        feedback.append({
            "category": "Speech Clarity",
            "status": "Needs Improvement",
            "score": speech_clarity_score,
            "detail": f"Pacing was {avg_wpm} WPM with higher filler words ({total_fillers} total). Practice slow, structured breathing."
        })

    # Confidence Feedback
    if face_detection_ratio < 0.1:
        feedback.append({
            "category": "Confidence",
            "status": "Needs Improvement",
            "score": confidence_score,
            "detail": "We could not evaluate confidence due to lack of face detection. Adjust your setup."
        })
    elif confidence_score >= 80:
        feedback.append({
            "category": "Confidence",
            "status": "Excellent",
            "score": confidence_score,
            "detail": "You showed great visual posture and highly confident vocal modulation/presence."
        })
    elif confidence_score >= 60:
        feedback.append({
            "category": "Confidence",
            "status": "Good",
            "score": confidence_score,
            "detail": "Solid confidence levels, though minor vocal tremor or excessive head movements were observed."
        })
    else:
        feedback.append({
            "category": "Confidence",
            "status": "Needs Improvement",
            "score": confidence_score,
            "detail": "Try to speak more dynamically and keep your head stable to project authority."
        })

    # Eye Contact Feedback
    if face_detection_ratio < 0.1:
        feedback.append({
            "category": "Eye Contact",
            "status": "Needs Improvement",
            "score": 0,
            "detail": "Adjust your camera so the tracking system can monitor your gaze orientation."
        })
    elif eye_contact_score >= 80:
        feedback.append({
            "category": "Eye Contact",
            "status": "Excellent",
            "score": eye_contact_score,
            "detail": "Superb eye contact! You looked directly at the camera, building strong interviewer engagement."
        })
    elif eye_contact_score >= 60:
        feedback.append({
            "category": "Eye Contact",
            "status": "Good",
            "score": eye_contact_score,
            "detail": "Good, but try to avoid looking away frequently when formulating your thoughts."
        })
    else:
        feedback.append({
            "category": "Eye Contact",
            "status": "Needs Improvement",
            "score": eye_contact_score,
            "detail": "Frequent gaze drift detected. Look directly at the webcam lens to engage your interviewer."
        })

    # Engagement Feedback
    if engagement_score >= 80:
        feedback.append({
            "category": "Engagement",
            "status": "Excellent",
            "score": engagement_score,
            "detail": "Highly interactive response style. Excellent structured arguments and physical gestures."
        })
    elif engagement_score >= 60:
        feedback.append({
            "category": "Engagement",
            "status": "Good",
            "score": engagement_score,
            "detail": "Good participation level. Try to use more industry keywords and keep hand gestures stable."
        })
    else:
        feedback.append({
            "category": "Engagement",
            "status": "Needs Improvement",
            "score": engagement_score,
            "detail": "Expand on your ideas and elaborate with specific case examples to build trust."
        })

    # Build the final scores breakdown dict
    breakdown = {
        "speech_clarity": speech_clarity_score,
        "confidence": confidence_score,
        "eye_contact": eye_contact_score,
        "engagement": engagement_score
    }
    
    metrics = {
        "eye_contact_ratio": round(eye_contact_ratio, 2),
        "average_posture": round(avg_posture, 2),
        "fidget_ratio": round(fidget_ratio, 2),
        "wpm": avg_wpm,
        "total_words": total_words,
        "filler_words_total": total_fillers
    }

    ai_summary = generate_ai_feedback(
        session_history.get("category", "General"),
        overall_score,
        breakdown,
        metrics,
        full_transcript_str
    )

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
                f"- Speech Clarity: {breakdown.get('speech_clarity')}/100\n"
                f"- Confidence: {breakdown.get('confidence')}/100\n"
                f"- Eye Contact: {breakdown.get('eye_contact')}/100\n"
                f"- Engagement: {breakdown.get('engagement')}/100\n"
                f"- Speaking Speed: {metrics.get('wpm')} WPM\n"
                f"- Total Words: {metrics.get('total_words')}\n"
                f"- Filler Words Total: {metrics.get('filler_words_total')}\n"
                f"- Eye Contact Ratio: {int(metrics.get('eye_contact_ratio', 1.0) * 100)}%\n"
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
    if overall_score >= 80:
        summary_text = f"**Executive Summary:** You delivered a highly confident and structured mock interview for the '{category}' role. Your speech clarity and presence reflect professional capabilities."
    elif overall_score >= 60:
        summary_text = f"**Executive Summary:** You have a solid foundation for the '{category}' role. Improving speech pacing, maintaining steady camera eye contact, and minimizing filler words will boost your overall rating."
    else:
        summary_text = f"**Executive Summary:** Consistent practice is highly recommended for this role. Focus on keeping steady eye contact, raising speaking clarity, and structuring answers using key terminology."

    strengths = []
    improvements = []
    
    # Eye Contact
    if breakdown.get('eye_contact', 80) >= 80:
        strengths.append("• **Direct Eye Contact:** You maintained excellent eye contact, conveying engagement and authenticity.")
    else:
        improvements.append("• **Eye Contact:** Practice looking directly at the camera lens rather than looking away when formulating ideas.")

    # Speech Clarity
    if breakdown.get('speech_clarity', 80) >= 80:
        strengths.append(f"• **Clear Speech Pacing:** You spoke with optimal pacing ({metrics.get('wpm')} WPM) and minimal filler words.")
    else:
        improvements.append("• **Speech Clarity:** Reduce filler words and practice taking clean silent pauses instead of verbal ticks.")

    # Confidence
    if breakdown.get('confidence', 80) >= 80:
        strengths.append("• **Confident Vocal Tone:** You spoke with a stable volume and pleasant vocal inflection, projecting professional authority.")
    else:
        improvements.append("• **Vocal Tremor/Postural Shift:** Focus on sitting upright and modulating your voice to show dynamic vocal energy.")

    # Engagement
    if breakdown.get('engagement', 80) >= 80:
        strengths.append("• **Dynamic Engagement:** You structured your answers with key industry concepts and appropriate gesture stability.")
    else:
        improvements.append("• **Answer Structuring:** Practice the STAR method (Situation, Task, Action, Result) to write structured and complete responses.")

    # Finalize lists
    if not strengths:
        strengths.append("• **Completion:** Successfully finished mock sessions, representing a dedication to practice.")
    if not improvements:
        improvements.append("• **Advanced Depth:** Elaborate on advanced design pattern nuances and concrete KPIs.")

    strengths_str = "\n".join(strengths[:2])
    improvements_str = "\n".join(improvements[:2])

    local_report = (
        f"{summary_text}\n\n"
        f"**Core Strengths:**\n"
        f"{strengths_str}\n\n"
        f"**Key Areas to Improve:**\n"
        f"{improvements_str}\n\n"
        f"**Actionable Next Steps:**\n"
        f"1. Practice structured breathing exercises to reduce speed when nervous.\n"
        f"2. Place a small visual marker near your camera to maintain stable eye contact.\n"
        f"3. Record response answers using specific keywords for mock verification."
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

def evaluate_answers(questions: list, answers: list, ideal_answers: list = None) -> list:
    import httpx
    evals = []
    if not questions:
        return evals

    api_key = os.getenv("OPENAI_API_KEY")

    for idx, (q, ans) in enumerate(zip(questions, answers)):
        ans_clean = ans.strip()
        
        # 1. Resolve ideal answer
        ideal_ans = ""
        if ideal_answers and idx < len(ideal_answers):
            ideal_ans = ideal_answers[idx]
        
        # Try lookup in QUESTIONS_POOL if still empty
        if not ideal_ans:
            for cat_list in QUESTIONS_POOL.values():
                for item in cat_list:
                    if item.get("question") == q:
                        ideal_ans = item.get("ideal_answer", "")
                        break
                if ideal_ans:
                    break
        
        # Default fallback if no preloaded answer exists
        if not ideal_ans:
            ideal_ans = "The response should demonstrate key industry knowledge, clear articulation of technical steps, and structured examples from prior experience."

        # If answer is empty or too short
        if not ans_clean or len(ans_clean) < 12:
            evals.append({
                "question": q,
                "user_answer": ans_clean if ans_clean else "No answer recorded.",
                "quality_score": 0,
                "feedback": "Answer was too brief or not captured. Try to elaborate on technical details and use industry terminology.",
                "ideal_answer": ideal_ans,
                "correctness_score": 0,
                "correctness_feedback": "No response was detected to match with the ideal answer. Ensure your microphone is properly connected."
            })
            continue

        # 2. Extract keywords for local scoring & feedback fallback
        keywords = []
        for cat_list in QUESTIONS_POOL.values():
            for item in cat_list:
                if item.get("question") == q:
                    keywords = item.get("keywords", [])
                    break
            if keywords:
                break
        
        if not keywords:
            clean_ideal_words = [w.strip(".,;:?!()\"'").lower() for w in ideal_ans.split()]
            stop_words = {"their", "there", "about", "would", "should", "could", "these", "those", "other", "where", "which"}
            keywords = list({w for w in clean_ideal_words if len(w) > 4 and w not in stop_words})[:5]

        matched_keys = [k for k in keywords if k.lower() in ans_clean.lower()]
        
        correctness_score = 0
        correctness_feedback = ""
        
        # Try OpenAI Path
        if api_key:
            try:
                prompt = (
                    f"Compare the candidate's answer against the ideal answer for the following question:\n"
                    f"Question: \"{q}\"\n"
                    f"Candidate's Answer: \"{ans_clean}\"\n"
                    f"Ideal Answer Key: \"{ideal_ans}\"\n\n"
                    f"Evaluate semantic correctness, accuracy, and completeness. Output EXACTLY in valid JSON format:\n"
                    f"{{\n"
                    f"  \"correctness_score\": <int between 0 and 100>,\n"
                    f"  \"correctness_feedback\": \"<constructive feedback of 1-2 sentences comparing both answers and highlighting what key concepts were correct and what was missing relative to the ideal key>\"\n"
                    f"}}\n"
                    f"Do not include any other text, markdown headers, or JSON wrapping outside the raw curly braces."
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
                            {"role": "system", "content": "You are a precise technical interviewer grading candidate answers."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.2,
                        "max_tokens": 200
                    },
                    timeout=5.0
                )
                if response.status_code == 200:
                    res_data = response.json()["choices"][0]["message"]["content"].strip()
                    parsed = json.loads(res_data)
                    correctness_score = int(parsed.get("correctness_score", 0))
                    correctness_feedback = parsed.get("correctness_feedback", "")
            except Exception as e:
                print(f"OpenAI answer comparison failed, falling back to local grading: {e}")

        # Local Fallback Path (if OpenAI key missing, failed, or timed out)
        if correctness_score == 0:
            cand_words = {w.strip(".,;:?!()\"'").lower() for w in ans_clean.split()}
            ideal_words = {w.strip(".,;:?!()\"'").lower() for w in ideal_ans.split()}
            stop_words = {"the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "to", "for", "in", "on", "at", "by", "of", "with", "that", "this", "it", "you", "i", "we", "they", "he", "she", "have", "has", "had", "do", "does", "did", "as", "from", "at"}
            
            cand_clean = cand_words - stop_words
            ideal_clean = ideal_words - stop_words
            
            overlap = cand_clean.intersection(ideal_clean)
            
            keyword_ratio = len(matched_keys) / len(keywords) if keywords else 0.0
            overlap_ratio = len(overlap) / len(ideal_clean) if ideal_clean else 0.0
            
            correctness_score = int((keyword_ratio * 60) + (overlap_ratio * 40))
            
            if len(ans_clean) > 100:
                correctness_score = min(100, correctness_score + 15)
            elif len(ans_clean) < 40:
                correctness_score = max(10, correctness_score - 10)
                
            correctness_score = max(10, min(100, correctness_score))
            
            missing_keys = [k for k in keywords if k not in matched_keys]
            if correctness_score >= 80:
                correctness_feedback = f"Excellent match! Your response is highly accurate and discussed key concepts including: {', '.join(matched_keys)}."
            elif correctness_score >= 55:
                correctness_feedback = f"Moderate accuracy. You hit key points like {', '.join(matched_keys)}, but you missed details regarding: {', '.join(missing_keys[:2]) if missing_keys else 'the core domain'}. Try to explain these key concepts."
            else:
                correctness_feedback = f"Low match. To hit the ideal response, please incorporate key terminology such as: {', '.join(keywords[:3])}."

        # Quality score aligns directly with accuracy correctness score
        quality_score = correctness_score

        # Main overall feedback
        if quality_score >= 80:
            main_feedback = f"Excellent technical answer! You clearly addressed the prompt and demonstrated solid understanding of the concepts."
        elif quality_score >= 55:
            main_feedback = f"Good answer, but could be more complete. Try to elaborate on technical details and explain how the components interact."
        else:
            main_feedback = "Your answer was somewhat generic or off-topic. Focus on using specific industry terms and structuring your explanation clearly."

        evals.append({
            "question": q,
            "user_answer": ans_clean,
            "quality_score": quality_score,
            "feedback": main_feedback,
            "ideal_answer": ideal_ans,
            "correctness_score": correctness_score,
            "correctness_feedback": correctness_feedback
        })
        
    return evals
