"""
Route Model - Graph Edges

This module defines the Route class, which represents a directed edge
in the airline route graph.

ROUTE CHARACTERISTICS:
    - Directed: A route from BOG to MDE is different from MDE to BOG
    - Weighted: Each route has a distance (used as weight in algorithms)
    - Multi-aircraft: A route can be operated by multiple aircraft types
    - Blockable: Routes can be temporarily blocked (simulating disruptions)

SUBSIDIZED ROUTES:
    A route with base_cost = 0 is a "subsidized" route (free to use).
    However, subsidized routes are subject to a 20% distance cap:
    - The total distance flown on subsidized routes cannot exceed 20%
      of the total distance flown
    - This prevents travelers from using only free routes
    
    Example:
        If total_distance = 1000 km
        And free_distance = 250 km (25%)
        Then the next subsidized route would be rejected because
        250 + new_distance > 1000 * 0.2

MINIMUM STAY:
    Some routes require a minimum stay at the destination before
    continuing the trip. This simulates real-world constraints like
    visa requirements or connection times.

DATA SOURCE:
    Routes are loaded from the "aristas" array in the JSON file.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Route:
    """
    A directed route (edge) between two airports.
    
    Routes represent direct flights between airports. Each route has
    properties that affect how it can be used in route planning.
    
    Attributes:
        origin: Origin airport IATA code (e.g., "BOG")
                This is the starting point of the directed edge
        destination: Destination airport IATA code (e.g., "MDE")
                     This is the ending point of the directed edge
        distance_km: Great-circle distance in kilometers
                     Used as the weight in pathfinding algorithms
        aircraft_types: List of aircraft type names that operate this route
                        Example: ["Avion Comercial", "Helice"]
                        The traveler can choose any of these for the flight
        base_cost: Base cost modifier
                   - If > 0: Normal route, cost = distance * cost_per_km
                   - If = 0: Subsidized route, cost = $0 (subject to 20% cap)
        min_stay_min: Minimum required stay at the destination in minutes
                      The traveler must wait this long before continuing
        blocked: Whether the route is currently blocked (disabled)
                 Blocked routes cannot be used until unblocked
                 Used for simulating disruptions (R2.4)
    """
    origin: str
    destination: str
    distance_km: float
    aircraft_types: List[str]
    base_cost: float
    min_stay_min: int
    blocked: bool = False
