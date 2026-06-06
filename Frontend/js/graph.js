/**
 * 3D Globe Visualization Module
 * 
 * This module implements an interactive 3D globe using D3.js with orthographic projection.
 * It displays airports as nodes and airline routes as great circle arcs.
 * 
 * Key features:
 * - Orthographic projection for realistic globe appearance
 * - Real country boundaries loaded from TopoJSON world atlas
 * - Great circle interpolation for accurate flight paths
 * - Interactive rotation (drag) and zoom (scroll)
 * - Flight animation along great circle paths
 * - Visual highlighting for visited airports and routes
 * 
 * Technical details:
 * - Uses D3.js v7 for projections and path generation
 * - Loads world boundaries from world-atlas@2 (110m resolution)
 * - Great circle math: Uses spherical geometry for accurate paths
 * - Animation: requestAnimationFrame for smooth 60fps rendering
 */

// Globe configuration constants
const GLOBE_CONFIG = {
  WORLD_DATA_URL: "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json",
  OCEAN_COLOR: "#1a4d6e",
  LAND_COLOR: "#3d7a4a",
  LAND_BORDER: "#2a5a3a",
  GLOBE_EDGE: "#0d2d4a",
  GRATICULE_COLOR: "rgba(255,255,255,0.08)",
  NODE_HUB_RADIUS: 7,
  NODE_REGULAR_RADIUS: 5,
  ARC_SEGMENTS: 100,
};

// Color palette for visualization
const COLORS = {
  HUB: "#ef4444",        // Red for hub airports
  NODE: "#14b8a6",       // Teal for regular airports
  ARC: "#f59e0b",        // Amber for routes
  ARC_BLOCKED: "#dc2626", // Red for blocked routes
  ARC_HIGHLIGHT: "#10b981", // Green for highlighted routes
  PLANE: "#fbbf24",      // Yellow for airplane
  LABEL: "#f5f0e8",      // Light text color
};

// Estado del módulo
let svg = null;
let projection = null;
let pathGenerator = null;
let globeGroup = null;
let nodesGroup = null;
let arcsGroup = null;
let planeElement = null;
let worldData = null;
let currentGraphData = null;
let onNodeClickCallback = null;
let rotation = [-70, -15]; // Centrado en Latinoamérica
let isDragging = false;
let dragStart = null;
let glowFilter = null;

// Animación de vuelo
let animationFrameId = null;
let flightStartTime = null;
let flightDurationMs = 0;
let flightPath = null;
let onFlightCompleteCallback = null;

// Cargar datos del mundo
async function loadWorldData() {
  if (worldData) return worldData;
  try {
    const response = await fetch(GLOBE_CONFIG.WORLD_DATA_URL);
    const world = await response.json();
    worldData = topojson.feature(world, world.objects.countries);
    return worldData;
  } catch (error) {
    console.error("Error cargando datos del mundo:", error);
    return null;
  }
}

// --- Animación de vuelo ---

/**
 * Calculate the bearing (heading) between two points on a great circle.
 * Returns the angle in degrees from north (0° = north, 90° = east, etc.)
 * 
 * @param {Array} start - [longitude, latitude] of start point
 * @param {Array} end - [longitude, latitude] of end point
 * @returns {number} Bearing in degrees
 */
function calculateBearing(start, end) {
  const [lon1, lat1] = start;
  const [lon2, lat2] = end;
  
  const phi1 = lat1 * Math.PI / 180;
  const phi2 = lat2 * Math.PI / 180;
  const deltaLambda = (lon2 - lon1) * Math.PI / 180;
  
  const y = Math.sin(deltaLambda) * Math.cos(phi2);
  const x = Math.cos(phi1) * Math.sin(phi2) - Math.sin(phi1) * Math.cos(phi2) * Math.cos(deltaLambda);
  
  const bearing = Math.atan2(y, x) * 180 / Math.PI;
  return (bearing + 360) % 360;
}

function flightLoop(timestamp) {
  if (!flightStartTime) flightStartTime = timestamp;

  const elapsed = timestamp - flightStartTime;
  const progress = Math.min(elapsed / flightDurationMs, 1);

  if (flightPath && planeElement && projection) {
    const point = getPointOnGreatCircle(flightPath.start, flightPath.end, progress);
    const projected = projection(point);
    if (projected && isPointVisible(point)) {
      // Calculate bearing for plane rotation
      const bearing = calculateBearing(flightPath.start, flightPath.end);
      planeElement
        .attr("transform", `translate(${projected[0]}, ${projected[1]}) rotate(${bearing})`)
        .style("display", "block");
    } else {
      planeElement.style("display", "none");
    }
  }

  if (progress < 1) {
    animationFrameId = requestAnimationFrame(flightLoop);
  } else {
    if (planeElement) planeElement.style("display", "none");
    if (onFlightCompleteCallback) {
      const cb = onFlightCompleteCallback;
      onFlightCompleteCallback = null;
      cb();
    }
  }
}

