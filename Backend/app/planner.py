from typing import Dict, List, Set

from .algorithms import dijkstra_path, greedy_cover_route
from .graph import DirectedGraph
from .models import AircraftConfig, DynamicPlan, DynamicStep, TravelPlan


def _sum_cost(segments) -> float:
    return sum(s.segment_cost for s in segments)


def _sum_time(segments) -> float:
    return sum(s.segment_time_min for s in segments)


def plan_basic_itinerary(
    graph: DirectedGraph,
    aircraft_cfg: Dict[str, AircraftConfig],
    origin: str,
    budget_usd: float,
    time_hours: float,
) -> Dict[str, TravelPlan]:
    max_destinations_budget = greedy_cover_route(
        graph=graph,
        aircraft_cfg=aircraft_cfg,
        origin=origin,
        budget_limit=budget_usd,
        time_limit_min=time_hours * 60,
        optimize_for="costo",
    )
    max_destinations_time = greedy_cover_route(
        graph=graph,
        aircraft_cfg=aircraft_cfg,
        origin=origin,
        budget_limit=budget_usd,
        time_limit_min=time_hours * 60,
        optimize_for="tiempo",
    )

    budget_airports = [origin] + [s.destination for s in max_destinations_budget]
    time_airports = [origin] + [s.destination for s in max_destinations_time]

    return {
        "budget_route": TravelPlan(
            title="Mayor cantidad de destinos sin exceder presupuesto",
            visited_airports=budget_airports,
            segments=max_destinations_budget,
            total_cost=_sum_cost(max_destinations_budget),
            total_time_min=_sum_time(max_destinations_budget),
        ),
        "time_route": TravelPlan(
            title="Mayor cantidad de destinos en menor tiempo",
            visited_airports=time_airports,
            segments=max_destinations_time,
            total_cost=_sum_cost(max_destinations_time),
            total_time_min=_sum_time(max_destinations_time),
        ),
    }


def plan_best_route_by_criteria(
    graph: DirectedGraph,
    aircraft_cfg: Dict[str, AircraftConfig],
    origin: str,
    destination: str,
    criteria: List[str],
    exclude_secondary: bool,
    allowed_aircraft: List[str],
):
    results = {}
    allowed_set: Set[str] = set(allowed_aircraft)
    for criterion in criteria:
        path = dijkstra_path(
            graph=graph,
            aircraft_cfg=aircraft_cfg,
            origin=origin,
            destination=destination,
            criterion=criterion,
            allowed_aircraft=allowed_set if allowed_aircraft else None,
            exclude_secondary=exclude_secondary,
        )
        results[criterion] = {
            "segments": [segment.__dict__ for segment in path],
            "total_cost": _sum_cost(path),
            "total_time_min": _sum_time(path),
            "total_distance_km": sum(s.distance_km for s in path),
            "reachable": len(path) > 0 or origin == destination,
        }
    return results


def simulate_dynamic_plan(
    graph: DirectedGraph,
    aircraft_cfg: Dict[str, AircraftConfig],
    origin: str,
    initial_budget: float,
    total_time_hours: float,
    budget_trigger_percent: float,
) -> DynamicPlan:
    # Version academica simplificada: recorre en modo greedy y trabaja si el presupuesto esta bajo.
    current_budget = initial_budget
    time_left_min = total_time_hours * 60
    total_spent = 0.0
    total_earned = 0.0
    visited = [origin]
    steps: List[DynamicStep] = []

    segments = greedy_cover_route(
        graph,
        aircraft_cfg,
        origin,
        budget_limit=10**9,
        time_limit_min=time_left_min,
        optimize_for="costo",
    )

    for segment in segments:
        if time_left_min <= 0:
            break

        min_budget_allowed = initial_budget * (budget_trigger_percent / 100.0)
        airport = graph.get_airport(segment.origin)

        if current_budget < min_budget_allowed and airport and airport.jobs:
            job = airport.jobs[0]
            worked_hours = min(2, job.max_hours)
            earned = job.hourly_rate * worked_hours
            current_budget += earned
            total_earned += earned
            time_left_min -= worked_hours * 60
            steps.append(
                DynamicStep(
                    airport_id=airport.id,
                    action="trabajo",
                    detail=f"Trabajo: {job.name} por {worked_hours}h, ingreso {earned:.2f} USD",
                    budget_after=current_budget,
                    time_left_min=time_left_min,
                )
            )

        travel_cost = segment.segment_cost
        travel_time = segment.segment_time_min

        if current_budget - travel_cost < 0 or time_left_min - travel_time < 0:
            break

        current_budget -= travel_cost
        total_spent += travel_cost
        time_left_min -= travel_time
        visited.append(segment.destination)
        steps.append(
            DynamicStep(
                airport_id=segment.destination,
                action="vuelo",
                detail=(
                    f"Vuelo {segment.origin}->{segment.destination} en {segment.aircraft}, "
                    f"costo {travel_cost:.2f} USD, tiempo {travel_time:.1f} min"
                ),
                budget_after=current_budget,
                time_left_min=time_left_min,
            )
        )

    return DynamicPlan(
        steps=steps,
        visited_airports=visited,
        total_spent=total_spent,
        total_earned=total_earned,
        final_budget=current_budget,
    )
