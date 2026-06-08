"""
REST API Routes

This module defines all the HTTP endpoints (routes) for the SkyRoute Planner API.
Each endpoint handles a specific operation like loading a graph, planning a route,
or managing a dynamic planning session.

API STRUCTURE:
    All routes are prefixed with /api when registered in main.py.
    For example: @router.post("/load") becomes POST /api/load

ENDPOINT CATEGORIES:
    1. Graph Management: /load, /graph, /config/aircraft, /route/block
    2. Route Planning: /plan/basic, /plan/best-route
    3. Dynamic Sessions: /dynamic/start, /dynamic/state, /dynamic/finish
    4. Dynamic Actions: /dynamic/activities, /dynamic/work, /dynamic/fly
    5. Reports: /dynamic/report, /dynamic/report/export
    6. Simulation: /simulation/fly, /simulation/arrive, /simulation/interrupt
    7. Health: /health

HOW FASTAPI ROUTING WORKS:
    1. Client sends HTTP request (e.g., POST /api/load)
    2. FastAPI matches the request to the appropriate route function
    3. Pydantic validates the request body against the schema
    4. The route function executes and returns a response
    5. FastAPI converts the response to JSON and sends it back
"""

import platform
import subprocess
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

# Create the API router
# WHY APIRouter: It allows us to define routes in a separate file and
# include them in the main app with a prefix (/api)
router = APIRouter()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _require_graph():
    """
    Check if a graph has been loaded before processing a request.
    
    WHY THIS FUNCTION:
        Most endpoints require a graph to be loaded first. Instead of
        repeating the same check in every endpoint, we use this helper.
        
    Raises:
        HTTPException: 400 error if no graph is loaded
    """
    if app_state.graph is None:
        raise HTTPException(status_code=400, detail="You must load a JSON file first")


def _dynamic_state_to_dict(state):
    """
    Convert a DynamicState object to a dictionary for JSON serialization.
    
    WHY THIS FUNCTION:
        Pydantic models and dataclasses can't be directly converted to JSON.
        We need to manually convert them to dictionaries first.
        
    Args:
        state: DynamicState object from a dynamic planning session
        
    Returns:
        Dictionary with all state properties, ready for JSON serialization
    """
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


# =============================================================================
# SIMULATION ENDPOINTS (Real-time flight simulation)
# =============================================================================

@router.post("/simulation/fly")
def fly(origin: str, destination: str, plan_id: str):
    """
    Approve a flight transition before frontend animation begins.
    
    This endpoint validates that the requested route exists and is not blocked.
    The frontend calls this BEFORE starting the flight animation.
    
    TWO-PHASE FLIGHT PROTOCOL:
        1. Frontend calls /simulation/fly to get approval
        2. Frontend runs the animation
        3. Frontend calls /simulation/arrive to confirm completion
        
    WHY TWO PHASES:
        This allows the frontend to show the animation while the backend
        tracks the flight state. If the route is blocked mid-animation,
        the interruption system can redirect the traveler.
    
    Args:
        origin: Departure airport IATA code
        destination: Arrival airport IATA code
        plan_id: Simulation plan identifier
        
    Returns:
        Dict with approval message and estimated flight time in minutes
    """
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    # Check if route exists and is not blocked
    if not graph.is_route_valid(origin, destination):
        return JSONResponse(
            status_code=409,  # 409 = Conflict
            content={
                "error": "Route is blocked or does not exist.",
                "from": origin,
                "to": destination
            }
        )

    route = graph.get_route(origin, destination)
    if not route:
        return JSONResponse(status_code=404, content={"error": "Route not found"})

    # Calculate estimated flight time
    # Note: This uses a simplified calculation. The actual time depends on aircraft type.
    return {
        "message": "Flight approved. You can start the animation.",
        "estimated_time_min": route.distance_km * 0.7  # Default: 0.7 min per km
    }


@router.post("/simulation/arrive")
def arrive(destination: str, plan_id: str):
    """
    Confirm arrival at a destination after frontend animation completes.
    
    This is Phase 2 of the two-phase flight protocol.
    Called after the frontend animation finishes.
    
    Args:
        destination: Arrival airport IATA code
        plan_id: Simulation plan identifier
        
    Returns:
        Dict with confirmation message
    """
    return {
        "message": f"Arrival at {destination} confirmed.",
    }


