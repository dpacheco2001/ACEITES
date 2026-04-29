# PROMPT PARA CURSOR — Fase 3: Frontend Dashboard Streamlit
## SaaS Predictivo de Aceites — Flota 794AC Quellaveco

---

## CONTEXTO

Este es el **dashboard frontend** del SaaS de mantenimiento predictivo de la flota
794AC de Quellaveco. Se conecta al backend FastAPI (corriendo en `http://localhost:8000`)
para mostrar predicciones, alertas y el estado de cada camión en tiempo real.

El usuario final es el **ingeniero de mantenimiento** de la mina. El diseño debe ser
claro, industrial y orientado a la acción — no académico.

---

## STACK TÉCNICO

```bash
pip install streamlit requests pandas plotly openpyxl altair
```

- **Streamlit**: framework del dashboard
- **Plotly**: gráficos interactivos (curvas de degradación, gauges, barras)
- **Requests**: llamadas a la API FastAPI
- **Pandas**: manejo de datos locales

---

## ESTRUCTURA DE ARCHIVOS A CREAR

```
frontend/
├── app.py                  ← Punto de entrada principal (CREAR)
├── pages/
│   ├── 01_flota.py         ← Vista de toda la flota (CREAR)
│   ├── 02_equipo.py        ← Vista detallada por equipo (CREAR)
│   ├── 03_nueva_muestra.py ← Registro de nueva muestra (CREAR)
│   └── 04_reportes.py      ← Reportes y exportaciones (CREAR)
├── components/
│   ├── semaforo.py         ← Componente semáforo reutilizable (CREAR)
│   ├── gauge_chart.py      ← Gráfico gauge para variables (CREAR)
│   └── degradacion_chart.py← Curva de degradación (CREAR)
└── config.py               ← URL de la API y constantes (CREAR)
```

---

## CONFIGURACIÓN: `frontend/config.py`

```python
# URL base del backend FastAPI
API_BASE_URL = "http://localhost:8000"

# Colores del sistema de alertas
COLORES = {
    'ROJO':     '#e74c3c',
    'AMARILLO': '#f39c12',
    'VERDE':    '#2ecc71',
    'GRIS':     '#95a5a6',
    'NORMAL':   '#2ecc71',
    'PRECAUCION':'#f39c12',
    'CRITICO':  '#e74c3c',
}

# Íconos de estado
ICONOS = {
    'ROJO':     '🔴',
    'AMARILLO': '🟡',
    'VERDE':    '🟢',
    'GRIS':     '⚪',
    'CRITICO':  '🚨',
    'PRECAUCION':'⚠️',
    'NORMAL':   '✅',
}

# Variables a mostrar en los gráficos (orden de importancia)
VARS_DISPLAY = {
    'TBN (mg KOH/g)':         {'label': 'TBN',          'unidad': 'mg KOH/g', 'icono': '🛡️'},
    'Hollin ABS/01 mm':        {'label': 'Hollín',        'unidad': 'ABS/0.1mm','icono': '💨'},
    'Fierro ppm':              {'label': 'Hierro (Fe)',   'unidad': 'ppm',      'icono': '⚙️'},
    'Viscosidad a 100 °C cSt': {'label': 'Viscosidad',   'unidad': 'cSt',      'icono': '💧'},
    'Oxidación ABS/01 mm':     {'label': 'Oxidación',    'unidad': 'ABS/0.1mm','icono': '🔥'},
    'Cobre ppm':               {'label': 'Cobre (Cu)',   'unidad': 'ppm',      'icono': '🔩'},
    'Potasio ppm':             {'label': 'Potasio (K)',  'unidad': 'ppm',      'icono': '💦'},
    'Silicio ppm':             {'label': 'Silicio (Si)', 'unidad': 'ppm',      'icono': '🏔️'},
}

LIMITES = {
    'TBN (mg KOH/g)':         {'precaucion': 8.0,  'critico': 7.5,  'dir': 'lower'},
    'Viscosidad a 100 °C cSt': {'precaucion': 13.0, 'critico': 12.5, 'dir': 'lower'},
    'Hollin ABS/01 mm':        {'precaucion': 0.70, 'critico': 1.00, 'dir': 'upper'},
    'Fierro ppm':              {'precaucion': 30,   'critico': 50,   'dir': 'upper'},
    'Cobre ppm':               {'precaucion': 10,   'critico': 20,   'dir': 'upper'},
    'Silicio ppm':             {'precaucion': 15,   'critico': 25,   'dir': 'upper'},
    'Potasio ppm':             {'precaucion': 3,    'critico': 5,    'dir': 'upper'},
    'Oxidación ABS/01 mm':     {'precaucion': 0.10, 'critico': 0.15, 'dir': 'upper'},
}
```

---

## COMPONENTES REUTILIZABLES

### `frontend/components/semaforo.py`

