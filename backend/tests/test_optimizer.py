from app.optimizer import generate_resume_optimization


def test_optimizer_reports_before_after_scores_and_changes():
    resume = "Python SQL backend project B.Tech computer science"
    job = {
        "id": 1,
        "title": "Cloud Backend Engineer",
        "company": "Example Product Company",
        "employment_type": "Full-time",
        "requirements": "Python SQL Docker Kubernetes Azure REST API backend system design",
    }

    report = generate_resume_optimization(resume, job)

    assert report["current_match_score"] <= report["potential_match_score"]
    assert report["ats_score_before"] <= report["ats_score_after"]
    assert report["suggested_changes"]
    assert report["role_focus"] == "cloud"
