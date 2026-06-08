"""
Application Configuration and State Management

This module manages the global state of the application, including:
- The loaded graph (airports and routes)
- Aircraft configurations (cost per km, time per km)
- Game rules (food intervals, lodging intervals, budget thresholds)
- Active dynamic planning sessions

WHY SEPARATE FILE:
    Following the Single Responsibility Principle, this file handles
    ONLY configuration and state management. The FastAPI app definition
    is in main.py, and the API routes are in api.py.

HOW IT WORKS:
    A global instance called 'app_state' is created at the bottom.
    All API routes access this same instance to read/write application data.
    This is a simple form of dependency injection for a single-server app.
"""

import os
from pathlib import Path
from typing import Dict, Optional, Tuple

from .graph import Graph
from .loader import load_graph_from_json
from .models import AircraftConfig


class AppConfig:
    """
    Manages the global application state.
    
    This class acts as a container for all shared data that needs to
    persist between API requests. It holds:
    - The airline route graph
    - Aircraft cost/time configurations
    - Game rules for dynamic planning
    - Active user sessions
    
    WHY A CLASS:
        Using a class instead of global variables provides better
        organization and makes it easier to reset state for testing.
    """
    
    def __init__(self):
        """
        Initialize all state variables to empty/default values.
        
        Called once when the application starts. All values start as
        None or empty because no graph has been loaded yet.
        """
        # The airline route graph - None until a JSON file is loaded
        self.graph: Optional[Graph] = None
        
        # Aircraft configurations: maps aircraft name to its config
        # Example: {"Avion Comercial": AircraftConfig(cost_per_km=0.18, ...)}
        self.aircraft_cfg: Dict[str, AircraftConfig] = {}
        
        # Game rules for dynamic planning sessions
        # Contains: food_interval_h, lodging_interval_h, budget_trigger_percent
        self.rules: Dict[str, float] = {}
        
        # Path to the currently loaded JSON file (for display purposes)
        self.loaded_file: Optional[str] = None
        
        # Active dynamic planning sessions, keyed by session UUID
        # Each session tracks a user's interactive trip planning state
        self.dynamic_sessions: Dict = {}
    
    def load_graph(self, file_path: str) -> Tuple[int, int]:
        """
        Load the airline route graph from a JSON file.
        
        This method:
        1. Converts the path to absolute if it's relative
        2. Checks if the file exists
        3. Parses the JSON and creates the graph
        4. Stores the graph, aircraft config, and rules in the app state
        
        HOW THE JSON IS STRUCTURED:
            The JSON file contains:
            - "nodos": List of airports with their properties
            - "aristas": List of routes between airports
            - "config": Aircraft configurations and game rules
        
        Args:
            file_path: Path to the JSON file (can be relative or absolute)
            
        Returns:
            A tuple of (number_of_airports, number_of_routes)
            This is returned so the API can tell the user how many items were loaded
            
        Raises:
            FileNotFoundError: If the specified file does not exist
        """
        file_path_obj = Path(file_path)
        
        # Convert relative paths to absolute paths
        # WHY: Relative paths are relative to this file's location, not the
        # current working directory. We need to resolve them correctly.
        if not file_path_obj.is_absolute():
            # parents[1] goes up two levels: from app/config.py to Backend/
            base = Path(__file__).resolve().parents[1]
            file_path_obj = (base / file_path_obj).resolve()
        
        # Check if file exists before trying to load it
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Graph file not found: {file_path_obj}")
        
        # Parse the JSON file and extract graph, aircraft config, and rules
        # The loader returns three separate objects that we store in app state
        self.graph, self.aircraft_cfg, self.rules = load_graph_from_json(str(file_path_obj))
        self.loaded_file = str(file_path_obj)
        
        # Count the loaded items for the API response
        num_airports = len(self.graph.get_all_airports())
        num_routes = len(self.graph.get_all_routes())
        
        return num_airports, num_routes
    
    def is_loaded(self) -> bool:
        """
        Check if a graph has been loaded.
        
        Returns:
            True if a graph is currently loaded, False otherwise
        
        WHY THIS METHOD:
            API routes use this to check if they can process requests
            that require graph data (like route planning).
        """
        return self.graph is not None


# Create the global application state instance
# WHY GLOBAL: In a single-server application, having one shared state
# is simpler than passing it through every function. This is a common
# pattern in FastAPI applications for small to medium projects.
app_state = AppConfig()
