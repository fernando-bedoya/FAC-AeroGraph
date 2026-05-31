"""
Application Configuration and Initialization

Handles loading graphs, aircraft configurations, and game rules.
Separates configuration logic from the FastAPI app definition.
"""

import os
from pathlib import Path
from typing import Dict, Optional, Tuple

from .graph import Graph
from .loader import load_graph_from_json
from .models import AircraftConfig


class AppConfig:
    """Manages application configuration state."""
    
    def __init__(self):
        self.graph: Optional[Graph] = None
        self.aircraft_cfg: Dict[str, AircraftConfig] = {}
        self.rules: Dict[str, float] = {}
        self.loaded_file: Optional[str] = None
        self.dynamic_sessions: Dict = {}
    
    def load_graph(self, file_path: str) -> Tuple[int, int]:
        """
        Load graph from JSON file.
        
        Args:
            file_path: Path to JSON file (relative or absolute)
            
        Returns:
            Tuple of (num_airports, num_routes)
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path_obj = Path(file_path)
        
        # Convert relative paths to absolute
        if not file_path_obj.is_absolute():
            base = Path(__file__).resolve().parents[1]
            file_path_obj = (base / file_path_obj).resolve()
        
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Graph file not found: {file_path_obj}")
        
        # Load from JSON
        self.graph, self.aircraft_cfg, self.rules = load_graph_from_json(str(file_path_obj))
        self.loaded_file = str(file_path_obj)
        
        num_airports = len(self.graph.get_all_airports())
        num_routes = len(self.graph.get_all_routes())
        
        return num_airports, num_routes
    
    def is_loaded(self) -> bool:
        """Check if a graph is currently loaded."""
        return self.graph is not None


# Global app state instance
app_state = AppConfig()
