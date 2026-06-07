# Análisis del Flujo Actual — Requerimiento 2.3 (Planificación Avanzada)

> Excluye: sugerencia de ruta (`routing.py` / `calculate_suggested_route`).

---

## 1. Arquitectura General

El R2.3 sigue una arquitectura **Frontend (JS) ↔ Backend (FastAPI REST) ↔ Lógica de Negocio (Python)** con sesiones almacenadas en memoria del servidor.

| Capa | Rol |
|------|-----|
| `app.js` | Orquestador: handlers de UI que llaman a `simulation.js` |
| `simulation.js` | Cliente de estado: gestiona `sessionId` y `state`, llama a `api.js` |
| `api.js` | HTTP Client: llama a endpoints REST del backend |
| `api.py` (FastAPI) | Router: expone endpoints, delega en módulos `dynamic/*` |
| `dynamic/core.py` | Motor central: validación, costos obligatorios, tiempo, regla 20% |
| `dynamic/models.py` | `DynamicState` dataclass: estado completo de la sesión |
| `dynamic/session.py` | Ciclo de vida: crear/obtener/finalizar sesión |
| `dynamic/activities.py` | Actividades opcionales |
| `dynamic/jobs.py` | Sistema de trabajo/ingresos |
| `dynamic/flights.py` | Operaciones de vuelo (inicio, llegada, listado) |
| `dynamic/report.py` | Generación de reporte final |
| `dynamic/interruption.py` | Manejo de interrupciones (R2.4, pero integrado) |
| `ui.js` | Renderizado de paneles HTML dinámicos |

---

## 2. Flujo Paso a Paso

### 2.1 Inicio de Sesión

```
[Usuario] → click "Iniciar Sesión Dinámica"
  → app.js: handleDynamicStart()
    → sim.startSession(origin, budget, hours)
      → api.dynamicStart(origin, budget, hours)  [POST /api/dynamic/start]
        → session.py: start_dynamic_session()
          1. Valida que el aeropuerto origen existe
          2. Crea session_id (UUID)
          3. Inicializa DynamicState:
             - budget_usd = initial_budget
             - time_left_min = total_time_hours * 60
             - visited = [origin]
             - minutes_since_food = 0, minutes_since_lodging = 0
             - total_distance_km = 0, free_distance_km = 0
             - in_transit = False
          4. Calcula suggested_route (excluido de este análisis)
          5. Almacena en app_state.dynamic_sessions[session_id]
        ← Devuelve estado serializado
    ← Almacena sessionId y state en memoria del frontend
  → highlightSession() — resalta nodos/aristas visitados en el globo
  → refreshDynamicUI() — renderiza:
      - showDynamicState() — info de sesión (ubicación, presupuesto, tiempo)
      - showSuggestedRoute() — ruta sugerida (excluido)
      - showSteps() — historial de acciones (vacío al inicio)
      + 3 llamadas paralelas:
        - sim.listActivities() → GET /api/dynamic/activities/{id}
        - sim.listJobs() → GET /api/dynamic/jobs/{id}
        - sim.listFlights() → GET /api/dynamic/flight-options/{id}
```

### 2.2 Actividades Opcionales (R2.3.a)

```
[Usuario] → selecciona actividades (checkboxes) → click "Aplicar Actividades"
  → app.js: handleDynamicActivities()
    → sim.applyActivities([nombres])
      → api.dynamicChooseActivities(sessionId, [nombres])  [POST /api/dynamic/activities/{id}]
        → activities.py: choose_dynamic_activities()
          1. Obtiene aeropuerto actual
          2. Por cada actividad:
             a. Busca actividad por nombre
             b. apply_cost_and_time():
                - validate_action() — verifica tiempo y presupuesto suficiente
                - budget_usd -= activity.cost_usd
                - total_spent += activity.cost_usd
                - advance_time() — incrementa minutos desde última comida/hospedaje,
                  calcula eventos obligatorios (comidas, hospedajes)
                - time_left_min -= duration_min
                - stay_min += duration_min (cuenta como tiempo de estancia)
                - Registra DynamicStep(action="actividad")
             c. apply_mandatory_events() — aplica descuentos de comida/alojamiento
                si se excedieron los intervalos (8h / 20h)
        ← Devuelve estado actualizado
    → refreshDynamicUI() — actualiza todos los paneles
```

