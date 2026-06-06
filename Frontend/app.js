/**
 * SkyRoute Planner - Main Application Entry Point
 * 
 * This is the main JavaScript module that coordinates all frontend functionality.
 * It handles user interactions, updates the UI, and communicates with the backend API.
 * 
 * Architecture:
 * - simulation.js: State management and API calls for dynamic planning
 * - graph.js: D3.js globe visualization and flight animations
 * - ui.js: UI rendering functions for panels and modals
 * - api.js: HTTP client for backend communication
 * 
 * Features implemented:
 * - R1: Graph loading and visualization on 3D globe
 * - R2: Basic planning with budget/time constraints
 * - R3: Dynamic planning with activities, jobs, and flights
 * - R4: Route interruption and recalculation
 * - R5: Final report generation and export
 */

import * as sim from "./js/simulation.js";
import * as graph from "./js/graph.js";
import * as ui from "./js/ui.js";

// DOM element references
const $ = (id) => document.getElementById(id);

// Local state for flight animation
let currentFlight = null;
let flightInterrupted = false;

// --- Graph Loading ---

/**
 * Handle graph loading from JSON file.
 * Loads the airline network and initializes the globe visualization.
 */
async function handleLoadGraph() {
  try {
    const filePath = $("jsonPath").value.trim();
    if (!filePath) { ui.showRouteError("Ingresa una ruta valida"); return; }

    const data = await sim.loadGraph(filePath);
    ui.fillAirportSelectors(data.airports);
    graph.renderGraph(data, handleAirportClick);
    ui.showRouteMessage("Red cargada correctamente");
    ui.showDebug({ airports: data.airports.length, routes: data.routes.length });
  } catch (err) {
    ui.showRouteError(err.message);
    ui.showDebugMessage(err.message);
  }
}

// --- Basic Planning ---

/**
 * Handle basic itinerary planning.
 * Calculates two routes: one optimized for budget, one for time.
 */
async function handleBasicPlan() {
  if (!sim.isGraphLoaded()) { ui.showRouteError("Primero carga un JSON"); return; }
  try {
    ui.showRouteMessage("Calculando...");
    const result = await sim.calculateBasicPlan(
      $("originBasic").value,
      Number($("budget").value),
      Number($("timeHours").value)
    );
    if (result.budget_route && result.time_route) {
      ui.showBasicPlans(result.budget_route, result.time_route);
      ui.showDebug(result);
    } else {
      ui.showRouteMessage("No se encontraron rutas");
    }
  } catch (err) {
    ui.showRouteError(err.message);
  }
}

// --- Route by Criteria ---

/**
 * Get selected optimization criteria from checkboxes.
 */
function getSelectedCriteria() {
  return Array.from(document.querySelectorAll(".criteria-checkbox"))
    .filter((cb) => cb.checked)
    .map((cb) => cb.value);
}

/**
 * Get selected aircraft types from checkboxes.
 */
function getSelectedAircraft() {
  return Array.from(document.querySelectorAll(".aircraft-checkbox"))
    .filter((cb) => cb.checked)
    .map((cb) => cb.value);
}

/**
 * Handle optimal route calculation by criteria.
 * Calculates routes optimized by distance, time, and/or cost.
 */
async function handleBestRoute() {
  if (!sim.isGraphLoaded()) { ui.showRouteError("Primero carga un JSON"); return; }

  const criteria = getSelectedCriteria();
  if (!criteria.length) { ui.showRouteError("Selecciona al menos un criterio"); return; }

  const aircraft = getSelectedAircraft();
  if (!aircraft.length) { ui.showRouteError("Selecciona al menos un transporte"); return; }

  try {
    ui.showRouteMessage("Calculando...");
    const origin = $("origin").value;
    const destination = $("destination").value;
    const excludeSecondary = $("excludeSecondary").checked;

    const result = await sim.calculateBestRoute(origin, destination, criteria, excludeSecondary, aircraft);
    const hasRoute = Object.values(result).some((r) => r.reachable);

    if (hasRoute) {
      ui.showOptimizedRoutes(result, origin, criteria);
      ui.showDebug(result);
    } else {
      const existsAny = await sim.checkRouteExists(origin, destination, criteria, excludeSecondary);
      if (existsAny) {
        ui.showNoTransport(origin, destination, aircraft);
      } else {
        ui.showRouteMessage("No se encontraron rutas");
      }
    }
  } catch (err) {
    ui.showRouteError(err.message);
  }
}

// --- Aircraft Configuration ---

/**
 * Handle aircraft configuration update.
 * Sends new cost/time per km values to the backend.
 */
