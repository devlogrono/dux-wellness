
import streamlit as st
import pandas as pd
from modules.i18n.i18n import t
from modules.reports.metrics import RPEFilters, compute_rpe_metrics
from .plots_grupales import (plot_carga_semanal, plot_estado_carga_grupal, plot_rpe_promedio, tabla_resumen)

def group_dashboard(df_filtrado: pd.DataFrame):
    """Panel grupal con gráficos y tablas agregadas."""

    #st.subheader(":material/group: Resumen grupal de cargas", divider=True)
    if df_filtrado.empty:
        st.info(t("No hay datos disponibles para el periodo seleccionado."))
        st.stop()

    df_estado = compute_rpe_timeseries_group(df_filtrado)
    
    #st.divider()
    tabs = st.tabs([
        t(":material/show_chart: Estado de carga"),
        t(":material/monitor_weight: Carga y esfuerzo"),
        t(":material/trending_up: RPE"),
        t(":material/table_chart: Resumen"),
    ])
    with tabs[0]:
        plot_estado_carga_grupal(df_estado)
    with tabs[1]:
        plot_carga_semanal(df_filtrado)
    with tabs[2]: 
        plot_rpe_promedio(df_filtrado)
    with tabs[3]: 
        tabla_resumen(df_filtrado)

def metricas_grupal(df: pd.DataFrame,
    jugadores: list[str] | None,
    turnos: list[str] | None,
    start,
    end) -> None:
    """
    Página de análisis grupal de cargas y RPE.
    Reutiliza métricas individuales y las agrega a nivel equipo.
    """

    if df is None or df.empty:
        st.info(t("No hay registros disponibles para análisis grupal."))
        return

    # --- métricas individuales ---
    df_players = compute_rpe_metrics_by_player(df, jugadores, turnos, start, end)

    if df_players.empty:
        st.info(t("No hay métricas grupales para el periodo seleccionado."))
        return

    # --- agregación grupal ---
    grupo = {
        "jugadoras_activas": len(df_players),
        "carga_semana_total": df_players["carga_semana"].sum(),
        "carga_semana_media": df_players["carga_semana"].mean(),
        "fatiga_aguda_media": df_players["fatiga_aguda"].mean(),
        "fatiga_cronica_28d_media": df_players["fatiga_cronica_28d"].mean(),
        "fatiga_cronica_42d_media": df_players["fatiga_cronica_42d"].mean(),
        "fatiga_cronica_56d_media": df_players["fatiga_cronica_56d"].mean(),
        "acwr_medio_28d": df_players["acwr_28d"].mean(),
        "acwr_medio_42d": df_players["acwr_42d"].mean(),
        "acwr_medio_56d": df_players["acwr_56d"].mean(),
        "dispersion_carga": df_players["carga_semana"].std(),
    }

    # --- UI ---
    st.divider()
    st.markdown(t("### **Resumen de carga grupal**"))

    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:
        st.metric(t("Jugadoras activas"), grupo["jugadoras_activas"])
        st.metric(t("Fatiga aguda media (7d)"), f"{grupo['fatiga_aguda_media']:.0f}")

    with k2:
        st.metric(t("Carga semana media"), f"{grupo['carga_semana_media']:.0f}")
        st.metric(t("F. crónica media (42d)"), f"{grupo['fatiga_cronica_42d_media']:.1f}")

    with k3:
        st.metric(t("Dispersión de carga"), f"{grupo['dispersion_carga']:.1f}")
        st.metric(t("ACWR medio 42d"), f"{grupo['acwr_medio_42d']:.2f}")

    with k4:
        st.metric(t("Monotonía media"), f"{df_players['monotonia'].mean():.2f}")
        #st.metric(t("ACWR medio 42d"), f"{grupo['acwr_medio_42d']:.2f}")
       
    with k5:
        st.metric(t("Carga semana total"), f"{grupo['carga_semana_total']:.0f}")
        
    # --- resumen técnico ---
    resumen = _get_resumen_tecnico_carga_grupal(grupo)
    st.markdown(resumen, unsafe_allow_html=True)

def _get_resumen_tecnico_carga_grupal(grupo: dict) -> str:
    return (
        f"<b>{t('Resumen técnico grupal')}:</b> "
        f"{t('El equipo presenta una carga semanal total de')} "
        f"<b>{grupo['carga_semana_total']:.0f} UA</b>, "
        f"{t('con una media por jugadora de')} "
        f"<b>{grupo['carga_semana_media']:.0f} UA</b>. "
        f"{t('La fatiga aguda media es de')} "
        f"<b>{grupo['fatiga_aguda_media']:.0f} UA</b> "
        f"{t('y el ACWR medio del grupo es')} "
        f"<b>{grupo['acwr_medio_42d']:.2f}</b>. "
        f"{t('La dispersión de carga indica una distribución')} "
        f"<b>{'heterogénea' if grupo['dispersion_carga'] > 300 else 'homogénea'}</b>."
    )

