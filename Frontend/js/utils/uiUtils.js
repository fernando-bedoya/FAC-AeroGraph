/**
 * UI Utils - Responsabilidad única: Utilidades de UI generales
 * Single Responsibility: Funciones auxiliares reutilizables
 */

import { CONFIG } from "../constants/config.js";

/**
 * Genera el favicon desde un collage de imágenes
 */
export function generateFaviconFromCollage() {
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

/**
 * Muestra la pantalla de splash y la oculta después del tiempo especificado
 */
export function initSplashScreen() {
  setTimeout(() => {
    document.body.classList.add("loaded");
  }, CONFIG.ANIMATION.SPLASH_DURATION);
}

/**
 * Redimensiona el grafo cuando la ventana cambia
 */
export function handleWindowResize(graphData) {
  if (graphData) {
    // La función se llamará desde el módulo de grafo
    window.dispatchEvent(new Event("graph:resize"));
  }
}
