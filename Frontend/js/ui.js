// --- Helpers ---

function fmtCost(n) { return `$${n.toFixed(2)}`; }
function fmtTime(min) { return (min / 60).toFixed(1) + "h"; }
function fmtMin(m) {
  const h = Math.floor(m / 60);
  const min = Math.round(m % 60);
  return h > 0 ? `${h}h ${min}min` : `${min}min`;
}

// --- Panel de aeropuerto ---

export function showAirportInfo(airport) {
  const el = document.getElementById("airportInfo");
  const aircraft = airport.aircraftTypes?.length > 0 ? airport.aircraftTypes.join(", ") : "Sin rutas salientes";
  el.innerHTML = `
    <div class="airport-header">
      <span class="airport-code">${airport.id}</span>
      <span class="airport-hub-badge">${airport.isHub ? "HUB" : "Regular"}</span>
    </div>
    <div class="airport-info">
      <p><strong>Aeropuerto:</strong> ${airport.name}</p>
      <p><strong>Ciudad:</strong> ${airport.city}</p>
      <p><strong>País:</strong> ${airport.country}</p>
      <p><strong>Zona horaria:</strong> ${airport.timezone}</p>
      <p><strong>Aeronaves:</strong> ${aircraft}</p>
    </div>`;
}

// --- Panel de rutas ---

function renderSegment(seg, idx, segments) {
  const accCost = segments.slice(0, idx + 1).reduce((s, x) => s + x.segment_cost, 0);
  return `
    <div class="segment">
      <div class="segment-header">
        <span class="airport-badge">${seg.origin}</span>
        <span class="segment-arrow">&rarr;</span>
        <span class="airport-badge">${seg.destination}</span>
        <span class="aircraft-badge">${seg.aircraft}</span>
      </div>
      <div class="segment-details">
        <div class="detail-item"><span>Distancia:</span><span class="detail-value distance-display">${seg.distance_km.toFixed(1)} km</span></div>
        <div class="detail-item"><span>Costo:</span><span class="detail-value cost-display">${fmtCost(seg.segment_cost)}</span></div>
        <div class="detail-item"><span>Tiempo:</span><span class="detail-value time-display">${fmtTime(seg.segment_time_min)}</span></div>
        <div class="detail-item"><span>Acum.:</span><span class="detail-value">${fmtCost(accCost)}</span></div>
      </div>
    </div>`;
}

function renderRouteCard(plan, title) {
  if (!plan || !plan.segments) return "";
  const segments = plan.segments.map((s, i) => renderSegment(s, i, plan.segments)).join("");
  const destinations = plan.visited_airports.map((a) => `<span class="dest-badge">${a}</span>`).join("");
  return `
    <div class="route-card">
      <div class="route-title">${title}</div>
      <div class="route-stats">
        <div class="stat-item"><div class="stat-label">Destinos</div><div class="stat-value">${plan.visited_airports.length - 1}</div></div>
        <div class="stat-item"><div class="stat-label">Costo</div><div class="stat-value cost-display">${fmtCost(plan.total_cost)}</div></div>
      </div>
      <div class="segments-list">${segments}</div>
      <div class="destination-list">
        <strong>Itinerario</strong>
        <div class="destination-badges">${destinations}</div>
      </div>
    </div>`;
}

export function showBasicPlans(budgetPlan, timePlan) {
  document.getElementById("routesContainer").innerHTML =
    renderRouteCard(budgetPlan, "Mayor destinos sin exceder presupuesto") +
    renderRouteCard(timePlan, "Mayor destinos en menor tiempo");
}

export function showSuggestedRoute(suggestedRoute) {
  const el = document.getElementById("routesContainer");
  if (!suggestedRoute || !suggestedRoute.airports || suggestedRoute.airports.length <= 1) return;

  const airports = suggestedRoute.airports;
  const segments = suggestedRoute.segments || [];
  const segsHtml = segments.map((seg) => `
    <div class="segment">
      <div class="segment-header">
        <span class="airport-badge">${seg.origin}</span>
        <span class="segment-arrow">&rarr;</span>
        <span class="airport-badge">${seg.destination}</span>
        <span class="aircraft-badge">${seg.aircraft}</span>
      </div>
      <div class="segment-details">
        <div class="detail-item"><span>Distancia:</span><span class="detail-value distance-display">${seg.distance_km.toFixed(1)} km</span></div>
        <div class="detail-item"><span>Costo:</span><span class="detail-value cost-display">${seg.segment_cost.toFixed(2)}</span></div>
        <div class="detail-item"><span>Tiempo:</span><span class="detail-value time-display">${fmtTime(seg.segment_time_min)}</span></div>
      </div>
    </div>`).join("");

  const badges = airports.map((a) => `<span class="dest-badge">${a}</span>`).join("");
  el.innerHTML = `
    <div class="route-card">
      <div class="route-title">Ruta Sugerida</div>
      <div class="route-stats">
        <div class="stat-item"><div class="stat-label">Destinos</div><div class="stat-value">${airports.length - 1}</div></div>
        <div class="stat-item"><div class="stat-label">Costo</div><div class="stat-value cost-display">${(suggestedRoute.total_cost || 0).toFixed(2)}</div></div>
      </div>
      <div class="segments-list">${segsHtml}</div>
      <div class="destination-list"><strong>Itinerario</strong><div class="destination-badges">${badges}</div></div>
    </div>`;
}

