"""
Aircraft Configuration Model

This module defines the configuration parameters for each aircraft type
used in the airline route network.

AIRCRAFT TYPES:
    The application supports three aircraft types by default:
    1. Avion Comercial (Commercial Airplane): Fast, moderate cost
    2. Avion Regional (Regional Airplane): Moderate speed, higher cost
    3. Helice (Propeller Plane): Slow, lowest cost

DEFAULT VALUES:
    These values are defined in config.py and can be overridden by:
    1. The JSON file's "config.aeronaves" section
    2. Runtime updates via the /api/config/aircraft endpoint

HOW AIRCRAFT AFFECT ROUTES:
    Each route specifies which aircraft types can operate it.
    When planning a route, the algorithm selects the best aircraft
    for each segment based on the optimization criterion:
    - For "costo": Select aircraft with lowest cost_per_km
    - For "tiempo": Select aircraft with lowest time_per_km
    - For "distancia": Aircraft doesn't matter (distance is fixed)

COST CALCULATION:
    segment_cost = distance_km * cost_per_km
    If base_cost is 0 (subsidized route), the cost is $0.

TIME CALCULATION:
    segment_time = distance_km * time_per_km
"""

from dataclasses import dataclass


@dataclass
class AircraftConfig:
    """
    Configuration parameters for a specific aircraft type.
    
    These parameters determine how expensive and how fast each aircraft
    type is. The values are used in all route cost and time calculations.
    
    Attributes:
        name: Aircraft type name (e.g., "Avion Comercial", "Helice")
              Must match the names used in route definitions
        cost_per_km: Operating cost in USD per kilometer
                     Example: 0.18 means $0.18 per km
        time_per_km: Travel time in minutes per kilometer
                     Example: 0.7 means 0.7 minutes per km
                     
    EXAMPLE CALCULATION:
        For a 500 km route with Avion Comercial:
        - Cost: 500 * 0.18 = $90
        - Time: 500 * 0.7 = 350 minutes (5.8 hours)
    """
    name: str
    cost_per_km: float
    time_per_km: float
