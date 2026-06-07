from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from .config import app_state
from .dynamic import (
    choose_dynamic_activities,
    complete_dynamic_flight,
    end_dynamic_session,
    export_report_format,
    generate_final_report,
    get_dynamic_state,
    handle_interruption,
    list_dynamic_activities,
    list_dynamic_flight_options,
    list_dynamic_jobs,
    perform_dynamic_flight,
    perform_dynamic_work,
    start_dynamic_flight,
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
    DynamicStartRequest,
    DynamicWorkRequest,
    InterruptRequest,
    LoadJsonRequest,
)

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
        "in_transit": state.in_transit,
        "transit_from": state.transit_from,
        "transit_to": state.transit_to,
        "transit_aircraft": state.transit_aircraft,
    }


# --- REAL-TIME SIMULATION ENGINE ENDPOINTS (R4) ---

@router.post("/simulation/fly")
def fly(origin: str, destination: str, plan_id: str):
    """
    Approve a flight transition before frontend animation begins.

    Validates that the requested route exists and is not blocked.

    Args:
        origin: Departure airport IATA code.
        destination: Arrival airport IATA code.
        plan_id: Simulation plan identifier.

    Returns:
        Dict with approval message and estimated flight time in minutes.
    """
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    if not graph.is_route_valid(origin, destination):
        return JSONResponse(
            status_code=409,
            content={
                "error": "Route is blocked or does not exist.",
                "from": origin,
                "to": destination
            }
        )

    route = graph.get_route(origin, destination)
    if not route:
        return JSONResponse(status_code=404, content={"error": "Route not found"})

    planner = app_state.planner
    assert planner is not None
    aircraft = planner.get_default_aircraft()
    segment_time = planner.calculate_segment_time(route.distance_km, aircraft)

    return {
        "message": "Flight approved. You can start the animation.",
        "estimated_time_min": segment_time
    }


@router.post("/simulation/arrive")
def arrive(destination: str, plan_id: str):
    """
    Confirm arrival at a destination after frontend animation completes.

    Args:
        destination: Arrival airport IATA code.
        plan_id: Simulation plan identifier.

    Returns:
        Dict with confirmation message.
    """
    return {
        "message": f"Arrival at {destination} confirmed.",
    }


