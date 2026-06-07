"""
Route model representing a directed edge in the airline graph.

Each route connects two airports and carries metadata about distance,
available aircraft, cost structure, and minimum stay requirements.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Route:
    """
    A directed route (edge) between two airports.

    Routes may be operated by multiple aircraft types and can be
    temporarily blocked to simulate real-world disruptions.
    A base_cost of 0 indicates a subsidised route subject to a
    20% distance cap.

    Attributes:
        origin: Origin airport IATA code.
        destination: Destination airport IATA code.
        distance_km: Great-circle distance in kilometres.
        aircraft_types: List of aircraft type names that operate this route.
        base_cost: Base cost modifier; 0 means subsidised route.
        min_stay_min: Minimum required stay at the destination in minutes.
        blocked: Whether the route is currently blocked (disabled).
    """

    origin: str
    destination: str
    distance_km: float
    aircraft_types: List[str]
    base_cost: float
    min_stay_min: int
    blocked: bool = False
