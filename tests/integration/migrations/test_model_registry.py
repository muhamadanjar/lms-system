from app.infrastructure.persistence.model_registry import metadata


def test_all_persistence_tables_are_registered():
    assert {
        "courses", "modules", "sections", "content_slug_registry",
        "course_lab_access", "enrollments", "remote_servers", "quizzes", "questions", "answers", "quiz_sittings",
        "question_code_sequences", "quiz_sitting_questions", "quiz_sitting_options",
        "quiz_sitting_answer_selections", "quiz_sitting_question_results", "quiz_exam_attempt_counters",
    }.issubset(metadata.tables)
    assert "lab_environment_settings" not in metadata.tables
    assert "lab_assignments" not in metadata.tables
