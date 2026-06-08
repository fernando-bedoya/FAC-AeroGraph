/**
 * Simulation State Management Module
 * 
 * Manages the client-side state for dynamic planning sessions.
 * Acts as an intermediary between the API client and the UI.
 * 
 * State tracked:
 * - sessionId: UUID of the active session
 * - state: Current session state (budget, time, location, etc.)
 * - graphData: Loaded graph data (airports, routes)
 * 
 * This module also handles:
 * - Aircraft type validation for route filtering
 * - Graph refresh after route blocking
 */

import * as api from "./api.js";

// =============================================================================
// SESSION STATE
// =============================================================================

// Active session UUID (null if no session)
let sessionId = null;

// Current session state from backend
let state = null;

// Loaded graph data (airports, routes, config)
let graphData = null;

// =============================================================================
// STATE ACCESSORS
// =============================================================================

/** Check if a dynamic session is active */
export function hasSession() { return !!sessionId; }

/** Get current session state */
export function getState() { return state; }

/** Get loaded graph data */
export function getGraphData() { return graphData; }

/** Check if graph has been loaded */
export function isGraphLoaded() { return graphData !== null; }

/** Get active session ID */
export function getSessionId() { return sessionId; }

// =============================================================================
// GRAPH OPERATIONS
// =============================================================================

/**
 * Load graph from JSON file and fetch complete graph data.
 * @param {string|null} filePath - Optional path to JSON file
 * @returns {Object} Graph data with airports and routes
 */
export async function loadGraph(filePath) {
  await api.loadGraph(filePath);
  graphData = await api.getGraph();
  return graphData;
}

/**
 * Refresh graph data from backend.
 * Used after route blocking/unblocking to get updated state.
 */
export async function refreshGraph() {
  graphData = await api.getGraph();
  return graphData;
}

/**
 * Block or unblock a route and refresh graph.
 * @param {string} origin - Origin airport code
 * @param {string} destination - Destination airport code
 * @param {boolean} blocked - True to block, false to unblock
 */
export async function blockRouteOnGraph(origin, destination, blocked) {
  await api.blockRoute(origin, destination, blocked);
  await refreshGraph();
}

/**
 * Update aircraft configuration and refresh graph.
 * @param {Object} config - Aircraft config with cost/time per km
 */
export async function updateAircraftConfig(config) {
  const result = await api.updateAircraftConfig(config);
  if (isGraphLoaded()) {
    try { await refreshGraph(); } catch (e) { /* continue */ }
  }
  return result;
}

// =============================================================================
// BASIC PLANNING (R2.2)
// =============================================================================

/**
 * Calculate basic itinerary with budget and time constraints.
 * Returns two routes: one optimized for budget, one for time.
 */
export async function calculateBasicPlan(origin, budget, hours) {
  return api.planBasic(origin, budget, hours);
}

// =============================================================================
// ROUTE BY CRITERIA (R2.2)
// =============================================================================

/**
 * Normalize aircraft name for comparison.
 * Removes accents and trims whitespace.
 */
function normalizeName(str) {
  if (!str) return "";
  return str.normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim();
}

/**
 * Validate that all segments use allowed aircraft types.
 * @param {Array} segments - Route segments
 * @param {Array} allowed - Allowed aircraft types
 * @returns {boolean} True if all segments use allowed aircraft
 */
function validateRouteAircraft(segments, allowed) {
  if (!segments || !segments.length) return true;
  const allowedSet = new Set(allowed.map(normalizeName));
  return segments.every((seg) => {
    const ac = seg.aircraft || seg.aircraftType || seg.aircraft_type;
    return ac && allowedSet.has(normalizeName(ac));
  });
}

/**
 * Calculate best route by criteria with aircraft filtering.
 * Filters results to only include routes using allowed aircraft types.
 */
