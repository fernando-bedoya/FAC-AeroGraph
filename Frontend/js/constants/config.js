/**
 * Configuración global de la aplicación
 * Single Responsibility: Centralizar todas las constantes de configuración
 */

export const CONFIG = {
  API: {
    BASE_URL: "http://127.0.0.1:8000/api",
    ENDPOINTS: {
      LOAD: "/load",
      GRAPH: "/graph",
      PLAN_BASIC: "/plan/basic",
      PLAN_BEST_ROUTE: "/plan/best-route",
      ROUTE_BLOCK: "/route/block",
      DYNAMIC_START: "/dynamic/start",
      DYNAMIC_STATE: "/dynamic/state",
      DYNAMIC_ACTIVITIES: "/dynamic/activities",
      DYNAMIC_JOBS: "/dynamic/jobs",
      DYNAMIC_WORK: "/dynamic/work",
      DYNAMIC_FLIGHT_OPTIONS: "/dynamic/flight-options",
      DYNAMIC_FLY: "/dynamic/fly",
      DYNAMIC_FINISH: "/dynamic/finish",
    },
  },
  UI: {
    GRAPH: {
      MIN_WIDTH: 900,
      MIN_HEIGHT: 600,
      FORCE_CHARGE: -420,
      FORCE_LINK_DISTANCE: (distKm) => Math.max(100, Math.min(240, distKm / 10)),
      NODE_HUB_RADIUS: 14,
      NODE_REGULAR_RADIUS: 10,
      MARKER_REF_X: 22,
    },
  },
  ANIMATION: {
    SPLASH_DURATION: 700,
  },
};

export const COLORS = {
  ACCENT: "#32d2ff",
  ACCENT_2: "#00ffa3",
  HUB: "#ff7f50",
  NODE: "#6ec8ff",
  ARROW: "#8dc9ef",
  ARROW_BLOCKED: "#ff4d6d",
  MUTED: "#9fc4da",
  INK: "#ecf7ff",
};

export const MESSAGES = {
  ERRORS: {
    NO_CRITERIA: "❌ Selecciona al menos un criterio",
    NO_GRAPH: "❌ Primero carga un archivo JSON",
    NO_ROUTES: "📭 No hay rutas para mostrar",
  },
  INFO: {
    INITIAL: "🛫 Selecciona un plan y presiona calcular para ver las rutas",
    LOADING: "⏳ Calculando...",
  },
};
