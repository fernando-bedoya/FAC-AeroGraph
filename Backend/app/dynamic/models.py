"""
Session state model for dynamic planning (Requirement 2.3).

DynamicState holds the complete runtime state of a traveller's interactive
planning session, including budget, time, location, mandatory event timers,
visited airports, action log, and transit status for interruption handling.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from ..models import DynamicStep


@dataclass
class DynamicState:
    """
    Complete runtime state for one dynamic planning session.

    Tracks all traveller resources (budget, time), location, mandatory
    event intervals (food, lodging), visited airports, distance counters
    for the 20% subsidy rule, and the transit status (for route
    interruption handling in R2.4).

    Attributes:
        session_id: Unique UUID identifying this session.
        origin: Original departure airport IATA code.
        current_airport: Airport where the traveller is currently located.
        initial_budget: Starting budget in USD (fixed reference).
        budget_usd: Current available budget in USD.
        time_left_min: Remaining time in minutes.
        total_spent: Cumulative spending in USD across all actions.
        total_earned: Cumulative income from work in USD.
        visited: List of airport IATA codes visited (in order).
        steps: Full action log as a list of DynamicStep entries.
        minutes_since_lodging: Minutes elapsed since last mandatory lodging.
        minutes_since_food: Minutes elapsed since last mandatory meal.
        stay_min: Minutes spent at the current airport (stay counter).
        required_stay_min: Minimum stay required at current airport.
        total_distance_km: Total distance travelled across all flights.
        free_distance_km: Distance travelled on subsidised (cost $0) routes.
        suggested_route: Optimal route calculated by backtracking algorithm.
        in_transit: Whether the traveller is currently mid-flight.
        transit_from: Origin airport of the current in-progress flight.
        transit_to: Destination airport of the current in-progress flight.
        transit_aircraft: Aircraft type used for the current in-progress flight.
    """

    session_id: str
    origin: str
    current_airport: str
    initial_budget: float
    budget_usd: float
    time_left_min: float
    total_spent: float
    total_earned: float
    visited: List[str] = field(default_factory=list)
    steps: List[DynamicStep] = field(default_factory=list)
    minutes_since_lodging: float = 0.0
    minutes_since_food: float = 0.0
    stay_min: float = 0.0
    required_stay_min: float = 0.0
    total_distance_km: float = 0.0
    free_distance_km: float = 0.0
    suggested_route: Dict[str, Any] = field(default_factory=dict)
    # Transit state for route interruption handling (R2.4)
    in_transit: bool = False
    transit_from: Optional[str] = None
    transit_to: Optional[str] = None
    transit_aircraft: Optional[str] = None

    def mark_in_transit(self, origin: str, destination: str, aircraft: str) -> None:
        """
        Mark the traveller as currently mid-flight.

        Args:
            origin: Departure airport IATA code.
            destination: Arrival airport IATA code.
            aircraft: Aircraft type name for this flight segment.
        """
        self.in_transit = True
        self.transit_from = origin
        self.transit_to = destination
        self.transit_aircraft = aircraft

    def clear_transit(self) -> None:
        """Clear the in-transit state after a flight is completed or interrupted."""
        self.in_transit = False
        self.transit_from = None
        self.transit_to = None
        self.transit_aircraft = None
