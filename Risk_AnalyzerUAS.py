"""
👨‍🔬 Autor:
Team. Tecnologías Aplicadas ING/Drummond
Desarrollador: Carlos Lozano
Ingeniero de Software y Técnico en construcción y reparación de drones.
Perfil profesional: https://www.linkedin.com/in/carlos-eduardo-lozano-miranda-285a717b/
Contacto: 3162950230
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from xml.etree import ElementTree as ET
from scipy.spatial import cKDTree
import plotly.express as px

# Configura el directorio base para ejecución desde ejecutables empaquetados (ej. PyInstaller)
BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE_DIR)

# Función que intenta extraer el número de serie del dron desde un archivo KML
def extraer_serial_desde_placemark(path):
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        for placemark in root.iter():
            if placemark.tag.endswith("Placemark"):
                for child in placemark:
                    if child.tag.endswith("name") and child.text:
                        if child.text.endswith(".JPG") and "_" in child.text:
                            return child.text.split("_")[0]
    except Exception:
        return None

# Parsea un archivo KML y devuelve un DataFrame con los datos de trayectoria
def parse_kml(path, drone_id):
    tree = ET.parse(path)
    root = tree.getroot()
    ns = {"gx": "http://www.google.com/kml/ext/2.2", "kml": "http://www.opengis.net/kml/2.2"}
    data = []
    for placemark in root.findall(".//kml:Placemark", ns):
        for track in placemark.findall(".//gx:Track", ns):
            coords = [coord.text.strip().split() for coord in track.findall("gx:coord", ns)]
            times = [when.text.strip() for when in track.findall("kml:when", ns)]
            for (lon, lat, alt), time in zip(coords, times):
                data.append({
                    "timestamp": datetime.fromisoformat(time),
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "altitude": float(alt),
                    "drone_id": drone_id
                })
    return pd.DataFrame(data)

# Define el umbral de proximidad mínima entre drones en metros
UMBRAL_PROXIMIDAD_METROS = 3.0

# Función principal para generar un informe HTML basado en los archivos KML disponibles
def generar_informe(kml_files, output_html):
    dfs = []       # Lista para almacenar DataFrames individuales
    resumen = []   # Lista para estadísticas por dron

    # Procesa cada archivo KML
    for i, path in enumerate(kml_files, start=1):
        serial = extraer_serial_desde_placemark(path)
        base_name = os.path.basename(path).split(".")[0]
        drone_id = f"{serial} ({base_name})" if serial else f"Drone_{i}"

        df_part = parse_kml(path, drone_id)
        df_part["timestamp"] = pd.to_datetime(df_part["timestamp"]).dt.tz_convert('America/Bogota')

        # Obtiene estadísticas de tiempo
        inicio_fmt = df_part["timestamp"].min().strftime("%H:%M:%S")
        fin_fmt = df_part["timestamp"].max().strftime("%H:%M:%S")
        dur_td = df_part["timestamp"].max() - df_part["timestamp"].min()
        total_sec = int(dur_td.total_seconds())
        h, rem = divmod(total_sec, 3600)
        m, s = divmod(rem, 60)
        dur_fmt = f"{h:02}:{m:02}:{s:02}"

        resumen.append({
            "drone_id": drone_id,
            "inicio": inicio_fmt,
            "fin": fin_fmt,
            "duracion": dur_fmt
        })

        dfs.append(df_part)

    # Une todos los vuelos en un único DataFrame
    df = pd.concat(dfs).reset_index(drop=True)

    # Conversión de coordenadas geográficas a cartesianas (para cálculo de distancias)
    R = 6371000  # Radio terrestre en metros
    lat0 = np.deg2rad(df["latitude"].mean())
    lon0 = np.deg2rad(df["longitude"].mean())
    df["x"] = (np.deg2rad(df["longitude"]) - lon0) * np.cos(lat0) * R
    df["y"] = (np.deg2rad(df["latitude"]) - lat0) * R
    df["z"] = df["altitude"]
    df["timestamp_round"] = df["timestamp"].dt.round("100ms")  # Agrupación temporal por instante

    # Estadísticas generales
    alt_max = df["altitude"].max()
    alt_min = df["altitude"].min()
    tiempo_total_min = (df["timestamp"].max() - df["timestamp"].min()).total_seconds() / 60

    # Detección de eventos de proximidad usando KDTree
    eventos = []
    total_instantes = df["timestamp_round"].nunique()
    for _, grupo in df.groupby("timestamp_round"):
        if grupo.shape[0] < 2:
            continue
        coords = grupo[["x", "y", "z"]].to_numpy()
        ids = grupo["drone_id"].to_numpy()
        tree = cKDTree(coords)
        pairs = tree.query_pairs(UMBRAL_PROXIMIDAD_METROS)
        for i, j in pairs:
            if ids[i] != ids[j]:
                eventos.append((grupo["timestamp_round"].iloc[0], ids[i], ids[j]))

    # Cálculo de la probabilidad empírica de colisión
    instantes_con_evento = set(t for t, _, _ in eventos)
    probabilidad_real = len(instantes_con_evento) / total_instantes if total_instantes > 0 else 0

    # Visualización 3D con Plotly
    fig = px.scatter_3d(df, x="x", y="y", z="z", color="drone_id",
                        title="Trayectorias 3D de Drones",
                        labels={"x": "X (m)", "y": "Y (m)", "z": "Altura (m)", "drone_id": "Dron"})
    fig.update_traces(marker=dict(size=2))
    fig.update_layout(scene=dict(aspectmode="data"),
                      margin=dict(l=0, r=0, t=30, b=0),
                      paper_bgcolor='white',
                      plot_bgcolor='white',
                      font_color='black')
    plot_html = fig.to_html(full_html=False, include_plotlyjs='cdn', config={"responsive": True},
                            default_width="100%", default_height="100%")

    # Generación de tabla HTML con resumen de misiones
    tabla_html = "<table border='1' style='border-collapse:collapse; width:100%; text-align:left;'>"
    tabla_html += "<thead><tr><th>Dron</th><th>Inicio</th><th>Fin</th><th>Duración</th></tr></thead><tbody>"
    for r in resumen:
        tabla_html += f"<tr><td>{r['drone_id']}</td><td>{r['inicio']}</td><td>{r['fin']}</td><td>{r['duracion']}</td></tr>"
    tabla_html += "</tbody></table>"

    # Escritura del informe HTML final con todos los resultados
    with open(output_html, "w", encoding="utf-8") as f:
        f.write("..." + plot_html + "...")  # Aquí se omite por brevedad el HTML extenso ya incrustado.

# Punto de entrada principal al ejecutar como script
if __name__ == "__main__":
    archivos_kml = [f for f in os.listdir('.') if f.lower().endswith('.kml')]
    if not archivos_kml:
        print("No se encontraron archivos KML en la carpeta.")
    else:
        print(f"Archivos KML encontrados: {archivos_kml}")
        try:
            generar_informe(archivos_kml, "Informe_MultiUAS_Risk_AnalyzerUAS.html")
            print("Informe_MultiUAS_Risk_AnalyzerUAS.html generado correctamente.")
        except Exception as e:
            print("¡Error durante la generación del informe!", e)

            print("Informe_MultiUAS_Risk_AnalyzerUAS.html generado correctamente.")
        except Exception as e:
            print("¡Error durante la generación del informe!", e)
#input("\nPresiona Enter para cerrar esta ventana…")

