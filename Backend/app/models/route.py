from dataclasses import dataclass
from typing import List


@dataclass
class Route:
    origin: str
    destination: str
    distance_km: float
    aircraft_types: List[str]
    base_cost: float
    min_stay_min: int
    blocked: bool = False
