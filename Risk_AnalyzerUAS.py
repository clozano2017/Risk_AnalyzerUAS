"""
👨‍🔬 Autor
**Team. Tecnologias Aplicadas ING/Drummond**
**Desarrollador**
**Carlos Lozano**  
Ingeniero de Software y Técnico en construcción y reparación de drones. Con capacidad de brindar soporte técnico y operativo a sistemas de visión electro-óptica relacionados con aeronaves pilotadas a distancia (RPAS).  
Perfil profesional: [LinkedIn](https://www.linkedin.com/in/carlos-eduardo-lozano-miranda-285a717b/)  
Contacto: 3162950230
"""
import os
import sys
BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE_DIR)
import os
import pandas as pd
import numpy as np
from datetime import datetime
from xml.etree import ElementTree as ET
from scipy.spatial import cKDTree
import plotly.express as px

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

UMBRAL_PROXIMIDAD_METROS = 3.0  # Distancia mínima recomendada entre drones (m)

def generar_informe(kml_files, output_html):
    dfs = []
    resumen = []

    for i, path in enumerate(kml_files, start=1):
        serial = extraer_serial_desde_placemark(path)
        base_name = os.path.basename(path).split(".")[0]
        drone_id = f"{serial} ({base_name})" if serial else f"Drone_{i}"

        df_part = parse_kml(path, drone_id)
        df_part["timestamp"] = pd.to_datetime(df_part["timestamp"]).dt.tz_convert('America/Bogota')

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

    df = pd.concat(dfs).reset_index(drop=True)

    R = 6371000
    lat0 = np.deg2rad(df["latitude"].mean())
    lon0 = np.deg2rad(df["longitude"].mean())
    df["x"] = (np.deg2rad(df["longitude"]) - lon0) * np.cos(lat0) * R
    df["y"] = (np.deg2rad(df["latitude"]) - lat0) * R
    df["z"] = df["altitude"]
    df["timestamp_round"] = df["timestamp"].dt.round("100ms")

    alt_max = df["altitude"].max()
    alt_min = df["altitude"].min()
    tiempo_total_min = (df["timestamp"].max() - df["timestamp"].min()).total_seconds() / 60

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

    instantes_con_evento = set(t for t, _, _ in eventos)
    probabilidad_real = len(instantes_con_evento) / total_instantes if total_instantes > 0 else 0

    # Por defecto en modo claro, pero preparado para modo oscuro dinámico
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

    tabla_html = "<table border='1' style='border-collapse:collapse; width:100%; text-align:left;'>"
    tabla_html += "<thead><tr><th>Dron</th><th>Inicio</th><th>Fin</th><th>Duración</th></tr></thead><tbody>"
    for r in resumen:
        tabla_html += f"<tr><td>{r['drone_id']}</td><td>{r['inicio']}</td><td>{r['fin']}</td><td>{r['duracion']}</td></tr>"
    tabla_html += "</tbody></table>"

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Informe Multi-UAS - Responsive</title>
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
  <style>
    :root {{
      --main-bg: #f4f4f4;
      --header-bg: #0a4275;
      --text-color: #222;
      --section-bg: #fff;
      --table-header: #0a4275;
      --table-bg-even: #f7faff;
      --box-shadow: 0 0 10px rgba(0,0,0,0.08);
      --footer-bg: #e9e9e9;
      --footer-color: #333;
    }}
    body {{
      font-family: 'Segoe UI', Arial, sans-serif;
      margin: 0;
      padding: 0;
      background: var(--main-bg);
      color: var(--text-color);
      transition: background 0.3s, color 0.3s;
    }}
    body.dark {{
      --main-bg: #222831;
      --header-bg: #101820;
      --text-color: #f3f3f3;
      --section-bg: #23272e;
      --table-header: #313b47;
      --table-bg-even: #23272e;
      --box-shadow: 0 0 16px rgba(0,0,0,0.3);
      --footer-bg: #101820;
      --footer-color: #d0d0d0;
    }}
    header {{
      background: var(--header-bg);
      color: var(--text-color);
      padding: 15px;
      text-align: center;
      border-radius: 0 0 15px 15px;
    }}
    nav {{
      background: #eee;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-around;
      padding: 10px 0;
      border-bottom: 1px solid #ccc;
    }}
    nav button, #btnFull, #btnDark {{
      background: #0a4275;
      color: white;
      border: none;
      padding: 10px 20px;
      border-radius: 5px;
      font-size: 14px;
      margin-bottom: 5px;
      transition: background 0.3s;
      cursor: pointer;
    }}
    nav button:hover, #btnFull:hover, #btnDark:hover {{
      background: #2562a6;
    }}
    #btnDark {{
      float: right;
      margin-left: 10px;
      background: #23272e;
    }}
    section {{
      padding: 20px;
      max-width: 900px;
      margin: 0 auto;
      background: var(--section-bg);
      border-radius: 12px;
      box-shadow: var(--box-shadow);
      margin-bottom: 20px;
    }}
    .responsive-table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--section-bg);
      border-radius: 10px;
      overflow: hidden;
      box-shadow: var(--box-shadow);
      margin-bottom: 25px;
    }}
    .responsive-table th, .responsive-table td {{
      border: 1px solid #eee;
      padding: 10px;
      text-align: left;
      font-size: 15px;
    }}
    .responsive-table th {{
      background: var(--table-header);
      color: white;
    }}
    .responsive-table tr:nth-child(even) {{
      background: var(--table-bg-even);
    }}
    .btn-download {{
      margin-top: 20px;
      display: block;
      width: 100%;
      text-align: center;
    }}
    .btn-download a {{
      background: #007bff;
      color: white;
      padding: 10px 15px;
      text-decoration: none;
      border-radius: 5px;
      font-size: 15px;
      transition: background 0.3s;
      display: inline-block;
    }}
    .btn-download a:hover {{
      background: #005bb5;
    }}
    /* ----- CENTRADO Y FULL WIDTH PARA VISOR ----- */
    #visor3d-plotly {{
      width: 100%;
      height: 70vh;
      min-height: 400px;
      margin: 0 auto;
      background: var(--section-bg);
      border-radius: 12px;
      box-shadow: var(--box-shadow);
      overflow: hidden;
      display: block;
      position: relative;
    }}
    #visor3d-plotly .js-plotly-plot {{
      width: 100% !important;
      height: 100% !important;
      margin: 0 auto !important;
      display: block !important;
      background: transparent !important;
    }}
    #visor3d-plotly:fullscreen, #visor3d-plotly:-webkit-full-screen {{
      width: 100vw !important;
      height: 100vh !important;
      min-width: 100vw !important;
      min-height: 100vh !important;
      border-radius: 0 !important;
      margin: 0 !important;
    }}
    #visor3d-plotly:fullscreen .js-plotly-plot, #visor3d-plotly:-webkit-full-screen .js-plotly-plot {{
      width: 100vw !important;
      height: 100vh !important;
      max-width: 100vw !important;
      min-width: 100vw !important;
      min-height: 100vh !important;
    }}
    footer {{
      text-align: center;
      padding: 18px 6px;
      font-size: 13px;
      background: var(--footer-bg);
      color: var(--footer-color);
      margin-top: 40px;
    }}
    @media (max-width: 600px) {{
      section {{
        padding: 10px;
      }}
      nav {{
        flex-direction: column;
        gap: 8px;
      }}
      #visor3d-plotly {{
        height: 40vh;
        min-height: 250px;
      }}
      .responsive-table th, .responsive-table td {{
        padding: 7px;
        font-size: 13px;
      }}
    }}
  </style>
