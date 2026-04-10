import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import altair as alt
from modules.i18n.i18n import t
from modules.app_config.styles import get_color_wellness
import pandas as pd
import plotly.graph_objects as go
import pandas as pd


# 1️⃣ RPE y UA -------------------------------------------------------
def grafico_rpe_ua(df: pd.DataFrame):
    #st.markdown("#### Evolución de RPE y Carga Interna (UA)")
    if "ua" in df.columns and "rpe" in df.columns:
        fig = px.bar(
            df,
            x="fecha_sesion",
            y="ua",
            color="rpe",
            color_continuous_scale="RdYlGn_r",
            labels={"ua": "Carga Interna (UA)", "fecha_sesion": "Fecha", "rpe": "RPE"},
            title=t("Evolución de RPE (color) y Carga Interna (barras)")
        )
        st.plotly_chart(fig)
    else:
        st.info(t("No hay datos de RPE o UA para graficar."))

# 2️⃣ Duración vs RPE ------------------------------------------------
def grafico_duracion_rpe(df: pd.DataFrame):
    #st.markdown("#### Relación entre duración y esfuerzo percibido")
    if "minutos_sesion" in df.columns and "rpe" in df.columns:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df["fecha_sesion"],
            y=df["minutos_sesion"],
            name="Minutos",
            marker_color="#1976D2"
        ))
        fig.add_trace(go.Scatter(
            x=df["fecha_sesion"],
            y=df["rpe"],
            mode="lines+markers",
            name="RPE",
            yaxis="y2",
            line=dict(color="#E64A19", width=3)
        ))
        fig.update_layout(
            title=t("Relación entre duración y esfuerzo percibido"),
            yaxis=dict(title="Minutos de sesión"),
            yaxis2=dict(title="RPE", overlaying="y", side="right"),
            legend_title_text="Variables"
        )
        st.plotly_chart(fig)
    else:
        st.info(t("No hay datos de minutos o RPE para graficar."))

# 3️⃣ ACWR -----------------------------------------------------------
# def grafico_acwr(df: pd.DataFrame):
#     #st.markdown("#### Evolución del índice ACWR (Relación Agudo:Crónico)")

#     if "ua" not in df.columns:
#         st.info(t("No hay datos de carga interna (UA) para calcular ACWR."))
#         return

#     df = df.copy()
#     df["ua"] = pd.to_numeric(df["ua"], errors="coerce")
#     df["acute7"] = df["ua"].rolling(7, min_periods=3).mean()
#     df["chronic28"] = df["ua"].rolling(28, min_periods=7).mean()
#     df["acwr"] = df["acute7"] / df["chronic28"]
#     df = df.dropna(subset=["acwr"])

#     if df.empty:
#         st.info(t("No hay suficientes datos para calcular ACWR."))
#         return

#     def _zone(v: float) -> str:
#         if v < 0.8: return "Subcarga"
#         elif v < 1.3: return "Sweet Spot"
#         elif v < 1.5: return "Elevada"
#         else: return "Peligro"

#     df["zona"] = df["acwr"].apply(_zone)

#     bandas = pd.DataFrame([
#         {"y0": 0.0, "y1": 0.8, "color": "#E3F2FD"},
#         {"y0": 0.8, "y1": 1.3, "color": "#C8E6C9"},
#         {"y0": 1.3, "y1": 1.5, "color": "#FFE0B2"},
#         {"y0": 1.5, "y1": 3.0, "color": "#FFCDD2"}
#     ])

#     bg = alt.Chart(bandas).mark_rect(opacity=0.6).encode(
#         y="y0:Q", y2="y1:Q",
#         color=alt.Color("color:N", scale=None, legend=None)
#     )

#     rules = alt.Chart(pd.DataFrame({"y": [0.8, 1.3, 1.5]})).mark_rule(
#         color="black", strokeDash=[4, 2], opacity=0.7
#     ).encode(y="y:Q")

