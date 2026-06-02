# ANÁLISIS DEL REQUERIMIENTO 2.4: INTERRUPCIONES EN LA RED

**Fecha del análisis:** 2 de Junio, 2026
**Versión del proyecto:** Main branch
**Estado general:** 60% implementado

---

## 📋 RESUMEN EJECUTIVO

El requerimiento 2.4 requiere que el sistema permita interrupciones en rutas aéreas durante tiempo de ejecución, bloqueando aristas, redirigiendo viajeros en tránsito y recalculando itinerarios automáticamente.

**Resultado:**
- ✅ 60% del requerimiento implementado
- ❌ 40% faltante (CRÍTICO para funcionalidad completa)

---

## ✅ LO QUE FUNCIONA (IMPLEMENTADO)

### 1. Bloqueo de Rutas en el Grafo
**Estado:** ✓ Completamente implementado

- **Backend:** `Backend/app/graph.py:41-47`
  ```python
  def toggle_route_status(self, origin: str, destination: str, block: bool) -> Optional[Route]:
      """Bloquea o desbloquea una ruta y devuelve la ruta actualizada."""
      route = self.get_route(origin, destination)
      if route:
          route.blocked = block
          return route
      return None
  ```
  - Modifica la propiedad `blocked` de la ruta
  - Disponible en el modelo `Route` (línea 13 de `route.py`)

- **Endpoint API:** `Backend/app/api.py:125-151`
  ```python
  @router.post("/simulation/interrupt")
  def interrupt(origin: str, destination: str, plan_id: str):
      # Bloquea la ruta en el grafo
      updated_route = graph.toggle_route_status(origin, destination, block=True)
  ```
  - Accesible desde el frontend
  - Retorna confirmación del bloqueo

#### Verificación de Rutas Bloqueadas
- `Backend/app/dynamic/engine.py:290-291`
  ```python
  for route in graph.get_outgoing_routes(state.current_airport):
      if route.blocked:
          continue  # Skip blocked routes
  ```
  - El motor dinámico excluye rutas bloqueadas de las opciones de vuelo

---

### 2. Visualización de Rutas Bloqueadas en el Mapa
**Estado:** ✓ Completamente implementado

- **Identificación visual:** `Frontend/js/ui/graphRenderer.js:154-157`
  ```javascript
  .attr("stroke", (d) => (d.blocked ? COLORS.ARROW_BLOCKED : COLORS.ARROW))
  .attr("stroke-width", (d) => (d.blocked ? 2.8 : 1.8))
  .attr("stroke-dasharray", (d) => (d.blocked ? "6 3" : "0"))
  .attr("marker-end", (d) => (d.blocked ? "url(#arrow-blocked)" : "url(#arrow)"))
  ```

- **Estilos aplicados:**
  - Color: Rojo (`#ff4d6d`) definido en `Frontend/js/constants/config.js:47`
  - Grosor: 2.8 píxeles (vs 1.8 normal)
  - Patrón: Línea punteada (6-3 dashes)
  - Flecha: Marcador rojo bloqueado (`arrow-blocked`)

- **Marcador visual:** `Frontend/js/ui/graphRenderer.js:80-92`
  ```javascript
  // Flecha bloqueada
  defs.append("marker")
    .attr("id", "arrow-blocked")
    .attr("fill", COLORS.ARROW_BLOCKED);
  ```

---

### 3. Interfaz de Usuario para Bloquear Rutas
**Estado:** ✓ Parcialmente implementado (existe UI, falta lógica completa)

- **Componente:** `Frontend/js/ui/simulationController.js`
  - Línea 14: Botón `btnBlockRoute`
  - Línea 215-236: Método `blockCurrentRoute()` que:
    - Obtiene origen y destino del vuelo actual
    - Llama a `simulationService.blockRoute()`
    - Muestra mensaje confirmación

- **Servicio de bloqueo:** `Frontend/js/services/dynamicPlanService.js:92-98`
  ```javascript
  async blockRoute(origin, destination) {
      return await apiClient.blockRoute(origin, destination, true);
  }
  ```

- **Mensaje de confirmación:** Muestra en pantalla por 5 segundos
  ```javascript
  this.blockMessage.textContent = `✓ Ruta ${origin} → ${destination} bloqueada...`
  ```

---

## ❌ LO QUE FALTA (NO IMPLEMENTADO - CRÍTICO)

### 1. Detección de Viajero en Tránsito
**Estado:** ✗ NO IMPLEMENTADO
**Criticidad:** 🔴 CRÍTICA

**Problema:**
- No hay lógica para detectar si el viajero está actualmente volando cuando se interrumpe
- El motor dinámico (`engine.py`) no monitorea el estado "en-vuelo" de forma activa
- No existe variable de estado que indique: "el viajero está entre A y B"

