import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///test_vaultscan.db")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    import main
    main._rate_limit_buckets.clear()
    yield
    main._rate_limit_buckets.clear()
