import { graphRenderer } from './graphRenderer.js';

// --- Variables para el control del bucle de animación ---
let animationFrameId;
let flightStartTime;
let flightDurationMs;
let currentPathNode;
let planeElement;
let onFlightCompleteCallback;

/**
 * El bucle principal de la simulación de vuelo.
 * Se ejecuta en cada frame del navegador para actualizar la posición del avión.
 * @param {DOMHighResTimeStamp} timestamp - Proporcionado por requestAnimationFrame.
 */
function simulationLoop(timestamp) {
    if (!flightStartTime) {
        flightStartTime = timestamp;
    }

    const elapsedTime = timestamp - flightStartTime;
    const progress = Math.min(elapsedTime / flightDurationMs, 1); // Progreso de 0.0 a 1.0

    updatePlanePosition(progress);

    if (progress < 1) {
        animationFrameId = requestAnimationFrame(simulationLoop);
    } else {
        // El vuelo ha terminado
        planeElement.style('display', 'none'); // Ocultar el avión al llegar
        if (onFlightCompleteCallback) {
            onFlightCompleteCallback();
        }
    }
}

/**
 * Actualiza la posición visual del elemento 'avión' a lo largo del path SVG.
 * @param {number} progress - El progreso del vuelo (0.0 a 1.0).
 */
function updatePlanePosition(progress) {
    if (currentPathNode) {
        const pathLength = currentPathNode.getTotalLength();
        const point = currentPathNode.getPointAtLength(progress * pathLength);
        planeElement.attr('transform', `translate(${point.x}, ${point.y})`);
    }
}

/**
 * Inicializa el controlador de animación. Crea el elemento visual para el avión.
 */
function initialize() {
    // Seleccionamos el SVG principal creado por graphRenderer
    const svg = graphRenderer.getSvg();
    if (!svg) {
        console.error("El SVG principal no está disponible para inicializar el avión.");
        return;
    }

    // Creamos el elemento del avión, inicialmente oculto.
    planeElement = svg.append('circle')
        .attr('id', 'plane-icon')
        .attr('r', 5)
        .attr('fill', 'red')
        .style('display', 'none')
        .style('filter', 'drop-shadow(0 0 2px rgba(0,0,0,0.7))');
}

/**
 * Inicia la animación de un vuelo de un punto a otro.
 * @param {string} originId - ID del aeropuerto de origen (ej: 'BOG').
 * @param {string} destinationId - ID del aeropuerto de destino (ej: 'MIA').
 * @param {number} durationMs - Duración de la animación en milisegundos.
 * @returns {Promise<void>} - Una promesa que se resuelve cuando el vuelo termina.
 */
function fly(originId, destinationId, durationMs) {
    return new Promise((resolve) => {
        const svg = graphRenderer.getSvg();
        if (!svg) {
            console.error("SVG no disponible para la animación");
            resolve();
            return;
        }

        // Busca el 'path' de la ruta que ya debería estar dibujado
        currentPathNode = d3.select(`#route-path-${originId}-${destinationId}`).node();
        
        // Si el path no existe, créalo dinámicamente basándote en las posiciones de los nodos
        if (!currentPathNode) {
            // Busca los nodos (círculos) en el SVG
            const originCircle = d3.select(`circle[data-id="${originId}"]`).node();
            const destCircle = d3.select(`circle[data-id="${destinationId}"]`).node();

            // Busca como alternativa en todos los circles (si no tienen data-id)
            if (!originCircle || !destCircle) {
                const circles = d3.selectAll('circle');
                let foundOrigin, foundDest;

                circles.each(function(d, i) {
                    if (d && d.id === originId) foundOrigin = this;
                    if (d && d.id === destinationId) foundDest = this;
                });

                if (!foundOrigin || !foundDest) {
                    console.error(`No se encontraron los nodos: ${originId} -> ${destinationId}`);
                    resolve();
                    return;
                }

                // Obtén las posiciones de los nodos (D3 las almacena en d.x y d.y)
                const originData = d3.select(foundOrigin).datum();
                const destData = d3.select(foundDest).datum();

                if (!originData || !destData || originData.x === undefined || destData.x === undefined) {
                    console.error("No se pudieron obtener las posiciones de los nodos");
                    resolve();
                    return;
                }

                // Crea un path temporal para la animación
                currentPathNode = svg.append('path')
                    .attr('id', `route-path-${originId}-${destinationId}`)
                    .attr('d', `M${originData.x},${originData.y}L${destData.x},${destData.y}`)
                    .attr('stroke', 'none')  // Invisible
                    .attr('fill', 'none')
                    .node();
            }
        }

        if (!currentPathNode) {
            console.error(`No se pudo crear el path para: ${originId} -> ${destinationId}`);
            resolve();
            return;
        }

        flightDurationMs = durationMs;
        flightStartTime = null;
        onFlightCompleteCallback = resolve;

        // Mostramos y posicionamos el avión en el inicio
        planeElement.style('display', 'block');
        updatePlanePosition(0);

        // Iniciamos el bucle de animación
        animationFrameId = requestAnimationFrame(simulationLoop);
    });
}

/**
 * Detiene cualquier animación de vuelo que esté en curso.
 */
function stopCurrentFlight() {
    cancelAnimationFrame(animationFrameId);
    console.log("Animación de vuelo detenida.");
}

// Exportamos las funciones públicas
export const animationController = {
    initialize,
    fly,
    stopCurrentFlight
};