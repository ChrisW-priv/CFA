from copy import deepcopy
from datetime import date
from operator import eq, ge, le

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from SimCFA.events import Events
from SimCFA.functional import apply, apply_kwarg, identity
from SimCFA.LedgerItem import Cash, Debt, GenericBuilder, LedgerItem, LedgerItemProperties, LedgerItemType
from SimCFA.simulation import ledger_items_type


def add_date_guard(fn, comparison_target: date | int, comparison_fn, transform_fn=identity):
    def inner(day_date, **kwargs):
        transformed = transform_fn(day_date)
        if not comparison_fn(transformed, comparison_target):
            return
        fn(day_date=day_date, **kwargs)

    return inner


def add_date_guard_exact_date(fn, date_trigger: date):
    return add_date_guard(fn, date_trigger, eq)


def add_date_guard_starts_on(fn, start_date: date):
    assert start_date, "Cannot create an starts on date guard with start_date_date as None"
    guarded_start = add_date_guard(fn, start_date, ge)
    return guarded_start


def add_date_guard_ends_on(fn, end_date: date):
    assert end_date, "Cannot create an ends on date guard with end_date as None"
    guarded_start = add_date_guard(fn, end_date, le)
    return guarded_start


def add_date_guard_date_between(fn, start_date: date, end_date: date):
    assert (
        start_date and end_date
    ), "Cannot create a between date guard with one of the args as None, use start|end date guards instead"
    guarded_start = add_date_guard_starts_on(fn, start_date)
    guarded_between = add_date_guard_ends_on(guarded_start, end_date)
    return guarded_between


def add_month_day_date_guard(fn, day_trigger: int):
    transform_fn = lambda x: x.day
    return add_date_guard(fn, day_trigger, eq, transform_fn)


def add_n_day_guard(fn, comparison_target: date | int, comparison_fn):
    def inner(n_day, **kwargs):
        if not comparison_fn(n_day, comparison_target):
            return
        fn(n_day=n_day, **kwargs)

    return inner


def add_n_day_guard_exact_n_day(fn, n_day_trigger: int):
    return add_n_day_guard(fn, n_day_trigger, eq)


def add_n_day_guard_ends_on(fn, n_day_trigger: int):
    return add_n_day_guard(fn, n_day_trigger, le)


def add_n_day_guard_starts_on(fn, n_day_trigger: int):
    return add_n_day_guard(fn, n_day_trigger, ge)


def create_simulate_monthly_cash_move(quantity: int, start_apply_date=None, end_apply_date=None, day_apply=10):
    """
    Each month, we will get or pay N money, on the day specified

    :param income_quantity:
    :return:
    """

    def inner(
        ledger_items: ledger_items_type,
        events: Events,
        **kwargs,
    ) -> None:
        change_cash_in_place(ledger_items, quantity, events)

    inner = add_month_day_date_guard(inner, day_apply)
    if start_apply_date:
        inner = add_date_guard_starts_on(inner, start_apply_date)
    if end_apply_date:
        inner = add_date_guard_ends_on(inner, end_apply_date)

    return inner


def create_cash_income(zipped_day_start_income, day_apply=10):
    def inner(ledger_items, day_date, events: Events, **kwargs):
        def pred(el):
            day, _ = el
            return day_date >= day

        el = next(filter(pred, zipped_day_start_income), None)
        if el is None:
            return
        _, income = el
        change_cash_in_place(ledger_items, income, events)

    inner = add_month_day_date_guard(inner, day_apply)
    return inner


def create_delayed_event_on_n_day(event_type: str, n_day_trigger: int, data: dict):
    def inner(n_day: int, events: Events, **kwargs):
        data["n_day"] = n_day
        events.post_event(event_type, data)

    inner = add_n_day_guard_exact_n_day(inner, n_day_trigger)
    return apply_kwarg(inner)


def change_cash_in_place(ledger_items: ledger_items_type, by_how_much: int, events: Events, index: int = 0):
    cash_item = ledger_items["cash"][index]
    quantity = cash_item.properties.quantity
    quantity += by_how_much
    cash_item.properties.quantity = quantity
    ledger_items["cash"][index] = cash_item
    events.post_event(
        "cash_state_change",
        {
            "index": index,
            "by_how_much": by_how_much,
            "new_state": quantity,
        },
    )
    if quantity < 0:
        events.post_event(
            "cash_state_negative",
            {
                "index": index,
                "debit_level": quantity,
            },
        )


