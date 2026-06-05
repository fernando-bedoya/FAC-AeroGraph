/**
 * Dynamic Plan Service - Responsabilidad unica: Gestion del flujo dinamico 2.3
 * Single Responsibility: Manejar sesion y llamadas dinamicas
 */

import { apiClient } from "../api/client.js";
import { animationController } from '../ui/animationController.js';
import { graphService } from "./graphService.js";

class DynamicPlanService {
  constructor() {
    this.sessionId = null;
    this.state = null;
  }

  hasSession() {
    return Boolean(this.sessionId);
  }

  async start(origin, budget, hours) {
    const result = await apiClient.dynamicStart(origin, budget, hours);
    this.sessionId = result.session_id;
    this.state = result;
    return result;
  }

  async refresh() {
    if (!this.sessionId) {
      throw new Error("No hay sesion dinamica activa");
    }
    const result = await apiClient.dynamicState(this.sessionId);
    this.state = result;
    return result;
  }

  async listActivities() {
    if (!this.sessionId) {
      throw new Error("No hay sesion dinamica activa");
    }
    return await apiClient.dynamicActivities(this.sessionId);
  }

  async applyActivities(activities) {
    if (!this.sessionId) {
      throw new Error("No hay sesion dinamica activa");
    }
    const result = await apiClient.dynamicChooseActivities(this.sessionId, activities);
    this.state = result;
    return result;
  }

  async listJobs() {
    if (!this.sessionId) {
      throw new Error("No hay sesion dinamica activa");
    }
    return await apiClient.dynamicJobs(this.sessionId);
  }

  async work(jobName, hours) {
    if (!this.sessionId) {
      throw new Error("No hay sesion dinamica activa");
    }
    const result = await apiClient.dynamicWork(this.sessionId, jobName, hours);
    this.state = result;
    return result;
  }

  async listFlights() {
    if (!this.sessionId) {
      throw new Error("No hay sesion dinamica activa");
    }
    return await apiClient.dynamicFlightOptions(this.sessionId);
  }

  async fly(destination, aircraft) {
    if (!this.sessionId) {
      throw new Error("No hay sesion dinamica activa");
    }
    const result = await apiClient.dynamicFly(this.sessionId, destination, aircraft);
    this.state = result;
    return result;
  }

  async flyStart(destination, aircraft) {
    if (!this.sessionId) {
      throw new Error("No hay sesion dinamica activa");
    }
    const result = await apiClient.dynamicFlyStart(this.sessionId, destination, aircraft);
    this.state = result;
    return result;
  }

  async flyArrive() {
    if (!this.sessionId) {
      throw new Error("No hay sesion dinamica activa");
    }
    const result = await apiClient.dynamicFlyArrive(this.sessionId);
    this.state = result;
    return result;
  }

  async finish() {
    if (!this.sessionId) {
      return;
    }
    await apiClient.dynamicFinish(this.sessionId);
    this.sessionId = null;
    this.state = null;
  }

  async blockRoute(origin, destination) {
    /**
     * Bloquea una ruta durante la simulación
     * Si hay una sesión activa, ejecuta la interrupción con redirección y recalculación
     */
    if (this.sessionId) {
      const result = await apiClient.simulationInterrupt(this.sessionId, origin, destination);
      this.state = result.state;
      
      // Actualizar datos del grafo localmente para reflejar la ruta bloqueada en rojo
      if (graphService.isLoaded()) {
        try {
          await graphService.refreshGraph();
        } catch (e) {
          console.error("No se pudo recargar el grafo tras la interrupción:", e);
        }
      }
      
      return result;
    }
    return await apiClient.blockRoute(origin, destination, true);
  }

  async getReport() {
    if (!this.sessionId) {
      throw new Error("No hay sesion dinamica activa");
    }
    return await apiClient.dynamicReport(this.sessionId);
  }
}

export const dynamicPlanService = new DynamicPlanService();
