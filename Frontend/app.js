const API_BASE = "http://127.0.0.1:8000/api";

const refs = {
  jsonPath: document.getElementById("jsonPath"),
  origin: document.getElementById("origin"),
  destination: document.getElementById("destination"),
  criteria: document.getElementById("criteria"),
  excludeSecondary: document.getElementById("excludeSecondary"),
  budget: document.getElementById("budget"),
  timeHours: document.getElementById("timeHours"),
  blockOrigin: document.getElementById("blockOrigin"),
  blockDestination: document.getElementById("blockDestination"),
  output: document.getElementById("output"),
  airportInfo: document.getElementById("airportInfo"),
  btnLoad: document.getElementById("btnLoad"),
  btnBestRoute: document.getElementById("btnBestRoute"),
  btnBasic: document.getElementById("btnBasic"),
  btnBlock: document.getElementById("btnBlock"),
  btnUnblock: document.getElementById("btnUnblock"),
};

let svg = null;
let simulation = null;
let cachedGraph = null;

function generateFaviconFromCollage() {
  const collage = new Image();
  collage.src = "assets/img/logotipos.png";

  collage.onload = () => {
    const tileW = collage.naturalWidth / 3;
    const tileH = collage.naturalHeight / 3;
    const sourceX = tileW * 2;
    const sourceY = tileH * 2;

    const canvas = document.createElement("canvas");
    canvas.width = 128;
    canvas.height = 128;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return;
    }

    ctx.drawImage(collage, sourceX, sourceY, tileW, tileH, 0, 0, 128, 128);

    const favicon = document.getElementById("appFavicon");
    if (favicon) {
      favicon.setAttribute("href", canvas.toDataURL("image/png"));
    }
  };
}

function setOutput(data) {
  refs.output.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

function getSelectedCriteria() {
  return Array.from(refs.criteria.selectedOptions).map((o) => o.value);
}

function fillAirportSelectors(airports) {
  refs.origin.innerHTML = "";
  refs.destination.innerHTML = "";

  airports.forEach((airport) => {
    const option1 = document.createElement("option");
    option1.value = airport.id;
    option1.textContent = `${airport.id} - ${airport.city}`;

    const option2 = option1.cloneNode(true);

    refs.origin.appendChild(option1);
    refs.destination.appendChild(option2);
  });

  if (airports.length > 1) {
    refs.origin.value = airports[0].id;
    refs.destination.value = airports[1].id;
  }
}

function showAirportDetails(data) {
  refs.airportInfo.textContent = [
    `IATA: ${data.id}`,
    `Aeropuerto: ${data.name}`,
    `Ciudad: ${data.city}`,
    `Pais: ${data.country}`,
    `Zona horaria: ${data.timezone}`,
    `Tipo: ${data.isHub ? "Hub" : "Secundario"}`,
    `Aerolineas: ${data.airlines}`,
  ].join("\n");
}

function drag(simulationRef) {
  function dragstarted(event, d) {
    if (!event.active) {
      simulationRef.alphaTarget(0.3).restart();
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
      simulationRef.alphaTarget(0);
    }
    d.fx = null;
    d.fy = null;
  }

  return d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended);
}

