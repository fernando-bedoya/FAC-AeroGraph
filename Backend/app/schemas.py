"""
Pydantic request/response schemas for the SkyRoute Planner API.

Defines the JSON body models for all REST endpoints, including
dynamic planning requests for Requirement 2.3.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class LoadJsonRequest(BaseModel):
    """Request body for loading a JSON graph file."""
    file_path: Optional[str] = Field(None, description="Ruta absoluta o relativa del JSON. Si no se envia, se abre el explorador de archivos nativo.")


class BasicPlanRequest(BaseModel):
    """Request body for basic itinerary planning (R2.2)."""
    origin: str
    budget_usd: float
    time_hours: float


class BestRouteRequest(BaseModel):
    """Request body for best-route-by-criteria calculation (R2.2)."""
    origin: str
    destination: str
    criteria: List[str]
    exclude_secondary: bool = False
    allowed_aircraft: List[str] = []


class DynamicStartRequest(BaseModel):
    """
    Request body for starting a dynamic planning session (R2.3).

    Attributes:
        origin: Departure airport IATA code.
        initial_budget: Starting budget in USD.
        total_time_hours: Total available travel time in hours.
    """
    origin: str
    initial_budget: float
    total_time_hours: float


class DynamicActivitiesRequest(BaseModel):
    """
    Request body for selecting optional activities (R2.3.a).

    Attributes:
        activities: List of activity names to perform.
    """
    activities: List[str] = []


class DynamicWorkRequest(BaseModel):
    """
    Request body for performing temporary work (R2.3.b).

    Attributes:
        job_name: Name of the job to perform.
        hours: Number of hours to work.
    """
    job_name: str
    hours: int


class DynamicFlyRequest(BaseModel):
    """
    Request body for initiating a flight segment (R2.3.c).

    Attributes:
        destination: Destination airport IATA code.
        aircraft: Aircraft type name for this segment.
    """
    destination: str
    aircraft: str


class BlockRouteRequest(BaseModel):
    """Request body for blocking or unblocking a route (R2.4)."""
    origin: str
    destination: str
    blocked: bool


class InterruptRequest(BaseModel):
    """
    Request body for handling a route interruption (R2.4).

    Attributes:
        origin: Origin of the route to interrupt.
        destination: Destination of the route to interrupt.
        session_id: UUID of the active dynamic session.
    """
    origin: str
    destination: str
    session_id: str