#     base = alt.Chart(df).encode(
#         x=alt.X("fecha_sesion:T", title="Fecha", axis=alt.Axis(format="%b %d")),
#         y=alt.Y("acwr:Q", title="ACWR", scale=alt.Scale(domain=[0, max(2.5, df["acwr"].max() + 0.2)]))
#     )

#     line = base.mark_line(color="black", strokeWidth=2, interpolate="monotone")
#     pts = base.mark_circle(size=70).encode(
#         color=alt.Color("zona:N", scale=alt.Scale(
#             domain=["Subcarga", "Sweet Spot", "Elevada", "Peligro"],
#             range=["#64B5F6", "#2ca25f", "#fdae6b", "#d62728"]
#         )),
#         tooltip=["fecha_sesion:T", alt.Tooltip("acwr:Q", format=".2f")]
#     )

#     labels = alt.Chart(pd.DataFrame([
#         {"y": 0.4, "text": "Subcarga"},
#         {"y": 1.05, "text": "Punto Óptimo"},
#         {"y": 1.4, "text": "Zona Elevada"},
#         {"y": 1.8, "text": "Peligro"}
#     ])).mark_text(align="left", dx=5, fontSize=11, color="#444").encode(y="y:Q", text="text:N")

#     chart = alt.layer(bg, rules, line, pts, labels).properties(height=320, width="container", title=t("Evolución del índice ACWR (Relación Agudo:Crónico)"))
#     st.altair_chart(chart)

def grafico_acwr(
    df_states: pd.DataFrame,
    ventana_cronica: int = 42,
):
    """
    Gráfico de evolución del ACWR a partir de un DataFrame ya calculado
    (compute_rpe_timeseries).
    """

    col_acwr = f"acwr_{ventana_cronica}d_ema"

    if df_states.empty or col_acwr not in df_states.columns:
        st.info(t("No hay datos suficientes para mostrar el ACWR."))
        return

    df = df_states[["fecha_sesion", col_acwr]].dropna().copy()
    df.rename(columns={col_acwr: "acwr"}, inplace=True)

    if df.empty:
        st.info(t("No hay suficientes datos para calcular ACWR."))
        return

    # -------------------------
    # Clasificación por zonas
    # -------------------------
    def _zone(v: float) -> str:
        if v < 0.8:
            return "Subcarga"
        elif v < 1.3:
            return "Sweet Spot"
        elif v < 1.5:
            return "Elevada"
        else:
            return "Peligro"

    df["zona"] = df["acwr"].apply(_zone)

    # -------------------------
    # Bandas de referencia
    # -------------------------
    bandas = pd.DataFrame([
        {"y0": 0.0, "y1": 0.8, "color": "#E3F2FD"},
        {"y0": 0.8, "y1": 1.3, "color": "#C8E6C9"},
        {"y0": 1.3, "y1": 1.5, "color": "#FFE0B2"},
        {"y0": 1.5, "y1": 3.0, "color": "#FFCDD2"},
    ])

    bg = alt.Chart(bandas).mark_rect(opacity=0.6).encode(
        y="y0:Q",
        y2="y1:Q",
        color=alt.Color("color:N", scale=None, legend=None),
    )

    rules = alt.Chart(
        pd.DataFrame({"y": [0.8, 1.3, 1.5]})
    ).mark_rule(
        color="black", strokeDash=[4, 2], opacity=0.7
    ).encode(y="y:Q")

    base = alt.Chart(df).encode(
        x=alt.X(
            "fecha_sesion:T",
            title=t("Fecha"),
            axis=alt.Axis(format="%b %d"),
        ),
        y=alt.Y(
            "acwr:Q",
            title="ACWR",
            scale=alt.Scale(domain=[0, max(2.5, df["acwr"].max() + 0.2)]),
        ),
    )

    line = base.mark_line(
        color="black", strokeWidth=2, interpolate="monotone"
    )

    pts = base.mark_circle(size=70).encode(
        color=alt.Color(
            "zona:N",
            scale=alt.Scale(
                domain=["Subcarga", "Sweet Spot", "Elevada", "Peligro"],
                range=["#64B5F6", "#2ca25f", "#fdae6b", "#d62728"],
            ),
        ),
        tooltip=[
            "fecha_sesion:T",
            alt.Tooltip("acwr:Q", format=".2f"),
            "zona:N",
        ],
    )

    labels = alt.Chart(pd.DataFrame([
        {"y": 0.4, "text": "Subcarga"},
        {"y": 1.05, "text": "Punto óptimo"},
        {"y": 1.4, "text": "Zona elevada"},
        {"y": 1.8, "text": "Peligro"},
    ])).mark_text(
        align="left", dx=5, fontSize=11, color="#444"
    ).encode(y="y:Q", text="text:N")

    chart = alt.layer(
        bg, rules, line, pts, labels
    ).properties(
        height=320,
        width="container",
        title=t(f"Evolución del índice ACWR "),
    )

    st.altair_chart(chart)

