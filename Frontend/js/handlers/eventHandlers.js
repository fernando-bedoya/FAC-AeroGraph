/**
 * Event Handlers - Responsabilidad única: Manejar todos los eventos del usuario
 * Single Responsibility: Conectar UI con servicios
 */

import { graphService } from "../services/graphService.js";
import { routeService } from "../services/routeService.js";
import { dynamicPlanService } from "../services/dynamicPlanService.js";
import { graphRenderer } from "../ui/graphRenderer.js";
import { routesRenderer } from "../ui/routesRenderer.js";
import { airportInfoPanel } from "../ui/airportPanel.js";
import { debugRenderer } from "../ui/debugRenderer.js";
import { dynamicPanel } from "../ui/dynamicPanel.js";
import { animationController } from "../ui/animationController.js";
import { MESSAGES } from "../constants/config.js";

export class EventHandlers {
  constructor(refs) {
    this.refs = refs;
  }

  /**
   * Maneja la carga del archivo JSON
   */
  async handleLoadGraph(event) {
    event?.preventDefault();
    try {
      const filePath = this.refs.jsonPath.value.trim();
      if (!filePath) {
        routesRenderer.displayError("❌ Ingresa una ruta válida");
        return;
      }

      await graphService.loadGraph(filePath);
      const graphData = graphService.getGraphData();
      
      this._fillAirportSelectors(graphData.airports);
      graphRenderer.render(graphData, (airport) => this.handleAirportClick(airport));
      animationController.initialize();
      routesRenderer.displayEmpty(MESSAGES.INFO.INITIAL);
      debugRenderer.displayJSON({
        message: "✅ Red cargada correctamente",
        airports: graphData.airports.length,
        routes: graphData.routes.length,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      routesRenderer.displayError(`⚠️ ${error.message}`);
      debugRenderer.displayError(error);
    }
  }

  /**
   * Maneja el cálculo del plan básico
   */
  async handleBasicPlan(event) {
    event?.preventDefault();
    
    if (!graphService.isLoaded()) {
      routesRenderer.displayError(MESSAGES.ERRORS.NO_GRAPH);
      return;
    }

    try {
      routesRenderer.displayEmpty(MESSAGES.INFO.LOADING);
      
      const result = await routeService.calculateBasicPlan(
        this.refs.originBasic.value,
        Number(this.refs.budget.value),
        Number(this.refs.timeHours.value)
      );

      if (result.budget_route && result.time_route) {
        routesRenderer.displayBasicPlans(result.budget_route, result.time_route);
        debugRenderer.displayJSON(result);
      } else {
        routesRenderer.displayEmpty(MESSAGES.ERRORS.NO_ROUTES);
        debugRenderer.displayMessage("⚠️ No se encontraron rutas");
      }
    } catch (error) {
      routesRenderer.displayError(`⚠️ ${error.message}`);
      debugRenderer.displayError(error);
    }
  }

  /**
   * Maneja el cálculo de mejor ruta
   */
  async handleBestRoute(event) {
    event?.preventDefault();

    if (!graphService.isLoaded()) {
      routesRenderer.displayError(MESSAGES.ERRORS.NO_GRAPH);
      return;
    }

    const selectedCriteria = this._getSelectedCriteria();
    if (selectedCriteria.length === 0) {
      routesRenderer.displayError(MESSAGES.ERRORS.NO_CRITERIA);
      return;
    }

    const selectedAircraft = this._getSelectedAircraftTypes();
    if (selectedAircraft.length === 0) {
      routesRenderer.displayError("❌ Debes seleccionar al menos un tipo de transporte");
      return;
    }

    try {
      routesRenderer.displayEmpty(MESSAGES.INFO.LOADING);
      
      const origin = this.refs.origin.value;
      const destination = this.refs.destination.value;
      
      const result = await routeService.calculateBestRoute(
        origin,
        destination,
        selectedCriteria,
        this.refs.excludeSecondary.checked,
        selectedAircraft
      );

      // Filtrar rutas que no respetan los transportes seleccionados
      const filteredResult = routeService.filterRoutesByAircraft(result, selectedAircraft);
      
      // Verificar si hay al menos una ruta alcanzable con el transporte seleccionado
      const hasReachableRoute = filteredResult && Object.values(filteredResult).some(r => r.reachable);
      
      if (hasReachableRoute) {
        routesRenderer.displayOptimizedRoute(filteredResult, origin, selectedCriteria);
        debugRenderer.displayJSON(filteredResult);
      } else {
        // No hay ruta con el transporte seleccionado. Verificar si hay ruta sin el filtro
        const resultAllTransport = await routeService.calculateBestRouteAllTransport(
          origin,
          destination,
          selectedCriteria,
          this.refs.excludeSecondary.checked
        );

        // Verificar si hay ruta alcanzable sin filtro de transporte
        const hasReachableRouteAllTransport = resultAllTransport && 
          Object.values(resultAllTransport).some(r => r.reachable);

        // Si hay ruta sin transporte pero no con el seleccionado: mostrar mensaje específico
        if (hasReachableRouteAllTransport) {
          routesRenderer.displayNoTransportAvailable(
            origin,
            destination,
            selectedAircraft
          );
          debugRenderer.displayMessage(
            `⚠️ No existe ruta disponible de ${origin} a ${destination} con los transportes seleccionados: ${selectedAircraft.join(", ")}`
          );
        } else {
          // No hay ruta ni con ni sin transporte
          routesRenderer.displayEmpty(MESSAGES.ERRORS.NO_ROUTES);
          debugRenderer.displayMessage(
            `⚠️ No se encontraron rutas disponibles de ${origin} a ${destination} para los criterios seleccionados`
          );
        }
      }
    } catch (error) {
      routesRenderer.displayError(`⚠️ ${error.message}`);
      debugRenderer.displayError(error);
    }
  }

  /**
   * Maneja el bloqueo/desbloqueo de rutas
   */
  async handleBlockRoute(blocked) {
    if (!graphService.isLoaded()) {
      routesRenderer.displayError(MESSAGES.ERRORS.NO_GRAPH);
      return;
    }

    try {
      const origin = this.refs.blockOrigin.value.trim().toUpperCase();
      const destination = this.refs.blockDestination.value.trim().toUpperCase();

      if (!origin || !destination) {
        routesRenderer.displayError("❌ Ingresa origen y destino válidos");
        return;
      }

      // Si hay una sesión dinámica activa y estamos bloqueando, manejamos la interrupción
      if (dynamicPlanService.hasSession() && blocked) {
        
        // Verificamos localmente para evitar condiciones de carrera (animación vs backend)
        if (this.currentFlight && this.currentFlight.origin === origin && this.currentFlight.destination === destination) {
          this.flightInterrupted = true;
          animationController.stopCurrentFlight();
        }

        const result = await dynamicPlanService.blockRoute(origin, destination);
        
        if (result && result.was_redirected) {
          routesRenderer.displayError(`🚨 ¡Vuelo interrumpido! El viajero fue redirigido a ${result.redirected_to}. La ruta ha sido bloqueada.`);
          // Aseguramos detener la animación y marcar interrupción por si acaso no se atrapó localmente
          animationController.stopCurrentFlight();
          this.flightInterrupted = true;
        } else {
          routesRenderer.displayEmpty(`✅ Ruta Bloqueada: ${origin} → ${destination}. El viajero no fue afectado.`);
        }
        
        // Recargar el panel dinámico con el nuevo estado (incluye posibles rutas alternativas)
        if (result && result.state) {
          await this._refreshDynamicPanel(result.state);
        }
        
        // El grafo ya se recarga en dynamicPlanService.blockRoute, 
        // pero podemos asegurarnos volviendo a renderizar
        const graphData = graphService.getGraphData();
        if (graphData) {
          graphRenderer.render(graphData, (airport) => this.handleAirportClick(airport));
          animationController.initialize();
          // Asegurar resaltar la planificación actual tras redibujar el grafo
          if (result && result.state) {
            this._highlightCurrentSession(result.state);
          }
        }
      } else {
        // Bloqueo / Desbloqueo normal del grafo (sin interrupción de sesión activa o es desbloqueo)
        await graphService.blockRoute(origin, destination, blocked);
        const graphData = graphService.getGraphData();
        graphRenderer.render(graphData, (airport) => this.handleAirportClick(airport));
        animationController.initialize();
        
        // Restaurar los resaltados de la sesión activa si la hay
        if (dynamicPlanService.hasSession() && dynamicPlanService.state) {
          this._highlightCurrentSession(dynamicPlanService.state);
        }

        const action = blocked ? "Bloqueada" : "Desbloqueada";
        const message = `✅ Ruta ${action}: ${origin} → ${destination}`;
        routesRenderer.displayEmpty(message);
        debugRenderer.displayJSON({
          message: message,
          route: { origin, destination, blocked },
          timestamp: new Date().toISOString(),
        });
      }
    } catch (error) {
      routesRenderer.displayError(`⚠️ ${error.message}`);
      debugRenderer.displayError(error);
    }
  }

  /**
   * Inicia la sesion dinamica
   */
  async handleDynamicStart(event) {
    event?.preventDefault();

    if (!graphService.isLoaded()) {
      routesRenderer.displayError(MESSAGES.ERRORS.NO_GRAPH);
      return;
    }

    try {
      const state = await dynamicPlanService.start(
        this.refs.originDynamic.value,
        Number(this.refs.dynamicBudget.value),
        Number(this.refs.dynamicTimeHours.value)
      );

      // Limpiar resaltados viejos y aplicar los de la nueva sesión actual
      this._highlightCurrentSession(state);

      await this._refreshDynamicPanel(state);
      debugRenderer.displayJSON(state);
    } catch (error) {
      routesRenderer.displayError(`⚠️ ${error.message}`);
      debugRenderer.displayError(error);
    }
  }

  /**
   * Actualiza el estado dinamico
   */
  async handleDynamicRefresh(event) {
    event?.preventDefault();

    try {
      const state = await dynamicPlanService.refresh();
      this._highlightCurrentSession(state);
      await this._refreshDynamicPanel(state);
    } catch (error) {
      routesRenderer.displayError(`⚠️ ${error.message}`);
      debugRenderer.displayError(error);
    }
  }

  /**
   * Registra actividades seleccionadas
   */
  async handleDynamicActivities(event) {
    event?.preventDefault();

    try {
      const selected = this._getSelectedActivities();
      const state = await dynamicPlanService.applyActivities(selected);
      await this._refreshDynamicPanel(state);
      debugRenderer.displayJSON(state);
    } catch (error) {
      routesRenderer.displayError(`⚠️ ${error.message}`);
      debugRenderer.displayError(error);
    }
  }

  /**
   * Registra trabajo seleccionado
   */
  async handleDynamicWork(event) {
    event?.preventDefault();

    try {
      const job = this._getSelectedJob();
      if (!job) {
        routesRenderer.displayError("❌ Selecciona un trabajo disponible");
        return;
      }

      const hours = Number(this.refs.dynamicJobHours.value);
      const state = await dynamicPlanService.work(job, hours);
      await this._refreshDynamicPanel(state);
      debugRenderer.displayJSON(state);
    } catch (error) {
      routesRenderer.displayError(`⚠️ ${error.message}`);
      debugRenderer.displayError(error);
    }
  }

  /**
   * Finaliza la sesion dinamica
   */
  async handleDynamicFinish(event) {
    event?.preventDefault();

    try {
      await dynamicPlanService.finish();
      graphRenderer.resetHighlights();
      dynamicPanel.showEmpty("Sesion finalizada. Inicia una nueva sesion.");
    } catch (error) {
      routesRenderer.displayError(`⚠️ ${error.message}`);
      debugRenderer.displayError(error);
    }
  }

  /**
   * Maneja el clic en aeropuertos del grafo
   */
  handleAirportClick(airport) {
    airportInfoPanel.displayAirport(airport);
  }

  /**
   * Llena los selectores de origen y destino
   * @private
   */
  _fillAirportSelectors(airports) {
    // Obtener elementos directamente del DOM para garantizar que existan
    const origin = document.getElementById("origin");
    const destination = document.getElementById("destination");
    const originBasic = document.getElementById("originBasic");
    const originDynamic = document.getElementById("originDynamic");

    // Limpiar todos los selectores
    if (origin) origin.innerHTML = "";
    if (destination) destination.innerHTML = "";
    if (originBasic) originBasic.innerHTML = "";
    if (originDynamic) originDynamic.innerHTML = "";

    airports.forEach((airport) => {
      const option1 = document.createElement("option");
      option1.value = airport.id;
      option1.textContent = `${airport.id} - ${airport.city}`;

      const option2 = option1.cloneNode(true);
      const option3 = option1.cloneNode(true);
      const option4 = option1.cloneNode(true);

      if (origin) origin.appendChild(option1);
      if (destination) destination.appendChild(option2);
      if (originBasic) originBasic.appendChild(option3);
      if (originDynamic) originDynamic.appendChild(option4);
    });

    if (airports.length > 1) {
      if (origin) origin.value = airports[0].id;
      if (destination) destination.value = airports[1].id;
      if (originBasic) originBasic.value = airports[0].id;
      if (originDynamic) originDynamic.value = airports[0].id;
    }
  }


  /**
   * Obtiene actividades seleccionadas
   * @private
   */
  _getSelectedActivities() {
    return Array.from(document.querySelectorAll("input[name='dynamic-activity']:checked"))
      .map((input) => input.value);
  }

  /**
   * Obtiene el trabajo seleccionado
   * @private
   */
  _getSelectedJob() {
    const selected = document.querySelector("input[name='dynamic-job']:checked");
    return selected ? selected.value : null;
  }

  /**
   * Obtiene el vuelo seleccionado
   * @private
   */
  _getSelectedFlight() {
    // Buscar cualquier radio button con data-destination que esté seleccionado
    const selected = document.querySelector("input[data-destination][data-aircraft]:checked");
    if (!selected) return null;
    return {
      destination: selected.dataset.destination,
      aircraft: selected.dataset.aircraft,
    };
  }

  /**
   * Actualiza el panel dinamico
   * @private
   */
  async _refreshDynamicPanel(state) {
    dynamicPanel.renderState(state);
    routesRenderer.displaySuggestedRoute(state.suggested_route || {}, state.origin);
    dynamicPanel.renderSteps(state.steps || []);

    const [activities, jobs, flights] = await Promise.all([
      dynamicPlanService.listActivities(),
      dynamicPlanService.listJobs(),
      dynamicPlanService.listFlights(),
    ]);

    dynamicPanel.renderActivities(activities.activities || []);
    dynamicPanel.renderJobs(jobs.jobs || []);
    dynamicPanel.renderFlights(flights.options || []);
  }

  /**
   * Obtiene los criterios seleccionados
   * @private
   */
  _getSelectedCriteria() {
    return Array.from(this.refs.criteriaCheckboxes)
      .filter(checkbox => checkbox.checked)
      .map(checkbox => checkbox.value);
  }

  /**
   * Obtiene los tipos de transporte seleccionados
   * @private
   */
  _getSelectedAircraftTypes() {
    return Array.from(this.refs.aircraftCheckboxes)
      .filter(checkbox => checkbox.checked)
      .map(checkbox => checkbox.value);
  }

  async handleDynamicFly(event) {
    event?.preventDefault();

    try {
      const flight = this._getSelectedFlight();
      if (!flight) {
        routesRenderer.displayError("Selecciona un vuelo disponible");
        return;
      }

      // 1. Obtener el origen actual antes de volar (para la animación)
      const currentOrigin = dynamicPlanService.state.current_airport || this.refs.originDynamic.value;

      // 2. Llamar a flyStart para marcar en tránsito en el backend
      const startResult = await dynamicPlanService.flyStart(flight.destination, flight.aircraft);
      await this._refreshDynamicPanel(startResult);

      // Tiempo de animación
      const flightTimeMinutes = startResult.estimated_time_min || 10;
      const animationDuration = (flightTimeMinutes * 100) + 5000; // 100ms por minuto + 5s base para animación

      // Variable para controlar si el vuelo se interrumpe
      this.flightInterrupted = false;
      this.currentFlight = { origin: currentOrigin, destination: flight.destination };

      // 3. SE DISPARA LA ANIMACIÓN: Bloqueamos la ejecución visual hasta que el avion llegue
      routesRenderer.displayEmpty("✈️ Vuelo en progreso... (Puedes interrumpirlo bloqueando la ruta en el panel lateral)");
      await animationController.fly(currentOrigin, flight.destination, animationDuration);

      // Limpiamos la referencia al vuelo actual
      this.currentFlight = null;

      // 4. Termina la animación, si no fue interrumpido, confirmamos la llegada
      if (!this.flightInterrupted) {
        const finalResult = await dynamicPlanService.flyArrive();
        await this._refreshDynamicPanel(finalResult);
        debugRenderer.displayJSON(finalResult);
        routesRenderer.displayEmpty(`✅ Vuelo completado a ${flight.destination}`);
        // Resaltar todo el recorrido de la sesión actual
        this._highlightCurrentSession(finalResult);
      }

    } catch (error) {
      const cleanMessage = error.message.replace("API Error: ", "");
      alert(cleanMessage);
      routesRenderer.displayError(`⚠️ ${cleanMessage}`);
      debugRenderer.displayError(error);
      
      try {
        if (dynamicPlanService.hasSession()) {
          const refreshedState = await dynamicPlanService.refresh();
          await this._refreshDynamicPanel(refreshedState);
        }
      } catch (e) {}
    }
  }

  /**
   * Genera y muestra el reporte final en el modal
   */
  async handleGenerateReport(event) {
    event?.preventDefault();

    if (!dynamicPlanService.hasSession()) {
      routesRenderer.displayError("❌ No hay una sesión dinámica activa");
      return;
    }

    try {
      const report = await dynamicPlanService.getReport();
      this._showReportModal(report);
    } catch (error) {
      routesRenderer.displayError(`⚠️ ${error.message}`);
      debugRenderer.displayError(error);
    }
  }

  /**
   * Muestra el modal con el reporte final
   * @private
   */
  _showReportModal(report) {
    const modal = document.getElementById("report-modal");
    const content = document.getElementById("report-modal-content");
    if (!modal || !content) return;

    const fmt = (n) => (typeof n === "number" ? n.toFixed(2) : (n ?? "-"));
    const fmtMin = (m) => {
      const h = Math.floor(m / 60);
      const min = Math.round(m % 60);
      return h > 0 ? `${h}h ${min}min` : `${min}min`;
    };

    let html = `
      <div class="report-section">
        <h3>📊 Totales del Viaje</h3>
        <div class="report-totals-grid">
          <div class="report-total-card"><span>Presupuesto Inicial</span><strong>$${fmt(report.totals?.initial_budget)} USD</strong></div>
          <div class="report-total-card"><span>Total Gastado</span><strong class="spent">$${fmt(report.totals?.total_spent)} USD</strong></div>
          <div class="report-total-card"><span>Total Ganado</span><strong class="earned">$${fmt(report.totals?.total_earned)} USD</strong></div>
          <div class="report-total-card"><span>Saldo Final</span><strong class="${(report.totals?.final_budget ?? 0) >= 0 ? 'earned' : 'spent'}">$${fmt(report.totals?.final_budget)} USD</strong></div>
          <div class="report-total-card"><span>Tiempo Total</span><strong>${fmtMin(report.totals?.total_time_spent_min ?? 0)}</strong></div>
          <div class="report-total-card"><span>Total Alimentación</span><strong class="spent">$${fmt(report.totals?.total_food_cost ?? 0)} USD</strong></div>
          <div class="report-total-card"><span>Total Alojamiento</span><strong class="spent">$${fmt(report.totals?.total_lodging_cost ?? 0)} USD</strong></div>
        </div>
      </div>`;

    if (report.mandatory_fees?.length) {
      html += `
      <div class="report-section">
        <h3>💸 Detalle de Cobros Obligatorios</h3>
        <table class="report-table">
          <thead>
            <tr>
              <th>Aeropuerto</th>
              <th>Concepto</th>
              <th>Valor</th>
              <th>Momento de Aplicación</th>
            </tr>
          </thead>
          <tbody>`;
      report.mandatory_fees.forEach(fee => {
        html += `
            <tr>
              <td><strong>${fee.airport_id}</strong> - ${fee.airport_name}</td>
              <td><span class="badge ${fee.action === 'Alimentación' ? 'badge-food' : 'badge-lodging'}">${fee.action}</span></td>
              <td class="spent">$${fmt(fee.cost_usd)} USD</td>
              <td>Hace ${fmtMin(fee.moment_min)}</td>
            </tr>`;
      });
      html += `</tbody></table></div>`;
    }

    if (report.destinations?.length) {
      html += `<div class="report-section"><h3>🏙️ Destinos Visitados</h3><table class="report-table"><thead><tr><th>ID</th><th>Ciudad</th><th>País</th><th>Estadía</th><th>Costo Total</th></tr></thead><tbody>`;
      report.destinations.forEach(d => {
        html += `<tr><td>${d.id}</td><td>${d.city}</td><td>${d.country}</td><td>${fmtMin(d.stay_min)}</td><td>$${fmt(d.total_cost)} USD</td></tr>`;
      });
      html += `</tbody></table></div>`;
    }

    if (report.flights?.length) {
      html += `<div class="report-section"><h3>✈️ Tramos Volados</h3><table class="report-table"><thead><tr><th>Origen</th><th>Destino</th><th>Aeronave</th><th>Distancia</th><th>Duración</th><th>Costo</th></tr></thead><tbody>`;
      report.flights.forEach(f => {
        html += `<tr><td>${f.origin}</td><td>${f.destination}</td><td>${f.aircraft}</td><td>${fmt(f.distance_km)} km</td><td>${fmtMin(f.duration_min)}</td><td>$${fmt(f.cost_usd)} USD</td></tr>`;
      });
      html += `</tbody></table></div>`;
    }

    if (report.activities?.length) {
      html += `<div class="report-section"><h3>🎯 Actividades Realizadas</h3><table class="report-table"><thead><tr><th>Aeropuerto</th><th>Actividad</th><th>Tipo</th><th>Duración</th><th>Costo</th></tr></thead><tbody>`;
      report.activities.forEach(a => {
        html += `<tr><td>${a.airport_id}</td><td>${a.name}</td><td>${a.kind}</td><td>${fmtMin(a.duration_min)}</td><td>$${fmt(a.cost_usd)} USD</td></tr>`;
      });
      html += `</tbody></table></div>`;
    }

    if (report.jobs?.length) {
      html += `<div class="report-section"><h3>💼 Trabajos Realizados</h3><table class="report-table"><thead><tr><th>Aeropuerto</th><th>Trabajo</th><th>Horas</th><th>Ingreso</th></tr></thead><tbody>`;
      report.jobs.forEach(j => {
        html += `<tr><td>${j.airport_id}</td><td>${j.name}</td><td>${fmt(j.hours)}h</td><td>$${fmt(j.earned_usd)} USD</td></tr>`;
      });
      html += `</tbody></table></div>`;
    }

    content.innerHTML = html;
    modal.classList.add("active");
  }

  /**
   * Resalta todos los nodos y tramos de la planificación actual
   * @private
   */
  _highlightCurrentSession(state) {
    if (!state) return;
    
    // Primero, limpiar todos los resaltados
    graphRenderer.resetHighlights();
    
    // Resaltar todos los aeropuertos visitados
    if (state.visited_airports && Array.isArray(state.visited_airports)) {
      state.visited_airports.forEach(airportId => {
        graphRenderer.highlightNode(airportId);
      });
      
      // Resaltar los tramos volados (enlaces entre consecutivos)
      for (let i = 0; i < state.visited_airports.length - 1; i++) {
        const origin = state.visited_airports[i];
        const destination = state.visited_airports[i + 1];
        graphRenderer.highlightEdge(origin, destination);
      }
    } else if (state.current_airport) {
      // Si no hay lista de visitados pero hay aeropuerto actual (por si acaso)
      graphRenderer.highlightNode(state.current_airport);
    }
  }
}