**Listado de actividades** (llamada GET automática):
- `list_dynamic_activities()`:
  - Para cada actividad del aeropuerto actual
  - Calcula `estimate_mandatory_costs()` — proyecta cuántas comidas/hospedajes se gatillarían
  - Marca `affordable: true/false` según si el presupuesto alcanza (costo actividad + costos obligatorios proyectados)
  - Frontend deshabilita checkboxes de actividades no asequibles

### 2.3 Trabajos e Ingresos (R2.3.b)

```
[Usuario] → cuando presupuesto < 35% del inicial, aparecen trabajos
  → ui.js: showJobs() — radio buttons con nombre, tarifa/hora, max horas

[Usuario] → ingresa horas → click "Trabajar"
  → app.js: handleDynamicWork()
    1. Validaciones previas (frontend):
       - horas ≤ max_horas del trabajo
       - tiempo_restante ≥ horas * 60
    2. sim.work(jobName, hours)
      → api.dynamicWork(sessionId, jobName, hours)  [POST /api/dynamic/work/{id}]
        → jobs.py: perform_dynamic_work()
          1. can_work() → budget_usd < initial_budget * 0.35
          2. Valida horas ≤ max_hours del trabajo
          3. apply_time_only():
             - validate_action() — solo verifica tiempo, costo = 0
             - advance_time() — avanza tiempo, gatilla eventos obligatorios
             - stay_min += hours * 60
          4. budget_usd += hourly_rate * hours  ← INGRESO
          5. total_earned += earned
          6. Registra DynamicStep(action="trabajo", metadata={earned, hours})
          7. apply_mandatory_events() — descuenta comidas/hospedajes si aplica
        ← Devuelve estado actualizado
    → refreshDynamicUI()
```

**Regla de activación**: `can_work()` verifica `budget_usd < initial_budget * 35%`. Si el presupuesto está por encima, la API devuelve `jobs: []` y el frontend muestra "Sin trabajos disponibles".

### 2.4 Vuelos Dinámicos (R2.3.c)

#### Listado de opciones de vuelo

```
GET /api/dynamic/flight-options/{session_id}
  → flights.py: list_dynamic_flight_options()
    Por cada ruta saliente del aeropuerto actual:
      - Filtra rutas bloqueadas
      - Filtra destinos ya visitados
      - Para cada aeronave disponible en la ruta:
        - calculate_segment_cost(route, cfg, state):
          - Si route.base_cost != 0 → costo normal (distancia × costo_km)
          - Si route.base_cost == 0 (subsidiada):
            - Si total_distance_km == 0 → permite (costo = 0)
            - Si no, calcula distancia total proyectada vs distancia gratuita proyectada
            - Si projected_free > projected_total * 0.2 → retorna None (no permitida)
            - Sino → costo = 0
          - Si retorna None, se asigna cost = 0.0 (en listado se muestra igual)
        - Calcula tiempo: distance_km × time_per_km
        - Incluye bandera "subsidized"
    ← Agrupa por destino, muestra costo, tiempo, tipo aeronave, badge de subsidio
```

#### Ejecución de vuelo en dos fases

