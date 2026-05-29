# R4 Quick Start Guide

## Project Structure Created

```
proyecto-grafos/FAC-AeroGraph/
├── Backend/
│   ├── app/
│   │   ├── r4_backend.py        ← REST endpoints (6 simple APIs)
│   │   ├── r4_dijkstra.py       ← Dijkstra algorithm (documented)
│   │   └── graph.py             ← Graph data structure (existing)
│   └── flask_app.py             ← Flask server setup
│
├── Frontend/
│   ├── templates/
│   │   └── index.html           ← Main page with canvas
│   └── static/
│       └── main.js              ← All JavaScript logic
│
└── R4_README.md                 ← Full documentation
```

## Installation & Setup

### 1. Install Python Dependencies
```bash
cd Backend
pip install flask
```

### 2. Prepare Graph Data
Create `Backend/data/grafo.json` with your airport network:

```json
{
  "aeropuertos": [
    {
      "id": "BOG",
      "nombre": "Bogotá",
      "ciudad": "Bogotá",
      "pais": "Colombia",
      "zona_horaria": "UTC-5",
      "hub": true,
      "costo_comida": 20,
      "costo_alojamiento": 80
    },
    {
      "id": "MDE",
      "nombre": "Medellín",
      "ciudad": "Medellín",
      "pais": "Colombia",
      "zona_horaria": "UTC-5",
      "hub": false,
      "costo_comida": 18,
      "costo_alojamiento": 70
    }
    // ... more airports
  ],
  "rutas": [
    {
      "origen": "BOG",
      "destino": "MDE",
      "distancia_km": 240,
      "tipos_aeronaves": ["Avion Comercial"],
      "costo_base": 0,
      "estancia_minima": 15
    }
    // ... more routes
  ]
}
```

### 3. Start the Server
```bash
python flask_app.py
```

You should see:
```
✓ Graph loaded from data/grafo.json
 * Running on http://127.0.0.1:5000
```

### 4. Open in Browser
```
http://localhost:5000
```

## How to Use (Demo)

### Start a Flight
1. Go to right panel → "Iniciar Vuelo"
2. Enter: Origen = `BOG`, Destino = `MDE`
3. Click **▶ Iniciar Vuelo**
4. Watch the ✈ emoji move across the route for 10 seconds

### Interrupt a Flight (Mid-Air)
1. While flight is moving (between 2-8 seconds)
2. Go to "Bloquear Ruta"
3. Enter same route: Origen = `BOG`, Destino = `MDE`
4. Click **🚫 Bloquear Ruta**
5. **Result**: Aircraft animates back to origin, new route shown in green

### View Airport Info
1. Click on any airport node (circle) on the canvas
2. Info panel appears in right sidebar

## API Endpoints (What Each Does)

| Method | Endpoint | What It Does |
|--------|----------|------------|
| `POST` | `/api/vuelo/iniciar` | Start a flight (updates state) |
| `GET` | `/api/vuelo/estado` | Get current flight status |
| `POST` | `/api/vuelo/completar` | Mark flight as finished |
| `POST` | `/api/rutas/bloquear` | Block a route (marks in graph) |
| `GET` | `/api/grafo` | Get all airports & routes |
| `POST` | `/api/itinerario/recalcular` | Find new route (Dijkstra) |

## Example: Block a Route with curl

```bash
# Block the BOG→MDE route
curl -X POST http://localhost:5000/api/rutas/bloquear \
  -H "Content-Type: application/json" \
  -d '{"origen":"BOG","destino":"MDE"}'

# Response: {"bloqueada": true}
```

## Code Breakdown (Where to Find Things)

### Flight Starts
**File**: `Frontend/static/main.js`, function `iniciarVuelo()`

```javascript
// 1. Call /api/vuelo/iniciar to mark flight active
// 2. Start 10-second timer
// 3. Every 500ms:
//    - Calculate progress [0, 1]
//    - Move aircraft icon
//    - Poll /api/vuelo/estado to check for blocking
```

### Route Gets Blocked
**File**: `Backend/app/r4_backend.py`, endpoint `/api/rutas/bloquear`

```python
# 1. Add (origen, destino) to rutas_bloqueadas list
# 2. Mark edge as blocked=True in graph
# 3. Frontend polling detects "interrumpido": true
# 4. Trigger interruption handling
```

### Aircraft Returns to Origin
**File**: `Frontend/static/main.js`, function `animarRegresoOrigen()`

```javascript
// 1. Animate position from current to origin (1 second)
// 2. Redraw canvas each frame
// 3. Show warning message
// 4. Call recalculate endpoint
```

### New Route Calculated
**File**: `Backend/app/r4_backend.py`, endpoint `/api/itinerario/recalcular`

```python
# 1. Convert graph to adjacency list
# 2. Run Dijkstra from origin (ignoring blocked routes)
# 3. Find furthest reachable airport within budget
# 4. Return path to that airport
```

### New Route Drawn in Green
**File**: `Frontend/static/main.js`, function `resaltarNuevaRuta()`

```javascript
// 1. Receive new route from server: ["BOG", "CLO", "LIM"]
// 2. Draw thick green line connecting airports
// 3. Show in info message
```

## Modify Flight Duration

**Current**: 10 seconds (for easy demo)

To change:
```javascript
// Frontend/static/main.js, line ~20
const DURACION_SIMULACION_MS = 10000  // milliseconds

// Change to:
const DURACION_SIMULACION_MS = 30000  // 30 seconds
```

## Modify Polling Interval

**Current**: Check every 500ms if flight is interrupted

To change:
```javascript
// Frontend/static/main.js, line ~21
const POLLING_INTERVALO_MS = 500  // milliseconds

// Change to:
const POLLING_INTERVALO_MS = 1000  // Check every 1 second
```

## Troubleshooting

### "Graph not loaded"
- Check that `Backend/data/grafo.json` exists
- Verify JSON is valid (use jsonlint.com)
- Check console for error message

### Aircraft doesn't move
- Ensure origin and destination are in graph
- Use 3-letter IATA codes (all uppercase)
- Check browser console (F12) for errors

### Blocking doesn't interrupt
- Flight must be mid-animation (not starting/ending)
- Frontend polls every 500ms, so there's a slight delay
- Wait 1 second after starting flight before blocking

### Port 5000 already in use
```bash
# Use different port:
# Edit Backend/flask_app.py, change:
app.run(host='127.0.0.1', port=5001)
```

## File Locations

| File | What | Size |
|------|------|------|
| `Backend/app/r4_backend.py` | 6 REST endpoints | 400 lines |
| `Backend/app/r4_dijkstra.py` | Dijkstra algorithm | 150 lines |
| `Backend/flask_app.py` | Flask setup | 70 lines |
| `Frontend/templates/index.html` | Canvas & UI | 300 lines |
| `Frontend/static/main.js` | Simulation logic | 600 lines |

## Next: What to Do After Setup

1. **Test each endpoint** with curl (see above)
2. **Walk through the code** - start with `iniciarVuelo()` in main.js
3. **Interrupt a flight** - see the full cycle
4. **Modify colors** - try changing UI colors in main.js
5. **Add routes** - add more airports to grafo.json and see them on canvas
6. **Explain to professor** - walk through code, show how Dijkstra works

## Contact Info

If something doesn't work:
1. Check `R4_README.md` for detailed explanation
2. Look at browser console (F12) for JavaScript errors
3. Check terminal for Python errors
4. Test endpoints with curl first
5. Verify grafo.json has correct format

---

**Remember**: This code is designed to be **simple and easy to explain**. Every function does one thing. Every endpoint is straightforward. Perfect for sustentation.
