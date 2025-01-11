from SimCFA.simulation import Simulation
from SimCFA.simulation_procedures import (
    create_simulate_monthly_cash_move,
    create_simulation_state_save,
    create_draw_simulation_run,
    create_calculate_inflation,
    append_cash,
)

from .models import SimulationConfig, SimulationEvent, ValidEvents


def build_save_fig(name: str):
    def save_fig(fig):
        fig.savefig('data/' + name)

    return save_fig


def build_simulation_event_from_db_event(event: SimulationEvent):
    sim_event = None
    if event.event == ValidEvents.monthly_income:
        sim_event = create_simulate_monthly_cash_move(event.value, event.start_date, event.end_date, 10)
    return sim_event


def run_simulation(simulation_config: SimulationConfig):
    """
    Runs the simulation given the events passed, returns the path to the new image with the simulation result.

    :param simulation_config: simulation configuration from database
    :return: Path to the simulation result
    """
    events = SimulationEvent.objects.filter(simulation=simulation_config)

    simulation = Simulation(start_date=simulation_config.start_date, end_date=simulation_config.end_date)
    simulation.add_event_listener_applied('simulation_started', append_cash(0, 0))
    if simulation_config.include_inflation:
        simulation.add_event_listener_applied('day_started', create_calculate_inflation(3))

    for event in events:
        sim_event = build_simulation_event_from_db_event(event)
        simulation.add_event_listener_applied('day_started', sim_event)

    save_state_fn, access_state_fn = create_simulation_state_save()
    save_fig = build_save_fig(f'{simulation_config.pk}.png')
    draw_simulation_run = create_draw_simulation_run(access_state_fn, save_fig)
    simulation.add_event_listener_applied('day_ended', save_state_fn)
    simulation.add_event_listener_applied('simulation_ended', draw_simulation_run)

    simulation.simulate()
