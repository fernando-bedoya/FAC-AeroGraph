"""
Airport models for the airline route graph.

Defines the core entities: airports (nodes), optional tourist activities,
and temporary job offerings available at each destination.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Activity:
    """
    An optional activity available at an airport destination.

    Activities include tours, museum visits, cultural experiences, etc.
    Each activity has a time cost (duration) and a monetary cost.

    Attributes:
        name: Display name of the activity.
        kind: Type/category (e.g. "tour", "museum", "cultural").
        duration_min: Duration of the activity in minutes.
        cost_usd: Cost of the activity in USD.
    """

    name: str
    kind: str
    duration_min: int
    cost_usd: float


@dataclass
class Job:
    """
    A temporary work offering available at an airport.

    Travellers can take jobs when their budget falls below a threshold.
    Income is calculated as hourly_rate * hours_worked.

    Attributes:
        name: Job title (e.g. "Baggage Handler", "Ramp Assistant").
        hourly_rate: Pay rate in USD per hour.
        max_hours: Maximum hours the traveller can work at this job.
    """

    name: str
    hourly_rate: float
    max_hours: int


@dataclass
class Airport:
    """
    An airport node in the airline route graph.

    Represents a city airport with its geographic location, associated costs,
    available activities, and temporary job listings.

    Attributes:
        id: Three-letter IATA code (e.g. "BOG", "MDE", "LIM").
        name: Full airport name.
        city: City where the airport is located.
        country: Country of the airport.
        timezone: Timezone string (e.g. "America/Bogota").
        is_hub: Whether this airport is a major hub.
        lodging_cost: Cost per night for mandatory lodging in USD.
        food_cost: Cost per meal for mandatory food in USD.
        lat: Latitude coordinate for map rendering.
        lon: Longitude coordinate for map rendering.
        activities: List of optional activities available at this airport.
        jobs: List of temporary job offerings at this airport.
    """

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
