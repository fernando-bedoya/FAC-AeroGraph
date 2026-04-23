from pathlib import Path

from fastapi import APIRouter, HTTPException

from .loader import load_graph_from_json
from .planner import plan_basic_itinerary, plan_best_route_by_criteria, simulate_dynamic_plan
from .schemas import (
    BasicPlanRequest,
    BestRouteRequest,
    BlockRouteRequest,
    DynamicPlanRequest,
    LoadJsonRequest,
)
from .state import app_state

router = APIRouter()


def _require_graph():
    if app_state.graph is None:
        raise HTTPException(status_code=400, detail="Primero debes cargar un archivo JSON")


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.post("/load")
def load_graph(payload: LoadJsonRequest):
    file_path = Path(payload.file_path)
    if not file_path.is_absolute():
        base = Path(__file__).resolve().parents[1]
        file_path = (base / file_path).resolve()

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"No existe el archivo: {file_path}")

    graph, aircraft_cfg, rules = load_graph_from_json(str(file_path))
    app_state.graph = graph
    app_state.aircraft_cfg = aircraft_cfg
    app_state.rules = rules
    app_state.loaded_file = str(file_path)

    return {
        "message": "Grafo cargado correctamente",
        "airports": len(graph.get_all_airports()),
        "routes": len(graph.get_all_routes()),
        "loaded_file": str(file_path),
    }


@router.get("/graph")
def get_graph_data():
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    airports = [
        {
            "id": airport.id,
            "name": airport.name,
            "city": airport.city,
            "country": airport.country,
            "timezone": airport.timezone,
            "isHub": airport.is_hub,
            "lodgingCost": airport.lodging_cost,
            "foodCost": airport.food_cost,
            "activities": [a.__dict__ for a in airport.activities],
            "jobs": [j.__dict__ for j in airport.jobs],
        }
        for airport in graph.get_all_airports()
    ]

    routes = [
        {
            "origin": route.origin,
            "destination": route.destination,
            "distanceKm": route.distance_km,
            "aircraftTypes": route.aircraft_types,
            "baseCost": route.base_cost,
            "minStayMin": route.min_stay_min,
            "blocked": route.blocked,
        }
        for route in graph.get_all_routes()
    ]

    return {
        "airports": airports,
        "routes": routes,
        "aircraftConfig": {k: v.__dict__ for k, v in app_state.aircraft_cfg.items()},
        "rules": app_state.rules,
        "loadedFile": app_state.loaded_file,
    }


@router.post("/plan/basic")
def basic_plan(payload: BasicPlanRequest):
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    if not graph.get_airport(payload.origin):
        raise HTTPException(status_code=404, detail="Aeropuerto de origen no encontrado")

    result = plan_basic_itinerary(
        graph=graph,
        aircraft_cfg=app_state.aircraft_cfg,
        origin=payload.origin,
        budget_usd=payload.budget_usd,
        time_hours=payload.time_hours,
    )

    return {
        "budget_route": {
            "title": result["budget_route"].title,
            "visited_airports": result["budget_route"].visited_airports,
            "segments": [s.__dict__ for s in result["budget_route"].segments],
            "total_cost": result["budget_route"].total_cost,
            "total_time_min": result["budget_route"].total_time_min,
        },
        "time_route": {
            "title": result["time_route"].title,
            "visited_airports": result["time_route"].visited_airports,
            "segments": [s.__dict__ for s in result["time_route"].segments],
            "total_cost": result["time_route"].total_cost,
            "total_time_min": result["time_route"].total_time_min,
        },
    }


@router.post("/plan/best-route")
def best_route(payload: BestRouteRequest):
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    if not graph.get_airport(payload.origin) or not graph.get_airport(payload.destination):
        raise HTTPException(status_code=404, detail="Origen o destino no existe")

    allowed = [a for a in payload.allowed_aircraft if a in app_state.aircraft_cfg]
    result = plan_best_route_by_criteria(
        graph=graph,
        aircraft_cfg=app_state.aircraft_cfg,
        origin=payload.origin,
        destination=payload.destination,
        criteria=payload.criteria,
        exclude_secondary=payload.exclude_secondary,
        allowed_aircraft=allowed,
    )
    return result


@router.post("/plan/dynamic")
def dynamic_plan(payload: DynamicPlanRequest):
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    if not graph.get_airport(payload.origin):
        raise HTTPException(status_code=404, detail="Aeropuerto de origen no existe")

    result = simulate_dynamic_plan(
        graph=graph,
        aircraft_cfg=app_state.aircraft_cfg,
        origin=payload.origin,
        initial_budget=payload.initial_budget,
        total_time_hours=payload.total_time_hours,
        budget_trigger_percent=app_state.rules.get("budget_trigger_percent", 35),
    )

    return {
        "steps": [s.__dict__ for s in result.steps],
        "visited_airports": result.visited_airports,
        "total_spent": result.total_spent,
        "total_earned": result.total_earned,
        "final_budget": result.final_budget,
    }


@router.post("/route/block")
def block_route(payload: BlockRouteRequest):
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    ok = graph.set_route_blocked(payload.origin, payload.destination, payload.blocked)
    if not ok:
        raise HTTPException(status_code=404, detail="No existe la ruta indicada")

    return {
        "message": "Ruta actualizada",
        "origin": payload.origin,
        "destination": payload.destination,
        "blocked": payload.blocked,
    }
