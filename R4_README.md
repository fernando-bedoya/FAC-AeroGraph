# R4: Flight Interruptions Module
## SkyRoute Planner - Requirement Implementation

---

## Overview

R4 implements a simple, functional flight simulation system with route blocking and automatic recovery. The system is designed for easy maintenance and modification during project sustentation.

**Key Principle**: Simple, readable code over complexity.

---

## Architecture

```
Backend (Python Flask)
├── Endpoints (6 simple REST APIs)
├── In-memory flight state
├── Dijkstra algorithm (documented line-by-line)
└── Graph operations

Frontend (Vanilla JavaScript)
├── HTML5 Canvas rendering
├── Local timer-based simulation
├── Polling for interruptions (500ms)
├── Automatic rerouting on blocking
```

---

## Backend: 6 Simple Endpoints

All endpoints operate on a global `flight_state` dictionary:

```python
flight_state = {
    "en_transito": False,
    "origen": None,
    "destino": None,
    "duracion_min": 0,
    "rutas_bloqueadas": []  # List of (origen, destino) tuples
}
```

### 1. `POST /api/vuelo/iniciar`
**Start a flight segment**

Request:
```json
{
    "origen": "BOG",
    "destino": "MDE",
    "duracion_min": 90
}
```

Response:
```json
{"ok": true}
```

**What it does**: Updates flight_state to mark flight in progress.

---

### 2. `GET /api/vuelo/estado`
**Get current flight state**

Response:
```json
{
    "en_transito": true,
    "origen": "BOG",
    "destino": "MDE",
    "interrumpido": false
}
```

**What it does**: Returns flight status and checks if current route is blocked.

---

### 3. `POST /api/vuelo/completar`
**Mark flight as completed**

Request:
```json
{
    "origen": "BOG",
    "destino": "MDE"
}
```

Response:
```json
{"ok": true}
```

**What it does**: Sets `en_transito = False`.

---

### 4. `POST /api/rutas/bloquear`
**Block a route**

Request:
```json
{
    "origen": "BOG",
    "destino": "MDE"
}
```

Response:
```json
{"bloqueada": true}
```

**What it does**:
1. Adds `(origen, destino)` tuple to `rutas_bloqueadas` list
2. Marks the edge as `blocked=True` in the graph
3. Subsequent pathfinding skips this edge

---

### 5. `GET /api/grafo`
**Get graph structure**

Response:
```json
{
    "nodos": [
        {
            "id": "BOG",
            "nombre": "Bogotá",
            "ciudad": "Bogotá",
            "hub": true
        },
        ...
    ],
    "aristas": [
        {
            "origen": "BOG",
            "destino": "MDE",
            "distancia": 150,
            "bloqueada": false
        },
        ...
    ]
}
```

**What it does**: Returns all airports and routes with current blocking status.

---

### 6. `POST /api/itinerario/recalcular`
**Recalculate route after interruption (Dijkstra)**

Request:
```json
{
    "origen": "BOG",
    "presupuesto_restante": 300,
    "tiempo_restante": 200
}
```

Response (route found):
```json
{
    "nueva_ruta": ["BOG", "CLO", "LIM"],
    "costo": 180,
    "tiempo": 150
}
```

Response (no route available):
```json
{
    "nueva_ruta": null,
    "mensaje": "Sin alternativas disponibles"
}
```

**What it does**:
1. Runs Dijkstra algorithm from `origen`
2. Ignores blocked routes
3. Finds furthest reachable airport within budget
4. Returns path to that airport

---

## Frontend: Canvas Simulation

### Key Features

#### 1. Graph Visualization
- **Hub airports**: Large green circles (>= 30px radius)
- **Regular airports**: Small gray circles (20px radius)
- **Normal routes**: Black lines with distance label (km)
- **Blocked routes**: Red dashed lines with ✕ symbol
- **Aircraft**: ✈ emoji moving along route

#### 2. Flight Simulation (Local Timer)
```javascript
// Frontend calculates progress locally
const progreso = (Date.now() - inicio) / duracion_ms
// Progress: 0.0 (origin) → 1.0 (destination)

// Demo uses 10-second flights (independent of real duration)
const DURACION_SIMULACION_MS = 10000
```

