from dataclasses import dataclass, field
from typing import List, Dict, Any

from ..models import DynamicStep


@dataclass
class DynamicState:
    session_id: str
    origin: str
    current_airport: str
    initial_budget: float
    budget_usd: float
    time_left_min: float
    total_spent: float
    total_earned: float
    visited: List[str] = field(default_factory=list)
    steps: List[DynamicStep] = field(default_factory=list)
    minutes_since_lodging: float = 0.0
    minutes_since_food: float = 0.0
    stay_min: float = 0.0
    required_stay_min: float = 0.0
    total_distance_km: float = 0.0
    free_distance_km: float = 0.0
    suggested_route: Dict[str, Any] = field(default_factory=dict)  # Ruta óptima sugerida: {airports, total_cost, total_time_min}
