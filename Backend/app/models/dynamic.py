"""
Data models for the dynamic planning session (Requirement 2.3).

These dataclasses represent the step-by-step log entries and aggregate
plan results produced during an interactive dynamic planning session.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class DynamicStep:
    """
    A single recorded action taken during a dynamic planning session.

    Every traveller action (flight, activity, work, mandatory event, etc.)
    is logged as a DynamicStep to enable step-by-step tracking and final
    report generation.

    Attributes:
        airport_id: IATA code of the airport where the action occurred.
        action: Type of action (e.g. "vuelo", "actividad", "trabajo", "alimentacion", "alojamiento").
        detail: Human-readable description of the action.
        budget_after: Remaining budget in USD after this action was applied.
        time_left_min: Remaining time in minutes after this action was applied.
        metadata: Additional structured data (cost, duration, origin, destination, etc.).
    """

    airport_id: str
    action: str
    detail: str
    budget_after: float
    time_left_min: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DynamicPlan:
    """
    Aggregated result of a completed dynamic planning session.

    Provides a summary view of all steps taken, airports visited, and
    the final financial state of the traveller.

    Attributes:
        steps: Complete list of DynamicStep entries recorded during the session.
        visited_airports: IATA codes of all airports visited in order.
        total_spent: Total amount spent in USD across all actions.
        total_earned: Total amount earned from work in USD.
        final_budget: Remaining budget in USD at session end.
    """

    steps: List[DynamicStep]
    visited_airports: List[str]
    total_spent: float
    total_earned: float
    final_budget: float