#### 3. Position Interpolation
```javascript
// Linear interpolation (lerp) between origin and destination
x = x_origin + (x_dest - x_origin) * progress
y = y_origin + (y_dest - y_origin) * progress
```

#### 4. Polling for Interruptions
```javascript
// Every 500ms during flight:
const estado = await fetch('/api/vuelo/estado')
if (estado.interrumpido === true) {
    // Handle interruption
    // 1. Stop timer
    // 2. Animate return to origin
    // 3. Recalculate route
    // 4. Show new route in green
}
```

#### 5. Modular Functions (Easy to Modify)

Each function does ONE thing:

| Function | Purpose |
|----------|---------|
| `dibujarGrafo()` | Draw all nodes and edges |
| `dibujarAvion(x, y)` | Draw aircraft at position |
| `calcularProgreso(inicio, duracion)` | Calculate 0.0-1.0 progress |
| `interpolarPosicion(x1,y1,x2,y2,t)` | Get intermediate position |
| `verificarInterrupcion()` | Poll server for interruption |
| `animarRegresoOrigen()` | Animate return to origin |
| `resaltarNuevaRuta(ruta)` | Draw new route in green |
| `iniciarVuelo()` | Main simulation loop |

---

## How to Run

### 1. Setup Backend
```bash
cd Backend
pip install flask

# Create data/grafo.json with airport network
```

### 2. Start Flask Server
```bash
python flask_app.py
# Server runs on http://localhost:5000
```

### 3. Open Frontend
```
http://localhost:5000
```

### 4. Use the Interface
- **Right panel**: Start flight (BOG → MDE)
- **Canvas**: Shows graph visualization
- **Watch**: Aircraft moves along route for 10 seconds
- **Block route**: Use "Bloquear Ruta" button to interrupt flight
- **See animation**: Aircraft returns to origin, new route appears in green

---

## Code Organization

```
Backend/
├── app/
│   ├── r4_backend.py      ← 6 REST endpoints
│   ├── r4_dijkstra.py     ← Dijkstra (documented)
│   └── graph.py           ← Graph data structure
├── flask_app.py           ← Flask setup
└── data/
    └── grafo.json         ← Airport network

Frontend/
├── templates/
│   └── index.html         ← Canvas + controls
└── static/
    └── main.js            ← All JavaScript logic
```

---

## Dijkstra Algorithm (Documented)

Located in `app/r4_dijkstra.py`:

**Time Complexity**: O((V + E) log V)
- V = number of airports
- E = number of routes

**Why Dijkstra?**
- Handles weighted edges (cost, time, distance)
- Guaranteed optimal path with positive weights
- Greedy approach is efficient
- Easy to skip blocked routes

**Line-by-line documentation** explains each step:
1. Initialize distances
2. Create min-heap priority queue
3. Process airports by cost order
4. Relax edges (check cheaper paths)
5. Update queue with improved paths
6. Return final distances

---

## Flight Interruption Flow

### Scenario: Flight is interrupted mid-flight

```
1. User starts flight: BOG → MDE (starts 10s timer)
2. At 3 seconds: User clicks "Bloquear Ruta" → BOG → MDE
3. Server adds (BOG, MDE) to rutas_bloqueadas
4. Client polls (every 500ms) and detects interrumpido=true
5. Client stops timer and animation
6. Client animates aircraft returning to BOG (1 second)
7. Client calls POST /api/itinerario/recalcular
8. Server runs Dijkstra from BOG (ignoring BOG→MDE)
9. Server returns new route: BOG → CLO → LIM
10. Client highlights new route in green
11. User can start a new flight with the new route
```

---

## Modifying the Code

### To Change Flight Duration
```javascript
// In Frontend/static/main.js
const DURACION_SIMULACION_MS = 10000  // Currently 10 seconds
// Change to your preferred value (milliseconds)
```

### To Change Polling Interval
```javascript
// In Frontend/static/main.js
const POLLING_INTERVALO_MS = 500  // Currently 500ms
// Change to check interruptions more/less frequently
```

