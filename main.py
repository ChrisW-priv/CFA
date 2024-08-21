from simulation_procedures import *
from simulation import Simulation
from LedgerItem import year_bond_builder


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
