from LedgerItem import *
from datetime import date
from events import Events
from typing import List
from collections import defaultdict
from functional import apply_kwarg


ledger_items_type = defaultdict[str, List[LedgerItem]]


class Simulation:
    def __init__(self, n_days=1000, start_date=date(2025, 1, 1)):
        # simulation has to have at least one cash item
        # could be rewritten to support multiple bank accounts
        # for now just leave one
        self.ledger_items = defaultdict(list)
        cash_properties = LedgerItemProperties(0, 0)
        cash = Cash(cash_properties)
        self.ledger_items['cash'].append(cash)
        self.events = Events()
        self.n_days = n_days
        self.start_date = start_date

    def simulate(self):
        self.post_event("simulation_started", vars(self))
        for day in range(self.n_days):
            x = vars(self)
            x.update({'n_day': day})
            self.post_event("day_started", x)
            self.post_event("day_ended", x)
        self.post_event("simulation_ended", vars(self))

    def add_event_listener_applied(self, event_type, fn):
        self.events.subscribe(event_type, apply_kwarg(fn))

    def add_event_listener_raw(self, event_type, fn):
        self.events.subscribe(event_type, fn)

    def post_event(self, event_type, data):
        self.events.post_event(event_type, data)
