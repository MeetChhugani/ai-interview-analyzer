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
            {"eye_contact": True, "posture_score": 100, "hand_fidgeting": False, "dominant_emotion": "confident"},
            {"eye_contact": True, "posture_score": 98, "hand_fidgeting": False, "dominant_emotion": "confident"},
            {"eye_contact": True, "posture_score": 100, "hand_fidgeting": False, "dominant_emotion": "confident"},
            {"eye_contact": True, "posture_score": 95, "hand_fidgeting": False, "dominant_emotion": "neutral"},
            {"eye_contact": True, "posture_score": 100, "hand_fidgeting": False, "dominant_emotion": "confident"},
        ],
        "speech": [
            {"word_count": 80, "wpm": 120, "filler_words_count": 1, "text": "I am a software engineer."},
            {"word_count": 90, "wpm": 130, "filler_words_count": 0, "text": "I have experience with Python."}
        ],
        "emotions": ["confident", "confident", "confident", "neutral", "confident"],
        "frame_count": 5
    }

    # Act
    report = calculate_final_scores(session_history)

    # Assert
    assert report["overall_score"] >= 80, f"Expected high overall score, got {report['overall_score']}"
    assert report["scores_breakdown"]["confidence"] >= 80
    assert report["scores_breakdown"]["communication"] >= 80
    assert report["scores_breakdown"]["behavioral"] >= 80
    assert len(report["feedback"]) > 0
    print("test_scoring_with_good_metrics: PASSED")

def test_scoring_with_poor_metrics():
    # Arrange: Mock session history with poor posture, low eye contact, and excessive fillers
    session_history = {
        "category": "Software Engineer",
        "frames": [
            {"eye_contact": False, "posture_score": 50, "hand_fidgeting": True, "dominant_emotion": "anxious"},
            {"eye_contact": False, "posture_score": 60, "hand_fidgeting": True, "dominant_emotion": "anxious"},
            {"eye_contact": True, "posture_score": 50, "hand_fidgeting": True, "dominant_emotion": "anxious"},
            {"eye_contact": False, "posture_score": 40, "hand_fidgeting": True, "dominant_emotion": "anxious"},
            {"eye_contact": False, "posture_score": 55, "hand_fidgeting": True, "dominant_emotion": "anxious"},
        ],
        "speech": [
            {"word_count": 50, "wpm": 80, "filler_words_count": 12, "text": "Um, uh, like, so, you know, it is, um, difficult."},
        ],
        "emotions": ["anxious", "anxious", "anxious", "anxious", "anxious"],
        "frame_count": 5
    }

    # Act
    report = calculate_final_scores(session_history)

    # Assert
    assert report["overall_score"] < 70, f"Expected lower overall score, got {report['overall_score']}"
    assert report["scores_breakdown"]["confidence"] < 70
    assert report["scores_breakdown"]["communication"] < 70
    assert report["scores_breakdown"]["behavioral"] < 70
    print("test_scoring_with_poor_metrics: PASSED")

if __name__ == "__main__":
    test_scoring_with_good_metrics()
    test_scoring_with_poor_metrics()
    print("All scoring tests passed successfully!")