```python
import streamlit as st
from frontend.config import COLORES, ICONOS

def render_semaforo(nivel: str, mensaje: str = "", size: str = "grande"):
    """
    Renderiza un semáforo visual con el nivel de alerta.
    size: 'grande' para vista de equipo, 'pequeño' para tabla de flota.
    """
    color = COLORES.get(nivel, COLORES['GRIS'])
    icono = ICONOS.get(nivel, '⚪')

    if size == "grande":
        st.markdown(f"""
        <div style="
            background-color: {color};
            border-radius: 16px;
            padding: 20px 30px;
            text-align: center;
            margin: 10px 0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        ">
            <h1 style="color: white; margin: 0; font-size: 3em;">{icono}</h1>
            <h2 style="color: white; margin: 5px 0; font-weight: bold;">{nivel}</h2>
            <p style="color: rgba(255,255,255,0.9); margin: 5px 0; font-size: 0.9em;">{mensaje[:120]}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(
            f'<span style="background:{color}; color:white; padding:3px 10px; '
            f'border-radius:8px; font-weight:bold;">{icono} {nivel}</span>',
            unsafe_allow_html=True
        )


def render_card_metrica(titulo: str, valor, unidad: str = "",
                        nivel: str = "NORMAL", delta=None):
    """
    Tarjeta de métrica con color según nivel de alerta.
    """
    color = COLORES.get(nivel, '#3498db')
    valor_str = f"{valor:.3f}" if isinstance(valor, float) else str(valor)
    delta_str = f'<small style="color:{"red" if delta and delta > 0 else "green"}">{"▲" if delta and delta > 0 else "▼"} {abs(delta):.3f}</small>' if delta is not None else ""

    st.markdown(f"""
    <div style="
        border-left: 5px solid {color};
        background: #f8f9fa;
        padding: 12px 16px;
        border-radius: 8px;
        margin: 4px 0;
    ">
        <p style="color: #666; margin: 0; font-size: 0.8em; font-weight: 600; text-transform: uppercase;">{titulo}</p>
        <p style="color: #1a1a2e; margin: 4px 0; font-size: 1.6em; font-weight: bold;">
            {valor_str} <small style="font-size:0.5em; color:#888;">{unidad}</small>
        </p>
        {delta_str}
    </div>
    """, unsafe_allow_html=True)
```

### `frontend/components/gauge_chart.py`

```python
import plotly.graph_objects as go
from frontend.config import LIMITES, VARS_DISPLAY

def render_gauge(variable: str, valor_actual: float, valor_predicho: float = None):
    """
    Gauge (velocímetro) para una variable analítica.
    Muestra el valor actual con zonas de color: verde/amarillo/rojo.
    """
    if variable not in LIMITES:
        return None

    lim = LIMITES[variable]
    info = VARS_DISPLAY.get(variable, {'label': variable, 'unidad': ''})
    p = lim['precaucion']
    c = lim['critico']
    es_lower = lim['dir'] == 'lower'

    # Rango del gauge
    if es_lower:
        range_min = min(c * 0.7, valor_actual * 0.9 if valor_actual else c * 0.7)
        range_max = max(p * 1.3, valor_actual * 1.1 if valor_actual else p * 1.3)
        steps = [
            {'range': [range_min, c], 'color': '#fadbd8'},   # rojo pálido
            {'range': [c, p],         'color': '#fdebd0'},   # naranja pálido
            {'range': [p, range_max], 'color': '#d5f5e3'},   # verde pálido
        ]
    else:
        range_min = 0
        range_max = max(c * 1.5, valor_actual * 1.2 if valor_actual else c * 1.5)
        steps = [
            {'range': [0, p],          'color': '#d5f5e3'},  # verde pálido
            {'range': [p, c],          'color': '#fdebd0'},  # naranja pálido
            {'range': [c, range_max],  'color': '#fadbd8'},  # rojo pálido
        ]

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta" if valor_predicho else "gauge+number",
        value=valor_actual if valor_actual is not None else 0,
        delta={'reference': valor_predicho, 'valueformat': '.3f'} if valor_predicho else None,
        title={'text': f"{info['label']}<br><span style='font-size:0.7em'>{info['unidad']}</span>"},
        gauge={
            'axis': {'range': [range_min, range_max], 'tickwidth': 1},
            'bar': {'color': '#2c3e50', 'thickness': 0.25},
            'steps': steps,
            'threshold': {
                'line': {'color': '#e74c3c', 'width': 3},
                'thickness': 0.8,
                'value': c,
            },
        },
        number={'valueformat': '.3f', 'font': {'size': 20}},
    ))

    fig.update_layout(
        height=220,
        margin=dict(l=10, r=10, t=50, b=10),
        font={'family': 'Arial'},
    )
    return fig


### `frontend/components/degradacion_chart.py`

import plotly.graph_objects as go
import pandas as pd
from frontend.config import COLORES, LIMITES

def render_curva_degradacion(historial: list, variable: str,
                              valor_predicho: float = None):
    """
    Gráfico de línea de la evolución de una variable en el tiempo.
    Eje X: Hora_Producto. Colores por estado. Líneas de límite.
    Muestra el punto predicho (t+1) con un marcador especial.
    """
    if not historial:
        return None

    df = pd.DataFrame(historial)
    if variable not in df.columns or 'Hora_Producto' not in df.columns:
        return None

    df = df.dropna(subset=[variable, 'Hora_Producto'])
    df['Hora_Producto'] = pd.to_numeric(df['Hora_Producto'], errors='coerce')
    df = df.sort_values('Hora_Producto')

    fig = go.Figure()

    # Trazar puntos por estado con colores
    for estado, color in [('NORMAL', '#2ecc71'), ('PRECAUCION', '#f39c12'), ('CRITICO', '#e74c3c')]:
        mask = df['Estado'] == estado
        if mask.sum() > 0:
            fig.add_trace(go.Scatter(
                x=df.loc[mask, 'Hora_Producto'],
                y=df.loc[mask, variable],
                mode='markers',
                name=estado,
                marker=dict(color=color, size=7, opacity=0.8),
                hovertemplate=(
                    f'<b>{estado}</b><br>'
                    'Horas: %{x:.0f}h<br>'
                    f'{variable}: %{{y:.4f}}<extra></extra>'
                )
            ))

    # Línea de tendencia suavizada
    if len(df) >= 3:
        rolling = df[variable].rolling(window=5, min_periods=2, center=True).mean()
        fig.add_trace(go.Scatter(
            x=df['Hora_Producto'], y=rolling,
            mode='lines', name='Tendencia',
            line=dict(color='#2c3e50', width=2, dash='dot'),
            opacity=0.7,
        ))

    # Punto predicho t+1
    if valor_predicho is not None:
        hora_siguiente = df['Hora_Producto'].max() + df['Hora_Producto'].diff().median()
        fig.add_trace(go.Scatter(
            x=[hora_siguiente], y=[valor_predicho],
            mode='markers',
            name='Predicción t+1',
            marker=dict(
                symbol='star', size=16, color='#9b59b6',
                line=dict(color='white', width=2)
            ),
            hovertemplate=f'<b>Predicción t+1</b><br>Horas: {hora_siguiente:.0f}h<br>{variable}: {valor_predicho:.4f}<extra></extra>',
        ))

    # Líneas de límite
    if variable in LIMITES:
        lim = LIMITES[variable]
        fig.add_hline(y=lim['precaucion'], line_color='#f39c12',
                      line_dash='dash', line_width=1.5,
                      annotation_text='Límite precaución', annotation_position='top right')
        fig.add_hline(y=lim['critico'], line_color='#e74c3c',
                      line_dash='dash', line_width=1.5,
                      annotation_text='Límite crítico', annotation_position='top right')

    fig.update_layout(
        title=dict(text=f'Evolución: {variable}', font=dict(size=13)),
        xaxis_title='Horas de Producto',
        yaxis_title=variable,
        height=350,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=40, r=20, t=60, b=40),
        hovermode='x unified',
        plot_bgcolor='#fafafa',
    )
    return fig
```

