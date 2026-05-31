/**
 * Controlador del Modal de Simulación
 * Gestiona la apertura/cierre del modal y muestra el progreso de la simulación
 */

export class SimulationController {
  constructor() {
    this.modal = document.getElementById('simulationModal');
    this.btnOpen = document.getElementById('btnSimulationLoop');
    this.btnClose = document.getElementById('btnCloseSimulation');
    this.btnStart = document.getElementById('btnStartSimulation');
    this.btnPause = document.getElementById('btnPauseSimulation');
    this.btnResume = document.getElementById('btnResumeSimulation');
    this.btnBlockRoute = document.getElementById('btnBlockRouteDuringSimulation');
    
    this.flightsList = document.getElementById('simulationFlights');
    this.progressSection = document.getElementById('simulationProgress');
    this.optionsSection = document.getElementById('simulationOptions');
    this.blockMessage = document.getElementById('blockMessage');
    
    // Elementos de progreso
    this.simOrigin = document.getElementById('simOrigin');
    this.simDestination = document.getElementById('simDestination');
    this.simPosition = document.getElementById('simPosition');
    this.simTimeRemaining = document.getElementById('simTimeRemaining');
    this.progressBarFill = document.getElementById('progressBarFill');
    
    this.isSimulating = false;
    this.currentFlight = null;
    this.simulationService = null;
    this.animationController = null;
    this.appState = null;
    
    this.initializeEventListeners();
  }

