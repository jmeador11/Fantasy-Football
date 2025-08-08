from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


DEFAULT_CONFIG_PATH = Path(os.path.expanduser("~/.ff_agent/config.json"))


@dataclass
class AgentConfig:
    username: Optional[str] = None
    season: Optional[int] = None
    league_id: Optional[str] = None
    slack_webhook_url: Optional[str] = None


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> AgentConfig:
    if not path.exists():
        return AgentConfig()
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return AgentConfig(**data)


def save_config(cfg: AgentConfig, path: Path = DEFAULT_CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump({k: v for k, v in asdict(cfg).items() if v is not None}, f, indent=2)