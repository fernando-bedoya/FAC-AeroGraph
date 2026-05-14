# INGENIERÍA EN SISTEMAS Y COMPUTACIÓN
# ESTRUCTURAS DE DATOS — PROYECTO GRAFOS

# SkyRoute Planner: Optimización de Rutas Aéreas

## 1 Contexto del problema

Una aerolínea regional opera una red de rutas entre ciudades de América Latina. Un viajero frecuente desea planificar sus desplazamientos de la forma más eficiente posible: maximizando los destinos visitados dentro de su presupuesto y tiempo disponibles, optimizando sus escalas y adaptando su itinerario en tiempo real a las condiciones de la red.

El sistema que se requiere desarrollar deberá modelar la red aérea como un grafo ponderado y dirigido, cargado desde un archivo JSON cuya estructura se describe en el documento adjunto. Sobre este grafo, el sistema aplicará algoritmos de camino mínimo y estrategias de búsqueda para responder las consultas del viajero.

### Restricciones generales del sistema

- El grafo representa rutas aéreas reales con costos en dólares (USD) y tiempos en minutos.
- Todas las rutas son dirigidas: si A→B existe, B→A debe declararse explícitamente, en caso de no especificarse, quiere decir que no existe.
- El viajero no desea hacer escala más de una vez en un mismo aeropuerto.
- El presupuesto y el tiempo son restricciones duras: ninguna ruta propuesta puede violarlos.
- Los datos de costos por kilómetro y tiempos por km de cada aeronave se pueden sobreescribir en el JSON desde la interfaz gráfica.

## 2 Requerimientos funcionales

### 2.1 1. Carga y visualización de la red aérea (0.5 puntos)

Una vez cargado el archivo JSON, el sistema debe representar gráficamente la red de rutas en pantalla. Cada nodo representa un aeropuerto identificado por su código IATA y cada arista representa una ruta dirigida. El grafo debe mostrar el tipo de aeronave disponible en cada ruta y los pesos de distancia en kilómetros.

- La representación gráfica debe distinguir visualmente los aeropuertos hubs de los secundarios.
- Las rutas deben mostrar la distancia en km sobre cada arista.
- Al seleccionar un nodo, debe desplegarse la información del aeropuerto: ciudad, país, zona horaria y lista de aerolíneas que operan desde allí.

### 2.2 2. Planificación básica de itinerario (1.5 puntos)

Dado el aeropuerto de origen, el presupuesto inicial del viajero en dólares USD y el tiempo total disponible para el viaje en horas, el sistema debe proponer automáticamente dos alternativas de itinerario (considerando que se debe usar al menos una vez cada tipo de transporte):

#### a.
La ruta que le permita visitar la mayor cantidad de destinos sin exceder el presupuesto inicial, mostrando la secuencia completa de vuelos, las escalas intermedias, el costo de cada tramo y el costo acumulado.

#### b.
La ruta que le permita visitar la mayor cantidad de destinos en el menor tiempo posible sin exceder el tiempo disponible, mostrando la secuencia de vuelos, la duración de cada tramo y el tiempo acumulado.

El sistema deberá permitir el cálculo de la mejor ruta considerando diferentes criterios de optimización. Para ello, se contemplan las siguientes funcionalidades:

- Seleccionar el criterio de optimización de la ruta, pudiendo elegir entre:
  - Distancia
  - Tiempo
  - Costo en USD
  - Cualquier combinación de los anteriores (si elige varios criterios, se debe calcular una ruta por cada criterio).
- Definir el punto de origen del viaje.
- Definir el destino final.
- Indicar si se desea incluir o excluir aeropuertos secundarios. En caso de excluirlos, estos no serán considerados dentro del cálculo de la ruta.
- Seleccionar los tipos de transporte preferidos:
  - El usuario deberá elegir al menos un tipo de transporte.
  - También podrá seleccionar múltiples opciones o la totalidad de los medios disponibles.

### 2.3 3. Planificación avanzada con gestión dinámica de presupuesto (2.0 puntos)

Dado el aeropuerto de origen, el sistema debe sugerir la ruta que permita conocer la mayor cantidad de destinos con el menor gasto total posible. A diferencia del requerimiento anterior, aquí el viajero puede aumentar su presupuesto durante el viaje tomando trabajos disponibles en los destinos, lo que introduce decisiones dinámicas que impiden una solución puramente estática.

El sistema debe ejecutarse paso a paso, presentando al viajero las alternativas disponibles en cada momento y registrando cada decisión. Los subpuntos siguientes definen las reglas del modelo:

#### a. Actividades en cada destino

