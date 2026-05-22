/**
 * Airport Info Panel - Responsabilidad única: Mostrar detalles de aeropuertos
 * Single Responsibility: Renderizar información de airport en el panel
 */

class AirportInfoPanel {
  constructor(containerSelector = "#airportInfo") {
    this.container = document.querySelector(containerSelector);
  }

  /**
   * Muestra información de un aeropuerto
   */
  displayAirport(airport) {
    const aircraftList = airport.aircraftTypes?.length > 0
      ? airport.aircraftTypes.join(", ")
      : "Sin rutas salientes";

    this.container.innerHTML = [
      `<div class="airport-header">`,
      `<span class="airport-code">${airport.id}</span>`,
      `<span class="airport-hub-badge">${airport.isHub ? "🔴 HUB" : "○ Regular"}</span>`,
      `</div>`,
      `<div class="airport-info">`,
      `<p><strong>Aeropuerto:</strong> ${airport.name}</p>`,
      `<p><strong>Ciudad:</strong> ${airport.city}</p>`,
      `<p><strong>País:</strong> ${airport.country}</p>`,
      `<p><strong>Zona horaria:</strong> ${airport.timezone}</p>`,
      `<p><strong>Aeronaves que operan:</strong><br/>${aircraftList}</p>`,
      `</div>`,
    ].join("");
  }

  /**
   * Muestra mensaje inicial
   */
  displayInitialMessage() {
    this.container.innerHTML = "Selecciona un aeropuerto para ver información.";
  }

  /**
   * Limpia el panel
   */
  clear() {
    this.container.innerHTML = "";
  }
}

export const airportInfoPanel = new AirportInfoPanel();
