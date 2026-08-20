"""Configuration management for ArcheoConverter."""

from dataclasses import dataclass, field
from typing import Optional

import json
import os

@dataclass
class AppConfig:
    supported_versions: list[str] = field(default_factory=lambda: ["3.2", "4.0"])
    default_version: str = "3.2"
    log_level: str = "INFO"
    max_memory_elements: int = 1_000_000
    ui_theme: str = "light"
    export_namespace: str = "http://www.opengroup.org/xsd/archimate/3.2"
    config_path: Optional[str] = None

    def save(self, path: str = "archeoea_config.json") -> None:
        with open(path, "w") as f:
            json.dump(vars(self), f, indent=2)

    @classmethod
    def load(cls, path: str = "archeoea_config.json") -> "AppConfig":
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            return cls(**data)
        return cls()
