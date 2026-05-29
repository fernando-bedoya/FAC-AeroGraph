import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.loader import load_graph_from_json
from app.dynamic.engine import start_dynamic_session, perform_dynamic_flight
from app.dynamic.engine import DynamicPlanError


def test_20_percent_restriction():
    """
    Verificar que se rechace un vuelo cuando la distancia subsidiada
    excederia el 20% de la distancia total.
    """
    json_path = backend_dir / "data" / "sample_network4.json"
    graph, aircraft_cfg, rules = load_graph_from_json(str(json_path))
    sessions = {}

    # Comenzar desde MDE que tiene rutas subsidiadas
    state = start_dynamic_session(
        graph=graph,
        aircraft_cfg=aircraft_cfg,
        rules=rules,
        origin="MDE",
        initial_budget=10000.0,
        total_time_hours=300.0,
        sessions=sessions,
    )

    print("=== TEST: Restriccion del 20% para rutas subsidiadas ===")
    print(f"Initial airport: {state.current_airport}")
    print(f"Initial budget: {state.budget_usd} USD")
    print(f"Total distance: {state.total_distance_km} km")
    print(f"Free distance: {state.free_distance_km} km")
    print()

    # Buscar ruta subsidiada desde el aeropuerto actual
    current = state.current_airport
    subsidized_from_current = None

    for route in graph.get_outgoing_routes(current):
        if route.base_cost == 0:
            subsidized_from_current = route
            break

    if subsidized_from_current:
        print(f"[OK] Ruta subsidiada encontrada: {current} -> {subsidized_from_current.destination}")
        print(f"     Distancia: {subsidized_from_current.distance_km} km")
    else:
        print("[SKIP] No hay ruta subsidiada desde el aeropuerto inicial")
        print("       Buscando rutas subsidiadas en el grafo...")
        subsidized_routes = [r for r in graph.get_all_routes() if r.base_cost == 0]
        if subsidized_routes:
            print(f"       Encontradas {len(subsidized_routes)} rutas subsidiadas")
            for r in subsidized_routes[:3]:
                print(f"         - {r.origin} -> {r.destination}: {r.distance_km} km")
        return None

    # Volar a la ruta subsidiada
    print("\n[1] Volando a ruta subsidiada...")
    try:
        state = perform_dynamic_flight(
            graph=graph,
            aircraft_cfg=aircraft_cfg,
            rules=rules,
            state=state,
            destination=subsidized_from_current.destination,
            aircraft="Avion Comercial",
        )
        print(f"[OK] Vuelo completado")
        print(f"     Current airport: {state.current_airport}")
        print(f"     Total distance: {state.total_distance_km} km")
        print(f"     Free distance: {state.free_distance_km} km")
        print(f"     Free %: {(state.free_distance_km/state.total_distance_km*100):.1f}%")
    except DynamicPlanError as e:
        print(f"[ERROR] No se pudo realizar el vuelo: {e}")
        return False

    # Volar a ruta pagada para acumular distancia
    print("\n[2] Volando a ruta pagada para acumular distancia...")
    current = state.current_airport
    paid_route = None
    for route in graph.get_outgoing_routes(current):
        if route.base_cost != 0:
            paid_route = route
            break

    if paid_route:
        try:
            state = perform_dynamic_flight(
                graph=graph,
                aircraft_cfg=aircraft_cfg,
                rules=rules,
                state=state,
                destination=paid_route.destination,
                aircraft="Avion Comercial",
            )
            print(f"[OK] Vuelo pagado completado: {current} -> {paid_route.destination}")
            print(f"     Total distance: {state.total_distance_km} km")
            print(f"     Free distance: {state.free_distance_km} km")
            print(f"     Free %: {(state.free_distance_km/state.total_distance_km*100):.1f}%")
        except DynamicPlanError as e:
            print(f"[ERROR] No se pudo realizar el vuelo: {e}")
            return False
    else:
        print("[SKIP] No hay ruta pagada desde el aeropuerto actual")
        return None

    # Intentar otra ruta subsidiada
    print("\n[3] Intentando ruta subsidiada que podria exceder 20%...")
    current = state.current_airport
    for route in graph.get_outgoing_routes(current):
        if route.base_cost == 0:
            projected_total = state.total_distance_km + route.distance_km
            projected_free = state.free_distance_km + route.distance_km
            max_free = projected_total * 0.2

            print(f"     Route: {current} -> {route.destination}")
            print(f"     Distance: {route.distance_km} km")
            print(f"     Projected total: {projected_total} km")
            print(f"     Projected free: {projected_free} km")
            print(f"     Max allowed (20%): {max_free:.0f} km")
            print(f"     Would exceed: {projected_free > max_free}")

            if projected_free > max_free:
                print(f"\n     Intentando volar (deberia ser rechazado)...")
                # Usar la aeronave disponible en la ruta
                available_aircraft = route.aircraft_types[0] if route.aircraft_types else "Avion Comercial"
                try:
                    state = perform_dynamic_flight(
                        graph=graph,
                        aircraft_cfg=aircraft_cfg,
                        rules=rules,
                        state=state,
                        destination=route.destination,
                        aircraft=available_aircraft,
                    )
                    print(f"[FAIL] El vuelo fue permitido cuando deberia ser rechazado")
                    return False
                except DynamicPlanError as e:
                    print(f"[OK] Vuelo rechazado correctamente")
                    print(f"     Error: {e}")
                    return True
            else:
                print(f"     (Esta ruta no excederia 20%, continuando...)")
                break

    print("\n[INCONCLUSIVE] No se pudo determinar resultado de prueba")
    return None


if __name__ == "__main__":
    result = test_20_percent_restriction()
    if result is True:
        print("\n=== PRUEBA EXITOSA ===")
    elif result is False:
        print("\n=== PRUEBA FALLIDA ===")
    else:
        print("\n=== PRUEBA INCONCLUSA (faltan rutas para completar) ===")
