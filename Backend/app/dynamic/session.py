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
    if not graph.get_airport(origin):
        raise DynamicPlanError("Aeropuerto de origen no existe")

    session_id = str(uuid.uuid4())
    total_time_min = total_time_hours * 60

    # Calcular la ruta sugerida
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
    sessions.pop(session_id, None)


def get_dynamic_state(session_id: str, sessions: Dict[str, DynamicState]) -> DynamicState:
    state = sessions.get(session_id)
    if not state:
        raise DynamicPlanError("Sesion dinamica no encontrada")
    return state