# 4️⃣ Wellness -------------------------------------------------------
def grafico_wellness(df: pd.DataFrame):
    #st.markdown("**Evolución de los indicadores de bienestar (1-5)**")
    cols = ["recuperacion", "energia", "sueno", "stress", "dolor"]
    if all(c in df.columns for c in cols):
        fig = px.line(
            df, x="fecha_sesion", y=cols, markers=True,
            labels={"value": "Nivel (1-5)", "fecha_sesion": "Fecha", "variable": "Parámetro"},
            title=t("Evolución de los indicadores de bienestar")
        )
        st.plotly_chart(fig)
    else:
        st.info(t("No hay datos de bienestar para graficar."))

# 5️⃣ Riesgo de lesión -----------------------------------------------
def grafico_riesgo_lesion(df: pd.DataFrame):
    """
    Visualiza el riesgo de lesión combinando el índice ACWR (Agudo:Crónico)
    con la fatiga subjetiva, mostrando zonas de carga de fondo.
    """

    st.markdown(t("#### Evolución del riesgo de lesión (ACWR + Fatiga)"))

    if "ua" not in df.columns:
        st.info(t("No hay datos suficientes para calcular el riesgo."))
        return

    df = df.copy()
    df["ua"] = pd.to_numeric(df["ua"], errors="coerce")
    df["fatiga"] = pd.to_numeric(df.get("energia", np.nan), errors="coerce")

    # Calcular cargas aguda y crónica
    df["acute7"] = df["ua"].rolling(7, min_periods=3).mean()
    df["chronic28"] = df["ua"].rolling(28, min_periods=7).mean()
    df["acwr"] = df["acute7"] / df["chronic28"]

    # --- Clasificación del riesgo ---
    def riesgo_calc(row):
        if pd.isna(row["acwr"]) or pd.isna(row["fatiga"]):
            return np.nan
        if row["acwr"] > 1.5 or row["fatiga"] >= 4:
            return "Alto"
        elif 1.3 <= row["acwr"] <= 1.5 or 3 <= row["fatiga"] < 4:
            return "Moderado"
        else:
            return "Bajo"

    df["riesgo_lesion"] = df.apply(riesgo_calc, axis=1)

    # --- Mapa de colores ---
    color_map = {"Bajo": "#43A047", "Moderado": "#FB8C00", "Alto": "#E53935"}

    # --- Gráfico base ---
    fig = px.scatter(
        df,
        x="fecha_sesion",
        y="acwr",
        color="riesgo_lesion",
        color_discrete_map=color_map,
        title=t("Evolución del riesgo de lesión (ACWR + Fatiga)"),
        labels={
            "acwr": "Relación Agudo:Crónico (ACWR)",
            "fecha_sesion": "Fecha",
            "riesgo_lesion": "Nivel de riesgo"
        },
        hover_data={
            "acwr": ":.2f",
            "fatiga": ":.1f",
            "riesgo_lesion": True
        }
    )

    # --- Bandas de color de fondo según ACWR ---
    fig.add_hrect(y0=0.0, y1=0.8, fillcolor="#BBDEFB", opacity=0.25, line_width=0)   # Azul: subcarga
    fig.add_hrect(y0=0.8, y1=1.3, fillcolor="#C8E6C9", opacity=0.25, line_width=0)   # Verde: zona óptima
    fig.add_hrect(y0=1.3, y1=1.5, fillcolor="#FFE0B2", opacity=0.25, line_width=0)   # Naranja: elevada
    fig.add_hrect(y0=1.5, y1=3.0, fillcolor="#FFCDD2", opacity=0.25, line_width=0)   # Roja: riesgo

    # --- Estética ---
    fig.update_layout(
        yaxis=dict(range=[0.7, max(2.0, df["acwr"].max() + 0.2)]),
        legend_title_text=t("Nivel de riesgo"),
        template="simple_white"
    )

    st.plotly_chart(fig)

    # --- Leyenda explicativa ---
    st.markdown(
        """
        **Interpretación del gráfico:**
        - 🟩 **Banda verde (0.8-1.3):** zona óptima o “sweet spot”.  
        - 🟧 **Banda naranja (1.3-1.5):** carga elevada, riesgo moderado.  
        - 🟥 **Banda roja (>1.5):** sobrecarga, riesgo alto de lesión.  
        - 🟦 **Banda azul (<0.8):** subcarga o pérdida de forma.  
        - El **color del punto** depende del riesgo combinado entre **ACWR y fatiga**:
            - 🟢 **Bajo:** carga estable y fatiga baja.  
            - 🟠 **Moderado:** aumento de carga o fatiga leve.  
            - 🔴 **Alto:** sobrecarga o fatiga elevada.
        """
    )