export function showOptimizedRoutes(allRoutes, origin, criteria) {
  const el = document.getElementById("routesContainer");
  const labels = { distancia: "Optima por Distancia", tiempo: "Optima por Tiempo", costo: "Optima por Costo" };

  let html = "";
  for (const criterion of criteria) {
    const route = allRoutes[criterion];
    if (!route || !route.reachable) continue;
    const plan = {
      visited_airports: [origin, ...(route.segments?.map((s) => s.destination) || [])],
      segments: route.segments || [],
      total_cost: route.total_cost || 0,
      total_time_min: route.total_time_min || 0,
    };
    html += renderRouteCard(plan, labels[criterion] || `Optima por ${criterion}`);
  }
  el.innerHTML = html || '<div class="empty-routes">No hay rutas alcanzables</div>';
}

export function showNoTransport(origin, destination, aircraft) {
  document.getElementById("routesContainer").innerHTML = `
    <div class="empty-routes">
      <div class="no-transport-message">
        <div class="message-icon">&#9992;</div>
        <div class="message-title">No hay ruta con el transporte seleccionado</div>
        <div class="message-details">
          <p><strong>Ruta:</strong> ${origin} &rarr; ${destination}</p>
          <p><strong>Transportes:</strong> ${aircraft.join(", ")}</p>
          <p class="message-hint">Intenta con otros tipos de transporte.</p>
        </div>
      </div>
    </div>`;
}

export function showRouteMessage(msg) {
  document.getElementById("routesContainer").innerHTML = `<div class="empty-routes">${msg}</div>`;
}

export function showRouteError(msg) {
  document.getElementById("routesContainer").innerHTML = `<div class="empty-routes">${msg}</div>`;
}

// --- Panel dinámico ---

export function showDynamicState(state) {
  const el = document.getElementById("dynamicState");
  if (!el || !state) return;
  el.innerHTML = `
    <div class="dynamic-state-row"><strong>Sesión:</strong> ${state.session_id}</div>
    <div class="dynamic-state-row"><strong>Ubicación:</strong> ${state.current_airport}</div>
    <div class="dynamic-state-row"><strong>Presupuesto:</strong> $${state.budget_usd.toFixed(2)}</div>
    <div class="dynamic-state-row"><strong>Tiempo restante:</strong> ${fmtTime(state.time_left_min)}</div>
    <div class="dynamic-state-row"><strong>Estancia:</strong> ${state.stay_min.toFixed(0)} / ${state.required_stay_min.toFixed(0)} min</div>
    <div class="dynamic-state-row"><strong>Visitados:</strong> ${state.visited_airports.length}</div>`;
}

export function showActivities(activities) {
  const el = document.getElementById("dynamicActivities");
  if (!el) return;
  if (!activities || activities.length === 0) {
    el.innerHTML = '<div class="empty-routes">Sin actividades disponibles</div>';
    return;
  }
  el.innerHTML = activities.map((a) => {
    const disabled = a.affordable ? "" : "disabled";
    const badge = a.affordable ? "" : '<span class="dynamic-tag">Sin presupuesto</span>';
    return `
      <label class="dynamic-item">
        <input type="checkbox" name="dynamic-activity" value="${a.name}" ${disabled} />
        <span>${a.name}</span>
        <span class="dynamic-meta">${a.duration_min} min - $${a.cost_usd.toFixed(2)}</span>
        ${badge}
      </label>`;
  }).join("");
}

export function showJobs(jobs) {
  const el = document.getElementById("dynamicJobs");
  if (!el) return;
  if (!jobs || jobs.length === 0) {
    el.innerHTML = '<div class="empty-routes">Sin trabajos disponibles</div>';
    return;
  }
  el.innerHTML = jobs.map((j) => `
    <label class="dynamic-item">
      <input type="radio" name="dynamic-job" value="${j.name}" data-max-hours="${j.max_hours}" />
      <span>${j.name}</span>
      <span class="dynamic-meta">$${j.hourly_rate.toFixed(2)}/h - max ${j.max_hours}h</span>
    </label>`).join("");
}