### To Add a New Endpoint
1. Add function to `Backend/app/r4_backend.py`
2. Add route decorator: `@r4_bp.route(...)`
3. Call from frontend: `await fetchAPI('/api/...')`

### To Change Colors
```javascript
// In Frontend/static/main.js, look for:
ctx.fillStyle = '#4CAF50'  // Hub color (green)
ctx.fillStyle = '#999999'  // Regular airport (gray)
ctx.strokeStyle = '#ff0000' // Blocked route (red)
```

---

## Debugging Tips

### Server-side (Python)
```python
# Add print statements in r4_backend.py
print(f"Flight state: {flight_state}")
print(f"Route blocked: {is_route_blocked('BOG', 'MDE')}")
```

### Client-side (JavaScript)
```javascript
// Open browser DevTools (F12)
// Look for console errors
console.log('Flight state:', estado)
console.log('Progress:', progreso)
```

### Test Endpoints with curl
```bash
# Get graph
curl http://localhost:5000/api/grafo

# Start flight
curl -X POST http://localhost:5000/api/vuelo/iniciar \
  -H "Content-Type: application/json" \
  -d '{"origen":"BOG","destino":"MDE","duracion_min":90}'

# Block route
curl -X POST http://localhost:5000/api/rutas/bloquear \
  -H "Content-Type: application/json" \
  -d '{"origen":"BOG","destino":"MDE"}'
```

---

## Key Design Decisions

| Decision | Why |
|----------|-----|
| **In-memory state** | Simple, no database needed. Resets on server restart (fine for demo). |
| **Local timer** | No WebSockets complexity. Polling is sufficient for 500ms intervals. |
| **10-second demo flights** | Independent of real flight time. Easy to test interruptions. |
| **Circular layout** | Deterministic, no node overlaps. Works for any graph size. |
| **Canvas (no libraries)** | Pure JavaScript, minimal dependencies. Easy to modify. |
| **Line-by-line Dijkstra docs** | Every step explained. Easy to understand and modify. |

---

## Common Issues & Solutions

### Issue: Graph not loading
**Solution**: Ensure `data/grafo.json` exists and contains valid airport data.

### Issue: Flight doesn't start
**Solution**: Check that origin and destination are in the graph. Use 3-letter IATA codes.

### Issue: Route blocking doesn't interrupt flight
**Solution**: The frontend polls every 500ms. If you block very quickly, it may miss the interrupt. Wait 1 second before blocking.

### Issue: New route not showing after interruption
**Solution**: Check browser console (F12) for errors. Ensure `presupuesto_restante` is reasonable (e.g., 300).

---

## Testing Checklist

- [ ] Backend: `python flask_app.py` runs without errors
- [ ] Frontend: `http://localhost:5000` loads canvas
- [ ] Flight: "Iniciar Vuelo" starts 10-second animation
- [ ] Aircraft: ✈ moves smoothly across route
- [ ] Blocking: "Bloquear Ruta" interrupts mid-flight
- [ ] Return: Aircraft animates back to origin
- [ ] Reroute: New green route appears
- [ ] Completion: Flight completes without interruption
- [ ] Info: Clicking airport shows info panel

---

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `Backend/app/r4_backend.py` | ~400 | 6 Flask endpoints, flight state |
| `Backend/app/r4_dijkstra.py` | ~150 | Dijkstra with full documentation |
| `Backend/flask_app.py` | ~70 | Flask app setup |
| `Frontend/templates/index.html` | ~300 | Canvas + sidebar + controls |
| `Frontend/static/main.js` | ~600 | Animation, polling, rerouting |

**Total**: ~1,500 lines of clean, documented, modular code.

---

## Next Steps for Sustentation

1. **Explain the global state**: Show how `flight_state` dict is updated
2. **Walk through a flight**: Trace the code from "Iniciar Vuelo" to completion
3. **Explain the interruption**: Show the polling loop and how blocking is detected
4. **Show Dijkstra**: Walk through a path recalculation
5. **Demo on live server**: Start a flight, block a route, show automatic recovery

---

**Remember**: The goal is **simplicity and functionality**. Every line of code serves a purpose. No premature optimization. No unnecessary libraries.

When asked how something works, you can point directly to the code and explain it. That's the mark of good sustentation-ready code.
