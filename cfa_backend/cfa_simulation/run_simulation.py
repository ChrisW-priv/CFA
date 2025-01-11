from pathlib import Path

from SimCFA.simulation_procedures import *  # noqa
from SimCFA.simulation import Simulation

from .models import SimulationConfig, SimulationEvent


def run_simulation(simulation_config: SimulationConfig) -> Path:
    """
    Runs the simulation given the events passed, returns the path to the new image with the simulation result.

    :param simulation_config: simulation configuration from database
    :return: Path to the simulation result
    """
    events = SimulationEvent.objects.filter(simulation=simulation_config)
    simulation = Simulation(start_date=simulation_config.start_date, end_date=simulation_config.end_date)
    for event in events:  # noqa Add event to the simulation
        ...
    simulation.simulate()
    # Use accessor to get the result and save it to path
    path = 'Lol, some path here'
    return path
