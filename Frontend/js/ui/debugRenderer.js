/**
 * Debug Renderer - Responsabilidad única: Mostrar datos de debug en JSON
 * Single Responsibility: Renderizar JSON para propósitos de depuración
 */

class DebugRenderer {
  constructor(containerSelector = "#output") {
    this.containerSelector = containerSelector;
    this.container = null;
  }

  /**
   * Inicializa el contenedor (ejecutarse después de DOMContentLoaded)
   */
  init() {
    this.container = document.querySelector(this.containerSelector);
    if (!this.container) {
      console.warn(`⚠️ DebugRenderer: No se encontró elemento ${this.containerSelector}`);
    }
  }

  /**
   * Muestra datos en formato JSON
   */
  displayJSON(data) {
    if (!this.container) this.init();
    if (!this.container) return;
    
    const jsonString = typeof data === "string" ? data : JSON.stringify(data, null, 2);
    this.container.textContent = jsonString;
  }

  /**
   * Muestra un mensaje de texto plano
   */
  displayMessage(message) {
    if (!this.container) this.init();
    if (!this.container) return;
    this.container.textContent = message;
  }

  /**
   * Limpia el contenedor
   */
  clear() {
    if (!this.container) this.init();
    if (!this.container) return;
    this.container.textContent = "";
  }

  /**
   * Muestra un error
   */
  displayError(error) {
    this.displayMessage(
      typeof error === "string" ? error : `❌ Error: ${error.message}`
    );
  }
}

export const debugRenderer = new DebugRenderer();
