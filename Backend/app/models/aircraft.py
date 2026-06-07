"""
Aircraft configuration model.

Defines the operational parameters for each aircraft type used in
route cost and duration calculations. Values can be overridden at
runtime via the aircraft configuration UI.
"""

from dataclasses import dataclass


@dataclass
class AircraftConfig:
    """
    Configuration parameters for a specific aircraft type.

    Attributes:
        name: Aircraft type name (e.g. "Avion Comercial", "Avion Regional", "Helice").
        cost_per_km: Operating cost in USD per kilometre.
        time_per_km: Travel time in minutes per kilometre.
    """

    name: str
    cost_per_km: float
    time_per_km: float
