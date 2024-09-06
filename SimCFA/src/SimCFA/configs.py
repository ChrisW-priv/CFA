from datetime import date
import io
import json

import matplotlib.pyplot as plt

from SimCFA.LedgerItem import DAYS_YEAR, three_year_bond_builder
from SimCFA.simulation import Simulation
from SimCFA.simulation_procedures import (
    append_cash,
    create_bond_buy,
    create_bond_buy_back_for_cash,
    create_bond_buy_on_date,
    create_buy_house,
    create_cash_income,
    create_debt_payback_strategy,
    create_debt_with_interest,
    create_draw_simulation_run,
    create_simulate_monthly_cash_move,
    create_simulation_state_save,
    get_final_cash_state,
)
from functional import identity, pipe


def show_fig(fig):
    fig.show()
    plt.pause(0.01)
    x = input()


def create_handle_fig_save_to_buff():
    bio = io.BytesIO()

    def save_fig_to_buffer(fig):
        fig.savefig(bio, dpi=250, format="png")
        return bio

    def access_buffer():
        return bio

    return save_fig_to_buffer, access_buffer


def manual_config():
    income_map = [
        (date(2024, 2, 1), 4125_00),
        (date(2024, 7, 1), 5500_00),
        (date(2024, 10, 1), 4125_00),
        (date(2025, 1, 1), 5500_00),
        (date(2026, 1, 1), 8000_00),
        (date(2027, 1, 1), 10000_00),
    ]

    income_map = income_map[::-1]
    work_income = create_cash_income(income_map)
    life_costs = create_simulate_monthly_cash_move(-800_00, date(2024, 1, 1))
    save_state_fn, access_state_fn = create_simulation_state_save()
    handle_fig = show_fig
    # handle_fig, access_fig = create_handle_fig_save_to_buff()
    draw_simulation_run = create_draw_simulation_run(access_state_fn, handle_fig)
    bonds_buy = create_bond_buy(1766, three_year_bond_builder)
    bonds_buy_on_date = create_bond_buy_on_date(bonds_buy, date(2023, 10, 26))
    bonds_buy_back = create_bond_buy_back_for_cash()

    handle_debt_acquisition_strategy = create_debt_with_interest()
    debt_payback_strategy = create_debt_payback_strategy(3000_00)

    house_price = 1_000_000_00
    house_buy = create_buy_house(house_price, date(2026, 11, 1))

    YEARS = 20
    DAYS = YEARS * DAYS_YEAR
    simulation = Simulation(DAYS, date(2023, 6, 1))

    simulation.add_event_listener_applied("simulation_started", append_cash(200_000_00, 0))

    simulation.add_event_listener_applied("day_started", work_income)
    simulation.add_event_listener_applied("day_started", life_costs)
    simulation.add_event_listener_applied("day_started", house_buy)
    simulation.add_event_listener_applied("day_started", bonds_buy_on_date)

    simulation.add_event_listener_applied("day_started", debt_payback_strategy)

    simulation.add_event_listener_applied("bond_buy_back", bonds_buy_back)

    simulation.add_event_listener_applied("cash_state_negative", handle_debt_acquisition_strategy)

    simulation.add_event_listener_applied("day_ended", save_state_fn)

    simulation.add_event_listener_applied("simulation_ended", draw_simulation_run)
    simulation.add_event_listener_applied("simulation_ended", get_final_cash_state)

    simulation.simulate()


def load_in_json_config(filename: str):
    with open(filename) as file:
        obj = json.load(file)
    return obj


def build_simulation_from_config(config):
    # build simulation obj
    sim_params = config['simulation_parameters']
    simulation = Simulation(**sim_params)

    # build events

    return simulation


def save_states_and_print_run(simulation):
    save_state_fn, access_state_fn = create_simulation_state_save()
    draw_simulation_run = create_draw_simulation_run(access_state_fn, show_fig)
    simulation.add_event_listener_applied("day_ended", save_state_fn)
    simulation.add_event_listener_applied("simulation_ended", draw_simulation_run)


def execute_loaded_config(config, transform_fn=identity):
    process = pipe(
        build_simulation_from_config,
        transform_fn,
        lambda simulation: simulation.simulate(),
    )
    return process(config)


def execute_config_from_file(filepath: str, transform_fn=identity):
    process = pipe(
        load_in_json_config,
        lambda config: execute_loaded_config(config, transform_fn),
    )
    return process(filepath)
