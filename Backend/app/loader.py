"""
JSON Graph Loader

This module reads a JSON file and converts it into the application's
internal data structures (Graph, AircraftConfig, rules).

JSON FILE STRUCTURE:
    The JSON file must have this format:
    {
        "nodos": [                    # List of airports (nodes)
            {
                "id": "BOG",          # 3-letter IATA code
                "nombre": "El Dorado",
                "ciudad": "Bogota",
                "pais": "Colombia",
                "zonaHoraria": "America/Bogota",
                "esHub": true,        # Is this a major hub airport?
                "costoAlojamiento": 50.0,
                "costoAlimentacion": 15.0,
                "latitud": 4.7016,
                "longitud": -74.1469,
                "actividades": [...], # Optional tourist activities
                "trabajos": [...]     # Optional temporary jobs
            }
        ],
        "aristas": [                  # List of routes (edges)
            {
                "origen": "BOG",
                "destino": "MDE",
                "distanciaKm": 215.0,
                "aeronaves": ["Avion Comercial", "Helice"],
                "costoBase": 1,       # 0 = subsidized route (free)
                "estanciaMinima": 30  # Minimum stay in minutes
            }
        ],
        "config": {                   # Global configuration
            "aeronaves": {
                "Avion Comercial": {"costoKm": 0.18, "tiempoKm": 0.7},
                "Avion Regional": {"costoKm": 0.25, "tiempoKm": 1.1},
                "Helice": {"costoKm": 0.12, "tiempoKm": 2.5}
            },
            "presupuestoMinimoPorc": 35,    # Budget threshold for work eligibility
            "intervaloAlojamiento": 20,     # Hours between mandatory lodging
            "intervaloAlimentacion": 8      # Hours between mandatory meals
        }
    }

WHY SEPARATE FILE:
    Separating the JSON parsing logic from the Graph class keeps the
    Graph class clean and focused on graph operations (Dijkstra, etc.).
"""

import json
from typing import Dict, Tuple

from .graph import Graph
from .models import (
    Activity,
    Airport,
    AircraftConfig,
    DEFAULT_AIRCRAFT,
    Job,
    Route,
)


def _normalize_aircraft_name(name: str) -> str:
    """
    Standardize aircraft type names to ensure consistency.
    
    WHY THIS FUNCTION:
        JSON files might have inconsistent naming like "avion comercial",
        "Avion Comercial", or "AVION COMERCIAL". This function ensures
        all variations are converted to the same standard format.
    
    Args:
        name: The raw aircraft name from the JSON file
        
    Returns:
        The standardized aircraft name
    """
    normalized = name.strip()
    
    # Handle common variations of each aircraft type
    if normalized.lower() == "avion comercial":
        return "Avion Comercial"
    if normalized.lower() == "avion regional":
        return "Avion Regional"
    if normalized.lower() == "helice":
        return "Helice"
    
    # Return as-is if it doesn't match known types
    return normalized