En cada aeropuerto del grafo existen actividades que se ofrecen al viajero. Algunas son obligatorias y otras opcionales:

- Obligatorias:
  - Alojamiento: el viajero debe hospedarse en el aeropuerto o ciudad de escala siempre que hayan transcurrido 20 horas desde el último hospedaje. Cada aeropuerto tiene un costo de alojamiento por noche definido en el JSON.
  - Alimentación: debe realizarse cada 8 horas. Si las 8 horas se cumplen durante un vuelo, el costo se tomará del último aeropuerto visitado. El costo de alimentación es específico de cada nodo.
- Opcionales: tours, visitas a museos, actividades culturales, etc. Cada una tiene un tiempo de ejecución en minutos y un costo en USD. El sistema debe presentarlas al viajero para que decida cuáles realizar. Si el tiempo total de actividades y trabajos no alcanza la estancia mínima en el aeropuerto, el tiempo restante se registra como tiempo libre.

#### b. Trabajos disponibles y gestión del presupuesto

En cada aeropuerto se ofertan trabajos temporales (cargador de equipaje, asistente de rampa, guía de aeropuerto, etc.). El viajero puede aceptar un trabajo cuando su presupuesto caiga por debajo del 35% del presupuesto inicial. El viajero especifica cuántas horas dedicará al trabajo elegido; el ingreso se calcula como: tarifa_por_hora × horas_trabajadas. El sistema debe:

- Mostrar la lista de trabajos disponibles en el aeropuerto actual con su tarifa horaria.
- Permitir al viajero elegir el trabajo y la cantidad de horas (con un máximo por trabajo definido en el JSON).
- Actualizar el presupuesto disponible y el tiempo restante del viaje.
- Registrar el trabajo realizado para incluirlo en el reporte final.

#### c. Medios de transporte y costos de ruta

En cada ruta entre aeropuertos operan uno o más tipos de aeronave. Los tipos disponibles son: Avión Comercial, Avión Regional y Hélice. Los valores predeterminados son:

| Aeronave | Costo (USD/km) | Tiempo (min/km) |
|---|---|---|
| Avión Comercial | 0.18 | 0.7 |
| Avión Regional | 0.25 | 1.1 |
| Hélice | 0.12 | 2.5 |

El costo total de un tramo se calcula como: distancia_km × costo_por_km_aeronave. El tiempo de vuelo se calcula como: distancia_km × tiempo_por_km_aeronave. Estos valores pueden sobreescribirse en el JSON desde la interfaz gráfica. Hay rutas en las que el costo del desplazamiento es cero (p.ej. rutas subsidiadas), lo cual debe estar indicado en el JSON sin que el viajero pueda tomar más del 20% de la distancia de la ruta usando esta opción.

En cada tramo, el sistema debe informar al viajero las aeronaves disponibles con sus costos y tiempos calculados para esa ruta específica, y permitirle elegir. El viajero debe poder comparar las opciones antes de decidir.

### 2.4 4. Interrupciones en la red (0.5 puntos)

El sistema debe permitir la interrupción de cualquier ruta en cualquier momento durante la ejecución, simulando situaciones reales como cierre de espacio aéreo, condiciones meteorológicas adversas o cancelación de operaciones de una aerolínea en un tramo específico. Al interrumpirse una ruta:

- El grafo debe actualizarse bloqueando la arista afectada.
- Si el viajero se encuentra en tránsito en esa ruta, debe redirigirse al aeropuerto de origen del tramo y recalcular el itinerario desde allí. Por esto en la interfaz del proyecto se deberá ver el desplazamiento del vuelo desde un punto hasta otro en un tiempo n para realizar este tipo de acciones. No es posible pasar de un aeropuerto a otro automáticamente.
- Si la ruta bloqueada invalida el itinerario planificado, el sistema debe recalcular automáticamente la mejor alternativa disponible.
- La ruta bloqueada debe resaltarse visualmente en el mapa con un color diferente.

### 2.5 5. Visualización de resultados y reporte final (0.5 puntos)

Todos los resultados de las operaciones deben resaltarse sobre el mapa de la red aérea. Al concluir el viaje o al solicitar un reporte, el sistema debe mostrar un resumen completo con la siguiente información para cada elemento del itinerario:

- Destinos visitados: nombre del aeropuerto, ciudad, país, tiempo de estadía y costo total incurrido en el destino.
- Tramos volados: aeropuerto origen, aeropuerto destino, aeronave elegida, distancia, tiempo de vuelo, costo del tramo.
- Actividades realizadas: nombre, tipo (obligatoria/opcional), tiempo y costo.
- Trabajos realizados: nombre del trabajo, horas trabajadas, ingreso obtenido.
- Totales: presupuesto inicial, total gastado, total ganado, saldo final, tiempo total del viaje.