```
FASE 1 — START (antes de la animación)
[Usuario] → selecciona vuelo → click "Volar"
  → app.js: handleDynamicFly()
    1. Validaciones frontend:
       - time_left_min ≥ flight_time
       - budget_usd ≥ flight_cost
       - Si es subsidiada y total_distance_km > 0:
         Calcula projected_free > projected_total * 0.2
         Si excede → muestra subsidy modal (advertencia, no bloquea)
    2. sim.flyStart(destination, aircraft)
      → api.dynamicFlyStart(sessionId, dest, aircraft)  [POST /api/dynamic/fly/start/{id}]
        → flights.py: start_dynamic_flight()
          1. Valida: ruta existe, no bloqueada, destino no visitado, aeronave disponible
          2. Si stay_min < required_stay_min:
             - Aplica tiempo libre forzoso (costo 0, avanza tiempo, cuenta como estancia)
          3. calculate_segment_cost() — verifica regla 20% (retorna None → error)
          4. estimate_mandatory_costs() — proyecta costos obligatorios del vuelo
          5. Valita projected_budget ≥ 0
          6. state.mark_in_transit(origin, destination, aircraft)
             - in_transit = True
             - transit_from, transit_to, transit_aircraft
        ← Devuelve estado con in_transit flags
    → refreshDynamicUI()
    → graph.fly(origin, destination, animDuration) — animación 3D

ANIMACIÓN EN CURSO (el usuario puede interrumpir bloqueando la ruta)
  → app.js: currentFlight = { origin, destination }
  → Si se bloquea la ruta:
    - graph.stopFlight()
    - flightInterrupted = true
    - sim.interruptRoute() → redirige al origen

FASE 2 — ARRIVE (después de la animación)
  → Si NO fue interrumpido:
    sim.flyArrive()
      → api.dynamicFlyArrive(sessionId)  [POST /api/dynamic/fly/arrive/{id}]
        → flights.py: complete_dynamic_flight()
          1. Verifica in_transit == True
          2. apply_cost_and_time():
             - budget_usd -= seg_cost
             - total_spent += seg_cost
             - advance_time() — avanza tiempo de vuelo
             - time_left_min -= seg_time
             - stay_min NO se incrementa (count_stay=False)
             - Registra DynamicStep(action="vuelo")
          3. apply_mandatory_events() — comidas/hospedajes si aplican
          4. total_distance_km += distance_km
          5. Si ruta subsidiada: free_distance_km += distance_km
          6. current_airport = destination
          7. visited.append(destination)
          8. stay_min = 0.0 (reinicia contador de estancia)
          9. required_stay_min = route.min_stay_min
          10. clear_transit() — limpia estado in_transit
        ← Devuelve estado actualizado
    → refreshDynamicUI()
    → highlightSession() — resalta nueva ruta en el globo
```

### 2.5 Finalizar Sesión

```
[Usuario] → click "Finalizar Sesión"
  → app.js: handleDynamicFinish()
    → sim.finishSession()
      → api.dynamicFinish(sessionId)  [POST /api/dynamic/finish/{id}]
        → session.py: end_dynamic_session()
          - Elimina session_id del diccionario
    → graph.resetHighlights() — limpia resaltados del globo
    → ui.clearDynamicPanel() — limpia todos los paneles dinámicos
    → sessionId = null, state = null (en simulation.js)
```

### 2.6 Generación de Reporte (R2.5)

```
[Usuario] → click "Generar Reporte"
  → app.js: handleGenerateReport()
    → sim.getReport()
      → api.dynamicReport(sessionId)  [GET /api/dynamic/report/{id}]
        → report.py: generate_final_report()
          1. Inicializa mapa de destinos desde state.visited
          2. Itera sobre todos los DynamicSteps:
             - "actividad" → agrega a lista activities, suma stay_min + duration
             - "trabajo" → agrega a lista jobs, suma stay_min + hours*60
             - "vuelo" → agrega a lista flights, suma elapsed_time
             - "alimentacion" → agrega a mandatory_fees, suma total_food_cost
             - "alojamiento" → agrega a mandatory_fees, suma total_lodging_cost
             - "tiempo_libre" → suma stay_min + duration
             - Cada step con costo > 0 suma al total_cost del destino
          3. Agrega stay_min actual del aeropuerto corriente
          4. Calcula totales:
             - initial_budget, total_spent, total_earned, final_budget
             - total_time_spent_min = stay_total + flight_total
             - total_food_cost, total_lodging_cost
        ← Devuelve estructura con:
           { destinations, flights, activities, jobs, totals, mandatory_fees }
    → ui.showReportModal(report) — modal con tablas por sección
```

### 2.7 Exportar Reporte

```
[Usuario] → selecciona formato (CSV/JSON) → click "Exportar"
  → Redirecciona a:
    GET /api/dynamic/report/export/{session_id}?format=csv|json
      → report.py: export_report_format()
        - Si JSON: json.dumps(report_data)
        - Si CSV: escribe filas para TOTALES, DESTINOS, VUELOS,
          ACTIVIDADES, TRABAJOS, COBROS OBLIGATORIOS
      ← Response con Content-Disposition: attachment
```

---

## 3. Reglas de Negocio Clave

### 3.1 Costos Obligatorios (Comida y Alojamiento)

- **Alimentación**: cada 8 horas (480 min). Si se cruza el intervalo durante una acción, se descuenta automáticamente.
- **Alojamiento**: cada 20 horas (1200 min). Misma lógica.
- El costo se toma del aeropuerto donde ocurre la acción (o último aeropuerto visitado si ocurre en vuelo).
- Se proyectan costos obligatorios en `estimate_mandatory_costs()` para validaciones preventivas.

