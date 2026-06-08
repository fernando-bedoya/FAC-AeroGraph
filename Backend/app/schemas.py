"""
Pydantic Request/Response Schemas

This module defines the data validation schemas for all API endpoints.
Pydantic automatically validates incoming JSON data against these schemas
and converts them to Python objects.

WHY PYDANTIC:
    1. Automatic validation: Rejects invalid data before it reaches our code
    2. Type conversion: Converts JSON types to Python types automatically
    3. Documentation: FastAPI uses these schemas to generate OpenAPI docs
    4. IDE support: Provides autocomplete and type checking

HOW IT WORKS:
    When a POST request arrives with JSON body:
    1. FastAPI reads the JSON
    2. Pydantic validates it against the schema class
    3. If valid, creates a Python object with the data
    4. If invalid, returns a 422 error with details about what's wrong

EXAMPLE:
    Request: POST /api/plan/basic
    Body: {"origin": "BOG", "budget_usd": 700, "time_hours": 28}
    
    FastAPI validates this against BasicPlanRequest:
    - origin: str ✓
    - budget_usd: float ✓
    - time_hours: float ✓
    
    Result: BasicPlanRequest(origin="BOG", budget_usd=700.0, time_hours=28.0)
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class LoadJsonRequest(BaseModel):
    """
    Request body for loading a JSON graph file.
    
    Used by: POST /api/load
    
    Attributes:
        file_path: Optional path to the JSON file.
                  If not provided, the backend opens a native file dialog
                  for the user to select a file manually.
    """
    file_path: Optional[str] = Field(
        None,
        description="Absolute or relative path to the JSON file. "
                    "If not provided, opens native file dialog."
    )


class BasicPlanRequest(BaseModel):
    """
    Request body for basic itinerary planning (R2.2).
    
    Used by: POST /api/plan/basic
    
    This creates two alternative routes:
    1. Maximum destinations within budget
    2. Maximum destinations within time limit
    
    Attributes:
        origin: Starting airport IATA code (e.g., "BOG")
        budget_usd: Maximum budget in USD for the budget-optimized route
        time_hours: Maximum time in hours for the time-optimized route
    """
    origin: str
    budget_usd: float
    time_hours: float


class BestRouteRequest(BaseModel):
    """
    Request body for best-route-by-criteria calculation (R2.2).
    
    Used by: POST /api/plan/best-route
    
    Finds the optimal route between two airports for each criterion.
    
    Attributes:
        origin: Starting airport IATA code
        destination: Ending airport IATA code
        criteria: List of optimization criteria.
                 Valid values: "distancia", "tiempo", "costo"
        exclude_secondary: If True, only use hub airports as waypoints
        allowed_aircraft: List of allowed aircraft types.
                         Empty list means all aircraft are allowed.
    """
    origin: str
    destination: str
    criteria: List[str]
    exclude_secondary: bool = False
    allowed_aircraft: List[str] = []


class DynamicStartRequest(BaseModel):
    """
    Request body for starting a dynamic planning session (R2.3).
    
    Used by: POST /api/dynamic/start
    
    A dynamic session allows interactive trip planning where the user
    can make decisions step by step (choose activities, work, fly, etc.)
    
    Attributes:
        origin: Departure airport IATA code
        initial_budget: Starting budget in USD
        total_time_hours: Total available travel time in hours
    """
    origin: str
    initial_budget: float
    total_time_hours: float


class DynamicActivitiesRequest(BaseModel):
    """
    Request body for selecting optional activities (R2.3.a).
    
    Used by: POST /api/dynamic/activities/{session_id}
    
    Activities are optional tourist options like tours, museums, etc.
    Each activity costs money and takes time.
    
    Attributes:
        activities: List of activity names to perform.
                   Names must match activities available at current airport.
    """
    activities: List[str] = []


class DynamicWorkRequest(BaseModel):
    """
    Request body for performing temporary work (R2.3.b).
    
    Used by: POST /api/dynamic/work/{session_id}
    
    Work allows the traveler to earn money when their budget is low.
    Work is only available when budget < 35% of initial budget.
    
    Attributes:
        job_name: Name of the job to perform.
                 Must match a job available at current airport.
        hours: Number of hours to work. Must be <= job's max_hours.
    """
    job_name: str
    hours: int


class DynamicFlyRequest(BaseModel):
    """
    Request body for initiating a flight segment (R2.3.c).
    
    Used by: POST /api/dynamic/fly/{session_id}
         and: POST /api/dynamic/fly/start/{session_id}
    
    Attributes:
        destination: Destination airport IATA code
        aircraft: Aircraft type name (e.g., "Avion Comercial")
    """
    destination: str
    aircraft: str


class BlockRouteRequest(BaseModel):
    """
    Request body for blocking or unblocking a route (R2.4).
    
    Used by: POST /api/route/block
    
    Blocking a route simulates real-world disruptions like weather
    or mechanical issues. Blocked routes cannot be used until unblocked.
    
    Attributes:
        origin: Origin airport IATA code of the route
        destination: Destination airport IATA code of the route
        blocked: True to block the route, False to unblock
    """
    origin: str
    destination: str
    blocked: bool


class InterruptRequest(BaseModel):
    """
    Request body for handling a route interruption (R2.4).
    
    Used by: POST /api/simulation/interrupt
    
    This is used when a route is blocked while a traveler is in transit.
    The system will redirect the traveler back to the origin airport
    and recalculate available options.
    
    Attributes:
        origin: Origin of the route being interrupted
        destination: Destination of the route being interrupted
        session_id: UUID of the active dynamic session
    """
    origin: str
    destination: str
    session_id: str