---

## PÁGINA PRINCIPAL: `frontend/app.py`

```python
import streamlit as st

st.set_page_config(
    page_title="SaaS Aceites 794AC — Quellaveco",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Estilos globales ────────────────────────────────────────────────
st.markdown("""
<style>
    /* Fondo general */
    .stApp { background-color: #f0f2f6; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    [data-testid="stSidebar"] * { color: white !important; }

    /* Cards */
    div[data-testid="metric-container"] {
        background: white;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }

    /* Títulos */
    h1 { color: #1a1a2e; font-weight: 800; }
    h2 { color: #2c3e50; }
    h3 { color: #34495e; }
</style>
""", unsafe_allow_html=True)

# ── Header principal ────────────────────────────────────────────────
col_logo, col_titulo = st.columns([1, 6])
with col_logo:
    st.markdown("# ⛏️")
with col_titulo:
    st.markdown("# SaaS Predictivo de Aceites")
    st.markdown("**Flota 794AC — Mina Quellaveco** | Motor Predictivo v1.0")

st.divider()

# ── Contenido de bienvenida ─────────────────────────────────────────
st.markdown("""
### Bienvenido al sistema de monitoreo predictivo

Este sistema analiza las muestras de aceite de la flota de camiones **Caterpillar 794AC**
y predice el estado futuro de cada equipo utilizando modelos de Machine Learning.

#### ¿Qué puedes hacer aquí?

| Página | Descripción |
|--------|-------------|
| 🚛 **Flota Completa** | Dashboard con el estado de todos los camiones en tiempo real |
| 🔍 **Análisis por Equipo** | Curvas de degradación, predicciones y alertas individuales |
| ➕ **Registrar Muestra** | Ingresar una nueva muestra de aceite y ver la predicción |
| 📊 **Reportes** | Exportar informes de estado y predicciones |

#### Sistema de alertas
""")

col1, col2, col3 = st.columns(3)
with col1:
    st.error("🔴 **ROJO — CRÍTICO**\nIntervención inmediata requerida")
with col2:
    st.warning("🟡 **AMARILLO — PRECAUCIÓN**\nMonitoreo intensivo recomendado")
with col3:
    st.success("🟢 **VERDE — NORMAL**\nOperación dentro de parámetros")
```

---

## PÁGINA 1: `frontend/pages/01_flota.py`

