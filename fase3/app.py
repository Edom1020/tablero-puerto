"""
Fase 3: Tablero de control del Puerto de Cartagena.

Ejecutar con:  streamlit run app.py
Lee el CSV limpio que produce la Fase 2 (datos_puerto_limpios.csv).
"""
from pathlib import Path
import base64
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import io
from PIL import Image

# ---------------------------------------------------------------------------
# Parámetros del negocio (acordados en la Fase 1)
# ---------------------------------------------------------------------------
NUM_MUELLES = 10
UMBRAL_AMARILLO_H = 3
UMBRAL_ROJO_H = 4

# Colores: un solo azul para magnitudes; rojo y amarillo reservados para alertas
AZUL = "#2a78d6"
AZUL_OSCURO = "#184f95"
GRIS = "#8a8983"
ROJO_ALERTA = "#d03b3b"
AMARILLO_ALERTA = "#fab219"
ESCALA_AZUL = ["#e6f0fc", "#9ec5f4", "#5598e7", "#256abf", "#0d366b"]
ORDEN_CLIMA = ["Despejado", "Lluvia Ligera", "Viento Fuerte", "Tormenta"]


RUTA_ANCLA = Path(__file__).resolve().parent / "anchor.png"
ICONO = str(RUTA_ANCLA) if RUTA_ANCLA.exists() else "⚓"

st.set_page_config(page_title="Tablero Puerto de Cartagena", page_icon=ICONO, layout="wide")

CARPETA_APP = Path(__file__).resolve().parent
ICONOS = {"check": ("check.png", "✅"), "amarilla": ("yellow.png", "🟡"), "roja": ("red.png", "🔴"),
          "alerta": ("redalert.png", "🚨"), "foco": ("light.png", "💡")}


def icono_datos(clave):
    ruta = CARPETA_APP / ICONOS[clave][0]
    if not ruta.exists():
        return None
    return "data:image/png;base64," + base64.b64encode(ruta.read_bytes()).decode()


def icono_html(clave, alto=20):
    datos = icono_datos(clave)
    if datos is None:
        return ICONOS[clave][1]
    return f'<img src="{datos}" height="{alto}" style="vertical-align:middle;margin-right:6px">'

def icono_tabla(clave, lienzo=34):
    """Icono para la tabla: Streamlit estira la imagen al alto de la fila, así que se centra
    en un lienzo transparente más grande para que se vea pequeña. Sube `lienzo` para achicarla."""
    ruta = CARPETA_APP / ICONOS[clave][0]
    if not ruta.exists():
        return ICONOS[clave][1]
    img = Image.open(ruta).convert("RGBA")
    fondo = Image.new("RGBA", (lienzo, lienzo), (0, 0, 0, 0))
    fondo.paste(img, ((lienzo - img.width) // 2, (lienzo - img.height) // 2), img)
    buffer = io.BytesIO()
    fondo.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()

def titulo(clave, texto):
    """Subtítulo con icono propio a la izquierda; si no hay imagen, usa el emoji."""
    ruta = CARPETA_APP / ICONOS[clave][0]
    if ruta.exists():
        col_icono, col_texto = st.columns([1, 30], vertical_alignment="center")
        col_icono.image(str(ruta), width=28)
        col_texto.subheader(texto)
    else:
        st.subheader(f"{ICONOS[clave][1]} {texto}")


def aviso(clave, texto_html, fondo, color_texto):
    st.markdown(
        f'<div style="background:{fondo};color:{color_texto};padding:14px 16px;border-radius:8px;'
        f'margin:4px 0 12px 0">{icono_html(clave)} {texto_html}</div>',
        unsafe_allow_html=True,
    )
# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------
@st.cache_data
def cargar_datos():
    aqui = Path(__file__).resolve().parent
    candidatos = [aqui / "datos_puerto_limpios.csv", aqui.parent / "fase2" / "datos_puerto_limpios.csv"]
    ruta = next(p for p in candidatos if p.exists())
    df = pd.read_csv(ruta, parse_dates=["Hora_Llegada", "Hora_Atraque", "Hora_Salida"])
    df["Fecha"] = df["Hora_Llegada"].dt.date
    return df


def estilo(fig, alto=340):
    """Estilo común: fondo limpio, cuadrícula suave y tipografía legible."""
    fig.update_layout(
        height=alto,
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13),
        hoverlabel=dict(font_size=13),
        showlegend=False,
    )
    fig.update_xaxes(showgrid=False, linecolor="#d6d5cf")
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.18)", zeroline=False)
    return fig