**Archivos afectados:**
- `Backend/app/dynamic/engine.py` - Falta contexto de tránsito
- `Backend/app/dynamic/models.py` - Falta estado `in_transit`
- `Frontend/js/ui/animationController.js` - No reporta estado de animación

**Lo que falta en el código:**

```python
# En Backend/app/dynamic/models.py (NO EXISTE):
@dataclass
class DynamicState:
    # ... campos existentes ...
    in_transit: bool = False  # ← FALTA
    transit_from: Optional[str] = None  # ← FALTA
    transit_to: Optional[str] = None    # ← FALTA
    transit_start_time: float = 0.0     # ← FALTA
```

---

### 2. Redirección al Aeropuerto de Origen
**Estado:** ✗ NO IMPLEMENTADO
**Criticidad:** 🔴 CRÍTICA

**Problema:**
- Cuando se interrumpe una ruta, no existe mecanismo para detener la animación
- No se comunica al estado de vuelo que fue interrumpido
- El viajero no se "teletransporta" de vuelta al origen

**Requerimiento específico:**
> "Si el viajero se encuentra en tránsito en esa ruta, debe redirigirse al aeropuerto de origen del tramo"

**Lo que falta:**

```python
# Backend
def handle_in_flight_interruption(state: DynamicState, route: Route) -> DynamicState:
    """Maneja interrupción de una ruta mientras el viajero está volando"""
    if state.in_transit and state.transit_to == route.destination:
        # Redirigir al origen
        state.current_airport = state.transit_from
        state.in_transit = False
        state.steps.append(DynamicStep(
            airport_id=state.transit_from,
            action="redirección_de_emergencia",
            detail=f"Ruta interrumpida. Redirigido a {state.transit_from}",
            budget_after=state.budget_usd,
            time_left_min=state.time_left_min
        ))
        return state
    return state
```

```javascript
// Frontend - animationController.js FALTA
export async function interruptFlight() {
    // 1. Detener la animación actual
    cancelAnimationFrame(animationFrameId);

    // 2. Ocultar el avión
    planeElement.style('display', 'none');

    // 3. Notificar que fue interrumpido
    // ← NO EXISTE
}
```

---

### 3. Recalculación Automática de Itinerario
**Estado:** ✗ NO IMPLEMENTADO
**Criticidad:** 🔴 CRÍTICA

**Problema:**
- Cuando se bloquea una ruta que invalida el itinerario, no hay recalculación
- No existe endpoint para buscar ruta alternativa desde la posición actual
- El viajero queda "atrapado" sin opciones

**Requerimiento específico:**
> "Si la ruta bloqueada invalida el itinerario planificado, el sistema debe recalcular automáticamente la mejor alternativa disponible"

**Lo que falta:**

```python
# Backend/app/api.py - FALTA
@router.post("/simulation/interrupt")
def interrupt(origin: str, destination: str, plan_id: str):
    graph.toggle_route_status(origin, destination, block=True)

    # ← FALTA: Detectar si hay vuelo activo y redirigir
    # ← FALTA: Recalcular mejor alternativa
    # ← FALTA: Actualizar estado del viajero

    return {"message": "Interruption acknowledged."}
```

**Endpoint que hace falta:**

```
POST /dynamic/recalculate-after-interruption
{
    "session_id": "uuid",
    "blocked_route": {"from": "BOG", "to": "MIA"}
}
Response:
{
    "new_current_airport": "BOG",
    "new_flight_options": [...],
    "recalculated_route": {...}
}
```

---

### 4. Pausar y Reanudar Animaciones
**Estado:** ✗ MÉTODOS NO EXISTEN
**Criticidad:** 🔴 CRÍTICA

**Problema:**
- `Frontend/js/ui/simulationController.js:193-209` llama a métodos que no existen
- `animationController.js` no tiene implementados `pause()` ni `resume()`

**Código problemático:**

```javascript
// simulationController.js - Línea 193 (FALLA)
pauseSimulation() {
    if (this.animationController) {
        this.animationController.pause();  // ← ERROR: método no existe
    }
}

// simulationController.js - Línea 205 (FALLA)
resumeSimulation() {
    if (this.animationController) {
        this.animationController.resume();  // ← ERROR: método no existe
    }
}
```

**Lo que falta en `animationController.js`:**

```javascript
// MÉTODOS FALTANTES:
let paused = false;
let pausedTime = 0;

export function pause() {
    paused = true;
    pausedTime = performance.now();
    cancelAnimationFrame(animationFrameId);  // ← FALTA
}

export function resume() {
    if (!paused) return;
    paused = false;
    flightStartTime += performance.now() - pausedTime;
    animationFrameId = requestAnimationFrame(simulationLoop);  // ← FALTA
}
```

