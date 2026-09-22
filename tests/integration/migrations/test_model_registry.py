from app.infrastructure.persistence.model_registry import metadata


def test_all_persistence_tables_are_registered():
    assert {
        "courses", "modules", "sections", "content_slug_registry",
        "lab_environment_settings", "quizzes", "questions", "answers", "quiz_sittings",
    }.issubset(metadata.tables)