## 3 Restricciones técnicas y criterios de evaluación

El proyecto debe implementarse en Python. La estructura de datos principal debe ser un grafo con lista de adyacencia implementado desde cero (no se permite el uso de librerías externas de grafos). El uso de Algoritmos vistos en clase es obligatorio y el código del algoritmo debe estar claramente documentado, indicando: la justificación de su aplicabilidad.

Se evaluará la calidad del análisis, no únicamente la implementación. El código generado por IA sin comprensión demostrable del estudiante será penalizado en la sustentación. Se realizarán preguntas específicas sobre las decisiones de diseño del grafo, la elección del algoritmo y los casos manejados.

| Requerimiento | Puntaje |
|---|---|
| R1 — Carga y visualización del grafo | 0.5 |
| R2 — Planificación básica (mayor cobertura con restricción) y cálculo de mejor ruta | 1.5 |
| R3 — Planificación avanzada con decisiones dinámicas | 2.0 |
| R4 — Interrupciones en la red y recálculo | 0.5 |
| R5 — Reporte final y visualización de resultados | 0.5 |
| Total | 5.0 |

## 4 Estructura del archivo JSON

El archivo JSON de entrada debe seguir la estructura definida en el documento adjunto. A continuación, se describe el esquema mínimo requerido:

### Nodos (aeropuertos)

- id: string — Código IATA (ej. "BOG", "MDE", "LIM")
- nombre: string — Nombre completo del aeropuerto
- ciudad: string, pais: string, zonaHoraria: string
- esHub: boolean — Indica si es aeropuerto hub
- costoAlojamiento: number — USD por noche
- costoAlimentacion: number — USD por comida
- actividades: array — Lista de actividades disponibles (nombre, tipo, duracionMin, costoUSD)
- trabajos: array — Lista de trabajos disponibles (nombre, tarifaHora, maxHoras)

### Aristas (rutas)

- origen: string — Código IATA origen
- destino: string — Código IATA destino
- distanciaKm: number — Distancia del tramo
- aeronaves: array — Tipos de aeronave que operan la ruta
- costoBase: number — 0 si la ruta tiene costo subsidiado
- estanciaMinima: number — Tiempo mínimo de permanencia en destino (minutos)

### Configuración global (opcional — sobreescribe valores predeterminados)

- aeronaves: objeto — costoKm y tiempoKm por tipo de aeronave
- presupuestoMinimoPorc: number — Porcentaje del presupuesto inicial que activa oferta de trabajos (default: 35%)
- intervaloAlojamiento: number — Horas entre hospedajes obligatorios (default: 20)
- intervaloAlimentacion: number — Horas entre comidas obligatorias (default: 8)

## 5 Condiciones de entrega

- Se permite trabajar en equipos de dos o tres integrantes.
- La sustentación es individual: cada integrante debe poder explicar cualquier parte del código. Es decir, no puede existir un integrante solo con frontend o solo con backend. Todos los miembros del equipo deben hacer parte del desarrollo completo.
- Se debe entregar: código fuente completo, archivo JSON de prueba con mínimo 30 aeropuertos.
- Fecha de entrega y sustentación: tentativamente última semana de mayo, por confirmar durante las siguientes semanas.

## 6 Entregables:

- Documentación (manual de usuario y manual técnico en PDF).
- Video explicativo de la solución y arquitectura del sistema (en un segundo idioma), todas las personas del equipo deben participar y deben estar en primer plano.
- Viudeotutorial: video explicativo del sistema, no reemplaza el manual de usuario (todos participan).
- Código debidamente versionado en una plataforma que soporte GIT, donde se evidencie los aportes de cada integrante del equipo. El código debe estar debidamente documentado en inglés.

En cualquier fecha, la entrega deberá realizarse el día anterior a más tardar a las 8:00 pm. vía correo electrónico. Los manuales y enlace a plataforma git deberán estar adjuntos en el correo, los vídeos pueden estar cargados en Youtube o en Drive, y referenciar los enlaces en el cuerpo del mensaje.

## Evaluación:

- Funcionalidad: 50% (en equipo).
- Sustentación individual: 50%.

La nota de la sustentación individual no podrá ser menor en una unidad (1) de la nota de la funcionalidad, en tal caso, la nota de funcionalidad será disminuida hasta el valor de la nota de la sustentación individual para el estudiante en cuestión.

> "El conocimiento que no puedes defender en una sustentación no es tuyo."

