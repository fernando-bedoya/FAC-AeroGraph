"""
Graph algorithms for route optimization.

This module implements pathfinding algorithms for finding optimal routes
in the airline network graph. It includes Dijkstra's algorithm for finding
shortest paths based on different criteria (distance, time, cost).

Algorithms used:
- Dijkstra's Algorithm: Finds the shortest path from a source node to all
  other nodes in a weighted graph with non-negative edge weights.
  Time Complexity: O((V + E) log V) where V is vertices and E is edges
  Justification: Used because airline routes have non-negative weights
  (distance, time, cost) and we need optimal paths.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
import heapq

from .graph import Graph
from .models import AircraftConfig, TravelSegment


# Local structures for dijkstra_path (without external dependencies)
@dataclass(frozen=False)
class _LocalRoute:
    """Local structure representing an airline route without importing from models."""
    origin: str
    destination: str
    distance_km: float
    aircraft_types: List[str]
    base_cost: float
    min_stay_min: float
    blocked: bool


@dataclass
class _LocalTravelSegment:
    """Local structure representing a travel segment without importing from models."""
    origin: str
    destination: str
    aircraft: str
    distance_km: float
    segment_cost: float
    segment_time_min: float


def _weight_for_route(route: Any, aircraft_cfg: Dict[str, Any], criterion: str) -> Tuple[float, str, float, float]:
    """
    Calculate the weight of a route based on the optimization criterion.
    
    Selects the best aircraft type for the given criterion on this segment.
    
    Args:
        route: Route object with distance and aircraft types
        aircraft_cfg: Dictionary of aircraft configurations
        criterion: Optimization criterion ('distancia', 'tiempo', or 'costo')
        
    Returns:
        Tuple of (weight, best_aircraft, cost, time)
    """
    # Choose the best aircraft for the current criterion on this segment
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
    graph: Any,
    aircraft_cfg: Dict[str, Any],
    origin: str,
    destination: str,
    criterion: str,
    allowed_aircraft: Optional[Set[str]] = None,
    exclude_secondary: bool = False,
) -> List[_LocalTravelSegment]:
    """
    Find the optimal path between two airports using Dijkstra's algorithm.
    
    This implementation uses a priority queue (min-heap) to efficiently find
    the shortest path based on the specified criterion.
    
    Algorithm: Dijkstra's Shortest Path
    - Uses priority queue for O((V + E) log V) complexity
    - Handles multiple aircraft types per route
    - Supports filtering by aircraft type and airport type
    - Skips blocked routes
    
    Args:
        graph: Graph object representing the airline network
        aircraft_cfg: Dictionary mapping aircraft names to their configurations
        origin: Origin airport IATA code
        destination: Destination airport IATA code
        criterion: Optimization criterion ('distancia', 'tiempo', or 'costo')
        allowed_aircraft: Optional set of allowed aircraft types
        exclude_secondary: If True, exclude non-hub airports from path
        
    Returns:
        List of travel segments representing the optimal path, empty if no path exists
    """
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

            filtered_route = _LocalRoute(
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

    path_segments: List[_LocalTravelSegment] = []
    current = destination
    while current != origin:
        p_node, aircraft, distance_km, seg_cost, seg_time = prev[current]
        path_segments.append(
            _LocalTravelSegment(
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


def backtracking_max_coverage(
    graph: Graph,
    aircraft_cfg: Dict[str, AircraftConfig],
    origin: str,
    budget_limit: float,
    time_limit_min: float,
    optimize_for: str,
) -> List[TravelSegment]:
    """
    Algoritmo de Backtracking para encontrar la ruta que visite la MAYOR
    CANTIDAD de aeropuertos sin exceder presupuesto ni tiempo.

    LLAMADAS DESDE planner.py (algoritmo 2.2):
    - Punto a (presupuesto): optimize_for="costo"  → poda cuando costo > budget_limit
    - Punto b (tiempo):      optimize_for="tiempo" → poda cuando tiempo > time_limit_min
    El mismo algoritmo se invoca dos veces con distintos criterios.

    IDEA CENTRAL:
    Se exploran recursivamente todos los caminos posibles desde el origen.
    Cuando una rama viola la restricción activa (presupuesto o tiempo), se
    descarta inmediatamente (poda temprana) sin continuar por ese subárbol.

    CRITERIO DE SELECCIÓN DEL MEJOR CAMINO (prioridad triple):
    1. PRIMERO:   Máxima cantidad de aeropuertos visitados  (DESCENDENTE)
    2. SEGUNDO:   Máximo uso de tipos distintos de aeronaves (DESCENDENTE)
    3. DESEMPATE: Menor costo o tiempo acumulado            (ASCENDENTE)

    DIFERENCIA CON BELLMAN-FORD:
    - Bellman-Ford: relaja TODAS las aristas en iteraciones sucesivas (enfoque global).
    - Backtracking: explora UN camino a la vez y retrocede al violar restricciones.
    - Para cobertura máxima con restricciones, el backtracking es más natural
      ya que la poda temprana evita acumular estados inválidos desde el inicio.

    COMPLEJIDAD:
    - Peor caso: O(V!) donde V = número de aeropuertos
    - En la práctica, la poda por presupuesto/tiempo reduce drásticamente el espacio
      de búsqueda, haciendo el algoritmo eficiente para grafos con restricciones reales

    PARÁMETROS:
        graph: Grafo dirigido de rutas aéreas
        aircraft_cfg: Diccionario de configuración de aeronaves por tipo
        origin: Código IATA del aeropuerto de origen
        budget_limit: Presupuesto máximo en USD
        time_limit_min: Tiempo máximo disponible en minutos
        optimize_for: Criterio de prioridad ("costo" o "tiempo")

    RETORNA:
        Lista de TravelSegment que representa la ruta con máxima cobertura
    """
    # Estado mutable del mejor resultado encontrado durante toda la exploración.
    # Se usa un dict para poder modificarlo desde la función interna anidada.
    best: Dict[str, Any] = {
        "path": [],            # copia del mejor camino encontrado hasta ahora
        "visited_count": 0,    # cantidad de destinos visitados (sin el origen)
        "aircraft_count": 0,   # cantidad de tipos distintos de aeronave usados
        "priority": float("inf"),  # costo o tiempo acumulado (menor = mejor)
    }

    def _backtrack(
        current_node: str,
        visited: Set[str],
        path: List[TravelSegment],
        cost: float,
        time_min: float,
        aircraft_used: Set[str],
    ) -> None:
        """
        Función recursiva interna del backtracking.

        PASOS EN CADA LLAMADA:
        1. Evalúa si el camino actual supera al mejor conocido y lo guarda.
        2. Itera sobre todas las rutas salientes del nodo actual.
        3. Para cada ruta y aeronave válidos, calcula el costo/tiempo del segmento.
        4. PODA TEMPRANA: si el nuevo acumulado viola la restricción, descarta la rama.
        5. Si pasa la poda, agrega el segmento al camino y recursa al siguiente nodo.
        6. Al volver de la recursión, REVIERTE los cambios (backtrack) para explorar
           la siguiente alternativa desde el mismo punto.
        """
        # ── PASO 1: Actualizar el mejor resultado ───────────────────────────────
        # "destinations" = aeropuertos visitados excluyendo el origen
        destinations = len(visited) - 1
        current_priority = cost if optimize_for == "costo" else time_min

        # Solo consideramos un camino válido si tiene al menos un segmento recorrido
        if destinations > 0:
            is_better = (
                destinations > best["visited_count"]
                or (
                    destinations == best["visited_count"]
                    and len(aircraft_used) > best["aircraft_count"]
                )
                or (
                    destinations == best["visited_count"]
                    and len(aircraft_used) == best["aircraft_count"]
                    and current_priority < best["priority"]
                )
            )
            if is_better:
                best["path"] = path[:]   # snapshot del camino actual
                best["visited_count"] = destinations
                best["aircraft_count"] = len(aircraft_used)
                best["priority"] = current_priority

        # ── PASO 2: Expandir vecinos ────────────────────────────────────────────
        for route in graph.get_outgoing_routes(current_node):
            # Descartar rutas bloqueadas o destinos ya en el camino actual
            if route.blocked or route.destination in visited:
                continue

            # Probar cada tipo de aeronave disponible en esta ruta
            for aircraft in route.aircraft_types:
                if aircraft not in aircraft_cfg:
                    continue

                # ── PASO 3: Calcular costo y tiempo del segmento ────────────────
                cfg = aircraft_cfg[aircraft]
                seg_cost = route.distance_km * cfg.cost_per_km
                if route.base_cost == 0:
                    seg_cost = 0.0  # ruta subsidiada: costo cero
                seg_time = route.distance_km * cfg.time_per_km

                new_cost = cost + seg_cost
                new_time = time_min + seg_time

                # ── PASO 4: PODA TEMPRANA ────────────────────────────────────────
                # Si la restricción activa se viola, se abandona esta rama completa
                if optimize_for == "costo" and new_cost > budget_limit:
                    continue
                if optimize_for == "tiempo" and new_time > time_limit_min:
                    continue

                # ── PASO 5: Agregar segmento y recursar ──────────────────────────
                new_segment = TravelSegment(
                    origin=route.origin,
                    destination=route.destination,
                    aircraft=aircraft,
                    distance_km=route.distance_km,
                    segment_cost=seg_cost,
                    segment_time_min=seg_time,
                )
                path.append(new_segment)
                visited.add(route.destination)
                # Registrar si esta aeronave era nueva (para revertirla correctamente)
                aircraft_is_new = aircraft not in aircraft_used
                aircraft_used.add(aircraft)

                _backtrack(
                    current_node=route.destination,
                    visited=visited,
                    path=path,
                    cost=new_cost,
                    time_min=new_time,
                    aircraft_used=aircraft_used,
                )

                # ── PASO 6: BACKTRACK — revertir todos los cambios ───────────────
                path.pop()
                visited.discard(route.destination)
                if aircraft_is_new:
                    aircraft_used.discard(aircraft)

    # Llamada inicial: estamos en el origen, sin segmentos, sin costo ni tiempo
    _backtrack(
        current_node=origin,
        visited={origin},
        path=[],
        cost=0.0,
        time_min=0.0,
        aircraft_used=set(),
    )

    return best["path"]

