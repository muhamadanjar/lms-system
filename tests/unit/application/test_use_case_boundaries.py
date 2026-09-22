from pathlib import Path


def test_application_use_cases_do_not_import_persistence_models():
    root = Path(__file__).parents[3] / "app" / "application"
    for source in root.rglob("*.py"):
        text = source.read_text()
        assert "sqlmodel" not in text.lower()
        assert "infrastructure.persistence.models" not in text
