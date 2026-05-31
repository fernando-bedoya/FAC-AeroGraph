from typing import Dict, List, Optional

from .models import Airport, Route


class Graph:
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

    def get_outgoing_routes(self, airport_id: str) -> List[Route]:
        return self._adjacency.get(airport_id, [])

    def get_route(self, origin: str, destination: str) -> Optional[Route]:
        """Encuentra y devuelve una ruta específica."""
        for route in self.get_outgoing_routes(origin):
            if route.destination == destination:
                return route
        return None

    def is_route_valid(self, origin: str, destination: str) -> bool:
        """Verifica si una ruta existe y no está bloqueada."""
        route = self.get_route(origin, destination)
        return route is not None and not route.blocked

    def toggle_route_status(self, origin: str, destination: str, block: bool) -> Optional[Route]:
        """Bloquea o desbloquea una ruta y devuelve la ruta actualizada."""
        route = self.get_route(origin, destination)
        if route:
            route.blocked = block
            return route
        return None

    def get_all_airports(self) -> List[Airport]:
        return list(self._airports.values())

    def get_all_routes(self) -> List[Route]:
        routes: List[Route] = []
        for route_list in self._adjacency.values():
            routes.extend(route_list)
        return routes
