/**
 * Dynamic Panel - Responsabilidad unica: Renderizar panel dinamico 2.3
 * Single Responsibility: Convertir estado y opciones a HTML
 */

class DynamicPanel {
  constructor(selectors) {
    this.stateBox = document.querySelector(selectors.state);
    this.activitiesBox = document.querySelector(selectors.activities);
    this.jobsBox = document.querySelector(selectors.jobs);
    this.flightsBox = document.querySelector(selectors.flights);
    this.stepsBox = document.querySelector(selectors.steps);
  }

  showEmpty(message) {
    if (this.stateBox) {
      this.stateBox.textContent = message;
    }
    if (this.activitiesBox) {
      this.activitiesBox.innerHTML = "";
    }
    if (this.jobsBox) {
      this.jobsBox.innerHTML = "";
    }
    if (this.flightsBox) {
      this.flightsBox.innerHTML = "";
    }
    if (this.stepsBox) {
      this.stepsBox.innerHTML = "";
    }
  }

  renderState(state) {
    if (!this.stateBox || !state) return;

    this.stateBox.innerHTML = [
      `<div class="dynamic-state-row"><strong>Sesion:</strong> ${state.session_id}</div>`,
      `<div class="dynamic-state-row"><strong>Ubicacion:</strong> ${state.current_airport}</div>`,
      `<div class="dynamic-state-row"><strong>Presupuesto:</strong> $${state.budget_usd.toFixed(2)}</div>`,
      `<div class="dynamic-state-row"><strong>Tiempo restante:</strong> ${(state.time_left_min / 60).toFixed(1)}h</div>`,
      `<div class="dynamic-state-row"><strong>Estancia:</strong> ${state.stay_min.toFixed(0)} / ${state.required_stay_min.toFixed(0)} min</div>`,
      `<div class="dynamic-state-row"><strong>Visitados:</strong> ${state.visited_airports.length}</div>`
    ].join("");
  }

  renderActivities(activities) {
    if (!this.activitiesBox) return;
    if (!activities || activities.length === 0) {
      this.activitiesBox.innerHTML = '<div class="empty-routes">Sin actividades disponibles</div>';
      return;
    }

    this.activitiesBox.innerHTML = activities.map((activity) => {
      const disabled = activity.affordable ? "" : "disabled";
      const badge = activity.affordable ? "" : '<span class="dynamic-tag">Sin presupuesto</span>';
      return `
        <label class="dynamic-item">
          <input type="checkbox" name="dynamic-activity" value="${activity.name}" ${disabled} />
          <span>${activity.name}</span>
          <span class="dynamic-meta">${activity.duration_min} min · $${activity.cost_usd.toFixed(2)}</span>
          ${badge}
        </label>
      `;
    }).join("");
  }

  renderJobs(jobs) {
    if (!this.jobsBox) return;
    if (!jobs || jobs.length === 0) {
      this.jobsBox.innerHTML = '<div class="empty-routes">Sin trabajos disponibles</div>';
      return;
    }

    this.jobsBox.innerHTML = jobs.map((job) => `
      <label class="dynamic-item">
        <input type="radio" name="dynamic-job" value="${job.name}" />
        <span>${job.name}</span>
        <span class="dynamic-meta">$${job.hourly_rate.toFixed(2)}/h · max ${job.max_hours}h</span>
      </label>
    `).join("");
  }

  renderFlights(options) {
    if (!this.flightsBox) return;
    if (!options || options.length === 0) {
      this.flightsBox.innerHTML = '<div class="empty-routes">Sin vuelos disponibles</div>';
      return;
    }

    const groupedByDestination = {};
    options.forEach((option) => {
      if (!groupedByDestination[option.destination]) {
        groupedByDestination[option.destination] = [];
      }
      groupedByDestination[option.destination].push(option);
    });

    this.flightsBox.innerHTML = Object.entries(groupedByDestination).map(([destination, flightOptions]) => `
      <div class="dynamic-flight-group">
        <div class="dynamic-flight-destination">${flightOptions[0].origin} → ${destination}</div>
        ${flightOptions.map((option) => `
          <label class="dynamic-item dynamic-item-flight">
            <input
              type="radio"
              name="dynamic-flight-${destination}"
              data-destination="${option.destination}"
              data-aircraft="${option.aircraft}"
            />
            <span>${option.aircraft}</span>
            <span class="dynamic-meta">${option.distance_km.toFixed(1)} km · $${option.segment_cost.toFixed(2)} · ${(option.segment_time_min / 60).toFixed(2)}h</span>
          </label>
        `).join("")}
      </div>
    `).join("");
  }

  renderSteps(steps) {
    if (!this.stepsBox) return;
    if (!steps || steps.length === 0) {
      this.stepsBox.innerHTML = '<div class="empty-routes">Sin acciones registradas</div>';
      return;
    }

    this.stepsBox.innerHTML = steps.map((step) => `
      <div class="dynamic-step">
        <div class="dynamic-step-title">${step.action.toUpperCase()} · ${step.airport_id}</div>
        <div class="dynamic-step-detail">${step.detail}</div>
        <div class="dynamic-step-meta">Presupuesto: $${step.budget_after.toFixed(2)} · Tiempo restante: ${(step.time_left_min / 60).toFixed(1)}h</div>
      </div>
    `).join("");
  }
}

export const dynamicPanel = new DynamicPanel({
  state: "#dynamicState",
  activities: "#dynamicActivities",
  jobs: "#dynamicJobs",
  flights: "#dynamicFlights",
  steps: "#dynamicSteps",
});