export function showFlights(options) {
  const el = document.getElementById("dynamicFlights");
  if (!el) return;
  if (!options || options.length === 0) {
    el.innerHTML = '<div class="empty-routes">Sin vuelos disponibles</div>';
    return;
  }

  const grouped = {};
  options.forEach((o) => {
    if (!grouped[o.destination]) grouped[o.destination] = [];
    grouped[o.destination].push(o);
  });

  el.innerHTML = Object.entries(grouped).map(([dest, opts]) => `
    <div class="dynamic-flight-group">
      <div class="dynamic-flight-destination">${opts[0].origin} &rarr; ${dest}</div>
      ${opts.map((o) => {
        const badge = o.subsidized ? `<span class="subsidy-badge">Subsidio</span>` : "";
        return `
        <label class="dynamic-item dynamic-item-flight">
          <input type="radio" name="dynamic-flight" data-destination="${o.destination}" data-aircraft="${o.aircraft}" data-distance="${o.distance_km}" data-subsidized="${o.subsidized}" data-cost="${o.segment_cost}" data-time="${o.segment_time_min}" />
          <span>${o.aircraft}</span>
          <span class="dynamic-meta">${o.distance_km.toFixed(1)} km - $${o.segment_cost.toFixed(2)} - ${fmtTime(o.segment_time_min)}</span>
          ${badge}
        </label>`;
      }).join("")}
    </div>`).join("");
}

export function showSteps(steps) {
  const el = document.getElementById("dynamicSteps");
  if (!el) return;
  if (!steps || steps.length === 0) {
    el.innerHTML = '<div class="empty-routes">Sin acciones registradas</div>';
    return;
  }
  el.innerHTML = steps.map((s) => `
    <div class="dynamic-step">
      <div class="dynamic-step-title">${s.action.toUpperCase()} - ${s.airport_id}</div>
      <div class="dynamic-step-detail">${s.detail}</div>
      <div class="dynamic-step-meta">Presupuesto: $${s.budget_after.toFixed(2)} - Tiempo: ${fmtTime(s.time_left_min)}</div>
    </div>`).join("");
}

export function clearDynamicPanel() {
  document.getElementById("dynamicState").textContent = "Inicia una sesion para ver el estado.";
  document.getElementById("dynamicActivities").innerHTML = "";
  document.getElementById("dynamicJobs").innerHTML = "";
  document.getElementById("dynamicFlights").innerHTML = "";
  document.getElementById("dynamicSteps").innerHTML = "";
}

// --- Debug ---

