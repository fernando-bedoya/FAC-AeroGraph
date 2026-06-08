"""
Travel Planning Models

This module defines the models used for representing travel plans
and their individual segments.

TRAVEL SEGMENT:
    A TravelSegment represents one leg of a journey:
    - Flying from airport A to airport B
    - Using a specific aircraft type
    - With calculated cost and time

TRAVEL PLAN:
    A TravelPlan represents a complete itinerary:
    - A title describing the optimization goal
    - List of visited airports in order
    - List of segments (flights)
    - Total cost and time

USAGE:
    These models are returned by the planning functions:
    - plan_basic_itinerary() returns two TravelPlans
    - backtracking_max_coverage() returns a list of TravelSegments
"""

from dataclasses import dataclass
from typing import List


@dataclass
class TravelSegment:
    """
    A single leg of a journey (one flight).
    
    Represents flying from one airport to another using a specific
    aircraft type. Includes the calculated cost and time for this segment.
    
    Attributes:
        origin: Origin airport IATA code (e.g., "BOG")
        destination: Destination airport IATA code (e.g., "MDE")
        aircraft: Aircraft type used for this flight (e.g., "Avion Comercial")
        distance_km: Distance of this segment in kilometers
        segment_cost: Cost in USD for this segment
                      Calculated as: distance_km * aircraft.cost_per_km
        segment_time_min: Time in minutes for this segment
                          Calculated as: distance_km * aircraft.time_per_km
    """
    origin: str
    destination: str
    aircraft: str
    distance_km: float
    segment_cost: float
    segment_time_min: float


@dataclass
class TravelPlan:
    """
    A complete travel itinerary.
    
    Represents a full trip from origin through multiple destinations.
    Used to return planning results to the API and frontend.
    
    Attributes:
        title: Description of the optimization goal
               Example: "Maximum destinations within budget"
        visited_airports: List of airport IATA codes in visit order
                          First element is always the origin
                          Example: ["BOG", "MDE", "CLO", "UIO"]
        segments: List of TravelSegment objects (one per flight)
                  Length = len(visited_airports) - 1
        total_cost: Sum of all segment costs in USD
        total_time_min: Sum of all segment times in minutes
    """
    title: str
    visited_airports: List[str]
    segments: List[TravelSegment]
    total_cost: float
    total_time_min: float
