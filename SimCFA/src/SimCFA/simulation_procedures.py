from copy import deepcopy
from datetime import date, timedelta

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from SimCFA.events import Events
from SimCFA.functional import apply, apply_kwarg
from SimCFA.LedgerItem import GenericBuilder, LedgerItem, LedgerItemProperties
from SimCFA.simulation import ledger_items_type


def convert_int_to_date(n_day: int, start_date) -> date:
    return start_date + timedelta(days=n_day)


def create_simulate_monthly_cash_move(quantity: int, day_apply=10):
    """
    Each month, we will get or pay N money, on the day specified

    :param income_quantity:
    :return:
    """

    def inner(
        ledger_items: ledger_items_type,
        n_day: int,
        events: Events,
        start_date,
        **kwargs,
    ) -> None:
        day_date = convert_int_to_date(n_day, start_date)
        if day_date.day != day_apply:
            return
        change_cash_in_place(ledger_items, quantity)
        events.post_event("cash_received", {"quantity": quantity, "n_day": n_day})

    return inner


def create_delayed_event(event_type: str, n_day_trigger: int, data: dict):
    def inner(n_day: int, events: Events, **kwargs):
        if n_day != n_day_trigger:
            return
        data["n_day"] = n_day
        events.post_event(event_type, data)

    return apply_kwarg(inner)


def change_cash_in_place(ledger_items: ledger_items_type, by_how_much: int, index: int = 0):
    cash_item = ledger_items["cash"][0]
    cash_item.properties.quantity += by_how_much
    ledger_items["cash"][index] = cash_item


def create_simulate_monthly_bond_buy(quantity: int, bond_builder: GenericBuilder, day_stop=400, day_apply=10):
    """
    Each month, we will buy N bonds lasting some relative delta of time (in months)

    :param quantity:
    :param duration:
    :param percent:
    :param day_apply:
    :return:
    """

    def inner(
        ledger_items: ledger_items_type,
        n_day: int,
        events: Events,
        start_date: date,
        **kwargs,
    ) -> None:
        if n_day >= day_stop:
            return
        day_date = convert_int_to_date(n_day, start_date)
        if day_date.day != day_apply:
            return
        # build and add to list of assets
        properties = LedgerItemProperties(quantity, n_day)
        bond_item = bond_builder.set("properties", properties).build()
        ledger_items["bonds"].append(bond_item)
        events.post_event("ledger_item_acquired", {"item": bond_item})

        bond_price = bond_item.price
        bond_value = quantity * bond_price
        change_cash_in_place(ledger_items, -bond_value)
        events.post_event("cash_spent", {"quantity": bond_value, "n_day": n_day})

        # create trigger to buy it back after certain time delta
        duration = bond_item.duration
        expiry_date = day_date + duration
        diff = expiry_date - day_date
        bond_duration_in_days = diff.days
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
    def inner(
        ledger_items: ledger_items_type,
        item: LedgerItem,
        n_day: int,
        events: Events,
        **kwargs,
    ):
        ledger_items["bonds"].remove(item)
        events.post_event("ledger_item_sold", {"item": item})

        cash_received = item.get_value(n_day)
        change_cash_in_place(ledger_items, cash_received)
        events.post_event("cash_received", {"quantity": cash_received, "n_day": n_day})

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
    for item in ledger_items["cash"]:
        total += item.properties.quantity
    print("Total amount of cash:", total)


def create_draw_simulation_run(access_state_fn):
    def inner(start_date: date, **kwargs):
        days, items = access_state_fn()
        dates = map(lambda x: convert_int_to_date(x, start_date), days)
        dates_labeled = [{"date": _date, "n_day": n_day} for n_day, _date in zip(days, dates)]

        df_dates = pd.DataFrame.from_records(dates_labeled)
        df_dates["date"] = pd.to_datetime(df_dates["date"])

        applied = apply(sum_all_ledger_items)
        zipped = zip(days, items)
        summed_by_cat = list(map(applied, zipped))
        df_values = pd.DataFrame.from_records(summed_by_cat)

        df_result = pd.concat([df_dates, df_values], axis=1)
        make_pretty_plot(df_result)
        return df_result

    return inner


def sum_all_ledger_items(n_day, ledger_items: ledger_items_type):
    result = {key: sum(item.get_value(n_day) for item in ledger_items[key]) for key in ledger_items}
    sum_all = sum(result[key] for key in result)
    result["net_worth"] = sum_all
    return result


def make_pretty_plot(df: pd.DataFrame, exclude: set[str] = None):
    if exclude is None:
        exclude = set()
    exclude = exclude.union({"date", "n_day"})

    plt.ylabel("money in the pocket", fontsize=12)
    plt.xlabel("dates")
    months = mdates.MonthLocator(interval=1, bymonthday=-1)
    plt.gca().xaxis.set_major_locator(months)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    plt.xticks(rotation=45, ha="right")
    for column in df.columns:
        if column in exclude:
            continue
        plt.plot(df["date"], df[column], label=column)

    plt.legend()
    plt.show(block=False)
    plt.pause(0.01)
    user_input = input()


def log_item_acq_change(direction: str, item):
    assert direction in ("acquired", "sold")
    print(f"Ledger item {direction}! Item: {item}")


def log_item_acquired(*args, **kwargs):
    log_item_acq_change("acquired", *args, **kwargs)


def log_item_sold(*args, **kwargs):
    log_item_acq_change("sold", *args, **kwargs)


def log_cash_state_change(direction, quantity: int, n_day: int, **kwargs):
    assert direction in ("received", "spent")
    if direction == "spent":
        quantity *= -1
    print(f"Cash {direction}! Day: {n_day:4d} {quantity=}")


def log_cash_state_received(*args, **kwargs):
    log_cash_state_change("received", *args, **kwargs)


def log_cash_state_spent(*args, **kwargs):
    log_cash_state_change("spent", *args, **kwargs)