@router.post("/simulation/interrupt")
def interrupt(payload: InterruptRequest):
    """
    Handle a route interruption during an active dynamic session.

    Blocks the route in the graph, detects whether the traveller is
    mid-flight on that route, redirects them if necessary, and
    recalculates available alternatives.

    Args:
        payload: InterruptRequest with session_id, origin, destination.

    Returns:
        Dict with interruption result, redirection info, and updated state.
    """
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    try:
        state = get_dynamic_state(payload.session_id, app_state.dynamic_sessions)
        result = handle_interruption(
            graph=graph,
            aircraft_cfg=app_state.aircraft_cfg,
            state=state,
            origin=payload.origin,
            destination=payload.destination,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "message": "Interrupción procesada.",
        **result,
        "state": _dynamic_state_to_dict(state),
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


@router.post("/config/aircraft")
def update_aircraft_config(payload: dict):
    """Update aircraft configuration (cost per km and time per km)."""
    _require_graph()
    
    for aircraft_name, config in payload.items():
        if aircraft_name in app_state.aircraft_cfg:
            if "costoKm" in config:
                app_state.aircraft_cfg[aircraft_name].cost_per_km = float(config["costoKm"])
            if "tiempoKm" in config:
                app_state.aircraft_cfg[aircraft_name].time_per_km = float(config["tiempoKm"])
    
    return {
        "message": "Configuracion actualizada",
        "aircraftConfig": {k: v.__dict__ for k, v in app_state.aircraft_cfg.items()},
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
            "lat": airport.lat,
            "lon": airport.lon,
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


@router.post("/dynamic/start")
def dynamic_start(payload: DynamicStartRequest):
    """
    Start a new dynamic planning session (R2.3).

    Creates a session with the given origin, budget, and time, calculates
    the optimal suggested route, and returns the initial session state.

    Args:
        payload: DynamicStartRequest with origin, initial_budget, total_time_hours.

    Returns:
        Complete session state dictionary.
    """
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
    """
    Get the current state of a dynamic planning session.

    Args:
        session_id: UUID of the session.

    Returns:
        Complete session state dictionary.
    """
    try:
        state = get_dynamic_state(session_id, app_state.dynamic_sessions)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _dynamic_state_to_dict(state)


@router.get("/dynamic/activities/{session_id}")
def dynamic_activities(session_id: str):
    """
    List optional activities available at the traveller's current airport (R2.3.a).

    Args:
        session_id: UUID of the session.

    Returns:
        Dict with "activities" list, each with name, kind, duration_min,
        cost_usd, and affordable flag.
    """
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
    """
    Apply selected optional activities to the session (R2.3.a).

    Deducts cost and time for each chosen activity.

    Args:
        session_id: UUID of the session.
        payload: DynamicActivitiesRequest with list of activity names.

    Returns:
        Updated session state dictionary.
    """
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
    """
    List temporary jobs available at the traveller's current airport (R2.3.b).

    Only returns jobs when budget is below the eligibility threshold.

    Args:
        session_id: UUID of the session.

    Returns:
        Dict with "jobs" list, each with name, hourly_rate, max_hours.
    """
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
    """
    Perform temporary work to earn income (R2.3.b).

    Advances time, credits income, and applies any triggered
    mandatory food/lodging costs.

    Args:
        session_id: UUID of the session.
        payload: DynamicWorkRequest with job_name and hours.

    Returns:
        Updated session state dictionary.
    """
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
    """
    List available flight options from the traveller's current airport (R2.3.c).

    Filters blocked routes and visited destinations.

    Args:
        session_id: UUID of the session.

    Returns:
        Dict with "options" list, each with origin, destination, aircraft,
        distance_km, segment_cost, segment_time_min, min_stay_min, subsidized.
    """
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
    """
    Execute a complete flight in a single step (R2.3.c).

    Applies all costs, updates location, and clears transit state
    atomically. Use this endpoint when no frontend animation is needed.

    Args:
        session_id: UUID of the session.
        payload: DynamicFlyRequest with destination and aircraft.

    Returns:
        Updated session state dictionary.
    """
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


@router.post("/dynamic/fly/start/{session_id}")
def dynamic_fly_start(session_id: str, payload: DynamicFlyRequest):
    """
    Initiate a flight (Phase 1 of the two-phase protocol, R2.3.c).

    Validates and marks the traveller as in-transit without applying
    costs. The frontend then runs the globe animation before calling
    /dynamic/fly/arrive to complete the flight.

    Args:
        session_id: UUID of the session.
        payload: DynamicFlyRequest with destination and aircraft.

    Returns:
        Updated session state with in_transit flags set.
    """
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    try:
        state = get_dynamic_state(session_id, app_state.dynamic_sessions)
        updated = start_dynamic_flight(
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


@router.post("/dynamic/fly/arrive/{session_id}")
def dynamic_fly_arrive(session_id: str):
    """
    Complete an in-progress flight (Phase 2 of the two-phase protocol, R2.3.c).

    Called after the frontend animation finishes. Applies flight cost
    and time, updates location, and clears transit state.

    Args:
        session_id: UUID of the session.

    Returns:
        Updated session state dictionary.
    """
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    try:
        state = get_dynamic_state(session_id, app_state.dynamic_sessions)
        updated = complete_dynamic_flight(
            graph,
            app_state.aircraft_cfg,
            app_state.rules,
            state,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _dynamic_state_to_dict(updated)


@router.post("/dynamic/finish/{session_id}")
def dynamic_finish(session_id: str):
    """
    End a dynamic planning session and release its resources.

    Args:
        session_id: UUID of the session to finish.

    Returns:
        Confirmation message.
    """
    try:
        end_dynamic_session(session_id, app_state.dynamic_sessions)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"message": "Sesion dinamica finalizada"}


@router.get("/dynamic/report/{session_id}")
def dynamic_report(session_id: str):
    """
    Generate the final trip report for a completed session (R2.5).

    Aggregates all steps into structured sections: destinations,
    flights, activities, jobs, mandatory fees, and financial totals.

    Args:
        session_id: UUID of the session.

    Returns:
        Complete report dictionary.
    """
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    try:
        state = get_dynamic_state(session_id, app_state.dynamic_sessions)
        report = generate_final_report(graph, state)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return report


@router.get("/dynamic/report/export/{session_id}")
def dynamic_report_export(session_id: str, format: str = "csv"):
    """
    Export the final trip report in JSON or CSV format (R2.5).

    Triggers a file download with the specified format.

    Args:
        session_id: UUID of the session.
        format: Output format ("csv" or "json"), defaults to "csv".

    Returns:
        File download response.
    """
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    try:
        state = get_dynamic_state(session_id, app_state.dynamic_sessions)
        report = generate_final_report(graph, state)
        exported_data = export_report_format(report, format)
        
        headers = {}
        if format.lower() == "csv":
            headers["Content-Disposition"] = 'attachment; filename="report.csv"'
            media_type = "text/csv"
        else:
            headers["Content-Disposition"] = 'attachment; filename="report.json"'
            media_type = "application/json"
            
        from fastapi import Response
        return Response(content=exported_data, media_type=media_type, headers=headers)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/route/block")
def block_route(payload: BlockRouteRequest):
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    route = graph.toggle_route_status(payload.origin, payload.destination, payload.blocked)
    if route is None:
        raise HTTPException(status_code=404, detail="No existe la ruta indicada")

    return {
        "message": "Ruta actualizada",
        "origin": payload.origin,
        "destination": payload.destination,
        "blocked": route.blocked,
    }
