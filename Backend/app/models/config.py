"""
Default Aircraft Configurations

This module defines the default aircraft configurations used when
no custom configurations are provided in the JSON file.

DEFAULT AIRCRAFT TYPES:
    1. Avion Comercial (Commercial Airplane)
       - Cost: $0.18 per km
       - Time: 0.7 minutes per km
       - Best for: Long distances, balanced cost/speed
    
    2. Avion Regional (Regional Airplane)
       - Cost: $0.25 per km
       - Time: 1.1 minutes per km
       - Best for: Medium distances, faster but more expensive
    
    3. Helice (Propeller Plane)
       - Cost: $0.12 per km
       - Time: 2.5 minutes per km
       - Best for: Short distances, cheapest but slowest

OVERRIDE MECHANISM:
    These defaults can be overridden by:
    1. The JSON file's "config.aeronaves" section
    2. Runtime updates via the /api/config/aircraft endpoint
    
    The loader.py module starts with these defaults and overrides
    them with any custom values from the JSON file.

EXAMPLE CALCULATION:
    For a 500 km route:
    - Avion Comercial: Cost = $90, Time = 350 min (5.8 hours)
    - Avion Regional: Cost = $125, Time = 550 min (9.2 hours)
    - Helice: Cost = $60, Time = 1250 min (20.8 hours)
"""

from typing import Dict

from .aircraft import AircraftConfig

# Dictionary mapping aircraft names to their default configurations
# This is used as the base configuration before any overrides
DEFAULT_AIRCRAFT: Dict[str, AircraftConfig] = {
    "Avion Comercial": AircraftConfig("Avion Comercial", 0.18, 0.7),
    "Avion Regional": AircraftConfig("Avion Regional", 0.25, 1.1),
    "Helice": AircraftConfig("Helice", 0.12, 2.5),
}
