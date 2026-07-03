import sys
import os

# Append the app directory to sys.path so we can run the test directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "AI Interview Analyzer API"}
    print("test_health_check: PASSED")

def test_session_lifecycle():
    # 1. Create Session
    response = client.post("/api/session", json={"category": "Software Engineer"})
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["category"] == "Software Engineer"
    assert data["status"] == "initialized"
    session_id = data["session_id"]
    print("test_create_session: PASSED")

    # 2. Get Report
    response = client.get(f"/api/session/{session_id}/report")
    assert response.status_code == 200
    report = response.json()
    assert "overall_score" in report
    assert "scores_breakdown" in report
    assert "metrics" in report
    assert len(report["feedback"]) > 0
    print("test_get_report: PASSED")

if __name__ == "__main__":
    test_health_check()
    test_session_lifecycle()
    print("All endpoint tests passed successfully!")
