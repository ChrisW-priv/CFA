from datetime import date

from SimCFA.LedgerItem import DAYS_YEAR, three_year_bond_builder
from SimCFA.simulation import Simulation
from SimCFA.simulation_procedures import *
from SimCFA.functional import empty


def main():
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
    draw_simulation_run = create_draw_simulation_run(access_state_fn)
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


if __name__ == "__main__":
    main()