def ocupacion_por_hora(datos, inicio, fin):
    """Cuenta cuántos buques están atracados en cada hora del periodo."""
    horas = pd.date_range(pd.Timestamp(inicio), pd.Timestamp(fin) + pd.Timedelta(days=1), freq="h", inclusive="left")
    atraque = datos["Hora_Atraque"].to_numpy()
    salida = datos["Hora_Salida"].to_numpy()
    conteo = [int(((atraque <= h) & (salida > h)).sum()) for h in horas.to_numpy()]
    return pd.DataFrame({"Hora": horas, "Buques_Atracados": conteo})


df = cargar_datos()

# ---------------------------------------------------------------------------
# Encabezado y filtros
# ---------------------------------------------------------------------------

if RUTA_ANCLA.exists():
    col_logo, col_titulo = st.columns([1,12], vertical_alignment="center")
    col_logo.image(str(RUTA_ANCLA),width=70)
    col_titulo.title("Tablero de control · Puerto de Cartagena")
else:
    st.title("⚓ Tablero de control · Puerto de Cartagena")
st.caption(
    f"Atención de buques del {df['Fecha'].min():%d/%m/%Y} al {df['Fecha'].max():%d/%m/%Y} · "
    f"Supuesto: {NUM_MUELLES} muelles · Alerta amarilla > {UMBRAL_AMARILLO_H} h de espera, roja > {UMBRAL_ROJO_H} h"
)

f1, f2, f3 = st.columns([1.2, 1.4, 1.4])
rango = f1.date_input(
    "Rango de fechas", value=(df["Fecha"].min(), df["Fecha"].max()),
    min_value=df["Fecha"].min(), max_value=df["Fecha"].max(), format="DD/MM/YYYY",
)
tipos = f2.multiselect("Tipo de carga", sorted(df["Tipo_Carga"].unique()), placeholder="Todos")
climas = f3.multiselect("Condición climática", [c for c in ORDEN_CLIMA if c in df["Condicion_Climatica"].unique()],
                        placeholder="Todas")

inicio, fin = (rango if isinstance(rango, tuple) and len(rango) == 2 else (df["Fecha"].min(), df["Fecha"].max()))
filtro = (df["Fecha"] >= inicio) & (df["Fecha"] <= fin)
if tipos:
    filtro &= df["Tipo_Carga"].isin(tipos)
if climas:
    filtro &= df["Condicion_Climatica"].isin(climas)
d = df[filtro]

if d.empty:
    st.warning("No hay buques con esos filtros. Amplía el rango de fechas o quita algún filtro.")
    st.stop()

# ---------------------------------------------------------------------------
# KPIs principales
# ---------------------------------------------------------------------------
horas_periodo = ((pd.Timestamp(fin) + pd.Timedelta(days=1)) - pd.Timestamp(inicio)).total_seconds() / 3600
tpe = d["Tiempo_Espera_Horas"].mean()
tpe_global = df["Tiempo_Espera_Horas"].mean()
hay_filtros = bool(tipos or climas) or (inicio, fin) != (df["Fecha"].min(), df["Fecha"].max())
ocupacion = 100 * d["Tiempo_Muelle_Horas"].sum() / (NUM_MUELLES * horas_periodo)
contenedores = d[d["Tipo_Carga"] == "Contenedores"]
eficiencia = contenedores["Eficiencia_TEU_Hora"].mean() if not contenedores.empty else None
rojas = int((d["Nivel_Alerta"] == "Roja").sum())
amarillas = int((d["Nivel_Alerta"] == "Amarilla").sum())

