# R4 Frontend - Arquitectura Modular Unificada (SOLID)

## Problema Resuelto

El proyecto tenía múltiples archivos con funcionalidades duplicadas:
- `Frontend/static/main.js` (Conflicto con `app.js`)
- `Frontend/templates/index.html` (Conflicto con `index.html`)
- Incompatibilidad con estructura SOLID existente

## Solución: Modularización SOLID

Se integró R4 **dentro de la arquitectura existente**, respetando **Single Responsibility Principle**.

---

## Estructura de Directorios

```
Frontend/
├── index.html                          ← HTML unificado (con sección R4)
├── app.js                              ← Entry point (orquesta todos los módulos)
├── styles.css
├── js/
│   ├── api/
│   │   └── client.js                   ← API HTTP calls
│   ├── constants/
│   │   └── config.js                   ← Configuración global (INCLUYE R4_API)
│   ├── services/
│   │   ├── r4InterruptionService.js    ✓ NUEVO - Lógica de interrupciones
│   │   ├── graphService.js             ← Existente - Operaciones de grafo
│   │   ├── dynamicPlanService.js       ← Existente - Planificación dinámica
│   │   └── routeService.js             ← Existente - Operaciones de rutas
│   ├── ui/
│   │   ├── r4FlightSimulation.js       ✓ NUEVO - Renderización vuelo
│   │   ├── graphRenderer.js            ← Existente - Grafo D3
│   │   ├── routesRenderer.js           ← Existente - Rutas
│   │   ├── airportPanel.js             ← Existente - Info aeropuerto
│   │   ├── dynamicPanel.js             ← Existente - Panel dinámico
│   │   └── debugRenderer.js            ← Existente - Debug
│   ├── handlers/
│   │   ├── r4EventHandlers.js          ✓ NUEVO - Eventos de R4
│   │   └── eventHandlers.js            ← Existente - Otros eventos
│   └── utils/
│       └── uiUtils.js                  ← Utilidades UI
```

---

## Principios SOLID Aplicados

### 1. **Single Responsibility Principle (SRP)**

Cada módulo tiene **una única responsabilidad**:

| Módulo | Responsabilidad |
|--------|-----------------|
| `r4InterruptionService.js` | Lógica de interrupciones (sin UI) |
| `r4FlightSimulation.js` | Renderización de vuelo (sin lógica) |
| `r4EventHandlers.js` | Manejo de eventos (sin lógica ni UI) |
| `config.js` | Configuración (sin lógica) |
| `app.js` | Orquestación (sin implementación) |

### 2. **Open/Closed Principle (OCP)**

- Módulos abiertos a extensión (se agregó R4 sin modificar existentes)
- Cerrados a modificación (existentes funcionan igual)

### 3. **Liskov Substitution Principle (LSP)**

- Services tienen interfaz consistente (métodos async)
- UI renderers intercambiables

### 4. **Interface Segregation Principle (ISP)**

- `apiClient` expone métodos específicos por dominio
- `r4InterruptionService` expone solo métodos R4

### 5. **Dependency Inversion (DI)**

- `app.js` inyecta `refs` en handlers
- Handlers usan servicios, no directamente fetch
- Services usan `apiClient` centralizado

---

## Flujo de Datos (SOLID Architecture)

```
app.js (orquestador)
  │
  ├─→ r4EventHandlers (event binding)
  │        │
  │        └─→ r4InterruptionService (lógica)
  │                 │
  │                 └─→ fetch (via baseURL)
  │
  └─→ r4FlightSimulation (UI)
           │
           └─→ canvas rendering
```

**Cada capa tiene responsabilidad única y bien definida.**

---

## Cómo se Integró R4

### 1. **Creación de Módulos Dedicados**

```
✓ r4InterruptionService.js  - Gestiona estado y lógica
✓ r4FlightSimulation.js     - Renderiza en canvas
✓ r4EventHandlers.js        - Conecta eventos con servicios
```

Cada módulo:
- Responsabilidad única
- Exporta instancia singleton
- No depende de otros módulos R4
- Depende de servicios genéricos (apiClient, config)

### 2. **Actualización de HTML**

```html
<!-- Agregada sección R4 en index.html -->
<section>
  <h2>R4: Simulación de Vuelo</h2>
  <!-- Controles R4 -->
</section>
```

- No se eliminó HTML anterior
- Se agregó como nueva sección
- Mismo estilo que secciones existentes

### 3. **Actualización de app.js**

```javascript
// Importar módulos R4
import { R4EventHandlers } from "./js/handlers/r4EventHandlers.js";
import { r4FlightSimulation } from "./js/ui/r4FlightSimulation.js";

// Crear instancia R4
const r4EventHandlers = new R4EventHandlers(refs);

// Registrar event listeners
refs.btnR4IniciarVuelo.addEventListener("click", (e) => 
  r4EventHandlers.handleR4IniciarVuelo(e)
);

// Inicializar R4 en DOMContentLoaded
r4FlightSimulation.init(canvas);
```

- Mismo patrón que código existente
- Sin modificar lógica existente
- Extensión limpia (OCP)

### 4. **Actualización de config.js**

```javascript
export const CONFIG = {
  API: { /* ... existente ... */ },
  R4_API: {  // ✓ NUEVO
    BASE_URL: "http://127.0.0.1:5000",
    ENDPOINTS: {
      VUELO_INICIAR: "/api/vuelo/iniciar",
      // ...
    }
  }
}
```

