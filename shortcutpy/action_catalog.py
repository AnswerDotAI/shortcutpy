import json
from functools import lru_cache
from pathlib import Path


@lru_cache
def load_catalog() -> tuple[dict, dict]:
    data = json.loads(Path(__file__).with_name("action_catalog.json").read_text())
    return data["actions"],data["enums"]


ACTION_SPECS,ENUM_SPECS = load_catalog()
