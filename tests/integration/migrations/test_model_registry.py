from app.infrastructure.persistence.model_registry import metadata


def test_all_persistence_tables_are_registered():
    assert {
        "courses", "modules", "sections", "content_slug_registry",
        "lab_environment_settings", "quizzes", "questions", "answers", "quiz_sittings",
        "question_code_sequences", "quiz_sitting_questions", "quiz_sitting_options",
        "quiz_sitting_answer_selections", "quiz_sitting_question_results", "quiz_exam_attempt_counters",
    }.issubset(metadata.tables)
