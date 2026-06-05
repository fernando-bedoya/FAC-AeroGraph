from typing import Dict, List

from ..graph import Graph
from ..models import AircraftConfig
from .core import (
    DynamicPlanError,
    apply_cost_and_time,
    calculate_segment_cost,
    estimate_mandatory_costs,
    find_route,
)
from .models import DynamicState


def list_dynamic_flight_options(
    graph: Graph,
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

            cost = calculate_segment_cost(route, cfg, state)
            if cost is None:
                cost = 0.0

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
    graph: Graph,
    aircraft_cfg: Dict[str, AircraftConfig],
    rules: Dict[str, float],
    state: DynamicState,
    destination: str,
    aircraft: str,
) -> DynamicState:
    route = find_route(graph, state.current_airport, destination)
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
        apply_cost_and_time(
            state,
            rules,
            cost_usd=0.0,
            duration_min=idle_min,
            cost_airport=graph.get_airport(state.current_airport),
            count_stay=True,
            action_label="tiempo_libre",
            detail=f"Tiempo libre para cumplir estancia minima ({idle_min:.0f} min)",
            metadata={"duration": idle_min, "cost": 0.0},
        )

    seg_cost = calculate_segment_cost(route, cfg, state)
    if seg_cost is None:
        raise DynamicPlanError("Este vuelo excede el límite de distancia subsidiada permitido")

    seg_time = route.distance_km * cfg.time_per_km

    # Validacion previa: presupuesto duro antes de confirmar el vuelo.
    _, _, mandatory_cost = estimate_mandatory_costs(
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

    # Marcar al viajero como en tránsito antes de iniciar el vuelo
    state.mark_in_transit(state.current_airport, destination, aircraft)

    apply_cost_and_time(
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
        metadata={
            "origin": route.origin,
            "destination": route.destination,
            "aircraft": aircraft,
            "distance_km": route.distance_km,
            "duration": seg_time,
            "cost": seg_cost,
        },
    )

    state.total_distance_km += route.distance_km
    if route.base_cost == 0:
        state.free_distance_km += route.distance_km

    state.current_airport = destination
    state.visited.append(destination)
    state.stay_min = 0.0
    state.required_stay_min = float(route.min_stay_min)

    # Limpiar estado de tránsito al completar el vuelo
    state.clear_transit()

    return state


def start_dynamic_flight(
    graph: Graph,
    aircraft_cfg: Dict[str, AircraftConfig],
    rules: Dict[str, float],
    state: DynamicState,
    destination: str,
    aircraft: str,
) -> DynamicState:
    route = find_route(graph, state.current_airport, destination)
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
        apply_cost_and_time(
            state,
            rules,
            cost_usd=0.0,
            duration_min=idle_min,
            cost_airport=graph.get_airport(state.current_airport),
            count_stay=True,
            action_label="tiempo_libre",
            detail=f"Tiempo libre para cumplir estancia minima ({idle_min:.0f} min)",
            metadata={"duration": idle_min, "cost": 0.0},
        )

    seg_cost = calculate_segment_cost(route, cfg, state)
    if seg_cost is None:
        raise DynamicPlanError("Este vuelo excede el límite de distancia subsidiada permitido")

    seg_time = route.distance_km * cfg.time_per_km

    # Validacion previa: presupuesto duro antes de confirmar el vuelo.
    _, _, mandatory_cost = estimate_mandatory_costs(
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

    # Marcar al viajero como en tránsito antes de iniciar el vuelo
    state.mark_in_transit(state.current_airport, destination, aircraft)
    return state


def complete_dynamic_flight(
    graph: Graph,
    aircraft_cfg: Dict[str, AircraftConfig],
    rules: Dict[str, float],
    state: DynamicState,
) -> DynamicState:
    if not state.in_transit:
        raise DynamicPlanError("El viajero no está en tránsito")

    origin = state.transit_from
    destination = state.transit_to
    aircraft = state.transit_aircraft

    route = find_route(graph, origin, destination)
    cfg = aircraft_cfg.get(aircraft)
    seg_cost = calculate_segment_cost(route, cfg, state)
    seg_time = route.distance_km * cfg.time_per_km

    apply_cost_and_time(
        state,
        rules,
        cost_usd=seg_cost,
        duration_min=seg_time,
        cost_airport=graph.get_airport(origin),
        count_stay=False,
        action_label="vuelo",
        detail=(
            f"Vuelo {origin}->{destination} en {aircraft}, "
            f"costo {seg_cost:.2f} USD, tiempo {seg_time:.1f} min"
        ),
        step_airport_id=destination,
        metadata={
            "origin": origin,
            "destination": destination,
            "aircraft": aircraft,
            "distance_km": route.distance_km,
            "duration": seg_time,
            "cost": seg_cost,
        },
    )

    state.total_distance_km += route.distance_km
    if route.base_cost == 0:
        state.free_distance_km += route.distance_km

    state.current_airport = destination
    state.visited.append(destination)
    state.stay_min = 0.0
    state.required_stay_min = float(route.min_stay_min)

    # Limpiar estado de tránsito al completar el vuelo
    state.clear_transit()

    return state
