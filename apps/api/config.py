"""Configuration from environment (no secrets checked into the repo)."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    db_host: str = os.getenv("SEEKDB_HOST", "127.0.0.1")
    db_port: int = int(os.getenv("SEEKDB_PORT", "2881"))
    db_user: str = os.getenv("SEEKDB_USER", "root")
    db_password: str = os.getenv("SEEKDB_PASSWORD", "")
    db_name: str = os.getenv("SEEKDB_DATABASE", "tingjian")
    embedding_enabled: bool = os.getenv("TINGJIAN_EMBEDDING", "1") != "0"
    mode: str = os.getenv("TINGJIAN_MODE", "live")


settings = Settings()