export function showDebug(data) {
  const el = document.getElementById("output");
  if (!el) return;
  el.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

export function showDebugMessage(msg) {
  const el = document.getElementById("output");
  if (el) el.textContent = msg;
}

// --- Reporte modal ---

export function showReportModal(report) {
  const modal = document.getElementById("report-modal");
  const content = document.getElementById("report-modal-content");
  if (!modal || !content) return;

  const f = (n) => (typeof n === "number" ? n.toFixed(2) : (n ?? "-"));

  let html = `
    <div class="report-section">
      <h3>Totales del Viaje</h3>
      <div class="report-totals-grid">
        <div class="report-total-card"><span>Presupuesto Inicial</span><strong>$${f(report.totals?.initial_budget)} USD</strong></div>
        <div class="report-total-card"><span>Total Gastado</span><strong class="spent">$${f(report.totals?.total_spent)} USD</strong></div>
        <div class="report-total-card"><span>Total Ganado</span><strong class="earned">$${f(report.totals?.total_earned)} USD</strong></div>
        <div class="report-total-card"><span>Saldo Final</span><strong class="${(report.totals?.final_budget ?? 0) >= 0 ? "earned" : "spent"}">$${f(report.totals?.final_budget)} USD</strong></div>
        <div class="report-total-card"><span>Tiempo Total</span><strong>${fmtMin(report.totals?.total_time_spent_min ?? 0)}</strong></div>
        <div class="report-total-card"><span>Alimentación</span><strong class="spent">$${f(report.totals?.total_food_cost ?? 0)} USD</strong></div>
        <div class="report-total-card"><span>Alojamiento</span><strong class="spent">$${f(report.totals?.total_lodging_cost ?? 0)} USD</strong></div>
      </div>
    </div>`;

  if (report.mandatory_fees?.length) {
    html += `<div class="report-section"><h3>Cobros Obligatorios</h3>
      <table class="report-table"><thead><tr><th>Aeropuerto</th><th>Concepto</th><th>Valor</th><th>Momento</th></tr></thead><tbody>`;
    report.mandatory_fees.forEach((fee) => {
      html += `<tr><td><strong>${fee.airport_id}</strong> - ${fee.airport_name}</td>
        <td><span class="badge ${fee.action === "Alimentación" ? "badge-food" : "badge-lodging"}">${fee.action}</span></td>
        <td class="spent">$${f(fee.cost_usd)} USD</td><td>Hace ${fmtMin(fee.moment_min)}</td></tr>`;
    });
    html += `</tbody></table></div>`;
  }

  if (report.destinations?.length) {
    html += `<div class="report-section"><h3>Destinos Visitados</h3>
      <table class="report-table"><thead><tr><th>ID</th><th>Ciudad</th><th>País</th><th>Estadía</th><th>Costo</th></tr></thead><tbody>`;
    report.destinations.forEach((d) => {
      html += `<tr><td>${d.id}</td><td>${d.city}</td><td>${d.country}</td><td>${fmtMin(d.stay_min)}</td><td>$${f(d.total_cost)} USD</td></tr>`;
    });
    html += `</tbody></table></div>`;
  }

  if (report.flights?.length) {
    html += `<div class="report-section"><h3>Tramos Volados</h3>
      <table class="report-table"><thead><tr><th>Origen</th><th>Destino</th><th>Aeronave</th><th>Distancia</th><th>Duración</th><th>Costo</th></tr></thead><tbody>`;
    report.flights.forEach((fl) => {
      html += `<tr><td>${fl.origin}</td><td>${fl.destination}</td><td>${fl.aircraft}</td><td>${f(fl.distance_km)} km</td><td>${fmtMin(fl.duration_min)}</td><td>$${f(fl.cost_usd)} USD</td></tr>`;
    });
    html += `</tbody></table></div>`;
  }

  if (report.activities?.length) {
    html += `<div class="report-section"><h3>Actividades</h3>
      <table class="report-table"><thead><tr><th>Aeropuerto</th><th>Actividad</th><th>Tipo</th><th>Duración</th><th>Costo</th></tr></thead><tbody>`;
    report.activities.forEach((a) => {
      html += `<tr><td>${a.airport_id}</td><td>${a.name}</td><td>${a.kind}</td><td>${fmtMin(a.duration_min)}</td><td>$${f(a.cost_usd)} USD</td></tr>`;
    });
    html += `</tbody></table></div>`;
  }

  if (report.jobs?.length) {
    html += `<div class="report-section"><h3>Trabajos</h3>
      <table class="report-table"><thead><tr><th>Aeropuerto</th><th>Trabajo</th><th>Horas</th><th>Ingreso</th></tr></thead><tbody>`;
    report.jobs.forEach((j) => {
      html += `<tr><td>${j.airport_id}</td><td>${j.name}</td><td>${f(j.hours)}h</td><td>$${f(j.earned_usd)} USD</td></tr>`;
    });
    html += `</tbody></table></div>`;
  }

  content.innerHTML = html;
  modal.classList.add("active");
}

// --- Selectores de aeropuerto ---

export function fillAirportSelectors(airports) {
  const selectors = ["origin", "destination", "originBasic", "originDynamic"];
  selectors.forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = "";
    airports.forEach((a) => {
      const opt = document.createElement("option");
      opt.value = a.id;
      opt.textContent = `${a.id} - ${a.city}`;
      el.appendChild(opt);
    });
  });
  if (airports.length > 1) {
    document.getElementById("origin").value = airports[0].id;
    document.getElementById("destination").value = airports[1].id;
    document.getElementById("originBasic").value = airports[0].id;
    document.getElementById("originDynamic").value = airports[0].id;
  }
}

// --- Modal de Ruta Subsidiada (Límite 20%) ---

export function showSubsidyModal(currentState, flightDistance) {
  const modal = document.getElementById("subsidy-modal");
  if (!modal) return;

  const currentDist = currentState.total_distance_km || 0;
  const currentFree = currentState.free_distance_km || 0;
  const projectedTotal = currentDist + flightDistance;
  const projectedFree = currentFree + flightDistance;
  const percentage = projectedTotal > 0 ? (projectedFree / projectedTotal) * 100 : 0;

  document.getElementById("subsidy-percentage-text").textContent = percentage.toFixed(1) + "%";
  
  const progressBar = document.getElementById("subsidy-progress-bar");
  if (progressBar) {
    progressBar.style.width = Math.min(percentage, 100).toFixed(1) + "%";
  }

  document.getElementById("subsidy-stat-current").textContent = currentDist.toFixed(1) + " km";
  document.getElementById("subsidy-stat-free").textContent = currentFree.toFixed(1) + " km";
  document.getElementById("subsidy-stat-requested").textContent = flightDistance.toFixed(1) + " km";
  document.getElementById("subsidy-stat-projected-total").textContent = projectedTotal.toFixed(1) + " km";
  document.getElementById("subsidy-stat-projected-free").textContent = projectedFree.toFixed(1) + " km";

  modal.classList.add("active");
}

export function showAlertModal(title, message) {
  const modal = document.getElementById("alert-modal");
  if (!modal) return;
  document.getElementById("alert-modal-title").textContent = title;
  document.getElementById("alert-modal-message").textContent = message;
  modal.classList.add("active");
}


