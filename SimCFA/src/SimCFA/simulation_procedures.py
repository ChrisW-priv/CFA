from copy import deepcopy
from datetime import date
from operator import eq, ge, le

import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
import matplotlib.pyplot as plt
import pandas as pd

from SimCFA.events import Events
from SimCFA.functional import apply, apply_kwarg, identity
from SimCFA.LedgerItem import Bond, Cash, Debt, GenericBuilder, House, LedgerItemProperties, LedgerItemType
from SimCFA.simulation import ledger_items_type


def add_date_guard(fn, comparison_target: date | int, comparison_fn, transform_fn=identity):
    def inner(day_date, **kwargs):
        transformed = transform_fn(day_date)
        if not comparison_fn(transformed, comparison_target):
            return
        fn(day_date=day_date, **kwargs)

    return inner


def add_date_guard_exact_date(fn, date_trigger: date):
    assert date_trigger, "Cannot create exact date guard with date_trigger as None"
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
    if start_date is not None:
        fn = add_date_guard_starts_on(fn, start_date)
    if end_date is not None:
        fn = add_date_guard_ends_on(fn, end_date)
    return fn


def add_month_day_date_guard(fn, day_trigger: int):
    transform_fn = lambda x: x.day
    return add_date_guard(fn, day_trigger, eq, transform_fn)


def create_simulate_monthly_cash_move(quantity: int, start_apply_date=None, end_apply_date=None, day_apply=10):
    """
    Each month, we will get or pay N money, on the day specified

    :param income_quantity:
    :return:
    """

    def inner(
        ledger_items: ledger_items_type,
        events: Events,
        n_day: int,
        **kwargs,
    ) -> None:
        change_cash_in_place(ledger_items, quantity, events, n_day, **kwargs)

    inner = add_month_day_date_guard(inner, day_apply)
    if start_apply_date:
        inner = add_date_guard_starts_on(inner, start_apply_date)
    if end_apply_date:
        inner = add_date_guard_ends_on(inner, end_apply_date)

    return inner


def create_cash_income(zipped_day_start_income, day_apply=10):
    def inner(ledger_items, day_date, events: Events, n_day: int, **kwargs):
        def predicate(el):
            day, _ = el
            return day_date >= day

        el = next(filter(predicate, zipped_day_start_income), None)
        if el is None:
            return
        _, income = el
        change_cash_in_place(ledger_items, income, events, n_day, **kwargs)

    inner = add_month_day_date_guard(inner, day_apply)
    return inner


def create_delayed_event_on_date(event_type: str, date_trigger: date, data: dict):
    def inner(n_day: int, day_date: date, events: Events, **kwargs):
        data["n_day"] = n_day
        data["day_date"] = day_date
        events.post_event(event_type, data)

    inner = add_date_guard_exact_date(inner, date_trigger)
    return apply_kwarg(inner)


def change_cash_in_place(
    ledger_items: ledger_items_type, by_how_much: int, events: Events, n_day=0, index: int = 0, **kwargs
):
    cash_item = ledger_items["cash"][index]
    original_quantity = cash_item.properties.quantity
    quantity = original_quantity + by_how_much
    cash_item.properties.quantity = max(quantity, 0)
    ledger_items["cash"][index] = cash_item
    events.post_event(
        "cash_state_change",
        {
            "index": index,
            "debit_level": quantity,
            "ledger_items": ledger_items,
            "by_how_much": by_how_much,
            "new_state": quantity,
            **kwargs,
        },
    )
    if by_how_much < 0 and quantity < 0:
        events.post_event(
            "cash_state_negative",
            {
                "index": index,
                "debit_level": quantity,
                "ledger_items": ledger_items,
                "events": events,
                "n_day": n_day,
                **kwargs,
            },
        )


