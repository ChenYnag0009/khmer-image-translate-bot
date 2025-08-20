from typing import Dict, List
from collections import defaultdict
import time

class AlbumCollector:
    """
    Collect photos that belong to the same media_group_id in Telegram.
    Flush them after a short timeout since Telegram delivers them as a burst.
    """
    def __init__(self, timeout_sec: int = 5):
        self.timeout = timeout_sec
        self.groups: Dict[str, Dict] = defaultdict(lambda: {"ts": time.time(), "items": []})

    def add(self, group_id: str, item):
        g = self.groups[group_id]
        g["items"].append(item)
        g["ts"] = time.time()

    def pop_if_ready(self, group_id: str):
        g = self.groups.get(group_id)
        if not g:
            return None
        if time.time() - g["ts"] >= self.timeout:
            return self.groups.pop(group_id)["items"]
        return None
