import uuid
from typing import Dict, List, Optional, Tuple

from ..algorithms import bellman_ford_max_coverage
from ..graph import DirectedGraph
from ..models import AircraftConfig, DynamicStep
from .models import DynamicState


class DynamicPlanError(ValueError):
    pass


def _calculate_suggested_route(
    graph: DirectedGraph,
    aircraft_cfg: Dict[str, AircraftConfig],
    origin: str,
    initial_budget: float,
    total_time_min: float,
) -> Dict:
    """
    Calcula la ruta óptima sugerida que maximiza destinos con menor gasto.
    
    Utiliza el algoritmo Bellman-Ford de cobertura máxima que:
    1. Maximiza la cantidad de aeropuertos visitados
    2. Minimiza el costo total
    3. Respeta restricciones de presupuesto y tiempo
    """
    try:
        # Calcular ruta optimizada por costo que maximice destinos
        segments = bellman_ford_max_coverage(
            graph=graph,
            aircraft_cfg=aircraft_cfg,
            origin=origin,
            budget_limit=initial_budget,
            time_limit_min=total_time_min,
            optimize_for="costo",
        )
        
        if not segments:
            return {
                "airports": [origin],
                "segments": [],
                "total_cost": 0.0,
                "total_time_min": 0.0,
                "destination_count": 1,
            }
        
        # Reconstruir la lista de aeropuertos visitados
        visited = [origin]
        total_cost = 0.0
        total_time = 0.0
        
        for segment in segments:
            visited.append(segment.destination)
            total_cost += segment.segment_cost
            total_time += segment.segment_time_min
        
        return {
            "airports": visited,
            "segments": [
                {
                    "origin": s.origin,
                    "destination": s.destination,
                    "aircraft": s.aircraft,
                    "distance_km": s.distance_km,
                    "segment_cost": s.segment_cost,
                    "segment_time_min": s.segment_time_min,
                }
                for s in segments
            ],
            "total_cost": total_cost,
            "total_time_min": total_time,
            "destination_count": len(visited),
        }
    except Exception as e:
        # Si hay error, retornar ruta vacía con solo origen
        return {
            "airports": [origin],
            "segments": [],
            "total_cost": 0.0,
            "total_time_min": 0.0,
            "destination_count": 1,
            "error": str(e),
        }


