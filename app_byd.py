import asyncio
import datetime
import json
import os
from zoneinfo import ZoneInfo
import streamlit as st
from pybyd import BydClient, BydConfig

# Zona horaria peninsular española
TZ_LOCAL = ZoneInfo("Europe/Madrid")
CONFIG_FILE = "config.json"

def obtener_ahora_local() -> datetime.datetime:
    return datetime.datetime.now(TZ_LOCAL)

# --- Persistencia de la última configuración y telemetría ---
def cargar_configuracion() -> dict:
    config_defecto = {
        "soc_objetivo": 80,
        "minutos_por_pct": 2.7,
        "hora_inicio": "05h",
        "minuto_inicio": "00m",
        "ultimo_soc_conocido": 50,
        "ultimo_timestamp_str": ""
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                datos = json.load(f)
                config_defecto.update(datos)
        except Exception:
            pass
    return config_defecto

def guardar_configuracion_multiple(pares: dict):
    config_actual = cargar_configuracion()
    config_actual.update(pares)
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_actual, f)
    except Exception:
        pass

def guardar_configuracion(clave: str, valor):
    guardar_configuracion_multiple({clave: valor})

st.set_page_config(
    page_title="Carga Atto 2 DMi",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
        .block-container { 
            padding-top: 3.5rem !important; 
            padding-bottom: 2rem; 
        }
        
        .app-title {
            text-align: center;
            font-size: 1.6rem;
            font-weight: 800;
            color: var(--text-color, #111827);
            margin-bottom: 0.4rem;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .soc-highlight-container {
            display: flex;
            align-items: baseline;
            justify-content: center;
            gap: 4px;
            margin-top: 5px;
            margin-bottom: 2px;
        }
        .soc-value {
            font-size: 3.8rem;
            font-weight: 800;
            color: #2563eb;
            line-height: 1;
        }
        .soc-unit {
            font-size: 2rem;
            font-weight: 700;
            color: #2563eb;
        }

        .timestamp-box {
            text-align: center;
            font-size: 0.8rem;
            color: #9ca3af;
            margin-bottom: 8px;
        }

        .bar-wrapper {
            width: 100%;
            padding: 0 4px;
            box-sizing: border-box;
            margin-top: 6px;
            margin-bottom: 20px;
        }

        .segmented-bar {
            display: flex;
            width: 100%;
            height: 16px;
            background-color: #374151;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.25);
        }
        .seg-actual { background-color: #2563eb; height: 100%; }
        .seg-deseado { background-color: #10b981; height: 100%; }
        .seg-resto { background-color: #374151; height: 100%; }

        .scale-relative-container {
            position: relative;
            width: 100%;
            height: 18px;
            margin-top: 6px;
        }
        
        .scale-point {
            position: absolute;
            top: 0;
            font-size: 0.72rem;
            color: #6b7280;
            white-space: nowrap;
            transform: translateX(-50%);
        }
        .scale-point-0 {
            left: 0% !important;
            transform: translateX(0) !important;
            text-align: left;
        }
        .scale-point-100 {
            left: 100% !important;
            transform: translateX(-100%) !important;
            text-align: right;
        }

        .section-time-title {
            font-size: 0.9rem;
            font-weight: 700;
            color: var(--text-color, #374151);
            margin-top: 14px;
            margin-bottom: 4px;
        }

        .schedule-card {
            background: linear-gradient(135deg, #1e293b, #0f172a);
            border: 2px solid #334155;
            border-radius: 16px;
            padding: 20px;
            text-align: center;
            margin: 15px 0 25px 0;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.4);
        }
        .time-box {
            font-size: 2.2rem;
            font-weight: 800;
            letter-spacing: 1px;
        }
        .time-start { color: #34d399; }
        .time-end { color: #f87171; }
        .card-label {
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #cbd5e1;
            margin-bottom: 4px;
        }

        .footer-text {
            text-align: left;
            font-size: 0.78rem;
            color: #9ca3af;
            margin-top: 30px;
            padding-top: 10px;
            border-top: 1px solid rgba(156, 163, 175, 0.2);
        }
    </style>
""", unsafe_allow_html=True)

def redondear_a_5_minutos(dt: datetime.datetime) -> datetime.datetime:
    minutos = dt.minute + dt.second / 60.0
    resto = minutos % 5
    if resto < 2.5:
        minutos_ajustados = minutos - resto
    else:
        minutos_ajustados = minutos + (5 - resto)
    dt_base = dt.replace(minute=0, second=0, microsecond=0)
    return dt_base + datetime.timedelta(minutes=round(minutos_ajustados))

async def descargar_datos_reales():
    usuario = st.secrets["byd"]["username"]
    password = st.secrets["byd"]["password"]

    config = BydConfig(username=usuario, password=password)
    async with BydClient(config) as client:
        vehicles = await client.get_vehicles()
        if not vehicles:
            return None
        vin = vehicles[0].vin
        realtime = await client.get_vehicle_realtime(vin)
        ahora = obtener_ahora_local()
        bateria_val = int(realtime.elec_percent)
        
        guardar_configuracion_multiple({
            "ultimo_soc_conocido": bateria_val,
            "ultimo_timestamp_str": ahora.strftime('%d/%m/%Y a las %H:%M:%S')
        })
        
        return {
            "vin": vin,
            "bateria": bateria_val,
            "timestamp_str": ahora.strftime('%d/%m/%Y a las %H:%M:%S'),
            "manual": False
        }

def intentar_actualizar_telemetria():
    cfg = cargar_configuracion()
    with st.spinner("Intentando conectar con el coche..."):
        try:
            res = asyncio.run(descargar_datos_reales())
            if res:
                st.session_state["datos_coche"] = res
                st.session_state["modo_manual"] = False
                return
        except Exception:
            pass
            
    st.session_state["modo_manual"] = True
    st.session_state["datos_coche"] = {
        "bateria": int(cfg.get("ultimo_soc_conocido", 50)),
        "timestamp_str": cfg.get("ultimo_timestamp_str", "Desconocido"),
        "manual": True
    }

if "datos_coche" not in st.session_state:
    intentar_actualizar_telemetria()

# Título centrado y simétrico con rayo a la izquierda y coche a la derecha
st.markdown("<div class='app-title'>⚡ Carga Atto 2 DMi 🚗</div>", unsafe_allow_html=True)

datos = st.session_state.get("datos_coche")
cfg = cargar_configuracion()

if datos:
    es_manual = datos.get("manual", False)
    
    # 1. Indicador numérico destacado o selector manual
    if es_manual:
        st.warning("⚠️ Sin conexión con el coche (garaje). Puedes ajustar la carga manualmente:")
        soc_actual = st.number_input(
            "Carga actual del coche (%):",
            min_value=0,
            max_value=100,
            value=int(datos["bateria"]),
            step=1,
            key="input_soc_manual",
            help="Introduce el porcentaje que marca el cuadro del vehículo."
        )
        datos["bateria"] = soc_actual
        guardar_configuracion("ultimo_soc_conocido", soc_actual)
        
        ts_str = datos.get("timestamp_str", "")
        if ts_str and ts_str != "Desconocido":
            st.markdown(f"<div class='timestamp-box'>🕒 Última telemetría leída: {ts_str}</div>", unsafe_allow_html=True)
    else:
        soc_actual = datos["bateria"]
        ts_str = datos.get("timestamp_str", "")
        st.markdown(f"""
            <div class="soc-highlight-container">
                <span class="soc-value">{soc_actual}</span>
                <span class="soc-unit">%</span>
            </div>
            <div class="timestamp-box">
                🕒 Leído el {ts_str}
            </div>
        """, unsafe_allow_html=True)

    # 2. Carga deseada (%)
    soc_objetivo = st.slider(
        "Carga deseada (%)",
        min_value=0,
        max_value=100,
        value=int(cfg.get("soc_objetivo", 80)),
        step=1,
        key="slider_soc",
        on_change=lambda: guardar_configuracion("soc_objetivo", st.session_state.slider_soc)
    )

    # 3. Barra tricolor con escala sin %
    pct_azul = min(max(soc_actual, 0), 100)
    pct_verde = max(0, soc_objetivo - soc_actual) if soc_objetivo > soc_actual else 0
    pct_gris = max(0, 100 - (pct_azul + pct_verde))

    scale_points_html = []
    for i in range(0, 101, 10):
        if i == 0:
            scale_points_html.append("<span class='scale-point scale-point-0'>0</span>")
        elif i == 100:
            scale_points_html.append("<span class='scale-point scale-point-100'>100</span>")
        else:
            scale_points_html.append(f"<span class='scale-point' style='left: {i}%;'>{i}%</span>")
    
    escala_html = "".join(scale_points_html)
    
    st.markdown(f"""
        <div class="bar-wrapper">
            <div class="segmented-bar">
                <div class="seg-actual" style="width: {pct_azul}%;"></div>
                <div class="seg-deseado" style="width: {pct_verde}%;"></div>
                <div class="seg-resto" style="width: {pct_gris}%;"></div>
            </div>
            <div class="scale-relative-container">
                {escala_html}
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 4. Pantalla "INTRODUCIR EN LA PANTALLA DEL BYD"
    minutos_por_pct_guardado = float(cfg.get("minutos_por_pct", 2.7))
    hora_guardada = cfg.get("hora_inicio", "05h")
    minuto_guardado = cfg.get("minuto_inicio", "00m")

    m_pct_actual = st.session_state.get("input_minutos_pct", minutos_por_pct_guardado)
    h_pill_actual = st.session_state.get("pills_hora", hora_guardada) or hora_guardada
    m_pill_actual = st.session_state.get("pills_minuto", minuto_guardado) or minuto_guardado

    if soc_objetivo <= soc_actual:
        st.info(f"El nivel actual ({soc_actual}%) ya cubre o supera el objetivo marcado ({soc_objetivo}%).")
    else:
        delta_pct = soc_objetivo - soc_actual
        minutos_totales = delta_pct * m_pct_actual
        duracion = datetime.timedelta(minutes=minutos_totales)
        
        h_val = int(h_pill_actual.replace("h", ""))
        m_val = int(m_pill_actual.replace("m", ""))
        
        hora_inicio_dt = datetime.time(h_val, m_val)
        fecha_local = obtener_ahora_local().date()
        dt_inicio = datetime.datetime.combine(fecha_local, hora_inicio_dt)
        dt_fin = redondear_a_5_minutos(dt_inicio + duracion)
        
        cambio_dia = " *(día siguiente)*" if dt_fin.date() > dt_inicio.date() else ""

        st.markdown(f"""
            <div class="schedule-card">
                <div style="font-size: 0.85rem; color: #cbd5e1; margin-bottom: 12px; font-weight: 600;">
                    INTRODUCIR EN LA PANTALLA DEL BYD
                </div>
                <div style="display: flex; justify-content: space-around; align-items: center;">
                    <div>
                        <div class="card-label">Inicio</div>
                        <div class="time-box time-start">{dt_inicio.strftime('%H:%M')}</div>
                    </div>
                    <div style="font-size: 1.8rem; color: #64748b;">➔</div>
                    <div>
                        <div class="card-label">Fin</div>
                        <div class="time-box time-end">{dt_fin.strftime('%H:%M')}</div>
                    </div>
                </div>
                <div style="margin-top: 14px; font-size: 0.85rem; color: #cbd5e1;">
                    Objetivo: <b>{soc_actual}% ➔ {soc_objetivo}% (+{delta_pct}%)</b> | Tiempo: <b>{int(minutos_totales // 60)}h {int(minutos_totales % 60)}m</b>{cambio_dia}
                </div>
            </div>
        """, unsafe_allow_html=True)

    # 5. Parámetro: minutos por 1%
    minutos_por_pct = st.number_input(
        "Minutos por 1%:",
        min_value=0.5,
        max_value=15.0,
        value=minutos_por_pct_guardado,
        step=0.1,
        format="%.2f",
        key="input_minutos_pct",
        on_change=lambda: guardar_configuracion("minutos_por_pct", st.session_state.input_minutos_pct)
    )

    # 6. Hora y Minutos de inicio
    lista_horas = [f"{i:02d}h" for i in range(24)]
    lista_minutos = [f"{i:02d}m" for i in range(0, 60, 5)]

    idx_hora_default = hora_guardada if hora_guardada in lista_horas else "05h"
    idx_min_default = minuto_guardado if minuto_guardado in lista_minutos else "00m"

    st.markdown("<div class='section-time-title'>🕐 Hora de inicio:</div>", unsafe_allow_html=True)
    hora_seleccionada = st.pills(
        "Seleccionar hora",
        options=lista_horas,
        default=idx_hora_default,
        key="pills_hora",
        on_change=lambda: guardar_configuracion("hora_inicio", st.session_state.pills_hora),
        label_visibility="collapsed"
    )

    st.markdown("<div class='section-time-title'>⏱️ Minutos de inicio:</div>", unsafe_allow_html=True)
    minuto_seleccionado = st.pills(
        "Seleccionar minutos",
        options=lista_minutos,
        default=idx_min_default,
        key="pills_minuto",
        on_change=lambda: guardar_configuracion("minuto_inicio", st.session_state.pills_minuto),
        label_visibility="collapsed"
    )

    # 7. Botón de actualización
    st.write("")
    if st.button("🔄 Actualizar valor carga actual", use_container_width=True):
        intentar_actualizar_telemetria()
        st.rerun()

    # 8. Pie de página alineado a la izquierda
    st.markdown("<div class='footer-text'>© Pablo Ruipérez - Septiembre 2026</div>", unsafe_allow_html=True)

else:
    st.warning("No hay datos de telemetría disponibles.")
    if st.button("🔄 Actualizar valor carga actual", use_container_width=True):
        intentar_actualizar_telemetria()
        st.rerun()
    st.markdown("<div class='footer-text'>© Pablo Ruipérez - Septiembre 2026</div>", unsafe_allow_html=True)
