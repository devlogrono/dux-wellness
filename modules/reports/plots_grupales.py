# src/plots_grupales.py
import streamlit as st
import pandas as pd
import plotly.express as px
from modules.app_config import styles
from modules.i18n.i18n import t
import plotly.graph_objects as go
import altair as alt

# ============================================================
# 🧭 Función auxiliar de fecha
# ============================================================
def _ensure_fecha(df: pd.DataFrame) -> pd.DataFrame:
    """Asegura columna 'fecha_sesion' y añade 'semana', 'anio' y 'rango_semana'."""
    df = df.copy()
    if "fecha_sesion" not in df.columns:
        st.warning("El DataFrame no contiene la columna 'fecha_sesion'.")
        return df

    df["fecha_sesion"] = pd.to_datetime(df["fecha_sesion"], errors="coerce")
    df["anio"] = df["fecha_sesion"].dt.year
    df["semana"] = df["fecha_sesion"].dt.isocalendar().week

    # Etiqueta más amigable: rango de lunes a domingo
    df["inicio_semana"] = df["fecha_sesion"] - pd.to_timedelta(df["fecha_sesion"].dt.weekday, unit="d")
    df["fin_semana"] = df["inicio_semana"] + pd.Timedelta(days=6)
    df["rango_semana"] = df["inicio_semana"].dt.strftime("%d %b") + "–" + df["fin_semana"].dt.strftime("%d %b")

    return df