// Interpolación a lo largo de un gran círculo (great circle)
function getPointOnGreatCircle(start, end, t) {
  const [lon1, lat1] = start;
  const [lon2, lat2] = end;

  // Convertir a radianes
  const phi1 = (lat1 * Math.PI) / 180;
  const lambda1 = (lon1 * Math.PI) / 180;
  const phi2 = (lat2 * Math.PI) / 180;
  const lambda2 = (lon2 * Math.PI) / 180;

  // Calcular distancia angular
  const d = 2 * Math.asin(
    Math.sqrt(
      Math.pow(Math.sin((phi2 - phi1) / 2), 2) +
      Math.cos(phi1) * Math.cos(phi2) * Math.pow(Math.sin((lambda2 - lambda1) / 2), 2)
    )
  );

  if (d === 0) return start;

  // Interpolación a lo largo del gran círculo
  const a = Math.sin((1 - t) * d) / Math.sin(d);
  const b = Math.sin(t * d) / Math.sin(d);

  const x = a * Math.cos(phi1) * Math.cos(lambda1) + b * Math.cos(phi2) * Math.cos(lambda2);
  const y = a * Math.cos(phi1) * Math.sin(lambda1) + b * Math.cos(phi2) * Math.sin(lambda2);
  const z = a * Math.sin(phi1) + b * Math.sin(phi2);

  const lat = Math.atan2(z, Math.sqrt(x * x + y * y)) * 180 / Math.PI;
  const lon = Math.atan2(y, x) * 180 / Math.PI;

  return [lon, lat];
}

export function fly(originId, destinationId, durationMs) {
  return new Promise((resolve) => {
    if (!currentGraphData || !projection) {
      resolve();
      return;
    }

    const origin = currentGraphData.airports.find((a) => a.id === originId);
    const destination = currentGraphData.airports.find((a) => a.id === destinationId);

    if (!origin || !destination) {
      resolve();
      return;
    }

    flightPath = {
      start: [origin.lon, origin.lat],
      end: [destination.lon, destination.lat],
    };

    flightDurationMs = durationMs;
    flightStartTime = null;
    onFlightCompleteCallback = resolve;

    if (planeElement) {
      planeElement.style("display", "block");
      const startPoint = projection(flightPath.start);
      if (startPoint) {
        // Calculate initial bearing
        const bearing = calculateBearing(flightPath.start, flightPath.end);
        planeElement.attr("transform", `translate(${startPoint[0]}, ${startPoint[1]}) rotate(${bearing})`);
      }
    }

    animationFrameId = requestAnimationFrame(flightLoop);
  });
}

export function stopFlight() {
  cancelAnimationFrame(animationFrameId);
  if (planeElement) planeElement.style("display", "none");
  if (onFlightCompleteCallback) {
    const cb = onFlightCompleteCallback;
    onFlightCompleteCallback = null;
    cb();
  }
}

export function pauseFlight() {
  cancelAnimationFrame(animationFrameId);
}

export function resumeFlight() {
  if (flightPath) {
    animationFrameId = requestAnimationFrame(flightLoop);
  }
}

// --- Renderizado del globo ---

function drawGlobe() {
  if (!globeGroup || !pathGenerator) return;

  // Océano con gradiente
  globeGroup.selectAll(".ocean").remove();
  globeGroup.append("path")
    .datum({ type: "Sphere" })
    .attr("class", "ocean")
    .attr("d", pathGenerator)
    .attr("fill", "url(#ocean-gradient)")
    .attr("stroke", GLOBE_CONFIG.GLOBE_EDGE)
    .attr("stroke-width", 2);

  // Países
  if (worldData) {
    globeGroup.selectAll(".country").remove();
    globeGroup.selectAll(".country")
      .data(worldData.features)
      .join("path")
      .attr("class", "country")
      .attr("d", pathGenerator)
      .attr("fill", GLOBE_CONFIG.LAND_COLOR)
      .attr("stroke", GLOBE_CONFIG.LAND_BORDER)
      .attr("stroke-width", 0.5);
  }

  // Grilla (meridianos y paralelos)
  globeGroup.selectAll(".graticule").remove();
  const graticule = d3.geoGraticule10();
  globeGroup.append("path")
    .datum(graticule)
    .attr("class", "graticule")
    .attr("d", pathGenerator)
    .attr("fill", "none")
    .attr("stroke", GLOBE_CONFIG.GRATICULE_COLOR)
    .attr("stroke-width", 0.5);
}