```python
import streamlit as st
import requests
import pandas as pd
from frontend.config import API_BASE_URL, COLORES, ICONOS
from frontend.components.semaforo import render_semaforo

st.set_page_config(page_title="Flota Completa", page_icon="🚛", layout="wide")
st.title("🚛 Estado de la Flota Completa")

# ── Obtener datos de la API ─────────────────────────────────────────
@st.cache_data(ttl=300)  # Cachear 5 minutos
def cargar_flota():
    try:
        r = requests.get(f"{API_BASE_URL}/flota/resumen", timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return None

with st.spinner("Cargando estado de la flota..."):
    datos = cargar_flota()

if datos is None:
    st.error("❌ No se pudo conectar con el backend. Verifica que la API esté corriendo en `localhost:8000`.")
    st.stop()

# ── KPIs principales ────────────────────────────────────────────────
st.markdown("### Resumen Ejecutivo")
col1, col2, col3, col4 = st.columns(4)
col1.metric("🚛 Total Equipos",   datos['total_equipos'])
col2.metric("🔴 En Alerta ROJA",  datos['equipos_rojo'],    delta=None)
col3.metric("🟡 En PRECAUCIÓN",   datos['equipos_amarillo'])
col4.metric("🟢 En NORMAL",       datos['equipos_verde'])

# Barra de progreso visual de la distribución de alertas
total = datos['total_equipos']
if total > 0:
    st.markdown("##### Distribución de alertas en la flota")
    pct_rojo    = datos['equipos_rojo'] / total
    pct_amarillo = datos['equipos_amarillo'] / total
    pct_verde   = datos['equipos_verde'] / total
    st.markdown(f"""
    <div style="display:flex; height:30px; border-radius:8px; overflow:hidden; margin:10px 0;">
        <div style="width:{pct_rojo*100:.1f}%; background:#e74c3c; display:flex; align-items:center;
                    justify-content:center; color:white; font-size:0.8em; font-weight:bold;">
            {pct_rojo*100:.0f}%
        </div>
        <div style="width:{pct_amarillo*100:.1f}%; background:#f39c12; display:flex; align-items:center;
                    justify-content:center; color:white; font-size:0.8em; font-weight:bold;">
            {pct_amarillo*100:.0f}%
        </div>
        <div style="width:{pct_verde*100:.1f}%; background:#2ecc71; display:flex; align-items:center;
                    justify-content:center; color:white; font-size:0.8em; font-weight:bold;">
            {pct_verde*100:.0f}%
        </div>
    </div>
    <small>🔴 Crítico &nbsp;&nbsp; 🟡 Precaución &nbsp;&nbsp; 🟢 Normal</small>
    """, unsafe_allow_html=True)

st.divider()

# ── Tabla de equipos con filtros ────────────────────────────────────
st.markdown("### Estado por Equipo")

col_filtro1, col_filtro2 = st.columns([1, 3])
with col_filtro1:
    filtro_alerta = st.multiselect(
        "Filtrar por alerta:",
        options=['ROJO', 'AMARILLO', 'VERDE'],
        default=['ROJO', 'AMARILLO', 'VERDE']
    )
with col_filtro2:
    ordenar_por = st.selectbox(
        "Ordenar por:",
        options=['Nivel de alerta', 'Horas hasta crítico', 'Horas acumuladas', '% muestras críticas']
    )

equipos = datos['equipos']
if filtro_alerta:
    equipos = [e for e in equipos if e.get('nivel_alerta') in filtro_alerta]

# Ordenar
orden_map = {
    'Nivel de alerta': lambda x: {'ROJO': 0, 'AMARILLO': 1, 'VERDE': 2, None: 3}.get(x.get('nivel_alerta'), 3),
    'Horas hasta crítico': lambda x: x.get('horas_hasta_critico') or 9999,
    'Horas acumuladas': lambda x: -(x.get('ultima_hora_producto') or 0),
    '% muestras críticas': lambda x: -(x.get('pct_muestras_criticas') or 0),
}
equipos_ordenados = sorted(equipos, key=orden_map[ordenar_por])

# Renderizar tarjetas de equipos en grid 4 columnas
cols_per_row = 4
for i in range(0, len(equipos_ordenados), cols_per_row):
    cols = st.columns(cols_per_row)
    for j, equipo in enumerate(equipos_ordenados[i:i+cols_per_row]):
        with cols[j]:
            nivel = equipo.get('nivel_alerta', 'GRIS')
            color = COLORES.get(nivel, '#95a5a6')
            icono = ICONOS.get(nivel, '⚪')
            estado_pred = equipo.get('estado_predicho', 'N/A')
            horas = equipo.get('ultima_hora_producto', 0) or 0
            h_critico = equipo.get('horas_hasta_critico')
            h_critico_str = f"{h_critico:.0f}h" if h_critico else "N/A"

            st.markdown(f"""
            <div style="
                border: 2px solid {color};
                border-radius: 12px;
                padding: 14px;
                margin: 4px 0;
                background: white;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            ">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <b style="font-size:1.1em; color:#1a1a2e;">{equipo['equipo']}</b>
                    <span style="background:{color}; color:white; padding:2px 8px;
                                 border-radius:6px; font-size:0.75em; font-weight:bold;">
                        {icono} {nivel}
                    </span>
                </div>
                <hr style="margin:8px 0; border-color:#eee;">
                <small style="color:#555;">
                    ⏱ <b>{horas:.0f}h</b> acumuladas &nbsp;|&nbsp;
                    🔮 <b>{estado_pred}</b><br>
                    ⏳ Hasta crítico: <b>{h_critico_str}</b><br>
                    📊 {equipo.get('n_muestras', 0)} muestras
                    ({equipo.get('pct_muestras_criticas', 0):.0f}% críticas)
                </small>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Ver {equipo['equipo']}", key=f"btn_{equipo['equipo']}", use_container_width=True):
                st.session_state['equipo_seleccionado'] = equipo['equipo']
                st.switch_page("pages/02_equipo.py")

# ── Tabla resumen exportable ────────────────────────────────────────
st.divider()
st.markdown("### Tabla de datos completa")

df_tabla = pd.DataFrame([{
    'Equipo': e['equipo'],
    'Alerta': e.get('nivel_alerta', 'N/A'),
    'Estado actual': e.get('estado_actual', 'N/A'),
    'Predicción t+1': e.get('estado_predicho', 'N/A'),
    'Horas acum.': e.get('ultima_hora_producto', 0),
    'Horas hasta crítico': e.get('horas_hasta_critico', None),
    'TBN último': e.get('tbn_ultimo', None),
    'Hollín último': e.get('hollin_ultimo', None),
    'Hierro último': e.get('fierro_ultimo', None),
    '% Muestras críticas': e.get('pct_muestras_criticas', 0),
    'N° muestras': e.get('n_muestras', 0),
} for e in equipos_ordenados])

st.dataframe(df_tabla, use_container_width=True, hide_index=True,
             column_config={
                 'Alerta': st.column_config.TextColumn('Alerta'),
                 'Horas hasta crítico': st.column_config.NumberColumn(format='%.0f h'),
                 'Horas acum.': st.column_config.NumberColumn(format='%.0f h'),
                 '% Muestras críticas': st.column_config.ProgressColumn(min_value=0, max_value=100, format='%.1f%%'),
             })

csv = df_tabla.to_csv(index=False).encode('utf-8')
st.download_button("⬇️ Exportar tabla CSV", data=csv,
                   file_name="flota_794AC_estado.csv", mime='text/csv')
```

