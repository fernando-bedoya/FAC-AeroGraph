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
}

export const apiClient = new ApiClient();
