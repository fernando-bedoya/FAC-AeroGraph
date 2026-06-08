"""
Legacy Graph Edge Model (NOT USED)

WARNING: This module contains a legacy Edge class that is NOT used
by the current implementation. The application uses Route (from route.py)
instead of Edge for graph edges.

WHY THIS FILE EXISTS:
    This file was created during early development but was superseded
    by the more comprehensive Route class. It's kept for backward
    compatibility in case any external code references it.

DIFFERENCE BETWEEN Edge AND Route:
    - Edge: Simple edge with just u, v, distance, is_active
    - Route: Full-featured edge with origin, destination, distance_km,
             aircraft_types, base_cost, min_stay_min, blocked

RECOMMENDATION:
    Do not use Edge in new code. Use Route instead.
"""

from dataclasses import dataclass


@dataclass
class Edge:
    """
    Legacy edge representation (NOT USED).
    
    This is a simplified edge class that was used in early development.
    The current implementation uses Route instead.
    
    Attributes:
        u: Source node identifier
        v: Target node identifier
        distance: Edge weight/distance
        is_active: Whether the edge is active (not blocked)
    """
    u: str
    v: str
    distance: float
    is_active: bool = True

    def to_dict(self):
        """Convert edge to dictionary for JSON serialization."""
        return {"u": self.u, "v": self.v, "distance": self.distance, "is_active": self.is_active}
