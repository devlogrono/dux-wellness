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

    st.markdown(t(f"#### {titulo}"))

    st.caption(
        t(
            "La línea muestra la carga total acumulada por semana. "
            "Sirve para detectar aumentos, descensos o semanas de descarga dentro del periodo analizado."
        )
    )

    fig = px.line(
        weekly,
        x="rango_semana",
        y="carga_total",
        markers=True,
        title=None,
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

    conclusion = interpretar_carga_semanal(weekly)

    render_interpretacion_grafico(
        "Lectura automática del periodo",
        conclusion,
        color="#43A047"
    )

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

def interpretar_carga_semanal(weekly: pd.DataFrame) -> str:
    """
    Genera una lectura automática del gráfico de carga semanal.
    """

    if weekly is None or weekly.empty:
        return t("No hay datos suficientes para interpretar la carga semanal.")

    df = weekly.copy().sort_values(["anio", "semana"])

    if "carga_total" not in df.columns:
        return t("No hay columna de carga total para interpretar la evolución semanal.")

    ultima = df.iloc[-1]
    carga_ultima = ultima["carga_total"]
    semana_ultima = ultima["rango_semana"]

    carga_max = df["carga_total"].max()
    semana_max = df.loc[df["carga_total"].idxmax(), "rango_semana"]

    if len(df) < 2:
        return (
            f"Solo hay una semana disponible ({semana_ultima}), con una carga total de "
            f"{carga_ultima:.0f} UA. Se necesita más histórico para valorar la tendencia."
        )

    anterior = df.iloc[-2]
    carga_anterior = anterior["carga_total"]

    if carga_anterior > 0:
        cambio = ((carga_ultima / carga_anterior) - 1) * 100

        if cambio > 20:
            tendencia = (
                f"La última semana ha aumentado un {cambio:.1f}% respecto a la anterior. "
                f"Este incremento puede indicar una subida importante del estímulo de carga."
            )
        elif cambio < -20:
            tendencia = (
                f"La última semana ha descendido un {abs(cambio):.1f}% respecto a la anterior. "
                f"Esto puede reflejar una fase de descarga, menor exposición o menor disponibilidad."
            )
        else:
            tendencia = (
                f"La carga semanal se mantiene relativamente estable respecto a la semana anterior "
                f"({cambio:+.1f}%)."
            )
    else:
        tendencia = (
            "La semana anterior tuvo una carga muy baja o nula, por lo que el cambio porcentual "
            "debe interpretarse con cautela."
        )

    return (
        f"{tendencia} "
        f"La última semana ({semana_ultima}) acumula {carga_ultima:.0f} UA. "
        f"La semana con mayor carga del periodo fue {semana_max}, con {carga_max:.0f} UA."
    )


def interpretar_carga_diaria(daily: pd.DataFrame) -> str:
    """
    Genera una lectura automática del detalle diario de carga.
    """

    if daily is None or daily.empty:
        return t("No hay datos suficientes para interpretar la carga diaria.")

    df = daily.copy()

    if "carga_total" not in df.columns or "fecha_sesion" not in df.columns:
        return t("No hay columnas suficientes para interpretar la carga diaria.")

    total_periodo = df["carga_total"].sum()
    media_diaria = df["carga_total"].mean()
    dias = len(df)

    dias_sin_carga = int((df["carga_total"] == 0).sum())

    idx_max = df["carga_total"].idxmax()
    dia_max = df.loc[idx_max, "fecha_sesion"]
    carga_max = df.loc[idx_max, "carga_total"]

    if pd.notna(dia_max):
        dia_max_txt = pd.to_datetime(dia_max).strftime("%d-%m-%Y")
    else:
        dia_max_txt = "-"

    if total_periodo > 0:
        peso_dia_max = carga_max / total_periodo * 100
    else:
        peso_dia_max = 0

    if peso_dia_max > 35:
        concentracion_txt = (
            f"La carga está bastante concentrada: el día de mayor carga representa "
            f"el {peso_dia_max:.1f}% del total del periodo."
        )
    else:
        concentracion_txt = (
            "La carga no parece excesivamente concentrada en un único día."
        )

    if dias_sin_carga > 0:
        descanso_txt = (
            f" Hay {dias_sin_carga} día(s) sin carga registrada, que pueden corresponder "
            f"a descanso, ausencia de sesión o falta de registro."
        )
    else:
        descanso_txt = " No hay días sin carga registrada en el rango mostrado."

    return (
        f"En los {dias} días mostrados se acumulan {total_periodo:.0f} UA, "
        f"con una media diaria de {media_diaria:.0f} UA. "
        f"El día de mayor carga fue el {dia_max_txt}, con {carga_max:.0f} UA. "
        f"{concentracion_txt}"
        f"{descanso_txt}"
    )

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

    st.markdown(t("#### Detalle diario de carga (UA)"))

    st.caption(
        t(
            "Las barras muestran la carga acumulada en cada día del rango seleccionado. "
            "Ayuda a identificar picos de carga, días sin carga y posibles acumulaciones en pocos días."
        )
    )

    fig = px.bar(
        daily,
        x="fecha_label",
        y="carga_total",
        title=None,
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
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
    )

    st.plotly_chart(fig, use_container_width=True)

    conclusion = interpretar_carga_diaria(daily)

    render_interpretacion_grafico(
        "Lectura automática del periodo",
        conclusion,
        color="#43A047"
    )

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

def interpretar_monotonia_strain(weekly: pd.DataFrame) -> str:
    """
    Genera una lectura automática de monotonía y strain semanal.
    """

    if weekly is None or weekly.empty:
        return t("No hay datos suficientes para interpretar la monotonía y el strain.")

    required = {"rango_semana", "carga_total", "media_diaria", "desv_std", "monotonia", "strain"}
    missing = required - set(weekly.columns)

    if missing:
        return t("No hay columnas suficientes para generar una interpretación automática.")

    df = weekly.copy().sort_values(["anio", "semana"])

    df_valid = df.dropna(subset=["monotonia", "strain"]).copy()

    if df_valid.empty:
        return t("No hay datos válidos de monotonía y strain para interpretar.")

    ultima = df_valid.iloc[-1]

    semana = ultima["rango_semana"]
    monotonia = ultima["monotonia"]
    strain = ultima["strain"]
    carga_total = ultima["carga_total"]
    desv_std = ultima["desv_std"]

    # Monotonía
    if monotonia > 2.0:
        mono_txt = (
            f"La monotonía de la última semana es alta ({monotonia:.2f}). "
            f"Esto indica que la carga se ha repartido de forma muy uniforme entre días, "
            f"con poca variación del estímulo."
        )
    elif monotonia >= 1.5:
        mono_txt = (
            f"La monotonía de la última semana es moderada ({monotonia:.2f}). "
            f"Conviene vigilar si se repiten cargas similares durante muchos días seguidos."
        )
    else:
        mono_txt = (
            f"La monotonía de la última semana es adecuada ({monotonia:.2f}). "
            f"La carga presenta una variabilidad razonable entre días."
        )

    # Strain
    if len(df_valid) >= 2:
        strain_anterior = df_valid["strain"].iloc[-2]

        if pd.notna(strain_anterior) and strain_anterior > 0:
            cambio_strain = ((strain / strain_anterior) - 1) * 100

            if cambio_strain > 25:
                strain_txt = (
                    f" El strain ha aumentado un {cambio_strain:.1f}% respecto a la semana anterior, "
                    f"lo que sugiere una mayor acumulación de carga y fatiga."
                )
            elif cambio_strain < -25:
                strain_txt = (
                    f" El strain ha descendido un {abs(cambio_strain):.1f}% respecto a la semana anterior, "
                    f"lo que puede indicar una semana de descarga o menor exposición."
                )
            else:
                strain_txt = (
                    f" El strain se mantiene relativamente estable respecto a la semana anterior "
                    f"({cambio_strain:+.1f}%)."
                )
        else:
            strain_txt = (
                " No se puede comparar el strain con la semana anterior porque la referencia previa es baja o nula."
            )
    else:
        strain_txt = (
            " Se necesita más histórico semanal para valorar la tendencia del strain."
        )

    # Variabilidad
    if desv_std == 0:
        variabilidad_txt = (
            " La variabilidad diaria es nula, por lo que la monotonía debe interpretarse con cautela."
        )
    elif desv_std < 100:
        variabilidad_txt = (
            " La variabilidad diaria es baja, lo que puede indicar estímulos muy parecidos entre días."
        )
    else:
        variabilidad_txt = (
            " La variabilidad diaria permite diferenciar mejor días de mayor y menor carga."
        )

    return (
        f"En la semana {semana}, la carga total fue de {carga_total:.0f} UA. "
        f"{mono_txt}"
        f"{strain_txt}"
        f"{variabilidad_txt}"
    )

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
        st.warning(t("No hay datos suficientes para calcular monotonía y strain."))
        return

    out = df.copy()
    out["ua"] = pd.to_numeric(out["ua"], errors="coerce").fillna(0)
    out["fecha_sesion"] = pd.to_datetime(out["fecha_sesion"], errors="coerce").dt.normalize()
    out = out.dropna(subset=["fecha_sesion"])

    if out.empty:
        st.info(t("No hay datos válidos para mostrar."))
        return

    # =====================================================
    # 1) Carga diaria real
    # =====================================================
    daily_real = (
        out.groupby("fecha_sesion", as_index=False)["ua"]
        .sum()
        .rename(columns={"ua": "ua_diaria"})
        .sort_values("fecha_sesion")
    )

    # =====================================================
    # 2) Serie diaria continua con ceros
    # =====================================================
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

    # =====================================================
    # 3) Variables semanales
    # =====================================================
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

    # =====================================================
    # 4) Resumen semanal
    # =====================================================
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

    # =====================================================
    # Título + caption explicativo
    # =====================================================
    st.markdown(t(f"#### Monotonía y strain semanal ({titulo_scope})"))

    st.caption(
        t(
            "La monotonía indica si la carga diaria se repite de forma muy parecida durante la semana. "
            "El strain combina la carga total semanal con esa monotonía: valores altos sugieren mayor acumulación de fatiga."
        )
    )

    # =====================================================
    # Gráfico
    # =====================================================
    fig = px.line(
        weekly,
        x="rango_semana",
        y=["monotonia", "strain"],
        markers=True,
        title=None,
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
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)

    # =====================================================
    # Lectura automática
    # =====================================================
    conclusion = interpretar_monotonia_strain(weekly)

    render_interpretacion_grafico(
        "Lectura automática del periodo",
        conclusion,
        color="#43A047"
    )

    # =====================================================
    # Tabla
    # =====================================================
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

    df = df.copy()
    df["fecha_sesion"] = pd.to_datetime(df["fecha_sesion"], errors="coerce")
    df = df.dropna(subset=["fecha_sesion"]).sort_values("fecha_sesion")

    col_aguda = "fatiga_aguda_7d_ema"
    col_cronica = f"fatiga_cronica_{ventana_cronica}d_ema"
    col_estado = f"estado_forma_{ventana_cronica}d_ema"

    # Validación mínima de columnas
    required = {"fecha_sesion", "ua_grupal", col_aguda, col_cronica}
    missing = required - set(df.columns)

    if missing:
        st.info(t("Faltan columnas para graficar el estado de carga grupal."))
        st.write("Missing:", list(missing))
        return

    # =====================================================
    # Título + caption explicativo
    # =====================================================
    st.markdown(t("#### Carga, Fatiga y Estado de forma"))

    st.caption(
        t(
            "Las barras grises muestran la carga diaria acumulada del grupo. "
            "La línea roja representa la fatiga aguda reciente y la azul la fatiga crónica o carga de referencia. "
            "La línea verde resume el estado de forma: valores positivos sugieren mejor adaptación y valores negativos indican que la carga reciente está pesando más que la base acumulada."
        )
    )

    # =====================================================
    # Gráfico
    # =====================================================
    fig = go.Figure()

    # UA diaria grupal
    fig.add_trace(go.Bar(
        x=df["fecha_sesion"],
        y=df["ua_grupal"],
        name=t("UA diaria grupal"),
        marker_color="rgba(150,150,150,0.4)"
    ))

    # Fatiga aguda EMA
    fig.add_trace(go.Scatter(
        x=df["fecha_sesion"],
        y=df[col_aguda],
        name=t("Fatiga aguda (7d)"),
        mode="lines",
        line=dict(color="#E53935", width=2)
    ))

    # Fatiga crónica EMA
    fig.add_trace(go.Scatter(
        x=df["fecha_sesion"],
        y=df[col_cronica],
        name=t(f"Fatiga crónica ({ventana_cronica}d)"),
        mode="lines",
        line=dict(color="#1E88E5", width=2)
    ))

    # Estado de forma EMA
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
        xaxis_title=t("Fecha"),
        yaxis_title=t("Carga (UA)"),
        barmode="overlay",
        plot_bgcolor="white",
        font_color=styles.BRAND_TEXT,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
    )

    st.plotly_chart(fig, use_container_width=True)

    # =====================================================
    # Lectura automática
    # =====================================================
    conclusion = interpretar_estado_carga_grupal(
        df,
        ventana_cronica=ventana_cronica
    )

    render_interpretacion_grafico(
        "Lectura automática del periodo",
        conclusion,
        color="#43A047"
    )

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
def interpretar_wellness_evolucion_diaria(
    df_daily: pd.DataFrame,
    scope: str = "grupal"
) -> str:
    """
    Genera una lectura automática para la evolución diaria del wellness.
    Escala:
    - valores bajos = mejor estado
    - valores altos = peor estado
    """

    sujeto = "El grupo" if scope == "grupal" else "La jugadora"
    sujeto_lower = "el grupo" if scope == "grupal" else "la jugadora"

    if df_daily is None or df_daily.empty:
        return t("No hay datos suficientes para interpretar la evolución diaria del wellness.")

    df = df_daily.copy()

    if "fecha_sesion" not in df.columns:
        return t("No se encontró una columna de fecha para interpretar el wellness diario.")

    cols_wellness = ["energia", "recuperacion", "sueno", "stress", "dolor"]
    cols_wellness = [c for c in cols_wellness if c in df.columns]

    if not cols_wellness:
        return t("No hay variables de wellness suficientes para generar una interpretación.")

    df["fecha_sesion"] = pd.to_datetime(df["fecha_sesion"], errors="coerce")
    df = df.dropna(subset=["fecha_sesion"]).sort_values("fecha_sesion")

    for col in cols_wellness:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["wellness_medio"] = df[cols_wellness].mean(axis=1, skipna=True)
    df = df.dropna(subset=["wellness_medio"]).copy()

    if df.empty:
        return t("No hay valores válidos de wellness para interpretar.")

    labels_map = {
        "energia": "energía",
        "recuperacion": "recuperación",
        "sueno": "sueño",
        "stress": "stress",
        "dolor": "dolor",
    }

    ultimo = df.iloc[-1]
    fecha_ultimo = ultimo["fecha_sesion"].strftime("%d-%m-%Y")
    wellness_actual = ultimo["wellness_medio"]

    # Estado actual
    if wellness_actual <= 2:
        estado_txt = (
            f"{sujeto} muestra un wellness favorable en el último día registrado "
            f"({fecha_ultimo}), con un valor medio de {wellness_actual:.2f}."
        )
    elif wellness_actual <= 3:
        estado_txt = (
            f"{sujeto} muestra un wellness en zona de atención en el último día registrado "
            f"({fecha_ultimo}), con un valor medio de {wellness_actual:.2f}."
        )
    else:
        estado_txt = (
            f"{sujeto} muestra un wellness en zona de alerta en el último día registrado "
            f"({fecha_ultimo}), con un valor medio de {wellness_actual:.2f}."
        )

    # Tendencia reciente
    tendencia_txt = ""

    if len(df) >= 6:
        last3 = df["wellness_medio"].tail(3).mean()
        prev3 = df["wellness_medio"].tail(6).head(3).mean()

        if pd.notna(prev3):
            cambio = last3 - prev3

            if cambio > 0.25:
                tendencia_txt = (
                    f" En los últimos 3 días el wellness ha empeorado "
                    f"en {cambio:.2f} puntos respecto a los 3 días anteriores."
                )
            elif cambio < -0.25:
                tendencia_txt = (
                    f" En los últimos 3 días el wellness ha mejorado "
                    f"en {abs(cambio):.2f} puntos respecto a los 3 días anteriores."
                )
            else:
                tendencia_txt = (
                    " En los últimos días el wellness se mantiene relativamente estable."
                )

    # Variable más comprometida del periodo
    medias = df[cols_wellness].mean(numeric_only=True).sort_values(ascending=False)
    var_peor = medias.index[0]
    valor_peor = medias.iloc[0]
    var_peor_txt = labels_map.get(var_peor, var_peor)

    if valor_peor > 3:
        variable_txt = (
            f" La variable más comprometida del periodo es {var_peor_txt}, "
            f"con un valor medio de {valor_peor:.2f}, por encima del umbral de alerta."
        )
    elif valor_peor > 2:
        variable_txt = (
            f" La variable que más conviene vigilar es {var_peor_txt}, "
            f"con un valor medio de {valor_peor:.2f}."
        )
    else:
        variable_txt = (
            f" Ninguna variable aparece claramente comprometida; la más alta es "
            f"{var_peor_txt} ({valor_peor:.2f})."
        )

    # Variables en alerta último día
    variables_alerta = [
        labels_map.get(col, col)
        for col in cols_wellness
        if pd.notna(ultimo[col]) and ultimo[col] > 3
    ]

    if variables_alerta:
        alerta_txt = f" En el último día aparecen en alerta: {', '.join(variables_alerta)}."
    else:
        alerta_txt = f" En el último día no se observan variables en alerta clara para {sujeto_lower}."

    return estado_txt + tendencia_txt + variable_txt + alerta_txt

