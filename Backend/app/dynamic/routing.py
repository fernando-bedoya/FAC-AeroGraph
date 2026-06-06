from typing import Dict

from ..algorithms import backtracking_max_coverage
from ..graph import Graph
from ..models import AircraftConfig


def calculate_suggested_route(
    graph: Graph,
    aircraft_cfg: Dict[str, AircraftConfig],
    origin: str,
    initial_budget: float,
    total_time_min: float,
) -> Dict:
    """
    Calcula la ruta óptima sugerida que maximiza destinos con menor gasto.
    
    Utiliza el algoritmo Bellman-Ford de cobertura máxima que:
    1. Maximiza la cantidad de aeropuertos visitados
    2. Minimiza el costo total
    3. Respeta restricciones de presupuesto y tiempo
    """
    try:
        # Calcular ruta optimizada por costo que maximice destinos
        segments = backtracking_max_coverage(
            graph=graph,
            aircraft_cfg=aircraft_cfg,
            origin=origin,
            budget_limit=initial_budget,
            time_limit_min=total_time_min,
            optimize_for="costo",
        )
        
        if not segments:
            return {
                "airports": [origin],
                "segments": [],
                "total_cost": 0.0,
                "total_time_min": 0.0,
                "destination_count": 1,
            }
        
        # Reconstruir la lista de aeropuertos visitados
        visited = [origin]
        total_cost = 0.0
        total_time = 0.0
        
        for segment in segments:
            visited.append(segment.destination)
            total_cost += segment.segment_cost
            total_time += segment.segment_time_min
        
        return {
            "airports": visited,
            "segments": [
                {
                    "origin": s.origin,
                    "destination": s.destination,
                    "aircraft": s.aircraft,
                    "distance_km": s.distance_km,
                    "segment_cost": s.segment_cost,
                    "segment_time_min": s.segment_time_min,
                }
                for s in segments
            ],
            "total_cost": total_cost,
            "total_time_min": total_time,
            "destination_count": len(visited),
        }
    except Exception as e:
        # Si hay error, retornar ruta vacía con solo origen
        return {
            "airports": [origin],
            "segments": [],
            "total_cost": 0.0,
            "total_time_min": 0.0,
            "destination_count": 1,
            "error": str(e),
        }
