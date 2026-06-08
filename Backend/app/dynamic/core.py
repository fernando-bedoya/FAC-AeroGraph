"""
Core Engine for Dynamic Planning (Requirement 2.3)

This module implements the central budget and time management logic for
the dynamic planning system. It handles:

1. ACTION VALIDATION: Check if an action can be performed
   - Is there enough time?
   - Is there enough budget (including projected mandatory costs)?

2. TIME ADVANCEMENT: Move the session clock forward
   - Track minutes since last food/lodging
   - Trigger mandatory events when thresholds are crossed

3. COST CALCULATION: Calculate costs for actions
   - Flight costs based on distance and aircraft
   - Subsidized route 20% cap enforcement

4. WORK ELIGIBILITY: Determine if traveler can work
   - Work only available when budget < 35% of initial

KEY CONCEPTS:
    - Mandatory Events: Food (every 8h) and lodging (every 20h) are
      automatically applied when time thresholds are crossed
    - Subsidized Routes: Routes with base_cost=0 are free, but total
      free distance cannot exceed 20% of total distance
    - Work Eligibility: Traveler can only work when budget is low

USAGE:
    Other modules (activities.py, jobs.py, flights.py) call functions
    from this module to apply costs, advance time, and validate actions.
"""

from typing import Dict, List, Optional, Tuple, Any

from ..graph import Graph
from ..models import AircraftConfig, DynamicStep
from .models import DynamicState


class DynamicPlanError(ValueError):
    """
    Exception raised for dynamic planning validation failures.
    
    This exception is raised when an action cannot be performed due to:
    - Insufficient budget
    - Insufficient time
    - Invalid action parameters
    - Subsidized route limit breach
    
    The API catches this exception and returns a 400 error to the client.
    """
    pass


