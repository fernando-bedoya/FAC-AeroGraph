# FastAPI Architecture Refactoring

## Changes Made

### ✅ New Files Created

1. **`app/config.py`** - Configuration Management
   - `AppConfig` class handles graph loading and state
   - `app_state` singleton for global app state
   - Separates configuration from API logic

2. **`run.py`** - Application Entry Point
   - Single responsibility: starts uvicorn server
   - Use: `python run.py`

### 📝 Files Modified

1. **`main.py`** - Simplified FastAPI App Definition
   - Now only creates the FastAPI app
   - Added `create_app()` factory function
   - No server startup logic

2. **`app/api.py`** - Updated Imports
   - Changed: `from .state import app_state` → `from .config import app_state`
   - Everything else remains the same

### ❌ Files to Remove

- **`flask_app.py`** - No longer needed (Flask removed in favor of FastAPI)
- **`app/state.py`** - Replaced by `app/config.py`

## Architecture Overview

```
run.py (entry point: python run.py)
  └─→ uvicorn starts main:app
        └─→ main.py (creates FastAPI app)
              ├─→ main:create_app()
              ├─→ CORSMiddleware
              └─→ app/api.py (routes)
                    └─→ app/config.py (app_state)
                          ├─→ graph
                          ├─→ aircraft_cfg
                          ├─→ rules
                          └─→ dynamic_sessions
```

## Single Responsibility Principle

| File | Responsibility |
|------|-----------------|
| `run.py` | Start server |
| `main.py` | Create app + configure middleware |
| `app/config.py` | Manage state + load graph |
| `app/api.py` | Define REST API routes |

## How to Run

### Development (with auto-reload)
```bash
python run.py
```

### Production (no auto-reload)
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

All endpoints are available at: `http://localhost:8000/api/`

- `POST /api/load` - Load graph from JSON
- `GET /api/graph` - Get graph data
- `POST /api/plan/basic` - Create basic itinerary
- `POST /api/plan/best-route` - Find best route by criteria
- `POST /api/dynamic/start` - Start dynamic session
- And more...

## Notes

- No version conflict: FastAPI only (no Flask)
- No responsibility conflicts: each file has one clear purpose
- Configuration is separated from routing
- Server startup is separated from app definition
