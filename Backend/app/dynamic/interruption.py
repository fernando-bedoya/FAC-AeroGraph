"""
Route interruption service (Requirement 2.4).

Handles real-time route disruptions by blocking the affected edge,
detecting whether the traveller is currently mid-flight on that route,
redirecting them to the origin airport if so, and recalculating
alternative flight options and the suggested route.
"""

from typing import Dict, List, Optional

from ..graph import Graph
from ..models import AircraftConfig, DynamicStep
from .models import DynamicState
from .flights import list_dynamic_flight_options
from .routing import calculate_suggested_route


# ---------------------------------------------------------------------------
# Core interruption logic
# ---------------------------------------------------------------------------
# Lógica principal de interrupción
# ---------------------------------------------------------------------------

def _block_route(graph: Graph, origin: str, destination: str) -> bool:
    """
    Block a route in the graph by toggling its status.

    Args:
        graph: The airline route graph.
        origin: Origin airport IATA code of the route to block.
        destination: Destination airport IATA code.

    Returns:
        True if the route existed and was blocked, False if not found.
    """
    route = graph.toggle_route_status(origin, destination, block=True)
    return route is not None


def _is_traveler_on_blocked_route(
    state: DynamicState,
    origin: str,
    destination: str,
) -> bool:
    """
    Check whether the traveller is currently mid-flight on the blocked route.

    Compares the in-progress flight endpoints with the route being interrupted.

    Args:
        state: Current dynamic session state.
        origin: Origin of the route being blocked.
        destination: Destination of the route being blocked.

    Returns:
        True if the traveller is in transit on exactly this route.
    """
    if not state.in_transit:
        return False
    return state.transit_from == origin and state.transit_to == destination


def _redirect_to_origin(state: DynamicState) -> str:
    """
    Redirect the traveller back to the origin airport of the interrupted leg.

    Updates current_airport, clears transit state, and logs an emergency
    redirection step.

    Args:
        state: Current dynamic session state (mutated in-place).

    Returns:
        IATA code of the airport to which the traveller was redirected.
    """
    redirect_airport = state.transit_from
    blocked_destination = state.transit_to

    state.current_airport = redirect_airport

    state.steps.append(
        DynamicStep(
            airport_id=redirect_airport,
            action="redireccion_emergencia",
            detail=(
                f"Flight interrupted. Route {redirect_airport}→{blocked_destination} "
                f"blocked mid-transit. Traveller redirected to {redirect_airport}."
            ),
            budget_after=state.budget_usd,
            time_left_min=state.time_left_min,
            metadata={
                "redirected_from": blocked_destination,
                "redirected_to": redirect_airport,
            },
        )
    )

    state.clear_transit()

    return redirect_airport


def _record_block_event(
    state: DynamicState,
    origin: str,
    destination: str,
) -> None:
    """
    Log an informational step when a route is blocked but the traveller
    is not affected (not in transit on that route).

    Args:
        state: Current dynamic session state (mutated in-place).
        origin: Origin of the blocked route.
        destination: Destination of the blocked route.
    """
    state.steps.append(
        DynamicStep(
            airport_id=state.current_airport,
            action="ruta_bloqueada",
            detail=f"Route {origin}→{destination} blocked. Traveller was not affected.",
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
    Recalculate available flight options from the traveller's current position.

    Args:
        graph: The airline route graph.
        aircraft_cfg: Aircraft configuration dictionary.
        state: Current dynamic session state.

    Returns:
        List of flight option dicts.
    """
    return list_dynamic_flight_options(graph, aircraft_cfg, state)


def _recalculate_suggested_route(
    graph: Graph,
    aircraft_cfg: Dict[str, AircraftConfig],
    state: DynamicState,
) -> Dict:
    """
    Recalculate the optimal suggested route from the traveller's current position.

    Uses the remaining budget and time to generate a new suggested route
    that maximises destination coverage at minimum cost.

    Args:
        graph: The airline route graph.
        aircraft_cfg: Aircraft configuration dictionary.
        state: Current dynamic session state (mutated in-place).

    Returns:
        Suggested route dictionary with airports, segments, total_cost.
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
# Public orchestrator function
# ---------------------------------------------------------------------------

def handle_interruption(
    graph: Graph,
    aircraft_cfg: Dict[str, AircraftConfig],
    state: DynamicState,
    origin: str,
    destination: str,
) -> Dict:
    """
    Orchestrate the full route interruption workflow.

    Flow:
        1. Block the route in the graph.
        2. Detect whether the traveller is mid-flight on that route.
        3. If mid-flight: redirect to the leg's origin airport.
        4. Recalculate alternative flight options.
        5. Recalculate the optimal suggested route.

    Args:
        graph: The airline route graph.
        aircraft_cfg: Aircraft configuration dictionary.
        state: Current dynamic session state (mutated in-place).
        origin: Origin of the route to block.
        destination: Destination of the route to block.

    Returns:
        Dictionary with:
            - blocked_route: the route that was blocked
            - was_redirected: whether the traveller was redirected
            - redirected_to: airport redirected to (or None)
            - new_flight_options: flight options from current position
            - suggested_route: newly calculated suggested route

    Raises:
        ValueError: If the route to block does not exist in the graph.
    """
    route_blocked = _block_route(graph, origin, destination)
    if not route_blocked:
        raise ValueError(
            f"Route {origin}→{destination} not found for blocking."
        )

    was_redirected = False
    redirected_to = None

    if _is_traveler_on_blocked_route(state, origin, destination):
        redirected_to = _redirect_to_origin(state)
        was_redirected = True
    else:
        _record_block_event(state, origin, destination)

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
