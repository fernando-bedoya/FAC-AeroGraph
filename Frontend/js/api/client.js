/**
 * API Client - Responsabilidad única: Comunicación HTTP con el backend
 * Single Responsibility: Manejar todas las peticiones HTTP
 */

import { CONFIG } from "../constants/config.js";

class ApiClient {
  constructor(baseURL = CONFIG.API.BASE_URL) {
    this.baseURL = baseURL;
  }

  /**
   * Realiza una solicitud POST genérica
   * @param {string} endpoint - Ruta del endpoint
   * @param {Object} payload - Datos a enviar
   * @returns {Promise<Object>} Respuesta del servidor
   */
  async post(endpoint, payload) {
    try {
      const response = await fetch(`${this.baseURL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `Error ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      throw new Error(`API Error: ${error.message}`);
    }
  }

  /**
   * Realiza una solicitud GET genérica
   * @param {string} endpoint - Ruta del endpoint
   * @returns {Promise<Object>} Respuesta del servidor
   */
  async get(endpoint) {
    try {
      const response = await fetch(`${this.baseURL}${endpoint}`);

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `Error ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      throw new Error(`API Error: ${error.message}`);
    }
  }

  // ===== Métodos específicos del dominio =====

  /**
   * Carga un archivo JSON de red aérea
   */
  async loadGraph(filePath) {
    return this.post(CONFIG.API.ENDPOINTS.LOAD, { file_path: filePath });
  }

  /**
   * Obtiene los datos del grafo (aeropuertos y rutas)
   */
  async getGraph() {
    return this.get(CONFIG.API.ENDPOINTS.GRAPH);
  }

  /**
   * Calcula plan básico de itinerario
   */
  async planBasic(origin, budget, hours) {
    return this.post(CONFIG.API.ENDPOINTS.PLAN_BASIC, {
      origin,
      budget_usd: budget,
      time_hours: hours,
    });
  }

  /**
   * Calcula ruta óptima por criterios
   */
  async planBestRoute(origin, destination, criteria, excludeSecondary, allowedAircraft) {
    return this.post(CONFIG.API.ENDPOINTS.PLAN_BEST_ROUTE, {
      origin,
      destination,
      criteria,
      exclude_secondary: excludeSecondary,
      allowed_aircraft: allowedAircraft,
    });
  }

  /**
   * Bloquea o desbloquea una ruta
   */
  async blockRoute(origin, destination, blocked) {
    return this.post(CONFIG.API.ENDPOINTS.ROUTE_BLOCK, {
      origin,
      destination,
      blocked,
    });
  }

  /**
   * Inicia sesion dinamica
   */
  async dynamicStart(origin, budget, hours) {
    return this.post(CONFIG.API.ENDPOINTS.DYNAMIC_START, {
      origin,
      initial_budget: budget,
      total_time_hours: hours,
    });
  }

  /**
   * Obtiene estado dinamico
   */
  async dynamicState(sessionId) {
    return this.get(`${CONFIG.API.ENDPOINTS.DYNAMIC_STATE}/${sessionId}`);
  }

  /**
   * Lista actividades
   */
  async dynamicActivities(sessionId) {
    return this.get(`${CONFIG.API.ENDPOINTS.DYNAMIC_ACTIVITIES}/${sessionId}`);
  }

  /**
   * Registra actividades
   */
  async dynamicChooseActivities(sessionId, activities) {
    return this.post(`${CONFIG.API.ENDPOINTS.DYNAMIC_ACTIVITIES}/${sessionId}`, {
      activities,
    });
  }

  /**
   * Lista trabajos
   */
  async dynamicJobs(sessionId) {
    return this.get(`${CONFIG.API.ENDPOINTS.DYNAMIC_JOBS}/${sessionId}`);
  }

  /**
   * Registra trabajo
   */
  async dynamicWork(sessionId, jobName, hours) {
    return this.post(`${CONFIG.API.ENDPOINTS.DYNAMIC_WORK}/${sessionId}`, {
      job_name: jobName,
      hours,
    });
  }

  /**
   * Lista opciones de vuelo
   */
  async dynamicFlightOptions(sessionId) {
    return this.get(`${CONFIG.API.ENDPOINTS.DYNAMIC_FLIGHT_OPTIONS}/${sessionId}`);
  }

  /**
   * Registra vuelo
   */
  async dynamicFly(sessionId, destination, aircraft) {
    return this.post(`${CONFIG.API.ENDPOINTS.DYNAMIC_FLY}/${sessionId}`, {
      destination,
      aircraft,
    });
  }

  /**
   * Inicia vuelo dinámico (R2.4)
   */
  async dynamicFlyStart(sessionId, destination, aircraft) {
    return this.post(`${CONFIG.API.ENDPOINTS.DYNAMIC_FLY_START}/${sessionId}`, {
      destination,
      aircraft,
    });
  }

  /**
   * Finaliza/confirma llegada de vuelo dinámico (R2.4)
   */
  async dynamicFlyArrive(sessionId) {
    return this.post(`${CONFIG.API.ENDPOINTS.DYNAMIC_FLY_ARRIVE}/${sessionId}`, {});
  }

  /**
   * Interrumpe una ruta durante el vuelo del viajero (R2.4)
   */
  async simulationInterrupt(sessionId, origin, destination) {
    return this.post(CONFIG.API.ENDPOINTS.SIMULATION_INTERRUPT, {
      session_id: sessionId,
      origin,
      destination,
    });
  }

  /**
   * Finaliza sesion dinamica
   */
  async dynamicFinish(sessionId) {
    return this.post(`${CONFIG.API.ENDPOINTS.DYNAMIC_FINISH}/${sessionId}`, {});
  }

  /**
   * Obtiene el reporte final de la sesión dinámica
   */
  async dynamicReport(sessionId) {
    return this.get(`/dynamic/report/${sessionId}`);
  }
}

export const apiClient = new ApiClient();
