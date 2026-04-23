import heapq
from typing import Dict, List, Optional, Set, Tuple

from .graph import DirectedGraph
from .models import AircraftConfig, Route, TravelSegment


def _weight_for_route(route: Route, aircraft_cfg: Dict[str, AircraftConfig], criterion: str) -> Tuple[float, str, float, float]:
    # Elegimos la mejor aeronave para el criterio actual en este tramo.
    best_weight = float("inf")
    best_aircraft = ""
    best_cost = 0.0
    best_time = 0.0

    for aircraft_name in route.aircraft_types:
        cfg = aircraft_cfg.get(aircraft_name)
        if not cfg:
            continue
        segment_cost = route.distance_km * cfg.cost_per_km
        if route.base_cost == 0:
            segment_cost = 0.0
        segment_time = route.distance_km * cfg.time_per_km

        if criterion == "distancia":
            weight = route.distance_km
        elif criterion == "tiempo":
            weight = segment_time
        else:
            weight = segment_cost

        if weight < best_weight:
            best_weight = weight
            best_aircraft = aircraft_name
            best_cost = segment_cost
            best_time = segment_time

    return best_weight, best_aircraft, best_cost, best_time


def dijkstra_path(
    graph: DirectedGraph,
    aircraft_cfg: Dict[str, AircraftConfig],
    origin: str,
    destination: str,
    criterion: str,
    allowed_aircraft: Optional[Set[str]] = None,
    exclude_secondary: bool = False,
) -> List[TravelSegment]:
    dist: Dict[str, float] = {origin: 0.0}
    prev: Dict[str, Tuple[str, str, float, float, float]] = {}
    queue: List[Tuple[float, str]] = [(0.0, origin)]
    visited: Set[str] = set()

    while queue:
        current_dist, node = heapq.heappop(queue)
        if node in visited:
            continue
        visited.add(node)

        if node == destination:
            break

        for route in graph.get_outgoing_routes(node):
            if route.blocked:
                continue
            airport_dest = graph.get_airport(route.destination)
            if exclude_secondary and airport_dest and not airport_dest.is_hub:
                continue

            available_types = route.aircraft_types
            if allowed_aircraft:
                available_types = [t for t in available_types if t in allowed_aircraft]
            if not available_types:
                continue

            filtered_route = Route(
                origin=route.origin,
                destination=route.destination,
                distance_km=route.distance_km,
                aircraft_types=available_types,
                base_cost=route.base_cost,
                min_stay_min=route.min_stay_min,
                blocked=route.blocked,
            )

            weight, aircraft, seg_cost, seg_time = _weight_for_route(filtered_route, aircraft_cfg, criterion)
            if aircraft == "":
                continue

            new_dist = current_dist + weight
            if new_dist < dist.get(route.destination, float("inf")):
                dist[route.destination] = new_dist
                prev[route.destination] = (node, aircraft, route.distance_km, seg_cost, seg_time)
                heapq.heappush(queue, (new_dist, route.destination))

    if destination not in prev and destination != origin:
        return []

    path_segments: List[TravelSegment] = []
    current = destination
    while current != origin:
        p_node, aircraft, distance_km, seg_cost, seg_time = prev[current]
        path_segments.append(
            TravelSegment(
                origin=p_node,
                destination=current,
                aircraft=aircraft,
                distance_km=distance_km,
                segment_cost=seg_cost,
                segment_time_min=seg_time,
            )
        )
        current = p_node

    path_segments.reverse()
    return path_segments


def greedy_cover_route(
    graph: DirectedGraph,
    aircraft_cfg: Dict[str, AircraftConfig],
    origin: str,
    budget_limit: float,
    time_limit_min: float,
    optimize_for: str,
) -> List[TravelSegment]:
    # Heuristica simple: desde el nodo actual tomamos el vecino mas conveniente que no rompa limites.
    current = origin
    used: Set[str] = {origin}
    total_cost = 0.0
    total_time = 0.0
    segments: List[TravelSegment] = []

    while True:
        best_choice: Optional[Tuple[float, TravelSegment]] = None

        for route in graph.get_outgoing_routes(current):
            if route.blocked or route.destination in used:
                continue

            best_weight, aircraft, seg_cost, seg_time = _weight_for_route(route, aircraft_cfg, optimize_for)
            if aircraft == "":
                continue

            if total_cost + seg_cost > budget_limit:
                continue
            if total_time + seg_time > time_limit_min:
                continue

            segment = TravelSegment(
                origin=route.origin,
                destination=route.destination,
                aircraft=aircraft,
                distance_km=route.distance_km,
                segment_cost=seg_cost,
                segment_time_min=seg_time,
            )
            if best_choice is None or best_weight < best_choice[0]:
                best_choice = (best_weight, segment)

        if best_choice is None:
            break

        chosen = best_choice[1]
        segments.append(chosen)
        used.add(chosen.destination)
        current = chosen.destination
        total_cost += chosen.segment_cost
        total_time += chosen.segment_time_min

    return segments