# ============================================================
# 📊 Carga semanal (UA)
# ============================================================
def plot_carga_semanal_base(df: pd.DataFrame, titulo: str = "Carga total semanal (UA)"):
    weekly = build_carga_semanal_base(df)

    if weekly.empty:
        st.info("No hay datos de carga disponibles.")
        return pd.DataFrame()

    fig = px.line(
        weekly,
        x="rango_semana",
        y="carga_total",
        markers=True,
        title=t(titulo),
        color_discrete_sequence=[styles.BRAND_PRIMARY],
    )

    fig.update_traces(line=dict(width=3))
    fig.update_layout(
        xaxis_title=t("Semana"),
        yaxis_title=t("Carga (UA)"),
        plot_bgcolor="white",
        font_color=styles.BRAND_TEXT,
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

def build_carga_semanal_base(df: pd.DataFrame) -> pd.DataFrame:
    df = _ensure_fecha(df)
    if df.empty or "ua" not in df.columns or df["ua"].isna().all():
        return pd.DataFrame()

    weekly = (
        df.groupby(["anio", "semana", "rango_semana"], as_index=False)
        .agg(
            carga_total=("ua", "sum"),
            carga_media=("ua", "mean"),
            rpe_prom=("rpe", "mean"),
            inicio_semana=("inicio_semana", "min"),
            fin_semana=("fin_semana", "max"),
        )
        .sort_values(["anio", "semana"])
    )

    return weekly

def plot_carga_diaria_detalle_base(df: pd.DataFrame, start=None, end=None):
    df = _ensure_fecha(df)

    if df.empty or "ua" not in df.columns:
        st.info("No hay datos de carga disponibles.")
        return

    daily = (
        df.groupby("fecha_sesion", as_index=False)
        .agg(
            carga_total=("ua", "sum"),
            carga_media=("ua", "mean"),
            rpe_prom=("rpe", "mean"),
        )
        .sort_values("fecha_sesion")
    )

    daily["fecha_sesion"] = pd.to_datetime(daily["fecha_sesion"], errors="coerce").dt.normalize()

    if start is not None and end is not None:
        fecha_min = pd.to_datetime(start).normalize()
        fecha_max = pd.to_datetime(end).normalize()
    else:
        fecha_min = daily["fecha_sesion"].min()
        fecha_max = daily["fecha_sesion"].max()

    full_range = pd.date_range(start=fecha_min, end=fecha_max, freq="D")

    daily = (
        daily.set_index("fecha_sesion")
        .reindex(full_range)
        .rename_axis("fecha_sesion")
        .reset_index()
    )

    daily["carga_total"] = daily["carga_total"].fillna(0)
    daily["carga_media"] = daily["carga_media"].fillna(0)
    daily["rpe_prom"] = daily["rpe_prom"].fillna(0)
    daily["fecha_label"] = daily["fecha_sesion"].dt.strftime("%d %b")

    fig = px.bar(
        daily,
        x="fecha_label",
        y="carga_total",
        title=t("Detalle diario de carga (UA)"),
        text="carga_total",
    )

    fig.update_traces(
        texttemplate="%{text:.0f}",
        textposition="outside"
    )

    fig.add_scatter(
        x=daily["fecha_label"],
        y=daily["carga_total"],
        mode="lines+markers",
        name=t("Carga diaria"),
        line=dict(color="#E53935", width=2),
        marker=dict(color="#E53935", size=7),
    )

    fig.update_layout(
        xaxis_title=t("Fecha"),
        yaxis_title=t("Carga (UA)"),
        plot_bgcolor="white",
        font_color=styles.BRAND_TEXT,
        xaxis=dict(type="category"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
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


# ============================================================
# 📉 RPE promedio diario
# ============================================================
def plot_rpe_promedio(df: pd.DataFrame):
    """Promedio de RPE diario del grupo."""
    df = _ensure_fecha(df)
    if "rpe" not in df.columns:
        st.warning("No se encontró la columna RPE.")
        return

    daily = df.groupby("fecha_sesion", as_index=False)["rpe"].mean()

    fig = px.bar(
        daily,
        x="fecha_sesion",
        y="rpe",
        title=t("RPE promedio diario"),
        color="rpe",
        color_continuous_scale=[
            styles.SEMAFORO["verde_oscuro"],
            styles.SEMAFORO["amarillo"],
            styles.SEMAFORO["rojo"],
        ],
    )
    fig.update_layout(
        xaxis_title=t("Fecha"),
        yaxis_title=t("RPE promedio"),
        plot_bgcolor="white",
        font_color=styles.BRAND_TEXT,
        coloraxis_colorbar=dict(title="RPE"),
    )
    st.plotly_chart(fig, use_container_width=False)

# ============================================================
# ⚙️ Monotonía y strain
# ============================================================
def plot_monotonia_strain(df: pd.DataFrame, scope: str = "grupal"):
    """
    Muestra la monotonía semanal y el strain semanal.

    Definiciones:
    - Monotonía = media diaria semanal / desviación estándar diaria semanal
    - Strain = carga semanal total * monotonía

    IMPORTANTE:
    - los días sin carga se incluyen como 0
    - la monotonía se calcula sobre el microciclo completo, no solo sobre los días con sesión
    - sirve tanto para grupo como para una jugadora, según el dataframe recibido
    """
    df = _ensure_fecha(df)

    if df.empty or "ua" not in df.columns or "fecha_sesion" not in df.columns:
        st.warning("No hay datos suficientes para calcular monotonía y strain.")
        return

    out = df.copy()
    out["ua"] = pd.to_numeric(out["ua"], errors="coerce").fillna(0)
    out["fecha_sesion"] = pd.to_datetime(out["fecha_sesion"], errors="coerce").dt.normalize()
    out = out.dropna(subset=["fecha_sesion"])

    if out.empty:
        st.info("No hay datos válidos para mostrar.")
        return

    # 1) Carga diaria real
    daily_real = (
        out.groupby("fecha_sesion", as_index=False)["ua"]
        .sum()
        .rename(columns={"ua": "ua_diaria"})
        .sort_values("fecha_sesion")
    )

    # 2) Serie diaria continua con ceros
    full_range = pd.date_range(
        start=daily_real["fecha_sesion"].min(),
        end=daily_real["fecha_sesion"].max(),
        freq="D"
    )

    daily = (
        daily_real.set_index("fecha_sesion")
        .reindex(full_range, fill_value=0)
        .rename_axis("fecha_sesion")
        .reset_index()
    )

    # 3) Variables semanales
    daily["anio"] = daily["fecha_sesion"].dt.year
    daily["semana"] = daily["fecha_sesion"].dt.isocalendar().week.astype(int)

    daily["inicio_semana"] = daily["fecha_sesion"] - pd.to_timedelta(
        daily["fecha_sesion"].dt.weekday, unit="d"
    )
    daily["fin_semana"] = daily["inicio_semana"] + pd.Timedelta(days=6)
    daily["rango_semana"] = (
        daily["inicio_semana"].dt.strftime("%d %b")
        + "–"
        + daily["fin_semana"].dt.strftime("%d %b")
    )

    # 4) Resumen semanal
    weekly = (
        daily.groupby(["anio", "semana", "rango_semana"], as_index=False)["ua_diaria"]
        .agg(["sum", "mean", "std"])
        .reset_index()
        .rename(columns={
            "sum": "carga_total",
            "mean": "media_diaria",
            "std": "desv_std"
        })
    )

    weekly["desv_std"] = weekly["desv_std"].fillna(0)

    weekly["monotonia"] = weekly.apply(
        lambda row: row["media_diaria"] / row["desv_std"]
        if row["desv_std"] > 0 else None,
        axis=1
    )

    weekly["strain"] = weekly.apply(
        lambda row: row["carga_total"] * row["monotonia"]
        if pd.notna(row["monotonia"]) else None,
        axis=1
    )

    titulo_scope = "grupal" if scope == "grupal" else "individual"

    fig = px.line(
        weekly,
        x="rango_semana",
        y=["monotonia", "strain"],
        markers=True,
        title=t(f"Monotonía y strain semanal ({titulo_scope})"),
        color_discrete_map={
            "monotonia": styles.SEMAFORO["naranja"],
            "strain": styles.SEMAFORO["rojo"],
        },
    )

    fig.update_layout(
        xaxis_title=t("Semana"),
        yaxis_title=t("Valor del índice"),
        plot_bgcolor="white",
        font_color=styles.BRAND_TEXT,
        legend_title_text=t("Indicador"),
    )

    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        weekly[["rango_semana", "carga_total", "media_diaria", "desv_std", "monotonia", "strain"]].rename(
            columns={
                "rango_semana": "Semana",
                "carga_total": "Carga total semanal (UA)",
                "media_diaria": "Media diaria semanal",
                "desv_std": "Desv. estándar diaria",
                "monotonia": "Monotonía",
                "strain": "Strain semanal",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )

def tabla_resumen(df_filtrado):
    # df_filtrado["jugadora"] = (
    #     df_filtrado["nombre"].fillna("") + " " + df_filtrado["apellido"].fillna("")
    # ).str.strip()

    resumen = (
        df_filtrado.groupby(["nombre_jugadora"], as_index=False)
        .agg(
            carga_total=("ua", "sum"),
            rpe_promedio=("rpe", "mean"),
            sesiones=("ua", "count"),
        )
        .sort_values("carga_total", ascending=False)
    )

    resumen["carga_total"] = resumen["carga_total"].round(0)
    resumen["rpe_promedio"] = resumen["rpe_promedio"].round(2)
    resumen = resumen.fillna(0)
    resumen.index = resumen.index + 1

    st.dataframe(
        resumen.rename(
            columns={
                "nombre_jugadora": "Jugadora",
                "carga_total": "Carga total (UA)",
                "rpe_promedio": "RPE promedio",
                "sesiones": "Nº sesiones",
            }
        ),
    )

# ============================================================
# 📈 Estado de Carga
# ============================================================
import plotly.graph_objects as go
import streamlit as st
from modules.i18n.i18n import t

def plot_estado_carga_grupal(
    df,
    ventana_cronica: int = 42,
):
    if df is None or df.empty:
        st.info(t("No hay datos suficientes para el estado de carga grupal."))
        return

    col_cronica = f"fatiga_cronica_{ventana_cronica}d_ema"
    col_estado = f"estado_forma_{ventana_cronica}d_ema"

    # Validación mínima de columnas
    required = {"fecha_sesion", "ua_grupal", "fatiga_aguda_7d_ema", col_cronica}
    missing = required - set(df.columns)
    if missing:
        st.info(t("Faltan columnas para graficar el estado de carga grupal."))
        st.write("Missing:", list(missing))
        return

    fig = go.Figure()

    # UA diaria (barras)
    fig.add_trace(go.Bar(
        x=df["fecha_sesion"],
        y=df["ua_grupal"],
        name=t("UA diaria grupal"),
        #opacity=0.6,
        marker_color="rgba(150,150,150,0.4)"
    ))

    # Fatiga aguda (7d)
    fig.add_trace(go.Scatter(
        x=df["fecha_sesion"],
        y=df["fatiga_aguda_7d_ema"],
        name=t("Fatiga aguda (7d)"),
        mode="lines",
        line=dict(color="#E53935", width=2)
    ))

    # Fatiga crónica (ventana)
    fig.add_trace(go.Scatter(
        x=df["fecha_sesion"],
        y=df[col_cronica],
        name=t(f"Fatiga crónica ({ventana_cronica}d)"),
        mode="lines",
        line=dict(color="#1E88E5", width=2)
    ))

    # ✅ Recuperación (ventana) – solo si existe
    if col_estado in df.columns:
        fig.add_trace(go.Scatter(
            x=df["fecha_sesion"],
            y=df[col_estado],
            name=t("Estado de forma"),
            mode="lines",
            line=dict(color="#43A047", width=2, dash="dot")
        ))
    else:
        st.caption(t(f"No se encontró la columna {col_estado}. No se grafica estado de forma."))

    fig.update_layout(
        title=t("Carga, Fatiga y Estado de forma"),
        xaxis_title=t("Fecha"),
        yaxis_title=t("Carga (UA)"),
        barmode="overlay",
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        #height=420
    )

    st.plotly_chart(fig, use_container_width=False)

def plot_estado_carga_grupal_sma(
    df,
    ventana_cronica: int = 42,
):
    if df is None or df.empty:
        st.info(t("No hay datos suficientes para el estado de carga grupal."))
        return

    col_cronica = f"fatiga_cronica_{ventana_cronica}d_sma"
    col_estado = f"estado_forma_{ventana_cronica}d_sma"

    required = {"fecha_sesion", "ua_grupal", "fatiga_aguda_7d_sma", col_cronica}
    missing = required - set(df.columns)
    if missing:
        st.info(t("Faltan columnas para graficar el estado de carga grupal (SMA)."))
        st.write("Missing:", list(missing))
        return

    fig = go.Figure()

    # UA diaria
    fig.add_trace(go.Bar(
        x=df["fecha_sesion"],
        y=df["ua_grupal"],
        name=t("UA diaria grupal"),
        marker_color="rgba(150,150,150,0.4)"
    ))

    # Fatiga aguda SMA
    fig.add_trace(go.Scatter(
        x=df["fecha_sesion"],
        y=df["fatiga_aguda_7d_sma"],
        name=t("Fatiga aguda (7d SMA)"),
        mode="lines",
        line=dict(color="#E53935", width=2)
    ))

    # Fatiga crónica SMA
    fig.add_trace(go.Scatter(
        x=df["fecha_sesion"],
        y=df[col_cronica],
        name=t(f"Fatiga crónica ({ventana_cronica}d SMA)"),
        mode="lines",
        line=dict(color="#1E88E5", width=2)
    ))

    # Estado de forma SMA
    if col_estado in df.columns:
        fig.add_trace(go.Scatter(
            x=df["fecha_sesion"],
            y=df[col_estado],
            name=t("Estado de forma (SMA)"),
            mode="lines",
            line=dict(color="#43A047", width=2, dash="dot")
        ))

    fig.update_layout(
        title=t("Carga, Fatiga y Estado de forma (SMA)"),
        xaxis_title=t("Fecha"),
        yaxis_title=t("Carga (UA)"),
        barmode="overlay",
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    st.plotly_chart(fig, use_container_width=False)

# ============================================================
# Evolución temporal del wellness grupal
# ============================================================
def plot_wellness_evolucion_grupal(df_daily: pd.DataFrame):
    """
    Evolución temporal del wellness medio del equipo.
    Espera un DataFrame agregado por fecha_sesion.
    """
    if df_daily is None or df_daily.empty:
        st.info(t("No hay datos de wellness para mostrar."))
        return

    df_daily = df_daily.copy()
    df_daily["fecha_sesion"] = pd.to_datetime(df_daily["fecha_sesion"], errors="coerce")
    df_daily = df_daily.dropna(subset=["fecha_sesion"]).sort_values("fecha_sesion")

    cols_wellness = ["fatiga", "recuperacion", "sueno", "stress", "dolor"]
    cols_wellness = [c for c in cols_wellness if c in df_daily.columns]

    if "fecha_sesion" not in df_daily.columns or not cols_wellness:
        st.warning(t("Faltan columnas necesarias para graficar el wellness grupal."))
        return

    fig = go.Figure()

    for col in cols_wellness:
        fig.add_trace(
            go.Scatter(
                x=df_daily["fecha_sesion"],
                y=df_daily[col],
                mode="lines+markers",
                name=col.capitalize()
            )
        )

    if "ua" in df_daily.columns:
        fig.add_trace(
            go.Bar(
                x=df_daily["fecha_sesion"],
                y=df_daily["ua"],
                name="UA",
                opacity=0.25,
                yaxis="y2"
            )
        )

    fig.update_layout(
        title=t("Evolución temporal del wellness grupal"),
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
        font_color=styles.BRAND_TEXT,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        barmode="overlay",
    )

    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# Wellness por tipo de carga
# ============================================================
def plot_wellness_por_tipo_carga(df_tipo_carga: pd.DataFrame):
    """
    Muestra el wellness medio según tipo de carga.
    Espera un DataFrame agregado por tipo_carga.
    """
    if df_tipo_carga is None or df_tipo_carga.empty:
        st.info(t("No hay datos por tipo de carga para mostrar."))
        return

    if "tipo_carga" not in df_tipo_carga.columns:
        st.warning(t("Falta la columna tipo_carga."))
        return

    cols_wellness = ["fatiga", "recuperacion", "sueno", "stress", "dolor"]
    cols_wellness = [c for c in cols_wellness if c in df_tipo_carga.columns]

    if not cols_wellness:
        st.warning(t("No hay variables de wellness disponibles para graficar."))
        return

    df_plot = df_tipo_carga.copy()

    df_long = df_plot.melt(
        id_vars="tipo_carga",
        value_vars=cols_wellness,
        var_name="variable",
        value_name="valor"
    )

    fig = px.bar(
        df_long,
        x="tipo_carga",
        y="valor",
        color="variable",
        barmode="group",
        title=t("Wellness medio según tipo de carga"),
    )

    fig.update_layout(
        xaxis_title=t("Tipo de carga"),
        yaxis_title=t("Valor medio"),
        plot_bgcolor="white",
        font_color=styles.BRAND_TEXT,
    )

    fig.update_xaxes(tickangle=45)

    st.plotly_chart(fig, use_container_width=True)


def plot_distribucion_estado_forma(df_players: pd.DataFrame):
    """
    Distribución del estado de forma solo sobre jugadoras activas con dato válido.
    """

    if df_players is None or df_players.empty or "estado_forma_42d" not in df_players.columns:
        st.info(t("No hay datos suficientes para mostrar la distribución del estado de forma."))
        return

    df_plot = df_players.dropna(subset=["estado_forma_42d"]).copy()

    if df_plot.empty:
        st.info(t("No hay jugadoras con estado de forma calculable en el periodo seleccionado."))
        return

    def clasificar_estado_forma(x):
        if x < 0:
            return "Negativo"
        elif x <= 5:
            return "Neutro"
        else:
            return "Positivo"

    df_plot["zona_estado_forma"] = df_plot["estado_forma_42d"].apply(clasificar_estado_forma)

    dist = (
        df_plot["zona_estado_forma"]
        .value_counts()
        .rename_axis("zona")
        .reset_index(name="n_jugadoras")
    )

    total = len(df_plot)
    dist["porcentaje"] = dist["n_jugadoras"] / total * 100

    orden = ["Negativo", "Neutro", "Positivo"]
    dist["zona"] = pd.Categorical(dist["zona"], categories=orden, ordered=True)
    dist = dist.sort_values("zona")

    fig = px.bar(
        dist,
        x="zona",
        y="porcentaje",
        title=t("Distribución del estado de forma del grupo"),
        text="porcentaje",
    )

    fig.update_traces(
        texttemplate="%{text:.1f}%",
        textposition="outside"
    )

    fig.add_hline(
        y=15,
        line_dash="dash",
        line_color="red",
        annotation_text="Umbral alerta 15%",
        annotation_position="top right"
    )

    fig.update_layout(
        xaxis_title=t("Zona de estado de forma"),
        yaxis_title=t("% jugadoras activas evaluables"),
        yaxis_range=[0, max(35, dist["porcentaje"].max() + 10 if not dist.empty else 35)],
        plot_bgcolor="white",
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)

    n_sin_dato = df_players["estado_forma_42d"].isna().sum()
    st.caption(
        f"Jugadoras evaluables: {total} | Sin estado de forma calculable: {n_sin_dato}"
    )


## ACWR COMUN INDIVIDUAL Y GRUPAL
def plot_acwr(
    df_states: pd.DataFrame,
    ventana_cronica: int = 42,
    metodo: str = "sma",
    scope: str = "grupal",
    fecha_lesion=None,
    window_days: int = 7,
):
    """
    Gráfico de ACWR a partir de un DataFrame de estados de carga
    generado por compute_rpe_timeseries() o compute_rpe_timeseries_group().

    Parámetros:
    - df_states: salida de compute_rpe_timeseries o compute_rpe_timeseries_group
    - ventana_cronica: 28, 42 o 56
    - metodo: "sma" o "ema"
    - scope: "grupal" o "individual"
    - fecha_lesion: opcional, para análisis pre-lesión
    - window_days: días previos a mostrar antes de la lesión
    """

    if df_states is None or df_states.empty:
        st.info(t(f"No hay datos suficientes para mostrar el ACWR {scope}."))
        return

    metodo = metodo.lower().strip()
    if metodo not in {"sma", "ema"}:
        metodo = "sma"

    col_acwr = f"acwr_{ventana_cronica}d_{metodo}"

    if col_acwr not in df_states.columns:
        st.info(t(f"No se encontró la columna necesaria para mostrar el ACWR {scope}."))
        st.write("Missing:", col_acwr)
        return

    df = df_states[["fecha_sesion", col_acwr]].dropna().copy()
    df["fecha_sesion"] = pd.to_datetime(df["fecha_sesion"], errors="coerce")
    df = df.dropna(subset=["fecha_sesion"])
    df.rename(columns={col_acwr: "acwr"}, inplace=True)

    # =========================
    # FILTRADO PRE-LESIÓN
    # =========================
    if fecha_lesion is not None:
        fecha_lesion = pd.to_datetime(fecha_lesion)

        start = fecha_lesion - pd.Timedelta(days=window_days)
        end = fecha_lesion + pd.Timedelta(days=2)

        df = df[
            (df["fecha_sesion"] >= start) &
            (df["fecha_sesion"] <= end)
        ].copy()

    if df.empty:
        st.info(t(f"No hay suficientes datos para calcular el ACWR {scope}."))
        return

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
        color="black",
        strokeDash=[4, 2],
        opacity=0.7
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
        color="black",
        strokeWidth=2,
        interpolate="monotone"
    )

    pts = base.mark_circle(size=70).encode(
        color=alt.Color(
            "zona:N",
            scale=alt.Scale(
                domain=["Subcarga", "Sweet Spot", "Elevada", "Peligro"],
                range=["#64B5F6", "#2ca25f", "#fdae6b", "#d62728"],
            )
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
        align="left",
        dx=5,
        fontSize=11,
        color="#444"
    ).encode(
        y="y:Q",
        text="text:N"
    )

    layers = [bg, rules, line, pts, labels]

    # Marca visual de lesión
    if fecha_lesion is not None:
        lesion_rule = alt.Chart(
            pd.DataFrame({"fecha_lesion": [fecha_lesion]})
        ).mark_rule(
            color="red",
            strokeDash=[6, 4],
            strokeWidth=2
        ).encode(
            x="fecha_lesion:T"
        )

        lesion_text = alt.Chart(
            pd.DataFrame({
                "fecha_lesion": [fecha_lesion],
                "y": [max(2.0, df["acwr"].max())]
            })
        ).mark_text(
            text="Lesión",
            color="red",
            dx=6,
            dy=-8,
            align="left"
        ).encode(
            x="fecha_lesion:T",
            y="y:Q"
        )

        layers.extend([lesion_rule, lesion_text])

    titulo_metodo = "SMA" if metodo == "sma" else "EMA"
    titulo_scope = "grupal" if scope == "grupal" else "individual"

    titulo = (
        f"ACWR {titulo_scope} ({ventana_cronica}d · {titulo_metodo})"
        if fecha_lesion is None
        else f"ACWR previo a lesión (-{window_days}d · {titulo_metodo})"
    )

    chart = alt.layer(*layers).properties(
        height=320,
        width="container",
        title=t(titulo),
    )

    st.altair_chart(chart, use_container_width=True)
