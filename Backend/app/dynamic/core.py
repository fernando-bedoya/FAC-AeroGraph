from typing import Dict, List, Optional, Tuple

from ..graph import Graph
from ..models import AircraftConfig, DynamicStep
from .models import DynamicState
from typing import Any


class DynamicPlanError(ValueError):
    pass


def apply_cost_and_time(
    state: DynamicState,
    rules: Dict[str, float],
    cost_usd: float,
    duration_min: float,
    cost_airport,
    count_stay: bool,
    action_label: str,
    detail: str,
    step_airport_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    validate_action(state, rules, duration_min, cost_usd, cost_airport)

    state.budget_usd -= cost_usd
    state.total_spent += cost_usd
    time_left_after_action, mandatory_events = advance_time(
        state, rules, duration_min, cost_airport, count_stay
    )

    step_airport = step_airport_id or state.current_airport
    state.steps.append(
        DynamicStep(
            airport_id=step_airport,
            action=action_label,
            detail=detail,
            budget_after=state.budget_usd,
            time_left_min=time_left_after_action,
            metadata=metadata or {},
        )
    )

    apply_mandatory_events(state, cost_airport, mandatory_events, time_left_after_action)


def apply_time_only(
    state: DynamicState,
    rules: Dict[str, float],
    duration_min: float,
    cost_airport,
    count_stay: bool,
) -> Tuple[float, List[Dict[str, float]]]:
    validate_action(state, rules, duration_min, 0.0, cost_airport)
    return advance_time(state, rules, duration_min, cost_airport, count_stay)


def apply_mandatory_events(
    state: DynamicState,
    cost_airport,
    mandatory_events: List[Dict[str, float]],
    time_left_after_action: float,
) -> None:
    if not cost_airport:
        return

    for event in mandatory_events:
        event_cost = event["cost"]
        state.budget_usd -= event_cost
        state.total_spent += event_cost
        state.steps.append(
            DynamicStep(
                airport_id=state.current_airport,
                action=event["action"],
                detail=event["detail"],
                budget_after=state.budget_usd,
                time_left_min=time_left_after_action,
                metadata={"cost": event["cost"]},
            )
        )


def validate_action(
    state: DynamicState,
    rules: Dict[str, float],
    duration_min: float,
    cost_usd: float,
    cost_airport,
) -> None:
    if duration_min <= 0:
        raise DynamicPlanError("Duracion invalida")

    if state.time_left_min - duration_min < 0:
        raise DynamicPlanError("No hay tiempo suficiente para esta accion")

    _, _, mandatory_cost = estimate_mandatory_costs(
        state,
        duration_min,
        rules,
        cost_airport,
    )
    total_cost = cost_usd + mandatory_cost
    if state.budget_usd - total_cost < 0:
        raise DynamicPlanError("Presupuesto insuficiente para esta accion")


def estimate_mandatory_costs(
    state: DynamicState,
    duration_min: float,
    rules: Dict[str, float],
    cost_airport,
) -> Tuple[int, int, float]:
    food_interval_min = rules.get("food_interval_h", 8) * 60
    lodging_interval_min = rules.get("lodging_interval_h", 20) * 60

    new_food = state.minutes_since_food + duration_min
    new_lodging = state.minutes_since_lodging + duration_min

    meals = int(new_food // food_interval_min) if food_interval_min > 0 else 0
    lodgings = int(new_lodging // lodging_interval_min) if lodging_interval_min > 0 else 0

    cost = 0.0
    if cost_airport:
        cost += meals * cost_airport.food_cost
        cost += lodgings * cost_airport.lodging_cost

    return meals, lodgings, cost


def advance_time(
    state: DynamicState,
    rules: Dict[str, float],
    duration_min: float,
    cost_airport,
    count_stay: bool,
) -> Tuple[float, List[Dict[str, float]]]:
    food_interval_min = rules.get("food_interval_h", 8) * 60
    lodging_interval_min = rules.get("lodging_interval_h", 20) * 60

    state.minutes_since_food += duration_min
    state.minutes_since_lodging += duration_min
    if count_stay:
        state.stay_min += duration_min

    meals = int(state.minutes_since_food // food_interval_min) if food_interval_min > 0 else 0
    lodgings = int(state.minutes_since_lodging // lodging_interval_min) if lodging_interval_min > 0 else 0

    if food_interval_min > 0:
        state.minutes_since_food -= meals * food_interval_min
    if lodging_interval_min > 0:
        state.minutes_since_lodging -= lodgings * lodging_interval_min

    mandatory_events: List[Dict[str, float]] = []
    if cost_airport:
        for _ in range(meals):
            mandatory_events.append(
                {
                    "action": "alimentacion",
                    "detail": f"Alimentacion obligatoria ({cost_airport.food_cost:.2f} USD)",
                    "cost": cost_airport.food_cost,
                }
            )

        for _ in range(lodgings):
            mandatory_events.append(
                {
                    "action": "alojamiento",
                    "detail": f"Alojamiento obligatorio ({cost_airport.lodging_cost:.2f} USD)",
                    "cost": cost_airport.lodging_cost,
                }
            )

    # Restar tiempo total de la accion
    state.time_left_min -= duration_min
    return state.time_left_min, mandatory_events


def calculate_segment_cost(route, cfg: AircraftConfig, state: DynamicState):
    base_cost = route.distance_km * cfg.cost_per_km
    if route.base_cost != 0:
        return base_cost

    # En la sesión inicial (sin haber viajado), permitir cualquier ruta subsidiada
    # La restricción del 20% solo se aplica después de haber viajado algo
    if state.total_distance_km == 0:
        return 0.0

    projected_total = state.total_distance_km + route.distance_km
    projected_free = state.free_distance_km + route.distance_km
    max_free = projected_total * 0.2

    if projected_free > max_free:
        return None
    return 0.0


def find_route(graph: Graph, origin: str, destination: str):
    for route in graph.get_outgoing_routes(origin):
        if route.destination == destination:
            return route
    return None


def can_work(state: DynamicState, rules: Dict[str, float]) -> bool:
    threshold = state.initial_budget * (rules.get("budget_trigger_percent", 35) / 100.0)
    return state.budget_usd < threshold


def is_affordable(state: DynamicState, cost_usd: float, duration_min: float) -> bool:
    return state.budget_usd >= cost_usd and state.time_left_min >= duration_min
