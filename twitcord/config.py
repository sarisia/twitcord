import json
from pathlib import Path

from .exceptions import ConfigError


class Config():
    def __init__(self, config_file=None):
        self._config_file = config_file
        if not self._config_file:
            self._config_file = "config/config.json"
        self._config = None

        self._load()

    def __getattr__(self, name: str):
        return self._config.get(name)

    def _load(self):
        file = Path(self._config_file)

        try:
            with file.open(encoding="utf8") as f:
                self._config = json.load(f)
        except OSError:
            raise ConfigError(f"Failed to open {str(self._config_file)}")
        except json.JSONDecodeError:
            raise ConfigError(f"Failed to parse {str(self._config_file)}")