</head>
<body>

<header style="display: flex; align-items: center; gap: 16px; background: var(--header-bg); color: var(--text-color); padding: 12px 20px; border-radius: 0 0 15px 15px;">
  <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAOcAAAA/CAYAAAAbmd9iAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAyhpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADw/eHBhY2tldCBiZWdpbj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8+IDx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IkFkb2JlIFhNUCBDb3JlIDUuNi1jMDE0IDc5LjE1Njc5NywgMjAxNC8wOC8yMC0wOTo1MzowMiAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvIiB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIgeG1sbnM6c3RSZWY9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZVJlZiMiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIENDIDIwMTQgKE1hY2ludG9zaCkiIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6OTM5MUE2NzlDMUYyMTFFNDkxREM4OTg3MEQ0MzFDQTIiIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6OTM5MUE2N0FDMUYyMTFFNDkxREM4OTg3MEQ0MzFDQTIiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDo5MzkxQTY3N0MxRjIxMUU0OTFEQzg5ODcwRDQzMUNBMiIgc3RSZWY6ZG9jdW1lbnRJRD0ieG1wLmRpZDo5MzkxQTY3OEMxRjIxMUU0OTFEQzg5ODcwRDQzMUNBMiIvPiA8L3JkZjpEZXNjcmlwdGlvbj4gPC9yZGY6UkRGPiA8L3g6eG1wbWV0YT4gPD94cGFja2V0IGVuZD0iciI/PjKU4LMAAA0sSURBVHja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" alt="Drummond Ltd." style="height:60px;">
  <h1 style="margin: 0; font-size: 2rem; font-weight: 700; flex: 1;">📊 Informe de Misión Multi-UAS</h1>
</header>

<nav>
  <button onclick="document.getElementById('resumen').scrollIntoView({{behavior: 'smooth'}});">Resumen</button>
  <button onclick="document.getElementById('visor').scrollIntoView({{behavior: 'smooth'}});">Visor 3D</button>
  <button onclick="document.getElementById('recomendaciones').scrollIntoView({{behavior: 'smooth'}});">Recomendaciones</button>
  <button id="btnDark">Modo Oscuro 🌙</button>
</nav>

