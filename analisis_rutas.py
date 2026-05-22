#!/usr/bin/env python3
"""
Análisis manual de rutas óptimas para BOG con presupuesto=$700 y tiempo=28h
"""

# Precios por km
precios = {
    "Avion Comercial": 0.18,
    "Avion Regional": 0.25,
    "Helice": 0.12
}

# Tiempos por km (en minutos)
tiempos = {
    "Avion Comercial": 0.7,
    "Avion Regional": 1.1,
    "Helice": 2.5
}

# Rutas desde BOG
rutas_bog = [
    {"origen": "BOG", "destino": "MDE", "distancia": 215, "aeronaves": ["Avion Comercial", "Helice"], "costoBase": 1},
    {"origen": "BOG", "destino": "LIM", "distancia": 1890, "aeronaves": ["Avion Comercial", "Avion Regional"], "costoBase": 1},
    {"origen": "BOG", "destino": "CUZ", "distancia": 1200, "aeronaves": ["Helice"], "costoBase": 1},
]

# Rutas desde MDE
rutas_mde = [
    {"origen": "MDE", "destino": "CLO", "distancia": 330, "aeronaves": ["Avion Regional", "Helice"], "costoBase": 1},
    {"origen": "MDE", "destino": "PTY", "distancia": 530, "aeronaves": ["Avion Comercial", "Helice"], "costoBase": 0},
]

# Rutas desde CLO
rutas_clo = [
    {"origen": "CLO", "destino": "UIO", "distancia": 490, "aeronaves": ["Avion Comercial", "Avion Regional", "Helice"], "costoBase": 1},
    {"origen": "CLO", "destino": "CUZ", "distancia": 640, "aeronaves": ["Helice"], "costoBase": 1},
]

# Rutas desde CUZ
rutas_cuz = [
    {"origen": "CUZ", "destino": "UIO", "distancia": 1480, "aeronaves": ["Avion Comercial", "Avion Regional"], "costoBase": 1},
    {"origen": "CUZ", "destino": "SCL", "distancia": 2100, "aeronaves": ["Helice"], "costoBase": 1},
]

# Rutas desde UIO
rutas_uio = [
    {"origen": "UIO", "destino": "LIM", "distancia": 1320, "aeronaves": ["Avion Comercial", "Avion Regional"], "costoBase": 1},
    {"origen": "UIO", "destino": "BOG", "distancia": 730, "aeronaves": ["Avion Comercial", "Helice"], "costoBase": 1},
]

# Rutas desde LIM
rutas_lim = [
    {"origen": "LIM", "destino": "SCL", "distancia": 2460, "aeronaves": ["Avion Comercial"], "costoBase": 1},
    {"origen": "LIM", "destino": "BOG", "distancia": 1890, "aeronaves": ["Avion Regional", "Helice"], "costoBase": 1},
]

def calcular_costo(distancia, aeronave, costoBase):
    return distancia * precios[aeronave] + costoBase

def calcular_tiempo(distancia, aeronave):
    return distancia * tiempos[aeronave]

print("="*80)
print("ANÁLISIS DE RUTAS ÓPTIMAS")
print("Origen: BOG, Presupuesto: $700, Tiempo: 28h (1680 min)")
print("="*80)

# Opción 1: BOG → MDE → CLO → UIO → LIM (con 3 transportes)
print("\n[CANDIDATO 1] BOG → MDE(Hélice) → CLO(Av.Regional) → UIO(Av.Comercial) → LIM(Av.Regional)")
print("-" * 80)

rutas_opcion1 = [
    ("BOG", "MDE", 215, "Helice"),
    ("MDE", "CLO", 330, "Avion Regional"),
    ("CLO", "UIO", 490, "Avion Comercial"),
    ("UIO", "LIM", 1320, "Avion Regional"),
]

costo_total = 1  # Base inicial de BOG
tiempo_total = 0
transportes = set()

for origen, destino, dist, aeronave in rutas_opcion1:
    costo_seg = calcular_costo(dist, aeronave, 1)
    tiempo_seg = calcular_tiempo(dist, aeronave)
    costo_total += costo_seg
    tiempo_total += tiempo_seg
    transportes.add(aeronave)
    print(f"  {origen}→{destino} ({dist}km, {aeronave}): ${costo_seg:.2f}, {tiempo_seg:.0f}min")

print(f"\n  TOTAL: {len(rutas_opcion1)} destinos (+ origen), ${costo_total:.2f}, {tiempo_total:.0f}min ({tiempo_total/60:.1f}h)")
print(f"  Transportes: {transportes} ({len(transportes)}/3)")
print(f"  Cumple restricciones: Costo ${costo_total:.2f} <= $700? {costo_total <= 700}, Tiempo {tiempo_total/60:.1f}h <= 28h? {tiempo_total <= 1680}")