def create_bond_buy(quantity: int, bond_builder: GenericBuilder):
    def inner(ledger_items, events, n_day, day_date, **kwargs):
        # build bond object
        properties = LedgerItemProperties(quantity, n_day)
        bond_item = bond_builder.set("properties", properties).build()

        # calculate the price needed to pay for the bonds
        bond_price = bond_item.price
        bond_value = quantity * bond_price

        # pay for bonds
        change_cash_in_place(ledger_items, -bond_value, events, n_day, **kwargs)

        # add bonds to the list of assets
        ledger_items["bonds"].append(bond_item)
        events.post_event("ledger_item_acquired", {"item": bond_item})

        # create trigger to buy it back after certain time delta
        duration = bond_item.duration
        expiry_date = day_date + duration
        data = {
            "item": bond_item,
            "events": events,
            "ledger_items": ledger_items,
        }
        bond_buy_back_trigger = create_delayed_event_on_date("bond_buy_back", expiry_date, data)
        events.subscribe("day_started", bond_buy_back_trigger)

    return inner


def create_bond_buy_on_date(bond_buy, date_trigger):
    inner = add_date_guard_exact_date(bond_buy, date_trigger)
    return inner


def create_bond_buy_back_for_cash():
    def inner(
        ledger_items: ledger_items_type,
        item: Bond,
        n_day: int,
        events: Events,
        **kwargs,
    ):
        # calculate how much do we get from the bonds
        cash_received = item.get_value(n_day)

        # sell bonds for cash
        ledger_items["bonds"].remove(item)
        events.post_event("ledger_item_sold", {"item": item})
        change_cash_in_place(ledger_items, cash_received, events, n_day, **kwargs)

    return inner


def create_simulation_state_save():
    states = []

    def save_state(**kwargs) -> None:
        nonlocal states
        states.append(deepcopy(kwargs))

    def access_state():
        return states

    return save_state, access_state


def get_final_cash_state(ledger_items: ledger_items_type, **kwargs):
    total = 0
    for item in ledger_items["cash"]:
        total += item.properties.quantity
    total /= 100
    print(f"Total amount of cash: {total:.2f}")


def create_draw_simulation_run(access_state_fn, handle_fig):
    def inner(**kwargs):
        states = access_state_fn()
        fig = make_pretty_plot(states)
        handle_fig(fig)

    return inner


def sum_all_ledger_items(n_day, ledger_items: ledger_items_type):
    result = {key: sum(item.get_value(n_day) for item in ledger_items[key]) for key in ledger_items}
    sum_all = sum(result[key] for key in result)
    result["net_worth"] = sum_all
    return result


def process_ledger_items_on_sim_step(n_day: int, ledger_items: ledger_items_type):
    result = {}
    for key in ledger_items:
        count_key = f"{key} - count"
        value_key = f"{key} - value"
        items_of_type = ledger_items[key]
        result[count_key] = sum(item.properties.quantity for item in items_of_type)
        result[value_key] = sum(item.get_value(n_day) for item in items_of_type)
    return result


def make_df_from_state_list(simulation_states: list):
    n_days = list(map(lambda state: state["n_day"], simulation_states))
    dates = list(map(lambda state: state["day_date"], simulation_states))
    ledger_items_list = list(map(lambda state: state["ledger_items"], simulation_states))
    zipped = zip(n_days, ledger_items_list)

    applied_process = apply(process_ledger_items_on_sim_step)
    results = map(applied_process, zipped)
    df = pd.DataFrame.from_records(results)
    value_columns = tuple(col for col in df.columns if "value" in col)
    for column in df.columns:
        if column in value_columns:
            df[column] /= 100
    df["cash - count"] /= 100
    df.fillna(0, inplace=True)
    df["date"] = dates
    df["date"] = pd.to_datetime(df["date"])
    return df


