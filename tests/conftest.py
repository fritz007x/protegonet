from __future__ import annotations

import pytest

from cyber_agent import config as cfg
from cyber_agent.data.store import init_db


@pytest.fixture
def isolated_db(tmp_path):
    """Point the audit DB at a tmp file so tests don't pollute ./data/audit.sqlite.

    The Settings dataclass is frozen, so we mutate it via object.__setattr__ —
    same pattern used by tests/test_invoice_agent.py.
    """
    db_path = str(tmp_path / "audit.sqlite")
    object.__setattr__(cfg.settings, "audit_db_path", db_path)
    init_db()
    return db_path
