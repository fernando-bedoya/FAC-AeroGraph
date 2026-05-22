/**
 * Routes Renderer - Responsabilidad única: Renderizar rutas dinámicamente
 * Single Responsibility: Convertir datos de rutas a HTML visual
 */

import { routeService } from "../services/routeService.js";

class RoutesRenderer {
  constructor(containerSelector = "#routesContainer") {
    this.container = document.querySelector(containerSelector);
  }

  /**
   * Renderiza una tarjeta de ruta individual
   */
  renderRoutePlan(plan, title) {
    if (!plan || !plan.segments) return "";

    const stats = this._renderStats(plan);
    const segments = this._renderSegments(plan.segments);
    const destinations = this._renderDestinations(plan.visited_airports);

    return `
      <div class="route-card">
        <div class="route-title">${title}</div>
        <div class="route-stats">${stats}</div>
        <div class="segments-list">${segments}</div>
        ${destinations}
      </div>
    `;
  }

  /**
   * Renderiza estadísticas de la ruta
   * @private
   */
  _renderStats(plan) {
    return `
      <div class="stat-item">
        <div class="stat-label">Destinos</div>
        <div class="stat-value">${plan.visited_airports.length - 1}</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">Costo USD</div>
        <div class="stat-value cost-display">${routeService.formatCost(plan.total_cost)}</div>
      </div>
    `;
  }

  /**
   * Renderiza lista de segmentos (vuelos individuales)
   * @private
   */
  _renderSegments(segments) {
    return segments.map((seg, idx) => `
      <div class="segment">
        <div class="segment-header">
          <span class="airport-badge">${seg.origin}</span>
          <span class="segment-arrow">→</span>
          <span class="airport-badge">${seg.destination}</span>
          <span class="aircraft-badge">${seg.aircraft}</span>
        </div>
        <div class="segment-details">
          <div class="detail-item">
            <span>Distancia:</span>
            <span class="detail-value distance-display">${seg.distance_km.toFixed(1)} km</span>
          </div>
          <div class="detail-item">
            <span>Costo:</span>
            <span class="detail-value cost-display">${routeService.formatCost(seg.segment_cost)}</span>
          </div>
          <div class="detail-item">
            <span>Tiempo:</span>
            <span class="detail-value time-display">${routeService.formatTime(seg.segment_time_min)}h</span>
          </div>
          <div class="detail-item">
            <span>Acum. Costo:</span>
            <span class="detail-value">${routeService.formatCost(
              routeService.calculateAccumulatedCost(segments, idx)
            )}</span>
          </div>
        </div>
      </div>
    `).join("");
  }

  /**
   * Renderiza el itinerario completo (lista de aeropuertos)
   * @private
   */
  _renderDestinations(airports) {
    return `
      <div class="destination-list">
        <strong>✈ Itinerario Completo</strong>
        <div class="destination-badges">
          ${airports.map(airport => `<span class="dest-badge">${airport}</span>`).join("")}
        </div>
      </div>
    `;
  }

  /**
   * Muestra plan básico (2 rutas: presupuesto y tiempo)
   */
  displayBasicPlans(budgetPlan, timePlan) {
    this.container.innerHTML = `
      ${this.renderRoutePlan(budgetPlan, "💰 Mayor cantidad de destinos sin exceder presupuesto")}
      ${this.renderRoutePlan(timePlan, "⏱️ Mayor cantidad de destinos en menor tiempo")}
    `;
  }

  /**
   * Muestra rutas optimizadas para múltiples criterios
   */
  displayOptimizedRoute(routesBycriterion, origin, selectedCriteria = null) {
    // Si recibe un objeto con múltiples criterios
    if (typeof routesBycriterion === 'object' && routesBycriterion !== null && !routesBycriterion.segments) {
      return this.displayMultipleOptimizedRoutes(routesBycriterion, origin, selectedCriteria);
    }

    // Si recibe una ruta única (para retrocompatibilidad)
    const plan = {
      title: "Ruta Optimizada",
      visited_airports: [origin, ...(routesBycriterion.segments?.map(s => s.destination) || [])],
      segments: routesBycriterion.segments || [],
      total_cost: routesBycriterion.total_cost || 0,
      total_time_min: routesBycriterion.total_time_min || 0
    };
    this.container.innerHTML = this.renderRoutePlan(plan, "🎯 Ruta Optimizada");
  }

  /**
   * Muestra múltiples rutas optimizadas, una por cada criterio
   */
  displayMultipleOptimizedRoutes(allRoutes, origin, selectedCriteria = null) {
    // Si no se especifican criterios, obtenerlos de las claves del objeto
    const criteria = selectedCriteria || Object.keys(allRoutes);
    
    const criteriaLabels = {
      distancia: "🎯 Ruta óptima por Distancia",
      tiempo: "⏱️ Ruta óptima por Tiempo",
      costo: "💰 Ruta óptima por Costo"
    };

    const routeCards = criteria
      .filter(criterion => allRoutes[criterion] && allRoutes[criterion].reachable)
      .map(criterion => {
        const route = allRoutes[criterion];
        const plan = {
          title: criterion,
          visited_airports: [origin, ...(route.segments?.map(s => s.destination) || [])],
          segments: route.segments || [],
          total_cost: route.total_cost || 0,
          total_time_min: route.total_time_min || 0,
          total_distance_km: route.total_distance_km || 0
        };
        const label = criteriaLabels[criterion] || `🎯 Ruta óptima por ${criterion}`;
        return this.renderRoutePlan(plan, label);
      })
      .join("");

    // Validar si hay rutas alcanzables
    if (!routeCards) {
      this.displayEmpty("❌ No hay rutas alcanzables para los criterios seleccionados");
      return;
    }

    this.container.innerHTML = routeCards;
  }

  /**
   * Muestra mensaje de error
   */
  displayError(message) {
    this.container.innerHTML = `<div class="empty-routes">${message}</div>`;
  }

  /**
   * Muestra mensaje cuando no hay ruta con el transporte seleccionado
   */
  displayNoTransportAvailable(origin, destination, selectedAircraft) {
    const aircraftList = selectedAircraft.join(", ");
    const message = `
      <div class="empty-routes">
        <div class="no-transport-message">
          <div class="message-icon">✈️</div>
          <div class="message-title">No hay ruta disponible con el transporte seleccionado</div>
          <div class="message-details">
            <p><strong>Ruta buscada:</strong> ${origin} → ${destination}</p>
            <p><strong>Transportes seleccionados:</strong> ${aircraftList}</p>
            <p class="message-hint">Intenta seleccionar otros tipos de transporte o criterios de búsqueda.</p>
          </div>
        </div>
      </div>
    `;
    this.container.innerHTML = message;
  }

  /**
   * Muestra mensaje vacío
   */
  displayEmpty(message) {
    this.container.innerHTML = `<div class="empty-routes">${message}</div>`;
  }

  /**
   * Limpia el contenedor
   */
  clear() {
    this.container.innerHTML = "";
  }
}

export const routesRenderer = new RoutesRenderer();
