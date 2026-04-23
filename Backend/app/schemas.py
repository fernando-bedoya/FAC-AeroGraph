from typing import List

from pydantic import BaseModel, Field


class LoadJsonRequest(BaseModel):
    file_path: str = Field(..., description="Ruta absoluta o relativa del JSON")


class BasicPlanRequest(BaseModel):
    origin: str
    budget_usd: float
    time_hours: float


class BestRouteRequest(BaseModel):
    origin: str
    destination: str
    criteria: List[str]
    exclude_secondary: bool = False
    allowed_aircraft: List[str] = []


class DynamicPlanRequest(BaseModel):
    origin: str
    initial_budget: float
    total_time_hours: float


class BlockRouteRequest(BaseModel):
    origin: str
    destination: str
    blocked: bool