function drawNodes() {
  if (!nodesGroup || !currentGraphData || !projection) return;

  nodesGroup.selectAll("*").remove();

  const visibleAirports = currentGraphData.airports.filter((a) => {
    return isPointVisible([a.lon, a.lat]);
  });

  const nodes = nodesGroup.selectAll("g.node")
    .data(visibleAirports)
    .join("g")
    .attr("class", "node")
    .attr("transform", (d) => {
      const p = projection([d.lon, d.lat]);
      return p ? `translate(${p[0]}, ${p[1]})` : "translate(-9999,-9999)";
    })
    .style("cursor", "pointer")
    .on("click", (event, d) => {
      if (onNodeClickCallback) onNodeClickCallback(d);
    });

  // Halo exterior con glow
  nodes.append("circle")
    .attr("r", (d) => (d.isHub ? GLOBE_CONFIG.NODE_HUB_RADIUS + 4 : GLOBE_CONFIG.NODE_REGULAR_RADIUS + 3))
    .attr("fill", "none")
    .attr("stroke", (d) => (d.isHub ? COLORS.HUB : COLORS.NODE))
    .attr("stroke-width", 1.5)
    .attr("stroke-opacity", 0.4)
    .attr("filter", "url(#glow)");

  // Círculo principal
  nodes.append("circle")
    .attr("class", "node-circle")
    .attr("id", (d) => `node-${d.id}`)
    .attr("r", (d) => (d.isHub ? GLOBE_CONFIG.NODE_HUB_RADIUS : GLOBE_CONFIG.NODE_REGULAR_RADIUS))
    .attr("fill", (d) => (d.isHub ? COLORS.HUB : COLORS.NODE))
    .attr("stroke", "#fff")
    .attr("stroke-width", 2)
    .attr("filter", "url(#glow)");

  // Etiquetas
  nodes.append("text")
    .attr("class", "node-label")
    .attr("dy", -14)
    .attr("text-anchor", "middle")
    .attr("fill", COLORS.LABEL)
    .attr("font-size", 11)
    .attr("font-weight", "bold")
    .attr("stroke", "#000")
    .attr("stroke-width", 2)
    .attr("paint-order", "stroke")
    .text((d) => d.id);
}

function drawArcs() {
  if (!arcsGroup || !currentGraphData || !projection) return;

  arcsGroup.selectAll("*").remove();

  const routes = currentGraphData.routes.map((r) => {
    const origin = currentGraphData.airports.find((a) => a.id === r.origin);
    const destination = currentGraphData.airports.find((a) => a.id === r.destination);
    return {
      ...r,
      originCoord: origin ? [origin.lon, origin.lat] : null,
      destinationCoord: destination ? [destination.lon, destination.lat] : null,
    };
  }).filter((r) => r.originCoord && r.destinationCoord)
    .sort((a, b) => (a.blocked ? 1 : 0) - (b.blocked ? 1 : 0));

  routes.forEach((route) => {
    // Generar puntos a lo largo del gran círculo
    const arcPoints = [];
    for (let i = 0; i <= GLOBE_CONFIG.ARC_SEGMENTS; i++) {
      const t = i / GLOBE_CONFIG.ARC_SEGMENTS;
      const point = getPointOnGreatCircle(route.originCoord, route.destinationCoord, t);
      arcPoints.push(point);
    }

    // Filtrar puntos visibles
    const visiblePoints = arcPoints.filter((p) => isPointVisible(p));

    if (visiblePoints.length < 2) return;

    // Dibujar el arco
    const lineGenerator = d3.line()
      .x((p) => {
        const proj = projection(p);
        return proj ? proj[0] : -9999;
      })
      .y((p) => {
        const proj = projection(p);
        return proj ? proj[1] : -9999;
      })
      .defined((p) => isPointVisible(p))
      .curve(d3.curveLinear);

    // Sombra del arco
    arcsGroup.append("path")
      .datum(visiblePoints)
      .attr("class", "arc-shadow")
      .attr("id", `arc-shadow-${route.origin}-${route.destination}`)
      .attr("d", lineGenerator)
      .attr("fill", "none")
      .attr("stroke", route.blocked ? COLORS.ARC_BLOCKED : COLORS.ARC)
      .attr("stroke-width", route.blocked ? 4 : 2.5)
      .attr("stroke-opacity", 0.3)
      .attr("filter", "url(#glow)");

    // Arco principal
    arcsGroup.append("path")
      .datum(visiblePoints)
      .attr("class", "arc")
      .attr("id", `arc-${route.origin}-${route.destination}`)
      .attr("d", lineGenerator)
      .attr("fill", "none")
      .attr("stroke", route.blocked ? COLORS.ARC_BLOCKED : COLORS.ARC)
      .attr("stroke-width", route.blocked ? 2.5 : 1.8)
      .attr("stroke-dasharray", route.blocked ? "6,4" : "none")
      .attr("stroke-opacity", 0.9)
      .attr("stroke-linecap", "round");

    // Etiqueta de distancia en el punto medio
    const midPoint = arcPoints[Math.floor(arcPoints.length / 2)];
    if (isPointVisible(midPoint)) {
      const midProjected = projection(midPoint);
      if (midProjected) {
        arcsGroup.append("text")
          .attr("x", midProjected[0])
          .attr("y", midProjected[1] - 8)
          .attr("text-anchor", "middle")
          .attr("fill", "#a8cce8")
          .attr("font-size", 9)
          .attr("font-weight", "500")
          .attr("stroke", "#000")
          .attr("stroke-width", 1.5)
          .attr("paint-order", "stroke")
          .text(`${Math.round(route.distanceKm)} km`);
      }
    }
  });
}

