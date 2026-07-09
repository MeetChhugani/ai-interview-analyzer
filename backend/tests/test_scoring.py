import sys
import os

# Append the app directory to sys.path so we can run the test directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.scoring import calculate_final_scores

def test_scoring_with_good_metrics():
    # Arrange: Mock session history with excellent behavior and clear speech
    session_history = {
        "category": "Software Engineer",
        "frames": [
            {"face_detected": True, "eye_contact": True, "posture_score": 100, "hand_fidgeting": False, "dominant_emotion": "confident", "head_angle": 3.0},
            {"face_detected": True, "eye_contact": True, "posture_score": 98, "hand_fidgeting": False, "dominant_emotion": "confident", "head_angle": 2.5},
            {"face_detected": True, "eye_contact": True, "posture_score": 100, "hand_fidgeting": False, "dominant_emotion": "confident", "head_angle": 2.0},
            {"face_detected": True, "eye_contact": True, "posture_score": 95, "hand_fidgeting": False, "dominant_emotion": "neutral", "head_angle": 3.5},
            {"face_detected": True, "eye_contact": True, "posture_score": 100, "hand_fidgeting": False, "dominant_emotion": "confident", "head_angle": 2.8},
        ],
        "speech": [
            {
                "word_count": 80,
                "wpm": 120,
                "filler_words_count": 1,
                "text": "I am a software engineer. I build tools and APIs.",
                "audio_metrics": {"rms": 0.08, "rms_std": 0.06, "zcr_var": 0.012}
            },
            {
                "word_count": 90,
                "wpm": 130,
                "filler_words_count": 0,
                "text": "I have experience with Python. We use FastAPI for clean architecture.",
                "audio_metrics": {"rms": 0.09, "rms_std": 0.05, "zcr_var": 0.010}
            }
        ],
        "emotions": ["confident", "confident", "confident", "neutral", "confident"],
        "frame_count": 5
    }

    # Act
    report = calculate_final_scores(session_history)

    # Assert
    assert report["overall_score"] >= 80, f"Expected high overall score, got {report['overall_score']}"
    assert report["scores_breakdown"]["speech_clarity"] >= 80
    assert report["scores_breakdown"]["confidence"] >= 80
    assert report["scores_breakdown"]["eye_contact"] >= 80
    assert report["scores_breakdown"]["engagement"] >= 80
    assert len(report["feedback"]) > 0
    print("test_scoring_with_good_metrics: PASSED")

def test_scoring_with_poor_metrics():
    # Arrange: Mock session history with poor posture, low eye contact, and excessive fillers
    session_history = {
        "category": "Software Engineer",
        "frames": [
            {"face_detected": True, "eye_contact": False, "posture_score": 50, "hand_fidgeting": True, "dominant_emotion": "anxious", "head_angle": 15.0},
            {"face_detected": True, "eye_contact": False, "posture_score": 60, "hand_fidgeting": True, "dominant_emotion": "anxious", "head_angle": 18.0},
            {"face_detected": True, "eye_contact": True, "posture_score": 50, "hand_fidgeting": True, "dominant_emotion": "anxious", "head_angle": 14.0},
            {"face_detected": True, "eye_contact": False, "posture_score": 40, "hand_fidgeting": True, "dominant_emotion": "anxious", "head_angle": 16.0},
            {"face_detected": True, "eye_contact": False, "posture_score": 55, "hand_fidgeting": True, "dominant_emotion": "anxious", "head_angle": 15.5},
        ],
        "speech": [
            {
                "word_count": 50,
                "wpm": 80,
                "filler_words_count": 12,
                "text": "Um, uh, like, so, you know, it is, um, difficult. I think.",
                "audio_metrics": {"rms": 0.03, "rms_std": 0.01, "zcr_var": 0.002}
            },
        ],
        "emotions": ["anxious", "anxious", "anxious", "anxious", "anxious"],
        "frame_count": 5
    }

    # Act
    report = calculate_final_scores(session_history)

    # Assert
    assert report["overall_score"] < 70, f"Expected lower overall score, got {report['overall_score']}"
    assert report["scores_breakdown"]["speech_clarity"] < 70
    assert report["scores_breakdown"]["confidence"] < 70
    assert report["scores_breakdown"]["eye_contact"] < 30
    assert report["scores_breakdown"]["engagement"] < 70
    print("test_scoring_with_poor_metrics: PASSED")

def test_scoring_with_low_eye_contact_correction():
    # Arrange: 0% eye contact. pre-correction confidence is based on voice tone (100) and head angle (100) -> 100.
    # Eye contact < 30 -> confidence score should be reduced by 40% (to 60).
    session_history = {
        "category": "Software Engineer",
        "frames": [
            {"face_detected": True, "eye_contact": False, "posture_score": 100, "hand_fidgeting": False, "head_angle": 2.0},
            {"face_detected": True, "eye_contact": False, "posture_score": 100, "hand_fidgeting": False, "head_angle": 2.0},
            {"face_detected": True, "eye_contact": False, "posture_score": 100, "hand_fidgeting": False, "head_angle": 2.0},
            {"face_detected": True, "eye_contact": False, "posture_score": 100, "hand_fidgeting": False, "head_angle": 2.0},
        ],
        "speech": [
            {
                "word_count": 100,
                "wpm": 120,
                "filler_words_count": 0,
                "text": "I speak perfectly. Pacing is perfect. No fillers. Structured.",
                "audio_metrics": {"rms": 0.08, "rms_std": 0.06, "zcr_var": 0.012}
            }
        ]
    }
    
    # Act
    report = calculate_final_scores(session_history)
    
    # Assert
    assert report["scores_breakdown"]["confidence"] == 60, f"Expected confidence score to be reduced to 60, got {report['scores_breakdown']['confidence']}"
    print("test_scoring_with_low_eye_contact_correction: PASSED")

def test_scoring_with_poor_speech_clarity_cap():
    # Arrange: Poor speech clarity (< 50) -> overall score capped at 55
    session_history = {
        "category": "Software Engineer",
        "frames": [
            {"face_detected": True, "eye_contact": True, "posture_score": 100, "hand_fidgeting": False, "head_angle": 2.0},
        ],
        "speech": [
            {
                "word_count": 50,
                "wpm": 40,
                "filler_words_count": 20,
                "text": "Um uh um uh like um uh like.",
                "audio_metrics": {"rms": 0.08, "rms_std": 0.06, "zcr_var": 0.012}
            }
        ]
    }
    
    # Act
    report = calculate_final_scores(session_history)
    
    # Assert
    assert report["scores_breakdown"]["speech_clarity"] < 50
    assert report["overall_score"] <= 55, f"Expected overall score capped at 55, got {report['overall_score']}"
    print("test_scoring_with_poor_speech_clarity_cap: PASSED")

if __name__ == "__main__":
    test_scoring_with_good_metrics()
    test_scoring_with_poor_metrics()
    test_scoring_with_low_eye_contact_correction()
    test_scoring_with_poor_speech_clarity_cap()
    print("All scoring tests passed successfully!")
