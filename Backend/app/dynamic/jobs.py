"""
Temporary work management for dynamic planning (Requirement 2.3.b).

Travellers can take on temporary jobs at airports when their budget falls
below the eligibility threshold. Income is earned per hour worked, and
both time and mandatory events are tracked during work periods.
"""

from typing import Dict, List

from ..graph import Graph
from ..models import DynamicStep
from .core import DynamicPlanError, apply_mandatory_events, apply_time_only, can_work
from .models import DynamicState


def list_dynamic_jobs(
    graph: Graph,
    rules: Dict[str, float],
    state: DynamicState,
) -> List[Dict[str, float]]:
    """
    List available temporary jobs at the traveller's current airport.

    Jobs are only returned when the traveller's budget is below the
    work eligibility threshold (default: 35% of initial budget).

    Args:
        graph: The airline route graph.
        rules: System rules dict with budget_trigger_percent.
        state: Current dynamic session state.

    Returns:
        List of dicts with keys: name, hourly_rate, max_hours.
        Empty list if no jobs or budget is above threshold.
    """
    airport = graph.get_airport(state.current_airport)
    if not airport:
        return []

    if not can_work(state, rules):
        return []

    return [
        {
            "name": job.name,
            "hourly_rate": job.hourly_rate,
            "max_hours": job.max_hours,
        }
        for job in airport.jobs
    ]


def perform_dynamic_work(
    graph: Graph,
    rules: Dict[str, float],
    state: DynamicState,
    job_name: str,
    hours: int,
) -> DynamicState:
    """
    Perform a temporary work assignment at the current airport.

    Validates budget eligibility, job existence, and hour limits.
    Advances time without monetary cost, then credits the traveller's
    budget by hourly_rate * hours. Mandatory food/lodging events are
    applied for the work duration.

    Args:
        graph: The airline route graph.
        rules: System rules dict.
        state: Current dynamic session state (mutated in-place).
        job_name: Name of the job to perform.
        hours: Number of hours to work (must be <= job.max_hours).

    Returns:
        Updated DynamicState with income credited and time deducted.

    Raises:
        DynamicPlanError: If budget is not low enough, job not found,
            or hours exceed the maximum allowed.
    """
    airport = graph.get_airport(state.current_airport)
    if not airport:
        raise DynamicPlanError("Aeropuerto actual no existe")

    if not can_work(state, rules):
        raise DynamicPlanError("Presupuesto suficiente, no se habilita trabajo")

    job_map = {job.name: job for job in airport.jobs}
    job = job_map.get(job_name)
    if not job:
        raise DynamicPlanError("Trabajo no encontrado")

    if hours <= 0:
        raise DynamicPlanError("Horas invalidas")
    if hours > job.max_hours:
        raise DynamicPlanError("Horas exceden el maximo permitido")

    duration_min = hours * 60
    time_left_after_work, mandatory_events = apply_time_only(
        state,
        rules,
        duration_min=duration_min,
        cost_airport=airport,
        count_stay=True,
    )

    earned = job.hourly_rate * hours
    state.budget_usd += earned
    state.total_earned += earned
    state.steps.append(
        DynamicStep(
            airport_id=airport.id,
            action="trabajo",
            detail=f"Trabajo: {job.name} por {hours}h, ingreso {earned:.2f} USD",
            budget_after=state.budget_usd,
            time_left_min=time_left_after_work,
            metadata={
                "name": job.name,
                "hours": hours,
                "earned": earned,
            },
        )
    )
    apply_mandatory_events(state, airport, mandatory_events, time_left_after_work)
    return state
