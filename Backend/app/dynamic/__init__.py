"""
Dynamic Planning Package (Requirement 2.3 and 2.4)

This package implements the interactive dynamic planning system that allows
travelers to make decisions step by step during their trip.

PACKAGE STRUCTURE:
    - models.py: DynamicState class (session state)
    - core.py: Core engine (validation, time advancement, cost calculation)
    - session.py: Session lifecycle (start, get, end)
    - activities.py: Optional activities (tours, museums)
    - jobs.py: Temporary work system
    - flights.py: Flight operations (list options, fly, start/arrive)
    - routing.py: Suggested route calculation
    - interruption.py: Route interruption handling (R2.4)
    - report.py: Final report generation (R2.5)

DYNAMIC PLANNING FLOW:
    1. Start session with origin, budget, and time
    2. At each airport, traveler can:
       - Do optional activities (costs money and time)
       - Take temporary work (earns money, costs time)
       - Fly to a new destination (costs money and time)
    3. Mandatory events (food, lodging) are applied automatically
    4. Route interruptions can occur (R2.4)
    5. End session and generate final report (R2.5)

KEY FEATURES:
    - Budget and time tracking
    - Mandatory food/lodging events
    - 20% subsidized route cap
    - Work eligibility when budget is low
    - Route interruption handling
    - Suggested route calculation
    - Final report generation
"""

from .activities import choose_dynamic_activities, list_dynamic_activities
from .core import DynamicPlanError
from .flights import (
    complete_dynamic_flight,
    list_dynamic_flight_options,
    perform_dynamic_flight,
    start_dynamic_flight,
)
from .interruption import handle_interruption
from .jobs import list_dynamic_jobs, perform_dynamic_work
from .report import generate_final_report, export_report_format
from .routing import calculate_suggested_route
from .session import end_dynamic_session, get_dynamic_state, start_dynamic_session

# Export all public functions and classes
# This allows importing directly from app.dynamic:
#   from app.dynamic import start_dynamic_session, DynamicPlanError
__all__ = [
    "DynamicPlanError",
    "calculate_suggested_route",
    "choose_dynamic_activities",
    "complete_dynamic_flight",
    "end_dynamic_session",
    "export_report_format",
    "generate_final_report",
    "get_dynamic_state",
    "list_dynamic_activities",
    "list_dynamic_flight_options",
    "list_dynamic_jobs",
    "perform_dynamic_flight",
    "perform_dynamic_work",
    "start_dynamic_flight",
    "start_dynamic_session",
    "handle_interruption",
]
