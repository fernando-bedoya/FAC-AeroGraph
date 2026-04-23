from typing import Dict, List, Optional

from .models import Airport, Route


class DirectedGraph:
    """Grafo dirigido con lista de adyacencia implementada manualmente."""

    def __init__(self) -> None:
        self._airports: Dict[str, Airport] = {}
        self._adjacency: Dict[str, List[Route]] = {}

    def add_airport(self, airport: Airport) -> None:
        self._airports[airport.id] = airport
        if airport.id not in self._adjacency:
            self._adjacency[airport.id] = []

    def add_route(self, route: Route) -> None:
        if route.origin not in self._adjacency:
            self._adjacency[route.origin] = []
        self._adjacency[route.origin].append(route)

    def get_airport(self, airport_id: str) -> Optional[Airport]:
        return self._airports.get(airport_id)

    def get_all_airports(self) -> List[Airport]:
        return list(self._airports.values())

    def get_outgoing_routes(self, airport_id: str) -> List[Route]:
        return self._adjacency.get(airport_id, [])

    def get_all_routes(self) -> List[Route]:
        routes: List[Route] = []
        for route_list in self._adjacency.values():
            routes.extend(route_list)
        return routes

    def set_route_blocked(self, origin: str, destination: str, blocked: bool) -> bool:
        found = False
        for route in self._adjacency.get(origin, []):
            if route.destination == destination:
                route.blocked = blocked
                found = True
        return found
