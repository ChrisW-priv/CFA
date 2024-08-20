from LedgerItem import *
from dateutil.relativedelta import relativedelta
from datetime import date, timedelta
import matplotlib.pyplot as plt
from events import Events
from typing import List
from compound_interest_calculator import compound_interest_calc
from copy import deepcopy
from collections import defaultdict
import matplotlib.dates as mdates
import pandas as pd

START_DATE = date(2025, 1, 1)

BOND_PRICE = 100_00

ledger_items_type = defaultdict[str, List[LedgerItem]]


def is_leap_year(year: int):
    return (year % 400 == 0) or (year % 100 != 0) and (year % 4 == 0)


def days_in_a_year(year: int = 1):
    return 365 + int(is_leap_year(year))


def apply(fn):
    def inner(args):
        return fn(*args)
    return inner


def apply_kwarg(fn):
    def inner(kwargs):
        return fn(**kwargs)
    return inner


class Simulation:

    def __init__(self, n_days=1000):
        # simulation has to have at least one cash item
        # could be rewritten to support multiple bank accounts
        # for now just leave one
        self.ledger_items = defaultdict(list)
        self.ledger_items['cash'].append(Cash(0, 0))
        self.events = Events()
        self.n_days = n_days

    def simulate(self):
        self.post_event("simulation_started", vars(self))
        for day in range(self.n_days):
            self.post_event("day_started", day)
            self.post_event("day_ended", day)
        self.post_event("simulation_ended", vars(self))

    def add_event_listener_applied(self, event_type, fn):
        self.events.subscribe(event_type, apply_kwarg(fn))

    def add_event_listener_raw(self, event_type, fn):
        self.events.subscribe(event_type, fn)

    def post_event(self, event_type, day):
        data = {
            "ledger_items": self.ledger_items,
            "events": self.events,
            "n_days": self.n_days,
            "n_day": day,
        }
        self.events.post_event(event_type, data)


def convert_int_to_date(n_day: int) -> date:
    return START_DATE + timedelta(days=n_day)


def create_simulate_monthly_cash_move(quantity: int, day_apply=10):
    """
    Each month, we will get or pay N money, on the day specified

    :param income_quantity:
    :return:
    """

    def inner(ledger_items: ledger_items_type, n_day: int, events: Events, **kwargs) -> None:
        day_date = convert_int_to_date(n_day)
        if day_date.day != day_apply:
            return
        change_cash_in_place(ledger_items, quantity)
        events.post_event("cash_received", {'quantity': quantity, 'n_day': n_day})

    return inner


def create_delayed_event(event_type: str, n_day_trigger: int, data: dict):
    def inner(n_day: int, events: Events, **kwargs):
        if n_day != n_day_trigger:
            return
        data["n_day"] = n_day
        events.post_event(event_type, data)

    return apply_kwarg(inner)


def change_cash_in_place(ledger_items: ledger_items_type, by_how_much: int, index: int = 0):
    cash_item = ledger_items['cash'][0]
    cash_item.quantity += by_how_much
    ledger_items['cash'][index] = cash_item


def create_simulate_monthly_bond_buy(quantity: int, bond_builder: GenericBuilder, day_stop=400, day_apply=10):
    """
    Each month, we will buy N bonds lasting some relative delta of time (in months)

    :param quantity:
    :param duration:
    :param percent:
    :param day_apply:
    :return:
    """

    def inner(ledger_items: ledger_items_type, n_day: int, events: Events, **kwargs) -> None:
        if n_day >= day_stop:
            return
        day_date = convert_int_to_date(n_day)
        if day_date.day != day_apply:
            return
        # build and add to list of assets
        bond_item = bond_builder.set('quantity', quantity).set('acquired_on', n_day).build()
        ledger_items['bonds'].append(bond_item)
        events.post_event("ledger_item_acquired", {"item": bond_item})

        bond_price = bond_item.price
        bond_value = quantity * bond_price
        change_cash_in_place(ledger_items, -bond_value)
        events.post_event("cash_spent", {'quantity': bond_value, 'n_day': n_day})

        # create trigger to buy it back after certain time delta
        duration = bond_item.duration
        years = duration.years
        bond_duration_in_days = years * days_in_a_year()
        trigger_day = n_day + bond_duration_in_days
        data = {
            "item": bond_item,
            "events": events,
            "ledger_items": ledger_items,
        }
        bond_buy_back_trigger = create_delayed_event("bond_buy_back", trigger_day, data)
        events.subscribe("day_started", bond_buy_back_trigger)

    return inner


