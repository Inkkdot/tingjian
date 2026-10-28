import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

# Integration tests use a dedicated database; never touch the live one.
os.environ.setdefault("SEEKDB_DATABASE", "tingjian_test")
os.environ.setdefault("SEEKDB_HOST", "127.0.0.1")
os.environ.setdefault("SEEKDB_PORT", "2881")
os.environ.setdefault("SEEKDB_USER", "root")
os.environ.setdefault("SEEKDB_PASSWORD", "")
