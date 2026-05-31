from typing import Dict, List, Set

from .algorithms import dijkstra_path, bellman_ford_max_coverage
from .graph import Graph
from .models import AircraftConfig, DynamicPlan, DynamicStep, TravelPlan


def _sum_cost(segments) -> float:
    return sum(s.segment_cost for s in segments)


def _sum_time(segments) -> float:
    return sum(s.segment_time_min for s in segments)


def plan_basic_itinerary(
    graph: Graph,
    aircraft_cfg: Dict[str, AircraftConfig],
    origin: str,
    budget_usd: float,
    time_hours: float,
) -> Dict[str, TravelPlan]:
    
    # 🔴 AQUÍ SE CALCULA LA RUTA POR PRESUPUESTO
    max_destinations_budget = bellman_ford_max_coverage(
        graph=graph,
        aircraft_cfg=aircraft_cfg,
        origin=origin,
        budget_limit=budget_usd,              # ← Límite presupuestario
        time_limit_min=time_hours * 60,
        optimize_for="costo",                 # ← Optimiza por COSTO
    )
    
    # También calcula por tiempo (parte b)
    max_destinations_time = bellman_ford_max_coverage(
        graph=graph,
        aircraft_cfg=aircraft_cfg,
        origin=origin,
        budget_limit=budget_usd,
        time_limit_min=time_hours * 60,
        optimize_for="tiempo",                # ← Optimiza por TIEMPO
    )

    # Extrae los aeropuertos visitados
    budget_airports = [origin] + [s.destination for s in max_destinations_budget]
    time_airports = [origin] + [s.destination for s in max_destinations_time]

    # 📦 RETORNA DOS ALTERNATIVAS
    return {
        "budget_route": TravelPlan(
            title="Mayor cantidad de destinos sin exceder presupuesto",
            visited_airports=budget_airports,
            segments=max_destinations_budget,   # ← Secuencia de vuelos
            total_cost=_sum_cost(max_destinations_budget),      # ← Costo acumulado
            total_time_min=_sum_time(max_destinations_budget),
        ),
        "time_route": TravelPlan(
            title="Mayor cantidad de destinos en menor tiempo",
            visited_airports=time_airports,
            segments=max_destinations_time,    # ← Secuencia de vuelos
            total_cost=_sum_cost(max_destinations_time),
            total_time_min=_sum_time(max_destinations_time),
        ),
    }


def plan_best_route_by_criteria(
    graph: Graph,
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
