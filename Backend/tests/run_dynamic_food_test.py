from pprint import pprint
import sys
from pathlib import Path

# Ensure Backend package is importable when running test from repo root
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.loader import load_graph_from_json
from app.dynamic.engine import start_dynamic_session, perform_dynamic_flight, get_dynamic_state


def main():
    json_path = backend_dir / "data" / "sample_network4.json"
    graph, aircraft_cfg, rules = load_graph_from_json(str(json_path))
    sessions = {}

    # Iniciar sesión dinámica en EZE con presupuesto suficiente
    state = start_dynamic_session(
        graph=graph,
        aircraft_cfg=aircraft_cfg,
        rules=rules,
        origin="EZE",
        initial_budget=5000.0,
        total_time_hours=200.0,
        sessions=sessions,
    )

    print("Session started. Current airport:", state.current_airport)

    # Realizar vuelo largo EZE -> PTY en Avion Comercial (debe activar comidas durante el vuelo)
    updated = perform_dynamic_flight(
        graph=graph,
        aircraft_cfg=aircraft_cfg,
        rules=rules,
        state=state,
        destination="PTY",
        aircraft="Avion Comercial",
    )

    print("After flight, steps:")
    pprint([s.__dict__ for s in updated.steps])

    print("Budget after:", updated.budget_usd)


if __name__ == "__main__":
    main()
