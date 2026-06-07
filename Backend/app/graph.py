"""
Graph data structure implementation using adjacency list.

This module implements a directed weighted graph to represent airline routes
between airports. Each airport is a node and each route is a directed edge
with weights for distance, cost, and time.
"""

from typing import Dict, List, Optional

from .models import Airport, Route


class Graph:
    """
    Directed weighted graph using adjacency list representation.
    
    This graph structure stores airports as nodes and routes as directed edges.
    The adjacency list maps each airport code to its list of outgoing routes.
    
    Attributes:
        _airports: Dictionary mapping airport IATA codes to Airport objects
        _adjacency: Dictionary mapping airport codes to lists of outgoing routes
    """

    def __init__(self) -> None:
        """Initialize an empty graph with no airports or routes."""
        self._airports: Dict[str, Airport] = {}
        self._adjacency: Dict[str, List[Route]] = {}

    def add_airport(self, airport: Airport) -> None:
        """
        Add an airport node to the graph.
        
        Args:
            airport: Airport object to add to the graph
        """
        self._airports[airport.id] = airport
        if airport.id not in self._adjacency:
            self._adjacency[airport.id] = []

    def add_route(self, route: Route) -> None:
        """
        Add a directed route (edge) to the graph.
        
        Args:
            route: Route object representing a directed edge from origin to destination
        """
        if route.origin not in self._adjacency:
            self._adjacency[route.origin] = []
        self._adjacency[route.origin].append(route)

    def get_airport(self, airport_id: str) -> Optional[Airport]:
        """
        Get airport by IATA code.
        
        Args:
            airport_id: Three-letter IATA airport code (e.g., 'BOG', 'LIM')
            
        Returns:
            Airport object if found, None otherwise
        """
        return self._airports.get(airport_id)

    def get_outgoing_routes(self, airport_id: str) -> List[Route]:
        """
        Get all outgoing routes from an airport.
        
        Args:
            airport_id: Three-letter IATA airport code
            
        Returns:
            List of Route objects representing outgoing flights
        """
        return self._adjacency.get(airport_id, [])

    def get_route(self, origin: str, destination: str) -> Optional[Route]:
        """
        Find and return a specific route between two airports.
        
        Args:
            origin: Origin airport IATA code
            destination: Destination airport IATA code
            
        Returns:
            Route object if found, None otherwise
        """
        for route in self.get_outgoing_routes(origin):
            if route.destination == destination:
                return route
        return None

    def is_route_valid(self, origin: str, destination: str) -> bool:
        """
        Check if a route exists and is not blocked.
        
        Args:
            origin: Origin airport IATA code
            destination: Destination airport IATA code
            
        Returns:
            True if route exists and is not blocked, False otherwise
        """
        route = self.get_route(origin, destination)
        return route is not None and not route.blocked

    def toggle_route_status(self, origin: str, destination: str, block: bool) -> Optional[Route]:
        """
        Block or unblock a route and return the updated route.
        
        Args:
            origin: Origin airport IATA code
            destination: Destination airport IATA code
            block: True to block the route, False to unblock
            
        Returns:
            Updated Route object if found, None otherwise
        """
        route = self.get_route(origin, destination)
        if route:
            route.blocked = block
            return route
        return None

    def get_all_airports(self) -> List[Airport]:
        """Get list of all airports in the graph."""
        return list(self._airports.values())

    def get_all_routes(self) -> List[Route]:
        """Get a flat list of all routes (edges) in the graph."""
        routes: List[Route] = []
        for route_list in self._adjacency.values():
            routes.extend(route_list)
        return routes
