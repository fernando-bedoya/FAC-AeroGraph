/**
 * Route Service - Responsabilidad única: Lógica de cálculo y gestión de rutas
 * Single Responsibility: Manejar planes y rutas óptimas
 */

import { apiClient } from "../api/client.js";

class RouteService {
  constructor() {
    this.currentPlans = null;
    this.currentRoute = null;
  }

  /**
   * Calcula plan básico (2 alternativas: por presupuesto y por tiempo)
   */
  async calculateBasicPlan(origin, budget, hours) {
    this.currentPlans = await apiClient.planBasic(origin, budget, hours);
    return this.currentPlans;
  }

  /**
   * Calcula ruta óptima por criterios
   */
  async calculateBestRoute(origin, destination, criteria, excludeSecondary, allowedAircraft) {
    this.currentRoute = await apiClient.planBestRoute(
      origin,
      destination,
      criteria,
      excludeSecondary,
      allowedAircraft
    );
    return this.currentRoute;
  }

  /**
   * Calcula ruta óptima sin restricción de transporte (para validación)
   */
  async calculateBestRouteAllTransport(origin, destination, criteria, excludeSecondary) {
    return await apiClient.planBestRoute(
      origin,
      destination,
      criteria,
      excludeSecondary,
      [] // Sin filtro de transporte
    );
  }

  /**
   * Normaliza un string removiendo acentos para comparación insensible a acentos
   * @param {string} str - String a normalizar
   * @returns {string} String normalizado
   */
  normalizeAircraftName(str) {
    if (!str) return '';
    return str.normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim();
  }

  /**
   * Valida si todos los segmentos de una ruta usan SOLO transportes permitidos
   * @param {Array} segments - Array de segmentos
   * @param {Array} allowedAircraft - Array de transportes permitidos
   * @returns {boolean} true si todos los segmentos usan transportes permitidos
   */
  validateRouteAircraft(segments, allowedAircraft) {
    if (!segments || segments.length === 0) return true;
    
    // Normalizar los transportes permitidos
    const allowedSet = new Set(allowedAircraft.map(a => this.normalizeAircraftName(a)));
    
    return segments.every(segment => {
      // Intentar varios nombres posibles del campo de transporte
      const aircraftUsed = segment.aircraft || segment.aircraftType || segment.aircraft_type;
      
      if (!aircraftUsed) {
        return false;
      }
      
      // Normalizar el transporte del segmento para comparación
      const normalizedAircraft = this.normalizeAircraftName(aircraftUsed);
      return allowedSet.has(normalizedAircraft);
    });
  }

  /**
   * Filtra rutas por criterio, removiendo aquellas que no respetan los transportes permitidos
   * @param {Object} allRoutes - Objeto con rutas por criterio
   * @param {Array} allowedAircraft - Array de transportes permitidos
   * @returns {Object} Rutas filtradas
   */
  filterRoutesByAircraft(allRoutes, allowedAircraft) {
    const filtered = {};
    
    Object.entries(allRoutes).forEach(([criterion, route]) => {
      // Si la ruta no tiene segmentos, conservarla como no alcanzable
      if (!route.segments || route.segments.length === 0) {
        filtered[criterion] = route;
        return;
      }
      
      // Validar que todos los segmentos usen transportes permitidos
      const isValid = this.validateRouteAircraft(route.segments, allowedAircraft);
      
      filtered[criterion] = {
        ...route,
        reachable: route.reachable && isValid
      };
    });
    
    return filtered;
  }

  /**
   * Obtiene el plan básico actual
   */
  getBasicPlans() {
    return this.currentPlans;
  }

  /**
   * Obtiene la ruta actual
   */
  getCurrentRoute() {
    return this.currentRoute;
  }

  /**
   * Calcula costo acumulado hasta un índice
   */
  calculateAccumulatedCost(segments, index) {
    if (!segments || index < 0) return 0;
    return segments
      .slice(0, index + 1)
      .reduce((sum, s) => sum + s.segment_cost, 0);
  }

  /**
   * Calcula tiempo acumulado hasta un índice
   */
  calculateAccumulatedTime(segments, index) {
    if (!segments || index < 0) return 0;
    return segments
      .slice(0, index + 1)
      .reduce((sum, s) => sum + s.segment_time_min, 0);
  }

  /**
   * Formatea tiempo de minutos a horas
   */
  formatTime(minutes) {
    return (minutes / 60).toFixed(1);
  }

  /**
   * Formatea costo con símbolo USD
   */
  formatCost(cost) {
    return `$${cost.toFixed(2)}`;
  }
}

export const routeService = new RouteService();
