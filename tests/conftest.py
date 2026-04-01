import os
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test.db"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
