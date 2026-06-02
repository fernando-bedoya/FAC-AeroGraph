from typing import Dict

from .aircraft import AircraftConfig

DEFAULT_AIRCRAFT: Dict[str, AircraftConfig] = {
    "Avion Comercial": AircraftConfig("Avion Comercial", 0.18, 0.7),
    "Avion Regional": AircraftConfig("Avion Regional", 0.25, 1.1),
    "Helice": AircraftConfig("Helice", 0.12, 2.5),
}
