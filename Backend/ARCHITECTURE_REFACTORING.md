# FastAPI Refactoring: Resolving Version & Responsibility Conflicts

## Respuesta a tu pregunta

**"¿Hay un conflicto de versiones y single responsibility entre flask_app.py y main.py?"**

### ✅ SÍ, había conflicto (ahora resuelto)

#### Conflicto 1: Dos Frameworks
- `main.py` → FastAPI (moderno, asincrónico)
- `flask_app.py` → Flask (sincrónico, legacy)
- **Problema:** App con dos frameworks = confusión, duplicación de código

#### Conflicto 2: Responsabilidad única violada
`flask_app.py` violaba SRP haciendo 5 cosas:
```python
1. Define la app Flask
2. Carga el grafo desde JSON
3. Registra blueprints
4. Sirve frontend estático
5. Inicia el servidor (app.run())
```

#### Conflicto 3: Entrada poco clara
- ¿Ejecuto `python flask_app.py`? (puerto 5000, Flask)
- ¿Ejecuto `uvicorn main:app`? (puerto 8000, FastAPI)
- ¿Cuál es la "versión correcta"?

---

## Solución: Arquitectura FastAPI Limpia

### 📁 Nueva Estructura

```
Backend/
├── run.py                 ← Entry point (python run.py)
├── main.py               ← App factory (crear app FastAPI)
├── app/
│   ├── __init__.py
│   ├── config.py         ← Config management (NUEVO)
│   ├── api.py            ← Routes
│   ├── models.py
│   ├── loader.py
│   ├── graph.py
│   └── ... (otros)
├── data/
│   └── grafo.json
└── requirements.txt
```

### 📝 Cambios Específicos

#### 1. `run.py` (NUEVO)
**Responsabilidad única:** Iniciar servidor
```python
import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```
- Una sola función: arrancar uvicorn
- Fácil de entender: `python run.py`

#### 2. `main.py` (REFACTORIZADO)
**Responsabilidad única:** Crear y configurar app FastAPI
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import router

def create_app() -> FastAPI:
    app = FastAPI(title="SkyRoute Planner API", version="1.0.0")
    app.add_middleware(CORSMiddleware, ...)
    app.include_router(router, prefix="/api")
    return app

app = create_app()  # ← La app que uvicorn ejecuta
```
- **Antes:** Definía la app + middleware + routes todo junto
- **Ahora:** Solo crea y configura. Las routes vienen de `api.py`
- Factory pattern = fácil de testear

#### 3. `app/config.py` (NUEVO)
**Responsabilidad única:** Gestionar configuración global
```python
class AppConfig:
    def __init__(self):
        self.graph = None
        self.aircraft_cfg = {}
        self.rules = {}
        self.dynamic_sessions = {}
    
    def load_graph(self, file_path: str):
        """Cargar grafo desde JSON"""
        ...

app_state = AppConfig()  # ← Singleton global
```
- **Antes:** `flask_app.py` cargaba el grafo + lo guardaba en variable global
- **Ahora:** `AppConfig` clase dedica a esto
- Los routes acceden a `app_state` (igual que antes, pero más limpio)

#### 4. `app/api.py` (ACTUALIZADO)
```python
# ANTES
from .state import app_state

# AHORA
from .config import app_state
```
- Todo el resto es igual
- Solo cambió la importación

---

## Responsabilidades Finales

| Archivo | Qué hace | Responsabilidad |
|---------|----------|-----------------|
| `run.py` | Inicia uvicorn | Arrancar servidor |
| `main.py` | Crea FastAPI + middleware | Configurar app |
| `app/config.py` | Maneja graph, aircraft, rules | Gestionar estado |
| `app/api.py` | Define 10+ endpoints | Definir rutas |
| `app/loader.py` | Parsea JSON → objetos | Cargar datos |
| `app/graph.py` | Lógica de grafo (Dijkstra, etc) | Algoritmos |

✅ Cada archivo: **UNA responsabilidad**

---

## Cómo Usar

### Desarrollo (con auto-reload)
```bash
cd Backend
python run.py
# Abre: http://localhost:8000/api/health
```

### Producción
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Probar endpoints
```bash
# Health check
curl http://localhost:8000/api/health

# Cargar grafo
curl -X POST http://localhost:8000/api/load \
  -H "Content-Type: application/json" \
  -d '{"file_path": "data/grafo.json"}'

# Ver grafo
curl http://localhost:8000/api/graph
```

---

## Archivos a Eliminar

⚠️ **Opcional:** Puedes mantener `flask_app.py` si lo necesitas, pero ya no se usa.

```bash
# (Opcional) Eliminar
rm Backend/flask_app.py
rm Backend/app/state.py
```

---

## Resumen de Beneficios

| Problema | Solución |
|----------|----------|
| Dos frameworks (FastAPI + Flask) | ✅ Solo FastAPI |
| Responsabilidad única violada | ✅ Cada archivo: una tarea |
| Confusión sobre cómo iniciar | ✅ Claro: `python run.py` |
| `flask_app.py` hace 5 cosas | ✅ Distribuido entre 4 archivos |
| Estado global en `flask_app.py` | ✅ En `app/config.py` |
| Startup logic en `main.py` | ✅ Separado en `run.py` |

---

## FAQ

**P: ¿Por qué `run.py` en lugar de `main.py`?**
A: `main.py` es el módulo que `uvicorn` importa. `run.py` es el script de inicio que el usuario ejecuta. Separados = claro.

**P: ¿Qué pasa con el frontend?**
A: Si quieres servir HTML estático, agrega a `main.py`:
```python
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="../Frontend/static"), name="static")
```

**P: ¿Puedo usar el viejo `flask_app.py`?**
A: No. Pero puedes mantenerlo en git por historial. No afecta nada.

**P: ¿Qué pasa con `app/state.py`?**
A: Reemplazado por `app/config.py`. Puedes eliminarlo.
