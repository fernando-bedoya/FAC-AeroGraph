"""
Tests para el módulo de interrupción de rutas (R2.4).

Cubre los escenarios:
1. Interrupción con viajero en tránsito → redirección exitosa
2. Interrupción sin viajero en tránsito → solo bloqueo
3. Interrupción de ruta inexistente → error controlado
4. Recalculación post-interrupción genera alternativas válidas
5. Campos in_transit se activan/desactivan correctamente con perform_dynamic_flight
"""

import pytest

from app.dynamic.interruption import (
    clear_transit,
    handle_interruption,
    mark_in_transit,
)
from app.dynamic.models import DynamicState
from app.graph import Graph
from app.models import AircraftConfig, Airport, Route


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_airport(airport_id: str, name: str = "", is_hub: bool = True) -> Airport:
    """Crea un aeropuerto de prueba con valores mínimos."""
    return Airport(
        id=airport_id,
        name=name or airport_id,
        city=airport_id,
        country="CO",
        timezone="UTC-5",
        is_hub=is_hub,
        lodging_cost=30.0,
        food_cost=10.0,
        activities=[],
        jobs=[],
    )


def _make_route(
    origin: str,
    destination: str,
    distance_km: float = 500.0,
    blocked: bool = False,
) -> Route:
    """Crea una ruta de prueba."""
    return Route(
        origin=origin,
        destination=destination,
        distance_km=distance_km,
        aircraft_types=["Avion Comercial"],
        base_cost=100.0,
        min_stay_min=30,
        blocked=blocked,
    )


def _make_graph() -> Graph:
    """
    Crea un grafo con 4 aeropuertos y rutas:
        A → B → C
        A → D (alternativa)
        B → D (alternativa desde B)
    """
    graph = Graph()
    for aid in ["A", "B", "C", "D"]:
        graph.add_airport(_make_airport(aid))

    graph.add_route(_make_route("A", "B", 500.0))
    graph.add_route(_make_route("B", "C", 300.0))
    graph.add_route(_make_route("A", "D", 400.0))
    graph.add_route(_make_route("B", "D", 350.0))

    return graph


def _make_aircraft_cfg() -> dict:
    """Configuración de aeronave de prueba."""
    return {
        "Avion Comercial": AircraftConfig(
            cost_per_km=0.5,
            time_per_km=0.1,
        ),
    }


def _make_state(
    current_airport: str = "B",
    in_transit: bool = False,
    transit_from: str = None,
    transit_to: str = None,
    transit_aircraft: str = None,
    visited: list = None,
) -> DynamicState:
    """Crea un DynamicState de prueba."""
    return DynamicState(
        session_id="test-session-001",
        origin="A",
        current_airport=current_airport,
        initial_budget=1000.0,
        budget_usd=800.0,
        time_left_min=600.0,
        total_spent=200.0,
        total_earned=0.0,
        visited=visited or ["A", "B"],
        steps=[],
        in_transit=in_transit,
        transit_from=transit_from,
        transit_to=transit_to,
        transit_aircraft=transit_aircraft,
    )


# ---------------------------------------------------------------------------
# Tests: mark_in_transit / clear_transit
# ---------------------------------------------------------------------------

class TestTransitStateManagement:
    """Tests para las funciones de gestión del estado de tránsito."""

    def test_mark_in_transit_sets_fields(self):
        state = _make_state()
        assert state.in_transit is False

        mark_in_transit(state, "B", "C", "Avion Comercial")

        assert state.in_transit is True
        assert state.transit_from == "B"
        assert state.transit_to == "C"
        assert state.transit_aircraft == "Avion Comercial"

    def test_clear_transit_resets_fields(self):
        state = _make_state(
            in_transit=True,
            transit_from="B",
            transit_to="C",
            transit_aircraft="Avion Comercial",
        )

        clear_transit(state)

        assert state.in_transit is False
        assert state.transit_from is None
        assert state.transit_to is None
        assert state.transit_aircraft is None

    def test_clear_transit_on_already_clear_state(self):
        """Limpiar un estado que ya está limpio no causa errores."""
        state = _make_state()
        clear_transit(state)  # No debe lanzar excepción

        assert state.in_transit is False
        assert state.transit_from is None


# ---------------------------------------------------------------------------
# Tests: handle_interruption
# ---------------------------------------------------------------------------