### 3.2 Regla del 20% de Rutas Subsidiadas

- Rutas con `base_cost == 0` son subsidiadas (costo 0).
- La distancia acumulada en rutas subsidiadas no puede exceder el 20% de la distancia total viajada.
- En la primera sesión (`total_distance_km == 0`), se permite cualquier ruta subsidiada.
- `calculate_segment_cost()` retorna `None` si se excede el 20%, y el backend lanza error.

### 3.3 Estancia Mínima

- Al llegar a un destino, `required_stay_min` se establece desde `route.min_stay_min`.
- Antes de volar, si `stay_min < required_stay_min`, se fuerza tiempo libre (costo 0) por la diferencia.
- El tiempo libre cuenta como estancia y se registra como `DynamicStep(action="tiempo_libre")`.

### 3.4 Restricción de No Repetir Aeropuertos

- `perform_dynamic_flight()` y `start_dynamic_flight()` lanzan error si `destination in state.visited`.

### 3.5 Presupuesto como Restricción Dura

- `validate_action()` verifica: `budget_usd - (cost + mandatory_costs) >= 0`.
- `estimate_mandatory_costs()` anticipa comidas/hospedajes durante la acción y los suma al costo proyectado.
- En vuelos, se hace doble validación: en `start_dynamic_flight()` y en `complete_dynamic_flight()`.

---

## 4. Flujo de Datos Completo (Diagrama de Secuencia)

```
Usuario          Frontend (app.js)      simulation.js       api.js            Backend (api.py → dynamic/)
  │                    │                    │                 │                     │
  ├─ Iniciar ─────────→┤                    │                 │                     │
  │                    ├─ startSession() ──→┤                 │                     │
  │                    │                    ├─ dynamicStart()─→┤                     │
  │                    │                    │                 ├─ POST /dynamic/start ─→ session.start_dynamic_session()
  │                    │                    │                 │                     │ ← DynamicState
  │                    │                    │← estado ───────┤                     │
  │                    │← state ───────────┤                    │                     │
  │                    ├─ refreshDynamicUI()                    │                     │
  │                    │  ├─ showDynamicState()                 │                     │
  │                    │  ├─ showSuggestedRoute()               │                     │
  │                    │  ├─ showSteps()                        │                     │
  │                    │  └─ Promise.all([                      │                     │
  │                    │        listActivities(),               │                     │
  │                    │        listJobs(),                     │                     │
  │                    │        listFlights()                   │                     │
  │                    │     ])                                 │                     │
  │                    │       │                                │                     │
  ├─ Actividades ─────→┤       │                                │                     │
  │                    ├─ applyActivities() ──→┤                 │                     │
  │                    │                    ├─ chooseActivities()┤                     │
  │                    │                    │  ├─ POST /activities ─→ activities.choose_dynamic_activities()
  │                    │                    │  │                   │  → apply_cost_and_time()
  │                    │                    │  │                   │  → advance_time()
  │                    │                    │  │                   │  → apply_mandatory_events()
  │                    │                    │← estado actualizado │                     │
  │                    ├─ refreshDynamicUI()│                    │                     │
  │                    │                    │                    │                     │
  ├─ Trabajar ────────→┤                    │                    │                     │
  │  (budget < 35%)    ├─ work() ──────────→┤                    │                     │
  │                    │                    ├─ dynamicWork() ───→┤                     │
  │                    │                    │                 ├─ POST /work ──────────→ jobs.perform_dynamic_work()
  │                    │                    │                 │                     │  → apply_time_only()
  │                    │                    │                 │                     │  → advance_time()
  │                    │                    │                 │                     │  → budget += earned
  │                    │                    │← estado ───────┤                     │  → apply_mandatory_events()
  │                    ├─ refreshDynamicUI()                    │                     │
  │                    │                    │                    │                     │
  ├─ Volar ───────────→┤                    │                    │                     │
  │                    ├─ flyStart() ──────→┤                    │                     │
  │                    │                    ├─ dynamicFlyStart()→┤                     │
  │                    │                    │                 ├─ POST /fly/start ─────→ flights.start_dynamic_flight()
  │                    │                    │                 │                     │  1. Validaciones
  │                    │                    │                 │                     │  2. Tiempo libre si estancia < min
  │                    │                    │                 │                     │  3. Verificar regla 20%
  │                    │                    │                 │                     │  4. Proyectar costos obligatorios
  │                    │                    │                 │                     │  5. mark_in_transit()
  │                    │                    │← in_transit ───┤                     │
  │◄─── Animación ────┤                    │                    │                     │
  │   graph.fly()      │                    │                    │                     │
  │                    │                    │                    │                     │
  ├─ (opcional) ──────→┤                    │                    │                     │
  │  Bloquear ruta     ├─ interruptRoute()─→┤                    │                     │
  │                    │                    ├─ POST /simulation/interrupt ────────────→ interruption.handle_interruption()
  │                    │                    │                 │                     │  → redirige viajero
  │◄─── stopFlight() ──┤                    │                    │                     │
  │                    │                    │                    │                     │
  ├─ Llegada ─────────→┤                    │                    │                     │
  │  (fin animación)   ├─ flyArrive() ─────→┤                    │                     │
  │                    │                    ├─ dynamicFlyArrive()┤                     │
  │                    │                    │                 ├─ POST /fly/arrive ───→ flights.complete_dynamic_flight()
  │                    │                    │                 │                     │  1. apply_cost_and_time()
  │                    │                    │                 │                     │  2. advance_time()
  │                    │                    │                 │                     │  3. apply_mandatory_events()
  │                    │                    │                 │                     │  4. Actualizar distancias
  │                    │                    │                 │                     │  5. Mover a destino
  │                    │                    │                 │                     │  6. clear_transit()
  │                    │                    │← estado ───────┤                     │
  │                    ├─ refreshDynamicUI()│                    │                     │
  │                    ├─ highlightSession()│                    │                     │
  │                    │                    │                    │                     │
  ├─ Reporte ─────────→┤                    │                    │                     │
  │                    ├─ getReport() ─────→┤                    │                     │
  │                    │                    ├─ dynamicReport() ─→┤                     │
  │                    │                    │                 ├─ GET /dynamic/report ──→ report.generate_final_report()
  │                    │                    │                 │                     │  → Procesa DynamicSteps
  │                    │                    │← report_data ──┤                     │
  │                    ├─ showReportModal() │                    │                     │
```