def load_graph_from_json(path: str) -> Tuple[Graph, Dict[str, AircraftConfig], Dict[str, float]]:
    """
    Parse a JSON file and create the application's data structures.
    
    This function performs three main tasks:
    1. Creates Airport objects and adds them to the Graph
    2. Creates Route objects and adds them to the Graph
    3. Extracts aircraft configurations and game rules
    
    HOW THE GRAPH IS BUILT:
        The Graph uses an adjacency list representation:
        - Each airport is stored in a dictionary: {airport_id: Airport}
        - Routes are stored as outgoing edges: {airport_id: [Route, Route, ...]}
        
        This allows efficient lookup of all routes FROM a given airport,
        which is essential for pathfinding algorithms like Dijkstra.
    
    Args:
        path: Absolute path to the JSON file
        
    Returns:
        A tuple containing:
        - Graph: The populated graph with airports and routes
        - Dict[str, AircraftConfig]: Aircraft cost/time configurations
        - Dict[str, float]: Game rules for dynamic planning
    """
    # Read and parse the JSON file
    with open(path, "r", encoding="utf-8") as file:
        raw = json.load(file)

    # Create an empty graph
    graph = Graph()

    # =========================================================================
    # STEP 1: Load airports (nodes) from the "nodos" array
    # =========================================================================
    for node in raw.get("nodos", []):
        # Parse optional activities available at this airport
        # Activities are tourist options like tours, museums, etc.
        activities = [
            Activity(
                name=item["nombre"],
                kind=item["tipo"],
                duration_min=int(item["duracionMin"]),
                cost_usd=float(item["costoUSD"]),
            )
            for item in node.get("actividades", [])
        ]
        
        # Parse optional temporary jobs available at this airport
        # Jobs allow travelers to earn money when budget is low
        jobs = [
            Job(
                name=item["nombre"],
                hourly_rate=float(item["tarifaHora"]),
                max_hours=int(item["maxHoras"]),
            )
            for item in node.get("trabajos", [])
        ]
        
        # Create the Airport object with all its properties
        airport = Airport(
            id=node["id"],
            name=node["nombre"],
            city=node["ciudad"],
            country=node["pais"],
            timezone=node["zonaHoraria"],
            is_hub=bool(node["esHub"]),
            lodging_cost=float(node["costoAlojamiento"]),
            food_cost=float(node["costoAlimentacion"]),
            lat=float(node.get("latitud", 0)),    # Default to 0 if missing
            lon=float(node.get("longitud", 0)),   # Default to 0 if missing
            activities=activities,
            jobs=jobs,
        )
        
        # Add the airport to the graph
        graph.add_airport(airport)

    # =========================================================================
    # STEP 2: Load routes (edges) from the "aristas" array
    # =========================================================================
    for edge in raw.get("aristas", []):
        # Create a Route object representing a directed edge
        # Routes are one-directional: origin -> destination
        route = Route(
            origin=edge["origen"],
            destination=edge["destino"],
            distance_km=float(edge["distanciaKm"]),
            # Normalize aircraft names to ensure consistency
            aircraft_types=[_normalize_aircraft_name(t) for t in edge.get("aeronaves", [])],
            # base_cost of 0 means the route is subsidized (free to use)
            base_cost=float(edge.get("costoBase", 1)),
            # Minimum stay required before continuing the trip
            min_stay_min=int(edge.get("estanciaMinima", 0)),
        )
        
        # Add the route to the graph's adjacency list
        graph.add_route(route)

    # =========================================================================
    # STEP 3: Load aircraft configurations
    # =========================================================================
    # Start with default configurations as a base
    aircraft_cfg: Dict[str, AircraftConfig] = dict(DEFAULT_AIRCRAFT)
    
    # Override with any custom configurations from the JSON file
    custom_aircraft = raw.get("config", {}).get("aeronaves", {})
    for name, cfg in custom_aircraft.items():
        n_name = _normalize_aircraft_name(name)
        aircraft_cfg[n_name] = AircraftConfig(
            name=n_name,
            # Use custom values if provided, otherwise use defaults
            cost_per_km=float(cfg.get("costoKm", DEFAULT_AIRCRAFT.get(n_name, DEFAULT_AIRCRAFT["Avion Comercial"]).cost_per_km)),
            time_per_km=float(cfg.get("tiempoKm", DEFAULT_AIRCRAFT.get(n_name, DEFAULT_AIRCRAFT["Avion Comercial"]).time_per_km)),
        )

    # =========================================================================
    # STEP 4: Load game rules for dynamic planning
    # =========================================================================
    rules = {
        # Budget threshold (as percentage of initial budget) below which
        # the traveler becomes eligible to work temporary jobs
        "budget_trigger_percent": float(raw.get("config", {}).get("presupuestoMinimoPorc", 35)),
        
        # Hours between mandatory lodging stays
        # After this many hours of travel, the traveler MUST pay for lodging
        "lodging_interval_h": float(raw.get("config", {}).get("intervaloAlojamiento", 20)),
        
        # Hours between mandatory meals
        # After this many hours of travel, the traveler MUST pay for food
        "food_interval_h": float(raw.get("config", {}).get("intervaloAlimentacion", 8)),
    }

    return graph, aircraft_cfg, rules
