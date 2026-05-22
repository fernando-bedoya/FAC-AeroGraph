/**
 * Graph Renderer - Responsabilidad única: Renderizar el grafo con D3.js
 * Single Responsibility: Visualizar red aérea con D3
 */

import { CONFIG, COLORS } from "../constants/config.js";

class GraphRenderer {
  constructor(containerSelector = "#graph") {
    this.container = document.querySelector(containerSelector);
    this.svg = null;
    this.simulation = null;
  }

  /**
   * Renderiza el grafo completo
   */
  render(graphData, onNodeClick) {
    const width = this.container.clientWidth || CONFIG.UI.GRAPH.MIN_WIDTH;
    const height = this.container.clientHeight || CONFIG.UI.GRAPH.MIN_HEIGHT;

    this._cleanup();
    this._initSvg(width, height);
    this._createMarkers();
    
    const { nodes, links } = this._prepareData(graphData);
    
    this._createForceSimulation(nodes, links, width, height);
    this._renderLinks(links);
    this._renderLinkLabels(links);
    this._renderNodes(nodes, onNodeClick);
    this._renderNodeLabels(nodes);
  }

  /**
   * Limpia la visualización anterior
   * @private
   */
  _cleanup() {
    if (this.simulation) {
      this.simulation.stop();
    }
    d3.select(this.container).selectAll("*").remove();
  }

  /**
   * Inicializa el SVG
   * @private
   */
  _initSvg(width, height) {
    this.svg = d3
      .select(this.container)
      .append("svg")
      .attr("width", width)
      .attr("height", height)
      .attr("viewBox", [0, 0, width, height]);
  }

  /**
   * Crea marcadores de flechas
   * @private
   */
  _createMarkers() {
    const defs = this.svg.append("defs");

    // Flecha normal
    defs
      .append("marker")
      .attr("id", "arrow")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", CONFIG.UI.GRAPH.MARKER_REF_X)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", COLORS.ARROW);

    // Flecha bloqueada
    defs
      .append("marker")
      .attr("id", "arrow-blocked")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", CONFIG.UI.GRAPH.MARKER_REF_X)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", COLORS.ARROW_BLOCKED);
  }

  /**
   * Prepara datos de nodos y enlaces
   * @private
   */
  _prepareData(graphData) {
    const nodes = graphData.airports.map((a) => ({
      id: a.id,
      name: a.name,
      city: a.city,
      country: a.country,
      timezone: a.timezone,
      isHub: a.isHub,
      aircraftTypes: a.aircraftTypes || [],
    }));

    const links = graphData.routes.map((r) => ({
      source: r.origin,
      target: r.destination,
      distanceKm: r.distanceKm,
      blocked: r.blocked,
      aircraft: r.aircraftTypes.join(", "),
    }));

    return { nodes, links };
  }

  /**
   * Crea la simulación de fuerzas
   * @private
   */
  _createForceSimulation(nodes, links, width, height) {
    this.simulation = d3
      .forceSimulation(nodes)
      .force(
        "link",
        d3
          .forceLink(links)
          .id((d) => d.id)
          .distance((d) => CONFIG.UI.GRAPH.FORCE_LINK_DISTANCE(d.distanceKm))
      )
      .force("charge", d3.forceManyBody().strength(CONFIG.UI.GRAPH.FORCE_CHARGE))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force(
        "collision",
        d3.forceCollide().radius((d) => (d.isHub ? 24 : 18))
      );
  }

  /**
   * Renderiza enlaces (rutas)
   * @private
   */
  _renderLinks(links) {
    this.svg
      .append("g")
      .attr("stroke-opacity", 0.9)
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", (d) => (d.blocked ? COLORS.ARROW_BLOCKED : COLORS.ARROW))
      .attr("stroke-width", (d) => (d.blocked ? 2.8 : 1.8))
      .attr("stroke-dasharray", (d) => (d.blocked ? "6 3" : "0"))
      .attr("marker-end", (d) => (d.blocked ? "url(#arrow-blocked)" : "url(#arrow)"));
  }

  /**
   * Renderiza etiquetas de enlaces
   * @private
   */
  _renderLinkLabels(links) {
    this.linkLabels = this.svg
      .append("g")
      .attr("class", "link-labels")
      .selectAll("text")
      .data(links)
      .join("text")
      .text((d) => `${d.distanceKm} km`)
      .attr("font-size", 10)
      .attr("fill", "#ccecff")
      .attr("text-anchor", "middle")
      .attr("pointer-events", "none");
  }

  /**
   * Renderiza nodos (aeropuertos)
   * @private
   */
  _renderNodes(nodes, onNodeClick) {
    const drag = this._createDragBehavior();

    this.svg
      .append("g")
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr("r", (d) => (d.isHub ? CONFIG.UI.GRAPH.NODE_HUB_RADIUS : CONFIG.UI.GRAPH.NODE_REGULAR_RADIUS))
      .attr("fill", (d) => (d.isHub ? COLORS.HUB : COLORS.NODE))
      .attr("stroke", "#12354d")
      .attr("stroke-width", 2)
      .call(drag(this.simulation))
      .on("click", (_, d) => onNodeClick(d));
  }

  /**
   * Renderiza etiquetas de nodos
   * @private
   */
  _renderNodeLabels(nodes) {
    this.nodeLabels = this.svg
      .append("g")
      .attr("class", "node-labels")
      .selectAll("text")
      .data(nodes)
      .join("text")
      .text((d) => d.id)
      .attr("font-size", 11)
      .attr("fill", "#ecf7ff")
      .attr("text-anchor", "middle")
      .attr("dy", 4)
      .attr("pointer-events", "none");

    this._setupTickHandlers();
  }

  /**
   * Configura el manejador de tick para actualizar posiciones
   * @private
   */
  _setupTickHandlers() {
    const links = this.svg.selectAll("line");
    const circles = this.svg.selectAll("circle");
    const linkLabels = this.linkLabels;
    const nodeLabels = this.nodeLabels;

    this.simulation.on("tick", () => {
      // Actualizar enlaces
      links
        .attr("x1", (d) => d.source.x)
        .attr("y1", (d) => d.source.y)
        .attr("x2", (d) => d.target.x)
        .attr("y2", (d) => d.target.y);

      // Actualizar nodos
      circles
        .attr("cx", (d) => d.x)
        .attr("cy", (d) => d.y);

      // Actualizar etiquetas de nodos
      nodeLabels
        .attr("x", (d) => d.x)
        .attr("y", (d) => d.y);

      // Actualizar etiquetas de enlaces
      linkLabels
        .attr("x", (d) => (d.source.x + d.target.x) / 2)
        .attr("y", (d) => (d.source.y + d.target.y) / 2 - 6);
    });
  }

  /**
   * Crea el comportamiento de arrastre
   * @private
   */
  _createDragBehavior() {
    const sim = this.simulation;

    return (simulation) => {
      function dragstarted(event, d) {
        if (!event.active) {
          simulation.alphaTarget(0.3).restart();
        }
        d.fx = d.x;
        d.fy = d.y;
      }

      function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
      }

      function dragended(event, d) {
        if (!event.active) {
          simulation.alphaTarget(0);
        }
        d.fx = null;
        d.fy = null;
      }

      return d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended);
    };
  }
}

export const graphRenderer = new GraphRenderer();
