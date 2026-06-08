"""
Airport Models - Graph Nodes

This module defines the core entities that represent airports (nodes)
in the airline route graph:

1. Airport: The main node representing a city airport
2. Activity: Optional tourist activities available at an airport
3. Job: Temporary work offerings available at an airport

RELATIONSHIP TO GRAPH:
    Airports are the NODES of the graph. Routes (defined in route.py)
    are the EDGES that connect airports.

DATA SOURCE:
    Airport data is loaded from the "nodos" array in the JSON file.
    Each node in the JSON becomes an Airport object.

USAGE:
    - Graph stores airports in _airports dictionary: {airport_id: Airport}
    - API returns airport data for frontend visualization
    - Dynamic planning uses airport costs for mandatory events
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Activity:
    """
    An optional activity available at an airport destination.
    
    Activities represent tourist options that travelers can choose to do
    during their trip. Each activity costs both money AND time.
    
    EXAMPLES:
        - City tour: 120 minutes, $25
        - Museum visit: 90 minutes, $15
        - Cultural experience: 180 minutes, $40
    
    WHEN ACTIVITIES ARE AVAILABLE:
        Activities are always available at an airport. The traveler can
        choose to do any number of activities during their stay.
    
    Attributes:
        name: Display name of the activity (e.g., "City Tour")
        kind: Type/category (e.g., "tour", "museum", "cultural")
        duration_min: Duration of the activity in minutes
        cost_usd: Cost of the activity in USD
    """
    name: str
    kind: str
    duration_min: int
    cost_usd: float


@dataclass
class Job:
    """
    A temporary work offering available at an airport.
    
    Jobs allow travelers to earn money when their budget is low.
    This is part of the dynamic planning feature (R2.3.b).
    
    WORK ELIGIBILITY:
        Jobs are only available when the traveler's budget falls below
        35% of their initial budget. This threshold is configurable in
        the JSON file (presupuestoMinimoPorc).
    
    INCOME CALCULATION:
        income = hourly_rate * hours_worked
        
    EXAMPLES:
        - Baggage Handler: $9/hour, max 8 hours
        - Ramp Assistant: $12/hour, max 6 hours
    
    Attributes:
        name: Job title (e.g., "Baggage Handler")
        hourly_rate: Pay rate in USD per hour
        max_hours: Maximum hours the traveler can work at this job
    """
    name: str
    hourly_rate: float
    max_hours: int


@dataclass
class Airport:
    """
    An airport node in the airline route graph.
    
    Represents a city airport with all its properties:
    - Location (coordinates, city, country, timezone)
    - Classification (hub or regular)
    - Costs (lodging, food for mandatory events)
    - Offerings (activities, jobs)
    
    HUB vs REGULAR AIRPORTS:
        - Hub airports (is_hub=True): Major airports with many connections
        - Regular airports: Smaller airports with fewer connections
        The "exclude_secondary" option in route planning excludes non-hub
        airports from the path.
    
    MANDATORY COSTS:
        Every airport has food_cost and lodging_cost. These are applied
        automatically when the traveler exceeds the time intervals for
        mandatory meals (8 hours) and lodging (20 hours).
    
    Attributes:
        id: Three-letter IATA code (e.g., "BOG", "MDE", "LIM")
            This is the unique identifier for the airport
        name: Full airport name (e.g., "El Dorado International")
        city: City where the airport is located (e.g., "Bogota")
        country: Country of the airport (e.g., "Colombia")
        timezone: Timezone string (e.g., "America/Bogota")
        is_hub: Whether this airport is a major hub
        lodging_cost: Cost per night for mandatory lodging in USD
        food_cost: Cost per meal for mandatory food in USD
        lat: Latitude coordinate for map rendering (-90 to 90)
        lon: Longitude coordinate for map rendering (-180 to 180)
        activities: List of optional activities available at this airport
        jobs: List of temporary job offerings at this airport
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
