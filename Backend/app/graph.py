"""
Graph Data Structure - Adjacency List Implementation

This module implements a directed weighted graph to represent the airline
route network. The graph is the core data structure of the application.

GRAPH REPRESENTATION:
    We use an adjacency list because:
    1. It's memory-efficient for sparse graphs (most airports don't connect
       to all other airports)
    2. It allows fast iteration over outgoing routes from any airport
    3. It's the natural choice for pathfinding algorithms like Dijkstra

    Structure:
        _airports: {airport_id: Airport}
            Maps each airport code to its Airport object
            
        _adjacency: {airport_id: [Route, Route, ...]}
            Maps each airport to its list of outgoing routes
            
    Example:
        If BOG has routes to MDE and LIM:
        _adjacency["BOG"] = [Route(BOG->MDE), Route(BOG->LIM)]

WHY DIRECTED GRAPH:
    Airline routes are typically one-directional. A flight from BOG to MDE
    doesn't mean there's a flight from MDE to BOG. Each direction must be
    explicitly defined in the JSON file.

ALGORITHMS USING THIS GRAPH:
    - Dijkstra's Algorithm: Finds shortest path by distance, time, or cost
    - Backtracking: Finds routes that maximize airports visited within
      budget/time constraints
"""

from typing import Dict, List, Optional

from .models import Airport, Route