def make_pretty_plot(simulation_states: list):
    """
    Makes a pretty plot that will show the value of the ledger items on the main plot
    and count of each below on smaller scale plots.
    Current plot aspect ratio is full size for value and 1/n_types for each type of ledger item

    :param simulation_states:
    :return:
    """
    df = make_df_from_state_list(simulation_states)
    value_columns = tuple(col for col in df.columns if "value" in col)
    count_columns = tuple(col for col in df.columns if "count" in col)

    count = len(count_columns)
    height_ratios = [count] + ([1] * (count - 0))

    fig, axs = plt.subplots(count + 1, gridspec_kw={"height_ratios": height_ratios})
    for column in df.columns:
        if column == "date":
            continue
        if column in value_columns:
            axs[0].plot(df["date"], df[column], label=column)
            axs[0].set_title("value of ledger items")
            axs[0].yaxis.set_major_locator(MaxNLocator(integer=True, nbins=6 * 2))
        else:
            indx = count_columns.index(column) + 1
            axs[indx].plot(df["date"], df[column], label="_nolegend_")
            axs[indx].set_title(column)
            axs[indx].yaxis.set_major_locator(MaxNLocator(integer=True, nbins=3))

    fig.tight_layout(h_pad=0)
    fig.legend()
    CONST_H_MUL = 2
    height = sum(height_ratios) * CONST_H_MUL
    fig.set_figheight(height)
    width = 10
    fig.set_figwidth(width)
    return fig


def create_append_ledger_item(quantity=0, acquired_on=0, ledger_item_name="cash", ledger_item=Cash(None)):
    def inner(ledger_items, **kwargs):
        properties = LedgerItemProperties(quantity, acquired_on)
        ledger_item.properties = properties
        ledger_items[ledger_item_name].append(ledger_item)

    return inner


append_cash = lambda x, y=0: create_append_ledger_item(x, y)


def create_buy_house(price: int, day_buy: date):
    def inner(ledger_items, n_day, events, **kwargs):
        change_cash_in_place(ledger_items, -price, events, n_day, **kwargs)
        properties = LedgerItemProperties(1, n_day)
        house = House(properties, price)
        ledger_items["house"].append(house)

    inner = add_date_guard_exact_date(inner, day_buy)
    return inner


def ignore_debt():
    def inner(ledger_items, events, debit_level, n_day, **kwargs):
        # define debt and add it to ledger_items
        DEBT_PERCENT = 0
        debt_properties = LedgerItemProperties(-debit_level, n_day, LedgerItemType.Liability)
        debt_item = Debt(debt_properties, DEBT_PERCENT)
        ledger_items["debt"].append(debt_item)
        data = {
            "ledger_items": ledger_items,
            "events": events,
            "debit_level": debit_level,
            "n_day": n_day,
            "item": debt_item,
            **kwargs,
        }
        events.post_event("debt_acquired", data)

    return inner


def create_debt_with_interest():
    def inner(ledger_items, events, debit_level, n_day, **kwargs):
        # define debt and add it to ledger_items
        DEBT_PERCENT = 18
        debt_properties = LedgerItemProperties(-debit_level, n_day, LedgerItemType.Liability)
        debt_item = Debt(debt_properties, DEBT_PERCENT)
        ledger_items["debt"].append(debt_item)
        data = {
            "ledger_items": ledger_items,
            "events": events,
            "debit_level": debit_level,
            "n_day": n_day,
            "item": debt_item,
            **kwargs,
        }
        events.post_event("debt_acquired", data)

    return inner


def create_debt_payback_strategy(quantity_month):
    def inner(ledger_items, **kwargs):
        nonlocal quantity_month

        if "debt" not in ledger_items:
            return
        debt_item_list = ledger_items["debt"]
        # list of items to remove later, mutating the list in place is allways bad idea
        items_to_remove = []
        for item in debt_item_list:
            debt_value = item.properties.quantity
            diff = debt_value - quantity_month
            if diff == 0:
                change_cash_in_place(ledger_items, -quantity_month, **kwargs)
                # we just paid back entire debt, so just mark the item as "to remove and finish the loop"
                items_to_remove.append(item)
                break
            if diff < 0:
                change_cash_in_place(ledger_items, -(quantity_month + diff), **kwargs)
                # we paid back more than the value of the debt, remove current, adjust how much money we have left and
                # move on to the next one
                items_to_remove.append(item)
                quantity_month += diff
            if diff > 0:
                change_cash_in_place(ledger_items, -quantity_month, **kwargs)
                # still, the debt is there, we just paid of some of it
                item.properties.quantity = diff
        for item in items_to_remove:
            ledger_items["debt"].remove(item)

    inner = add_month_day_date_guard(inner, 10)
    return inner
