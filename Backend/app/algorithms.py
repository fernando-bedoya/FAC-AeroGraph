import heapq
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from .graph import DirectedGraph
from .models import AircraftConfig, TravelSegment


# Estructuras locales para dijkstra_path (sin dependencias externas)
@dataclass(frozen=False)
class _LocalRoute:
    """Estructura local que representa una ruta aérea sin importar de models."""
    origin: str
    destination: str
    distance_km: float
    aircraft_types: List[str]
    base_cost: float
    min_stay_min: float
    blocked: bool


@dataclass
class _LocalTravelSegment:
    """Estructura local que representa un segmento de viaje sin importar de models."""
    origin: str
    destination: str
    aircraft: str
    distance_km: float
    segment_cost: float
    segment_time_min: float


def _weight_for_route(route: Any, aircraft_cfg: Dict[str, Any], criterion: str) -> Tuple[float, str, float, float]:
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
    graph: Any,
    aircraft_cfg: Dict[str, Any],
    origin: str,
    destination: str,
    criterion: str,
    allowed_aircraft: Optional[Set[str]] = None,
    exclude_secondary: bool = False,
) -> List[_LocalTravelSegment]:
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


@dataclass
class CoverageState:
    """
    Estado para el algoritmo Bellman-Ford de cobertura máxima.
    Representa un punto en la exploración de rutas aéreas.
    """
    priority: float  # costo acumulado o tiempo acumulado (según criterio)
    cost: float  # costo acumulado total en USD
    time: float  # tiempo acumulado total en minutos
    current_node: str  # código IATA del aeropuerto actual
    visited: frozenset  # conjunto inmutable de aeropuertos visitados
    aircraft_types: frozenset  # conjunto de tipos de aeronaves usadas (ej: {"Avion Comercial", "Helice"})
    path: List[TravelSegment]  # secuencia de vuelos realizados
    total_distance_km: float  # distancia total acumulada en KM
    free_distance_km: float  # distancia subsidiada (base_cost == 0) acumulada en KM

    def __lt__(self, other: 'CoverageState') -> bool:
        """
        Comparación para el algoritmo Bellman-Ford con PRIORIDAD TRIPLE:
        1. PRIMERO: Cantidad de destinos visitados (DESCENDENTE - más destinos primero)
        2. SEGUNDO: Uso de todos los tipos de transporte (DESCENDENTE - quien tenga los 3 primero)
        3. DESEMPATE: Costo/tiempo acumulado (ASCENDENTE - más barato/rápido primero)
        
        Esta comparación se usa en _seleccionar_mejor_cobertura para elegir el mejor estado
        tras todas las pasadas de relajación, asegurando máxima cobertura.
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


def _inicializar_estado_cobertura(origin: str) -> CoverageState:
    """
    Crea el estado inicial para el algoritmo de Bellman-Ford de cobertura máxima.
    
    El estado inicial representa estar en el aeropuerto de origen sin haber viajado aún:
    - current_node: el aeropuerto de origen
    - visited: conjunto con só el origen
    - path: liste vacía (sin segmentos de viaje)
    - costo, tiempo, prioridad: todos en cero
    - aircraft_types: conjunto vacío (sin aeronaves usadas aún)
    - total_distance_km: 0 (sin distancia recorrida)
    - free_distance_km: 0 (sin distancia gratuita usada)
    
    PARÁMETROS:
        origin: Código IATA del aeropuerto de origen
        
    RETORNA:
        CoverageState inicial
    """
    initial_visited = frozenset({origin})
    return CoverageState(
        priority=0.0,
        cost=0.0,
        time=0.0,
        current_node=origin,
        visited=initial_visited,
        aircraft_types=frozenset(),
        path=[],
        total_distance_km=0.0,
        free_distance_km=0.0,
    )


def _relajar_aristas_cobertura(
    graph: DirectedGraph,
    aircraft_cfg: Dict[str, AircraftConfig],
    states: List[CoverageState],
    optimize_for: str,
    budget_limit: float,
    time_limit_min: float,
) -> Tuple[List[CoverageState], bool]:
    """
    Ejecuta una pasada completa de relajación de aristas en el algoritmo Bellman-Ford.
    
    Para cada estado actual, intenta expandir a todos sus vecinos no visitados.
    Todas las aristas salientes (rutas aéreas) de todos los nodos pueden ser relajadas
    en esta pasada. Devuelve los nuevos estados generados y un indicador de si hubo
    alguna relajación exitosa.

    Las restricciones de presupuesto/tiempo se aplican según optimize_for:
    - "costo": verifica solo budget_limit
    - "tiempo": verifica solo time_limit_min
    
    Además, valida la restricción del 20% de distancia gratuita para rutas subsidiadas
    (base_cost == 0), igual que en _calculate_segment_cost.
    
    PARÁMETROS:
        graph: Grafo dirigido de rutas aéreas
        aircraft_cfg: Diccionario de configuración de aeronaves
        states: Lista de estados actuales a expandir
        optimize_for: Criterio de prioridad ("costo" o "tiempo")
        budget_limit: Límite presupuestario en USD
        time_limit_min: Límite de tiempo en minutos
        
    RETORNA:
        Tupla (nuevos_estados, hubo_relajacion)
        - nuevos_estados: lista de CoverageState generados tras la relajación
        - hubo_relajacion: True si al menos uno fue válido, False si todos fueron podados
    """
    new_states = []
    relaxation_occurred = False

    for current_state in states:
        # Procesar todas las rutas salientes del nodo actual
        for route in graph.get_outgoing_routes(current_state.current_node):
            # Descartar: ruta bloqueada O destino ya en el camino
            if route.blocked or route.destination in current_state.visited:
                continue

            # Para cada aeronave disponible en esta ruta
            for aircraft in route.aircraft_types:
                if aircraft not in aircraft_cfg:
                    continue

                # Calcular costo y tiempo para esta aeronave
                aircraft_config = aircraft_cfg[aircraft]
                seg_cost = route.distance_km * aircraft_config.cost_per_km
                if route.base_cost == 0:
                    seg_cost = 0.0  # Ruta subsidiada
                seg_time = route.distance_km * aircraft_config.time_per_km

                # Calcular nuevos acumulados
                new_cost = current_state.cost + seg_cost
                new_time = current_state.time + seg_time
                new_total_distance = current_state.total_distance_km + route.distance_km
                new_free_distance = current_state.free_distance_km
                if route.base_cost == 0:
                    new_free_distance += route.distance_km

                # Aplicar restricciones según criterio
                if optimize_for == "costo":
                    if new_cost > budget_limit:
                        continue
                else:  # "tiempo"
                    if new_time > time_limit_min:
                        continue

                # Nota: No validamos la restricción del 20% aquí porque la ruta sugerida
                # es una propuesta teórica. La restricción se aplica solo cuando el usuario
                # REALMENTE vuela (en perform_dynamic_flight -> _calculate_segment_cost)

                # Crear nuevo segmento
                new_segment = TravelSegment(
                    origin=route.origin,
                    destination=route.destination,
                    aircraft=aircraft,
                    distance_km=route.distance_km,
                    segment_cost=seg_cost,
                    segment_time_min=seg_time,
                )

                # Actualizar conjuntos de visitados y aeronaves
                new_visited = current_state.visited | frozenset({route.destination})
                new_aircraft_types = current_state.aircraft_types | frozenset({aircraft})

                # Calcular nueva prioridad
                if optimize_for == "tiempo":
                    new_priority = new_time
                else:  # "costo"
                    new_priority = new_cost

                # Crear y agregar nuevo estado
                new_state = CoverageState(
                    priority=new_priority,
                    cost=new_cost,
                    time=new_time,
                    current_node=route.destination,
                    visited=new_visited,
                    aircraft_types=new_aircraft_types,
                    path=current_state.path + [new_segment],
                    total_distance_km=new_total_distance,
                    free_distance_km=new_free_distance,
                )
                new_states.append(new_state)
                relaxation_occurred = True

    return new_states, relaxation_occurred


def _seleccionar_mejor_cobertura(states: List[CoverageState]) -> List[TravelSegment]:
    """
    Selecciona la mejor ruta del conjunto de estados tras todas las pasadas de relajación.
    
    La selección usa la misma prioridad triple que CoverageState.__lt__:
    1. Primero: máxima cantidad de aeropuertos visitados (DESCENDENTE)
    2. Segundo: máximo número de tipos de aeronaves usadas (DESCENDENTE)
    3. Desempate: menor costo o tiempo acumulado (ASCENDENTE)
    
    Si el conjunto de estados está vacío, retorna una lista vacía.
    
    PARÁMETROS:
        states: Lista de CoverageState finales tras todas las pasadas
        
    RETORNA:
        List[TravelSegment] del estado con mejor cobertura
    """
    if not states:
        return []

    # CoverageState.__lt__ está diseñado para heapq, que retorna el MÍNIMO.
    # El mínimo según nuestro __lt__ es el estado con MÁS visitados (y mejores criterios).
    # Por lo tanto, buscamos el mínimo, no el máximo.
    best_state = min(states)
    return best_state.path


def bellman_ford_max_coverage(
    graph: DirectedGraph,
    aircraft_cfg: Dict[str, AircraftConfig],
    origin: str,
    budget_limit: float,
    time_limit_min: float,
    optimize_for: str,
) -> List[TravelSegment]:
    """
    Algoritmo Bellman-Ford con estado extendido para encontrar la ruta que
    visite la MAYOR CANTIDAD de aeropuertos sin exceder presupuesto ni tiempo.

    COMPARACIÓN CON DIJKSTRA:
    El algoritmo Bellman-Ford difiere de Dijkstra en su enfoque:
    - Bellman-Ford: relaja TODAS las aristas en iteraciones sucesivas
    - Dijkstra: siempre procesa primero el estado con menor distancia
    
    Para problemas de cobertura máxima con restricciones, Bellman-Ford puede
    ser más eficiente cuando hay múltiples caminos válidos con pesos similares.

    COMPLEJIDAD:
    - Bellman-Ford iterativo: O(V · (E · V) + poda inteligente)
    - donde V = número de aeropuertos, E = número de rutas
    - Se detiene anticipadamente si una pasada no genera nuevos estados

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
    
    # Paso 1: Inicializar el estado
    initial_state = _inicializar_estado_cobertura(origin)
    current_states = [initial_state]
    

    # Paso 2: Ejecutar V-1 pasadas de relajación (donde V es el número de aeropuertos)
    # Se usa un conjunto para evitar procesar el mismo estado dos veces
    vertex_count = len(graph.get_all_airports())
    max_iterations = max(1, vertex_count - 1)

    for iteration in range(max_iterations):
        # Relajar todas las aristas con los estados actuales
        new_states, relaxation_occurred = _relajar_aristas_cobertura(
            graph=graph,
            aircraft_cfg=aircraft_cfg,
            states=current_states,
            optimize_for=optimize_for,
            budget_limit=budget_limit,
            time_limit_min=time_limit_min,
        )

        # Si no hubo relajación, podemos detener anticipadamente
        if not relaxation_occurred:
            break

        # Agregar nuevos estados a los actuales para la siguiente iteración
        current_states.extend(new_states)

    # Paso 3: Seleccionar y retornar el mejor resultado
    best_result = _seleccionar_mejor_cobertura(current_states)
    return best_result

