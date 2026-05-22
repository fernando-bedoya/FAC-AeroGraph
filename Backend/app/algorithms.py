import heapq
from dataclasses import dataclass
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


@dataclass
class CoverageState:
    """
    Estado para el algoritmo Dijkstra de cobertura máxima.
    Representa un punto en la exploración de rutas aéreas.
    """
    priority: float  # costo acumulado o tiempo acumulado (según criterio)
    cost: float  # costo acumulado total en USD
    time: float  # tiempo acumulado total en minutos
    current_node: str  # código IATA del aeropuerto actual
    visited: frozenset  # conjunto inmutable de aeropuertos visitados
    aircraft_types: frozenset  # conjunto de tipos de aeronaves usadas (ej: {"Avion Comercial", "Helice"})
    path: List[TravelSegment]  # secuencia de vuelos realizados

    def __lt__(self, other: 'CoverageState') -> bool:
        """
        Comparación para heapq con PRIORIDAD TRIPLE:
        1. PRIMERO: Cantidad de destinos visitados (DESCENDENTE - más destinos primero)
        2. SEGUNDO: Uso de todos los tipos de transporte (DESCENDENTE - quien tenga los 3 primero)
        3. DESEMPATE: Costo/tiempo acumulado (ASCENDENTE - más barato/rápido primero)
        
        Esto asegura que Dijkstra expanda primero los estados con más destinos Y que hayan
        usado los 3 tipos de transporte obligatorios, garantizando máxima cobertura.
        """
        # 1. Si la cantidad de visitados es diferente, priorizar el que tiene MÁS destinos
        if len(self.visited) != len(other.visited):
            return len(self.visited) > len(other.visited)
        
        # 2. Si ambos tienen misma cantidad de destinos, priorizar quien tenga los 3 transportes
        self_has_all_aircraft = len(self.aircraft_types) == 3
        other_has_all_aircraft = len(other.aircraft_types) == 3
        if self_has_all_aircraft != other_has_all_aircraft:
            return self_has_all_aircraft  # True > False, así que quien tenga los 3 va primero
        
        # 3. Si hay empate en destinos y transportes, usar criterio de costo/tiempo
        return self.priority < other.priority


