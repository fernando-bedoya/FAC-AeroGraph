"""
Dynamic Planning Session Models (Requirement 2.3)

This module defines the models used for interactive dynamic planning sessions.
Dynamic planning allows travelers to make decisions step by step:
- Choose activities at each airport
- Take temporary jobs to earn money
- Fly to new destinations
- Handle route interruptions

DYNAMIC STEP:
    Every action taken during a session is recorded as a DynamicStep.
    This creates an audit trail for the final report.
    
    Action types:
    - "vuelo": Flight to a new airport
    - "actividad": Optional tourist activity
    - "trabajo": Temporary work
    - "alimentacion": Mandatory meal
    - "alojamiento": Mandatory lodging
    - "tiempo_libre": Waiting for minimum stay
    - "ruta_bloqueada": Route blocked (informational)
    - "redireccion_emergencia": Emergency redirection

DYNAMIC PLAN:
    Aggregated summary of a completed session.
    Used for generating the final report (R2.5).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class DynamicStep:
    """
    A single recorded action taken during a dynamic planning session.
    
    Every action the traveler takes is logged as a DynamicStep.
    This creates a complete history of the trip for:
    1. Displaying the trip history in the UI
    2. Generating the final report
    3. Debugging and auditing
    
    Attributes:
        airport_id: IATA code of the airport where the action occurred
                    Example: "BOG"
        action: Type of action performed
                Valid values: "vuelo", "actividad", "trabajo", 
                             "alimentacion", "alojamiento", "tiempo_libre",
                             "ruta_bloqueada", "redireccion_emergencia"
        detail: Human-readable description of the action
                Example: "Flight BOG->MDE in Avion Comercial, cost $38.70"
        budget_after: Remaining budget in USD after this action
                      Shows the financial impact of the action
        time_left_min: Remaining time in minutes after this action
                       Shows the time impact of the action
        metadata: Additional structured data specific to the action type
                  For flights: {"origin": "BOG", "destination": "MDE", 
                               "aircraft": "Avion Comercial", "distance_km": 215,
                               "duration": 150, "cost": 38.70}
                  For activities: {"name": "City Tour", "kind": "tour",
                                  "duration": 120, "cost": 25.0}
                  For work: {"name": "Baggage Handler", "hours": 4, "earned": 36.0}
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
    
    This provides a summary view of the entire trip, useful for
    generating the final report (R2.5).
    
    Attributes:
        steps: Complete list of DynamicStep entries recorded during the session
               This is the full audit trail of all actions taken
        visited_airports: IATA codes of all airports visited in order
                         Example: ["BOG", "MDE", "CLO", "UIO"]
        total_spent: Total amount spent in USD across all actions
                     Includes flights, activities, food, lodging
        total_earned: Total amount earned from work in USD
                     This offsets the total_spent
        final_budget: Remaining budget in USD at session end
                     Calculated as: initial_budget - total_spent + total_earned
    """
    steps: List[DynamicStep]
    visited_airports: List[str]
    total_spent: float
    total_earned: float
    final_budget: float
