/**
 * Dynamic Plan Service - Responsabilidad unica: Gestion del flujo dinamico 2.3
 * Single Responsibility: Manejar sesion y llamadas dinamicas
 */

import { apiClient } from "../api/client.js";
import { animationController } from '../ui/animationController.js';

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
     * Puede causar que viajeros en tránsito sean redirigidos al aeropuerto de origen
     */
    return await apiClient.blockRoute(origin, destination, true);
  }
}

export const dynamicPlanService = new DynamicPlanService();
