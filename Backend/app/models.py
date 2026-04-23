from dataclasses import dataclass, field
from typing import Dict, List


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
    activities: List[Activity] = field(default_factory=list)
    jobs: List[Job] = field(default_factory=list)


@dataclass
class AircraftConfig:
    name: str
    cost_per_km: float
    time_per_km: float


@dataclass
class Route:
    origin: str
    destination: str
    distance_km: float
    aircraft_types: List[str]
    base_cost: float
    min_stay_min: int
    blocked: bool = False


@dataclass
class TravelSegment:
    origin: str
    destination: str
    aircraft: str
    distance_km: float
    segment_cost: float
    segment_time_min: float


@dataclass
class TravelPlan:
    title: str
    visited_airports: List[str]
    segments: List[TravelSegment]
    total_cost: float
    total_time_min: float


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


DEFAULT_AIRCRAFT: Dict[str, AircraftConfig] = {
    "Avion Comercial": AircraftConfig("Avion Comercial", 0.18, 0.7),
    "Avion Regional": AircraftConfig("Avion Regional", 0.25, 1.1),
    "Helice": AircraftConfig("Helice", 0.12, 2.5),
}