@router.post("/simulation/interrupt")
def interrupt(payload: InterruptRequest):
    """
    Handle a route interruption during an active dynamic session.
    
    This endpoint is called when a route is blocked while a traveler
    might be in transit. It:
    1. Blocks the route in the graph
    2. Checks if the traveler is mid-flight on that route
    3. If yes, redirects them back to the origin airport
    4. Recalculates available flight options
    5. Recalculates the suggested route
    
    Args:
        payload: InterruptRequest with session_id, origin, destination
        
    Returns:
        Dict with interruption result, redirection info, and updated state
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
        "message": "Interruption processed.",
        **result,
        "state": _dynamic_state_to_dict(state),
    }


@router.get("/health")
def health_check():
    """
    Health check endpoint.
    
    Used by monitoring systems and load balancers to verify the server is running.
    Returns a simple "ok" status.
    """
    return {"status": "ok"}


# =============================================================================
# FILE DIALOG HELPER
# =============================================================================

def _open_file_dialog() -> str:
    """
    Open the native file dialog to select a JSON file.
    
    This function detects the operating system and uses the appropriate
    native tool to open a file selection dialog:
    - Linux: zenity (GTK dialog tool)
    - Windows: PowerShell with OpenFileDialog
    - macOS: osascript with AppleScript
    
    WHY NATIVE DIALOG:
        Using the native file dialog provides a familiar experience for users
        and allows them to browse their file system naturally.
    
    Returns:
        str: Absolute path to the selected file
        
    Raises:
        HTTPException: If the user cancels the selection or the tool is unavailable
    """
    system = platform.system()

    if system == "Linux":
        # zenity: Native GTK dialog tool for Linux
        # --file-selection: Opens the file picker
        # --file-filter: Filters to show only .json files
        result = subprocess.run(
            ["zenity", "--file-selection", "--title=Select JSON file", "--file-filter=JSON Files | *.json"],
            capture_output=True,
            text=True,
        )
        # Exit code 1 means user cancelled
        if result.returncode != 0:
            raise HTTPException(status_code=400, detail="File selection cancelled")
        return result.stdout.strip()

    elif system == "Windows":
        # PowerShell: Native Windows shell
        # Creates an OpenFileDialog with filter for .json files
        script = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "$dialog = New-Object System.Windows.Forms.OpenFileDialog; "
            "$dialog.Filter = 'JSON Files (*.json)|*.json'; "
            "$dialog.Title = 'Select JSON file'; "
            "if ($dialog.ShowDialog() -eq 'OK') { Write-Output $dialog.FileName }"
        )
        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not result.stdout.strip():
            raise HTTPException(status_code=400, detail="File selection cancelled")
        return result.stdout.strip()

    elif system == "Darwin":
        # macOS: osascript runs AppleScript
        # 'choose file' opens the native macOS file picker
        # 'of type "json"' filters to show only .json files
        script = 'choose file of type "json" with prompt "Select JSON file"'
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise HTTPException(status_code=400, detail="File selection cancelled")
        # AppleScript returns path in "alias Macintosh HD:path:to:file.json" format
        # We need to convert it to POSIX format (/path/to/file.json)
        alias_path = result.stdout.strip()
        conversion = subprocess.run(
            ["osascript", "-e", f'POSIX path of "{alias_path}"'],
            capture_output=True,
            text=True,
        )
        return conversion.stdout.strip()

    else:
        raise HTTPException(status_code=500, detail=f"Unsupported operating system: {system}")


# =============================================================================
# GRAPH MANAGEMENT ENDPOINTS
# =============================================================================

@router.post("/load")
def load_graph(payload: LoadJsonRequest):
    """
    Load the airline route graph from a JSON file.
    
    This is the first endpoint that must be called before any other
    graph-dependent endpoints can work.
    
    HOW IT WORKS:
        1. If file_path is provided, use it directly
        2. If file_path is not provided, open native file dialog
        3. Parse the JSON file and create the graph
        4. Store the graph, aircraft config, and rules in app state
        
    Args:
        payload: LoadJsonRequest with optional file_path
        
    Returns:
        Dict with success message, number of airports/routes, and file path
    """
    # If no path provided, open native file dialog
    if not payload.file_path:
        file_path_str = _open_file_dialog()
    else:
        file_path_str = payload.file_path

    file_path = Path(file_path_str)
    # Convert relative paths to absolute (relative to Backend/ directory)
    if not file_path.is_absolute():
        base = Path(__file__).resolve().parents[1]
        file_path = (base / file_path).resolve()

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    # Parse JSON and populate app state
    graph, aircraft_cfg, rules = load_graph_from_json(str(file_path))
    app_state.graph = graph
    app_state.aircraft_cfg = aircraft_cfg
    app_state.rules = rules
    app_state.loaded_file = str(file_path)

    return {
        "message": "Graph loaded successfully",
        "airports": len(graph.get_all_airports()),
        "routes": len(graph.get_all_routes()),
        "loaded_file": str(file_path),
    }


@router.post("/config/aircraft")
def update_aircraft_config(payload: dict):
    """
    Update aircraft configuration (cost per km and time per km).
    
    This allows the user to customize how much each aircraft type
    costs and how fast it flies. Changes affect all future calculations.
    
    Args:
        payload: Dictionary mapping aircraft names to their new config
                Example: {"Avion Comercial": {"costoKm": 0.20, "tiempoKm": 0.8}}
                
    Returns:
        Dict with success message and updated aircraft configurations
    """
    _require_graph()
    
    # Update each aircraft's configuration
    for aircraft_name, config in payload.items():
        if aircraft_name in app_state.aircraft_cfg:
            if "costoKm" in config:
                app_state.aircraft_cfg[aircraft_name].cost_per_km = float(config["costoKm"])
            if "tiempoKm" in config:
                app_state.aircraft_cfg[aircraft_name].time_per_km = float(config["tiempoKm"])
    
    return {
        "message": "Configuration updated",
        "aircraftConfig": {k: v.__dict__ for k, v in app_state.aircraft_cfg.items()},
    }


@router.get("/graph")
def get_graph_data():
    """
    Get the complete graph data (airports and routes).
    
    This endpoint returns all the data needed to render the graph
    visualization on the frontend, including:
    - All airports with their properties
    - All routes with their properties
    - Aircraft configurations
    - Game rules
    
    Returns:
        Dict with airports, routes, aircraftConfig, rules, and loadedFile
    """
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    # Build a mapping of aircraft types available at each airport
    # This is used by the frontend to show which aircraft can be used where
    all_routes = graph.get_all_routes()
    aircraft_by_airport = {}
    
    for route in all_routes:
        if route.origin not in aircraft_by_airport:
            aircraft_by_airport[route.origin] = set()
        for aircraft in route.aircraft_types:
            aircraft_by_airport[route.origin].add(aircraft)

    # Convert airports to dictionaries for JSON serialization
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

    # Convert routes to dictionaries for JSON serialization
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


# =============================================================================
# ROUTE PLANNING ENDPOINTS
# =============================================================================

@router.post("/plan/basic")
def basic_plan(payload: BasicPlanRequest):
    """
    Create a basic itinerary with two alternative routes (R2.2).
    
    Returns two routes:
    1. Maximum destinations within budget
    2. Maximum destinations within time limit
    
    Args:
        payload: BasicPlanRequest with origin, budget_usd, time_hours
        
    Returns:
        Dict with budget_route and time_route
    """
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    if not graph.get_airport(payload.origin):
        raise HTTPException(status_code=404, detail="Origin airport not found")

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
    """
    Find the best route between two airports for each criterion (R2.2).
    
    Uses Dijkstra's algorithm to find optimal routes by distance, time, or cost.
    
    Args:
        payload: BestRouteRequest with origin, destination, criteria, etc.
        
    Returns:
        Dict mapping each criterion to its optimal route
    """
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    if not graph.get_airport(payload.origin) or not graph.get_airport(payload.destination):
        raise HTTPException(status_code=404, detail="Origin or destination does not exist")

    # Filter allowed aircraft to only include known types
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


# =============================================================================
# DYNAMIC PLANNING ENDPOINTS (R2.3)
# =============================================================================

@router.post("/dynamic/start")
def dynamic_start(payload: DynamicStartRequest):
    """
    Start a new dynamic planning session (R2.3).
    
    A dynamic session allows interactive trip planning where the user
    makes decisions step by step: choose activities, work, fly, etc.
    
    The session starts with:
    - Initial budget and time
    - A suggested route (calculated using backtracking)
    - The traveler at the origin airport
    
    Args:
        payload: DynamicStartRequest with origin, initial_budget, total_time_hours
        
    Returns:
        Complete session state dictionary
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
    
    The frontend calls this to refresh the UI with the latest state.
    
    Args:
        session_id: UUID of the session
        
    Returns:
        Complete session state dictionary
    """
    try:
        state = get_dynamic_state(session_id, app_state.dynamic_sessions)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _dynamic_state_to_dict(state)


@router.get("/dynamic/activities/{session_id}")
def dynamic_activities(session_id: str):
    """
    List optional activities available at the traveler's current airport (R2.3.a).
    
    Activities are tourist options like tours, museums, etc.
    Each activity has a cost and duration.
    
    Args:
        session_id: UUID of the session
        
    Returns:
        Dict with "activities" list
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
    May trigger mandatory food/lodging costs if time thresholds are crossed.
    
    Args:
        session_id: UUID of the session
        payload: DynamicActivitiesRequest with list of activity names
        
    Returns:
        Updated session state dictionary
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
    List temporary jobs available at the traveler's current airport (R2.3.b).
    
    Jobs are only returned when the traveler's budget is below 35% of
    the initial budget. This is the work eligibility threshold.
    
    Args:
        session_id: UUID of the session
        
    Returns:
        Dict with "jobs" list
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
        session_id: UUID of the session
        payload: DynamicWorkRequest with job_name and hours
        
    Returns:
        Updated session state dictionary
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
    List available flight options from the traveler's current airport (R2.3.c).
    
    Filters out blocked routes and already-visited destinations.
    For each option, calculates the segment cost (including 20% subsidy cap check).
    
    Args:
        session_id: UUID of the session
        
    Returns:
        Dict with "options" list
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
    
    This is the single-phase flight option (no animation).
    Applies all costs, updates location, and clears transit state atomically.
    
    For animated flights, use /dynamic/fly/start and /dynamic/fly/arrive instead.
    
    Args:
        session_id: UUID of the session
        payload: DynamicFlyRequest with destination and aircraft
        
    Returns:
        Updated session state dictionary
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
    
    Validates and marks the traveler as in-transit WITHOUT applying costs.
    The frontend then runs the globe animation before calling
    /dynamic/fly/arrive to complete the flight.
    
    TWO-PHASE PROTOCOL:
        1. /dynamic/fly/start - Mark as in-transit (no cost yet)
        2. Frontend runs animation
        3. /dynamic/fly/arrive - Apply costs and complete flight
        
    WHY TWO PHASES:
        This allows the frontend to show the animation while the backend
        tracks the flight state. If the route is blocked mid-animation,
        the interruption system can redirect the traveler.
    
    Args:
        session_id: UUID of the session
        payload: DynamicFlyRequest with destination and aircraft
        
    Returns:
        Updated session state with in_transit flags set
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
        session_id: UUID of the session
        
    Returns:
        Updated session state dictionary
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
    
    Removes the session from the active sessions dictionary.
    After this, the session_id is no longer valid.
    
    Args:
        session_id: UUID of the session to finish
        
    Returns:
        Confirmation message
    """
    try:
        end_dynamic_session(session_id, app_state.dynamic_sessions)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"message": "Dynamic session finished"}


# =============================================================================
# REPORT ENDPOINTS (R2.5)
# =============================================================================

@router.get("/dynamic/report/{session_id}")
def dynamic_report(session_id: str):
    """
    Generate the final trip report for a completed session (R2.5).
    
    Aggregates all steps into structured sections:
    - Destinations visited with stay times and costs
    - Flight segments with details
    - Optional activities performed
    - Work assignments with earnings
    - Mandatory food/lodging fees
    - Financial totals
    
    Args:
        session_id: UUID of the session
        
    Returns:
        Complete report dictionary
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
        session_id: UUID of the session
        format: Output format ("csv" or "json"), defaults to "csv"
        
    Returns:
        File download response
    """
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    try:
        state = get_dynamic_state(session_id, app_state.dynamic_sessions)
        report = generate_final_report(graph, state)
        exported_data = export_report_format(report, format)
        
        # Set headers for file download
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


# =============================================================================
# ROUTE BLOCKING ENDPOINT (R2.4)
# =============================================================================

@router.post("/route/block")
def block_route(payload: BlockRouteRequest):
    """
    Block or unblock a route (R2.4).
    
    Blocking a route simulates real-world disruptions like weather
    or mechanical issues. Blocked routes cannot be used until unblocked.
    
    If a traveler is in transit on a blocked route, the interruption
    system will redirect them.
    
    Args:
        payload: BlockRouteRequest with origin, destination, blocked
        
    Returns:
        Dict with success message and updated route status
    """
    _require_graph()
    graph = app_state.graph
    assert graph is not None

    route = graph.toggle_route_status(payload.origin, payload.destination, payload.blocked)
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")

    return {
        "message": "Route updated",
        "origin": payload.origin,
        "destination": payload.destination,
        "blocked": route.blocked,
    }
