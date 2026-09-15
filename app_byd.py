import asyncio
import datetime
from zoneinfo import ZoneInfo
import streamlit as st
from pybyd import BydClient, BydConfig

# Zona horaria peninsular española
TZ_LOCAL = ZoneInfo("Europe/Madrid")

def obtener_ahora_local() -> datetime.datetime:
    return datetime.datetime.now(TZ_LOCAL)

st.set_page_config(
    page_title="Ayuda carga Atto 2 Dmi",
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
        }

        .soc-highlight-container {
            display: flex;
            align-items: baseline;
            justify-content: center;
            gap: 8px;
            margin-top: 5px;
            margin-bottom: 2px;
        }
        .soc-value {
            font-size: 3.5rem;
            font-weight: 800;
            color: #2563eb;
            line-height: 1;
        }
        .soc-unit {
            font-size: 1.8rem;
            font-weight: 700;
            color: #2563eb;
        }
        .soc-km {
            font-size: 1.1rem;
            color: #6b7280;
            margin-left: 10px;
        }

        .timestamp-box {
            text-align: center;
            font-size: 0.8rem;
            color: #9ca3af;
            margin-bottom: 12px;
        }

        .segmented-bar {
            display: flex;
            width: 100%;
            height: 18px;
            background-color: #e5e7eb;
            border-radius: 9px;
            overflow: hidden;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.15);
        }
        .seg-actual { background-color: #2563eb; height: 100%; }
        .seg-deseado { background-color: #10b981; height: 100%; }
        .seg-resto { background-color: #4b5563; height: 100%; }

        .scale-container {
            display: flex;
            justify-content: space-between;
            margin-top: 5px;
            margin-bottom: 20px;
            padding: 0 2px;
        }
        .scale-label {
            font-size: 0.72rem;
            color: #6b7280;
            text-align: center;
        }

        /* --- CONTENEDOR HORA Y MINUTOS ANTI-DESBORDE --- */
        .time-header-title {
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-color, #374151);
            margin-top: 8px;
            margin-bottom: 4px;
        }

        div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            width: 100% !important;
            gap: 8px !important;
            align-items: flex-end !important;
        }
        
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            flex: 1 1 calc(50% - 4px) !important;
            width: calc(50% - 4px) !important;
            max-width: calc(50% - 4px) !important;
            min-width: 0 !important;
        }

        /* Oculta los botones laterales (+ / -) solo dentro de las columnas para eliminar el ancho mínimo forzado */
        div[data-testid="stHorizontalBlock"] button[data-testid="stNumberInputStepDown"],
        div[data-testid="stHorizontalBlock"] button[data-testid="stNumberInputStepUp"] {
            display: none !important;
        }

        /* Ajuste fino del input numérico para que ocupe el 100% sin padding excesivo */
        div[data-testid="stHorizontalBlock"] input {
            text-align: center !important;
            padding: 6px 4px !important;
            font-size: 1.1rem !important;
            font-weight: 600 !important;
        }

        .schedule-card {
            background: linear-gradient(135deg, #1e293b, #0f172a);
            border: 2px solid #334155;
            border-radius: 16px;
            padding: 20px;
            text-align: center;
            margin: 15px 0;
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
        return {
            "vin": vin,
            "bateria": int(realtime.elec_percent),
            "autonomia_ev": int(realtime.ev_endurance),
            "timestamp": obtener_ahora_local()
        }

def actualizar_telemetria():
    with st.spinner("Conectando con el coche..."):
        try:
            res = asyncio.run(descargar_datos_reales())
            if res:
                st.session_state["datos_coche"] = res
            else:
                st.error("No se encontraron vehículos vinculados.")
        except Exception as e:
            st.error(f"Error al contactar con la API de BYD: {e}")

if "datos_coche" not in st.session_state:
    actualizar_telemetria()

st.markdown("<div class='app-title'>⚡ Ayuda carga Atto 2 Dmi</div>", unsafe_allow_html=True)

datos = st.session_state.get("datos_coche")

if datos:
    soc_actual = datos["bateria"]
    dt_lectura = datos["timestamp"]

    # 1. Métrica destacada
    st.markdown(f"""
        <div class="soc-highlight-container">
            <span class="soc-value">{soc_actual}</span>
            <span class="soc-unit">%</span>
            <span class="soc-km">· {datos['autonomia_ev']} km EV</span>
        </div>
        <div class="timestamp-box">
            🕒 Leído el {dt_lectura.strftime('%d/%m/%Y a las %H:%M:%S')}
        </div>
    """, unsafe_allow_html=True)

    # 2. Configuración interactiva
    with st.expander("⚙️ Parámetros de carga", expanded=True):
        soc_objetivo = st.slider(
            "Carga deseada (%)",
            min_value=0,
            max_value=100,
            value=max(soc_actual + 1 if soc_actual < 100 else 100, 80 if soc_actual < 80 else soc_actual),
            step=1
        )
        
        minutos_por_pct = st.number_input(
            "Minutos por 1%:",
            min_value=0.5,
            max_value=15.0,
            value=2.7,
            step=0.1,
            format="%.2f"
        )
        
        st.markdown("<div class='time-header-title'>⏰ Hora de inicio (Hora : Minutos)</div>", unsafe_allow_html=True)
        
        ahora = redondear_a_5_minutos(obtener_ahora_local())
        
        col_hora, col_min = st.columns(2)
        with col_hora:
            hora_val = st.number_input(
                "Hora (0-23)",
                min_value=0,
                max_value=23,
                value=ahora.hour,
                step=1,
                format="%02d"
            )
        with col_min:
            min_val = st.number_input(
                "Min (0-55)",
                min_value=0,
                max_value=55,
                value=ahora.minute,
                step=5,
                format="%02d"
            )

    # 3. Barra de progreso tricolor
    pct_azul = min(max(soc_actual, 0), 100)
    pct_verde = max(0, soc_objetivo - soc_actual) if soc_objetivo > soc_actual else 0
    pct_gris = max(0, 100 - (pct_azul + pct_verde))

    escala_html = "".join([f"<div class='scale-label'>{i}%</div>" for i in range(0, 101, 10)])
    
    st.markdown(f"""
        <div class="segmented-bar">
            <div class="seg-actual" style="width: {pct_azul}%;"></div>
            <div class="seg-deseado" style="width: {pct_verde}%;"></div>
            <div class="seg-resto" style="width: {pct_gris}%;"></div>
        </div>
        <div class="scale-container">
            {escala_html}
        </div>
    """, unsafe_allow_html=True)

    # 4. Cálculo de horarios
    if soc_objetivo <= soc_actual:
        st.info(f"El nivel actual ({soc_actual}%) ya cubre o supera el objetivo marcado ({soc_objetivo}%).")
    else:
        delta_pct = soc_objetivo - soc_actual
        minutos_totales = delta_pct * minutos_por_pct
        duracion = datetime.timedelta(minutes=minutos_totales)
        
        hora_inicio_dt = datetime.time(int(hora_val), int(min_val))
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

    if st.button("🔄 Leer carga coche", use_container_width=True):
        actualizar_telemetria()
        st.rerun()

else:
    st.warning("No hay datos de telemetría disponibles.")
    if st.button("🔄 Intentar leer carga coche", use_container_width=True):
        actualizar_telemetria()
        st.rerun()
