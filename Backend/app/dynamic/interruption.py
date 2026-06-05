"""
Servicio de Interrupción de Vuelos (R2.4)

Responsabilidad única: gestionar interrupciones de rutas aéreas durante
el tiempo de ejecución, incluyendo bloqueo, redirección del viajero
y recalculación de alternativas.
"""

from typing import Dict, List, Optional

from ..graph import Graph
from ..models import AircraftConfig, DynamicStep
from .models import DynamicState
from .flights import list_dynamic_flight_options
from .routing import calculate_suggested_route




# ---------------------------------------------------------------------------
# Lógica principal de interrupción
# ---------------------------------------------------------------------------

def _block_route(graph: Graph, origin: str, destination: str) -> bool:
    """
    Bloquea una ruta en el grafo.

    Retorna True si la ruta existía y fue bloqueada, False si no se encontró.
    """
    route = graph.toggle_route_status(origin, destination, block=True)
    return route is not None


def _is_traveler_on_blocked_route(
    state: DynamicState,
    origin: str,
    destination: str,
) -> bool:
    """
    Determina si el viajero está actualmente en tránsito en la ruta bloqueada.

    Compara los extremos del tramo actual con los de la ruta que se
    está interrumpiendo.
    """
    if not state.in_transit:
        return False
    return state.transit_from == origin and state.transit_to == destination


def _redirect_to_origin(state: DynamicState) -> str:
    """
    Redirige al viajero al aeropuerto de origen del tramo interrumpido.

    Actualiza current_airport al punto de partida del vuelo y limpia
    el estado de tránsito. Registra un DynamicStep de emergencia.

    Retorna el aeropuerto al que fue redirigido.
    """
    redirect_airport = state.transit_from
    blocked_destination = state.transit_to

    # Redirigir al aeropuerto de origen del tramo
    state.current_airport = redirect_airport

    # Registrar paso de redirección de emergencia
    state.steps.append(
        DynamicStep(
            airport_id=redirect_airport,
            action="redireccion_emergencia",
            detail=(
                f"Vuelo interrumpido. Ruta {redirect_airport}→{blocked_destination} "
                f"bloqueada en tránsito. Viajero redirigido a {redirect_airport}."
            ),
            budget_after=state.budget_usd,
            time_left_min=state.time_left_min,
            metadata={
                "redirected_from": blocked_destination,
                "redirected_to": redirect_airport,
            },
        )
    )

    # Limpiar estado de tránsito
    state.clear_transit()

    return redirect_airport


def _record_block_event(
    state: DynamicState,
    origin: str,
    destination: str,
) -> None:
    """
    Registra un paso informativo cuando se bloquea una ruta que no afecta
    al viajero directamente (no está en tránsito en esa ruta).
    """
    state.steps.append(
        DynamicStep(
            airport_id=state.current_airport,
            action="ruta_bloqueada",
            detail=f"Ruta {origin}→{destination} bloqueada. El viajero no fue afectado.",
            budget_after=state.budget_usd,
            time_left_min=state.time_left_min,
            metadata={
                "blocked_origin": origin,
                "blocked_destination": destination,
            },
        )
    )


def _recalculate_flight_options(
    graph: Graph,
    aircraft_cfg: Dict[str, AircraftConfig],
    state: DynamicState,
) -> List[Dict]:
    """
    Calcula las opciones de vuelo disponibles desde la posición actual.
    """
    return list_dynamic_flight_options(graph, aircraft_cfg, state)


def _recalculate_suggested_route(
    graph: Graph,
    aircraft_cfg: Dict[str, AircraftConfig],
    state: DynamicState,
) -> Dict:
    """
    Recalcula la ruta sugerida óptima desde la posición actual del viajero.

    Utiliza el presupuesto y tiempo restantes para generar una nueva
    ruta sugerida que maximice destinos con el menor gasto.
    """
    new_suggested = calculate_suggested_route(
        graph=graph,
        aircraft_cfg=aircraft_cfg,
        origin=state.current_airport,
        initial_budget=state.budget_usd,
        total_time_min=state.time_left_min,
    )

    state.suggested_route = new_suggested
    return new_suggested


# ---------------------------------------------------------------------------
# Función orquestadora (punto de entrada público)
# ---------------------------------------------------------------------------

def handle_interruption(
    graph: Graph,
    aircraft_cfg: Dict[str, AircraftConfig],
    state: DynamicState,
    origin: str,
    destination: str,
) -> Dict:
    """
    Orquesta toda la lógica de una interrupción de ruta.

    Flujo:
        1. Bloquea la ruta en el grafo
        2. Detecta si el viajero está en tránsito en esa ruta
        3. Si está en tránsito: redirige al aeropuerto de origen del tramo
        4. Recalcula opciones de vuelo alternativas
        5. Recalcula la ruta sugerida óptima

    Args:
        graph: Grafo de rutas aéreas.
        aircraft_cfg: Configuración de aeronaves por tipo.
        state: Estado dinámico de la sesión del viajero.
        origin: Origen de la ruta a bloquear.
        destination: Destino de la ruta a bloquear.

    Returns:
        Diccionario con:
            - blocked_route: la ruta que fue bloqueada
            - was_redirected: si el viajero fue redirigido
            - redirected_to: aeropuerto al que fue redirigido (o None)
            - new_flight_options: opciones de vuelo desde posición actual
            - suggested_route: nueva ruta sugerida recalculada
            - state: estado actualizado del viajero

    Raises:
        ValueError: Si la ruta a bloquear no existe en el grafo.
    """
    # 1. Bloquear la ruta
    route_blocked = _block_route(graph, origin, destination)
    if not route_blocked:
        raise ValueError(
            f"No se encontró la ruta {origin}→{destination} para bloquear."
        )

    # 2. Detectar y manejar redirección
    was_redirected = False
    redirected_to = None

    if _is_traveler_on_blocked_route(state, origin, destination):
        redirected_to = _redirect_to_origin(state)
        was_redirected = True
    else:
        _record_block_event(state, origin, destination)

    # 3. Recalcular alternativas
    new_flight_options = _recalculate_flight_options(
        graph, aircraft_cfg, state
    )
    new_suggested_route = _recalculate_suggested_route(
        graph, aircraft_cfg, state
    )

    return {
        "blocked_route": {"from": origin, "to": destination},
        "was_redirected": was_redirected,
        "redirected_to": redirected_to,
        "new_flight_options": new_flight_options,
        "suggested_route": new_suggested_route,
    }
