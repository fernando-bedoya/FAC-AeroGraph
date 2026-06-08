"""
Models Package - Core Data Structures

This package contains all the data models (dataclasses) used throughout
the application. Models are organized by domain responsibility.

DOMAIN ORGANIZATION:
    - airport.py: Airport, Activity, Job entities (graph nodes)
    - aircraft.py: Aircraft configuration (cost/time per km)
    - route.py: Flight route definitions (graph edges)
    - travel.py: Travel planning models (segments and plans)
    - dynamic.py: Dynamic planning session models (steps and plans)
    - config.py: Default aircraft configurations
    - graph.py: Legacy Edge class (not used, kept for compatibility)

WHY DATACLASSES:
    Python dataclasses provide a concise way to define data containers:
    - Automatic __init__, __repr__, __eq__ methods
    - Type hints for better IDE support
    - Less boilerplate than regular classes
    
    Example:
        @dataclass
        class Airport:
            id: str
            name: str
        
        # Automatically generates:
        # def __init__(self, id: str, name: str): ...
        # def __repr__(self): return f"Airport(id={self.id}, name={self.name})"
        # def __eq__(self, other): ...

IMPORTS:
    The __init__.py file re-exports all models so they can be imported
    directly from the package:
        from app.models import Airport, Route, AircraftConfig
    Instead of:
        from app.models.airport import Airport
        from app.models.route import Route
        from app.models.aircraft import AircraftConfig
"""

from .airport import Activity, Airport, Job
from .aircraft import AircraftConfig
from .config import DEFAULT_AIRCRAFT
from .dynamic import DynamicPlan, DynamicStep
from .graph import Edge
from .route import Route
from .travel import TravelPlan, TravelSegment

# __all__ defines what gets exported when someone does: from app.models import *
# It also helps IDEs with autocomplete
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