---

## PÁGINA 2: `frontend/pages/02_equipo.py`

```python
import streamlit as st
import requests
import pandas as pd
from frontend.config import API_BASE_URL, VARS_DISPLAY, LIMITES, COLORES
from frontend.components.semaforo import render_semaforo, render_card_metrica
from frontend.components.gauge_chart import render_gauge
from frontend.components.degradacion_chart import render_curva_degradacion

st.set_page_config(page_title="Análisis por Equipo", page_icon="🔍", layout="wide")
st.title("🔍 Análisis Detallado por Equipo")

# ── Selección de equipo ─────────────────────────────────────────────
@st.cache_data(ttl=60)
def cargar_equipos():
    try:
        r = requests.get(f"{API_BASE_URL}/equipos", timeout=10)
        return r.json().get('equipos', [])
    except:
        return []

equipos_disponibles = cargar_equipos()
default_idx = 0
if 'equipo_seleccionado' in st.session_state:
    try:
        default_idx = equipos_disponibles.index(st.session_state['equipo_seleccionado'])
    except ValueError:
        default_idx = 0

equipo_sel = st.selectbox("Selecciona el equipo:", equipos_disponibles, index=default_idx)

if not equipo_sel:
    st.info("Selecciona un equipo para ver su análisis.")
    st.stop()

# ── Cargar predicción e historial ──────────────────────────────────
@st.cache_data(ttl=120)
def cargar_prediccion(equipo):
    try:
        r = requests.get(f"{API_BASE_URL}/equipos/{equipo}/prediccion", timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {'error': str(e)}

@st.cache_data(ttl=120)
def cargar_historial(equipo):
    try:
        r = requests.get(f"{API_BASE_URL}/equipos/{equipo}/historial", timeout=30)
        r.raise_for_status()
        return r.json().get('muestras', [])
    except:
        return []

with st.spinner(f"Cargando datos de {equipo_sel}..."):
    pred = cargar_prediccion(equipo_sel)
    historial = cargar_historial(equipo_sel)

if 'error' in pred:
    st.error(f"Error: {pred['error']}")
    st.stop()

# ── Header del equipo ───────────────────────────────────────────────
col_semaforo, col_info = st.columns([1, 3])

with col_semaforo:
    render_semaforo(pred.get('nivel_alerta', 'GRIS'),
                    pred.get('mensaje_alerta', ''),
                    size="grande")

with col_info:
    st.markdown(f"## Camión **{equipo_sel}**")
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Estado actual",    pred.get('estado_actual', 'N/A'))
    col_b.metric("Predicción t+1",   pred.get('estado_predicho', 'N/A'))
    col_c.metric("Horas acumuladas", f"{pred.get('hora_actual', 0):.0f}h")

    horas_critico = pred.get('horas_hasta_critico')
    col_d.metric(
        "Horas hasta crítico",
        f"{horas_critico:.0f}h" if horas_critico else "N/A",
        delta=None
    )

    # Barra de confianza del modelo
    confianza = pred.get('confianza_modelo', 'BAJA')
    color_conf = {'ALTA': 'green', 'MEDIA': 'orange', 'BAJA': 'red'}.get(confianza, 'gray')
    st.markdown(f"Confianza del modelo: :{color_conf}[**{confianza}**] "
                f"(basado en {pred.get('n_muestras_historial', 0)} muestras)")

    # Probabilidades del clasificador
    probs = pred.get('probabilidades', {})
    if probs:
        st.markdown("**Probabilidades del clasificador:**")
        prob_cols = st.columns(3)
        for i, (estado, prob) in enumerate(probs.items()):
            color_e = {'CRITICO': '#e74c3c', 'PRECAUCION': '#f39c12', 'NORMAL': '#2ecc71'}.get(estado, '#888')
            prob_cols[i].markdown(
                f'<div style="background:{color_e}22; border:1px solid {color_e}; '
                f'border-radius:8px; padding:8px; text-align:center;">'
                f'<b>{estado}</b><br><span style="font-size:1.5em;font-weight:bold;">{prob*100:.1f}%</span>'
                f'</div>', unsafe_allow_html=True
            )

st.divider()

# ── Alertas de variables ────────────────────────────────────────────
alertas = pred.get('alertas_variables', [])
if alertas:
    st.markdown("### ⚠️ Variables fuera de límites")
    for alerta in alertas:
        nivel_a = alerta['nivel']
        if nivel_a == 'CRITICO':
            st.error(f"🚨 **{alerta['variable']}**: {alerta['valor_actual']:.4f} "
                     f"(límite crítico: {alerta['limite_critico']})")
        else:
            st.warning(f"⚠️ **{alerta['variable']}**: {alerta['valor_actual']:.4f} "
                       f"(límite precaución: {alerta['limite_precaucion']})")

# ── Gauges de variables clave ───────────────────────────────────────
st.markdown("### 📊 Estado actual de variables analíticas")
vars_actuales  = pred.get('valores_actuales', {})
vars_predichos = pred.get('valores_predichos', {})

gauge_vars = [v for v in VARS_DISPLAY.keys() if v in LIMITES and vars_actuales.get(v) is not None]
cols_gauge = st.columns(min(4, len(gauge_vars)))

for idx, var in enumerate(gauge_vars[:8]):
    with cols_gauge[idx % 4]:
        val_actual = vars_actuales.get(var)
        val_pred   = vars_predichos.get(var)
        if val_actual is not None:
            fig = render_gauge(var, float(val_actual), float(val_pred) if val_pred else None)
            if fig:
                st.plotly_chart(fig, use_container_width=True, key=f"gauge_{var}_{equipo_sel}")

# ── Curvas de degradación ───────────────────────────────────────────
st.divider()
st.markdown("### 📈 Curvas de degradación (histórico completo)")

vars_graficar = st.multiselect(
    "Variables a graficar:",
    options=list(VARS_DISPLAY.keys()),
    default=list(VARS_DISPLAY.keys())[:4]
)

cols_graf = st.columns(2)
for idx, var in enumerate(vars_graficar):
    with cols_graf[idx % 2]:
        val_pred = vars_predichos.get(var)
        fig = render_curva_degradacion(historial, var, float(val_pred) if val_pred else None)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key=f"deg_{var}_{equipo_sel}")

# ── Tabla de historial ──────────────────────────────────────────────
st.divider()
with st.expander("📋 Ver historial completo de muestras"):
    if historial:
        df_hist = pd.DataFrame(historial)
        cols_mostrar = ['Fecha', 'Hora_Producto', 'Estado'] + [
            v for v in VARS_DISPLAY.keys() if v in df_hist.columns
        ]
        cols_mostrar = [c for c in cols_mostrar if c in df_hist.columns]
        st.dataframe(df_hist[cols_mostrar].sort_values('Hora_Producto', ascending=False),
                     use_container_width=True, hide_index=True)
    else:
        st.info("Sin historial disponible.")
```

