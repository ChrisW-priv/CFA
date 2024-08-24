from collections import defaultdict
from dataclasses import dataclass


@dataclass
class Events:
    def __init__(self) -> None:
        self.subscribers = defaultdict(list)

    def subscribe(self, event_type: str, fn):
        self.subscribers[event_type].append(fn)

    def post_event(self, event_type: str, data):
        if event_type not in self.subscribers:
            return
        for fn in self.subscribers[event_type]:
            fn(data)
