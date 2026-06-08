"""
Session lifecycle management for dynamic planning (Requirement 2.3).

Provides functions to create, retrieve, and terminate interactive dynamic
planning sessions. Each session is stored in-memory keyed by a UUID.
"""

import uuid
from typing import Dict

from ..graph import Graph
from ..models import AircraftConfig
from .core import DynamicPlanError
from .models import DynamicState
from .routing import calculate_suggested_route


def start_dynamic_session(
    graph: Graph,
    aircraft_cfg: Dict[str, AircraftConfig],
    rules: Dict[str, float],
    origin: str,
    initial_budget: float,
    total_time_hours: float,
    sessions: Dict[str, DynamicState],
) -> DynamicState:
    """
    Create and initialise a new dynamic planning session.

    Validates the origin airport, generates a unique session UUID,
    calculates the optimal suggested route via backtracking, and
    initialises a DynamicState with full budget and time resources.

    Args:
        graph: The airline route graph.
        aircraft_cfg: Aircraft configuration dictionary keyed by type name.
        rules: System rules (intervals, budget trigger, etc.).
        origin: Departure airport IATA code.
        initial_budget: Starting budget in USD.
        total_time_hours: Total available time in hours.
        sessions: In-memory dict of active sessions (mutated in-place).

    Returns:
        The newly created DynamicState instance.

    Raises:
        DynamicPlanError: If the origin airport does not exist.
    """
    if not graph.get_airport(origin):
        raise DynamicPlanError("Origin airport does not exist")

    session_id = str(uuid.uuid4())
    total_time_min = total_time_hours * 60

    suggested_route = calculate_suggested_route(
        graph=graph,
        aircraft_cfg=aircraft_cfg,
        origin=origin,
        initial_budget=initial_budget,
        total_time_min=total_time_min,
    )

    state = DynamicState(
        session_id=session_id,
        origin=origin,
        current_airport=origin,
        initial_budget=initial_budget,
        budget_usd=initial_budget,
        time_left_min=total_time_min,
        total_spent=0.0,
        total_earned=0.0,
        visited=[origin],
        steps=[],
        minutes_since_food=0.0,
        minutes_since_lodging=0.0,
        stay_min=0.0,
        required_stay_min=0.0,
        total_distance_km=0.0,
        free_distance_km=0.0,
        suggested_route=suggested_route,
    )
    sessions[session_id] = state
    return state


def end_dynamic_session(session_id: str, sessions: Dict[str, DynamicState]) -> None:
    """
    Terminate and remove a dynamic planning session.

    Args:
        session_id: UUID of the session to remove.
        sessions: In-memory dict of active sessions (mutated in-place).
    """
    sessions.pop(session_id, None)


def get_dynamic_state(session_id: str, sessions: Dict[str, DynamicState]) -> DynamicState:
    """
    Retrieve the current state of a dynamic planning session.

    Args:
        session_id: UUID of the session.
        sessions: In-memory dict of active sessions.

    Returns:
        The DynamicState for the given session.

    Raises:
        DynamicPlanError: If the session ID is not found.
    """
    state = sessions.get(session_id)
    if not state:
        raise DynamicPlanError("Dynamic session not found")
    return state