def tabla_wellness_individual(df: pd.DataFrame):
    """
    Muestra una tabla detallada por fecha con indicadores de bienestar (1-5)
    aplicando la escala de interpretación Wellness global (normal e invertida).
    """

    st.markdown(t("**Wellness por sesión**"))

    # --- Verificar columnas necesarias ---
    cols_min = ["fecha_sesion", "periodizacion_tactica", "energia", "recuperacion", "sueno", "stress", "dolor"]
    if not all(c in df.columns for c in cols_min):
        st.warning("No hay suficientes datos para mostrar la tabla de Wellness.")
        return

    # --- Crear tabla base ---
    t_df = df.copy()
    t_df["fecha_sesion"] = pd.to_datetime(t_df["fecha_sesion"], errors="coerce")
    t_df = t_df.sort_values("fecha_sesion", ascending=False).reset_index(drop=True)

    # Día de la semana en español
    day_map = {
        "Monday": t("Lunes"),
        "Tuesday": t("Martes"),
        "Wednesday": t("Miércoles"),
        "Thursday": t("Jueves"),
        "Friday": t("Viernes"),
        "Saturday": t("Sábado"),
        "Sunday": t("Domingo")
    }

    t_df["Día Semana"] = t_df["fecha_sesion"].dt.day_name().map(day_map)
    #t_df["Día Semana"] = t_df["fecha_sesion"].dt.day_name(locale="es_ES")
    t_df["fecha_sesion"] = t_df["fecha_sesion"].dt.date

    #st.dataframe(t_df)
    # Tipo de estímulo y readaptación
    t_df["Tipo de estímulo"] = t_df.get("tipo_carga", "").fillna("").astype(str)
    t_df["Tipo de readaptación"] = t_df.get("rehabilitación_readaptación", "").fillna("").astype(str)

    # Calcular Promedio Wellness
    t_df["Promedio Wellness"] = t_df[["recuperacion", "energia", "sueno", "stress", "dolor"]].mean(axis=1)

    # Selección y renombre de columnas
    t_show = t_df[[
        "fecha_sesion", "Día Semana", "periodizacion_tactica",
        "Tipo de estímulo", "Tipo de readaptación",
        "recuperacion", "energia", "sueno", "stress", "dolor", "Promedio Wellness"
    ]].rename(columns={
        "fecha_sesion": "Fecha sesión",
        "periodizacion_tactica": "Periodización táctica",
        "recuperacion": "Recuperación",
        "energia": "Energía",
        "sueno": "Sueño",
        "stress": "Estrés",
        "dolor": "Dolor"
    })

    # --- Aplicar colores desde styles.py ---
    def style_func(col):
        if col.name in ["Recuperación", "Energía", "Sueño", "Estrés", "Dolor"]:
            return [
                f"background-color:{get_color_wellness(v, col.name)}; "
                f"color:white; font-weight:bold; text-align:center;"
                for v in col
            ]
        elif col.name == "Promedio Wellness":
            return [
                # Rojo bajo, amarillo moderado, rVerde óptimo 
                # "background-color:#27AE60; color:white; font-weight:bold; text-align:center;" if v >= 4 else
                # "background-color:#F1C40F; color:black; text-align:center;" if 3 <= v < 4 else
                # "background-color:#E74C3C; color:white; font-weight:bold; text-align:center;"

                "background-color:#E74C3C; color:white; font-weight:bold; text-align:center;" if v >= 4 else
                "background-color:#F1C40F; color:black; text-align:center;" if 3 <= v < 4 else
                "background-color:#27AE60; color:white; font-weight:bold; text-align:center;"
                for v in col
            ]
        return [""] * len(col)

    # --- Aplicar estilo al DataFrame ---
    styled = (
        t_show.style
        .apply(style_func, subset=["Recuperación", "Energía", "Sueño", "Estrés", "Dolor", "Promedio Wellness"])
        .format(precision=2)
    )

    st.dataframe(styled)        

    # caption_green = t("**Valores altos indican mejor bienestar** en Recuperación, Energía y Sueño.")
    # caption_red = t("**Valores bajos indican mejor bienestar** en Estrés y Dolor (escala invertida).")
    # # --- Explicación ---
    # st.caption(f"🟩 {caption_green}")
    # st.caption(f"🟥 {caption_red}")