function isPointVisible(coord) {
  const rotated = projection.rotate();
  const center = [-rotated[0], -rotated[1]];
  const distance = d3.geoDistance(coord, center);
  return distance < Math.PI / 2;
}

function updateView() {
  if (!projection) return;
  projection.rotate(rotation);
  drawGlobe();
  drawNodes();
  drawArcs();
}

function createFilters(svg) {
  const defs = svg.append("defs");

  // Gradiente del océano
  const oceanGradient = defs.append("radialGradient")
    .attr("id", "ocean-gradient")
    .attr("cx", "30%")
    .attr("cy", "30%")
    .attr("r", "70%");

  oceanGradient.append("stop")
    .attr("offset", "0%")
    .attr("stop-color", "#2a6a8e");

    oceanGradient.append("stop")
    .attr("offset", "100%")
    .attr("stop-color", "#0d3d5a");

  // Filtro de glow
  const glowFilter = defs.append("filter")
    .attr("id", "glow")
    .attr("x", "-50%")
    .attr("y", "-50%")
    .attr("width", "200%")
    .attr("height", "200%");

  glowFilter.append("feGaussianBlur")
    .attr("stdDeviation", "2")
    .attr("result", "coloredBlur");

  const feMerge = glowFilter.append("feMerge");
  feMerge.append("feMergeNode").attr("in", "coloredBlur");
  feMerge.append("feMergeNode").attr("in", "SourceGraphic");
}

export async function renderGraph(graphData, onNodeClick) {
  const container = document.querySelector("#graph");
  const width = container.clientWidth || 800;
  const height = container.clientHeight || 600;

  currentGraphData = graphData;
  onNodeClickCallback = onNodeClick;

  // Cargar datos del mundo si no están cargados
  if (!worldData) {
    await loadWorldData();
  }

  d3.select(container).selectAll("*").remove();

  svg = d3.select(container)
    .append("svg")
    .attr("width", width)
    .attr("height", height);

  // Crear filtros
  createFilters(svg);

  // Proyección ortográfica (globo)
  projection = d3.geoOrthographic()
    .scale(Math.min(width, height) / 2.3)
    .translate([width / 2, height / 2])
    .rotate(rotation)
    .clipAngle(90);

  pathGenerator = d3.geoPath().projection(projection);

  // Grupos
  globeGroup = svg.append("g").attr("class", "globe");
  arcsGroup = svg.append("g").attr("class", "arcs");
  nodesGroup = svg.append("g").attr("class", "nodes");

  // Avión (icono SVG tipo Flightradar24)
  planeElement = svg.append("g")
    .attr("class", "plane-icon")
    .style("display", "none");
  
  // Path de avión apuntando hacia arriba (norte)
  planeElement.append("path")
    .attr("d", "M0,-10 L2,-6 L8,-2 L8,0 L2,-1 L2,4 L4,6 L4,8 L0,7 L-4,8 L-4,6 L-2,4 L-2,-1 L-8,0 L-8,-2 L-2,-6 Z")
    .attr("fill", COLORS.PLANE)
    .attr("stroke", "#000")
    .attr("stroke-width", 0.8)
    .style("filter", "url(#glow)");

  // Interactividad - arrastrar para rotar
  svg.call(d3.drag()
    .on("start", (event) => {
      isDragging = true;
      dragStart = [event.sourceEvent.clientX, event.sourceEvent.clientY];
    })
    .on("drag", (event) => {
      if (!isDragging) return;
      const currentPos = [event.sourceEvent.clientX, event.sourceEvent.clientY];
      const dx = currentPos[0] - dragStart[0];
      const dy = currentPos[1] - dragStart[1];

      const sensitivity = 0.4;
      rotation[0] += dx * sensitivity;
      rotation[1] = Math.max(-80, Math.min(80, rotation[1] - dy * sensitivity));

      dragStart = currentPos;
      updateView();
    })
    .on("end", () => {
      isDragging = false;
    }));

  // Zoom
  svg.call(d3.zoom()
    .scaleExtent([0.5, 5])
    .on("zoom", (event) => {
      const newScale = Math.min(width, height) / 2.3 * event.transform.k;
      projection.scale(newScale);
      updateView();
    }));

  updateView();
}