class Graph:
    """
    Directed weighted graph using adjacency list representation.
    
    This is the main data structure for the airline route network.
    It stores airports as nodes and routes as directed edges.
    
    ATTRIBUTES:
        _airports: Dictionary mapping airport IATA codes to Airport objects
                   Example: {"BOG": Airport(id="BOG", name="El Dorado", ...)}
                   
        _adjacency: Dictionary mapping airport codes to lists of outgoing routes
                    Example: {"BOG": [Route(BOG->MDE), Route(BOG->LIM)]}
    
    WHY PRIVATE ATTRIBUTES (underscore prefix):
        The underscore indicates these are internal implementation details.
        External code should use the public methods instead of accessing
        the dictionaries directly. This encapsulation allows us to change
        the internal representation without breaking external code.
    """

    def __init__(self) -> None:
        """
        Initialize an empty graph with no airports or routes.
        
        Called when creating a new graph before loading data from JSON.
        Both dictionaries start empty and are populated by add_airport()
        and add_route() methods.
        """
        self._airports: Dict[str, Airport] = {}
        self._adjacency: Dict[str, List[Route]] = {}

    def add_airport(self, airport: Airport) -> None:
        """
        Add an airport (node) to the graph.
        
        This method:
        1. Stores the airport in the _airports dictionary
        2. Creates an empty list in _adjacency for its outgoing routes
        
        WHY CREATE EMPTY ADJACENCY LIST:
            Even if an airport has no outgoing routes yet, we need an
            empty list so that get_outgoing_routes() doesn't fail when
            queried before any routes are added.
        
        Args:
            airport: Airport object to add to the graph
            
        Example:
            graph.add_airport(Airport(id="BOG", name="El Dorado", ...))
            # Now graph.get_airport("BOG") returns this airport
            # And graph.get_outgoing_routes("BOG") returns []
        """
        self._airports[airport.id] = airport
        # Initialize empty adjacency list for this airport
        if airport.id not in self._adjacency:
            self._adjacency[airport.id] = []

    def add_route(self, route: Route) -> None:
        """
        Add a directed route (edge) to the graph.
        
        This method adds the route to the origin airport's adjacency list.
        Routes are one-directional: this route goes FROM origin TO destination.
        
        WHY APPEND TO LIST:
            An airport can have multiple outgoing routes (to different
            destinations). We store them all in a list.
        
        Args:
            route: Route object representing a directed edge
            
        Example:
            graph.add_route(Route(origin="BOG", destination="MDE", distance_km=215))
            # Now graph.get_outgoing_routes("BOG") includes this route
        """
        # Ensure the origin airport has an adjacency list
        if route.origin not in self._adjacency:
            self._adjacency[route.origin] = []
        # Add the route to the origin's outgoing routes
        self._adjacency[route.origin].append(route)

    def get_airport(self, airport_id: str) -> Optional[Airport]:
        """
        Get an airport by its IATA code.
        
        This is a O(1) dictionary lookup - very fast even for large graphs.
        
        Args:
            airport_id: Three-letter IATA airport code (e.g., 'BOG', 'LIM')
            
        Returns:
            Airport object if found, None if the airport doesn't exist
            
        Example:
            bogota = graph.get_airport("BOG")
            if bogota:
                print(f"Found: {bogota.name}")
        """
        return self._airports.get(airport_id)

    def get_outgoing_routes(self, airport_id: str) -> List[Route]:
        """
        Get all outgoing routes from an airport.
        
        This is the most frequently called method in pathfinding algorithms.
        Dijkstra's algorithm uses this to find all neighbors of a node.
        
        WHY RETURN EMPTY LIST INSTEAD OF NONE:
            Returning an empty list allows algorithms to iterate directly
            without checking for None first. This simplifies the code:
                for route in graph.get_outgoing_routes("BOG"):
                    # Process route...
            Instead of:
                routes = graph.get_outgoing_routes("BOG")
                if routes:
                    for route in routes:
                        # Process route...
        
        Args:
            airport_id: Three-letter IATA airport code
            
        Returns:
            List of Route objects representing outgoing flights
            Returns empty list if airport has no outgoing routes
            
        Example:
            routes = graph.get_outgoing_routes("BOG")
            for route in routes:
                print(f"Can fly to: {route.destination}")
        """
        return self._adjacency.get(airport_id, [])

    def get_route(self, origin: str, destination: str) -> Optional[Route]:
        """
        Find a specific route between two airports.
        
        This method performs a linear search through the origin's outgoing
        routes to find one that matches the destination.
        
        TIME COMPLEXITY: O(E) where E is the number of outgoing routes
        from the origin airport. In practice, this is small (typically < 20).
        
        Args:
            origin: Origin airport IATA code
            destination: Destination airport IATA code
            
        Returns:
            Route object if found, None if no direct route exists
            
        Example:
            route = graph.get_route("BOG", "MDE")
            if route:
                print(f"Distance: {route.distance_km} km")
        """
        # Linear search through outgoing routes
        for route in self.get_outgoing_routes(origin):
            if route.destination == destination:
                return route
        return None

    def is_route_valid(self, origin: str, destination: str) -> bool:
        """
        Check if a route exists and is not blocked.
        
        This is used by the API to validate flight requests before
        allowing a traveler to fly on a route.
        
        A route is valid if:
        1. It exists in the graph (there is a direct flight)
        2. It is not blocked (not temporarily disabled)
        
        Args:
            origin: Origin airport IATA code
            destination: Destination airport IATA code
            
        Returns:
            True if route exists and is not blocked, False otherwise
            
        Example:
            if graph.is_route_valid("BOG", "MDE"):
                # Allow the flight
            else:
                # Reject the flight
        """
        route = self.get_route(origin, destination)
        # Route must exist AND not be blocked
        return route is not None and not route.blocked

    def toggle_route_status(self, origin: str, destination: str, block: bool) -> Optional[Route]:
        """
        Block or unblock a route and return the updated route.
        
        This is used for the route interruption feature (R2.4).
        When a route is blocked, travelers cannot fly on it until
        it is unblocked.
        
        WHY RETURN THE ROUTE:
            The caller needs to know if the operation succeeded.
            If the route doesn't exist, we return None.
            If it exists, we return the updated route so the caller
            can confirm the new blocked status.
        
        Args:
            origin: Origin airport IATA code
            destination: Destination airport IATA code
            block: True to block the route, False to unblock
            
        Returns:
            Updated Route object if found, None if route doesn't exist
            
        Example:
            # Block a route due to weather
            route = graph.toggle_route_status("BOG", "MDE", block=True)
            if route:
                print(f"Route blocked: {route.blocked}")  # True
        """
        route = self.get_route(origin, destination)
        if route:
            route.blocked = block
            return route
        return None

    def get_all_airports(self) -> List[Airport]:
        """
        Get a list of all airports in the graph.
        
        This is used by the API to populate dropdown menus and
        display airport information.
        
        Returns:
            List of all Airport objects in the graph
            
        Example:
            airports = graph.get_all_airports()
            print(f"Total airports: {len(airports)}")
        """
        return list(self._airports.values())

    def get_all_routes(self) -> List[Route]:
        """
        Get a flat list of all routes (edges) in the graph.
        
        This flattens the adjacency list into a single list of routes.
        Used by the API to display all routes and for visualization.
        
        HOW IT WORKS:
            Iterates through all airports' adjacency lists and combines
            them into one flat list.
            
        Returns:
            List of all Route objects in the graph
            
        Example:
            routes = graph.get_all_routes()
            blocked_routes = [r for r in routes if r.blocked]
            print(f"Blocked routes: {len(blocked_routes)}")
        """
        routes: List[Route] = []
        # Flatten the adjacency list: combine all route lists into one
        for route_list in self._adjacency.values():
            routes.extend(route_list)
        return routes
