# 🚀 Informe Técnico: Análisis de Proximidad en Vuelos Multi-Dron

👨‍🔬 Autor
**Team. Tecnologias Aplicadas ING/Drummond Ltd.**
**Desarrollador**
**Carlos Lozano**  
Ingeniero de Software y Técnico en construcción y reparación de drones. Con capacidad de brindar soporte técnico y operativo a sistemas de visión electro-óptica relacionados con aeronaves pilotadas a distancia (RPAS).  
Perfil profesional: [LinkedIn](https://www.linkedin.com/in/carlos-eduardo-lozano-miranda-285a717b/)  
Contacto: 3162950230

---

## 🌟 Objetivo General

Esta herramienta tiene como propósito principal **analizar eventos de proximidad crítica entre drones durante misiones simultáneas**, utilizando trayectorias registradas mediante sistemas GNSS de alta precisión como el **AsteRx-m2 OEM** de Septentrio (RTK/PPK). Los resultados se presentan en un informe HTML interactivo que permite comprender el comportamiento espacial-temporal de cada dron y detectar potenciales situaciones de riesgo.

---

## 🔹 Características Clave

- Lectura de archivos **KML** generados por drones con receptores GNSS.
- Conversión de coordenadas geodésicas a sistema **cartesiano local (x, y, z)**.
- Agrupación temporal en intervalos de **100 ms**, considerando latencias de control y registro.
- Implementación del algoritmo **`cKDTree` (scipy.spatial)** para detección eficiente de pares cercanos.
- Cálculo de **probabilidad empírica** de conflicto aéreo.
- Informe HTML con **tabla resumen**, **métricas por dron** y **mapa 3D interactivo**.

---

## 🛸 Dron de Referencia: eBee X

| Especificación       | Valor                          |
|------------------------|---------------------------------|
| Modelo                 | senseFly eBee X                 |
| Clase                  | C2 (certificación EASA)         |
| Autorización          | Vuelo BVLOS y sobre personas     |
| Envergadura            | ~1.16 metros                   |
| Velocidad de crucero   | ~12 m/s                         |

---

## ⚙️ Configuración y Algoritmos

| Parámetro                         | Valor          | Descripción |
|----------------------------------|----------------|-------------|
| `UMBRAL_PROXIMIDAD_METROS`       | 3.0 m          | Distancia mínima segura entre drones |
| `Intervalo temporal`             | 100 ms         | Resolución temporal por instancia |
| `Proyección local`               | basada en media lat/lon  | Conversión de lat/lon a coordenadas x,y |
| `Agrupación temporal`            | `timestamp.round('100ms')` | Agrupación por simultaneidad de eventos |
| `Algoritmo espacial`             | `cKDTree.query_pairs` | Búsqueda eficiente de pares a <3.0m |

---

## 🤖 Justificación del Umbral de 3.0 metros

Aunque inicialmente se consideró un umbral basado en la envergadura (~1.1 m), se adoptó **3.0 metros** considerando:

- Errores GNSS a pesar de RTK (hasta 0.5 m)
- Condiciones dinámicas: viento cruzado, maniobras evasivas
- Requerimientos de separación segura según prácticas internacionales
- Consultas académicas recientes que validan márgenes similares (Nature 2023, IEEE 2024)

> Nota: La latencia de 200–400 ms referida en artículos académicos no proviene del eBee X ni del AsteRx-m2 directamente, pero sirve como referencia para el diseño de herramientas predictivas y preventivas.

---

## 📊 Flujo Lógico del Script

```
1. Leer archivos KML de cada dron
2. Extraer coordenadas y timestamps (parse_kml)
3. Convertir coordenadas a sistema cartesiano local
4. Agrupar por timestamp en ventanas de 100ms
5. Usar KDTree para identificar pares cercanos (< 3.0m)
6. Filtrar eventos entre drones distintos
7. Calcular cantidad de instantes críticos
8. Obtener probabilidad empírica
9. Generar informe HTML con gráficos y tabla resumen
```

---

## 📈 Salida HTML Generada

El informe incluye:
- Tabla por dron: fecha, hora de inicio/fin, duración.
- Estadísticas globales: altitud máx/mín, tiempo total.
- Eventos críticos detectados.
- Probabilidad empírica de conflicto.
- Gráfico 3D con las trayectorias.

---

## 📊 Fundamento Académico: Probabilidad Empírica

La herramienta aplica una **métrica de seguridad observacional** ampliamente usada por la **OACI y la FAA**, donde se mide la frecuencia de ocurrencia real:

\[ **P(E) = \frac{\text{Eventos detectados}}{\text{Total de instantes analizados}}** \]

Esta aproximación es robusta, directa y sin suposiciones de distribuciones teóricas. Se apoya en los siguientes documentos:

- [OACI Doc 9859 - Safety Management Manual](https://www.icao.int/SAM/Documents/2017-SSP-GUY/Doc%209859%20SMM%20Third%20edition%20en.pdf)
- [FAA ATO Safety Management System Manual](https://www.faa.gov/air_traffic/publications/media/ATO-SMS-Manual.pdf)

---

## 📖 Bibliografía de Soporte

- "Safe and scalable multi-drone coordination" – *Nature, 2023*.  
- "Strategies for Real-time Collision Avoidance in UAV Swarms" – *IEEE, 2024*.  
- Documentación técnica Septentrio: **AsteRx-m2 OEM** GNSS RTK/PPK.

---

## 🛡️ Recomendaciones Profesionales

- Usar receptores GNSS certificados con registro RTK/PPK.
- Mantener intervalos de vuelo sincronizados (< 100 ms).
- Aplicar esta herramienta en etapas de validación antes de operar en espacios compartidos.
- Considerar escenarios con viento, carga, y errores de control para definir umbrales más conservadores.

---

Este informe representa un **modelo base reproducible** para el análisis de riesgos en entornos multi-UAV con respaldo en geometría computacional, teoría de probabilidad y regulaciones aeronáuticas internacionales.

