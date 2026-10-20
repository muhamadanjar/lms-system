from pathlib import Path
import re

from alembic.script import ScriptDirectory
from alembic.config import Config


def test_migration_chain_is_reversible_and_has_head():
    config = Config(str(Path(__file__).parents[3] / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)
    revisions = list(scripts.walk_revisions())
    assert {revision.revision for revision in revisions} == {
        "0001_initial_content_hierarchy",
        "0002_typed_section_content",
        "0003_remote_server",
        "0004_quiz_sitting_results",
        "0005_add_content",
        "0006_store_enums_as_strings",
        "0007_lab_assignments",
        "0008_course_lab_access",
        "0009_course_enrollment",
        "0010_add_sequence_course",
        "0011_course_quiz_lifecycle",
        "0012_quiz_snapshot_fks",
        "0013_question_type_length",
        "0014_course_progress_tasks",
        "0015_collect_task_files",
        "0016_section_terminal_enabled",
        "0017_section_is_preview",
        "0018_course_watch_position",
        "0019_collect_task_file_staging",
        "0020_course_instructors",
    }
    assert scripts.get_current_head() == "0020_course_instructors"
    assert all(re.fullmatch(r"\d{4}_[a-z0-9_]+", revision.revision) for revision in revisions)