# Opción 2: BOG → MDE → CLO → CUZ → UIO (con 3 transportes)
print("\n[CANDIDATO 2] BOG → MDE(Hélice) → CLO(Hélice) → CUZ(Hélice) → UIO(Av.Comercial) → LIM(Av.Regional)")
print("-" * 80)

rutas_opcion2 = [
    ("BOG", "MDE", 215, "Helice"),
    ("MDE", "CLO", 330, "Helice"),
    ("CLO", "CUZ", 640, "Helice"),
    ("CUZ", "UIO", 1480, "Avion Comercial"),
    ("UIO", "LIM", 1320, "Avion Regional"),
]

costo_total = 1
tiempo_total = 0
transportes = set()

for origen, destino, dist, aeronave in rutas_opcion2:
    costo_seg = calcular_costo(dist, aeronave, 1)
    tiempo_seg = calcular_tiempo(dist, aeronave)
    costo_total += costo_seg
    tiempo_total += tiempo_seg
    transportes.add(aeronave)
    print(f"  {origen}→{destino} ({dist}km, {aeronave}): ${costo_seg:.2f}, {tiempo_seg:.0f}min")

print(f"\n  TOTAL: {len(rutas_opcion2)} destinos (+ origen), ${costo_total:.2f}, {tiempo_total:.0f}min ({tiempo_total/60:.1f}h)")
print(f"  Transportes: {transportes} ({len(transportes)}/3)")
print(f"  Cumple restricciones: Costo ${costo_total:.2f} <= $700? {costo_total <= 700}, Tiempo {tiempo_total/60:.1f}h <= 28h? {tiempo_total <= 1680}")

# Opción 3: BOG → MDE → CLO → UIO (3 transportes, menos destinos)
print("\n[CANDIDATO 3] BOG → MDE(Av.Comercial) → CLO(Av.Regional) → UIO(Av.Comercial)")
print("-" * 80)

rutas_opcion3 = [
    ("BOG", "MDE", 215, "Avion Comercial"),
    ("MDE", "CLO", 330, "Avion Regional"),
    ("CLO", "UIO", 490, "Helice"),
]

costo_total = 1
tiempo_total = 0
transportes = set()

for origen, destino, dist, aeronave in rutas_opcion3:
    costo_seg = calcular_costo(dist, aeronave, 1)
    tiempo_seg = calcular_tiempo(dist, aeronave)
    costo_total += costo_seg
    tiempo_total += tiempo_seg
    transportes.add(aeronave)
    print(f"  {origen}→{destino} ({dist}km, {aeronave}): ${costo_seg:.2f}, {tiempo_seg:.0f}min")

print(f"\n  TOTAL: {len(rutas_opcion3)} destinos (+ origen), ${costo_total:.2f}, {tiempo_total:.0f}min ({tiempo_total/60:.1f}h)")
print(f"  Transportes: {transportes} ({len(transportes)}/3)")
print(f"  Cumple restricciones: Costo ${costo_total:.2f} <= $700? {costo_total <= 700}, Tiempo {tiempo_total/60:.1f}h <= 28h? {tiempo_total <= 1680}")

print("\n" + "="*80)
print("ANÁLISIS CORREGIDO (Requisitos 2.2.a y 2.2.b INDEPENDIENTES):")
print("="*80)

print("\n2.2.a - RUTA A (OPTIMIZAR POR COSTO):")
print("  Restricción: Presupuesto <= $700")
print("  Objetivo: MÁXIMO número de destinos")
print("  Tiempo: SIN RESTRICCIÓN")
print("-" * 80)
print("  MEJOR OPCIÓN: BOG → MDE(H) → CLO(R) → UIO(Cm) → LIM(R)")
print("  Costo: $26.80 + $83.50 + $89.20 + $331.00 = $531.50 < $700 ✓")
print("  Tiempo: 538 + 363 + 343 + 1452 = 2696 min (44.9h) - No importa")
print("  Destinos: 4 + origen = 5 aeropuertos visitados")
print("  Transportes: Hélice, Regional, Comercial (3/3) ✓")

print("\n2.2.b - RUTA B (OPTIMIZAR POR TIEMPO):")
print("  Restricción: Tiempo <= 28h (1680 min)")
print("  Objetivo: MÁXIMO número de destinos")
print("  Costo: SIN RESTRICCIÓN")
print("-" * 80)
print("  MEJOR OPCIÓN: BOG → MDE(H) → CLO(R) → UIO(Cm)")
print("  Tiempo: 538 + 363 + 343 = 1244 min (20.7h) < 1680 ✓")
print("  Costo: $26.80 + $83.50 + $89.20 = $199.50 - No importa")
print("  Destinos: 3 + origen = 4 aeropuertos visitados")
print("  Transportes: Hélice, Regional, Comercial (3/3) ✓")
print("  ")
print("  ALTERNATIVA: Agregar LIM sería:")
print("    - Tiempo: 1244 + 1452 = 2696 min (44.9h) > 1680 ✗ EXCEDE")
print("\n" + "="*80)