// --- Highlights ---

export function highlightNode(nodeId) {
  if (!svg) return;
  svg.select(`#node-${nodeId}`)
    .transition().duration(500)
    .attr("r", 12)
    .attr("fill", COLORS.ARC_HIGHLIGHT)
    .attr("stroke", "#fff")
    .attr("stroke-width", 3);
}

export function highlightEdge(originId, destId) {
  if (!svg) return;
  svg.select(`#arc-${originId}-${destId}`)
    .transition().duration(500)
    .attr("stroke", COLORS.ARC_HIGHLIGHT)
    .attr("stroke-width", 4)
    .attr("stroke-opacity", 1);
}

export function resetHighlights() {
  if (!svg || !currentGraphData) return;

  svg.selectAll(".node-circle")
    .transition().duration(500)
    .attr("r", (d) => (d.isHub ? GLOBE_CONFIG.NODE_HUB_RADIUS : GLOBE_CONFIG.NODE_REGULAR_RADIUS))
    .attr("fill", (d) => (d.isHub ? COLORS.HUB : COLORS.NODE))
    .attr("stroke", "#fff")
    .attr("stroke-width", 2);

  svg.selectAll(".arc-shadow")
    .transition().duration(500)
    .attr("stroke", function() {
      const id = d3.select(this).attr("id");
      if (!id) return COLORS.ARC;
      const parts = id.replace("arc-shadow-", "").split("-");
      const route = currentGraphData.routes.find(r => r.origin === parts[0] && r.destination === parts[1]);
      return route?.blocked ? COLORS.ARC_BLOCKED : COLORS.ARC;
    })
    .attr("stroke-width", function() {
      const id = d3.select(this).attr("id");
      if (!id) return 2.5;
      const parts = id.replace("arc-shadow-", "").split("-");
      const route = currentGraphData.routes.find(r => r.origin === parts[0] && r.destination === parts[1]);
      return route?.blocked ? 4 : 2.5;
    })
    .attr("stroke-opacity", 0.3);

  svg.selectAll(".arc")
    .transition().duration(500)
    .attr("stroke", function() {
      const id = d3.select(this).attr("id");
      if (!id) return COLORS.ARC;
      const parts = id.replace("arc-", "").split("-");
      const route = currentGraphData.routes.find(r => r.origin === parts[0] && r.destination === parts[1]);
      return route?.blocked ? COLORS.ARC_BLOCKED : COLORS.ARC;
    })
    .attr("stroke-width", function() {
      const id = d3.select(this).attr("id");
      if (!id) return 1.8;
      const parts = id.replace("arc-", "").split("-");
      const route = currentGraphData.routes.find(r => r.origin === parts[0] && r.destination === parts[1]);
      return route?.blocked ? 2.5 : 1.8;
    })
    .attr("stroke-dasharray", function() {
      const id = d3.select(this).attr("id");
      if (!id) return "none";
      const parts = id.replace("arc-", "").split("-");
      const route = currentGraphData.routes.find(r => r.origin === parts[0] && r.destination === parts[1]);
      return route?.blocked ? "6,4" : "none";
    })
    .attr("stroke-opacity", 0.9);
}

export function getSvg() {
  return svg;
}