function renderGraph(graphData) {
  const container = document.getElementById("graph");
  const width = container.clientWidth || 900;
  const height = container.clientHeight || 600;

  if (simulation) {
    simulation.stop();
  }

  d3.select("#graph").selectAll("*").remove();

  svg = d3
    .select("#graph")
    .append("svg")
    .attr("width", width)
    .attr("height", height)
    .attr("viewBox", [0, 0, width, height]);

  svg
    .append("defs")
    .append("marker")
    .attr("id", "arrow")
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 22)
    .attr("refY", 0)
    .attr("markerWidth", 6)
    .attr("markerHeight", 6)
    .attr("orient", "auto")
    .append("path")
    .attr("d", "M0,-5L10,0L0,5")
    .attr("fill", "#8dc9ef");

  svg
    .append("defs")
    .append("marker")
    .attr("id", "arrow-blocked")
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 22)
    .attr("refY", 0)
    .attr("markerWidth", 6)
    .attr("markerHeight", 6)
    .attr("orient", "auto")
    .append("path")
    .attr("d", "M0,-5L10,0L0,5")
    .attr("fill", "#ff4d6d");

  const nodes = graphData.airports.map((a) => ({
    id: a.id,
    name: a.name,
    city: a.city,
    country: a.country,
    timezone: a.timezone,
    isHub: a.isHub,
    airlines: "No definido en dataset",
  }));

  const links = graphData.routes.map((r) => ({
    source: r.origin,
    target: r.destination,
    distanceKm: r.distanceKm,
    blocked: r.blocked,
    aircraft: r.aircraftTypes.join(", "),
  }));

  simulation = d3
    .forceSimulation(nodes)
    .force("link", d3.forceLink(links).id((d) => d.id).distance((d) => Math.max(100, Math.min(240, d.distanceKm / 10))))
    .force("charge", d3.forceManyBody().strength(-420))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide().radius((d) => (d.isHub ? 24 : 18)));

  const link = svg
    .append("g")
    .attr("stroke-opacity", 0.9)
    .selectAll("line")
    .data(links)
    .join("line")
    .attr("stroke", (d) => (d.blocked ? "#ff4d6d" : "#8dc9ef"))
    .attr("stroke-width", (d) => (d.blocked ? 2.8 : 1.8))
    .attr("stroke-dasharray", (d) => (d.blocked ? "6 3" : "0"))
    .attr("marker-end", (d) => (d.blocked ? "url(#arrow-blocked)" : "url(#arrow)"));

  const linkLabel = svg
    .append("g")
    .selectAll("text")
    .data(links)
    .join("text")
    .text((d) => `${d.distanceKm} km`)
    .attr("font-size", 10)
    .attr("fill", "#ccecff")
    .attr("text-anchor", "middle")
    .attr("pointer-events", "none");

  const node = svg
    .append("g")
    .selectAll("circle")
    .data(nodes)
    .join("circle")
    .attr("r", (d) => (d.isHub ? 14 : 10))
    .attr("fill", (d) => (d.isHub ? "#ff7f50" : "#6ec8ff"))
    .attr("stroke", "#12354d")
    .attr("stroke-width", 2)
    .call(drag(simulation))
    .on("click", (_, d) => showAirportDetails(d));

  const nodeLabel = svg
    .append("g")
    .selectAll("text")
    .data(nodes)
    .join("text")
    .text((d) => d.id)
    .attr("font-size", 11)
    .attr("fill", "#ecf7ff")
    .attr("text-anchor", "middle")
    .attr("dy", 4)
    .attr("pointer-events", "none");

  simulation.on("tick", () => {
    link
      .attr("x1", (d) => d.source.x)
      .attr("y1", (d) => d.source.y)
      .attr("x2", (d) => d.target.x)
      .attr("y2", (d) => d.target.y);

    linkLabel
      .attr("x", (d) => (d.source.x + d.target.x) / 2)
      .attr("y", (d) => (d.source.y + d.target.y) / 2 - 6);

    node.attr("cx", (d) => d.x).attr("cy", (d) => d.y);
    nodeLabel.attr("x", (d) => d.x).attr("y", (d) => d.y);
  });
}

async function api(path, payload) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error((await response.json()).detail || "Error de API");
  }
  return response.json();
}

async function fetchGraph() {
  const response = await fetch(`${API_BASE}/graph`);
  if (!response.ok) {
    throw new Error((await response.json()).detail || "No se pudo obtener grafo");
  }
  const data = await response.json();
  cachedGraph = data;
  fillAirportSelectors(data.airports);
  renderGraph(data);
}

refs.btnLoad.addEventListener("click", async () => {
  try {
    const result = await api("/load", { file_path: refs.jsonPath.value.trim() });
    await fetchGraph();
    setOutput(result);
  } catch (error) {
    setOutput(error.message);
  }
});

refs.btnBestRoute.addEventListener("click", async () => {
  try {
    const selectedCriteria = getSelectedCriteria();
    if (selectedCriteria.length === 0) {
      setOutput("Selecciona al menos un criterio");
      return;
    }

    const result = await api("/plan/best-route", {
      origin: refs.origin.value,
      destination: refs.destination.value,
      criteria: selectedCriteria,
      exclude_secondary: refs.excludeSecondary.checked,
      allowed_aircraft: [],
    });
    setOutput(result);
  } catch (error) {
    setOutput(error.message);
  }
});

refs.btnBasic.addEventListener("click", async () => {
  try {
    const result = await api("/plan/basic", {
      origin: refs.origin.value,
      budget_usd: Number(refs.budget.value),
      time_hours: Number(refs.timeHours.value),
    });
    setOutput(result);
  } catch (error) {
    setOutput(error.message);
  }
});

async function updateRouteBlock(blocked) {
  try {
    const result = await api("/route/block", {
      origin: refs.blockOrigin.value.trim().toUpperCase(),
      destination: refs.blockDestination.value.trim().toUpperCase(),
      blocked,
    });
    await fetchGraph();
    setOutput(result);
  } catch (error) {
    setOutput(error.message);
  }
}

refs.btnBlock.addEventListener("click", () => updateRouteBlock(true));
refs.btnUnblock.addEventListener("click", () => updateRouteBlock(false));

window.addEventListener("resize", () => {
  if (cachedGraph) {
    renderGraph(cachedGraph);
  }
});

window.addEventListener("load", () => {
  generateFaviconFromCollage();
  setTimeout(() => {
    document.body.classList.add("loaded");
  }, 700);
});

setOutput("1) Inicia backend\n2) Carga el JSON\n3) Prueba rutas y bloqueos");
