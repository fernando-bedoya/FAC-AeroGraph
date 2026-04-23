from dataclasses import dataclass, field
from typing import Dict, Optional

from .graph import DirectedGraph
from .models import AircraftConfig


@dataclass
class AppState:
    graph: Optional[DirectedGraph] = None
    aircraft_cfg: Dict[str, AircraftConfig] = field(default_factory=dict)
    rules: Dict[str, float] = field(default_factory=dict)
    loaded_file: Optional[str] = None


app_state = AppState()
