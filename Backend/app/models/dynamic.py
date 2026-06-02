from dataclasses import dataclass
from typing import List


@dataclass
class DynamicStep:
    airport_id: str
    action: str
    detail: str
    budget_after: float
    time_left_min: float


@dataclass
class DynamicPlan:
    steps: List[DynamicStep]
    visited_airports: List[str]
    total_spent: float
    total_earned: float
    final_budget: float
