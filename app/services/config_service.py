from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


CONFIG_DIR = Path.home() / ".curs_marking"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class AppConfig:
    db_type: str = "sqlite"
    db_path: str = "./curs_marking.db"
    storage_path: str = "./storage"
    temp_path: str = "./tmp"


class ConfigService:
    @staticmethod
    def load() -> AppConfig:
        if not CONFIG_FILE.exists():
            return AppConfig()
        with CONFIG_FILE.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return AppConfig(**data)

    @staticmethod
    def save(config: AppConfig) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with CONFIG_FILE.open("w", encoding="utf-8") as fh:
            json.dump(asdict(config), fh, ensure_ascii=False, indent=2)

    @staticmethod
    def make_db_url(config: AppConfig) -> str:
        if config.db_type == "sqlite":
            return f"sqlite:///{config.db_path}"
        raise ValueError("В версии MVP поддержан только sqlite-режим. PostgreSQL добавляется следующим шагом.")