def dijkstra_max_coverage(
    graph: DirectedGraph,
    aircraft_cfg: Dict[str, AircraftConfig],
    origin: str,
    budget_limit: float,
    time_limit_min: float,
    optimize_for: str,
) -> List[TravelSegment]:
    """
    Algoritmo Dijkstra con estado extendido para encontrar la ruta que
    visite la MAYOR CANTIDAD de aeropuertos sin exceder presupuesto ni tiempo.

    JUSTIFICACIÓN DE DIJKSTRA SOBRE GREEDY:
    El algoritmo greedy toma decisiones locales óptimas que NO garantizan
    la solución global óptima. Puede elegir un destino cercano (bajo costo)
    que luego bloquea el acceso a múltiples destinos mejores.

    Dijkstra con estado extendido (conjunto de nodos visitados) explora
    TODAS las rutas posibles en orden de costo/tiempo creciente, garantizando
    encontrar la ruta con cobertura máxima dentro de las restricciones.
    Mediante poda de estados dominados, se reduce significativamente la
    complejidad exponencial en grafos reales.

    COMPLEJIDAD:
    - Peor caso: O((V · 2^V) · log(V · 2^V) + E · V)
    - Caso promedio con poda: mucho mejor, típicamente polinomial
    donde V = número de aeropuertos, E = número de rutas.

    PARÁMETROS:
        graph: Grafo dirigido de rutas aéreas
        aircraft_cfg: Diccionario de configuración de aeronaves por tipo
        origin: Código IATA del aeropuerto de origen
        budget_limit: Presupuesto máximo en USD
        time_limit_min: Tiempo máximo disponible en minutos
        optimize_for: Criterio de prioridad ("costo", "tiempo" o "distancia")

    RETORNA:
        Lista de TravelSegment que representa la ruta con máxima cobertura
    """

    # Estado inicial: en el origen, sin destinos visitados aún
    initial_visited = frozenset({origin})
    initial_state = CoverageState(
        priority=0.0,
        cost=0.0,
        time=0.0,
        current_node=origin,
        visited=initial_visited,
        aircraft_types=frozenset(),  # Sin aeronaves usadas aún
        path=[]
    )

    # Heap: estados ordenados por prioridad (cobertura → transportes → costo/tiempo)
    # Dijkstra siempre expande primero los estados que maximizan destinos y usan todos los transportes
    heap = [initial_state]

    # Tabla de poda: (current_node, visited_frozenset) -> min_priority visto
    # Evita re-expandir el mismo nodo con el mismo conjunto de visitados
    # si ya lo procesamos con costo/tiempo <= al actual
    processed = {}

    # Mejor resultado global: guardamos la ruta con máxima qty de nodos Y que use los 3 transportes
    best_result = []
    best_count = 1  # El origen cuenta como 1 nodo visitado
    best_has_all_aircraft = False  # ¿El mejor resultado tiene los 3 transportes?

    while heap:
        current_state = heapq.heappop(heap)

        # PODA: si ya procesamos este (nodo, visitados, tipos_transporte) con
        # prioridad <= actual, saltar. Ahora incluimos aircraft_types para permitir
        # explorar la misma cobertura con diferentes combinaciones de transporte
        state_key = (current_state.current_node, current_state.visited, current_state.aircraft_types)
        if state_key in processed:
            if processed[state_key] <= current_state.priority:
                continue
        processed[state_key] = current_state.priority

        # ACTUALIZAR MEJOR RESULTADO con prioridad doble:
        # 1. Primero: Máxima cantidad de destinos
        # 2. Segundo: Que use los 3 tipos de transporte
        visited_count = len(current_state.visited)
        current_has_all_aircraft = len(current_state.aircraft_types) == 3
        
        # Actualizar si: más destinos O (mismos destinos pero ahora tiene los 3 transportes)
        if visited_count > best_count or (visited_count == best_count and current_has_all_aircraft and not best_has_all_aircraft):
            best_count = visited_count
            best_result = current_state.path
            best_has_all_aircraft = current_has_all_aircraft

        # EXPLORAR VECINOS: procesar todas las rutas salientes del nodo actual
        for route in graph.get_outgoing_routes(current_state.current_node):
            # Descartamos: ruta bloqueada O destino ya visitado
            if route.blocked or route.destination in current_state.visited:
                continue

            # IMPORTANTE: Iterar sobre TODAS las aeronaves disponibles en esta ruta
            # para explorar diferentes combinaciones de transporte
            for aircraft in route.aircraft_types:
                if aircraft not in aircraft_cfg:
                    continue
                
                # Calcular costo y tiempo para esta aeronave específica
                aircraft_config = aircraft_cfg[aircraft]
                seg_cost = (route.distance_km * aircraft_config.cost_per_km) + route.base_cost
                seg_time = route.distance_km * aircraft_config.time_per_km

                # RESTRICCIÓN DURA: Según criterio de optimización
                # 2.2.a (costo): Solo válido si NO se excede presupuesto
                # 2.2.b (tiempo): Solo válido si NO se excede tiempo límite
                new_cost = current_state.cost + seg_cost
                new_time = current_state.time + seg_time

                if optimize_for == "costo":
                    # Ruta por presupuesto: solo aplica límite de costo
                    if new_cost > budget_limit:
                        continue
                else:  # optimize_for == "tiempo"
                    # Ruta por tiempo: solo aplica límite de tiempo
                    if new_time > time_limit_min:
                        continue

                # Crear segmento de viaje
                new_segment = TravelSegment(
                    origin=route.origin,
                    destination=route.destination,
                    aircraft=aircraft,
                    distance_km=route.distance_km,
                    segment_cost=seg_cost,
                    segment_time_min=seg_time,
                )

                # Nuevo conjunto de visitados (incluye destino actual)
                new_visited = current_state.visited | frozenset({route.destination})
                
                # Nuevo conjunto de aeronaves usadas (agregar esta aeronave)
                new_aircraft_types = current_state.aircraft_types | frozenset({aircraft})

                # Calcular prioridad según criterio de optimización
                # Esto es lo que determina el orden de expansión de Dijkstra
                if optimize_for == "tiempo":
                    new_priority = new_time
                else:  # "costo" o "distancia"
                    new_priority = new_cost

                # Crear nuevo estado y agregar al heap
                new_state = CoverageState(
                    priority=new_priority,
                    cost=new_cost,
                    time=new_time,
                    current_node=route.destination,
                    visited=new_visited,
                    aircraft_types=new_aircraft_types,  # ← Incluir los tipos de aeronaves usadas
                    path=current_state.path + [new_segment]
                )

                heapq.heappush(heap, new_state)

    return best_result