class TestHandleInterruption:
    """Tests para la función orquestadora de interrupción."""

    def test_interruption_with_traveler_in_transit_redirects(self):
        """
        Escenario: Viajero volando B→C, se bloquea B→C.
        Resultado: Viajero redirigido a B, ruta bloqueada.
        """
        graph = _make_graph()
        cfg = _make_aircraft_cfg()
        state = _make_state(
            current_airport="B",
            in_transit=True,
            transit_from="B",
            transit_to="C",
            transit_aircraft="Avion Comercial",
        )

        result = handle_interruption(graph, cfg, state, "B", "C")

        # Verificar que fue redirigido
        assert result["was_redirected"] is True
        assert result["redirected_to"] == "B"

        # Verificar que la ruta fue bloqueada
        assert result["blocked_route"] == {"from": "B", "to": "C"}
        route_bc = graph.get_route("B", "C")
        assert route_bc.blocked is True

        # Verificar que el estado fue actualizado
        assert state.current_airport == "B"
        assert state.in_transit is False
        assert state.transit_from is None

        # Verificar que se registró paso de redirección
        redirect_steps = [
            s for s in state.steps
            if s.action == "redireccion_emergencia"
        ]
        assert len(redirect_steps) == 1
        assert "B" in redirect_steps[0].detail
        assert "C" in redirect_steps[0].detail

    def test_interruption_without_traveler_in_transit(self):
        """
        Escenario: Viajero en B (en tierra), se bloquea B→C.
        Resultado: Ruta bloqueada, viajero NO redirigido.
        """
        graph = _make_graph()
        cfg = _make_aircraft_cfg()
        state = _make_state(current_airport="B", in_transit=False)

        result = handle_interruption(graph, cfg, state, "B", "C")

        assert result["was_redirected"] is False
        assert result["redirected_to"] is None

        # Verificar que se registró paso informativo
        block_steps = [
            s for s in state.steps if s.action == "ruta_bloqueada"
        ]
        assert len(block_steps) == 1

        # Viajero sigue en B
        assert state.current_airport == "B"

    def test_interruption_traveler_on_different_route(self):
        """
        Escenario: Viajero volando A→B, se bloquea B→C.
        Resultado: Ruta B→C bloqueada, viajero NO redirigido (está en otro tramo).
        """
        graph = _make_graph()
        cfg = _make_aircraft_cfg()
        state = _make_state(
            current_airport="A",
            in_transit=True,
            transit_from="A",
            transit_to="B",
            transit_aircraft="Avion Comercial",
            visited=["A"],
        )

        result = handle_interruption(graph, cfg, state, "B", "C")

        assert result["was_redirected"] is False
        # El viajero sigue en tránsito A→B
        assert state.in_transit is True
        assert state.transit_from == "A"
        assert state.transit_to == "B"

    def test_interruption_nonexistent_route_raises(self):
        """
        Escenario: Se intenta bloquear una ruta que no existe.
        Resultado: ValueError.
        """
        graph = _make_graph()
        cfg = _make_aircraft_cfg()
        state = _make_state()

        with pytest.raises(ValueError, match="No se encontró la ruta"):
            handle_interruption(graph, cfg, state, "A", "Z")

    def test_interruption_recalculates_flight_options(self):
        """
        Escenario: Viajero en B, se bloquea B→C.
        Resultado: Las opciones recalculadas NO incluyen B→C pero SÍ incluyen B→D.
        """
        graph = _make_graph()
        cfg = _make_aircraft_cfg()
        state = _make_state(
            current_airport="B",
            in_transit=False,
            visited=["A", "B"],  # A y B ya visitados
        )

        result = handle_interruption(graph, cfg, state, "B", "C")

        options = result["new_flight_options"]
        destinations = [opt["destination"] for opt in options]

        # B→C bloqueada, no debe aparecer
        assert "C" not in destinations or all(
            opt.get("blocked") for opt in options if opt["destination"] == "C"
        )
        # B→D debe estar disponible (D no visitado)
        assert "D" in destinations

    def test_interruption_recalculates_suggested_route(self):
        """
        Verifica que handle_interruption actualiza la ruta sugerida.
        """
        graph = _make_graph()
        cfg = _make_aircraft_cfg()
        state = _make_state(current_airport="B", in_transit=False)

        result = handle_interruption(graph, cfg, state, "B", "C")

        assert "suggested_route" in result
        assert "airports" in result["suggested_route"]
        # La ruta sugerida debe empezar desde B (posición actual)
        assert result["suggested_route"]["airports"][0] == "B"


# ---------------------------------------------------------------------------
# Tests: integración con perform_dynamic_flight
# ---------------------------------------------------------------------------

class TestFlightTransitIntegration:
    """
    Verifica que perform_dynamic_flight activa/desactiva
    correctamente los campos de tránsito.
    """

    def test_perform_flight_marks_and_clears_transit(self):
        """
        Tras completar un vuelo, in_transit debe ser False
        (se marcó durante el vuelo y se limpió al llegar).
        """
        from app.dynamic.engine import perform_dynamic_flight

        graph = _make_graph()
        cfg = _make_aircraft_cfg()
        rules = {"food_interval_h": 8, "lodging_interval_h": 20, "budget_trigger_percent": 35}

        state = _make_state(
            current_airport="A",
            visited=["A"],
            in_transit=False,
        )
        state.budget_usd = 1000.0
        state.time_left_min = 600.0

        updated = perform_dynamic_flight(
            graph, cfg, rules, state, "B", "Avion Comercial"
        )

        # Después de completar el vuelo, tránsito debe estar limpio
        assert updated.in_transit is False
        assert updated.transit_from is None
        assert updated.transit_to is None
        assert updated.transit_aircraft is None
        assert updated.current_airport == "B"
