/**
 * ============================================
 * FAC AeroGraph - SkyRoute Planner
 * Aplicación Principal (Punto de entrada)
 * ============================================
 * 
 * Arquitectura SOLID:
 * - Single Responsibility: Cada módulo tiene una única responsabilidad
 * - Open/Closed: Extensible sin modificar código existente
 * - Liskov Substitution: Services intercambiables
 * - Interface Segregation: Interfaces específicas
 * - Dependency Inversion: Inyección de dependencias
 * 
 * Estructura modular:
 * - /api: Comunicación HTTP
 * - /services: Lógica de negocio
 * - /ui: Renderización visual
 * - /handlers: Manejo de eventos
 * - /constants: Configuración global
 * - /utils: Funciones auxiliares
 */

import { EventHandlers } from "./js/handlers/eventHandlers.js";
import { graphRenderer } from "./js/ui/graphRenderer.js";
import { routesRenderer } from "./js/ui/routesRenderer.js";
import { airportInfoPanel } from "./js/ui/airportPanel.js";
import { debugRenderer } from "./js/ui/debugRenderer.js";
import { dynamicPanel } from "./js/ui/dynamicPanel.js";
import { generateFaviconFromCollage, initSplashScreen } from "./js/utils/uiUtils.js";
import { MESSAGES } from "./js/constants/config.js";
import { animationController } from './js/ui/animationController.js';
import { dynamicPlanService } from "./js/services/dynamicPlanService.js";
import { routeService } from "./js/services/routeService.js";
import { graphService } from "./js/services/graphService.js";
/**
 * Referencias a elementos del DOM
 * Centralizadas para fácil referencia
 */
const refs = {
  jsonPath: document.getElementById("jsonPath"),
  origin: document.getElementById("origin"),
  destination: document.getElementById("destination"),
  criteriaCheckboxes: document.querySelectorAll(".criteria-checkbox"),
  aircraftCheckboxes: document.querySelectorAll(".aircraft-checkbox"),
  excludeSecondary: document.getElementById("excludeSecondary"),
  budget: document.getElementById("budget"),
  timeHours: document.getElementById("timeHours"),
  originBasic: document.getElementById("originBasic"),
  originDynamic: document.getElementById("originDynamic"),
  blockOrigin: document.getElementById("blockOrigin"),
  blockDestination: document.getElementById("blockDestination"),
  btnLoad: document.getElementById("btnLoad"),
  btnBestRoute: document.getElementById("btnBestRoute"),
  btnBasic: document.getElementById("btnBasic"),
  btnBlock: document.getElementById("btnBlock"),
  btnUnblock: document.getElementById("btnUnblock"),
  dynamicBudget: document.getElementById("dynamicBudget"),
  dynamicTimeHours: document.getElementById("dynamicTimeHours"),
  dynamicJobHours: document.getElementById("dynamicJobHours"),
  btnDynamicStart: document.getElementById("btnDynamicStart"),
  btnDynamicRefresh: document.getElementById("btnDynamicRefresh"),
  btnDynamicFinish: document.getElementById("btnDynamicFinish"),
  btnDynamicApplyActivities: document.getElementById("btnDynamicApplyActivities"),
  btnDynamicWork: document.getElementById("btnDynamicWork"),
  btnDynamicFly: document.getElementById("btnDynamicFly"),
};

/**
 * Inicializa los manejadores de eventos
 */
const eventHandlers = new EventHandlers(refs);

/**
 * ============================================
 * REGISTRO DE EVENT LISTENERS
 * ============================================
 */

// Cargar red aérea
refs.btnLoad.addEventListener("click", (e) => eventHandlers.handleLoadGraph(e));

// Calcular plan básico (2 alternativas)
refs.btnBasic.addEventListener("click", (e) => eventHandlers.handleBasicPlan(e));

// Calcular mejor ruta por criterios
refs.btnBestRoute.addEventListener("click", (e) => eventHandlers.handleBestRoute(e));

// Bloquear/desbloquear rutas
refs.btnBlock.addEventListener("click", () => eventHandlers.handleBlockRoute(true));
refs.btnUnblock.addEventListener("click", () => eventHandlers.handleBlockRoute(false));

// Planificacion dinamica
refs.btnDynamicStart.addEventListener("click", (e) => eventHandlers.handleDynamicStart(e));
refs.btnDynamicRefresh.addEventListener("click", (e) => eventHandlers.handleDynamicRefresh(e));
refs.btnDynamicFinish.addEventListener("click", (e) => eventHandlers.handleDynamicFinish(e));
refs.btnDynamicApplyActivities.addEventListener("click", (e) => eventHandlers.handleDynamicActivities(e));
refs.btnDynamicWork.addEventListener("click", (e) => eventHandlers.handleDynamicWork(e));
refs.btnDynamicFly.addEventListener("click", (e) => eventHandlers.handleDynamicFly(e));

// Redimensionamiento de ventana
window.addEventListener("resize", () => {
  window.dispatchEvent(new CustomEvent("layout:resized"));
});

/**
 * ============================================
 * INICIALIZACIÓN DE LA APLICACIÓN
 * ============================================
 */

document.addEventListener("DOMContentLoaded", () => {
  // 1. Generar favicon
  generateFaviconFromCollage();

  // 2. Mostrar pantalla de splash
  initSplashScreen();

  // 3. Inicializar el debug renderer
  debugRenderer.init();

  // 4. Mostrar estado inicial
  airportInfoPanel.displayInitialMessage();
  routesRenderer.displayEmpty(MESSAGES.INFO.INITIAL);
  dynamicPanel.showEmpty("Inicia una sesion para ver el estado.");

  // 5. El modal de simulación antiguo ha sido integrado nativamente.

  // 6. Escuchar cambios de estado dinámico para actualizar toda la UI
  window.addEventListener("dynamic:state-changed", async (e) => {
    const state = e.detail;
    if (state) {
      await eventHandlers._refreshDynamicPanel(state);
      
      // Volver a dibujar el grafo para reflejar rutas bloqueadas en rojo
      const graphData = graphService.getGraphData();
      if (graphData) {
        graphRenderer.render(graphData, (airport) => eventHandlers.handleAirportClick(airport));
        animationController.initialize();
      }
    }
  });
});

/**
 * Logs para desarrollo
 */
console.log("🛫 FAC AeroGraph - SkyRoute Planner initialized");
console.log("📦 Arquitectura: SOLID Principles");
console.log("🔧 Módulos cargados: API, Services, UI, Handlers");