async function handleUpdateAircraftConfig() {
  try {
    const config = {
      "Avion Comercial": {
        costoKm: Number($("costAvionComercial").value),
        tiempoKm: Number($("timeAvionComercial").value),
      },
      "Avion Regional": {
        costoKm: Number($("costAvionRegional").value),
        tiempoKm: Number($("timeAvionRegional").value),
      },
      "Helice": {
        costoKm: Number($("costHelice").value),
        tiempoKm: Number($("timeHelice").value),
      },
    };
    
    const result = await sim.updateAircraftConfig(config);
    ui.showRouteMessage("Configuracion de aeronaves actualizada");
    ui.showDebug(result);
  } catch (err) {
    ui.showRouteError(err.message);
  }
}

// --- Route Blocking/Unblocking ---

/**
 * Handle route blocking or unblocking.
 * If a dynamic session is active and a flight is in progress on the blocked route,
 * the flight is interrupted and the passenger is redirected.
 */
async function handleBlockRoute(blocked) {
  if (!sim.isGraphLoaded()) { ui.showRouteError("Primero carga un JSON"); return; }

  const origin = $("blockOrigin").value.trim().toUpperCase();
  const destination = $("blockDestination").value.trim().toUpperCase();
  if (!origin || !destination) { ui.showRouteError("Ingresa origen y destino"); return; }

  try {
    // Si hay sesión activa y estamos bloqueando, manejar interrupción
    if (sim.hasSession() && blocked) {
      if (currentFlight && currentFlight.origin === origin && currentFlight.destination === destination) {
        flightInterrupted = true;
        graph.stopFlight();
      }

      const result = await sim.interruptRoute(origin, destination);

      if (result && result.was_redirected) {
        ui.showRouteError(`Vuelo interrumpido! Redirigido a ${result.redirected_to}`);
        graph.stopFlight();
        flightInterrupted = true;
      } else {
        ui.showRouteMessage(`Ruta bloqueada: ${origin} -> ${destination}`);
      }

      if (result?.state) await refreshDynamicUI(result.state);

      const data = sim.getGraphData();
      if (data) {
        graph.renderGraph(data, handleAirportClick);
        if (result?.state) highlightSession(result.state);
      }
    } else {
      await sim.blockRouteOnGraph(origin, destination, blocked);
      const data = sim.getGraphData();
      graph.renderGraph(data, handleAirportClick);

      if (sim.hasSession() && sim.getState()) highlightSession(sim.getState());

      const action = blocked ? "Bloqueada" : "Desbloqueada";
      ui.showRouteMessage(`Ruta ${action}: ${origin} -> ${destination}`);
      ui.showDebug({ route: { origin, destination, blocked } });
    }
  } catch (err) {
    ui.showRouteError(err.message);
  }
}

// --- Sesión dinámica ---

async function handleDynamicStart() {
  if (!sim.isGraphLoaded()) { ui.showRouteError("Primero carga un JSON"); return; }
  try {
    const state = await sim.startSession(
      $("originDynamic").value,
      Number($("dynamicBudget").value),
      Number($("dynamicTimeHours").value)
    );
    highlightSession(state);
    await refreshDynamicUI(state);
    ui.showDebug(state);
  } catch (err) {
    ui.showRouteError(err.message);
  }
}

async function handleDynamicRefresh() {
  try {
    const state = await sim.refreshState();
    highlightSession(state);
    await refreshDynamicUI(state);
  } catch (err) {
    ui.showRouteError(err.message);
  }
}

async function handleDynamicFinish() {
  try {
    await sim.finishSession();
    graph.resetHighlights();
    ui.clearDynamicPanel();
  } catch (err) {
    ui.showRouteError(err.message);
  }
}

async function handleDynamicActivities() {
  try {
    const selected = Array.from(document.querySelectorAll("input[name='dynamic-activity']:checked"))
      .map((input) => input.value);
    const state = await sim.applyActivities(selected);
    await refreshDynamicUI(state);
    ui.showDebug(state);
  } catch (err) {
    ui.showRouteError(err.message);
  }
}

async function handleDynamicWork() {
  try {
    const jobRadio = document.querySelector("input[name='dynamic-job']:checked");
    if (!jobRadio) { ui.showRouteError("Selecciona un trabajo"); return; }
    const hours = Number($("dynamicJobHours").value);
    const state = await sim.work(jobRadio.value, hours);
    await refreshDynamicUI(state);
    ui.showDebug(state);
  } catch (err) {
    ui.showRouteError(err.message);
  }
}

