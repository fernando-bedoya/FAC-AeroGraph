"""
Optional activities management for dynamic planning (Requirement 2.3.a).

Travellers can choose from optional activities (tours, museums, etc.)
available at their current airport. Each activity consumes time and
budget; affordability is projected including mandatory events.
"""

from typing import Dict, List

from ..graph import Graph
from .core import DynamicPlanError, apply_cost_and_time, estimate_mandatory_costs, is_affordable
from .models import DynamicState


def list_dynamic_activities(
    graph: Graph,
    rules: Dict[str, float],
    state: DynamicState,
) -> List[Dict[str, float]]:
    """
    List optional activities available at the traveller's current airport.

    Each activity is annotated with an affordability flag that accounts
    for the activity's cost plus any mandatory food/lodging costs that
    would be triggered during its duration.

    Args:
        graph: The airline route graph.
        rules: System rules dict.
        state: Current dynamic session state.

    Returns:
        List of dicts with keys: name, kind, duration_min, cost_usd, affordable.
    """
    airport = graph.get_airport(state.current_airport)
    if not airport:
        return []

    items = []
    for activity in airport.activities:
        _, _, mandatory_cost = estimate_mandatory_costs(
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
                "affordable": is_affordable(
                    state,
                    activity.cost_usd + mandatory_cost,
                    activity.duration_min,
                ),
            }
        )
    return items


def choose_dynamic_activities(
    graph: Graph,
    rules: Dict[str, float],
    state: DynamicState,
    activity_names: List[str],
) -> DynamicState:
    """
    Apply a set of chosen optional activities to the session state.

    Validates each activity exists at the current airport, then applies
    cost and time via apply_cost_and_time(). Each activity increments
    the stay counter and may trigger mandatory food/lodging events.

    Args:
        graph: The airline route graph.
        rules: System rules dict.
        state: Current dynamic session state (mutated in-place).
        activity_names: List of activity names to perform.

    Returns:
        Updated DynamicState with costs deducted and steps logged.

    Raises:
        DynamicPlanError: If the airport or an activity is not found.
    """
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

        apply_cost_and_time(
            state,
            rules,
            cost_usd=activity.cost_usd,
            duration_min=activity.duration_min,
            cost_airport=airport,
            count_stay=True,
            action_label="actividad",
            detail=f"Actividad: {activity.name} ({activity.duration_min} min)",
            metadata={
                "name": activity.name,
                "kind": activity.kind,
                "duration": activity.duration_min,
                "cost": activity.cost_usd,
            },
        )

    return state
