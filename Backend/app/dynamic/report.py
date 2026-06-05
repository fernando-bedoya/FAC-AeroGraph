import json
import csv
import io
from typing import Any, Dict, List

from ..graph import Graph
from .models import DynamicState


def export_report_format(report_data: Dict[str, Any], fmt: str) -> str:
    if fmt.lower() == "json":
        return json.dumps(report_data, indent=2, ensure_ascii=False)
    elif fmt.lower() == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(["--- TOTALES ---"])
        writer.writerow(["Presupuesto Inicial", "Total Gastado", "Total Ganado", "Saldo Final", "Tiempo Total (min)"])
        t = report_data.get("totals", {})
        writer.writerow([t.get("initial_budget"), t.get("total_spent"), t.get("total_earned"), t.get("final_budget"), t.get("total_time_spent_min")])
        writer.writerow([])
        
        writer.writerow(["--- DESTINOS ---"])
        writer.writerow(["ID", "Ciudad", "Pais", "Estadia (min)", "Costo Total"])
        for d in report_data.get("destinations", []):
            writer.writerow([d.get("id"), d.get("city"), d.get("country"), d.get("stay_min"), d.get("total_cost")])
        writer.writerow([])
        
        writer.writerow(["--- VUELOS ---"])
        writer.writerow(["Origen", "Destino", "Aeronave", "Distancia (km)", "Duracion (min)", "Costo USD"])
        for f in report_data.get("flights", []):
            writer.writerow([f.get("origin"), f.get("destination"), f.get("aircraft"), f.get("distance_km"), f.get("duration_min"), f.get("cost_usd")])
        writer.writerow([])
        
        writer.writerow(["--- ACTIVIDADES ---"])
        writer.writerow(["Aeropuerto", "Actividad", "Tipo", "Duracion (min)", "Costo USD"])
        for a in report_data.get("activities", []):
            writer.writerow([a.get("airport_id"), a.get("name"), a.get("kind"), a.get("duration_min"), a.get("cost_usd")])
        writer.writerow([])
        
        writer.writerow(["--- TRABAJOS ---"])
        writer.writerow(["Aeropuerto", "Trabajo", "Horas", "Ingreso USD"])
        for j in report_data.get("jobs", []):
            writer.writerow([j.get("airport_id"), j.get("name"), j.get("hours"), j.get("earned_usd")])
            
        return output.getvalue()
    else:
        raise ValueError(f"Formato no soportado: {fmt}")


def generate_final_report(graph: Graph, state: DynamicState) -> Dict[str, Any]:
    destinations_map: Dict[str, Dict[str, Any]] = {}
    flights = []
    activities = []
    jobs = []

    # Initialize visited airports in the map to track costs and stays
    for ap_id in state.visited:
        if ap_id not in destinations_map:
            airport = graph.get_airport(ap_id)
            destinations_map[ap_id] = {
                "id": ap_id,
                "name": airport.name if airport else ap_id,
                "city": airport.city if airport else "Desconocida",
                "country": airport.country if airport else "Desconocido",
                "stay_min": 0.0,
                "total_cost": 0.0,
            }

    # Process all steps to aggregate data
    for step in state.steps:
        # Aggregating costs per destination
        if step.airport_id in destinations_map:
            cost = step.metadata.get("cost", 0.0)
            if cost > 0:
                destinations_map[step.airport_id]["total_cost"] += cost
            
            # Action specific aggregation
            if step.action == "tiempo_libre":
                destinations_map[step.airport_id]["stay_min"] += step.metadata.get("duration", 0.0)
            elif step.action == "actividad":
                destinations_map[step.airport_id]["stay_min"] += step.metadata.get("duration", 0.0)
                activities.append({
                    "airport_id": step.airport_id,
                    "name": step.metadata.get("name", "Desconocida"),
                    "kind": step.metadata.get("kind", "Desconocido"),
                    "duration_min": step.metadata.get("duration", 0.0),
                    "cost_usd": cost,
                })
            elif step.action == "trabajo":
                destinations_map[step.airport_id]["stay_min"] += step.metadata.get("hours", 0.0) * 60
                jobs.append({
                    "airport_id": step.airport_id,
                    "name": step.metadata.get("name", "Desconocido"),
                    "hours": step.metadata.get("hours", 0.0),
                    "earned_usd": step.metadata.get("earned", 0.0),
                })
        
        # Flight segments
        if step.action == "vuelo":
            flights.append({
                "origin": step.metadata.get("origin"),
                "destination": step.metadata.get("destination"),
                "aircraft": step.metadata.get("aircraft"),
                "distance_km": step.metadata.get("distance_km", 0.0),
                "duration_min": step.metadata.get("duration", 0.0),
                "cost_usd": step.metadata.get("cost", 0.0),
            })

    # The current airport stay time needs to include the current stay_min
    if state.current_airport in destinations_map:
        destinations_map[state.current_airport]["stay_min"] += state.stay_min

    destinations = list(destinations_map.values())

    totals = {
        "initial_budget": state.initial_budget,
        "total_spent": state.total_spent,
        "total_earned": state.total_earned,
        "final_budget": state.budget_usd,
        "total_time_spent_min": state.initial_budget - state.budget_usd, # Esto está mal, la logica de tiempo debe ser (initial_time - time_left_min)
    }

    # Asumiendo que podemos recuperar el tiempo inicial si lo tuvieramos, pero 
    # dado que el estado guarda `time_left_min`, necesitamos calcular el tiempo gastado
    # El tiempo gastado es la suma de duraciones de vuelos y estancias.
    total_stay_min = sum(d["stay_min"] for d in destinations)
    total_flight_min = sum(f["duration_min"] for f in flights)
    
    totals["total_time_spent_min"] = total_stay_min + total_flight_min

    return {
        "destinations": destinations,
        "flights": flights,
        "activities": activities,
        "jobs": jobs,
        "totals": totals,
    }