# Lesiones ------------------------------------------------

def grafico_wellness_pre_lesion(df_pre: pd.DataFrame):
    """
    Gráfico interactivo de wellness previo a la lesión.
    Incluye línea vertical de lesión y tooltip con zona afectada.
    """

    if df_pre is None or df_pre.empty:
        return None

    df = df_pre.sort_values("fecha_sesion")

    # Datos clave de la lesión (una sola por gráfico)
    fecha_lesion = pd.to_datetime(df["fecha_lesion"].iloc[0])
    zona = df["zona_especifica_id"].iloc[0]
    lateralidad = df["lateralidad"].iloc[0]
    id_lesion = df["id_lesion"].iloc[0]

    fig = go.Figure()

    # ----------------------------
    # Líneas de wellness
    # ----------------------------
    wellness_vars = {
        "Recuperación": "recuperacion",
        "Energía": "energia",
        "Sueño": "sueno",
        "Estrés": "stress",
        "Dolor": "dolor",
    }

    for label, col in wellness_vars.items():
        fig.add_trace(
            go.Scatter(
                x=df["fecha_sesion"],
                y=df[col],
                mode="lines+markers",
                name=label,
                hovertemplate=(
                    "<b>%{x|%d-%m-%Y}</b><br>"
                    f"{label}: %{{y}}<extra></extra>"
                )
            )
        )

    # ----------------------------
    # Línea vertical de lesión
    # ----------------------------
    fig.add_vline(
        x=fecha_lesion,
        line_width=3,
        line_dash="dash",
        line_color="red"
    )

    # ----------------------------
    # Punto de lesión (marcador)
    # ----------------------------
    fig.add_trace(
        go.Scatter(
            x=[fecha_lesion],
            y=[5.2],
            mode="markers",
            marker=dict(
                size=16,
                color="red",
                symbol="x"
            ),
            name="Lesión",
            hovertemplate=(
                "<b>Lesión</b><br>"
                f"ID: {id_lesion}<br>"
                f"Zona: {zona}<br>"
                f"Lateralidad: {lateralidad}<br>"
                f"Fecha: {fecha_lesion.strftime('%d-%m-%Y')}"
                "<extra></extra>"
            )
        )
    )

    # ----------------------------
    # Layout
    # ----------------------------
    fig.update_layout(
        title="Contexto de wellness previo a la lesión",
        xaxis_title="Fecha",
        yaxis_title="Escala Wellness (1–5)",
        yaxis=dict(range=[1, 5.5]),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        ),
        margin=dict(t=80),
        hovermode="x unified"
    )

    # ----------------------------
    # Eje X: fechas claras
    # ----------------------------
    fig.update_xaxes(
        tickformat="%d-%m",
        dtick="D1",
        tickangle=-45
    )

    #return fig
    st.plotly_chart(fig, use_container_width=True)