---

## PÁGINA 3: `frontend/pages/03_nueva_muestra.py`

```python
import streamlit as st
import requests
from datetime import date
from frontend.config import API_BASE_URL
from frontend.components.semaforo import render_semaforo

st.set_page_config(page_title="Registrar Muestra", page_icon="➕", layout="wide")
st.title("➕ Registrar Nueva Muestra de Aceite")
st.markdown("Ingresa los datos del análisis de aceite para generar una predicción inmediata.")

@st.cache_data(ttl=60)
def cargar_equipos():
    try:
        r = requests.get(f"{API_BASE_URL}/equipos", timeout=10)
        return r.json().get('equipos', [])
    except:
        return []

equipos = cargar_equipos()

# ── Formulario de ingreso ───────────────────────────────────────────
with st.form("form_nueva_muestra", clear_on_submit=False):
    st.markdown("#### Datos de identificación")
    col1, col2, col3 = st.columns(3)
    equipo = col1.selectbox("🚛 Equipo *", equipos)
    fecha  = col2.date_input("📅 Fecha de muestra *", value=date.today())
    hora_producto = col3.number_input("⏱ Horas de producto *", min_value=0.0,
                                       max_value=1000.0, value=300.0, step=1.0)

    st.markdown("#### Variables analíticas del aceite")
    st.info("💡 Puedes dejar campos en blanco si no tienes el dato — el modelo usará el historial previo.")

    col_a, col_b, col_c, col_d = st.columns(4)
    tbn           = col_a.number_input("TBN (mg KOH/g)", min_value=0.0, max_value=20.0, value=8.5, step=0.01)
    viscosidad    = col_b.number_input("Viscosidad 100°C (cSt)", min_value=5.0, max_value=25.0, value=13.5, step=0.01)
    hollin        = col_c.number_input("Hollín (ABS/0.1mm)", min_value=0.0, max_value=2.0, value=0.5, step=0.001)
    fierro        = col_d.number_input("Hierro (ppm)", min_value=0.0, max_value=300.0, value=15.0, step=0.1)

    col_e, col_f, col_g, col_h = st.columns(4)
    oxidacion     = col_e.number_input("Oxidación (ABS/0.1mm)", min_value=0.0, max_value=1.0, value=0.03, step=0.001)
    sulfatacion   = col_f.number_input("Sulfatación (ABS/0.1mm)", min_value=0.0, max_value=1.0, value=0.02, step=0.001)
    cobre         = col_g.number_input("Cobre (ppm)", min_value=0.0, max_value=100.0, value=1.0, step=0.1)
    potasio       = col_h.number_input("Potasio (ppm)", min_value=0.0, max_value=200.0, value=0.5, step=0.1)

    col_i, col_j, _, _ = st.columns(4)
    silicio       = col_i.number_input("Silicio (ppm)", min_value=0.0, max_value=200.0, value=8.0, step=0.1)
    aluminio      = col_j.number_input("Aluminio (ppm)", min_value=0.0, max_value=100.0, value=1.0, step=0.1)

    observacion   = st.text_area("📝 Observación del analista (opcional)", height=80)

    submitted = st.form_submit_button("🔮 Registrar y Predecir", use_container_width=True, type="primary")

# ── Procesar envío ──────────────────────────────────────────────────
if submitted:
    payload = {
        "fecha":         str(fecha),
        "hora_producto": hora_producto,
        "tbn":           tbn,
        "viscosidad_100":viscosidad,
        "hollin":        hollin,
        "fierro":        fierro,
        "oxidacion":     oxidacion,
        "sulfatacion":   sulfatacion,
        "cobre":         cobre,
        "potasio":       potasio,
        "silicio":       silicio,
        "aluminio":      aluminio,
        "observacion":   observacion,
    }

    with st.spinner("Registrando muestra y generando predicción..."):
        try:
            r = requests.post(
                f"{API_BASE_URL}/equipos/{equipo}/muestras",
                json=payload, timeout=30
            )
            r.raise_for_status()
            resultado = r.json()

            st.success(f"✅ {resultado['mensaje']}")
            pred = resultado.get('prediccion', {})

            if pred:
                st.divider()
                st.markdown(f"## Resultado de Predicción — {equipo}")

                col_sem, col_res = st.columns([1, 2])
                with col_sem:
                    render_semaforo(pred.get('nivel_alerta', 'GRIS'),
                                    pred.get('mensaje_alerta', ''),
                                    size="grande")
                with col_res:
                    c1, c2 = st.columns(2)
                    c1.metric("Estado predicho (t+1)", pred.get('estado_predicho'))
                    c2.metric("Horas hasta crítico",
                              f"{pred.get('horas_hasta_critico', 0):.0f}h"
                              if pred.get('horas_hasta_critico') else "N/A")
                    st.markdown("**Probabilidades:**")
                    probs = pred.get('probabilidades', {})
                    for estado, prob in probs.items():
                        color = {'CRITICO': '#e74c3c', 'PRECAUCION': '#f39c12', 'NORMAL': '#2ecc71'}.get(estado)
                        st.markdown(f"- **{estado}**: {prob*100:.1f}%")

                st.markdown("#### Valores predichos para la próxima muestra (t+1):")
                vals_pred = pred.get('valores_predichos', {})
                cols_pred = st.columns(4)
                for idx, (var, val) in enumerate(vals_pred.items()):
                    if val is not None:
                        cols_pred[idx % 4].metric(var[:20], f"{val:.4f}")

        except requests.exceptions.ConnectionError:
            st.error("❌ No se puede conectar con el backend. Verifica que la API esté corriendo.")
        except Exception as e:
            st.error(f"Error: {e}")
```

