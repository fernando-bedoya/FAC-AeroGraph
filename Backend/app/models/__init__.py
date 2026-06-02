"""
Models package: Core data structures for the AeroGraph application.

Organized by domain responsibility:
- airport: Airport, Activity, Job entities
- aircraft: Aircraft configuration
- route: Flight route definitions
- travel: Travel planning models
- dynamic: Dynamic planning session models
- graph: Graph edge representation
- config: Default aircraft configurations
"""

from .airport import Activity, Airport, Job
from .aircraft import AircraftConfig
from .config import DEFAULT_AIRCRAFT
from .dynamic import DynamicPlan, DynamicStep
from .graph import Edge
from .route import Route
from .travel import TravelPlan, TravelSegment

__all__ = [
    "Activity",
    "Airport",
    "Job",
    "AircraftConfig",
    "DEFAULT_AIRCRAFT",
    "DynamicPlan",
    "DynamicStep",
    "Edge",
    "Route",
    "TravelPlan",
    "TravelSegment",
]