### RPE ------------------------------------------------

def plot_carga_fatiga_recuperacion(
    df_states: pd.DataFrame,
    ventana_cronica: int = 42,
    metodo: str = "ema",
    fecha_lesion=None,
    window_days: int = 7,
):
    """
    Gráfico individual de estado de carga:
    - Barras: UA diaria
    - Líneas: Fatiga aguda y crónica
    - Línea: Estado de forma
    - OPCIONAL: ventana centrada en lesión + línea vertical
    """

    if df_states is None or df_states.empty:
        st.info(t("No hay datos suficientes para mostrar el estado de carga."))
        return

    df_plot = df_states.copy()
    df_plot["fecha_sesion"] = pd.to_datetime(df_plot["fecha_sesion"])

    # =========================
    # 🎯 FILTRADO PRE-LESIÓN
    # =========================
    if fecha_lesion is not None:
        fecha_lesion = pd.to_datetime(fecha_lesion)

        start = fecha_lesion - pd.Timedelta(days=window_days)
        end = fecha_lesion + pd.Timedelta(days=2)

        df_plot = df_plot[
            (df_plot["fecha_sesion"] >= start) &
            (df_plot["fecha_sesion"] <= end)
        ].copy()

        if df_plot.empty:
            st.info("No hay datos en la ventana de la lesión.")
            return

    # =========================
    # Columnas dinámicas
    # =========================
    metodo = metodo.lower().strip()
    if metodo not in {"sma", "ema"}:
        metodo = "ema"

    col_aguda = f"fatiga_aguda_7d_{metodo}"
    col_cronica = f"fatiga_cronica_{ventana_cronica}d_{metodo}"
    col_estado = f"estado_forma_{ventana_cronica}d_{metodo}"

    required = {"fecha_sesion", "ua_diaria", col_aguda, col_cronica}
    missing = required - set(df_plot.columns)
    if missing:
        st.info(t("Faltan columnas para graficar el estado de carga individual."))
        st.write("Missing:", list(missing))
        return

    # =========================
    # GRÁFICO
    # =========================
    fig = go.Figure()

    # Barras UA
    fig.add_bar(
        x=df_plot["fecha_sesion"],
        y=df_plot["ua_diaria"],
        name=t("Carga diaria (UA)"),
        marker_color="rgba(150,150,150,0.4)",
    )

    # Fatiga aguda
    fig.add_trace(
        go.Scatter(
            x=df_plot["fecha_sesion"],
            y=df_plot[col_aguda],
            mode="lines",
            name=t("Fatiga aguda (7d)"),
            line=dict(color="#E53935", width=2),
        )
    )

    # Fatiga crónica
    fig.add_trace(
        go.Scatter(
            x=df_plot["fecha_sesion"],
            y=df_plot[col_cronica],
            mode="lines",
            name=t(f"Fatiga crónica ({ventana_cronica}d)"),
            line=dict(color="#1E88E5", width=2),
        )
    )

    # Estado de forma
    if col_estado in df_plot.columns:
        fig.add_trace(
            go.Scatter(
                x=df_plot["fecha_sesion"],
                y=df_plot[col_estado],
                mode="lines",
                name=t("Estado de forma"),
                line=dict(color="#43A047", width=2, dash="dot"),
            )
        )

    # =========================
    # 🔴 MARCA DE LESIÓN
    # =========================
    if fecha_lesion is not None:
        fig.add_vline(
            x=fecha_lesion,
            line_width=2,
            line_dash="dash",
            line_color="red",
        )

        fig.add_annotation(
            x=fecha_lesion,
            y=df_plot["ua_diaria"].max(),
            text="Lesión",
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-40,
            font=dict(color="red")
        )

    titulo_metodo = "SMA" if metodo == "sma" else "EMA"

    titulo = (
        f"Carga, Fatiga y Estado de forma ({titulo_metodo})"
        if fecha_lesion is None
        else f"Carga previa a lesión (-{window_days}d)"
    )

    fig.update_layout(
        title=t(titulo),
        xaxis_title=t("Fecha"),
        yaxis=dict(
            title=t("Carga / Fatiga / Estado de forma (UA)"),
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor="gray",
        ),
        plot_bgcolor="white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        barmode="overlay",
    )

    st.plotly_chart(fig, use_container_width=True)