def plot_wellness_evolucion_grupal(
    df_daily: pd.DataFrame,
    scope: str = "grupal"
):
    """
    Evolución temporal del wellness.
    Sirve para gráfico grupal e individual según scope.
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
        st.warning(t("Faltan columnas necesarias para graficar el wellness."))
        return

    for col in cols_wellness + ["ua"]:
        if col in df_plot.columns:
            df_plot[col] = pd.to_numeric(df_plot[col], errors="coerce")

    df_plot["wellness_medio"] = df_plot[cols_wellness].mean(axis=1, skipna=True)

    sujeto = "grupal" if scope == "grupal" else "individual"

    # =====================================================
    # Título + caption
    # =====================================================
    st.markdown(t(f"#### Evolución diaria del wellness {sujeto}"))

    st.caption(
        t(
            "La línea principal muestra el wellness medio diario. "
            "En esta escala, valores más bajos indican mejor estado y valores más altos indican mayor fatiga, malestar o alerta."
        )
    )

    # =====================================================
    # Gráfico
    # =====================================================
    fig = go.Figure()

    # Bandas de interpretación
    fig.add_hrect(
        y0=1,
        y1=2,
        fillcolor="#C8E6C9",
        opacity=0.25,
        line_width=0,
    )

    fig.add_hrect(
        y0=2,
        y1=3,
        fillcolor="#FFE0B2",
        opacity=0.25,
        line_width=0,
    )

    fig.add_hrect(
        y0=3,
        y1=5,
        fillcolor="#FFCDD2",
        opacity=0.25,
        line_width=0,
    )

    # UA opcional en segundo eje
    if "ua" in df_plot.columns:
        fig.add_trace(
            go.Bar(
                x=df_plot["fecha_sesion"],
                y=df_plot["ua"],
                name=t("UA"),
                marker_color="rgba(150,150,150,0.25)",
                yaxis="y2",
            )
        )

    # Línea principal: wellness medio
    fig.add_trace(
        go.Scatter(
            x=df_plot["fecha_sesion"],
            y=df_plot["wellness_medio"],
            mode="lines+markers",
            name=t("Wellness medio"),
            line=dict(color="#263238", width=4),
            marker=dict(size=8),
        )
    )

    label_cols = {
        "energia": t("Energía"),
        "recuperacion": t("Recuperación"),
        "sueno": t("Sueño"),
        "stress": t("Stress"),
        "dolor": t("Dolor"),
    }

    color_cols = {
        "energia": "#1E88E5",
        "recuperacion": "#43A047",
        "sueno": "#8E24AA",
        "stress": "#FB8C00",
        "dolor": "#E53935",
    }

    # Variables individuales
    for col in cols_wellness:
        fig.add_trace(
            go.Scatter(
                x=df_plot["fecha_sesion"],
                y=df_plot[col],
                mode="lines+markers",
                name=label_cols.get(col, col.capitalize()),
                line=dict(
                    color=color_cols.get(col, "#607D8B"),
                    width=2,
                    dash="dot"
                ),
                marker=dict(size=6),
                opacity=0.85,
            )
        )

    # Líneas de referencia
    fig.add_hline(
        y=2,
        line_dash="dash",
        line_color="#43A047",
        annotation_text=t("Favorable"),
        annotation_position="bottom right"
    )

    fig.add_hline(
        y=3,
        line_dash="dash",
        line_color="#E53935",
        annotation_text=t("Alerta"),
        annotation_position="top right"
    )

    fig.update_layout(
        xaxis_title=t("Fecha"),
        yaxis=dict(
            title=t("Wellness medio"),
            range=[1, 5],
        ),
        yaxis2=dict(
            title=t("UA"),
            overlaying="y",
            side="right",
            showgrid=False,
            rangemode="tozero",
        ),
        plot_bgcolor="white",
        font_color=styles.BRAND_TEXT,
        hovermode="x unified",
        barmode="overlay",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.08,
            xanchor="left",
            x=0
        ),
        margin=dict(t=70, b=40),
    )

    fig.update_xaxes(
        tickformat="%d %b",
        tickangle=0,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displaylogo": False,
            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        }
    )

    # =====================================================
    # Lectura automática
    # =====================================================
    conclusion = interpretar_wellness_evolucion_diaria(
        df_plot,
        scope=scope
    )

    render_interpretacion_grafico(
        "Lectura automática del periodo",
        conclusion,
        color="#43A047"
    )


# ============================================================
# Wellness por tipo de carga
# ============================================================
def interpretar_wellness_tipo_carga(
    df_tipo_carga: pd.DataFrame,
    scope: str = "grupal",
) -> str:
    """
    Genera una lectura automática del wellness según tipo de carga.
    Escala:
    - valores bajos = mejor estado
    - valores altos = peor estado
    """

    sujeto = "El grupo" if scope == "grupal" else "La jugadora"

    if df_tipo_carga is None or df_tipo_carga.empty:
        return t("No hay datos suficientes para interpretar el wellness por tipo de carga.")

    df = df_tipo_carga.copy()

    if "tipo_carga" not in df.columns:
        return t("No se encontró la columna de tipo de carga.")

    cols_wellness = ["energia", "recuperacion", "sueno", "stress", "dolor"]
    cols_wellness = [c for c in cols_wellness if c in df.columns]

    if not cols_wellness:
        return t("No hay variables de wellness suficientes para interpretar el gráfico.")

    for col in cols_wellness:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if "wellness_medio" not in df.columns:
        df["wellness_medio"] = df[cols_wellness].mean(axis=1, skipna=True)

    df = df.dropna(subset=["wellness_medio"]).copy()

    if df.empty:
        return t("No hay valores válidos de wellness para interpretar.")

    # Mejor y peor tipo de carga
    peor = df.sort_values("wellness_medio", ascending=False).iloc[0]
    mejor = df.sort_values("wellness_medio", ascending=True).iloc[0]

    peor_tipo = peor["tipo_carga"]
    peor_val = peor["wellness_medio"]

    mejor_tipo = mejor["tipo_carga"]
    mejor_val = mejor["wellness_medio"]

    labels_map = {
        "energia": "energía",
        "recuperacion": "recuperación",
        "sueno": "sueño",
        "stress": "stress",
        "dolor": "dolor",
    }

    # Variable más comprometida dentro del peor tipo de carga
    valores_peor = peor[cols_wellness].sort_values(ascending=False)
    var_peor = valores_peor.index[0]
    var_peor_val = valores_peor.iloc[0]
    var_peor_txt = labels_map.get(var_peor, var_peor)

    # Estado del peor tipo de carga
    if peor_val > 3:
        estado_peor = (
            f"{sujeto} muestra la peor respuesta global en {peor_tipo}, "
            f"con un wellness medio de {peor_val:.2f}, situado en zona de alerta."
        )
    elif peor_val > 2:
        estado_peor = (
            f"{sujeto} muestra una respuesta que conviene vigilar en {peor_tipo}, "
            f"con un wellness medio de {peor_val:.2f}."
        )
    else:
        estado_peor = (
            f"No hay tipos de carga claramente comprometidos. "
            f"El valor más alto aparece en {peor_tipo}, con {peor_val:.2f}."
        )

    # Diferencia entre mejor y peor
    diferencia = peor_val - mejor_val

    if diferencia >= 0.75:
        diferencia_txt = (
            f" La diferencia respecto al tipo de carga con mejor respuesta "
            f"({mejor_tipo}, {mejor_val:.2f}) es relevante ({diferencia:.2f} puntos)."
        )
    elif diferencia >= 0.3:
        diferencia_txt = (
            f" La diferencia con el tipo de carga mejor valorado "
            f"({mejor_tipo}, {mejor_val:.2f}) es moderada ({diferencia:.2f} puntos)."
        )
    else:
        diferencia_txt = (
            " Las diferencias entre tipos de carga son pequeñas; la respuesta es bastante similar "
            "entre los distintos estímulos."
        )

    variable_txt = (
        f" En {peor_tipo}, la variable más comprometida es {var_peor_txt} "
        f"({var_peor_val:.2f})."
    )

    return estado_peor + diferencia_txt + variable_txt


def plot_wellness_por_tipo_carga(
    df_tipo_carga: pd.DataFrame,
    scope: str = "grupal",
):
    """
    Muestra el wellness medio según tipo de carga.
    Sirve para grupal e individual según scope.

    Escala:
    - valores bajos = mejor estado
    - valores altos = peor estado
    """

    if df_tipo_carga is None or df_tipo_carga.empty:
        st.info(t("No hay datos por tipo de carga para mostrar."))
        return

    if "tipo_carga" not in df_tipo_carga.columns:
        st.warning(t("Falta la columna tipo_carga."))
        return

    cols_wellness = ["energia", "recuperacion", "sueno", "stress", "dolor"]
    cols_wellness = [c for c in cols_wellness if c in df_tipo_carga.columns]

    if not cols_wellness:
        st.warning(t("No hay variables de wellness disponibles para graficar."))
        return

    df_plot = df_tipo_carga.copy()

    for col in cols_wellness + ["rpe", "ua"]:
        if col in df_plot.columns:
            df_plot[col] = pd.to_numeric(df_plot[col], errors="coerce")

    df_plot["wellness_medio"] = df_plot[cols_wellness].mean(axis=1, skipna=True)
    df_plot = df_plot.dropna(subset=["wellness_medio"]).copy()

    if df_plot.empty:
        st.info(t("No hay valores válidos para mostrar el wellness por tipo de carga."))
        return

    # Orden: mejor respuesta arriba, peor abajo
    df_plot = df_plot.sort_values("wellness_medio", ascending=True)

    sujeto_titulo = "del grupo" if scope == "grupal" else "de la jugadora"

    # =====================================================
    # Título + caption
    # =====================================================
    st.markdown(t(f"#### Wellness medio según tipo de carga {sujeto_titulo}"))

    st.caption(
        t(
            "El gráfico compara la respuesta media de wellness para cada tipo de carga. "
            "En esta escala, valores más bajos indican mejor estado y valores más altos indican mayor fatiga, malestar o alerta."
        )
    )

    # =====================================================
    # Gráfico
    # =====================================================
    fig = go.Figure()

    # Bandas de interpretación en eje X
    fig.add_vrect(
        x0=1,
        x1=2,
        fillcolor="#C8E6C9",
        opacity=0.25,
        line_width=0,
    )

    fig.add_vrect(
        x0=2,
        x1=3,
        fillcolor="#FFE0B2",
        opacity=0.25,
        line_width=0,
    )

    fig.add_vrect(
        x0=3,
        x1=5,
        fillcolor="#FFCDD2",
        opacity=0.25,
        line_width=0,
    )

    # Barra principal: wellness medio
    fig.add_trace(
        go.Bar(
            x=df_plot["wellness_medio"],
            y=df_plot["tipo_carga"],
            orientation="h",
            name=t("Wellness medio"),
            marker_color="#263238",
            opacity=0.75,
            hovertemplate=(
                "<b>%{y}</b><br>"
                + t("Wellness medio")
                + ": %{x:.2f}<extra></extra>"
            ),
        )
    )

    # Variables individuales como puntos
    label_cols = {
        "energia": t("Energía"),
        "recuperacion": t("Recuperación"),
        "sueno": t("Sueño"),
        "stress": t("Stress"),
        "dolor": t("Dolor"),
    }

    color_cols = {
        "energia": "#1E88E5",
        "recuperacion": "#43A047",
        "sueno": "#8E24AA",
        "stress": "#FB8C00",
        "dolor": "#E53935",
    }

    for col in cols_wellness:
        fig.add_trace(
            go.Scatter(
                x=df_plot[col],
                y=df_plot["tipo_carga"],
                mode="markers",
                name=label_cols.get(col, col.capitalize()),
                marker=dict(
                    size=10,
                    color=color_cols.get(col, "#607D8B"),
                    symbol="diamond",
                    line=dict(width=1, color="white"),
                ),
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    + label_cols.get(col, col.capitalize())
                    + ": %{x:.2f}<extra></extra>"
                ),
            )
        )

    # Líneas de referencia
    fig.add_vline(
        x=2,
        line_dash="dash",
        line_color="#43A047",
        annotation_text=t("Favorable"),
        annotation_position="top"
    )

    fig.add_vline(
        x=3,
        line_dash="dash",
        line_color="#E53935",
        annotation_text=t("Alerta"),
        annotation_position="top"
    )

    fig.update_layout(
        xaxis_title=t("Wellness medio"),
        yaxis_title=t("Tipo de carga"),
        xaxis=dict(range=[1, 5]),
        plot_bgcolor="white",
        font_color=styles.BRAND_TEXT,
        hovermode="closest",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.08,
            xanchor="left",
            x=0
        ),
        margin=dict(t=70, b=40, l=20, r=20),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displaylogo": False,
            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        }
    )

    # =====================================================
    # Lectura automática
    # =====================================================
    conclusion = interpretar_wellness_tipo_carga(
        df_plot,
        scope=scope,
    )

    render_interpretacion_grafico(
        "Lectura automática del periodo",
        conclusion,
        color="#43A047"
    )

    # =====================================================
    # Tabla resumen
    # =====================================================
    columnas_tabla = ["tipo_carga", "wellness_medio"] + cols_wellness
    columnas_extra = [c for c in ["rpe", "ua"] if c in df_plot.columns]
    columnas_tabla += columnas_extra

    with st.expander(t("Ver tabla resumen"), expanded=False):
        st.dataframe(
            df_plot[columnas_tabla].round(2).rename(
                columns={
                    "tipo_carga": t("Tipo de carga"),
                    "wellness_medio": t("Wellness medio"),
                    "energia": t("Energía"),
                    "recuperacion": t("Recuperación"),
                    "sueno": t("Sueño"),
                    "stress": t("Stress"),
                    "dolor": t("Dolor"),
                    "rpe": t("RPE"),
                    "ua": t("UA"),
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


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
def interpretar_acwr(
    df_acwr: pd.DataFrame,
    scope: str = "grupal",
) -> str:
    """
    Genera una lectura automática del gráfico ACWR.
    Espera un dataframe con columnas:
    - fecha_sesion
    - acwr
    - zona
    """

    if df_acwr is None or df_acwr.empty:
        return t("No hay datos suficientes para interpretar el ACWR.")

    required = {"fecha_sesion", "acwr", "zona"}
    missing = required - set(df_acwr.columns)

    if missing:
        return t("No hay columnas suficientes para generar una lectura automática del ACWR.")

    df = df_acwr.copy()
    df["fecha_sesion"] = pd.to_datetime(df["fecha_sesion"], errors="coerce")
    df = df.dropna(subset=["fecha_sesion", "acwr"]).sort_values("fecha_sesion")

    if df.empty:
        return t("No hay datos válidos para interpretar el ACWR.")

    ultimo = df.iloc[-1]
    acwr_actual = ultimo["acwr"]
    zona_actual = ultimo["zona"]

    total = len(df)
    dias_peligro = int((df["acwr"] >= 1.5).sum())
    dias_elevada = int(((df["acwr"] >= 1.3) & (df["acwr"] < 1.5)).sum())
    dias_sweet = int(((df["acwr"] >= 0.8) & (df["acwr"] < 1.3)).sum())
    dias_subcarga = int((df["acwr"] < 0.8).sum())

    pct_peligro = dias_peligro / total * 100 if total > 0 else 0
    pct_elevada = dias_elevada / total * 100 if total > 0 else 0
    pct_sweet = dias_sweet / total * 100 if total > 0 else 0
    pct_subcarga = dias_subcarga / total * 100 if total > 0 else 0

    # Tendencia reciente: últimos 3 valores vs 3 anteriores
    tendencia_txt = ""

    if len(df) >= 6:
        last3 = df["acwr"].tail(3).mean()
        prev3 = df["acwr"].tail(6).head(3).mean()

        if pd.notna(prev3):
            cambio = last3 - prev3

            if cambio > 0.15:
                tendencia_txt = (
                    " En los últimos días el ACWR muestra una tendencia ascendente, "
                    "por lo que conviene vigilar si el aumento de carga se mantiene."
                )
            elif cambio < -0.15:
                tendencia_txt = (
                    " En los últimos días el ACWR muestra una tendencia descendente, "
                    "lo que puede indicar una fase de descarga o menor exposición reciente."
                )
            else:
                tendencia_txt = (
                    " En los últimos días el ACWR se mantiene relativamente estable."
                )

    # Interpretación del último valor
    if acwr_actual < 0.8:
        estado_txt = (
            f"El ACWR actual es {acwr_actual:.2f}, situado en zona de subcarga. "
            "Esto indica que la carga reciente está por debajo de la referencia crónica; "
            "puede ser adecuado en una fase de descarga, pero si se mantiene podría reflejar falta de estímulo."
        )
    elif acwr_actual < 1.3:
        estado_txt = (
            f"El ACWR actual es {acwr_actual:.2f}, dentro de la zona óptima. "
            "La carga reciente está equilibrada respecto a la carga que se venía tolerando."
        )
    elif acwr_actual < 1.5:
        estado_txt = (
            f"El ACWR actual es {acwr_actual:.2f}, en zona elevada. "
            "La carga reciente está por encima de la referencia habitual, por lo que conviene controlar la respuesta."
        )
    else:
        estado_txt = (
            f"El ACWR actual es {acwr_actual:.2f}, en zona de peligro. "
            "La carga reciente supera claramente la referencia crónica, lo que requiere especial vigilancia."
        )

    # Lectura global del periodo
    if pct_peligro > 25:
        periodo_txt = (
            f" Durante el periodo analizado, el {pct_peligro:.1f}% de los días estuvo en zona de peligro."
        )
    elif pct_elevada + pct_peligro > 30:
        periodo_txt = (
            f" Durante el periodo analizado, el {pct_elevada + pct_peligro:.1f}% de los días estuvo en zona elevada o de peligro."
        )
    elif pct_sweet >= 60:
        periodo_txt = (
            f" La mayor parte del periodo se mantuvo en zona óptima ({pct_sweet:.1f}% de los días)."
        )
    elif pct_subcarga > 40:
        periodo_txt = (
            f" Una parte importante del periodo estuvo en subcarga ({pct_subcarga:.1f}% de los días)."
        )
    else:
        periodo_txt = (
            " El periodo muestra una distribución mixta entre zonas de carga."
        )

    return estado_txt + periodo_txt + tendencia_txt

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

    # =====================================================
    # FILTRADO PRE-LESIÓN
    # =====================================================
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

    # =====================================================
    # Clasificación por zonas
    # =====================================================
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

    # =====================================================
    # Título + caption explicativo
    # =====================================================
    titulo_metodo = "SMA" if metodo == "sma" else "EMA"
    titulo_scope = "grupal" if scope == "grupal" else "individual"

    titulo = (
        f"ACWR {titulo_scope} ({ventana_cronica}d · {titulo_metodo})"
        if fecha_lesion is None
        else f"ACWR previo a lesión (-{window_days}d · {titulo_metodo})"
    )

    st.markdown(t(f"#### {titulo}"))

    st.caption(
        t(
            "El ACWR compara la carga reciente con la carga crónica de referencia. "
            "La zona verde indica equilibrio, la azul subcarga, la naranja carga elevada y la roja posible exceso de carga."
        )
    )

    # =====================================================
    # Bandas de referencia
    # =====================================================
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
            ),
            legend=alt.Legend(title=t("Zona"))
        ),
        tooltip=[
            alt.Tooltip("fecha_sesion:T", title=t("Fecha")),
            alt.Tooltip("acwr:Q", title="ACWR", format=".2f"),
            alt.Tooltip("zona:N", title=t("Zona")),
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

    # =====================================================
    # Marca visual de lesión
    # =====================================================
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

    chart = alt.layer(*layers).properties(
        height=320,
        width="container",
    )

    st.altair_chart(chart, use_container_width=True)

    # =====================================================
    # Lectura automática
    # =====================================================
    conclusion = interpretar_acwr(
        df,
        scope=scope
    )

    render_interpretacion_grafico(
        "Lectura automática del periodo",
        conclusion,
        color="#43A047"
    )


def render_interpretacion_grafico(titulo: str, texto: str, color: str = "#1E88E5"):
    """
    Muestra una caja de interpretación debajo de un gráfico.
    """
    st.markdown(
        f"""
        <div style="
            background-color:#F8F9FA;
            border-left:5px solid {color};
            padding:14px 18px;
            border-radius:8px;
            margin-top:10px;
            margin-bottom:14px;
            text-align:justify;
        ">
            <b>{t(titulo)}:</b><br>
            {t(texto)}
        </div>
        """,
        unsafe_allow_html=True
    )

def interpretar_estado_carga_grupal(
    df: pd.DataFrame,
    ventana_cronica: int = 42,
) -> str:
    """
    Genera una interpretación automática del gráfico de estado de carga grupal.
    Usa las columnas EMA del dataframe de estado de carga.
    """

    if df is None or df.empty:
        return t("No hay datos suficientes para generar una interpretación automática.")

    col_aguda = "fatiga_aguda_7d_ema"
    col_cronica = f"fatiga_cronica_{ventana_cronica}d_ema"
    col_estado = f"estado_forma_{ventana_cronica}d_ema"

    required = {"fecha_sesion", "ua_grupal", col_aguda, col_cronica, col_estado}
    missing = required - set(df.columns)

    if missing:
        return t("No hay columnas suficientes para generar una interpretación automática del estado de carga.")

    out = df.copy()
    out["fecha_sesion"] = pd.to_datetime(out["fecha_sesion"], errors="coerce")
    out = out.dropna(subset=["fecha_sesion"]).sort_values("fecha_sesion")

    if out.empty:
        return t("No hay datos válidos para interpretar el estado de carga.")

    last = out.iloc[-1]

    ua_actual = last["ua_grupal"]
    fatiga_aguda = last[col_aguda]
    fatiga_cronica = last[col_cronica]
    estado_forma = last[col_estado]

    ratio = fatiga_aguda / fatiga_cronica if fatiga_cronica and fatiga_cronica > 0 else None

    # Cambio reciente: últimos 3 días vs 3 anteriores
    cambio_txt = ""
    if len(out) >= 6:
        last3 = out["ua_grupal"].tail(3).mean()
        prev3 = out["ua_grupal"].tail(6).head(3).mean()

        if prev3 > 0:
            cambio = ((last3 / prev3) - 1) * 100

            if cambio > 20:
                cambio_txt = (
                    f" Además, la carga media de los últimos 3 días ha aumentado "
                    f"un {cambio:.1f}% respecto a los 3 días anteriores, lo que sugiere "
                    f"un incremento reciente importante."
                )
            elif cambio < -20:
                cambio_txt = (
                    f" Además, la carga media de los últimos 3 días ha descendido "
                    f"un {abs(cambio):.1f}% respecto a los 3 días anteriores, lo que puede indicar "
                    f"una fase de descarga o menor exposición al entrenamiento."
                )
            else:
                cambio_txt = (
                    f" La carga reciente se mantiene relativamente estable "
                    f"respecto a los días anteriores."
                )

    # Interpretación principal
    if ratio is None:
        estado_carga_txt = (
            "No hay suficiente referencia crónica para valorar correctamente "
            "la relación entre fatiga reciente y carga acumulada."
        )
    elif ratio > 1.5:
        estado_carga_txt = (
            "La fatiga aguda está claramente por encima de la fatiga crónica. "
            "Esto indica que la carga reciente del grupo supera con fuerza su referencia habitual, "
            "por lo que conviene vigilar signos de fatiga, molestias o bajo rendimiento."
        )
    elif ratio >= 1.3:
        estado_carga_txt = (
            "La fatiga aguda se encuentra por encima de la referencia crónica. "
            "El grupo está entrando en una zona de carga elevada, por lo que sería recomendable "
            "controlar la respuesta individual de las jugadoras."
        )
    elif ratio >= 0.8:
        estado_carga_txt = (
            "La relación entre fatiga aguda y crónica se mantiene en una zona controlada. "
            "Esto sugiere que la carga reciente está bastante alineada con la carga que el grupo "
            "venía tolerando."
        )
    else:
        estado_carga_txt = (
            "La fatiga aguda está por debajo de la referencia crónica. "
            "Esto puede reflejar una fase de descarga, recuperación o una posible falta de estímulo "
            "si se mantiene durante varios días."
        )

    # Estado de forma
    if pd.isna(estado_forma):
        forma_txt = "El estado de forma no es interpretable con los datos actuales."
    elif estado_forma < 0:
        forma_txt = (
            f" El estado de forma es negativo ({estado_forma:.1f}), lo que indica que "
            f"la carga reciente está pesando más que la base acumulada."
        )
    elif estado_forma <= 5:
        forma_txt = (
            f" El estado de forma es prácticamente neutro ({estado_forma:.1f}), "
            f"por lo que el grupo parece estar en equilibrio."
        )
    else:
        forma_txt = (
            f" El estado de forma es positivo ({estado_forma:.1f}), lo que sugiere "
            f"una buena adaptación general del grupo."
        )

    return (
        f"{estado_carga_txt}"
        f"{forma_txt}"
        f"{cambio_txt}"
        f" Última carga diaria registrada: {ua_actual:.0f} UA."
    )


def plot_estado_forma_puntos_grupal(df_players: pd.DataFrame):
    """
    Muestra el estado de forma 42d de cada jugadora como puntos.
    La línea horizontal en 0 marca el equilibrio:
    - por encima de 0: estado de forma positivo
    - por debajo de 0: fatiga aguda por encima de la referencia crónica
    """

    if (
        df_players is None
        or df_players.empty
        or "estado_forma_42d" not in df_players.columns
    ):
        st.info(t("No hay datos suficientes para mostrar el estado de forma por jugadora."))
        return

    df_plot = df_players.dropna(subset=["estado_forma_42d"]).copy()

    if df_plot.empty:
        st.info(t("No hay jugadoras con estado de forma calculable."))
        return

    def clasificar_estado_forma(x):
        if x < 0:
            return "Negativo"
        elif x <= 5:
            return "Neutro"
        else:
            return "Positivo"

    df_plot["zona_estado_forma"] = df_plot["estado_forma_42d"].apply(clasificar_estado_forma)
    df_plot = df_plot.sort_values("estado_forma_42d", ascending=True)

    color_map = {
        "Negativo": "#E53935",
        "Neutro": "#FB8C00",
        "Positivo": "#43A047",
    }

    # =====================================================
    # Título + caption explicativo
    # =====================================================
    st.markdown(t("#### Estado de forma por jugadora"))

    st.caption(
        t(
            "Cada punto representa una jugadora. La línea horizontal marca el equilibrio: "
            "por encima de 0, la carga crónica supera a la fatiga aguda reciente; "
            "por debajo de 0, la carga reciente está pesando más que la base acumulada."
        )
    )

    # =====================================================
    # Gráfico
    # =====================================================
    fig = px.scatter(
        df_plot,
        x="nombre_jugadora",
        y="estado_forma_42d",
        color="zona_estado_forma",
        color_discrete_map=color_map,
        title=None,
        labels={
            "nombre_jugadora": t("Jugadora"),
            "estado_forma_42d": t("Estado de forma 42d"),
            "zona_estado_forma": t("Zona"),
        },
        hover_data={
            "nombre_jugadora": True,
            "estado_forma_42d": ":.2f",
            "zona_estado_forma": True,
            "acwr_42d": ":.2f" if "acwr_42d" in df_plot.columns else False,
            "fatiga_aguda_7d_media": ":.1f" if "fatiga_aguda_7d_media" in df_plot.columns else False,
            "fatiga_cronica_42d": ":.1f" if "fatiga_cronica_42d" in df_plot.columns else False,
        },
    )

    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="#263238",
        annotation_text=t("Equilibrio"),
        annotation_position="top left"
    )

    fig.update_traces(
        marker=dict(
            size=11,
            line=dict(width=1, color="white")
        )
    )

    fig.update_layout(
        xaxis_title=t("Jugadora"),
        yaxis_title=t("Estado de forma 42d"),
        plot_bgcolor="white",
        font_color=styles.BRAND_TEXT,
        legend_title_text=t("Zona"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
    )

    fig.update_xaxes(tickangle=45)

    st.plotly_chart(fig, use_container_width=True)

    # =====================================================
    # Lectura automática
    # =====================================================
    total = len(df_plot)
    n_negativas = int((df_plot["estado_forma_42d"] < 0).sum())
    pct_negativas = (n_negativas / total * 100) if total > 0 else 0
    media_estado = df_plot["estado_forma_42d"].mean()

    if pct_negativas > 30:
        conclusion = (
            f"Hay {n_negativas} de {total} jugadoras con estado de forma negativo "
            f"({pct_negativas:.1f}%). Es una proporción elevada, por lo que conviene revisar "
            f"la carga reciente y la respuesta individual."
        )
    elif pct_negativas > 15:
        conclusion = (
            f"Hay {n_negativas} de {total} jugadoras con estado de forma negativo "
            f"({pct_negativas:.1f}%). El grupo está mayoritariamente controlado, "
            f"pero hay perfiles concretos que requieren seguimiento."
        )
    else:
        conclusion = (
            f"La mayoría del grupo presenta un estado de forma controlado. "
            f"Solo {n_negativas} de {total} jugadoras están en negativo "
            f"({pct_negativas:.1f}%)."
        )

    conclusion += f" El estado de forma medio del grupo es {media_estado:.1f}."

    render_interpretacion_grafico(
        "Lectura automática del periodo",
        conclusion,
        color="#43A047"
    )


def interpretar_wellness_periodico(
    df_periodo: pd.DataFrame,
    periodo_col: str,
    etiqueta_periodo: str = "periodo",
    scope: str = "grupal",
) -> str:
    """
    Genera una lectura automática para el resumen semanal/mensual de wellness.
    Escala asumida:
    - valores bajos = mejor estado
    - valores altos = peor estado
    """

    sujeto = "El grupo" if scope == "grupal" else "La jugadora"

    if df_periodo is None or df_periodo.empty:
        return t("No hay datos suficientes para interpretar el wellness.")

    cols_wellness = ["energia", "recuperacion", "sueno", "stress", "dolor"]
    cols_wellness = [c for c in cols_wellness if c in df_periodo.columns]

    if periodo_col not in df_periodo.columns or not cols_wellness:
        return t("No hay columnas suficientes para interpretar el wellness.")

    df = df_periodo.copy()

    for col in cols_wellness:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if "wellness_medio" not in df.columns:
        df["wellness_medio"] = df[cols_wellness].mean(axis=1, skipna=True)

    df = df.dropna(subset=["wellness_medio"]).copy()

    if df.empty:
        return t("No hay valores válidos de wellness para interpretar.")

    labels_map = {
        "energia": "energía",
        "recuperacion": "recuperación",
        "sueno": "sueño",
        "stress": "stress",
        "dolor": "dolor",
    }

    ultima = df.iloc[-1]
    periodo_actual = ultima[periodo_col]
    wellness_actual = ultima["wellness_medio"]

    # Estado actual
    if wellness_actual <= 2:
        estado_txt = (
            f"{sujeto} presenta un wellness favorable en el último {etiqueta_periodo} "
            f"({periodo_actual}), con un valor medio de {wellness_actual:.2f}."
        )
    elif wellness_actual <= 3:
        estado_txt = (
            f"{sujeto} presenta un wellness en zona de atención en el último {etiqueta_periodo} "
            f"({periodo_actual}), con un valor medio de {wellness_actual:.2f}."
        )
    else:
        estado_txt = (
            f"{sujeto} presenta un wellness en zona de alerta en el último {etiqueta_periodo} "
            f"({periodo_actual}), con un valor medio de {wellness_actual:.2f}."
        )

    # Tendencia respecto al periodo anterior
    tendencia_txt = ""

    if len(df) >= 2:
        anterior = df.iloc[-2]
        wellness_anterior = anterior["wellness_medio"]

        if pd.notna(wellness_anterior):
            cambio = wellness_actual - wellness_anterior

            if cambio > 0.25:
                tendencia_txt = (
                    f" Respecto al {etiqueta_periodo} anterior, el wellness ha empeorado "
                    f"en {cambio:.2f} puntos."
                )
            elif cambio < -0.25:
                tendencia_txt = (
                    f" Respecto al {etiqueta_periodo} anterior, el wellness ha mejorado "
                    f"en {abs(cambio):.2f} puntos."
                )
            else:
                tendencia_txt = (
                    f" Respecto al {etiqueta_periodo} anterior, el wellness se mantiene estable."
                )

    # Variable más comprometida
    medias_ultimo = ultima[cols_wellness].sort_values(ascending=False)
    var_peor = medias_ultimo.index[0]
    valor_peor = medias_ultimo.iloc[0]
    var_peor_txt = labels_map.get(var_peor, var_peor)

    if valor_peor > 3:
        variable_txt = (
            f" La variable más comprometida es {var_peor_txt}, con un valor medio de "
            f"{valor_peor:.2f}, por encima del umbral de alerta."
        )
    elif valor_peor > 2:
        variable_txt = (
            f" La variable que más conviene vigilar es {var_peor_txt}, con un valor medio de "
            f"{valor_peor:.2f}."
        )
    else:
        variable_txt = (
            f" Ninguna variable aparece claramente comprometida; la más alta es "
            f"{var_peor_txt} ({valor_peor:.2f})."
        )

    # Variables en alerta
    variables_alerta = [
        labels_map.get(col, col)
        for col in cols_wellness
        if pd.notna(ultima[col]) and ultima[col] > 3
    ]

    if variables_alerta:
        alerta_txt = f" Variables en alerta: {', '.join(variables_alerta)}."
    else:
        alerta_txt = " No hay variables en alerta clara en el último periodo."

    return estado_txt + tendencia_txt + variable_txt + alerta_txt


def plot_wellness_resumen_periodico(
    df_periodo: pd.DataFrame,
    periodo_col: str,
    titulo: str,
    etiqueta_periodo: str,
    scope: str = "grupal",
):
    """
    Gráfico de resumen semanal/mensual de wellness.
    Sirve para grupal e individual según scope.

    Escala:
    - valores bajos = mejor estado
    - valores altos = peor estado
    """

    if df_periodo is None or df_periodo.empty:
        st.info(t(f"No hay datos de wellness para mostrar en {etiqueta_periodo}."))
        return

    if periodo_col not in df_periodo.columns:
        st.warning(t(f"Falta la columna {periodo_col}."))
        return

    df = df_periodo.copy()

    cols_wellness = ["energia", "recuperacion", "sueno", "stress", "dolor"]
    cols_wellness = [c for c in cols_wellness if c in df.columns]

    if not cols_wellness:
        st.warning(t("No hay variables de wellness disponibles para graficar."))
        return

    for col in cols_wellness + ["rpe", "ua"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["wellness_medio"] = df[cols_wellness].mean(axis=1, skipna=True)
    df = df.dropna(subset=["wellness_medio"]).copy()

    if df.empty:
        st.info(t("No hay valores válidos de wellness para mostrar."))
        return

    # =====================================================
    # Preparar eje X con formato limpio
    # =====================================================
    df["periodo_original"] = df[periodo_col].astype(str)
    etiqueta = etiqueta_periodo.lower().strip()

    if etiqueta == "semana":
        # Caso 1: si ya vienen inicio_semana y fin_semana
        if "inicio_semana" in df.columns and "fin_semana" in df.columns:
            df["_inicio_semana"] = pd.to_datetime(df["inicio_semana"], errors="coerce")
            df["_fin_semana"] = pd.to_datetime(df["fin_semana"], errors="coerce")

        # Caso 2: si semana viene como "2026-03-02/2026-03-08"
        elif df["periodo_original"].str.contains("/", regex=False).any():
            partes = df["periodo_original"].str.split("/", expand=True)

            df["_inicio_semana"] = pd.to_datetime(partes[0], errors="coerce")
            df["_fin_semana"] = pd.to_datetime(partes[1], errors="coerce")

        # Caso 3: si solo tenemos una fecha o etiqueta
        else:
            df["_inicio_semana"] = pd.to_datetime(
                df["periodo_original"],
                errors="coerce"
            )
            df["_fin_semana"] = df["_inicio_semana"] + pd.Timedelta(days=6)

        if df["_inicio_semana"].notna().any():
            df = df.sort_values("_inicio_semana")
            df["periodo_label"] = (
                df["_inicio_semana"].dt.strftime("%d %b")
                + "–"
                + df["_fin_semana"].dt.strftime("%d %b")
            )
        else:
            df["periodo_label"] = df["periodo_original"]

        x_col = "periodo_label"

    elif etiqueta == "mes":
        # Caso mensual tipo "2026-03"
        df["_periodo_dt"] = pd.to_datetime(
            df["periodo_original"],
            format="%Y-%m",
            errors="coerce"
        )

        # Si no entra con formato YYYY-MM, intentamos conversión normal
        if not df["_periodo_dt"].notna().any():
            df["_periodo_dt"] = pd.to_datetime(
                df["periodo_original"],
                errors="coerce"
            )

        if df["_periodo_dt"].notna().any():
            df = df.sort_values("_periodo_dt")
            df["periodo_label"] = df["_periodo_dt"].dt.strftime("%b %Y")
        else:
            df["periodo_label"] = df["periodo_original"]

        x_col = "periodo_label"

    else:
        df["periodo_label"] = df["periodo_original"]
        x_col = "periodo_label"

    # =====================================================
    # Título + caption
    # =====================================================
    st.markdown(t(f"#### {titulo}"))

    sujeto_caption = "del grupo" if scope == "grupal" else "de la jugadora"

    st.caption(
        t(
            f"La línea principal muestra el wellness medio {sujeto_caption}. "
            "En esta escala, valores más bajos indican mejor estado y valores más altos indican mayor fatiga, malestar o alerta."
        )
    )

    # =====================================================
    # Gráfico
    # =====================================================
    fig = go.Figure()

    # Bandas de interpretación
    fig.add_hrect(
        y0=1,
        y1=2,
        fillcolor="#C8E6C9",
        opacity=0.25,
        line_width=0,
    )

    fig.add_hrect(
        y0=2,
        y1=3,
        fillcolor="#FFE0B2",
        opacity=0.25,
        line_width=0,
    )

    fig.add_hrect(
        y0=3,
        y1=5,
        fillcolor="#FFCDD2",
        opacity=0.25,
        line_width=0,
    )

    # Línea principal: wellness medio
    fig.add_trace(
        go.Scatter(
            x=df[x_col],
            y=df["wellness_medio"],
            mode="lines+markers",
            name=t("Wellness medio"),
            line=dict(color="#263238", width=4),
            marker=dict(size=9),
        )
    )

    # Variables individuales
    label_cols = {
        "energia": t("Energía"),
        "recuperacion": t("Recuperación"),
        "sueno": t("Sueño"),
        "stress": t("Stress"),
        "dolor": t("Dolor"),
    }

    color_cols = {
        "energia": "#1E88E5",
        "recuperacion": "#43A047",
        "sueno": "#8E24AA",
        "stress": "#FB8C00",
        "dolor": "#E53935",
    }

    for col in cols_wellness:
        fig.add_trace(
            go.Scatter(
                x=df[x_col],
                y=df[col],
                mode="lines+markers",
                name=label_cols.get(col, col.capitalize()),
                line=dict(
                    color=color_cols.get(col, "#607D8B"),
                    width=2,
                    dash="dot"
                ),
                marker=dict(size=7),
                opacity=0.85,
            )
        )

    # Líneas de referencia
    fig.add_hline(
        y=2,
        line_dash="dash",
        line_color="#43A047",
        annotation_text=t("Favorable"),
        annotation_position="bottom right"
    )

    fig.add_hline(
        y=3,
        line_dash="dash",
        line_color="#E53935",
        annotation_text=t("Alerta"),
        annotation_position="top right"
    )

    fig.update_layout(
        xaxis_title=t("Periodo"),
        yaxis_title=t("Wellness medio"),
        yaxis=dict(range=[1, 5]),
        plot_bgcolor="white",
        font_color=styles.BRAND_TEXT,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.08,
            xanchor="left",
            x=0
        ),
        margin=dict(t=70, b=40),
    )

    fig.update_xaxes(
        type="category",
        tickangle=-30
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displaylogo": False,
            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        }
    )

    # =====================================================
    # Lectura automática
    # =====================================================
    conclusion = interpretar_wellness_periodico(
        df,
        periodo_col=periodo_col,
        etiqueta_periodo=etiqueta_periodo,
        scope=scope,
    )

    render_interpretacion_grafico(
        "Lectura automática del periodo",
        conclusion,
        color="#43A047"
    )

    # =====================================================
    # Tabla resumen
    # =====================================================
    columnas_tabla = [periodo_col, "wellness_medio"] + cols_wellness
    columnas_extra = [c for c in ["rpe", "ua"] if c in df.columns]
    columnas_tabla += columnas_extra

    with st.expander(t("Ver tabla resumen"), expanded=False):
        st.dataframe(
            df[columnas_tabla].round(2).rename(
                columns={
                    periodo_col: t("Periodo"),
                    "wellness_medio": t("Wellness medio"),
                    "energia": t("Energía"),
                    "recuperacion": t("Recuperación"),
                    "sueno": t("Sueño"),
                    "stress": t("Stress"),
                    "dolor": t("Dolor"),
                    "rpe": t("RPE"),
                    "ua": t("UA"),
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