<section id="resumen">
  <h2>📌 Resumen</h2>
  <p>Este informe analiza el riesgo de colisión entre múltiples drones según sus trayectorias registradas. 
  La distancia de proximidad evaluada es de <b>{UMBRAL_PROXIMIDAD_METROS} m</b> y la probabilidad empírica observada fue de <b>{probabilidad_real:.2%}</b> 
  sobre {total_instantes} instantes temporales.</p>
  <ul>
    <li>🚁 Altura máxima: <b>{alt_max:.2f} m</b></li>
    <li>🚁 Altura mínima: <b>{alt_min:.2f} m (take off AMSL)</b></li>
    <li>🕒 Tiempo total de operación: <b>{tiempo_total_min:.2f} min</b></li>
    <li>📉 Total de eventos detectados: <b>{len(eventos)}</b></li>
    <p><strong>Nota técnica:</strong> El análisis de colisión se realiza evaluando la distancia tridimensional entre cada par de drones en intervalos de 100 milisegundos. 
        Para cada instante, se utiliza la estructura espacial <b>cKDTree</b> para identificar pares de drones separados por menos de <strong>3.0 m</strong>, umbral que corresponde 
        a aproximadamente <b>2.7</b> veces la envergadura típica de los <b>eBee x </b>. Se considera un evento cuando dos drones diferentes cumplen esta condición.</p>
        <p>La <strong>probabilidad empírica de colisión</strong> se calcula como el cociente entre la cantidad de instantes con al menos un evento de colisión detectado y el total de instantes procesados:<br>
        <span style="display: block; text-align: center; margin-top: 0.5em; font-size: 1.1em;">
        <strong>P</strong> = <sub>N<sub>col</sub></sub> / <sub>N<sub>tot</sub></sub>
  </span>
</p>

    <p><b>Variables tenidas en cuenta:</b> coordenadas cartesianas (<code>x</code>, <code>y</code>, <code>z</code>), tiempo agrupado cada 100 ms y etiquetas únicas por dron.</p>

  </ul>
  <div style="overflow-x:auto">
    {tabla_html.replace('<table', '<table class="responsive-table"')}
  </div>
</section>

<section id="visor">
  <h2>🌐 Visor 3D Interactivo 
    <button id="btnFull">Pantalla Completa</button>
  </h2>
  <div id="visor3d-plotly">
    {plot_html}
  </div>
</section>
<script>
document.addEventListener('DOMContentLoaded', function() {{
  var btn = document.getElementById('btnFull');
  var elem = document.getElementById('visor3d-plotly');
  btn.onclick = function() {{
    if (elem.requestFullscreen) {{
      elem.requestFullscreen();
    }} else if (elem.mozRequestFullScreen) {{
      elem.mozRequestFullScreen();
    }} else if (elem.webkitRequestFullscreen) {{
      elem.webkitRequestFullscreen();
    }} else if (elem.msRequestFullscreen) {{
      elem.msRequestFullscreen();
    }}
  }};
  // Forzar resize de Plotly en pantalla completa
  function resizePlotly() {{
    var plot = elem.querySelector('.js-plotly-plot');
    if(plot && window.Plotly) {{
      Plotly.Plots.resize(plot);
    }}
  }}
  document.addEventListener('fullscreenchange', resizePlotly);
  document.addEventListener('webkitfullscreenchange', resizePlotly);
  document.addEventListener('mozfullscreenchange', resizePlotly);
  document.addEventListener('MSFullscreenChange', resizePlotly);

  // MODO OSCURO
  var btnDark = document.getElementById('btnDark');
  btnDark.onclick = function() {{
    document.body.classList.toggle('dark');
    // Cambiar tema del plotly
    var plot = elem.querySelector('.js-plotly-plot');
    if(plot && window.Plotly) {{
      var isDark = document.body.classList.contains('dark');
      Plotly.update(plot, {{}}, {{
        paper_bgcolor: isDark ? '#222831' : 'white',
        plot_bgcolor: isDark ? '#222831' : 'white',
        font: {{
          color: isDark ? '#f3f3f3' : '#222'
        }}
      }});
    }}
  }};
}});
</script>

<section id="recomendaciones">
  <h2>⚙️ Recomendaciones</h2>
  <ul>
    <li>⌚ Mantener resoluciones temporales entre drones 🛫 --> 🛬 de manera sincronizados (< 100 ms).</li>
    <li>✅ Mantener separación mínima de seguridad ≥ {UMBRAL_PROXIMIDAD_METROS} m.</li>
    <li>🛫 Aplicar esta herramienta en etapas de validación antes de operar en espacios compartidos.</li>
    <li>🤖 Recomendar al fabricante Considerar algoritmos de evasión automática en vuelos simultáneos.</li>
    <li>🚧 Considerar escenarios con viento, carga, y errores de control para definir umbrales más conservadores..</li>
  </ul>
</section>

<footer>
  Desarrollado por <strong>Tecnologías Aplicadas – Drummond Ltd.</strong><br>
  📞 316 295 0230
</footer>

</body>
</html>
""")

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
#input("\nPresiona Enter para cerrar esta ventana…")

