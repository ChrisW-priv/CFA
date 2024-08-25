from collections import defaultdict
from datetime import date, timedelta
from typing import List

from SimCFA.events import Events
from SimCFA.functional import apply_kwarg
from SimCFA.LedgerItem import LedgerItem

ledger_items_type = defaultdict[str, List[LedgerItem]]


def convert_int_to_date(n_day: int, start_date) -> date:
    return start_date + timedelta(days=n_day)


class Simulation:
    def __init__(self, n_days=1000, start_date=date(2025, 1, 1)):
        self.ledger_items = defaultdict(list)
        self.events = Events()
        self.n_days = n_days
        self.start_date = start_date

    def simulate(self):
        kwargs = vars(self)
        self.post_event("simulation_started", kwargs)
        for day in range(self.n_days):
            kwargs["n_day"] = day
            kwargs["day_date"] = convert_int_to_date(day, self.start_date)
            self.post_event("day_started", kwargs)
            self.post_event("day_ended", kwargs)
        self.post_event("simulation_ended", kwargs)

    def add_event_listener_applied(self, event_type, fn):
        self.events.subscribe(event_type, apply_kwarg(fn))

    def add_event_listener_raw(self, event_type, fn):
        self.events.subscribe(event_type, fn)

    def post_event(self, event_type, data):
        self.events.post_event(event_type, data)