k1, k2, k3, k4 = st.columns(4)
k1.metric(
    "Tiempo Promedio de Espera (TPE)", f"{tpe:.2f} h",
    delta=f"{tpe - tpe_global:+.2f} h vs. total" if hay_filtros else None, delta_color="inverse",
    help="Promedio de horas entre la llegada a la bahía y el atraque. Menos es mejor.",
    border=True,
)
k2.metric(
    "Ocupación de muelles", f"{ocupacion:.1f} %",
    help=f"Horas de muelle usadas ÷ ({NUM_MUELLES} muelles × horas del periodo).", border=True,
)
k3.metric(
    "Eficiencia de carga/descarga", f"{eficiencia:.0f} TEU/h" if eficiencia is not None else "N/A",
    help="TEUs movidos por hora en muelle. Solo aplica a buques de contenedores.", border=True,
)
k4.metric(
    "Buques en demora crítica", f"{rojas + amarillas}",
    help=f"{rojas} en alerta roja (> {UMBRAL_ROJO_H} h) · {amarillas} en alerta amarilla (> {UMBRAL_AMARILLO_H} h)",
    border=True,
)

if rojas:
    aviso("roja", f"<b>{rojas} buque(s) en alerta roja</b>: esperaron más de {UMBRAL_ROJO_H} horas para atracar. "
                  f"Detalle en la tabla de alertas al final del tablero.", "rgba(208,59,59,0.12)", "#9b1c1c")
elif amarillas:
    aviso("amarilla", f"<b>{amarillas} buque(s) en alerta amarilla</b>: esperaron más de {UMBRAL_AMARILLO_H} horas.",
          "rgba(250,178,25,0.18)", "#7a5200")
else:
    aviso("check", "Ningún buque supera el umbral de demora crítica con estos filtros.",
          "rgba(12,163,12,0.12)", "#145c14")

# ---------------------------------------------------------------------------
# Fila 1: horas pico y tipo de carga
# ---------------------------------------------------------------------------
c1, c2 = st.columns(2)

with c1:
    st.subheader("¿A qué hora llegan más buques?")
    por_hora = d.groupby("Hora_Del_Dia").agg(Llegadas=("ID_Registro", "count"),
                                            Espera=("Tiempo_Espera_Horas", "mean")).reindex(range(24), fill_value=0)
    por_hora = por_hora.reset_index()
    fig = px.line(por_hora, x="Hora_Del_Dia", y="Llegadas", markers=True,
                  custom_data=["Espera"], color_discrete_sequence=[AZUL])
    fig.update_traces(line_width=2, marker_size=8,
                      hovertemplate="<b>%{x}:00 h</b><br>%{y} llegadas<br>Espera prom.: %{customdata[0]:.2f} h<extra></extra>")
    pico = por_hora.loc[por_hora["Llegadas"].idxmax()]
    fig.add_annotation(x=pico["Hora_Del_Dia"], y=pico["Llegadas"], text=f"Pico: {int(pico['Hora_Del_Dia'])}:00 h",
                       showarrow=True, arrowhead=0, ay=-28, font=dict(color=AZUL_OSCURO))
    fig.update_xaxes(title="Hora del día", tickmode="linear", dtick=2)
    fig.update_yaxes(title="Buques que llegan")
    st.plotly_chart(estilo(fig), use_container_width=True)

with c2:
    st.subheader("Espera promedio por tipo de carga")
    por_tipo = (d.groupby("Tipo_Carga").agg(Espera=("Tiempo_Espera_Horas", "mean"),
                                            Muelle=("Tiempo_Muelle_Horas", "mean"),
                                            Buques=("ID_Registro", "count"))
                .sort_values("Espera").reset_index())
    por_tipo["Etiqueta"] = por_tipo["Tipo_Carga"] + " (" + por_tipo["Buques"].astype(str) + ")"
    fig = px.bar(por_tipo, x="Espera", y="Etiqueta", orientation="h", text="Espera",
                 custom_data=["Muelle", "Buques"], color_discrete_sequence=[AZUL])
    fig.update_traces(texttemplate="%{x:.2f} h", textposition="outside", cliponaxis=False,
                      marker_cornerradius=4,
                      hovertemplate="<b>%{y}</b><br>Espera prom.: %{x:.2f} h<br>"
                                    "Tiempo en muelle prom.: %{customdata[0]:.1f} h<br>%{customdata[1]} buques<extra></extra>")
    fig.add_vline(x=tpe, line_dash="dot", line_color=GRIS,
                  annotation_text=f"TPE {tpe:.2f} h", annotation_position="top", annotation_font_color=GRIS)
    fig = estilo(fig)
    fig.update_layout(bargap=0.35, margin=dict(t=30))
    fig.update_xaxes(title="Horas de espera (entre paréntesis: número de buques)")
    fig.update_yaxes(title=None, showgrid=False)
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Fila 2: clima
# ---------------------------------------------------------------------------
c3, c4 = st.columns(2)

