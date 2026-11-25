"""
Fails on purpose against every QuestDB release but the pinned one: shows that the nightly run
reports a failure against the newest release as a warning, without failing the run (CI-T12)
"""

from tests.integration.conftest import select
from tests.integration_support.database_choice import DEFAULT_IMAGE


def test_the_server_runs_the_pinned_questdb_release(fresh_db):
    pinned = DEFAULT_IMAGE.rsplit(":", 1)[1]
    [(build,)] = select(fresh_db, "SELECT build()")
    assert f"QuestDB {pinned}," in build