def compute_rpe_metrics_by_player(
    df: pd.DataFrame,
    jugadores: list[str] | None,
    turnos: list[str] | None,
    start,
    end
) -> pd.DataFrame:
    """
    Calcula métricas RPE por jugadora reutilizando compute_rpe_metrics.
    Devuelve un DataFrame con una fila por jugadora.
    """

    rows = []

    for id_jugadora, df_jug in df.groupby("id_jugadora"):
        flt = RPEFilters(
            jugadores=[id_jugadora],
            turnos=turnos or None,
            start=start,
            end=end
        )

        metrics = compute_rpe_metrics(df_jug, flt)

        if not metrics:
            continue

        rows.append({
            "id_jugadora": id_jugadora,
            "nombre_jugadora": df_jug["nombre_jugadora"].iloc[0],

            # --- núcleo ---
            "ua_dia": metrics["ua_total_dia"],
            "minutos_dia": metrics["minutos_sesion"],
            "carga_semana": metrics["carga_semana"],
            "carga_mes": metrics["carga_mes"],

            # --- fatiga ---
            "fatiga_aguda": metrics["fatiga_aguda"],
            "fatiga_cronica_28d": metrics["fatiga_cronica_28d"],
            "fatiga_cronica_42d": metrics["fatiga_cronica_42d"],
            "fatiga_cronica_56d": metrics["fatiga_cronica_56d"],

            # --- índices ---
            "acwr_28d": metrics["acwr_28d"],
            "acwr_42d": metrics["acwr_42d"],
            "acwr_56d": metrics["acwr_56d"],
            "monotonia": metrics["monotonia_semana"],
            "variabilidad": metrics["variabilidad_semana"],
            "adaptacion_28d": metrics["adaptacion_28d"],
            "adaptacion_42d": metrics["adaptacion_42d"],
            "adaptacion_56d": metrics["adaptacion_56d"],
        })

    return pd.DataFrame(rows)

def aggregate_group_metrics(df_players: pd.DataFrame) -> dict:
    """
    Agrega métricas individuales a nivel grupal.
    """

    if df_players.empty:
        return {}

    return {
        # --- contexto ---
        "jugadoras_activas": len(df_players),

        # --- carga ---
        "carga_total_semana": df_players["carga_semana"].sum(),
        "carga_media_jugadora": df_players["carga_semana"].mean(),

        # --- fatiga ---
        "fatiga_aguda_media": df_players["fatiga_aguda"].mean(),
        "fatiga_cronica_28d_media": df_players["fatiga_cronica_28d"].mean(),

        # --- dispersión ---
        "dispersion_carga": df_players["carga_semana"].std(),

        # --- riesgo ---
        "acwr_medio": df_players["acwr"].mean(),
        "pct_acwr_alto": (
            (df_players["acwr"] > 1.3).sum() / len(df_players) * 100
        ),
    }

# ============================================================
# 📈 Estado de Carga
# ============================================================

def compute_rpe_timeseries_group(
    df: pd.DataFrame,
    ventana_aguda: int = 7,
    ventana_cronica: int = 42,
) -> pd.DataFrame:
    """
    Calcula el estado de carga diario A NIVEL GRUPAL.

    Devuelve un DataFrame con:
    - UA diaria grupal (suma)
    - Fatiga aguda (media móvil)
    - Fatiga crónica (media móvil)
    - Recuperación
    - ACWR
    """

    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()

    # -------------------------
    # Fecha
    # -------------------------
    df["fecha_sesion"] = pd.to_datetime(df["fecha_sesion"], errors="coerce")
    df = df.dropna(subset=["fecha_sesion"])

    # -------------------------
    # UA diaria grupal (SUMA)
    # -------------------------
    daily = (
        df.groupby("fecha_sesion", as_index=False)["ua"]
        .sum()
        .rename(columns={"ua": "ua_grupal"})
        .set_index("fecha_sesion")
        .asfreq("D")
    )

    daily["ua_grupal"] = daily["ua_grupal"].fillna(0)

    # -------------------------
    # Fatiga aguda (7d)
    # -------------------------
    daily["fatiga_aguda_7d"] = (
        daily["ua_grupal"]
        .rolling(window=ventana_aguda, min_periods=1)
        .mean()
    )

    # -------------------------
    # Fatiga crónica (Xd)
    # -------------------------
    col_cronica = f"fatiga_cronica_{ventana_cronica}d"
    daily[col_cronica] = (
        daily["ua_grupal"]
        .rolling(window=ventana_cronica, min_periods=1)
        .mean()
    )

    # -------------------------
    # Recuperación
    # -------------------------
    daily[f"recuperacion_{ventana_cronica}d"] = (
        daily[col_cronica] - daily["fatiga_aguda_7d"]
    )

    # -------------------------
    # ACWR
    # -------------------------
    daily[f"acwr_{ventana_cronica}d"] = (
        daily["fatiga_aguda_7d"] / daily[col_cronica]
    )

    # -------------------------
    # Redondeo
    # -------------------------
    num_cols = daily.select_dtypes("number").columns
    daily[num_cols] = daily[num_cols].round(2)

    return daily.reset_index()
