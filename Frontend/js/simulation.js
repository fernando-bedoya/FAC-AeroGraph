import * as api from "./api.js";

// Estado de la sesión dinámica
let sessionId = null;
let state = null;

// Estado del grafo cargado
let graphData = null;

export function hasSession() { return !!sessionId; }
export function getState() { return state; }
export function getGraphData() { return graphData; }
export function isGraphLoaded() { return graphData !== null; }

// --- Grafo ---

export async function loadGraph(filePath) {
  await api.loadGraph(filePath);
  graphData = await api.getGraph();
  return graphData;
}

export async function refreshGraph() {
  graphData = await api.getGraph();
  return graphData;
}

export async function blockRouteOnGraph(origin, destination, blocked) {
  await api.blockRoute(origin, destination, blocked);
  await refreshGraph();
}

// --- Plan básico ---

export async function calculateBasicPlan(origin, budget, hours) {
  return api.planBasic(origin, budget, hours);
}

// --- Ruta por criterios ---

function normalizeName(str) {
  if (!str) return "";
  return str.normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim();
}

function validateRouteAircraft(segments, allowed) {
  if (!segments || !segments.length) return true;
  const allowedSet = new Set(allowed.map(normalizeName));
  return segments.every((seg) => {
    const ac = seg.aircraft || seg.aircraftType || seg.aircraft_type;
    return ac && allowedSet.has(normalizeName(ac));
  });
}

export async function calculateBestRoute(origin, destination, criteria, excludeSecondary, allowedAircraft) {
  const result = await api.planBestRoute(origin, destination, criteria, excludeSecondary, allowedAircraft);

  // Filtrar por transporte
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

export async function checkRouteExists(origin, destination, criteria, excludeSecondary) {
  const result = await api.planBestRoute(origin, destination, criteria, excludeSecondary, []);
  return result && Object.values(result).some((r) => r.reachable);
}

// --- Sesión dinámica ---

export async function startSession(origin, budget, hours) {
  const result = await api.dynamicStart(origin, budget, hours);
  sessionId = result.session_id;
  state = result;
  return result;
}

export async function refreshState() {
  if (!sessionId) throw new Error("No hay sesion activa");
  state = await api.dynamicState(sessionId);
  return state;
}

export async function listActivities() {
  if (!sessionId) throw new Error("No hay sesion activa");
  return api.dynamicActivities(sessionId);
}

export async function applyActivities(activities) {
  if (!sessionId) throw new Error("No hay sesion activa");
  state = await api.dynamicChooseActivities(sessionId, activities);
  return state;
}

export async function listJobs() {
  if (!sessionId) throw new Error("No hay sesion activa");
  return api.dynamicJobs(sessionId);
}

export async function work(jobName, hours) {
  if (!sessionId) throw new Error("No hay sesion activa");
  state = await api.dynamicWork(sessionId, jobName, hours);
  return state;
}

export async function listFlights() {
  if (!sessionId) throw new Error("No hay sesion activa");
  return api.dynamicFlightOptions(sessionId);
}

export async function flyStart(destination, aircraft) {
  if (!sessionId) throw new Error("No hay sesion activa");
  state = await api.dynamicFlyStart(sessionId, destination, aircraft);
  return state;
}

export async function flyArrive() {
  if (!sessionId) throw new Error("No hay sesion activa");
  state = await api.dynamicFlyArrive(sessionId);
  return state;
}

export async function interruptRoute(origin, destination) {
  if (!sessionId) return api.blockRoute(origin, destination, true);
  const result = await api.simulationInterrupt(sessionId, origin, destination);
  state = result.state;
  if (isGraphLoaded()) {
    try { await refreshGraph(); } catch (e) { /* continuar */ }
  }
  return result;
}

export async function finishSession() {
  if (!sessionId) return;
  await api.dynamicFinish(sessionId);
  sessionId = null;
  state = null;
}

export async function getReport() {
  if (!sessionId) throw new Error("No hay sesion activa");
  return api.dynamicReport(sessionId);
}

export function getSessionId() { return sessionId; }
