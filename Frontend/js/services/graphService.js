/**
 * Graph Service - Responsabilidad única: Lógica de datos del grafo
 * Single Responsibility: Manejar estado y lógica del grafo
 */

import { apiClient } from "../api/client.js";

class GraphService {
  constructor() {
    this.graph = null;
    this.aircraft = null;
    this.rules = null;
  }

  /**
   * Carga el grafo desde archivo JSON
   */
  async loadGraph(filePath) {
    const result = await apiClient.loadGraph(filePath);
    await this.refreshGraph();
    return result;
  }

  /**
   * Refresca los datos del grafo desde el backend sin recargar el archivo JSON original
   */
  async refreshGraph() {
    const graphData = await apiClient.getGraph();
    this.graph = graphData;
    this.aircraft = graphData.aircraftConfig;
    this.rules = graphData.rules;
    return graphData;
  }

  /**
   * Obtiene todos los aeropuertos
   */
  getAirports() {
    return this.graph?.airports || [];
  }

  /**
   * Obtiene todas las rutas
   */
  getRoutes() {
    return this.graph?.routes || [];
  }

  /**
   * Obtiene un aeropuerto por código
   */
  getAirport(code) {
    return this.getAirports().find(a => a.id === code);
  }

  /**
   * Verifica si el grafo está cargado
   */
  isLoaded() {
    return this.graph !== null;
  }

  /**
   * Obtiene los datos completos del grafo
   */
  getGraphData() {
    return this.graph;
  }

  /**
   * Bloquea o desbloquea una ruta
   */
  async blockRoute(origin, destination, blocked) {
    const result = await apiClient.blockRoute(origin, destination, blocked);
    // Actualizar estado local
    await this.refreshGraph();
    return result;
  }
}

export const graphService = new GraphService();