---

### 5. Callback de Progreso Durante Animación
**Estado:** ✗ NO IMPLEMENTADO
**Criticidad:** 🟠 MEDIA

**Problema:**
- La animación no reporta su progreso en tiempo real
- No se puede actualizar barra de progreso durante el vuelo
- El usuario no ve progreso del viaje

**Código problemático:**

```javascript
// simulationController.js - Línea 164
await this.animationController.fly(
    flight.origin,
    flight.destination,
    animationDuration,
    (progress) => this.updateProgress(progress, flight)  // ← Callback esperado
);

// animationController.js - Línea 76
function fly(originId, destinationId, durationMs) {
    return new Promise((resolve) => {
        // ... código ...
        // ← NO LLAMA AL CALLBACK CON PROGRESO
    });
}
```

---

## 📊 TABLA COMPARATIVA

| Aspecto | Requerimiento | Implementado | Estado |
|---------|----------------|--------------|--------|
| Bloquear aristas | "El grafo debe actualizarse bloqueando la arista" | ✅ Sí | Funcional |
| Visualizar bloqueadas | "La ruta bloqueada debe resaltarse visualmente" | ✅ Sí | Funcional |
| Detectar en-tránsito | "Si está en tránsito... debe redirigirse" | ❌ No | FALTA |
| Redireccionar | "Al aeropuerto de origen del tramo" | ❌ No | FALTA |
| Recalcular | "Recalcular automáticamente la mejor alternativa" | ❌ No | FALTA |
| Pausa/Reanuda | "Pausar y reanudar la animación de vuelo" | ❌ No | FALTA |
| Progreso visual | "Mostrar progreso durante el vuelo" | ❌ No | FALTA |

---

## 🔧 ARQUITECTURA PROPUESTA PARA COMPLETAR

### Backend
1. Extender `DynamicState` con campos de tránsito
2. Crear función `handle_flight_interruption()` en `engine.py`
3. Agregar endpoint `/dynamic/recalculate-after-interruption`
4. Modificar `/simulation/interrupt` para detectar y redirigir

### Frontend
1. Implementar `pause()` y `resume()` en `animationController.js`
2. Agregar callback de progreso a la función `fly()`
3. Mejorar `simulationController.js` para manejar interrupciones
4. Sincronizar estado de animación con backend

---

## 📍 ARCHIVOS CRÍTICOS IDENTIFICADOS

### Backend
| Archivo | Línea | Problema |
|---------|-------|----------|
| `dynamic/engine.py` | - | Falta lógica de redirección |
| `dynamic/models.py` | - | Falta estado `in_transit` |
| `api.py` | 125-151 | `/interrupt` incompleto |

### Frontend
| Archivo | Línea | Problema |
|---------|-------|----------|
| `ui/animationController.js` | 76-146 | Falta `pause()`, `resume()`, callback |
| `ui/simulationController.js` | 193-209 | Llama métodos inexistentes |
| `services/dynamicPlanService.js` | 92-98 | Bloqueo sin redirección |

---

## ✅ RECOMENDACIONES

### Prioridad 1 (CRÍTICA)
1. [ ] Implementar `pause()` y `resume()` en `animationController.js`
2. [ ] Extender `DynamicState` con campo `in_transit`
3. [ ] Crear lógica de redirección en `engine.py`

### Prioridad 2 (ALTA)
4. [ ] Agregar endpoint `/dynamic/recalculate-after-interruption`
5. [ ] Mejorar `/simulation/interrupt` para manejar tránsito
6. [ ] Sincronizar estado frontend-backend

### Prioridad 3 (MEDIA)
7. [ ] Implementar callback de progreso en animación
8. [ ] Agregar trazabilidad de interrupciones en logs
9. [ ] Agregar tests para escenarios de interrupción

---

## 📈 PUNTUACIÓN ESTIMADA

**Funcionaldad implementada:** 60% (3/5 requisitos)
- ✅ Bloqueo de rutas
- ✅ Visualización
- ✅ Interfaz básica
- ❌ Redirección
- ❌ Recalculación

**Puntuación R2.4 esperada:** 0.3/0.5 puntos (60%)
**Puntuación total afectada:** Reducción de 0.2 puntos en nota final

---

## 📝 NOTAS ADICIONALES

- El código está bien estructurado y separado por responsabilidades
- La falta no es de arquitectura, sino de implementación incompleta de funcionalidad
- Los métodos se pueden añadir sin refactorización mayor
- Todos los puntos críticos están en `engine.py` y `animationController.js`

---

**Fecha de generación:** 2 de Junio, 2026
**Generado por:** Análisis de código Claude
**Versión:** 1.0
