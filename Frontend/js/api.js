/**
 * API Client Module
 * 
 * Handles all HTTP communication with the backend server.
 * Base URL: http://localhost:3000/api
 * 
 * Functions are organized by domain:
 * - Graph operations (load, get, block)
 * - Configuration (aircraft settings)
 * - Planning (basic plan, best route)
 * - Dynamic session (start, state, activities, jobs, flights)
 * - Reports (generate, export)
 */

const BASE_URL = "http://localhost:3000/api";

/**
 * POST request helper with error handling
 */
async function post(endpoint, payload) {
  const res = await fetch(`${BASE_URL}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || `Error ${res.status}`);
  }
  return res.json();
}

/**
 * GET request helper with error handling
 */
async function get(endpoint) {
  const res = await fetch(`${BASE_URL}${endpoint}`);
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || `Error ${res.status}`);
  }
  return res.json();
}

// =============================================================================
// GRAPH OPERATIONS
// =============================================================================

/** Load graph from JSON file (opens native file dialog if no path provided) */
export const loadGraph = (filePath) => post("/load", filePath ? { file_path: filePath } : {});

/** Get complete graph data (airports, routes, aircraft config) */
export const getGraph = () => get("/graph");

/** Block or unblock a route */
export const blockRoute = (origin, destination, blocked) =>
  post("/route/block", { origin, destination, blocked });

// =============================================================================
// CONFIGURATION
// =============================================================================

/** Update aircraft cost/time per km settings */
export const updateAircraftConfig = (config) => post("/config/aircraft", config);

// =============================================================================
// PLANNING (R2.2)
// =============================================================================

/** Calculate basic itinerary with budget and time constraints */
export const planBasic = (origin, budget, hours) =>
  post("/plan/basic", { origin, budget_usd: budget, time_hours: hours });

/** Find best route by criteria (distance, time, cost) */
export const planBestRoute = (origin, destination, criteria, excludeSecondary, allowedAircraft) =>
  post("/plan/best-route", {
    origin,
    destination,
    criteria,
    exclude_secondary: excludeSecondary,
    allowed_aircraft: allowedAircraft,
  });

// =============================================================================
// DYNAMIC SESSION (R2.3)
// =============================================================================

/** Start a new dynamic planning session */
export const dynamicStart = (origin, budget, hours) =>
  post("/dynamic/start", { origin, initial_budget: budget, total_time_hours: hours });

/** Get current session state */
export const dynamicState = (sessionId) => get(`/dynamic/state/${sessionId}`);

/** List available activities at current airport */
export const dynamicActivities = (sessionId) => get(`/dynamic/activities/${sessionId}`);

/** Apply selected activities to session */
export const dynamicChooseActivities = (sessionId, activities) =>
  post(`/dynamic/activities/${sessionId}`, { activities });

/** List available jobs at current airport */
export const dynamicJobs = (sessionId) => get(`/dynamic/jobs/${sessionId}`);

/** Perform work at current airport to earn income */
export const dynamicWork = (sessionId, jobName, hours) =>
  post(`/dynamic/work/${sessionId}`, { job_name: jobName, hours });

/** List available flight options from current airport */
export const dynamicFlightOptions = (sessionId) => get(`/dynamic/flight-options/${sessionId}`);

/** Execute complete flight (single-phase, no animation) */
export const dynamicFly = (sessionId, destination, aircraft) =>
  post(`/dynamic/fly/${sessionId}`, { destination, aircraft });

/** Phase 1: Start flight animation (marks traveler as in-transit) */
export const dynamicFlyStart = (sessionId, destination, aircraft) =>
  post(`/dynamic/fly/start/${sessionId}`, { destination, aircraft });

/** Phase 2: Complete flight after animation finishes */
export const dynamicFlyArrive = (sessionId) => post(`/dynamic/fly/arrive/${sessionId}`, {});

/** End dynamic session and release resources */
export const dynamicFinish = (sessionId) => post(`/dynamic/finish/${sessionId}`, {});

// =============================================================================
// SIMULATION (R2.4)
// =============================================================================

/** Handle route interruption during active session */
export const simulationInterrupt = (sessionId, origin, destination) =>
  post("/simulation/interrupt", { session_id: sessionId, origin, destination });

// =============================================================================
// REPORTS (R2.5)
// =============================================================================

/** Generate final trip report */
export const dynamicReport = (sessionId) => get(`/dynamic/report/${sessionId}`);