---

## 5. Archivos Involucrados

| Archivo | Propósito | Líneas Relevantes |
|---------|-----------|-------------------|
| `Backend/app/dynamic/models.py` | Dataclass `DynamicState` (sesión) | 7–42 |
| `Backend/app/dynamic/session.py` | Crear/obtener/finalizar sesión | 11–66 |
| `Backend/app/dynamic/core.py` | Motor: validación, costos obligatorios, tiempo, regla 20% | 13–211 |
| `Backend/app/dynamic/activities.py` | Listar/elegir actividades opcionales | 8–77 |
| `Backend/app/dynamic/jobs.py` | Listar/realizar trabajos | 9–82 |
| `Backend/app/dynamic/flights.py` | Listar/iniciar/completar vuelos | 15–261 |
| `Backend/app/dynamic/report.py` | Generar/exportar reporte final | 10–195 |
| `Backend/app/dynamic/interruption.py` | Manejo de interrupciones de ruta | (integrado con R2.4) |
| `Backend/app/api.py` | Endpoints REST (líneas 328–552) | 328–552 |
| `Backend/app/config.py` | Estado global de la app (`dynamic_sessions`) | — |
| `Backend/app/schemas.py` | Pydantic models para requests | — |
| `Frontend/app.js` | Handlers: `handleDynamicStart/Fly/Work/Activities/Finish/Report` | 226–415 |
| `Frontend/js/simulation.js` | Cliente de estado: `startSession`, `flyStart`, `flyArrive`, etc. | 86–160 |
| `Frontend/js/api.js` | Llamadas HTTP a endpoints REST | — |
| `Frontend/js/ui.js` | Renderizado: `showDynamicState`, `showActivities`, `showJobs`, `showFlights`, `showSteps`, `showReportModal`, `showSubsidyModal` | 174–420 |
| `Frontend/index.html` | Paneles HTML: `#dynamicPanel`, modals de subsidio/alerta/reporte | 69–78, 152–280 |
| `Frontend/js/graph.js` | Animación de vuelo en globo 3D | — |