async function handleDynamicFly() {
  try {
    const selected = document.querySelector("input[data-destination][data-aircraft]:checked");
    if (!selected) { ui.showRouteError("Selecciona un vuelo"); return; }

    const destination = selected.dataset.destination;
    const aircraft = selected.dataset.aircraft;
    const currentOrigin = sim.getState().current_airport || $("originDynamic").value;

    const isSubsidized = selected.dataset.subsidized === "true";
    const distance = parseFloat(selected.dataset.distance);
    const state = sim.getState();

    if (isSubsidized && state && state.total_distance_km > 0) {
      const projectedTotal = state.total_distance_km + distance;
      const projectedFree = state.free_distance_km + distance;
      if (projectedFree > projectedTotal * 0.2) {
        ui.showSubsidyModal(state, distance);
        return;
      }
    }

    // Marcar en tránsito
    const startResult = await sim.flyStart(destination, aircraft);
    await refreshDynamicUI(startResult);

    // Duración de la animación
    const flightMin = startResult.estimated_time_min || 10;
    const animDuration = (flightMin * 100) + 5000;

    // Animar vuelo
    flightInterrupted = false;
    currentFlight = { origin: currentOrigin, destination };

    ui.showRouteMessage("Vuelo en progreso... (Puedes bloquear la ruta para interrumpir)");
    await graph.fly(currentOrigin, destination, animDuration);

    currentFlight = null;

    if (!flightInterrupted) {
      const finalResult = await sim.flyArrive();
      await refreshDynamicUI(finalResult);
      ui.showDebug(finalResult);
      ui.showRouteMessage(`Vuelo completado a ${destination}`);
      highlightSession(finalResult);
    }
  } catch (err) {
    const msg = err.message.replace("API Error: ", "");
    ui.showRouteError(msg);
    try {
      if (sim.hasSession()) {
        const refreshed = await sim.refreshState();
        await refreshDynamicUI(refreshed);
      }
    } catch (e) { /* continuar */ }
  }
}

async function handleGenerateReport() {
  if (!sim.hasSession()) { ui.showRouteError("No hay sesion activa"); return; }
  try {
    const report = await sim.getReport();
    ui.showReportModal(report);
  } catch (err) {
    ui.showRouteError(err.message);
  }
}

// --- Helpers ---

function handleAirportClick(airport) {
  ui.showAirportInfo(airport);
}

async function refreshDynamicUI(state) {
  ui.showDynamicState(state);
  ui.showSuggestedRoute(state.suggested_route || {});
  ui.showSteps(state.steps || []);

  const [activities, jobs, flights] = await Promise.all([
    sim.listActivities(),
    sim.listJobs(),
    sim.listFlights(),
  ]);

  ui.showActivities(activities.activities || []);
  ui.showJobs(jobs.jobs || []);
  ui.showFlights(flights.options || []);
}

function highlightSession(state) {
  if (!state) return;
  graph.resetHighlights();
  if (state.visited_airports?.length) {
    state.visited_airports.forEach((id) => graph.highlightNode(id));
    for (let i = 0; i < state.visited_airports.length - 1; i++) {
      graph.highlightEdge(state.visited_airports[i], state.visited_airports[i + 1]);
    }
  }
}

// --- Inicialización ---

document.addEventListener("DOMContentLoaded", () => {
  // Event listeners
  $("btnLoad").addEventListener("click", handleLoadGraph);
  $("btnBasic").addEventListener("click", handleBasicPlan);
  $("btnBestRoute").addEventListener("click", handleBestRoute);
  $("btnUpdateAircraft").addEventListener("click", handleUpdateAircraftConfig);
  $("btnBlock").addEventListener("click", () => handleBlockRoute(true));
  $("btnUnblock").addEventListener("click", () => handleBlockRoute(false));
  $("btnDynamicStart").addEventListener("click", handleDynamicStart);
  $("btnDynamicRefresh").addEventListener("click", handleDynamicRefresh);
  $("btnDynamicFinish").addEventListener("click", handleDynamicFinish);
  $("btnDynamicApplyActivities").addEventListener("click", handleDynamicActivities);
  $("btnDynamicWork").addEventListener("click", handleDynamicWork);
  $("btnDynamicFly").addEventListener("click", handleDynamicFly);
  $("btnGenerateReport").addEventListener("click", handleGenerateReport);

  // Modal de reporte
  $("report-modal-close").addEventListener("click", () => {
    $("report-modal").classList.remove("active");
  });
  $("report-modal").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) e.currentTarget.classList.remove("active");
  });

  // Modal de advertencia de ruta subsidiada (Límite 20%)
  $("subsidy-modal-close").addEventListener("click", () => {
    $("subsidy-modal").classList.remove("active");
  });
  $("subsidy-modal-btn-ok").addEventListener("click", () => {
    $("subsidy-modal").classList.remove("active");
  });
  $("subsidy-modal").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) e.currentTarget.classList.remove("active");
  });

  // Exportar reporte
  $("report-export-btn").addEventListener("click", () => {
    if (!sim.hasSession()) return;
    const format = $("report-export-format").value;
    const url = `http://localhost:3000/api/dynamic/report/export/${sim.getSessionId()}?format=${format}`;
    window.location.href = url;
  });

  // Redimensionamiento
  window.addEventListener("resize", () => {
    if (sim.isGraphLoaded()) {
      const data = sim.getGraphData();
      graph.renderGraph(data, handleAirportClick);
    }
  });

  // Estado inicial
  document.getElementById("airportInfo").textContent = "Selecciona un aeropuerto para ver informacion.";
  ui.showRouteMessage("Selecciona un plan y presiona calcular");
  ui.clearDynamicPanel();
});