  initializeEventListeners() {
    this.btnOpen.addEventListener('click', () => this.openModal());
    this.btnClose.addEventListener('click', () => this.closeModal());
    this.btnStart.addEventListener('click', () => this.startSimulation());
    this.btnPause.addEventListener('click', () => this.pauseSimulation());
    this.btnResume.addEventListener('click', () => this.resumeSimulation());
    this.btnBlockRoute.addEventListener('click', () => this.blockCurrentRoute());
    
    // Cerrar modal con Escape
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !this.modal.style.display || this.modal.style.display === 'grid') {
        this.closeModal();
      }
    });
    
    // Cerrar modal al hacer clic afuera
    this.modal.addEventListener('click', (e) => {
      if (e.target === this.modal) {
        this.closeModal();
      }
    });
  }

  /**
   * Inyectar dependencias necesarias
   */
  setDependencies(simulationService, animationController, appState) {
    this.simulationService = simulationService;
    this.animationController = animationController;
    this.appState = appState;
  }

  /**
   * Abrir el modal
   */
  openModal() {
    this.modal.style.display = 'grid';
    this.loadAvailableFlights();
  }

  /**
   * Cerrar el modal
   */
  closeModal() {
    this.modal.style.display = 'none';
    this.resetSimulation();
  }

  /**
   * Cargar vuelos disponibles en la sesión dinámica actual
   */
  loadAvailableFlights() {
    if (!this.appState || !this.appState.dynamicSession) {
      this.flightsList.innerHTML = '<p style="color: var(--muted);">No hay sesión dinámica activa. Inicia una primero.</p>';
      return;
    }

    const session = this.appState.dynamicSession;
    if (!session.flight_options || session.flight_options.length === 0) {
      this.flightsList.innerHTML = '<p style="color: var(--muted);">No hay vuelos disponibles en este momento.</p>';
      return;
    }

    this.flightsList.innerHTML = '';
    
    session.flight_options.forEach((flight, index) => {
      const item = document.createElement('label');
      item.className = 'flight-radio-item';
      
      const radio = document.createElement('input');
      radio.type = 'radio';
      radio.name = 'simulationFlight';
      radio.value = index;
      if (index === 0) radio.checked = true;
      
      const info = document.createElement('div');
      info.className = 'flight-info';
      info.innerHTML = `
        <div class="flight-info-line"><strong>${flight.origin} → ${flight.destination}</strong></div>
        <div class="flight-info-line">Tiempo: ${flight.time_h}h | Costo: $${flight.cost}</div>
        <div class="flight-info-line">Distancia: ${flight.distance}km</div>
      `;
      
      item.appendChild(radio);
      item.appendChild(info);
      this.flightsList.appendChild(item);
    });
  }

  /**
   * Iniciar simulación del vuelo seleccionado
   */
  async startSimulation() {
    const selectedRadio = document.querySelector('input[name="simulationFlight"]:checked');
    if (!selectedRadio) {
      alert('Selecciona un vuelo primero');
      return;
    }

    const flightIndex = parseInt(selectedRadio.value);
    const flight = this.appState.dynamicSession.flight_options[flightIndex];
    
    this.currentFlight = flight;
    this.isSimulating = true;
    
    // Cambiar botones visibles
    this.btnStart.style.display = 'none';
    this.btnPause.style.display = 'inline-block';
    this.btnResume.style.display = 'none';
    this.progressSection.style.display = 'block';
    this.optionsSection.style.display = 'block';
    
    // Actualizar información de progreso inicial
    this.simOrigin.textContent = flight.origin;
    this.simDestination.textContent = flight.destination;
    this.simPosition.textContent = '0%';
    this.simTimeRemaining.textContent = `${flight.time_h}h`;
    
    // Iniciar animación visual
    if (this.animationController) {
      const animationDuration = (flight.time_h * 60) * 1000; // convertir horas a ms
      
      try {
        await this.animationController.fly(
          flight.origin,
          flight.destination,
          animationDuration,
          (progress) => this.updateProgress(progress, flight)
        );
        
        this.finishSimulation();
      } catch (error) {
        console.error('Error durante la simulación:', error);
        this.resetSimulation();
      }
    }
  }

  /**
   * Actualizar barra de progreso durante la simulación
   */
  updateProgress(progress, flight) {
    const percentage = Math.round(progress * 100);
    this.simPosition.textContent = `${percentage}%`;
    this.progressBarFill.style.width = `${percentage}%`;
    
    // Calcular tiempo restante
    const remaining = Math.max(0, flight.time_h * (1 - progress));
    this.simTimeRemaining.textContent = remaining > 0 ? `${remaining.toFixed(1)}h` : 'Llegando...';
  }

  /**
   * Pausar simulación
   */
  pauseSimulation() {
    if (this.animationController) {
      this.animationController.pause();
    }
    this.isSimulating = false;
    this.btnPause.style.display = 'none';
    this.btnResume.style.display = 'inline-block';
  }

  /**
   * Reanudar simulación
   */
  resumeSimulation() {
    if (this.animationController) {
      this.animationController.resume();
    }
    this.isSimulating = true;
    this.btnPause.style.display = 'inline-block';
    this.btnResume.style.display = 'none';
  }

  /**
   * Bloquear la ruta actual
   */
  async blockCurrentRoute() {
    if (!this.currentFlight) return;
    
    const { origin, destination } = this.currentFlight;
    
    try {
      await this.simulationService.blockRoute(origin, destination);
      
      this.blockMessage.style.display = 'block';
      this.blockMessage.textContent = `✓ Ruta ${origin} → ${destination} bloqueada. Si el viajero está en tránsito, será redirigido al aeropuerto de origen.`;
      
      // Limpiar mensaje después de 5 segundos
      setTimeout(() => {
        this.blockMessage.style.display = 'none';
      }, 5000);
    } catch (error) {
      console.error('Error bloqueando ruta:', error);
      this.blockMessage.style.display = 'block';
      this.blockMessage.style.color = '#ff6b6b';
      this.blockMessage.textContent = '✗ Error bloqueando la ruta';
    }
  }

  /**
   * Terminar simulación
   */
  finishSimulation() {
    this.isSimulating = false;
    this.btnStart.style.display = 'inline-block';
    this.btnPause.style.display = 'none';
    this.btnResume.style.display = 'none';
    
    this.simPosition.textContent = '100%';
    this.progressBarFill.style.width = '100%';
    this.simTimeRemaining.textContent = '¡Llegada!';
  }

  /**
   * Resetear simulación
   */
  resetSimulation() {
    this.isSimulating = false;
    this.currentFlight = null;
    this.btnStart.style.display = 'inline-block';
    this.btnPause.style.display = 'none';
    this.btnResume.style.display = 'none';
    this.progressSection.style.display = 'none';
    this.optionsSection.style.display = 'none';
    this.blockMessage.style.display = 'none';
    this.progressBarFill.style.width = '0%';
  }
}