---

## PÁGINA 4: `frontend/pages/04_reportes.py`

```python
import streamlit as st
import requests
import pandas as pd
from datetime import date, timedelta
from io import BytesIO
from frontend.config import API_BASE_URL, VARS_DISPLAY

st.set_page_config(page_title="Reportes", page_icon="📊", layout="wide")
st.title("📊 Reportes y Exportaciones")

@st.cache_data(ttl=60)
def cargar_equipos():
    try:
        r = requests.get(f"{API_BASE_URL}/equipos", timeout=10)
        return r.json().get('equipos', [])
    except:
        return []

equipos = cargar_equipos()

tab1, tab2 = st.tabs(["📋 Reporte de Flota", "🔍 Reporte por Equipo"])

with tab1:
    st.markdown("### Reporte consolidado de la flota")
    if st.button("🔄 Generar reporte de flota", type="primary"):
        with st.spinner("Generando reporte..."):
            try:
                r = requests.get(f"{API_BASE_URL}/flota/resumen", timeout=60)
                datos = r.json()
                df_reporte = pd.DataFrame([{
                    'Equipo': e['equipo'],
                    'Nivel Alerta': e.get('nivel_alerta'),
                    'Estado actual': e.get('estado_actual'),
                    'Predicción t+1': e.get('estado_predicho'),
                    'Horas acumuladas': e.get('ultima_hora_producto'),
                    'Horas hasta crítico': e.get('horas_hasta_critico'),
                    'TBN último': e.get('tbn_ultimo'),
                    'Hollín último': e.get('hollin_ultimo'),
                    'Hierro último': e.get('fierro_ultimo'),
                    '% Muestras críticas': e.get('pct_muestras_criticas'),
                    'N° muestras totales': e.get('n_muestras'),
                    'Última muestra': e.get('ultima_muestra_fecha'),
                } for e in datos['equipos']])

                st.dataframe(df_reporte, use_container_width=True, hide_index=True)

                # Exportar a Excel
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_reporte.to_excel(writer, sheet_name='Estado_Flota', index=False)
                buffer.seek(0)
                st.download_button(
                    "⬇️ Descargar reporte Excel",
                    data=buffer,
                    file_name=f"reporte_flota_794AC_{date.today()}.xlsx",
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            except Exception as e:
                st.error(f"Error generando reporte: {e}")

with tab2:
    st.markdown("### Reporte detallado por equipo")
    equipo_reporte = st.selectbox("Selecciona equipo:", equipos, key="eq_reporte")

    if equipo_reporte and st.button("🔄 Generar reporte del equipo", type="primary"):
        with st.spinner(f"Generando reporte de {equipo_reporte}..."):
            try:
                r_hist = requests.get(f"{API_BASE_URL}/equipos/{equipo_reporte}/historial", timeout=30)
                r_pred = requests.get(f"{API_BASE_URL}/equipos/{equipo_reporte}/prediccion", timeout=30)

                historial = r_hist.json().get('muestras', [])
                pred = r_pred.json()

                df_hist = pd.DataFrame(historial)

                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_hist.to_excel(writer, sheet_name='Historial_Completo', index=False)
                    pd.DataFrame([{
                        'Equipo': equipo_reporte,
                        'Estado actual': pred.get('estado_actual'),
                        'Estado predicho t+1': pred.get('estado_predicho'),
                        'Nivel alerta': pred.get('nivel_alerta'),
                        'Horas acumuladas': pred.get('hora_actual'),
                        'Horas hasta crítico': pred.get('horas_hasta_critico'),
                        'Confianza modelo': pred.get('confianza_modelo'),
                    }]).to_excel(writer, sheet_name='Prediccion_Actual', index=False)

                buffer.seek(0)
                st.success(f"✅ Reporte de {equipo_reporte} listo.")
                st.download_button(
                    f"⬇️ Descargar reporte {equipo_reporte}",
                    data=buffer,
                    file_name=f"reporte_{equipo_reporte}_{date.today()}.xlsx",
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            except Exception as e:
                st.error(f"Error: {e}")
```

