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
    }
    assert scripts.get_current_head() == "0006_store_enums_as_strings"
    assert all(re.fullmatch(r"\d{4}_[a-z0-9_]+", revision.revision) for revision in revisions)
