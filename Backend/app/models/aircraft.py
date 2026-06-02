from dataclasses import dataclass


@dataclass
class AircraftConfig:
    name: str
    cost_per_km: float
    time_per_km: float