---

## CÓMO EJECUTAR EL FRONTEND

Crear el archivo `run_frontend.py` en la raíz del proyecto:
```python
import subprocess
subprocess.run(["streamlit", "run", "frontend/app.py", "--server.port=8501"])
```

O directamente desde terminal:
```bash
streamlit run frontend/app.py --server.port 8501
```

El dashboard estará disponible en: **`http://localhost:8501`**

---

## NOTAS FINALES PARA CURSOR

1. **Crear `frontend/__init__.py`** vacío para que Python reconozca el módulo.

2. **Orden de ejecución:**
   ```
   # Terminal 1 — Backend
   python run_backend.py

   # Terminal 2 — Frontend
   streamlit run frontend/app.py
   ```

3. **Caché de Streamlit**: `@st.cache_data(ttl=300)` cachea las respuestas 5 minutos.
   Para forzar recarga: presionar `R` en el navegador o el botón de rerun.

4. **Si el backend no está disponible**, el frontend debe mostrar mensajes de error claros
   (ya implementado con los `try/except` en cada llamada).

5. **Paleta de colores industrial**: predominan `#1a1a2e` (azul oscuro), `#e74c3c` (rojo),
   `#f39c12` (naranja), `#2ecc71` (verde). Evitar colores brillantes que cansen la vista.

6. **Para producción futura**: agregar autenticación con `streamlit-authenticator` y
   cambiar `allow_origins=["*"]` en el backend por el dominio real del frontend.
