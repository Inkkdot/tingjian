"""Configuration from environment (no secrets checked into the repo)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _bilibili_cookie() -> str:
    cookie = os.getenv("BILIBILI_COOKIE", "").strip()
    if cookie:
        return cookie
    path = os.getenv("BILIBILI_COOKIE_FILE", "").strip()
    if not path:
        return ""
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


@dataclass(frozen=True)
class Settings:
    db_host: str = os.getenv("SEEKDB_HOST", "127.0.0.1")
    db_port: int = int(os.getenv("SEEKDB_PORT", "2881"))
    db_user: str = os.getenv("SEEKDB_USER", "root")
    db_password: str = os.getenv("SEEKDB_PASSWORD", "")
    db_name: str = os.getenv("SEEKDB_DATABASE", "tingjian")
    embedding_enabled: bool = os.getenv("TINGJIAN_EMBEDDING", "1") != "0"
    mode: str = os.getenv("TINGJIAN_MODE", "live")
    bilibili_cookie: str = field(default_factory=_bilibili_cookie, repr=False)

    @property
    def bilibili_login_configured(self) -> bool:
        return bool(self.bilibili_cookie)


settings = Settings()