def apply_cost_and_time(
    state: DynamicState,
    rules: Dict[str, float],
    cost_usd: float,
    duration_min: float,
    cost_airport,
    count_stay: bool,
    action_label: str,
    detail: str,
    step_airport_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Apply a monetary cost and time duration for an action.
    
    This is the main function for processing actions that cost both
    money AND time (like flights and activities). It:
    
    1. Validates the action can be performed
    2. Deducts the cost from budget
    3. Advances the session clock
    4. Logs the action as a DynamicStep
    5. Applies any triggered mandatory events (food/lodging)
    
    WHY THIS FUNCTION:
        This centralizes all the logic for applying costs and time,
        ensuring consistency across all action types.
    
    Args:
        state: Current dynamic session state (mutated in-place)
        rules: System rules dict (intervals, budget trigger)
        cost_usd: Monetary cost of the action in USD
        duration_min: Duration of the action in minutes
        cost_airport: Airport object whose food/lodging costs apply
                      (used for mandatory event calculations)
        count_stay: Whether the duration counts toward airport stay time
                    Activities count, flights don't
        action_label: Short label for the step log
                     Examples: "vuelo", "actividad", "tiempo_libre"
        detail: Human-readable description of the action
        step_airport_id: Airport to associate with the step
                        Default: current airport
        metadata: Additional structured data to attach to the step
        
    Raises:
        DynamicPlanError: If budget or time is insufficient
    """
    # Step 1: Validate the action can be performed
    validate_action(state, rules, duration_min, cost_usd, cost_airport)

    # Step 2: Deduct cost from budget
    state.budget_usd -= cost_usd
    state.total_spent += cost_usd
    
    # Step 3: Advance time and get any triggered mandatory events
    time_left_after_action, mandatory_events = advance_time(
        state, rules, duration_min, cost_airport, count_stay
    )

    # Step 4: Log the action as a DynamicStep
    step_airport = step_airport_id or state.current_airport
    state.steps.append(
        DynamicStep(
            airport_id=step_airport,
            action=action_label,
            detail=detail,
            budget_after=state.budget_usd,
            time_left_min=time_left_after_action,
            metadata=metadata or {},
        )
    )

    # Step 5: Apply any triggered mandatory events
    apply_mandatory_events(state, cost_airport, mandatory_events, time_left_after_action)


def apply_time_only(
    state: DynamicState,
    rules: Dict[str, float],
    duration_min: float,
    cost_airport,
    count_stay: bool,
) -> Tuple[float, List[Dict[str, float]]]:
    """
    Advance time for an action without monetary cost (e.g., working).
    
    This is used for actions that only cost time, not money.
    For example, working at a job earns money but takes time.
    
    The function:
    1. Validates there's enough time
    2. Advances the clock
    3. Triggers mandatory food/lodging events if thresholds crossed
    4. Does NOT deduct budget (the caller adds income separately)
    
    Args:
        state: Current dynamic session state
        rules: System rules dict
        duration_min: Duration of the action in minutes
        cost_airport: Airport whose food/lodging costs apply
        count_stay: Whether time counts toward minimum stay
        
    Returns:
        Tuple of (time_left_after, list_of_mandatory_events)
        
    Raises:
        DynamicPlanError: If time is insufficient
    """
    # Validate there's enough time (cost is 0 for time-only actions)
    validate_action(state, rules, duration_min, 0.0, cost_airport)
    return advance_time(state, rules, duration_min, cost_airport, count_stay)


def apply_mandatory_events(
    state: DynamicState,
    cost_airport,
    mandatory_events: List[Dict[str, float]],
    time_left_after_action: float,
) -> None:
    """
    Apply mandatory food/lodging costs and log them as steps.
    
    Called after advancing time. For each mandatory event triggered:
    1. Deducts the cost from budget
    2. Adds to total_spent
    3. Logs a DynamicStep for the event
    
    MANDATORY EVENTS:
        - "alimentacion": Mandatory meal (cost = airport.food_cost)
        - "alojamiento": Mandatory lodging (cost = airport.lodging_cost)
    
    Args:
        state: Current dynamic session state (mutated in-place)
        cost_airport: Airport with food/lodging cost data
        mandatory_events: List of events generated by advance_time()
        time_left_after_action: Remaining time to record in step logs
    """
    if not cost_airport:
        return

    for event in mandatory_events:
        event_cost = event["cost"]
        # Deduct cost
        state.budget_usd -= event_cost
        state.total_spent += event_cost
        # Log the event
        state.steps.append(
            DynamicStep(
                airport_id=state.current_airport,
                action=event["action"],
                detail=event["detail"],
                budget_after=state.budget_usd,
                time_left_min=time_left_after_action,
                metadata={"cost": event["cost"]},
            )
        )


def validate_action(
    state: DynamicState,
    rules: Dict[str, float],
    duration_min: float,
    cost_usd: float,
    cost_airport,
) -> None:
    """
    Validate that an action can be performed given current resources.
    
    This function performs three checks:
    1. Duration is positive (sanity check)
    2. Enough time remains for the action
    3. Enough budget remains (including projected mandatory costs)
    
    WHY INCLUDE MANDATORY COSTS:
        If an action takes 10 hours, it will trigger at least one
        mandatory meal. We need to ensure the traveler has enough
        budget for both the action AND the mandatory costs.
    
    Args:
        state: Current dynamic session state
        rules: System rules dict
        duration_min: Duration of the proposed action
        cost_usd: Direct monetary cost of the action
        cost_airport: Airport for mandatory cost estimation
        
    Raises:
        DynamicPlanError: If any constraint is violated
    """
    # Check 1: Duration must be positive
    if duration_min <= 0:
        raise DynamicPlanError("Invalid duration")

    # Check 2: Enough time remaining
    if state.time_left_min - duration_min < 0:
        raise DynamicPlanError("Not enough time for this action")

    # Check 3: Enough budget (including projected mandatory costs)
    _, _, mandatory_cost = estimate_mandatory_costs(
        state,
        duration_min,
        rules,
        cost_airport,
    )
    total_cost = cost_usd + mandatory_cost
    if state.budget_usd - total_cost < 0:
        raise DynamicPlanError("Insufficient budget for this action")


def estimate_mandatory_costs(
    state: DynamicState,
    duration_min: float,
    rules: Dict[str, float],
    cost_airport,
) -> Tuple[int, int, float]:
    """
    Estimate mandatory food and lodging costs for a given duration.
    
    This function projects how many meals and lodgings would be triggered
    if the traveler spends the given duration. It's used for validation
    to ensure the traveler has enough budget.
    
    CALCULATION:
        - Food interval: 8 hours (configurable)
        - Lodging interval: 20 hours (configurable)
        - Meals = (minutes_since_food + duration) // food_interval
        - Lodgings = (minutes_since_lodging + duration) // lodging_interval
    
    Args:
        state: Current dynamic session state (for current intervals)
        duration_min: Prospective duration in minutes
        rules: System rules dict with food_interval_h and lodging_interval_h
        cost_airport: Airport object with food_cost and lodging_cost
        
    Returns:
        Tuple of (meals_count, lodgings_count, total_cost)
    """
    # Get intervals from rules (convert hours to minutes)
    food_interval_min = rules.get("food_interval_h", 8) * 60
    lodging_interval_min = rules.get("lodging_interval_h", 20) * 60

    # Calculate new totals after the proposed duration
    new_food = state.minutes_since_food + duration_min
    new_lodging = state.minutes_since_lodging + duration_min

    # Count how many intervals would be crossed
    meals = int(new_food // food_interval_min) if food_interval_min > 0 else 0
    lodgings = int(new_lodging // lodging_interval_min) if lodging_interval_min > 0 else 0

    # Calculate total cost
    cost = 0.0
    if cost_airport:
        cost += meals * cost_airport.food_cost
        cost += lodgings * cost_airport.lodging_cost

    return meals, lodgings, cost


def advance_time(
    state: DynamicState,
    rules: Dict[str, float],
    duration_min: float,
    cost_airport,
    count_stay: bool,
) -> Tuple[float, List[Dict[str, float]]]:
    """
    Advance the session clock and compute triggered mandatory events.
    
    This function:
    1. Increments the minutes-since-food/lodging counters
    2. Counts how many intervals have been crossed
    3. Generates mandatory event descriptors
    4. Resets the counters (subtracting crossed intervals)
    5. Decrements the remaining time
    
    TIME TRACKING:
        The state tracks minutes since last food/lodging. When these
        exceed the interval thresholds, mandatory events are triggered.
        After triggering, the counters are reset (modulo the interval).
    
    Args:
        state: Current dynamic session state (mutated in-place)
        rules: System rules dict with interval settings
        duration_min: Minutes to advance
        cost_airport: Airport whose cost data is used for event generation
        count_stay: If True, the duration counts toward stay_min
        
    Returns:
        Tuple of (new_time_left_min, list_of_mandatory_event_dicts)
    """
    # Get intervals from rules (convert hours to minutes)
    food_interval_min = rules.get("food_interval_h", 8) * 60
    lodging_interval_min = rules.get("lodging_interval_h", 20) * 60

    # Increment counters
    state.minutes_since_food += duration_min
    state.minutes_since_lodging += duration_min
    if count_stay:
        state.stay_min += duration_min

    # Count how many intervals have been crossed
    meals = int(state.minutes_since_food // food_interval_min) if food_interval_min > 0 else 0
    lodgings = int(state.minutes_since_lodging // lodging_interval_min) if lodging_interval_min > 0 else 0

    # Reset counters (subtract crossed intervals)
    if food_interval_min > 0:
        state.minutes_since_food -= meals * food_interval_min
    if lodging_interval_min > 0:
        state.minutes_since_lodging -= lodgings * lodging_interval_min

    # Generate mandatory event descriptors
    mandatory_events: List[Dict[str, float]] = []
    if cost_airport:
        for _ in range(meals):
            mandatory_events.append(
                {
                    "action": "alimentacion",
                    "detail": f"Mandatory meal ({cost_airport.food_cost:.2f} USD)",
                    "cost": cost_airport.food_cost,
                }
            )

        for _ in range(lodgings):
            mandatory_events.append(
                {
                    "action": "alojamiento",
                    "detail": f"Mandatory lodging ({cost_airport.lodging_cost:.2f} USD)",
                    "cost": cost_airport.lodging_cost,
                }
            )

    # Decrement remaining time
    state.time_left_min -= duration_min
    return state.time_left_min, mandatory_events


def calculate_segment_cost(route, cfg: AircraftConfig, state: DynamicState):
    """
    Calculate the monetary cost of a flight segment.
    
    This function handles both normal and subsidized routes:
    
    NORMAL ROUTES (base_cost != 0):
        cost = distance_km * cost_per_km
        
    SUBSIDIZED ROUTES (base_cost == 0):
        - If no distance traveled yet: cost = $0 (always allowed)
        - Otherwise: check 20% cap
          projected_free = free_distance_km + route.distance_km
          projected_total = total_distance_km + route.distance_km
          If projected_free > projected_total * 0.2: return None (rejected)
          Otherwise: cost = $0
    
    WHY THE 20% CAP:
        Subsidized routes are free, but we don't want travelers to only
        use free routes. The 20% cap ensures they use some paid routes too.
    
    Args:
        route: Route object for the segment
        cfg: Aircraft configuration with cost_per_km
        state: Current session state with distance trackers
        
    Returns:
        Cost in USD, 0.0 for subsidized routes, or None if over cap
    """
    # Calculate normal cost
    base_cost = route.distance_km * cfg.cost_per_km
    
    # If not subsidized, return normal cost
    if route.base_cost != 0:
        return base_cost

    # First leg of the trip: always allow subsidized routes
    if state.total_distance_km == 0:
        return 0.0

    # Check 20% cap for subsequent legs
    projected_total = state.total_distance_km + route.distance_km
    projected_free = state.free_distance_km + route.distance_km
    max_free = projected_total * 0.2

    if projected_free > max_free:
        return None  # Would exceed 20% cap
    return 0.0


def find_route(graph: Graph, origin: str, destination: str):
    """
    Look up a specific route between two airports.
    
    This is a convenience function that wraps graph.get_route().
    
    Args:
        graph: The airline route graph
        origin: Origin airport IATA code
        destination: Destination airport IATA code
        
    Returns:
        Route object if found, None otherwise
    """
    for route in graph.get_outgoing_routes(origin):
        if route.destination == destination:
            return route
    return None


def can_work(state: DynamicState, rules: Dict[str, float]) -> bool:
    """
    Determine whether the traveler is eligible to work.
    
    Work is only available when the traveler's budget drops below
    a threshold percentage of their initial budget.
    
    DEFAULT THRESHOLD: 35%
        If initial_budget = $1000, work is available when budget < $350
    
    WHY THIS RULE:
        This simulates the need to work only when financially necessary.
        Travelers with plenty of budget don't need to work.
    
    Args:
        state: Current dynamic session state
        rules: System rules dict with budget_trigger_percent
        
    Returns:
        True if the traveler can work, False otherwise
    """
    threshold = state.initial_budget * (rules.get("budget_trigger_percent", 35) / 100.0)
    return state.budget_usd < threshold


def is_affordable(state: DynamicState, cost_usd: float, duration_min: float) -> bool:
    """
    Quick check if an action is affordable in terms of both budget and time.
    
    This is a simplified check that does NOT include projected mandatory
    costs. It's used for UI display flags (e.g., graying out activities
    that are clearly unaffordable).
    
    For accurate validation, use validate_action() instead.
    
    Args:
        state: Current dynamic session state
        cost_usd: Monetary cost of the action
        duration_min: Duration of the action
        
    Returns:
        True if budget >= cost AND time_left >= duration
    """
    return state.budget_usd >= cost_usd and state.time_left_min >= duration_min