with c3:
    st.subheader("¿Cuánto afecta el clima la espera?")
    por_clima = (d.groupby("Condicion_Climatica").agg(Espera=("Tiempo_Espera_Horas", "mean"),
                                                      Buques=("ID_Registro", "count"))
                 .reindex([c for c in ORDEN_CLIMA if c in d["Condicion_Climatica"].unique()]).reset_index())
    fig = px.bar(por_clima, x="Condicion_Climatica", y="Espera", text="Espera", custom_data=["Buques"],
                 color_discrete_sequence=[AZUL])
    fig.update_traces(texttemplate="%{y:.2f} h", textposition="outside", cliponaxis=False, marker_cornerradius=4,
                      hovertemplate="<b>%{x}</b><br>Espera prom.: %{y:.2f} h<br>%{customdata[0]} buques<extra></extra>")
    fig.add_hline(y=UMBRAL_ROJO_H, line_dash="dash", line_color=ROJO_ALERTA,
                  annotation_text=f"Umbral rojo ({UMBRAL_ROJO_H} h)", annotation_position="top left",
                  annotation_font_color=ROJO_ALERTA)
    fig = estilo(fig)
    fig.update_layout(bargap=0.35, margin=dict(t=30))
    fig.update_xaxes(title=None)
    fig.update_yaxes(title="Horas de espera")
    st.plotly_chart(fig, use_container_width=True)

with c4:
    st.subheader("Clima × tipo de carga: ¿dónde está lo más crítico?")
    cruce = d.pivot_table(index="Tipo_Carga", columns="Condicion_Climatica", values="Tiempo_Espera_Horas",
                          aggfunc="mean").reindex(columns=[c for c in ORDEN_CLIMA if c in d["Condicion_Climatica"].unique()])
    fig = px.imshow(cruce, text_auto=".1f", color_continuous_scale=ESCALA_AZUL, aspect="auto",
                    labels=dict(x="", y="", color="Horas"))
    fig.update_traces(hovertemplate="<b>%{y}</b> con <b>%{x}</b><br>Espera prom.: %{z:.2f} h<extra></extra>")
    fig = estilo(fig)
    fig.update_layout(coloraxis_colorbar=dict(title="h", thickness=12))
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Las celdas vacías son combinaciones sin buques registrados.")

# ---------------------------------------------------------------------------
# Fila 3: ocupación de muelles en el tiempo
# ---------------------------------------------------------------------------
st.subheader("Ocupación de muelles hora a hora")
ocup = ocupacion_por_hora(d, inicio, fin)
fig = go.Figure(go.Scatter(x=ocup["Hora"], y=ocup["Buques_Atracados"], mode="lines", line=dict(color=AZUL, width=2),
                           line_shape="hv", fill="tozeroy", fillcolor="rgba(42,120,214,0.12)",
                           hovertemplate="%{x|%d/%m %H:00}<br>%{y} buques atracados<extra></extra>"))
fig.add_hline(y=NUM_MUELLES, line_dash="dash", line_color=ROJO_ALERTA,
              annotation_text=f"Capacidad: {NUM_MUELLES} muelles", annotation_position="top left",
              annotation_font_color=ROJO_ALERTA)
fig.update_yaxes(title="Buques atracados", range=[0, NUM_MUELLES + 1.5])
fig.update_xaxes(title=None)
st.plotly_chart(estilo(fig, alto=300), use_container_width=True)
max_ocup = ocup["Buques_Atracados"].max()
st.caption(f"Máximo simultáneo en el periodo: {max_ocup} de {NUM_MUELLES} muelles · "
           f"Horas con los {NUM_MUELLES} muelles llenos: {(ocup['Buques_Atracados'] >= NUM_MUELLES).sum()}")

