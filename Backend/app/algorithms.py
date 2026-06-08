"""
Graph Algorithms for Route Optimization

This module implements pathfinding algorithms for finding optimal routes
in the airline network graph.

ALGORITHMS IMPLEMENTED:

1. DIJKSTRA'S ALGORITHM (dijkstra_path)
   - Purpose: Find the shortest path between two airports
   - Criterion: Can optimize by distance, time, or cost
   - Time Complexity: O((V + E) log V)
     where V = number of airports, E = number of routes
   - Why Dijkstra: Airline routes have non-negative weights (you can't
     have negative distance or negative cost), and we need optimal paths.
   - Use Case: Finding the best route from A to B based on a specific
     criterion (shortest distance, fastest time, or cheapest cost)

2. BACKTRACKING ALGORITHM (backtracking_max_coverage)
   - Purpose: Find the route that visits the MAXIMUM number of airports
     without exceeding budget or time constraints
   - Time Complexity: O(V!) worst case, but pruning reduces this dramatically
   - Why Backtracking: We need to explore all possible paths and find the
     one with maximum coverage. Dijkstra can't do this because it only
     finds the shortest path to ONE destination, not the path that visits
     the MOST destinations.
   - Use Case: "Plan básico" (basic plan) - given a budget and time limit,
     find the route that visits the most airports

KEY DIFFERENCES:
    - Dijkstra: Point A to Point B, optimize ONE criterion
    - Backtracking: Start anywhere, visit as many places as possible
      within constraints
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
import heapq

from .graph import Graph
from .models import AircraftConfig, TravelSegment


# =============================================================================
# LOCAL DATA STRUCTURES
# =============================================================================
# We define local versions of Route and TravelSegment to avoid circular
# imports and keep this module self-contained for the pathfinding logic.

@dataclass(frozen=False)
class _LocalRoute:
    """
    Local representation of an airline route for pathfinding.
    
    WHY LOCAL CLASS:
        The dijkstra_path function needs to filter aircraft types based
        on the allowed_aircraft parameter. Creating a filtered copy of
        the route avoids modifying the original route in the graph.
    
    Attributes:
        origin: Origin airport IATA code
        destination: Destination airport IATA code
        distance_km: Distance in kilometers
        aircraft_types: List of available aircraft types (may be filtered)
        base_cost: Base cost modifier (0 = subsidized route)
        min_stay_min: Minimum required stay at destination
        blocked: Whether the route is currently blocked
    """
    origin: str
    destination: str
    distance_km: float
    aircraft_types: List[str]
    base_cost: float
    min_stay_min: float
    blocked: bool


@dataclass
class _LocalTravelSegment:
    """
    Local representation of a travel segment for pathfinding results.
    
    A travel segment represents one leg of a journey: flying from one
    airport to another using a specific aircraft.
    
    Attributes:
        origin: Origin airport IATA code
        destination: Destination airport IATA code
        aircraft: Aircraft type used for this segment
        distance_km: Distance in kilometers
        segment_cost: Cost in USD for this segment
        segment_time_min: Time in minutes for this segment
    """
    origin: str
    destination: str
    aircraft: str
    distance_km: float
    segment_cost: float
    segment_time_min: float


def _weight_for_route(route: Any, aircraft_cfg: Dict[str, Any], criterion: str) -> Tuple[float, str, float, float]:
    """
    Calculate the weight of a route based on the optimization criterion.
    
    This function determines which aircraft type is BEST for the given
    criterion on this specific route segment. Different aircraft may have
    different costs and times, so we need to pick the optimal one.
    
    HOW IT WORKS:
        For each aircraft type available on this route:
        1. Calculate the segment cost: distance * cost_per_km
        2. Calculate the segment time: distance * time_per_km
        3. Calculate the weight based on the criterion:
           - "distancia": weight = distance (same for all aircraft)
           - "tiempo": weight = segment time
           - "costo": weight = segment cost
        4. Keep track of the aircraft with the LOWEST weight
    
    WHY THIS FUNCTION:
        A route might have multiple aircraft types (e.g., "Avion Comercial"
        and "Helice"). Each has different cost/time characteristics. We need
        to select the best one for the current optimization criterion.
    
    Args:
        route: Route object with distance and aircraft types
        aircraft_cfg: Dictionary mapping aircraft names to their configurations
        criterion: Optimization criterion ('distancia', 'tiempo', or 'costo')
        
    Returns:
        Tuple of (best_weight, best_aircraft_name, segment_cost, segment_time)
        - best_weight: The lowest weight found (for the priority queue)
        - best_aircraft_name: Name of the aircraft that achieves this weight
        - segment_cost: Cost in USD for this segment
        - segment_time: Time in minutes for this segment
    """
    # Initialize with worst possible values
    best_weight = float("inf")
    best_aircraft = ""
    best_cost = 0.0
    best_time = 0.0

    # Try each aircraft type available on this route
    for aircraft_name in route.aircraft_types:
        cfg = aircraft_cfg.get(aircraft_name)
        if not cfg:
            continue  # Skip if aircraft config not found
        
        # Calculate cost for this segment
        # If base_cost is 0, the route is subsidized (free)
        segment_cost = route.distance_km * cfg.cost_per_km
        if route.base_cost == 0:
            segment_cost = 0.0
        
        # Calculate time for this segment
        segment_time = route.distance_km * cfg.time_per_km

        # Determine the weight based on the optimization criterion
        if criterion == "distancia":
            # Distance is the same regardless of aircraft
            weight = route.distance_km
        elif criterion == "tiempo":
            # Optimize for shortest time
            weight = segment_time
        else:  # "costo"
            # Optimize for lowest cost
            weight = segment_cost

        # Update if this aircraft is better than the current best
        if weight < best_weight:
            best_weight = weight
            best_aircraft = aircraft_name
            best_cost = segment_cost
            best_time = segment_time

    return best_weight, best_aircraft, best_cost, best_time


def dijkstra_path(
    graph: Any,
    aircraft_cfg: Dict[str, Any],
    origin: str,
    destination: str,
    criterion: str,
    allowed_aircraft: Optional[Set[str]] = None,
    exclude_secondary: bool = False,
) -> List[_LocalTravelSegment]:
    """
    Find the optimal path between two airports using Dijkstra's algorithm.
    
    DIJKSTRA'S ALGORITHM EXPLAINED:
        Dijkstra's algorithm finds the shortest path from a source node to
        all other nodes in a weighted graph. It works by:
        
        1. Start at the origin with distance 0
        2. Use a priority queue (min-heap) to always process the node
           with the smallest known distance
        3. For each neighbor, calculate the distance through the current node
        4. If this distance is smaller than the previously known distance,
           update it and add the neighbor to the priority queue
        5. Repeat until the destination is reached or the queue is empty
        
        WHY PRIORITY QUEUE:
            A priority queue ensures we always process the closest unvisited
            node first. This guarantees that when we reach a node, we've
            found the shortest path to it.
            
            Using a simple list would require O(V) to find the minimum,
            making the algorithm O(V²). With a heap, finding the minimum
            is O(log V), making the algorithm O((V + E) log V).
    
    Args:
        graph: Graph object representing the airline network
        aircraft_cfg: Dictionary mapping aircraft names to their configurations
        origin: Origin airport IATA code (starting point)
        destination: Destination airport IATA code (ending point)
        criterion: Optimization criterion:
                   - 'distancia': Minimize total distance
                   - 'tiempo': Minimize total travel time
                   - 'costo': Minimize total cost
        allowed_aircraft: Optional set of allowed aircraft types.
                         If provided, only these aircraft will be considered.
        exclude_secondary: If True, exclude non-hub airports from the path.
                          Only major hub airports will be used as waypoints.
        
    Returns:
        List of travel segments representing the optimal path.
        Empty list if no path exists.
        
    Example:
        segments = dijkstra_path(graph, cfg, "BOG", "LIM", "costo")
        # Returns: [Segment(BOG->MDE), Segment(MDE->LIM)]
    """
    # =========================================================================
    # INITIALIZATION
    # =========================================================================
    
    # Distance from origin to each node
    # Initialize origin with 0, all others with infinity (unknown)
    dist: Dict[str, float] = {origin: 0.0}
    
    # Previous node and segment info for path reconstruction
    # Maps each node to: (previous_node, aircraft, distance, cost, time)
    prev: Dict[str, Tuple[str, str, float, float, float]] = {}
    
    # Priority queue: (distance, airport_id)
    # The heap automatically keeps the smallest distance at the top
    queue: List[Tuple[float, str]] = [(0.0, origin)]
    
    # Set of already-processed nodes
    # Once a node is visited, we've found the shortest path to it
    visited: Set[str] = set()

    # =========================================================================
    # MAIN LOOP: Process nodes in order of increasing distance
    # =========================================================================
    while queue:
        # Get the node with the smallest distance
        current_dist, node = heapq.heappop(queue)
        
        # Skip if already processed (can happen with duplicate entries in queue)
        if node in visited:
            continue
        visited.add(node)

        # Early termination: if we reached the destination, stop
        # WHY: We don't need to find shortest paths to ALL nodes,
        # just the one to our destination
        if node == destination:
            break

        # =====================================================================
        # RELAXATION: Check all outgoing routes from this node
        # =====================================================================
        for route in graph.get_outgoing_routes(node):
            # Skip blocked routes (temporarily disabled)
            if route.blocked:
                continue
            
            # Skip non-hub airports if exclude_secondary is True
            # WHY: Sometimes we want to only route through major hubs
            airport_dest = graph.get_airport(route.destination)
            if exclude_secondary and airport_dest and not airport_dest.is_hub:
                continue

            # Filter aircraft types if allowed_aircraft is specified
            available_types = route.aircraft_types
            if allowed_aircraft:
                available_types = [t for t in available_types if t in allowed_aircraft]
            if not available_types:
                continue  # No valid aircraft for this route

            # Create a filtered route with only allowed aircraft
            filtered_route = _LocalRoute(
                origin=route.origin,
                destination=route.destination,
                distance_km=route.distance_km,
                aircraft_types=available_types,
                base_cost=route.base_cost,
                min_stay_min=route.min_stay_min,
                blocked=route.blocked,
            )

            # Calculate the weight and best aircraft for this route
            weight, aircraft, seg_cost, seg_time = _weight_for_route(
                filtered_route, aircraft_cfg, criterion
            )
            if aircraft == "":
                continue  # No valid aircraft found

            # =================================================================
            # RELAXATION STEP: Update distance if we found a shorter path
            # =================================================================
            new_dist = current_dist + weight
            
            # If this path is shorter than any previously known path
            if new_dist < dist.get(route.destination, float("inf")):
                # Update the shortest distance
                dist[route.destination] = new_dist
                # Record how we got here (for path reconstruction)
                prev[route.destination] = (node, aircraft, route.distance_km, seg_cost, seg_time)
                # Add to priority queue for processing
                heapq.heappush(queue, (new_dist, route.destination))

    # =========================================================================
    # PATH RECONSTRUCTION: Build the path from destination back to origin
    # =========================================================================
    
    # Check if destination was reached
    if destination not in prev and destination != origin:
        return []  # No path exists

    # Trace back from destination to origin using the 'prev' dictionary
    path_segments: List[_LocalTravelSegment] = []
    current = destination
    
    while current != origin:
        p_node, aircraft, distance_km, seg_cost, seg_time = prev[current]
        path_segments.append(
            _LocalTravelSegment(
                origin=p_node,
                destination=current,
                aircraft=aircraft,
                distance_km=distance_km,
                segment_cost=seg_cost,
                segment_time_min=seg_time,
            )
        )
        current = p_node  # Move to the previous node

    # Reverse the path because we built it backwards (destination -> origin)
    path_segments.reverse()
    return path_segments


def backtracking_max_coverage(
    graph: Graph,
    aircraft_cfg: Dict[str, AircraftConfig],
    origin: str,
    budget_limit: float,
    time_limit_min: float,
    optimize_for: str,
) -> List[TravelSegment]:
    """
    Find the route that visits the MAXIMUM number of airports without
    exceeding budget or time constraints.
    
    BACKTRACKING ALGORITHM EXPLAINED:
        Backtracking is a systematic way to explore all possible solutions
        by building candidates incrementally and abandoning ("backtracking")
        when a candidate is determined to be invalid.
        
        HOW IT WORKS:
        1. Start at the origin airport
        2. Try all possible next destinations
        3. For each destination, recursively try all further destinations
        4. PRUNING: If adding a destination would exceed the budget or time
           limit, don't explore that branch (cut it early)
        5. Keep track of the best path found so far
        6. When all possibilities are explored, return the best path
        
        WHY BACKTRACKING INSTEAD OF DIJKSTRA:
        - Dijkstra finds the shortest path to ONE destination
        - Backtracking finds the path that visits the MOST destinations
        - These are fundamentally different problems
        
        PRUNING STRATEGY:
        - If we're optimizing for cost and current_cost > budget_limit, stop
        - If we're optimizing for time and current_time > time_limit, stop
        - This dramatically reduces the search space
        
        SELECTION CRITERIA (for choosing the "best" path):
        1. Maximum number of airports visited (primary)
        2. Maximum number of different aircraft types used (secondary)
        3. Minimum cost or time (tiebreaker)
    
    Args:
        graph: The airline route graph
        aircraft_cfg: Aircraft configurations (cost/time per km)
        origin: Starting airport IATA code
        budget_limit: Maximum budget in USD
        time_limit_min: Maximum time in minutes
        optimize_for: Which constraint to optimize for:
                     - "costo": Prune when cost exceeds budget_limit
                     - "tiempo": Prune when time exceeds time_limit_min
    
    Returns:
        List of TravelSegment objects representing the optimal route
    """
    # =========================================================================
    # MUTABLE STATE: Track the best path found during exploration
    # =========================================================================
    # We use a dictionary instead of separate variables because nested
    # functions need to modify these values (closures can read but not
    # reassign outer variables without 'nonlocal')
    best: Dict[str, Any] = {
        "path": [],            # Copy of the best path found so far
        "visited_count": 0,    # Number of destinations visited (excluding origin)
        "aircraft_count": 0,   # Number of different aircraft types used
        "priority": float("inf"),  # Cost or time (lower is better)
    }

    def _backtrack(
        current_node: str,
        visited: Set[str],
        path: List[TravelSegment],
        cost: float,
        time_min: float,
        aircraft_used: Set[str],
    ) -> None:
        """
        Recursive function that explores all possible paths.
        
        This is the heart of the backtracking algorithm. At each call:
        1. Check if the current path is better than the best known path
        2. Try all possible next destinations
        3. For each valid destination, recurse deeper
        4. After returning from recursion, undo changes (backtrack)
        
        Args:
            current_node: Current airport being explored
            visited: Set of airports already in the current path
            path: List of segments in the current path
            cost: Total cost accumulated so far
            time_min: Total time accumulated so far
            aircraft_used: Set of aircraft types used so far
        """
        # =====================================================================
        # STEP 1: Update the best result if current path is better
        # =====================================================================
        # Count destinations (excluding the origin)
        destinations = len(visited) - 1
        current_priority = cost if optimize_for == "costo" else time_min

        # A path is better if:
        # 1. It visits more destinations (primary criterion)
        # 2. OR same destinations but more aircraft types (secondary)
        # 3. OR same destinations and aircraft but lower cost/time (tiebreaker)
        if destinations > 0:
            is_better = (
                destinations > best["visited_count"]
                or (
                    destinations == best["visited_count"]
                    and len(aircraft_used) > best["aircraft_count"]
                )
                or (
                    destinations == best["visited_count"]
                    and len(aircraft_used) == best["aircraft_count"]
                    and current_priority < best["priority"]
                )
            )
            if is_better:
                # Save a copy of the current path (not a reference!)
                best["path"] = path[:]
                best["visited_count"] = destinations
                best["aircraft_count"] = len(aircraft_used)
                best["priority"] = current_priority

        # =====================================================================
        # STEP 2: Explore all outgoing routes from current airport
        # =====================================================================
        for route in graph.get_outgoing_routes(current_node):
            # Skip blocked routes or airports already in the path
            # WHY: We don't want to visit the same airport twice
            if route.blocked or route.destination in visited:
                continue

            # Try each aircraft type available on this route
            for aircraft in route.aircraft_types:
                if aircraft not in aircraft_cfg:
                    continue  # Skip unknown aircraft types

                # =================================================================
                # STEP 3: Calculate cost and time for this segment
                # =================================================================
                cfg = aircraft_cfg[aircraft]
                seg_cost = route.distance_km * cfg.cost_per_km
                if route.base_cost == 0:
                    seg_cost = 0.0  # Subsidized route: free
                seg_time = route.distance_km * cfg.time_per_km

                new_cost = cost + seg_cost
                new_time = time_min + seg_time

                # =================================================================
                # STEP 4: PRUNING - Skip if constraints would be violated
                # =================================================================
                # This is the key optimization that makes backtracking feasible.
                # Without pruning, we'd explore ALL possible paths (O(V!)).
                # With pruning, we cut branches early when they can't lead to
                # a valid solution.
                if optimize_for == "costo" and new_cost > budget_limit:
                    continue  # Would exceed budget
                if optimize_for == "tiempo" and new_time > time_limit_min:
                    continue  # Would exceed time limit

                # =================================================================
                # STEP 5: Add segment and recurse deeper
                # =================================================================
                new_segment = TravelSegment(
                    origin=route.origin,
                    destination=route.destination,
                    aircraft=aircraft,
                    distance_km=route.distance_km,
                    segment_cost=seg_cost,
                    segment_time_min=seg_time,
                )
                path.append(new_segment)
                visited.add(route.destination)
                
                # Track if this aircraft type is new (for diversity criterion)
                aircraft_is_new = aircraft not in aircraft_used
                aircraft_used.add(aircraft)

                # Recurse: explore further from the new airport
                _backtrack(
                    current_node=route.destination,
                    visited=visited,
                    path=path,
                    cost=new_cost,
                    time_min=new_time,
                    aircraft_used=aircraft_used,
                )

                # =================================================================
                # STEP 6: BACKTRACK - Undo all changes for next iteration
                # =================================================================
                # This is the "backtrack" in backtracking. We undo the changes
                # so we can try a different path from the same starting point.
                path.pop()  # Remove the segment we added
                visited.discard(route.destination)  # Remove from visited set
                if aircraft_is_new:
                    aircraft_used.discard(aircraft)  # Remove if we added it

    # =========================================================================
    # INITIAL CALL: Start the exploration from the origin
    # =========================================================================
    _backtrack(
        current_node=origin,
        visited={origin},  # Origin is already visited
        path=[],           # Start with empty path
        cost=0.0,          # Start with zero cost
        time_min=0.0,      # Start with zero time
        aircraft_used=set(),  # Start with no aircraft used
    )

    return best["path"]
