from dataclasses import dataclass
from typing import List


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
