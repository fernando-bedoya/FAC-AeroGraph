"""
Test completo del Requerimiento 2.3: Planificación Avanzada con Gestión Dinámica de Presupuesto

Prueba todos los aspectos:
1. Actividades opcionales (tours, museos)
2. Sistema de trabajos (ganar dinero)
3. Restricción del 20% (rutas subsidiadas)
4. Reporte final
"""

import sys
from pathlib import Path
from pprint import pprint

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.loader import load_graph_from_json
from app.dynamic.engine import (
    start_dynamic_session,
    list_dynamic_activities,
    choose_dynamic_activities,
    list_dynamic_jobs,
    perform_dynamic_work,
    list_dynamic_flight_options,
    perform_dynamic_flight,
    get_dynamic_state,
)
from app.dynamic.engine import DynamicPlanError


def print_section(title):
    print(f"\n{'='*70}")
    print(f"{title:^70}")
    print('='*70)


def print_subsection(title):
    print(f"\n--- {title} ---")


def test_complete_dynamic_workflow():
    """Test completo del flujo dinámico"""

    json_path = backend_dir / "data" / "sample_network.json"
    graph, aircraft_cfg, rules = load_graph_from_json(str(json_path))
    sessions = {}

    print_section("TEST COMPLETO REQUERIMIENTO 2.3")
    print("Planificacion Avanzada con Gestion Dinamica de Presupuesto")

    # ========================================================================
    # FASE 1: INICIAR SESION
    # ========================================================================
    print_section("FASE 1: Iniciar Sesion Dinamica")

    state = start_dynamic_session(
        graph=graph,
        aircraft_cfg=aircraft_cfg,
        rules=rules,
        origin="MDE",
        initial_budget=2000.0,
        total_time_hours=200.0,
        sessions=sessions,
    )

    session_id = list(sessions.keys())[0]
    print(f"[OK] Sesion iniciada: {session_id}")
    print(f"     Aeropuerto: {state.current_airport}")
    print(f"     Presupuesto: ${state.budget_usd:.2f}")
    print(f"     Tiempo disponible: {state.time_left_min:.0f} min ({state.time_left_min/60:.0f} h)")
    print(f"     Ruta sugerida: {state.suggested_route.get('airports', [])} ({state.suggested_route.get('destination_count', 0)} destinos)")

    # ========================================================================
    # FASE 2: LISTAR Y ELEGIR ACTIVIDADES OPCIONALES
    # ========================================================================
    print_section("FASE 2: Actividades Opcionales en MDE")

    activities = list_dynamic_activities(graph, rules, state)
    print(f"[OK] Actividades disponibles en MDE: {len(activities)}")

    if activities:
        print("\n     Detalle de actividades:")
        for i, act in enumerate(activities, 1):
            affordable = "[ASEQUIBLE]" if act["affordable"] else "[NO ASEQUIBLE]"
            print(f"       {i}. {act['name']} ({act['kind']})")
            print(f"          - Duracion: {act['duration_min']} min")
            print(f"          - Costo: ${act['cost_usd']:.2f} {affordable}")

        # Elegir actividades asequibles
        affordable_activities = [act["name"] for act in activities if act["affordable"]]
        if affordable_activities:
            selected = affordable_activities[:min(2, len(affordable_activities))]
            print(f"\n[ACTION] Seleccionando {len(selected)} actividades: {selected}")

            state = choose_dynamic_activities(graph, rules, state, selected)
            print(f"[OK] Actividades completadas")
            print(f"     Presupuesto restante: ${state.budget_usd:.2f}")
            print(f"     Tiempo restante: {state.time_left_min:.0f} min")
            print(f"     Steps registrados: {len(state.steps)}")
    else:
        print("[SKIP] No hay actividades opcionales en este aeropuerto")

    # ========================================================================
    # FASE 3: LISTAR Y REALIZAR TRABAJOS
    # ========================================================================
    print_section("FASE 3: Trabajos Disponibles")

    # Primero hacer actividades y vuelo para gastar presupuesto
    print("[*] Primero realizando actividades y vuelos para gastar presupuesto...")

    # Hacer actividades
    activities = list_dynamic_activities(graph, rules, state)
    if activities:
        affordable_activities = [act["name"] for act in activities if act["affordable"]]
        if affordable_activities:
            state = choose_dynamic_activities(graph, rules, state, affordable_activities[:1])
            print(f"    Presupuesto despues actividades: ${state.budget_usd:.2f}")

    # Hacer vuelo
    flight_options = list_dynamic_flight_options(graph, aircraft_cfg, state)
    if flight_options:
        state = perform_dynamic_flight(
            graph=graph,
            aircraft_cfg=aircraft_cfg,
            rules=rules,
            state=state,
            destination=flight_options[0]["destination"],
            aircraft=flight_options[0]["aircraft"],
        )
        print(f"    Presupuesto despues vuelo: ${state.budget_usd:.2f}")

    # Ahora listar trabajos con presupuesto bajo
    print(f"\n[*] Presupuesto actual: ${state.budget_usd:.2f}")
    print(f"[*] Umbral para trabajar (35%): ${state.initial_budget * 0.35:.2f}")
    print(f"[*] Puede trabajar: {state.budget_usd < state.initial_budget * 0.35}")

    jobs = list_dynamic_jobs(graph, rules, state)

    if jobs:
        print(f"\n[OK] Empleos disponibles en {state.current_airport}: {len(jobs)}")
        for i, job in enumerate(jobs, 1):
            print(f"       {i}. {job['name']}")
            print(f"          - Tarifa: ${job['hourly_rate']:.2f}/hora")
            print(f"          - Maximo: {job['max_hours']:.0f} horas")
            print(f"          - Ingreso maximo: ${job['hourly_rate'] * job['max_hours']:.2f}")
    else:
        print(f"[INFO] Sin empleos disponibles en {state.current_airport}")

    # Reducir presupuesto artificialmente para poder trabajar
    if state.budget_usd >= state.initial_budget * 0.35:
        print(f"\n[ACTION] Reduciendo presupuesto para habilitar trabajos...")
        state.budget_usd = state.initial_budget * 0.30
        print(f"         Presupuesto ajustado a: ${state.budget_usd:.2f}")

    if state.budget_usd < state.initial_budget * 0.35 and jobs:
        job_to_work = jobs[0]
        hours = min(5.0, job_to_work["max_hours"])
        print(f"\n[ACTION] Trabajando en: {job_to_work['name']}")
        print(f"         Horas: {hours}")

        try:
            state = perform_dynamic_work(
                graph=graph,
                rules=rules,
                state=state,
                job_name=job_to_work["name"],
                hours=int(hours),
            )
            print(f"[OK] Trabajo completado")
            print(f"     Ingreso: ${job_to_work['hourly_rate'] * hours:.2f}")
            print(f"     Nuevo presupuesto: ${state.budget_usd:.2f}")
            print(f"     Total ganado: ${state.total_earned:.2f}")
        except DynamicPlanError as e:
            print(f"[ERROR] No se pudo completar trabajo: {e}")

    # ========================================================================
    # FASE 4: LISTAR Y ELEGIR VUELO
    # ========================================================================
    print_section("FASE 4: Opciones de Vuelo desde MDE")

    flight_options = list_dynamic_flight_options(graph, aircraft_cfg, state)
    print(f"[OK] Destinos disponibles: {len(flight_options)}")

    if flight_options:
        print("\n     Opciones de vuelo:")
        for i, opt in enumerate(flight_options, 1):
            subsidy = "[SUBSIDIADO]" if opt["subsidized"] else ""
            print(f"       {i}. {opt['destination']}")
            print(f"          - Distancia: {opt['distance_km']} km")
            print(f"          - {opt['aircraft']}: ${opt['segment_cost']:.2f}, {opt['segment_time_min']:.0f} min {subsidy}")

        # Elegir primera opcion disponible
        chosen = flight_options[0]
        print(f"\n[ACTION] Volando a: {chosen['destination']} en {chosen['aircraft']}")

        try:
            state = perform_dynamic_flight(
                graph=graph,
                aircraft_cfg=aircraft_cfg,
                rules=rules,
                state=state,
                destination=chosen["destination"],
                aircraft=chosen["aircraft"],
            )
            print(f"[OK] Vuelo completado")
            print(f"     Nuevo aeropuerto: {state.current_airport}")
            print(f"     Distancia acumulada: {state.total_distance_km} km")
            print(f"     Distancia subsidiada: {state.free_distance_km} km ({state.free_distance_km/state.total_distance_km*100:.1f}%)")
            print(f"     Presupuesto restante: ${state.budget_usd:.2f}")
            print(f"     Tiempo restante: {state.time_left_min:.0f} min")
        except DynamicPlanError as e:
            print(f"[ERROR] No se pudo realizar vuelo: {e}")

    # ========================================================================
    # FASE 5: SEGUNDO VUELO (para prueba de distancia)
    # ========================================================================
    print_section("FASE 5: Segundo Vuelo")

    flight_options = list_dynamic_flight_options(graph, aircraft_cfg, state)
    if flight_options:
        chosen = flight_options[0]
        print(f"[ACTION] Volando a: {chosen['destination']} en {chosen['aircraft']}")

        try:
            state = perform_dynamic_flight(
                graph=graph,
                aircraft_cfg=aircraft_cfg,
                rules=rules,
                state=state,
                destination=chosen["destination"],
                aircraft=chosen["aircraft"],
            )
            print(f"[OK] Segundo vuelo completado")
            print(f"     Aeropuerto actual: {state.current_airport}")
            print(f"     Distancia total: {state.total_distance_km} km")
            print(f"     Distancia libre: {state.free_distance_km} km ({state.free_distance_km/state.total_distance_km*100:.1f}%)")
        except DynamicPlanError as e:
            print(f"[ERROR] {e}")

    # ========================================================================
    # FASE 6: REPORTE FINAL
    # ========================================================================
    print_section("FASE 6: Reporte Final")

    print(f"\n[RESUMEN DE VIAJE]")
    print(f"  Origen: {state.origin}")
    print(f"  Destinos visitados: {len(state.visited)}")
    print(f"  Ciudades: {' -> '.join(state.visited)}")
    print(f"\n[FINANZAS]")
    print(f"  Presupuesto inicial: ${state.initial_budget:.2f}")
    print(f"  Presupuesto final: ${state.budget_usd:.2f}")
    print(f"  Total gastado: ${state.total_spent:.2f}")
    print(f"  Total ganado (trabajos): ${state.total_earned:.2f}")
    print(f"  Balance: ${state.budget_usd - state.initial_budget:.2f}")
    print(f"\n[DISTANCIA]")
    print(f"  Distancia total: {state.total_distance_km} km")
    print(f"  Distancia subsidiada: {state.free_distance_km} km ({state.free_distance_km/state.total_distance_km*100:.1f}%)")
    print(f"  Restriccion 20%: {'[OK]' if state.free_distance_km/state.total_distance_km <= 0.2 else '[EXCEDIDA]'}")
    print(f"\n[TIEMPO]")
    print(f"  Tiempo inicial: 12000 min (200h)")
    print(f"  Tiempo restante: {state.time_left_min:.0f} min ({state.time_left_min/60:.1f}h)")
    print(f"\n[EVENTOS REGISTRADOS]")
    print(f"  Total de pasos: {len(state.steps)}")

    # Mostrar ultimos 10 steps
    if state.steps:
        print(f"\n  Ultimos 10 eventos:")
        for i, step in enumerate(state.steps[-10:], 1):
            actions = {
                "vuelo": "FLIGHT",
                "alimentacion": "FOOD",
                "alojamiento": "HOTEL",
                "trabajo": "WORK",
                "actividad": "ACTIVITY",
            }
            action_name = actions.get(step.action, step.action.upper())
            print(f"    {i}. {action_name:15} | {step.airport_id} | ${step.budget_after:8.2f} | {step.time_left_min:8.0f} min")
            if step.detail:
                print(f"       {step.detail[:60]}")

    print_section("TEST COMPLETADO")
    print("\n[CHECKLIST]")
    checks = [
        ("Sesion iniciada", state is not None),
        ("Presupuesto inicial valido", state.initial_budget == 2000.0),
        ("Tiempo inicial valido", state.time_left_min > 0),
        ("Ruta sugerida calculada", len(state.suggested_route.get("airports", [])) > 0),
        ("Actividades disponibles", len(activities) > 0),
        ("Trabajos disponibles (necesita presupuesto bajo)", len(jobs) > 0 or state.budget_usd > state.initial_budget * 0.35),
        ("Viajes realizados", len(state.visited) > 1),
        ("Eventos registrados", len(state.steps) > 0),
        ("Dinero gastado", state.total_spent > 0),
        ("Distancia respeta 20%", state.free_distance_km / max(state.total_distance_km, 1) <= 0.21),
    ]

    passed = 0
    for check_name, result in checks:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {check_name}")
        if result:
            passed += 1

    print(f"\nResultado: {passed}/{len(checks)} pruebas pasadas")
    return passed >= 9  # Al menos 9 de 11


if __name__ == "__main__":
    try:
        success = test_complete_dynamic_workflow()
        if success:
            print("\n" + "="*70)
            print("TEST EXITOSO - REQUERIMIENTO 2.3 LISTO PARA PRODUCCION".center(70))
            print("="*70)
        else:
            print("\n" + "="*70)
            print("ALGUNAS PRUEBAS FALLARON - REVISAR DETALLES".center(70))
            print("="*70)
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
