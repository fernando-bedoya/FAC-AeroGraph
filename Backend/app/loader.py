import json
from typing import Dict, Tuple

from .graph import DirectedGraph
from .models import (
    Activity,
    Airport,
    AircraftConfig,
    DEFAULT_AIRCRAFT,
    Job,
    Route,
)


def _normalize_aircraft_name(name: str) -> str:
    normalized = name.strip()
    if normalized.lower() == "avion comercial":
        return "Avion Comercial"
    if normalized.lower() == "avion regional":
        return "Avion Regional"
    if normalized.lower() == "helice":
        return "Helice"
    return normalized


def load_graph_from_json(path: str) -> Tuple[DirectedGraph, Dict[str, AircraftConfig], Dict[str, float]]:
    with open(path, "r", encoding="utf-8") as file:
        raw = json.load(file)

    graph = DirectedGraph()

    for node in raw.get("nodos", []):
        activities = [
            Activity(
                name=item["nombre"],
                kind=item["tipo"],
                duration_min=int(item["duracionMin"]),
                cost_usd=float(item["costoUSD"]),
            )
            for item in node.get("actividades", [])
        ]
        jobs = [
            Job(
                name=item["nombre"],
                hourly_rate=float(item["tarifaHora"]),
                max_hours=int(item["maxHoras"]),
            )
            for item in node.get("trabajos", [])
        ]
        airport = Airport(
            id=node["id"],
            name=node["nombre"],
            city=node["ciudad"],
            country=node["pais"],
            timezone=node["zonaHoraria"],
            is_hub=bool(node["esHub"]),
            lodging_cost=float(node["costoAlojamiento"]),
            food_cost=float(node["costoAlimentacion"]),
            activities=activities,
            jobs=jobs,
        )
        graph.add_airport(airport)

    for edge in raw.get("aristas", []):
        route = Route(
            origin=edge["origen"],
            destination=edge["destino"],
            distance_km=float(edge["distanciaKm"]),
            aircraft_types=[_normalize_aircraft_name(t) for t in edge.get("aeronaves", [])],
            base_cost=float(edge.get("costoBase", 1)),
            min_stay_min=int(edge.get("estanciaMinima", 0)),
        )
        graph.add_route(route)

    aircraft_cfg: Dict[str, AircraftConfig] = dict(DEFAULT_AIRCRAFT)
    custom_aircraft = raw.get("config", {}).get("aeronaves", {})
    for name, cfg in custom_aircraft.items():
        n_name = _normalize_aircraft_name(name)
        aircraft_cfg[n_name] = AircraftConfig(
            name=n_name,
            cost_per_km=float(cfg.get("costoKm", DEFAULT_AIRCRAFT.get(n_name, DEFAULT_AIRCRAFT["Avion Comercial"]).cost_per_km)),
            time_per_km=float(cfg.get("tiempoKm", DEFAULT_AIRCRAFT.get(n_name, DEFAULT_AIRCRAFT["Avion Comercial"]).time_per_km)),
        )

    rules = {
        "budget_trigger_percent": float(raw.get("config", {}).get("presupuestoMinimoPorc", 35)),
        "lodging_interval_h": float(raw.get("config", {}).get("intervaloAlojamiento", 20)),
        "food_interval_h": float(raw.get("config", {}).get("intervaloAlimentacion", 8)),
    }

    return graph, aircraft_cfg, rules
