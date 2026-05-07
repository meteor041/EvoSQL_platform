from evosql_platform.engine.refiners import ECARefiner, SCRRefiner, extract_references
from evosql_platform.models import CandidateSQL


def test_extract_references() -> None:
    tables, columns = extract_references(
        "SELECT s.student_name, c.college_name FROM students s JOIN colleges c ON s.college_id = c.college_id"
    )
    assert "students" in tables
    assert "colleges" in tables
    assert columns


def test_scr_union_tables() -> None:
    refiner = SCRRefiner()
    candidates = [
        CandidateSQL(sql="SELECT * FROM students", referenced_tables=["students"]),
        CandidateSQL(sql="SELECT * FROM courses", referenced_tables=["courses"]),
    ]
    tables, hints = refiner.refine(candidates)
    assert tables == {"students", "courses"}
    assert hints == []


def test_eca_clusters_same_signature() -> None:
    refiner = ECARefiner()
    candidates = [
        CandidateSQL(sql="SELECT 1", referenced_tables=["students"], execution_signature="same", score=1.0),
        CandidateSQL(sql="SELECT 1 LIMIT 5", referenced_tables=["students"], execution_signature="same", score=0.8),
        CandidateSQL(sql="SELECT 2", referenced_tables=["courses"], execution_signature="other", score=0.6),
    ]
    tables, anchors, best = refiner.refine(candidates, top_k=2)
    assert "students" in tables
    assert anchors
    assert best is not None
    assert best.execution_signature == "same"
