from collections import defaultdict


class Events:
    # Default value of the dictionary will be list
    subscribers = defaultdict(list)

    def __init__(self):
        ...

    def subscribe(self, event_type: str, fn):
        self.subscribers[event_type].append(fn)

    def post_event(self, event_type: str, data):
        if not event_type in self.subscribers:
            return
        for fn in self.subscribers[event_type]:
            fn(data)