### PIAY

def plot_wellness_evolucion_individual(df_daily: pd.DataFrame):
    """
    Evolución temporal del wellness de una jugadora.
    Espera un DataFrame agregado por fecha_sesion.
    """

    if df_daily is None or df_daily.empty:
        st.info(t("No hay datos de wellness para mostrar."))
        return

    df_plot = df_daily.copy()
    df_plot["fecha_sesion"] = pd.to_datetime(df_plot["fecha_sesion"], errors="coerce")
    df_plot = df_plot.dropna(subset=["fecha_sesion"]).sort_values("fecha_sesion")

    cols_wellness = ["energia", "recuperacion", "sueno", "stress", "dolor"]
    cols_wellness = [c for c in cols_wellness if c in df_plot.columns]

    if "fecha_sesion" not in df_plot.columns or not cols_wellness:
        st.warning(t("Faltan columnas necesarias para graficar el wellness individual."))
        return

    fig = go.Figure()

    for col in cols_wellness:
        fig.add_trace(
            go.Scatter(
                x=df_plot["fecha_sesion"],
                y=df_plot[col],
                mode="lines+markers",
                name=col.capitalize()
            )
        )

    # UA opcional en segundo eje
    if "ua" in df_plot.columns:
        fig.add_trace(
            go.Bar(
                x=df_plot["fecha_sesion"],
                y=df_plot["ua"],
                name="UA",
                opacity=0.20,
                yaxis="y2"
            )
        )

    fig.update_layout(
        title=t("Evolución temporal del wellness individual"),
        xaxis_title=t("Fecha"),
        yaxis=dict(
            title=t("Wellness medio"),
            range=[1, 5]
        ),
        yaxis2=dict(
            title=t("UA"),
            overlaying="y",
            side="right",
            showgrid=False
        ),
        plot_bgcolor="white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        barmode="overlay",
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)