def create_bond_buy(quantity: int, bond_builder: GenericBuilder, date_apply: date):
    def inner(ledger_items, events, n_day, day_date, start_date, **kwargs):
        # build and add to list of assets
        properties = LedgerItemProperties(quantity, n_day)
        bond_item = bond_builder.set("properties", properties).build()
        ledger_items["bonds"].append(bond_item)
        events.post_event("ledger_item_acquired", {"item": bond_item})

        bond_price = bond_item.price
        bond_value = quantity * bond_price
        change_cash_in_place(ledger_items, -bond_value, events)
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
        bond_buy_back_trigger = create_delayed_event_on_n_day("bond_buy_back", trigger_day, data)
        events.subscribe("day_started", bond_buy_back_trigger)

    inner = add_date_guard_exact_date(inner, date_apply)
    return inner


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
        # build and add to list of assets
        properties = LedgerItemProperties(quantity, n_day)
        bond_item = bond_builder.set("properties", properties).build()
        ledger_items["bonds"].append(bond_item)
        events.post_event("ledger_item_acquired", {"item": bond_item})

        bond_price = bond_item.price
        bond_value = quantity * bond_price
        change_cash_in_place(ledger_items, -bond_value, events)
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
        bond_buy_back_trigger = create_delayed_event_on_n_day("bond_buy_back", trigger_day, data)
        events.subscribe("day_started", bond_buy_back_trigger)

    inner = add_n_day_guard_ends_on(inner, day_stop)
    inner = add_month_day_date_guard(inner, day_apply)

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
        change_cash_in_place(ledger_items, cash_received, events)
        events.post_event("cash_received", {"quantity": cash_received, "n_day": n_day})

    return inner


def create_simulation_state_save():
    n_days = []
    day_dates = []
    ledger_items_saved = []

    def save_state(ledger_items: ledger_items_type, n_day: int, day_date: date, **kwargs) -> None:
        nonlocal n_days, ledger_items_saved, day_dates
        n_days.append(n_day)
        day_dates.append(day_date)
        ledger_items_saved.append(deepcopy(ledger_items))

    def access_state():
        return n_days, ledger_items_saved, day_dates

    return save_state, access_state


def get_final_cash_state(ledger_items: ledger_items_type, **kwargs):
    total = 0
    for item in ledger_items["cash"]:
        total += item.properties.quantity
    total /= 100
    print(f"Total amount of cash: {total:.2f}")


def create_draw_simulation_run(access_state_fn):
    def inner(start_date: date, **kwargs):
        days, items, day_dates = access_state_fn()
        dates_labeled = [{"date": _date, "n_day": n_day} for n_day, _date in zip(days, day_dates)]

        df_dates = pd.DataFrame.from_records(dates_labeled)
        df_dates["date"] = pd.to_datetime(df_dates["date"])

        applied = apply(sum_all_ledger_items)
        zipped = zip(days, items)
        summed_by_cat = list(map(applied, zipped))
        print(f"Net worth at the end {summed_by_cat[-1]['net_worth']/100:.2f}")
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


def create_append_cash(quantity=0):
    def inner(ledger_items, **kwargs):
        cash_properties = LedgerItemProperties(quantity, 0)
        cash = Cash(cash_properties)
        ledger_items["cash"].append(cash)

    return inner


append_cash = create_append_cash()


def create_buy_house(price: int, day_buy: date):
    def inner(ledger_items, n_day, events, **kwargs):
        one_time_expense = create_one_time_expense(price, n_day)
        one_time_expense(ledger_items, n_day, events, **kwargs)

    inner = add_date_guard_exact_date(inner, day_buy)

    return inner


def create_one_time_expense(quantity: int, n_day_apply: int):
    def inner(ledger_items, n_day: int, events: Events, **kwargs):
        if n_day != n_day_apply:
            return

        cash_item = ledger_items["cash"][0]
        cash_on_hand = cash_item.properties.quantity
        debt_volume = quantity - cash_on_hand
        if debt_volume <= 0:
            change_cash_in_place(ledger_items, quantity, events)
            return

        # set the cash state to 0
        change_cash_in_place(ledger_items, -cash_on_hand, events)

        # define debt and add it to ledger_items
        DEBT_PERCENT = 18
        debt_properties = LedgerItemProperties(debt_volume, n_day, LedgerItemType.Liability)
        debt_item = Debt(debt_properties, DEBT_PERCENT)
        ledger_items["debt"].append(debt_item)
        events.post_event("debt_acquired", debt_item)

    return inner
