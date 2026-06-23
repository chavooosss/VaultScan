import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///test_vaultscan.db")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
