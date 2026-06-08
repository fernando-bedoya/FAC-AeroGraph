"""
Route Planner - High-Level Planning Functions

This module provides high-level planning functions that combine the
low-level algorithms (Dijkstra, Backtracking) into user-friendly
planning operations.

PLANNING FUNCTIONS:

1. plan_basic_itinerary (R2.2)
   - Creates two alternative routes from the same origin:
     a) Route optimized for MAXIMUM destinations within budget
     b) Route optimized for MAXIMUM destinations within time
   - Uses the backtracking algorithm for both
   - Returns both alternatives so the user can choose

2. plan_best_route_by_criteria (R2.2)
   - Finds the best route between two specific airports
   - Can optimize by multiple criteria (distance, time, cost)
   - Uses Dijkstra's algorithm
   - Returns one result per criterion

WHY SEPARATE FILE:
    The algorithms.py file contains low-level pathfinding logic.
    This file contains business logic that combines algorithms with
    application-specific requirements (like returning two alternatives).
"""

from typing import Dict, List, Set

from .algorithms import dijkstra_path, backtracking_max_coverage
from .graph import Graph
from .models import AircraftConfig, DynamicPlan, DynamicStep, TravelPlan


def _sum_cost(segments) -> float:
    """
    Calculate the total cost of a list of travel segments.
    
    Args:
        segments: List of TravelSegment or similar objects with segment_cost
        
    Returns:
        Sum of all segment costs
    """
    return sum(s.segment_cost for s in segments)


def _sum_time(segments) -> float:
    """
    Calculate the total time of a list of travel segments.
    
    Args:
        segments: List of TravelSegment or similar objects with segment_time_min
        
    Returns:
        Sum of all segment times in minutes
    """
    return sum(s.segment_time_min for s in segments)


def plan_basic_itinerary(
    graph: Graph,
    aircraft_cfg: Dict[str, AircraftConfig],
    origin: str,
    budget_usd: float,
    time_hours: float,
) -> Dict[str, TravelPlan]:
    """
    Create a basic itinerary with two alternative routes (R2.2).
    
    This function implements the "Plan Básico" feature which gives the
    user two options for their trip:
    
    OPTION A: Maximum destinations within budget
        - Uses backtracking with "costo" optimization
        - Prunes paths that exceed the budget
        - Ignores time constraint (can take as long as needed)
        
    OPTION B: Maximum destinations within time
        - Uses backtracking with "tiempo" optimization
        - Prunes paths that exceed the time limit
        - Ignores budget constraint (can spend as much as needed)
    
    WHY TWO OPTIONS:
        Different travelers have different priorities:
        - Budget-conscious travelers want Option A
        - Time-constrained travelers want Option B
        By providing both, the user can choose based on their priority.
    
    Args:
        graph: The airline route graph
        aircraft_cfg: Aircraft configurations
        origin: Starting airport IATA code
        budget_usd: Maximum budget in USD (for Option A)
        time_hours: Maximum time in hours (for Option B)
        
    Returns:
        Dictionary with two TravelPlan objects:
        - "budget_route": Maximum destinations within budget
        - "time_route": Maximum destinations within time limit
    """
    # Convert hours to minutes for the algorithm
    time_limit_min = time_hours * 60
    
    # =========================================================================
    # OPTION A: Maximize destinations within budget constraint
    # =========================================================================
    # The backtracking algorithm will:
    # - Explore all possible paths from origin
    # - Prune paths where cost > budget_usd
    # - Return the path with the most destinations
    max_destinations_budget = backtracking_max_coverage(
        graph=graph,
        aircraft_cfg=aircraft_cfg,
        origin=origin,
        budget_limit=budget_usd,        # Budget constraint
        time_limit_min=time_limit_min,  # Time limit (not used for pruning here)
        optimize_for="costo",           # Prune based on cost
    )
    
    # =========================================================================
    # OPTION B: Maximize destinations within time constraint
    # =========================================================================
    # The backtracking algorithm will:
    # - Explore all possible paths from origin
    # - Prune paths where time > time_limit_min
    # - Return the path with the most destinations
    max_destinations_time = backtracking_max_coverage(
        graph=graph,
        aircraft_cfg=aircraft_cfg,
        origin=origin,
        budget_limit=budget_usd,        # Budget limit (not used for pruning here)
        time_limit_min=time_limit_min,  # Time constraint
        optimize_for="tiempo",          # Prune based on time
    )

    # =========================================================================
    # BUILD RESULT: Extract visited airports and create TravelPlan objects
    # =========================================================================
    
    # Build list of visited airports: origin + all destinations in order
    budget_airports = [origin] + [s.destination for s in max_destinations_budget]
    time_airports = [origin] + [s.destination for s in max_destinations_time]

    # Return both alternatives
    return {
        "budget_route": TravelPlan(
            title="Mayor cantidad de destinos sin exceder presupuesto",
            visited_airports=budget_airports,
            segments=max_destinations_budget,
            total_cost=_sum_cost(max_destinations_budget),
            total_time_min=_sum_time(max_destinations_budget),
        ),
        "time_route": TravelPlan(
            title="Mayor cantidad de destinos en menor tiempo",
            visited_airports=time_airports,
            segments=max_destinations_time,
            total_cost=_sum_cost(max_destinations_time),
            total_time_min=_sum_time(max_destinations_time),
        ),
    }


def plan_best_route_by_criteria(
    graph: Graph,
    aircraft_cfg: Dict[str, AircraftConfig],
    origin: str,
    destination: str,
    criteria: List[str],
    exclude_secondary: bool,
    allowed_aircraft: List[str],
):
    """
    Find the best route between two airports for each criterion (R2.2).
    
    This function uses Dijkstra's algorithm to find the optimal route
    from origin to destination for each specified criterion.
    
    CRITERIA OPTIONS:
        - "distancia": Minimize total distance (shortest path)
        - "tiempo": Minimize total travel time (fastest path)
        - "costo": Minimize total cost (cheapest path)
    
    WHY MULTIPLE CRITERIA:
        The user can select multiple criteria and get a route for each.
        This allows comparing routes optimized for different priorities.
        For example, the cheapest route might take longer than the fastest.
    
    Args:
        graph: The airline route graph
        aircraft_cfg: Aircraft configurations
        origin: Starting airport IATA code
        destination: Ending airport IATA code
        criteria: List of optimization criteria (e.g., ["costo", "tiempo"])
        exclude_secondary: If True, only use hub airports as waypoints
        allowed_aircraft: List of allowed aircraft types (empty = all allowed)
        
    Returns:
        Dictionary mapping each criterion to its result:
        {
            "costo": {
                "segments": [...],
                "total_cost": 123.45,
                "total_time_min": 678.9,
                "total_distance_km": 1234.5,
                "reachable": True
            },
            "tiempo": { ... }
        }
    """
    results = {}
    allowed_set: Set[str] = set(allowed_aircraft)
    
    # Run Dijkstra for each criterion
    for criterion in criteria:
        path = dijkstra_path(
            graph=graph,
            aircraft_cfg=aircraft_cfg,
            origin=origin,
            destination=destination,
            criterion=criterion,
            allowed_aircraft=allowed_set if allowed_aircraft else None,
            exclude_secondary=exclude_secondary,
        )
        results[criterion] = {
            "segments": [segment.__dict__ for segment in path],
            "total_cost": _sum_cost(path),
            "total_time_min": _sum_time(path),
            "total_distance_km": sum(s.distance_km for s in path),
            # A route is reachable if we found segments OR origin == destination
            "reachable": len(path) > 0 or origin == destination,
        }
    return results