def start_dynamic_session(
    graph: DirectedGraph,
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
    suggested_route = _calculate_suggested_route(
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


def list_dynamic_activities(
    graph: DirectedGraph,
    rules: Dict[str, float],
    state: DynamicState,
) -> List[Dict[str, float]]:
    airport = graph.get_airport(state.current_airport)
    if not airport:
        return []

    items = []
    for activity in airport.activities:
        _, _, mandatory_cost = _estimate_mandatory_costs(
            state,
            activity.duration_min,
            rules,
            airport,
        )
        items.append(
            {
                "name": activity.name,
                "kind": activity.kind,
                "duration_min": activity.duration_min,
                "cost_usd": activity.cost_usd,
                "affordable": _is_affordable(
                    state,
                    activity.cost_usd + mandatory_cost,
                    activity.duration_min,
                ),
            }
        )
    return items


def choose_dynamic_activities(
    graph: DirectedGraph,
    rules: Dict[str, float],
    state: DynamicState,
    activity_names: List[str],
) -> DynamicState:
    airport = graph.get_airport(state.current_airport)
    if not airport:
        raise DynamicPlanError("Aeropuerto actual no existe")

    if not activity_names:
        return state

    activity_map = {activity.name: activity for activity in airport.activities}
    for name in activity_names:
        activity = activity_map.get(name)
        if not activity:
            raise DynamicPlanError(f"Actividad no encontrada: {name}")

        _apply_cost_and_time(
            state,
            rules,
            cost_usd=activity.cost_usd,
            duration_min=activity.duration_min,
            cost_airport=airport,
            count_stay=True,
            action_label="actividad",
            detail=f"Actividad: {activity.name} ({activity.duration_min} min)",
        )

    return state


def list_dynamic_jobs(
    graph: DirectedGraph,
    rules: Dict[str, float],
    state: DynamicState,
) -> List[Dict[str, float]]:
    airport = graph.get_airport(state.current_airport)
    if not airport:
        return []

    if not _can_work(state, rules):
        return []

    return [
        {
            "name": job.name,
            "hourly_rate": job.hourly_rate,
            "max_hours": job.max_hours,
        }
        for job in airport.jobs
    ]


def perform_dynamic_work(
    graph: DirectedGraph,
    rules: Dict[str, float],
    state: DynamicState,
    job_name: str,
    hours: int,
) -> DynamicState:
    airport = graph.get_airport(state.current_airport)
    if not airport:
        raise DynamicPlanError("Aeropuerto actual no existe")

    if not _can_work(state, rules):
        raise DynamicPlanError("Presupuesto suficiente, no se habilita trabajo")

    job_map = {job.name: job for job in airport.jobs}
    job = job_map.get(job_name)
    if not job:
        raise DynamicPlanError("Trabajo no encontrado")

    if hours <= 0:
        raise DynamicPlanError("Horas invalidas")
    if hours > job.max_hours:
        raise DynamicPlanError("Horas exceden el maximo permitido")

    duration_min = hours * 60
    _apply_time_only(
        state,
        rules,
        duration_min=duration_min,
        cost_airport=airport,
        count_stay=True,
    )

    earned = job.hourly_rate * hours
    state.budget_usd += earned
    state.total_earned += earned
    state.steps.append(
        DynamicStep(
            airport_id=airport.id,
            action="trabajo",
            detail=f"Trabajo: {job.name} por {hours}h, ingreso {earned:.2f} USD",
            budget_after=state.budget_usd,
            time_left_min=state.time_left_min,
        )
    )
    return state


def list_dynamic_flight_options(
    graph: DirectedGraph,
    aircraft_cfg: Dict[str, AircraftConfig],
    state: DynamicState,
) -> List[Dict[str, float]]:
    options = []
    for route in graph.get_outgoing_routes(state.current_airport):
        if route.blocked:
            continue
        if route.destination in state.visited:
            continue

        for aircraft in route.aircraft_types:
            cfg = aircraft_cfg.get(aircraft)
            if not cfg:
                continue

            cost = _calculate_segment_cost(route, cfg, state)
            if cost is None:
                continue

            time_min = route.distance_km * cfg.time_per_km
            options.append(
                {
                    "origin": route.origin,
                    "destination": route.destination,
                    "aircraft": aircraft,
                    "distance_km": route.distance_km,
                    "segment_cost": cost,
                    "segment_time_min": time_min,
                    "min_stay_min": route.min_stay_min,
                    "subsidized": route.base_cost == 0,
                }
            )
    return options


def perform_dynamic_flight(
    graph: DirectedGraph,
    aircraft_cfg: Dict[str, AircraftConfig],
    rules: Dict[str, float],
    state: DynamicState,
    destination: str,
    aircraft: str,
) -> DynamicState:
    route = _find_route(graph, state.current_airport, destination)
    if not route:
        raise DynamicPlanError("Ruta no encontrada")
    if route.blocked:
        raise DynamicPlanError("Ruta bloqueada")
    if destination in state.visited:
        raise DynamicPlanError("No se permite visitar el mismo aeropuerto dos veces")
    if aircraft not in route.aircraft_types:
        raise DynamicPlanError("Aeronave no disponible en la ruta")

    cfg = aircraft_cfg.get(aircraft)
    if not cfg:
        raise DynamicPlanError("Configuracion de aeronave no encontrada")

    if state.stay_min < state.required_stay_min:
        idle_min = state.required_stay_min - state.stay_min
        _apply_cost_and_time(
            state,
            rules,
            cost_usd=0.0,
            duration_min=idle_min,
            cost_airport=graph.get_airport(state.current_airport),
            count_stay=True,
            action_label="tiempo_libre",
            detail=f"Tiempo libre para cumplir estancia minima ({idle_min:.0f} min)",
        )

    seg_cost = _calculate_segment_cost(route, cfg, state)
    if seg_cost is None:
        raise DynamicPlanError("Ruta subsidiada excede el limite permitido")

    seg_time = route.distance_km * cfg.time_per_km

    # Validacion previa: presupuesto duro antes de confirmar el vuelo.
    _, _, mandatory_cost = _estimate_mandatory_costs(
        state,
        seg_time,
        rules,
        graph.get_airport(route.origin),
    )
    projected_budget = state.budget_usd - (seg_cost + mandatory_cost)
    if projected_budget < 0:
        raise DynamicPlanError(
            "Presupuesto insuficiente por costos de alimentacion y alojamiento para completar el trayecto."
        )

    _apply_cost_and_time(
        state,
        rules,
        cost_usd=seg_cost,
        duration_min=seg_time,
        cost_airport=graph.get_airport(route.origin),
        count_stay=False,
        action_label="vuelo",
        detail=(
            f"Vuelo {route.origin}->{route.destination} en {aircraft}, "
            f"costo {seg_cost:.2f} USD, tiempo {seg_time:.1f} min"
        ),
        step_airport_id=route.destination,
    )

    state.total_distance_km += route.distance_km
    if route.base_cost == 0:
        state.free_distance_km += route.distance_km

    state.current_airport = destination
    state.visited.append(destination)
    state.stay_min = 0.0
    state.required_stay_min = float(route.min_stay_min)

    return state


def _apply_cost_and_time(
    state: DynamicState,
    rules: Dict[str, float],
    cost_usd: float,
    duration_min: float,
    cost_airport,
    count_stay: bool,
    action_label: str,
    detail: str,
    step_airport_id: Optional[str] = None,
) -> None:
    _validate_action(state, rules, duration_min, cost_usd, cost_airport)

    state.budget_usd -= cost_usd
    state.total_spent += cost_usd
    _advance_time(state, rules, duration_min, cost_airport, count_stay)

    step_airport = step_airport_id or state.current_airport
    state.steps.append(
        DynamicStep(
            airport_id=step_airport,
            action=action_label,
            detail=detail,
            budget_after=state.budget_usd,
            time_left_min=state.time_left_min,
        )
    )


def _apply_time_only(
    state: DynamicState,
    rules: Dict[str, float],
    duration_min: float,
    cost_airport,
    count_stay: bool,
) -> None:
    _validate_action(state, rules, duration_min, 0.0, cost_airport)
    _advance_time(state, rules, duration_min, cost_airport, count_stay)


def _validate_action(
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

    _, _, mandatory_cost = _estimate_mandatory_costs(
        state,
        duration_min,
        rules,
        cost_airport,
    )
    total_cost = cost_usd + mandatory_cost
    if state.budget_usd - total_cost < 0:
        raise DynamicPlanError("Presupuesto insuficiente para esta accion")


def _estimate_mandatory_costs(
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


def _advance_time(
    state: DynamicState,
    rules: Dict[str, float],
    duration_min: float,
    cost_airport,
    count_stay: bool,
) -> None:
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

    # Registrar comidas y alojamientos con tiempo progresivo
    if cost_airport:
        for i in range(meals):
            state.budget_usd -= cost_airport.food_cost
            state.total_spent += cost_airport.food_cost
            # Calcular tiempo restante progresivamente: restar proporcionalmente
            time_per_event = (meals + lodgings) > 0 and duration_min / (meals + lodgings) or 0
            progressive_time = state.time_left_min - duration_min + (i + 1) * time_per_event
            state.steps.append(
                DynamicStep(
                    airport_id=state.current_airport,
                    action="alimentacion",
                    detail=f"Alimentacion obligatoria ({cost_airport.food_cost:.2f} USD)",
                    budget_after=state.budget_usd,
                    time_left_min=progressive_time,
                )
            )

        for i in range(lodgings):
            state.budget_usd -= cost_airport.lodging_cost
            state.total_spent += cost_airport.lodging_cost
            # Calcular tiempo restante progresivamente
            time_per_event = (meals + lodgings) > 0 and duration_min / (meals + lodgings) or 0
            progressive_time = state.time_left_min - duration_min + (meals + i + 1) * time_per_event
            state.steps.append(
                DynamicStep(
                    airport_id=state.current_airport,
                    action="alojamiento",
                    detail=f"Alojamiento obligatorio ({cost_airport.lodging_cost:.2f} USD)",
                    budget_after=state.budget_usd,
                    time_left_min=progressive_time,
                )
            )

    # Restar tiempo total DESPUÉS de registrar eventos progresivos
    state.time_left_min -= duration_min


def _calculate_segment_cost(route, cfg: AircraftConfig, state: DynamicState):
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


def _find_route(graph: DirectedGraph, origin: str, destination: str):
    for route in graph.get_outgoing_routes(origin):
        if route.destination == destination:
            return route
    return None


def _can_work(state: DynamicState, rules: Dict[str, float]) -> bool:
    threshold = state.initial_budget * (rules.get("budget_trigger_percent", 35) / 100.0)
    return state.budget_usd < threshold


def _is_affordable(state: DynamicState, cost_usd: float, duration_min: float) -> bool:
    return state.budget_usd >= cost_usd and state.time_left_min >= duration_min
