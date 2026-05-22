# 📁 Estructura del Frontend - Principios SOLID

## Descripción General

El frontend está estructurado siguiendo **principios SOLID** para garantizar:
- ✅ Mantenibilidad
- ✅ Escalabilidad
- ✅ Testabilidad
- ✅ Reusabilidad

---

## 📂 Estructura de Carpetas

```
Frontend/
├── index.html                    # Punto de entrada HTML
├── styles.css                    # Estilos globales
├── app.js                        # Orquestador principal (modules)
│
└── js/                           # Módulos JavaScript
    ├── api/
    │   └── client.js            # Cliente HTTP (Responsabilidad única: comunicación)
    │
    ├── services/                # Lógica de negocio
    │   ├── graphService.js      # Gestión del grafo
    │   └── routeService.js      # Gestión de rutas
    │
    ├── ui/                      # Renderización visual
    │   ├── graphRenderer.js     # Render de grafo D3.js
    │   ├── routesRenderer.js    # Render de tarjetas de rutas
    │   └── airportPanel.js      # Panel de información de aeropuertos
    │
    ├── handlers/                # Manejo de eventos
    │   └── eventHandlers.js     # Conecta UI con servicios
    │
    ├── constants/               # Configuración global
    │   └── config.js            # Configuración, colores, mensajes
    │
    └── utils/                   # Funciones auxiliares
        └── uiUtils.js           # Utilidades de interfaz
```

---

## 🎯 Principios SOLID Aplicados

### 1️⃣ **Single Responsibility Principle (SRP)**

Cada módulo tiene **una única responsabilidad**:

| Módulo | Responsabilidad |
|--------|---|
| `api/client.js` | Comunicación HTTP con el backend |
| `services/graphService.js` | Gestión y estado del grafo |
| `services/routeService.js` | Lógica de cálculo de rutas |
| `ui/graphRenderer.js` | Visualizar el grafo con D3.js |
| `ui/routesRenderer.js` | Renderizar tarjetas de rutas |
| `ui/airportPanel.js` | Mostrar info de aeropuertos |
| `handlers/eventHandlers.js` | Conectar eventos con servicios |

**Ventaja:** Si necesitas cambiar cómo se visualizan las rutas, solo editas `routesRenderer.js`

---

### 2️⃣ **Open/Closed Principle (OCP)**

Los módulos están **abiertos a extensión, cerrados a modificación**:

```javascript
// Para agregar un nuevo tipo de render, solo creas:
// ui/customRenderer.js sin tocar los existentes

export class CustomRenderer {
  render(data) { /* tu lógica */ }
}
```

---

### 3️⃣ **Liskov Substitution Principle (LSP)**

Los servicios pueden ser intercambiables:

```javascript
// Puedes reemplazar graphService con otro que tenga misma interfaz
export class GraphService {
  async loadGraph(filePath) { /* ... */ }
  getAirports() { /* ... */ }
  getRoutes() { /* ... */ }
}
```

---

### 4️⃣ **Interface Segregation Principle (ISP)**

Cada módulo expone solo lo necesario:

```javascript
// api/client.js expone métodos específicos del dominio
export class ApiClient {
  async loadGraph(filePath) { /* endpoint específico */ }
  async planBasic(origin, budget, hours) { /* endpoint específico */ }
}
```

---

### 5️⃣ **Dependency Inversion Principle (DIP)**

Dependencias inyectadas, no creadas dentro:

```javascript
// EventHandlers recibe servicios inyectados
export class EventHandlers {
  constructor(refs) {
    this.refs = refs;
    // Usa graphService, routeService, etc. que son singleton
  }
}
```

---

## 🔄 Flujo de Datos

```
Usuario interactúa con UI
        ↓
EventHandlers.handleLoadGraph()
        ↓
graphService.loadGraph()
        ↓
apiClient.loadGraph()
        ↓
Backend API
        ↓
graphService [actualiza estado]
        ↓
graphRenderer.render()
        ↓
D3.js renderiza grafo visual
```

---

## 📋 Cómo Usar Cada Módulo

### **API Client** - Comunicación
```javascript
import { apiClient } from "./js/api/client.js";

// Usar directamente:
const result = await apiClient.planBasic(origin, budget, hours);
```

### **Services** - Lógica de Negocio
```javascript
import { graphService } from "./js/services/graphService.js";
import { routeService } from "./js/services/routeService.js";

// Obtener datos
const airports = graphService.getAirports();

// Calcular
const plans = await routeService.calculateBasicPlan(origin, budget, hours);
```

### **UI Renderers** - Visualización
```javascript
import { graphRenderer } from "./js/ui/graphRenderer.js";
import { routesRenderer } from "./js/ui/routesRenderer.js";

// Renderizar
graphRenderer.render(graphData, onCustomClick);
routesRenderer.displayBasicPlans(budgetPlan, timePlan);
```

### **Event Handlers** - Coordinación
```javascript
import { EventHandlers } from "./js/handlers/eventHandlers.js";

const handlers = new EventHandlers(refs);
refs.btnLoad.addEventListener("click", (e) => handlers.handleLoadGraph(e));
```

---

## 🚀 Ventajas de esta Estructura

| Ventaja | Razón |
|---------|-------|
| 🔧 **Fácil mantener** | Si algo falla, sabes exactamente dónde |
| ➕ **Fácil agregar** | Nuevas funciones sin tocar código existente |
| 🧪 **Fácil testear** | Cada módulo es independiente |
| 📊 **Escalable** | Puedes agregar más servicios/renders |
| 🔄 **Reusable** | Módulos pueden usarse en otras apps |

---

## 📝 Naming Conventions

- **`*Service.js`** → Lógica de negocio
- **`*Renderer.js`** → Renderización visual
- **`*Client.js`** → Comunicación con APIs externas
- **`*Handlers.js`** → Manejo de eventos
- **`config.js`** → Configuración global

---

## 🔗 Dependencias Entre Módulos

```
app.js (orquestador)
├── → eventHandlers
│   ├── → graphService
│   ├── → routeService
│   ├── → graphRenderer
│   ├── → routesRenderer
│   └── → airportPanel
│
└── Utilidades
    └── → uiUtils
```

**Regla:** Los módulos de nivel inferior nunca importan de nivel superior.

---

## 🎓 Cómo Extender

### Agregar un nuevo renderer

1. Crear `js/ui/newRenderer.js`
2. Exportar una clase con método `render()`
3. Importar en `app.js`
4. Usar en event handlers

### Agregar un nuevo servicio

1. Crear `js/services/newService.js`
2. Exportar una clase singleton
3. Usar desde event handlers

### Agregar un nuevo endpoint

1. Agregar método en `api/client.js`
2. Usar desde services correspondiente

---

## ✅ Checklist SOLID

- [x] Cada módulo tiene una única responsabilidad
- [x] Módulos abiertos a extensión, cerrados a modificación
- [x] Servicios intercambiables
- [x] Interfaces segregadas
- [x] Dependencias inyectadas
- [x] Sin ciclos de dependencia
- [x] Módulos testeable...s

---

**Creado con ❤️ bajo principios SOLID**
