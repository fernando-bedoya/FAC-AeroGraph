const BASE_URL = "http://localhost:3000/api";

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

async function get(endpoint) {
  const res = await fetch(`${BASE_URL}${endpoint}`);
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || `Error ${res.status}`);
  }
  return res.json();
}

// Grafo
export const loadGraph = (filePath) => post("/load", filePath ? { file_path: filePath } : {});
export const getGraph = () => get("/graph");
export const blockRoute = (origin, destination, blocked) =>
  post("/route/block", { origin, destination, blocked });

// Configuracion
export const updateAircraftConfig = (config) => post("/config/aircraft", config);

// Plan basico
export const planBasic = (origin, budget, hours) =>
  post("/plan/basic", { origin, budget_usd: budget, time_hours: hours });

// Ruta por criterios
export const planBestRoute = (origin, destination, criteria, excludeSecondary, allowedAircraft) =>
  post("/plan/best-route", {
    origin,
    destination,
    criteria,
    exclude_secondary: excludeSecondary,
    allowed_aircraft: allowedAircraft,
  });

// Dinamico
export const dynamicStart = (origin, budget, hours) =>
  post("/dynamic/start", { origin, initial_budget: budget, total_time_hours: hours });

export const dynamicState = (sessionId) => get(`/dynamic/state/${sessionId}`);

export const dynamicActivities = (sessionId) => get(`/dynamic/activities/${sessionId}`);

export const dynamicChooseActivities = (sessionId, activities) =>
  post(`/dynamic/activities/${sessionId}`, { activities });

export const dynamicJobs = (sessionId) => get(`/dynamic/jobs/${sessionId}`);

export const dynamicWork = (sessionId, jobName, hours) =>
  post(`/dynamic/work/${sessionId}`, { job_name: jobName, hours });

export const dynamicFlightOptions = (sessionId) => get(`/dynamic/flight-options/${sessionId}`);

export const dynamicFly = (sessionId, destination, aircraft) =>
  post(`/dynamic/fly/${sessionId}`, { destination, aircraft });

export const dynamicFlyStart = (sessionId, destination, aircraft) =>
  post(`/dynamic/fly/start/${sessionId}`, { destination, aircraft });

export const dynamicFlyArrive = (sessionId) => post(`/dynamic/fly/arrive/${sessionId}`, {});

export const dynamicFinish = (sessionId) => post(`/dynamic/finish/${sessionId}`, {});

export const simulationInterrupt = (sessionId, origin, destination) =>
  post("/simulation/interrupt", { session_id: sessionId, origin, destination });

export const dynamicReport = (sessionId) => get(`/dynamic/report/${sessionId}`);
