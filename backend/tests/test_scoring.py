from app.scoring import score_match


def test_score_match_is_stable_and_explained():
    resume = "Python FastAPI SQL Docker backend project B.Tech computer science intern"
    job = "Backend engineer requiring Python FastAPI SQL Docker and REST API"

    first = score_match(resume, job)
    second = score_match(resume, job)

    assert first == second
    assert first["overall_score"] >= 0
    assert "formula_version" in first
    assert "skills" in first["matched_evidence"]
    assert "skills" in first["missing_evidence"]
