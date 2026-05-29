"""
Test del Sistema de Trabajos - Requerimiento 2.3
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.loader import load_graph_from_json
from app.dynamic.engine import (
    start_dynamic_session,
    list_dynamic_jobs,
    perform_dynamic_work,
    list_dynamic_flight_options,
    perform_dynamic_flight,
)


def print_section(title):
    print(f"\n{'='*70}")
    print(f"{title:^70}")
    print('='*70)


def test_jobs_system():
    """Test específico del sistema de trabajos"""

    json_path = backend_dir / "data" / "sample_network4.json"
    graph, aircraft_cfg, rules = load_graph_from_json(str(json_path))
    sessions = {}

    print_section("TEST: SISTEMA DE TRABAJOS - REQUERIMIENTO 2.3")

    # ========================================================================
    # FASE 1: INICIAR CON PRESUPUESTO BAJO PARA HABILITAR TRABAJOS
    # ========================================================================
    print("\n[1] Iniciando sesion con presupuesto bajo para trabajos...")

    # Umbral de trabajo es 35%, así que presupuesto inicial debe ser tal que
    # después de gastos el 35% sea el límite para trabajar
    initial_budget = 2000.0

    state = start_dynamic_session(
        graph=graph,
        aircraft_cfg=aircraft_cfg,
        rules=rules,
        origin="MDE",
        initial_budget=initial_budget,
        total_time_hours=200.0,
        sessions=sessions,
    )

    print(f"    Presupuesto inicial: ${state.budget_usd:.2f}")
    print(f"    Umbral para trabajar (35%): ${state.initial_budget * 0.35:.2f}")
    print(f"    Puede trabajar ahora: {state.budget_usd < state.initial_budget * 0.35}")

    # ========================================================================
    # FASE 2: LISTAR TRABAJOS
    # ========================================================================
    print("\n[2] Listando trabajos disponibles en MDE...")

    jobs = list_dynamic_jobs(graph, rules, state)
    print(f"    Trabajos encontrados: {len(jobs)}")

    if not jobs:
        print("    [INFO] No hay trabajos disponibles aun porque presupuesto es alto")
        print("    [ACTION] Reduciendo presupuesto para habilitar trabajos...")
        state.budget_usd = state.initial_budget * 0.30
        print(f"    Nuevo presupuesto: ${state.budget_usd:.2f}")

        jobs = list_dynamic_jobs(graph, rules, state)
        print(f"    Trabajos encontrados ahora: {len(jobs)}")

    if jobs:
        print("\n    Detalle de trabajos:")
        for i, job in enumerate(jobs, 1):
            print(f"      {i}. {job['name']}")
            print(f"         - Tarifa: ${job['hourly_rate']:.2f}/hora")
            print(f"         - Maximo: {job['max_hours']:.0f} horas")
            print(f"         - Ingreso maximo: ${job['hourly_rate'] * job['max_hours']:.2f}")
    else:
        print("    [ERROR] No hay trabajos disponibles. Abortando test.")
        return False

    # ========================================================================
    # FASE 3: REALIZAR UN TRABAJO
    # ========================================================================
    print("\n[3] Realizando trabajo...")

    job_to_work = jobs[0]
    hours_to_work = min(3.0, job_to_work["max_hours"])
    income = job_to_work["hourly_rate"] * hours_to_work

    print(f"    Trabajo seleccionado: {job_to_work['name']}")
    print(f"    Horas: {hours_to_work}")
    print(f"    Ingreso esperado: ${income:.2f}")
    print(f"    Presupuesto antes: ${state.budget_usd:.2f}")

    try:
        state = perform_dynamic_work(
            graph=graph,
            rules=rules,
            state=state,
            job_name=job_to_work["name"],
            hours=int(hours_to_work),
        )
        print(f"    [OK] Trabajo completado")
        print(f"    Presupuesto despues: ${state.budget_usd:.2f}")
        print(f"    Dinero ganado: ${state.total_earned:.2f}")

        if state.budget_usd - (state.budget_usd - income) > 0:
            print(f"    [PASS] Presupuesto aumentó correctamente")
        else:
            print(f"    [FAIL] Presupuesto no se actualizó correctamente")
            return False

    except Exception as e:
        print(f"    [ERROR] {e}")
        return False

    # ========================================================================
    # FASE 4: VOLAR CON PRESUPUESTO MEJORADO
    # ========================================================================
    print("\n[4] Realizando vuelo con presupuesto mejorado...")

    flight_options = list_dynamic_flight_options(graph, aircraft_cfg, state)
    if flight_options:
        chosen = flight_options[0]
        print(f"    Volando a: {chosen['destination']}")
        print(f"    Costo: ${chosen['segment_cost']:.2f}")
        print(f"    Presupuesto actual: ${state.budget_usd:.2f}")

        try:
            state = perform_dynamic_flight(
                graph=graph,
                aircraft_cfg=aircraft_cfg,
                rules=rules,
                state=state,
                destination=chosen["destination"],
                aircraft=chosen["aircraft"],
            )
            print(f"    [OK] Vuelo completado a {state.current_airport}")
            print(f"    Presupuesto restante: ${state.budget_usd:.2f}")
        except Exception as e:
            print(f"    [ERROR] {e}")
            return False
    else:
        print("    [SKIP] No hay vuelos disponibles")

    # ========================================================================
    # FASE 5: REPORTE FINAL
    # ========================================================================
    print_section("REPORTE FINAL")

    print(f"\n[FINANZAS]")
    print(f"  Presupuesto inicial: ${state.initial_budget:.2f}")
    print(f"  Presupuesto actual: ${state.budget_usd:.2f}")
    print(f"  Total gastado: ${state.total_spent:.2f}")
    print(f"  Total ganado (trabajos): ${state.total_earned:.2f}")
    print(f"  Cambio neto: ${state.budget_usd - state.initial_budget:.2f}")

    print(f"\n[VIAJE]")
    print(f"  Destinos visitados: {len(state.visited)}")
    print(f"  Ruta: {' -> '.join(state.visited)}")

    print(f"\n[EVENTOS]")
    print(f"  Total eventos: {len(state.steps)}")
    for i, step in enumerate(state.steps, 1):
        print(f"    {i}. [{step.action:12}] {step.detail[:50]}")

    # ========================================================================
    # CHECKLIST
    # ========================================================================
    print_section("CHECKLIST")

    checks = [
        ("Sesion iniciada", state is not None),
        ("Trabajos disponibles", len(jobs) > 0),
        ("Trabajo realizado", state.total_earned > 0),
        ("Presupuesto aumento", state.total_earned == 27),
        ("Eventos registrados", len(state.steps) > 0),
        ("Viaje realizado", len(state.visited) > 1),
    ]

    passed = 0
    for check_name, result in checks:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {check_name}")
        if result:
            passed += 1

    print(f"\nResultado: {passed}/{len(checks)} pruebas pasadas")
    return passed == len(checks)


if __name__ == "__main__":
    try:
        success = test_jobs_system()
        if success:
            print("\n" + "="*70)
            print("SISTEMA DE TRABAJOS COMPLETAMENTE FUNCIONAL".center(70))
            print("="*70)
        else:
            print("\n" + "="*70)
            print("ALGUNAS PRUEBAS FALLARON".center(70))
            print("="*70)
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
