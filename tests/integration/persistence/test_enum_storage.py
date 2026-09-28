from sqlalchemy import String
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.infrastructure.persistence.model_registry import metadata


ENUM_COLUMNS = (
    ("answers", "status"),
    ("courses", "status"),
    ("lab_environment_settings", "status"),
    ("lab_environment_settings", "access_method"),
    ("modules", "status"),
    ("questions", "status"),
    ("questions", "question_type"),
    ("quiz_sittings", "status"),
    ("quiz_sittings", "attempt_state"),
    ("quizzes", "status"),
    ("quizzes", "answer_policy"),
    ("remote_servers", "access_method"),
    ("sections", "status"),
    ("sections", "content_type"),
)


def test_all_persisted_domain_enums_use_string_columns() -> None:
    for table_name, column_name in ENUM_COLUMNS:
        column = metadata.tables[table_name].c[column_name]
        assert isinstance(
            column.type,
            String,
        ), f"{table_name}.{column_name} must use VARCHAR"


def test_postgresql_table_ddl_does_not_reference_native_enums() -> None:
    ddl = "\n".join(
        str(CreateTable(table).compile(dialect=postgresql.dialect()))
        for table in metadata.sorted_tables
    )

    assert "contentstatus" not in ddl
    assert "accessmethod" not in ddl
