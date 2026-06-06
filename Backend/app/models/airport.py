from dataclasses import dataclass, field
from typing import List


@dataclass
class Activity:
    name: str
    kind: str
    duration_min: int
    cost_usd: float


@dataclass
class Job:
    name: str
    hourly_rate: float
    max_hours: int


@dataclass
class Airport:
    id: str
    name: str
    city: str
    country: str
    timezone: str
    is_hub: bool
    lodging_cost: float
    food_cost: float
    lat: float = 0.0
    lon: float = 0.0
    activities: List[Activity] = field(default_factory=list)
    jobs: List[Job] = field(default_factory=list)
