from pathlib import Path

from fastapi import APIRouter, HTTPException

from .dynamic import (
    choose_dynamic_activities,
    end_dynamic_session,
    get_dynamic_state,
    list_dynamic_activities,
    list_dynamic_flight_options,
    list_dynamic_jobs,
    perform_dynamic_flight,
    perform_dynamic_work,
    start_dynamic_session,
)
from .loader import load_graph_from_json
from .planner import plan_basic_itinerary, plan_best_route_by_criteria
from .schemas import (
    BasicPlanRequest,
    BestRouteRequest,
    BlockRouteRequest,
    DynamicActivitiesRequest,
    DynamicFlyRequest,
    DynamicPlanRequest,
    DynamicStartRequest,
    DynamicWorkRequest,
    LoadJsonRequest,
)
from .state import app_state

router = APIRouter()


def _require_graph():
    if app_state.graph is None:
        raise HTTPException(status_code=400, detail="Primero debes cargar un archivo JSON")


def _dynamic_state_to_dict(state):
    return {
        "session_id": state.session_id,
        "origin": state.origin,
        "current_airport": state.current_airport,
        "initial_budget": state.initial_budget,
        "budget_usd": state.budget_usd,
        "time_left_min": state.time_left_min,
        "total_spent": state.total_spent,
        "total_earned": state.total_earned,
        "visited_airports": state.visited,
        "minutes_since_food": state.minutes_since_food,
        "minutes_since_lodging": state.minutes_since_lodging,
        "stay_min": state.stay_min,
        "required_stay_min": state.required_stay_min,
        "total_distance_km": state.total_distance_km,
        "free_distance_km": state.free_distance_km,
        "steps": [s.__dict__ for s in state.steps],
        "suggested_route": state.suggested_route,
    }


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

    # Get all routes to extract aircraft types by airport
    all_routes = graph.get_all_routes()
    aircraft_by_airport = {}
    
    for route in all_routes:
        if route.origin not in aircraft_by_airport:
            aircraft_by_airport[route.origin] = set()
        for aircraft in route.aircraft_types:
            aircraft_by_airport[route.origin].add(aircraft)

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
            "aircraftTypes": sorted(list(aircraft_by_airport.get(airport.id, []))),
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

    try:
        state = start_dynamic_session(
            graph=graph,
            aircraft_cfg=app_state.aircraft_cfg,
            rules=app_state.rules,
            origin=payload.origin,
            initial_budget=payload.initial_budget,
            total_time_hours=payload.total_time_hours,
            sessions=app_state.dynamic_sessions,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _dynamic_state_to_dict(state)


@router.post("/dynamic/start")
def dynamic_start(payload: DynamicStartRequest):
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    try:
        state = start_dynamic_session(
            graph=graph,
            aircraft_cfg=app_state.aircraft_cfg,
            rules=app_state.rules,
            origin=payload.origin,
            initial_budget=payload.initial_budget,
            total_time_hours=payload.total_time_hours,
            sessions=app_state.dynamic_sessions,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _dynamic_state_to_dict(state)


@router.get("/dynamic/state/{session_id}")
def dynamic_state(session_id: str):
    try:
        state = get_dynamic_state(session_id, app_state.dynamic_sessions)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _dynamic_state_to_dict(state)


@router.get("/dynamic/activities/{session_id}")
def dynamic_activities(session_id: str):
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    try:
        state = get_dynamic_state(session_id, app_state.dynamic_sessions)
        activities = list_dynamic_activities(graph, app_state.rules, state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"activities": activities}


@router.post("/dynamic/activities/{session_id}")
def dynamic_choose_activities(session_id: str, payload: DynamicActivitiesRequest):
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    try:
        state = get_dynamic_state(session_id, app_state.dynamic_sessions)
        updated = choose_dynamic_activities(graph, app_state.rules, state, payload.activities)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _dynamic_state_to_dict(updated)


@router.get("/dynamic/jobs/{session_id}")
def dynamic_jobs(session_id: str):
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    try:
        state = get_dynamic_state(session_id, app_state.dynamic_sessions)
        jobs = list_dynamic_jobs(graph, app_state.rules, state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"jobs": jobs}


@router.post("/dynamic/work/{session_id}")
def dynamic_work(session_id: str, payload: DynamicWorkRequest):
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    try:
        state = get_dynamic_state(session_id, app_state.dynamic_sessions)
        updated = perform_dynamic_work(
            graph,
            app_state.rules,
            state,
            payload.job_name,
            payload.hours,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _dynamic_state_to_dict(updated)


@router.get("/dynamic/flight-options/{session_id}")
def dynamic_flight_options(session_id: str):
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    try:
        state = get_dynamic_state(session_id, app_state.dynamic_sessions)
        options = list_dynamic_flight_options(graph, app_state.aircraft_cfg, state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"options": options}


@router.post("/dynamic/fly/{session_id}")
def dynamic_fly(session_id: str, payload: DynamicFlyRequest):
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    try:
        state = get_dynamic_state(session_id, app_state.dynamic_sessions)
        updated = perform_dynamic_flight(
            graph,
            app_state.aircraft_cfg,
            app_state.rules,
            state,
            payload.destination,
            payload.aircraft,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _dynamic_state_to_dict(updated)


@router.post("/dynamic/finish/{session_id}")
def dynamic_finish(session_id: str):
    try:
        end_dynamic_session(session_id, app_state.dynamic_sessions)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"message": "Sesion dinamica finalizada"}


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