def create_bond_buy_back_for_cash():
    def inner(ledger_items: ledger_items_type, item: LedgerItem, n_day: int, events: Events, **kwargs):
        ledger_items['bonds'].remove(item)
        events.post_event("ledger_item_sold", {"item": item})

        cash_received = item.get_value(n_day)
        change_cash_in_place(ledger_items, cash_received)
        events.post_event("cash_received", {'quantity': cash_received, 'n_day': n_day})

    return inner


def create_simulation_state_save():
    days = []
    ledger_items_saved = []

    def save_state(ledger_items: ledger_items_type, n_day: int, **kwargs) -> None:
        nonlocal days, ledger_items_saved
        days.append(n_day)
        ledger_items_saved.append(deepcopy(ledger_items))

    def access_state():
        return days, ledger_items_saved

    return save_state, access_state


def get_final_cash_state(ledger_items: ledger_items_type, **kwargs):
    total = 0
    for item in ledger_items['cash']:
        total += item.quantity
    print("Total amount of cash:", total)


def create_draw_simulation_run(access_state_fn):
    def inner(**kwargs):
        days, items = access_state_fn()
        dates = map(convert_int_to_date, days)
        dates_labeled = [{"date": _date} for _date in dates]

        df_dates = pd.DataFrame.from_records(dates_labeled)
        df_dates['date'] = pd.to_datetime(df_dates['date'])

        applied = apply(sum_all_ledger_items)
        zipped = zip(days, items)
        summed_by_cat = list(map(applied, zipped))
        df_values = pd.DataFrame.from_records(summed_by_cat)

        df_result = pd.concat([df_dates, df_values], axis=1)
        make_pretty_plot(df_result)
        return df_result

    return inner


def sum_all_ledger_items(n_day, ledger_items: ledger_items_type):
    result = {
        key: sum(item.get_value(n_day) for item in ledger_items[key])
        for key in ledger_items
    }
    sum_all = sum(result[key] for key in result)
    result['net_worth'] = sum_all
    return result


def make_pretty_plot(df: pd.DataFrame):
    plt.ylabel('money in the pocket', fontsize=12)
    plt.xlabel('dates')
    months = mdates.MonthLocator(interval=1, bymonthday=-1)
    plt.gca().xaxis.set_major_locator(months)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45, ha='right')
    for column in df.columns:
        if column == 'date':
            continue
        plt.plot(df['date'], df[column])
    plt.show()


def log_item_acq_change(direction, item: LedgerItem):
    assert direction in ('acquired', 'sold')
    print(f"Ledger item {direction}! Item: {item}")


def log_item_acquired(*args, **kwargs):
    log_item_acq_change('acquired', *args, **kwargs)


def log_item_sold(*args, **kwargs):
    log_item_acq_change('sold', *args, **kwargs)


def log_cash_state_change(direction, quantity: int, n_day: int, **kwargs):
    assert direction in ('received', 'spent')
    if direction == 'spent':
        quantity *= -1
    print(f"Cash {direction}! Day: {n_day:4d} {quantity=}")


def log_cash_state_received(*args, **kwargs):
    log_cash_state_change('received', *args, **kwargs)


def log_cash_state_spent(*args, **kwargs):
    log_cash_state_change('spent', *args, **kwargs)


def main():
    steady_income = create_simulate_monthly_cash_move(5500_00)
    life_costs = create_simulate_monthly_cash_move(-3000_00, 20)
    save_state_fn, access_state_fn = create_simulation_state_save()
    draw_simulation_run = create_draw_simulation_run(access_state_fn)
    bonds_buy = create_simulate_monthly_bond_buy(100, year_bond_builder, 400, 25)
    bonds_buy_back = create_bond_buy_back_for_cash()

    simulation = Simulation()
    simulation.add_event_listener_raw("log", print)
    simulation.add_event_listener_applied("day_started", steady_income)
    simulation.add_event_listener_applied("day_started", life_costs)
    simulation.add_event_listener_applied("day_started", bonds_buy)
    simulation.add_event_listener_applied("bond_buy_back", bonds_buy_back)

    simulation.add_event_listener_applied("cash_received", log_cash_state_received)
    simulation.add_event_listener_applied("cash_spent", log_cash_state_spent)
    simulation.add_event_listener_applied("ledger_item_acquired", log_item_acquired)
    simulation.add_event_listener_applied("ledger_item_sold", log_item_sold)

    simulation.add_event_listener_applied("day_ended", save_state_fn)
    simulation.add_event_listener_applied("simulation_ended", draw_simulation_run)
    simulation.add_event_listener_applied("simulation_ended", get_final_cash_state)

    simulation.simulate()


if __name__ == '__main__':
    main()