def plot_carga_semanal_individual(df: pd.DataFrame) -> pd.DataFrame:
    """Evolución semanal de la carga total y media de una jugadora."""
    if df is None or df.empty or "fecha_sesion" not in df.columns or "ua" not in df.columns:
        st.info(t("No hay datos de carga disponibles."))
        return pd.DataFrame()

    out = df.copy()
    out["fecha_sesion"] = pd.to_datetime(out["fecha_sesion"], errors="coerce")

    out["anio"] = out["fecha_sesion"].dt.year
    out["semana"] = out["fecha_sesion"].dt.isocalendar().week

    out["inicio_semana"] = out["fecha_sesion"] - pd.to_timedelta(out["fecha_sesion"].dt.weekday, unit="d")
    out["fin_semana"] = out["inicio_semana"] + pd.Timedelta(days=6)
    out["rango_semana"] = out["inicio_semana"].dt.strftime("%d %b") + "–" + out["fin_semana"].dt.strftime("%d %b")

    weekly = (
        out.groupby(["anio", "semana", "rango_semana"], as_index=False)
        .agg(
            carga_total=("ua", "sum"),
            carga_media=("ua", "mean"),
            rpe_prom=("rpe", "mean"),
            fecha_min=("fecha_sesion", "min"),
            fecha_max=("fecha_sesion", "max"),
        )
        .sort_values(["anio", "semana"])
    )

    fig = px.line(
        weekly,
        x="rango_semana",
        y="carga_total",
        markers=True,
        title=t("Carga total semanal (UA)"),
    )

    fig.update_layout(
        xaxis_title=t("Semana"),
        yaxis_title=t("Carga (UA)"),
        plot_bgcolor="white",
    )

    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        weekly[["rango_semana", "carga_total", "carga_media", "rpe_prom"]].rename(
            columns={
                "rango_semana": "Semana",
                "carga_total": "Carga total (UA)",
                "carga_media": "Carga media (UA)",
                "rpe_prom": "RPE promedio",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )

    return weekly


def plot_carga_diaria_detalle_individual(df: pd.DataFrame, start=None, end=None):
    """Detalle diario de carga individual, incluyendo días sin carga."""

    if df is None or df.empty or "ua" not in df.columns or "fecha_sesion" not in df.columns:
        st.info(t("No hay datos de carga disponibles."))
        return

    out = df.copy()
    out["fecha_sesion"] = pd.to_datetime(out["fecha_sesion"], errors="coerce").dt.normalize()

    daily_real = (
        out.groupby("fecha_sesion", as_index=False)
        .agg(
            carga_total=("ua", "sum"),
            carga_media=("ua", "mean"),
            rpe_prom=("rpe", "mean"),
        )
        .sort_values("fecha_sesion")
    )

    if start is not None and end is not None:
        fecha_min = pd.to_datetime(start).normalize()
        fecha_max = pd.to_datetime(end).normalize()
    else:
        fecha_min = daily_real["fecha_sesion"].min()
        fecha_max = daily_real["fecha_sesion"].max()

    calendario = pd.DataFrame({
        "fecha_sesion": pd.date_range(start=fecha_min, end=fecha_max, freq="D")
    })

    daily = calendario.merge(daily_real, on="fecha_sesion", how="left")

    daily["carga_total"] = daily["carga_total"].fillna(0)
    daily["carga_media"] = daily["carga_media"].fillna(0)
    daily["rpe_prom"] = daily["rpe_prom"].fillna(0)

    daily["fecha_label"] = daily["fecha_sesion"].dt.strftime("%d %b")

    fig = px.bar(
        daily,
        x="fecha_label",
        y="carga_total",
        text="carga_total",
        title=t("Detalle diario de carga (UA)"),
    )

    fig.update_traces(
        texttemplate="%{text:.0f}",
        textposition="outside",
        cliponaxis=False,
    )

    fig.update_layout(
        xaxis_title=t("Fecha"),
        yaxis_title=t("Carga (UA)"),
        plot_bgcolor="white",
        xaxis=dict(type="category", categoryorder="array", categoryarray=daily["fecha_label"].tolist()),
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)

    daily_show = daily.copy()
    daily_show["fecha_sesion"] = daily_show["fecha_sesion"].dt.date

    st.dataframe(
        daily_show[["fecha_sesion", "carga_total", "carga_media", "rpe_prom"]].rename(
            columns={
                "fecha_sesion": "Fecha",
                "carga_total": "Carga total (UA)",
                "carga_media": "Carga media (UA)",
                "rpe_prom": "RPE promedio",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )


def plot_carga_vs_wellness(df: pd.DataFrame):
    """
    Scatter: carga vs wellness.
    """

    if df is None or df.empty:
        st.info("No hay datos suficientes.")
        return

    df_plot = df.copy()

    # wellness promedio
    cols = ["recuperacion", "energia", "sueno", "stress", "dolor"]
    df_plot["wellness"] = df_plot[cols].mean(axis=1)

    fig = px.scatter(
        df_plot,
        x="ua",
        y="wellness",
        color="rpe",
        title="Carga vs Wellness",
        labels={
            "ua": "Carga (UA)",
            "wellness": "Wellness",
            "rpe": "RPE"
        }
    )

    st.plotly_chart(fig, use_container_width=True)