- R4 puede estar en servidor separado
- Si integran en Flask/FastAPI existente, cambiar BASE_URL

---

## Ventajas de Esta Arquitectura

✅ **Single Responsibility**: Cada archivo tiene una responsabilidad clara
✅ **Modular**: Se puede eliminar R4 sin afectar el resto
✅ **Testeable**: Cada módulo se puede testear independientemente
✅ **Mantenible**: Fácil de entender y modificar
✅ **Extensible**: Agregar nuevas features sin modificar existentes
✅ **Reutilizable**: Services reutilizables por otros handlers

---

## Cómo Funciona el Flujo Completo (SOLID)

### Ejemplo: Usuario hace clic en "Iniciar Vuelo"

```
1. Click event (DOM)
   ↓
2. app.js → r4EventHandlers.handleR4IniciarVuelo()
   ↓
3. r4EventHandlers valida inputs
   ↓
4. Llama r4InterruptionService.iniciarVuelo()
   ↓
5. r4InterruptionService.fetch() → Backend
   ↓
6. Recibe respuesta { ok: true }
   ↓
7. Llama r4FlightSimulation.animarVuelo()
   ↓
8. r4FlightSimulation.dibujarAvionEnVuelo()
   ↓
9. Canvas renderiza ✈
```

**Cada paso es independiente y reutilizable.**

---

## Configuración de Servidores

### Opción A: R4 en Flask separado (actual)

```javascript
// config.js
R4_API: {
  BASE_URL: "http://127.0.0.1:5000",  // Flask (Puerto diferente)
  ENDPOINTS: { /* R4 endpoints */ }
}
```

### Opción B: R4 integrado en FastAPI existente

```javascript
// config.js
R4_API: {
  BASE_URL: "http://127.0.0.1:8000/api",  // Mismo que API principal
  ENDPOINTS: { /* R4 endpoints */ }
}
```

**Para cambiar: Editar solo `config.js`, nada más.**

---

## Archivos Eliminados (Duplicados Resueltos)

```
❌ Frontend/static/main.js      (ahora todo está modularizado)
❌ Frontend/templates/index.html (todo en Frontend/index.html)
❌ Frontend/app.js (antiguo)     (ahora Frontend/app.js con modularización)
```

**Los controles de esos archivos se integraron en los nuevos módulos.**

---

## Verificación de SOLID

### ✅ Single Responsibility

```javascript
// r4InterruptionService.js - Solo interrupciones
// r4FlightSimulation.js - Solo rendering
// r4EventHandlers.js - Solo manejo de eventos
// app.js - Solo orquestación
```

### ✅ Open/Closed

```javascript
// Abierto a extensión:
// - Agregar nuevos servicios sin modificar existentes
// - Agregar nuevos handlers sin modificar existentes

// Cerrado a modificación:
// - eventHandlers.js no cambió
// - graphRenderer.js no cambió
// - API client no cambió
```

### ✅ Liskov Substitution

```javascript
// Todos los services usan fetch estándar
// Todos los handlers usan mismo patrón de eventos
// UI renderers usan canvas de forma consistente
```

### ✅ Interface Segregation

```javascript
// r4InterruptionService expone:
// - iniciarVuelo()
// - completarVuelo()
// - obtenerEstado()
// - bloquearRuta()
// - recalcularItinerario()
// SIN exponer detalles internos de fetch
```

### ✅ Dependency Inversion

```javascript
// app.js (alto nivel) NO depende de detalles de r4EventHandlers
// r4EventHandlers depende de r4InterruptionService (abstración)
// r4InterruptionService depende de apiClient (abstración)
// Inyección de dependencias via config centralizado
```

---

## Cómo Mantener la Arquitectura

### Para agregar nuevas features:

1. **Crear nuevo service** en `js/services/`
   - Responsabilidad única
   - Export singleton

2. **Crear nuevo handler** en `js/handlers/` (si necesita eventos)
   - Recibe referencias de refs
   - Usa service

3. **Actualizar HTML** si necesita UI
   - Agregaryuevo ID a elementos

4. **Actualizar app.js**
   - Importar nuevo módulo
   - Crear instancia
   - Registrar listeners

5. **Nunca**:
   - ❌ Agregar lógica a handlers
   - ❌ Agregar lógica a renderers
   - ❌ Mezclar responsabilidades

---

## Prueba de Integración

```bash
# 1. Iniciar backend R4 (Flask)
cd Backend
python flask_app.py
# Debería conectar en http://127.0.0.1:5000

# 2. Abrir frontend
# http://localhost:8000  (o donde esté servido)

# 3. Cambiar puerto si es necesario
# Editar Frontend/js/constants/config.js
# CONFIG.R4_API.BASE_URL = "http://127.0.0.1:8000/api"  # si integrado
```

---

## Resumen

| Aspecto | Antes | Después |
|--------|-------|---------|
| Archivos conflictivos | app.js + main.js | Solo app.js modularizado |
| Responsabilidades | Mezcladas | Separadas (SOLID) |
| Mantenibilidad | Difícil | Fácil |
| Extensibilidad | Limitada | Abierta |
| Testabilidad | Baja | Alta |
| Documentación | Ninguna | SOLID clara |

**Resultado**: Código limpio, modular y profesional listo para sustentación.