# ---------------------------------------------------------------------------
# Tabla de alertas
# ---------------------------------------------------------------------------
titulo("alerta", "Alertas de demoras críticas")
alertas = (d[d["Nivel_Alerta"] != "Normal"]
           .sort_values("Tiempo_Espera_Horas", ascending=False)
           .assign(Icono=lambda x: x["Nivel_Alerta"].map({"Roja": icono_tabla("roja"),
           "Amarilla": icono_tabla("amarilla")}))
           [["Icono", "Nivel_Alerta", "ID_Registro", "Buque", "Tipo_Carga", "Condicion_Climatica", "Hora_Llegada",
             "Hora_Atraque", "Tiempo_Espera_Horas"]])


def color_fila(fila):
    tono = "rgba(208,59,59,0.12)" if fila["Nivel_Alerta"] == "Roja" else "rgba(250,178,25,0.15)"
    return [f"background-color: {tono}"] * len(fila)


if alertas.empty:
    st.info("Sin buques en alerta con estos filtros.")
else:
    st.dataframe(
        alertas.style.apply(color_fila, axis=1).format({"Tiempo_Espera_Horas": "{:.2f} h"}),
        hide_index=True, use_container_width=True,
        column_config={
            "Icono": (st.column_config.ImageColumn("", width="small") if icono_datos("roja")
             else st.column_config.TextColumn("", width="small")),
            "Nivel_Alerta": "Alerta",
            "ID_Registro": "Registro", "Tipo_Carga": "Tipo de carga", "Condicion_Climatica": "Clima",
            "Hora_Llegada": st.column_config.DatetimeColumn("Llegada", format="DD/MM HH:mm"),
            "Hora_Atraque": st.column_config.DatetimeColumn("Atraque", format="DD/MM HH:mm"),
            "Tiempo_Espera_Horas": "Espera",
        },
    )

# ---------------------------------------------------------------------------
# Hallazgos (se recalculan con los filtros)
# ---------------------------------------------------------------------------
titulo("foco", "Hallazgos y recomendaciones")
# Solo se comparan tipos con al menos 5 buques, para no sacar conclusiones de casos aislados
comparables = por_tipo[por_tipo["Buques"] >= 5]
comparables = comparables if not comparables.empty else por_tipo
peor_tipo = comparables.iloc[-1]
mejor_tipo = comparables.iloc[0]
lineas = [
    f"**Horas pico:** la mayor cantidad de llegadas ocurre a las **{int(pico['Hora_Del_Dia'])}:00 h** "
    f"({int(pico['Llegadas'])} buques). Conviene reforzar personal y grúas en esa franja.",
    f"**Tipo de carga:** **{peor_tipo['Tipo_Carga']}** espera más ({peor_tipo['Espera']:.2f} h) y "
    f"**{mejor_tipo['Tipo_Carga']}** menos ({mejor_tipo['Espera']:.2f} h).",
]
if len(por_clima) > 1:
    peor_clima, mejor_clima = por_clima.loc[por_clima["Espera"].idxmax()], por_clima.loc[por_clima["Espera"].idxmin()]
    lineas.append(
        f"**Clima:** con **{peor_clima['Condicion_Climatica']}** la espera promedio es "
        f"**{peor_clima['Espera'] / mejor_clima['Espera']:.1f} veces** la de {mejor_clima['Condicion_Climatica']} "
        f"({peor_clima['Espera']:.2f} h vs. {mejor_clima['Espera']:.2f} h). Se recomienda un protocolo de contingencia climática."
    )
lineas.append(
    f"**Capacidad:** la ocupación promedio es de **{ocupacion:.0f} %** y el máximo simultáneo fue {max_ocup} de "
    f"{NUM_MUELLES} muelles. " + ("Las demoras no se explican solo por falta de muelles: pesan más el clima y "
                                  "la concentración de llegadas." if ocupacion < 60 else
                                  "Los muelles operan cerca de su capacidad: evaluar ampliar ventanas de atraque.")
)
for linea in lineas:
    st.markdown(f"- {linea}")

with st.expander("Ver datos filtrados"):
    st.dataframe(d, hide_index=True, use_container_width=True)