export async function calculateBestRoute(origin, destination, criteria, excludeSecondary, allowedAircraft) {
  const result = await api.planBestRoute(origin, destination, criteria, excludeSecondary, allowedAircraft);

  // Filter by transport type
  const filtered = {};
  for (const [criterion, route] of Object.entries(result)) {
    if (!route.segments || !route.segments.length) {
      filtered[criterion] = route;
      continue;
    }
    filtered[criterion] = { ...route, reachable: route.reachable && validateRouteAircraft(route.segments, allowedAircraft) };
  }

  return filtered;
}

/**
 * Check if any route exists between origin and destination.
 * Used to show appropriate error message when no route found.
 */
export async function checkRouteExists(origin, destination, criteria, excludeSecondary) {
  const result = await api.planBestRoute(origin, destination, criteria, excludeSecondary, []);
  return result && Object.values(result).some((r) => r.reachable);
}

// =============================================================================
// DYNAMIC SESSION (R2.3)
// =============================================================================

/**
 * Start a new dynamic planning session.
 * Stores session ID and initial state.
 */
export async function startSession(origin, budget, hours) {
  const result = await api.dynamicStart(origin, budget, hours);
  sessionId = result.session_id;
  state = result;
  return result;
}

/**
 * Refresh session state from backend.
 * Updates local state with latest values.
 */
export async function refreshState() {
  if (!sessionId) throw new Error("No hay sesion activa");
  state = await api.dynamicState(sessionId);
  return state;
}

/**
 * List available activities at current airport.
 */
export async function listActivities() {
  if (!sessionId) throw new Error("No hay sesion activa");
  return api.dynamicActivities(sessionId);
}

/**
 * Apply selected activities to session.
 * Deducts cost and time for each activity.
 */
export async function applyActivities(activities) {
  if (!sessionId) throw new Error("No hay sesion activa");
  state = await api.dynamicChooseActivities(sessionId, activities);
  return state;
}

/**
 * List available jobs at current airport.
 * Only returns jobs when budget is below threshold.
 */
export async function listJobs() {
  if (!sessionId) throw new Error("No hay sesion activa");
  return api.dynamicJobs(sessionId);
}

/**
 * Perform work to earn income.
 * Advances time and credits budget.
 */
export async function work(jobName, hours) {
  if (!sessionId) throw new Error("No hay sesion activa");
  state = await api.dynamicWork(sessionId, jobName, hours);
  return state;
}

/**
 * List available flight options from current airport.
 */
export async function listFlights() {
  if (!sessionId) throw new Error("No hay sesion activa");
  return api.dynamicFlightOptions(sessionId);
}

/**
 * Phase 1: Start flight (marks traveler as in-transit).
 * Frontend runs animation after this call.
 */
export async function flyStart(destination, aircraft) {
  if (!sessionId) throw new Error("No hay sesion activa");
  state = await api.dynamicFlyStart(sessionId, destination, aircraft);
  return state;
}

/**
 * Phase 2: Complete flight after animation.
 * Applies costs and updates location.
 */
export async function flyArrive() {
  if (!sessionId) throw new Error("No hay sesion activa");
  state = await api.dynamicFlyArrive(sessionId);
  return state;
}

/**
 * Handle route interruption.
 * If session active, uses interruption endpoint.
 * Otherwise, just blocks the route.
 */
export async function interruptRoute(origin, destination) {
  if (!sessionId) return api.blockRoute(origin, destination, true);
  const result = await api.simulationInterrupt(sessionId, origin, destination);
  state = result.state;
  if (isGraphLoaded()) {
    try { await refreshGraph(); } catch (e) { /* continue */ }
  }
  return result;
}

/**
 * End dynamic session and clear local state.
 */
export async function finishSession() {
  if (!sessionId) return;
  await api.dynamicFinish(sessionId);
  sessionId = null;
  state = null;
}

/**
 * Generate final trip report.
 */
export async function getReport() {
  if (!sessionId) throw new Error("No hay sesion activa");
  return api.dynamicReport(sessionId);
}
