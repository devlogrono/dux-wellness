
import streamlit as st
import pandas as pd
from modules.i18n.i18n import t
from modules.reports.metrics import RPEFilters, _ema, compute_rpe_metrics, _daily_loads, _prepare_checkout_df
from .plots_grupales import (
                            plot_estado_carga_grupal, 
                             plot_rpe_promedio, tabla_resumen, 
                             plot_distribucion_estado_forma,
                             plot_estado_carga_grupal_sma, 
                             plot_monotonia_strain,
                             plot_acwr,
                             plot_carga_semanal_base,
                             plot_carga_diaria_detalle_base)

def group_dashboard(
    df_visual: pd.DataFrame,
    df_calculo: pd.DataFrame,
    start=None,
    end=None,
):
    """Panel grupal con gráficos y tablas agregadas."""

    if df_visual is None or df_visual.empty:
        st.info(t("No hay datos disponibles para el periodo seleccionado."))
        st.stop()

    df_estado = compute_rpe_timeseries_group(df_calculo)

    if start is not None and end is not None:
        df_estado_plot = df_estado[
            (pd.to_datetime(df_estado["fecha_sesion"]).dt.date >= start) &
            (pd.to_datetime(df_estado["fecha_sesion"]).dt.date <= end)
        ].copy()
    else:
        df_estado_plot = df_estado.copy()
    df_players = compute_rpe_metrics_by_player(df_calculo, None, None, start, end)

    tabs = st.tabs([
        t(":material/monitor_heart: Wellness"),
        t(":material/show_chart: Estado de carga"),
        t(":material/monitor_weight: Carga y esfuerzo"),
        t(" Montonía y strain"),
        t(":material/trending_up: RPE"),
        t("ACWR"),
        t(":material/table_chart: Resumen"),
    ])
    with tabs[0]:
        wellness_dashboard_grupal(df_visual)
    with tabs[1]:
        plot_estado_carga_grupal(df_estado_plot)
        st.divider()
        plot_estado_carga_grupal_sma(df_estado_plot)
        st.divider()
        plot_distribucion_estado_forma(df_players)

    with tabs[2]:
        weekly = plot_carga_semanal_base(df_visual)

        if start is not None and end is not None:
            n_dias = (end - start).days + 1

            if n_dias <= 7:
                st.divider()
                plot_carga_diaria_detalle_base(
                    df_visual,
                    start=start,
                    end=end
                )

            elif not weekly.empty:
                semana_sel = st.selectbox(
                    "Ver detalle de la semana",
                    options=weekly["rango_semana"].tolist(),
                    index=len(weekly) - 1,
                    key="semana_detalle_grupal"
                )

                row = weekly[weekly["rango_semana"] == semana_sel].iloc[0]
                start_week = pd.to_datetime(row["inicio_semana"]).date()
                end_week = pd.to_datetime(row["fin_semana"]).date()

            st.divider()
            plot_carga_diaria_detalle_base(df_visual, start=start_week, end=end_week)
        
    with tabs[3]:
        plot_monotonia_strain(df_visual, scope="grupal")
    with tabs[4]:
        plot_rpe_promedio(df_visual)
    with tabs[5]:
         plot_acwr(df_estado_plot, ventana_cronica=42, metodo="sma", scope="grupal")
    with tabs[6]:
        tabla_resumen(df_visual)


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

    grupo = {
        "jugadoras_activas": len(df_players),

        # nuevas dinámicas del periodo
        "carga_total_periodo": df_players["carga_total_periodo"].sum(),
        "carga_media_jug_periodo": df_players["carga_total_periodo"].mean(),

        # fisiología fija
        "fatiga_aguda_media": df_players["fatiga_aguda_7d_media"].mean(),
        "fatiga_cronica_28d_media": df_players["fatiga_cronica_28d"].mean(),
        "fatiga_cronica_42d_media": df_players["fatiga_cronica_42d"].mean(),
        "fatiga_cronica_56d_media": df_players["fatiga_cronica_56d"].mean(),

        "estado_forma_28d_medio": df_players["estado_forma_28d"].mean(),
        "estado_forma_42d_medio": df_players["estado_forma_42d"].mean(),
        "estado_forma_56d_medio": df_players["estado_forma_56d"].mean(),

        "acwr_medio_28d": df_players["acwr_28d"].mean(),
        "acwr_medio_42d": df_players["acwr_42d"].mean(),
        "acwr_medio_56d": df_players["acwr_56d"].mean(),

        "dispersion_carga": df_players["carga_total_periodo"].std(),
    }


    # --- UI ---
    st.divider()
    st.markdown(t("### **Resumen de carga grupal**"))

    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:
        st.metric(
            t("Jugadoras activas"),
            grupo["jugadoras_activas"],
            help=t("Número de jugadoras con métricas de carga calculables en el periodo seleccionado.")
        )
        st.metric(
            t("Fatiga aguda media (7d)"),
            f"{grupo['fatiga_aguda_media']:.1f}",
            help=t("Media grupal de la carga diaria de los últimos 7 días.")
        )

    with k2:
        st.metric(
            t("Carga media/ jug "),
            f"{grupo['carga_media_jug_periodo']:.0f}",
            help=t("Carga media en el periodo de cada jugadora.")
        )
        st.metric(
            t("F. crónica media (42d)"),
            f"{grupo['fatiga_cronica_42d_media']:.1f}",
            help=t("Media grupal de la carga diaria de referencia a 42 días.")
        )

    with k3:
        st.metric(
            t("Dispersión de carga"),
            f"{grupo['dispersion_carga']:.1f}",
            help=t("Desviación entre jugadoras en la carga 7d. Un valor alto indica más heterogeneidad.")
        )
        st.metric(
            t("ACWR medio 42d"),
            f"{grupo['acwr_medio_42d']:.2f}",
            help=t("Relación entre carga aguda 7d y carga crónica 42d a nivel grupal.")
        )

    with k4:
        st.metric(
            t("Monotonía media/jug"),
            f"{df_players['monotonia'].mean():.2f}",
            help=t("Indica si la carga reciente ha sido demasiado uniforme entre días.")
        )
        st.metric(
            t("Estado de forma medio (42d)"),
            f"{grupo['estado_forma_42d_medio']:.1f}",
            help=t("Balance medio entre fatiga crónica y carga aguda reciente. Valores positivos indican mejor adaptación.")
        )

    with k5:
        st.metric(
            t("Carga total periodo"),
            f"{grupo['carga_total_periodo']:.0f}",
            help=t("Suma de la carga acumulada en el periodo de todas las jugadoras.")
        )
        
        
    # --- resumen técnico ---
    resumen = _get_resumen_tecnico_carga_grupal(grupo)
    st.markdown(resumen, unsafe_allow_html=True)
    alertas = build_group_alerts(grupo, df_players)
    render_group_alerts(alertas)

def _get_resumen_tecnico_carga_grupal(grupo: dict) -> str:
    """
    Resumen técnico grupal con colores dinámicos según nivel de alerta.
    Adaptado a:
    - carga total del periodo
    - carga media por jugadora del periodo
    """

    def color_text(text, color):
        return f"<b style='color:{color}'>{text}</b>"

    acwr = grupo.get("acwr_medio_42d")
    estado_forma = grupo.get("estado_forma_42d_medio")
    dispersion = grupo.get("dispersion_carga")

    carga_total_periodo = grupo.get("carga_total_periodo", 0)
    carga_media_jug_periodo = grupo.get("carga_media_jug_periodo", 0)
    fatiga_aguda = grupo.get("fatiga_aguda_media")
    fatiga_cronica = grupo.get("fatiga_cronica_42d_media")

    # =========================
    # ACWR
    # =========================
    if acwr is None:
        acwr_txt = color_text("sin datos suficientes", "#757575")
        acwr_val = color_text("-", "#607D8B")
    elif acwr > 1.5:
        acwr_txt = color_text("muy alto (peligro)", "#E53935")
        acwr_val = color_text(f"{acwr:.2f}", "#E53935")
    elif 1.3 <= acwr <= 1.5:
        acwr_txt = color_text("alto (precaución)", "#FB8C00")
        acwr_val = color_text(f"{acwr:.2f}", "#FB8C00")
    elif 0.8 <= acwr < 1.3:
        acwr_txt = color_text("óptimo", "#43A047")
        acwr_val = color_text(f"{acwr:.2f}", "#43A047")
    else:
        acwr_txt = color_text("bajo", "#FBC02D")
        acwr_val = color_text(f"{acwr:.2f}", "#FBC02D")

    # =========================
    # Estado de forma
    # =========================
    if estado_forma is None:
        estado_forma_txt = color_text("no disponible", "#757575")
        estado_forma_val = color_text("-", "#607D8B")
    elif estado_forma < 0:
        estado_forma_txt = color_text("negativo", "#E53935")
        estado_forma_val = color_text(f"{estado_forma:.1f}", "#E53935")
    elif estado_forma == 0:
        estado_forma_txt = color_text("neutro", "#FB8C00")
        estado_forma_val = color_text(f"{estado_forma:.1f}", "#FB8C00")
    else:
        estado_forma_txt = color_text("positivo", "#43A047")
        estado_forma_val = color_text(f"{estado_forma:.1f}", "#43A047")

    # =========================
    # Dispersión
    # =========================
    if dispersion is None:
        distribucion_txt = color_text("no valorable", "#757575")
    elif dispersion > 400:
        distribucion_txt = color_text("alta y heterogénea", "#E53935")
    elif dispersion > 250:
        distribucion_txt = color_text("moderadamente heterogénea", "#FB8C00")
    else:
        distribucion_txt = color_text("estable", "#43A047")

    # =========================
    # Fatiga aguda vs crónica
    # =========================
    if fatiga_aguda is None or fatiga_cronica is None:
        fatiga_txt = color_text("sin referencia suficiente", "#757575")
        fatiga_vals = color_text("-", "#607D8B")
    elif fatiga_aguda > fatiga_cronica:
        fatiga_txt = color_text("por encima de la referencia crónica", "#E53935")
        fatiga_vals = color_text(f"{fatiga_aguda:.1f} vs {fatiga_cronica:.1f} UA/día", "#E53935")
    elif fatiga_aguda == fatiga_cronica:
        fatiga_txt = color_text("alineada con la referencia crónica", "#FB8C00")
        fatiga_vals = color_text(f"{fatiga_aguda:.1f} vs {fatiga_cronica:.1f} UA/día", "#FB8C00")
    else:
        fatiga_txt = color_text("controlada respecto a la referencia crónica", "#43A047")
        fatiga_vals = color_text(f"{fatiga_aguda:.1f} vs {fatiga_cronica:.1f} UA/día", "#43A047")

    return (
        f"{t(':material/description: **Resumen técnico grupal:**')} "
        f"<div style='text-align: justify;'>"

        f"{t('El equipo acumula una carga total en el periodo de')} "
        f"{color_text(f'{carga_total_periodo:.0f} UA', '#607D8B')}, "
        f"{t('con una carga media por jugadora de')} "
        f"{color_text(f'{carga_media_jug_periodo:.0f} UA', '#607D8B')}. "

        f"{t('La fatiga aguda media diaria de 7 días se encuentra')} "
        f"{fatiga_txt} "
        f"({fatiga_vals}). "

        f"{t('El ACWR medio del grupo se sitúa en un nivel')} "
        f"{acwr_txt} "
        f"({acwr_val}), "

        f"{t('mientras que el estado de forma medio es')} "
        f"{estado_forma_txt} "
        f"({estado_forma_val}). "

        f"{t('La distribución de la carga entre jugadoras es')} "
        f"{distribucion_txt}."

        f"</div>"
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

        # Núcleo
        "ua_dia": metrics["ua_total_dia"],
        "minutos_dia": metrics["minutos_sesion"],

        # NUEVAS dinámicas por periodo
        "carga_total_periodo": metrics["carga_total_periodo"],
        "carga_media_periodo": metrics["carga_media_periodo"],

        # Compatibilidad / antiguas si las quieres mantener
        "carga_semana": metrics["carga_semana"],
        "carga_mes": metrics["carga_mes"],
        "carga_media_semana": metrics["carga_media_semana"],
        "carga_media_mes": metrics["carga_media_mes"],

        # Fatiga
        "fatiga_aguda": metrics["fatiga_aguda"],
        "fatiga_aguda_7d_media": metrics["fatiga_aguda_7d_media"],
        "fatiga_cronica_28d": metrics["fatiga_cronica_28d"],
        "fatiga_cronica_42d": metrics["fatiga_cronica_42d"],
        "fatiga_cronica_56d": metrics["fatiga_cronica_56d"],

        # Estado de forma
        "estado_forma_28d": metrics["estado_forma_28d"],
        "estado_forma_42d": metrics["estado_forma_42d"],
        "estado_forma_56d": metrics["estado_forma_56d"],

        # Índices
        "acwr_28d": metrics["acwr_28d"],
        "acwr_42d": metrics["acwr_42d"],
        "acwr_56d": metrics["acwr_56d"],
        "monotonia": metrics["monotonia_semana"],
        "variabilidad": metrics["variabilidad_semana"],
    })

    return pd.DataFrame(rows)

def aggregate_group_metrics(df_players: pd.DataFrame) -> dict:
    """
    Agrega métricas individuales a nivel grupal.
    """

    if df_players is None or df_players.empty:
        return {}

    return {
        # Contexto
        "jugadoras_activas": len(df_players),

        # Carga
        "carga_semana_total": df_players["carga_semana"].sum(),
        "carga_semana_media": df_players["carga_semana"].mean(),

        # Fatiga
        "fatiga_aguda_media": df_players["fatiga_aguda_7d_media"].mean(),
        "fatiga_cronica_28d_media": df_players["fatiga_cronica_28d"].mean(),
        "fatiga_cronica_42d_media": df_players["fatiga_cronica_42d"].mean(),
        "fatiga_cronica_56d_media": df_players["fatiga_cronica_56d"].mean(),

        # Estado de forma
        "estado_forma_28d_medio": df_players["estado_forma_28d"].mean(),
        "estado_forma_42d_medio": df_players["estado_forma_42d"].mean(),
        "estado_forma_56d_medio": df_players["estado_forma_56d"].mean(),

        # Dispersión
        "dispersion_carga": df_players["carga_semana"].std(),

        # Riesgo
        "acwr_medio_28d": df_players["acwr_28d"].mean(),
        "acwr_medio_42d": df_players["acwr_42d"].mean(),
        "acwr_medio_56d": df_players["acwr_56d"].mean(),
        "pct_acwr_alto": (
            (df_players["acwr_42d"] > 1.3).sum() / len(df_players) * 100
        ),

        # Distribución de riesgo
        "pct_estado_forma_negativo": (
            (df_players["estado_forma_42d"] < 0).sum() / len(df_players) * 100
        ),
    }

# ============================================================
# 📈 Estado de Carga
# ============================================================

# def compute_rpe_timeseries_group(
#     df: pd.DataFrame,
#     ventana_aguda: int = 7,
#     ventana_cronica: int = 42,
# ) -> pd.DataFrame:
#     """
#     Calcula el estado de carga diario A NIVEL GRUPAL.

#     Devuelve un DataFrame con:
#     - UA diaria grupal (suma)
#     - Fatiga aguda (media móvil)
#     - Fatiga crónica (media móvil)
#     - Recuperación
#     - ACWR
#     """

#     if df is None or df.empty:
#         return pd.DataFrame()

#     df = df.copy()

#     # -------------------------
#     # Fecha
#     # -------------------------
#     df["fecha_sesion"] = pd.to_datetime(df["fecha_sesion"], errors="coerce")
#     df = df.dropna(subset=["fecha_sesion"])

#     # -------------------------
#     # UA diaria grupal (SUMA)
#     # -------------------------
#     daily = (
#         df.groupby("fecha_sesion", as_index=False)["ua"]
#         .sum()
#         .rename(columns={"ua": "ua_grupal"})
#         .set_index("fecha_sesion")
#         .asfreq("D")
#     )

#     daily["ua_grupal"] = daily["ua_grupal"].fillna(0)

#     # -------------------------
#     # Fatiga aguda (7d)
#     # -------------------------
#     daily["fatiga_aguda_7d"] = (
#         daily["ua_grupal"]
#         .rolling(window=ventana_aguda, min_periods=1)
#         .mean()
#     )

#     # -------------------------
#     # Fatiga crónica (Xd)
#     # -------------------------
#     col_cronica = f"fatiga_cronica_{ventana_cronica}d"
#     daily[col_cronica] = (
#         daily["ua_grupal"]
#         .rolling(window=ventana_cronica, min_periods=1)
#         .mean()
#     )

#     # -------------------------
#     # Recuperación
#     # -------------------------
#     daily[f"recuperacion_{ventana_cronica}d"] = (
#         daily[col_cronica] - daily["fatiga_aguda_7d"]
#     )

#     # -------------------------
#     # ACWR
#     # -------------------------
#     daily[f"acwr_{ventana_cronica}d"] = (
#         daily["fatiga_aguda_7d"] / daily[col_cronica]
#     )

#     # -------------------------
#     # Redondeo
#     # -------------------------
#     num_cols = daily.select_dtypes("number").columns
#     daily[num_cols] = daily[num_cols].round(2)

#     return daily.reset_index()

def compute_rpe_timeseries_group(
    df: pd.DataFrame,
    ventana_aguda: int = 7,
    ventana_cronica: int = 42,
) -> pd.DataFrame:
    """
    Calcula el estado de carga diario a nivel grupal.
    Devuelve UA diaria grupal + SMA/EMA de fatiga, estado de forma y ACWR.
    """

    df = _prepare_checkout_df(df)

    if df is None or df.empty:
        return pd.DataFrame()

    daily_base = _daily_loads(df).copy()

    if daily_base.empty:
        return pd.DataFrame()

    daily = daily_base.copy()
    daily["fecha_sesion"] = pd.to_datetime(daily["fecha_sesion"], errors="coerce")
    daily = daily.dropna(subset=["fecha_sesion"]).sort_values("fecha_sesion")

    daily = daily.rename(columns={"ua_total": "ua_grupal"})

    # SMA
    daily[f"fatiga_aguda_{ventana_aguda}d_sma"] = (
        daily["ua_grupal"]
        .rolling(window=ventana_aguda, min_periods=1)
        .mean()
    )

    daily[f"fatiga_cronica_{ventana_cronica}d_sma"] = (
        daily["ua_grupal"]
        .rolling(window=ventana_cronica, min_periods=1)
        .mean()
    )

    daily[f"estado_forma_{ventana_cronica}d_sma"] = (
        daily[f"fatiga_cronica_{ventana_cronica}d_sma"]
        - daily[f"fatiga_aguda_{ventana_aguda}d_sma"]
    )

    daily[f"acwr_{ventana_cronica}d_sma"] = (
        daily[f"fatiga_aguda_{ventana_aguda}d_sma"]
        / daily[f"fatiga_cronica_{ventana_cronica}d_sma"]
    )

    # EMA
    daily[f"fatiga_aguda_{ventana_aguda}d_ema"] = _ema(
        daily["ua_grupal"],
        ventana_aguda
    )

    daily[f"fatiga_cronica_{ventana_cronica}d_ema"] = _ema(
        daily["ua_grupal"],
        ventana_cronica
    )

    daily[f"estado_forma_{ventana_cronica}d_ema"] = (
        daily[f"fatiga_cronica_{ventana_cronica}d_ema"]
        - daily[f"fatiga_aguda_{ventana_aguda}d_ema"]
    )

    daily[f"acwr_{ventana_cronica}d_ema"] = (
        daily[f"fatiga_aguda_{ventana_aguda}d_ema"]
        / daily[f"fatiga_cronica_{ventana_cronica}d_ema"]
    )

    num_cols = daily.select_dtypes(include="number").columns
    daily[num_cols] = daily[num_cols].round(2)

    return daily.reset_index(drop=True)


from modules.reports.wellness_metrics import (
    compute_team_wellness_kpis,
    build_team_daily_wellness,
    build_team_weekly_wellness,
    build_team_monthly_wellness,
    build_wellness_by_tipo_carga,
)

from .plots_grupales import (
    plot_estado_carga_grupal,
    plot_rpe_promedio,
    tabla_resumen,
    plot_wellness_evolucion_grupal,
    plot_wellness_por_tipo_carga,
)


def wellness_dashboard_grupal(df_filtrado: pd.DataFrame):
    """
    Bloque grupal de wellness analytics.
    Requiere que df_filtrado ya venga filtrado y preparado.
    """

    if df_filtrado is None or df_filtrado.empty:
        st.info(t("No hay datos de wellness disponibles para el periodo seleccionado."))
        return

    # -------------------------
    # KPIs
    # -------------------------
    kpis = compute_team_wellness_kpis(df_filtrado)

    st.divider()
    st.markdown(t("### **Wellness grupal**"))

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        st.metric(
            t("Energía media"),
            f"{kpis['energia_media']:.2f}" if kpis["energia_media"] is not None else "-"
        )

    with c2:
        st.metric(
            t("Recuperación media"),
            f"{kpis['recuperacion_media']:.2f}" if kpis["recuperacion_media"] is not None else "-"
        )

    with c3:
        st.metric(
            t("Sueño medio"),
            f"{kpis['sueno_medio']:.2f}" if kpis["sueno_medio"] is not None else "-"
        )

    with c4:
        st.metric(
            t("Stress medio"),
            f"{kpis['stress_medio']:.2f}" if kpis["stress_medio"] is not None else "-"
        )

    with c5:
        st.metric(
            t("Dolor medio"),
            f"{kpis['dolor_medio']:.2f}" if kpis["dolor_medio"] is not None else "-"
        )

    with c6:
        st.metric(
            t("% dolor ≥ 3"),
            f"{kpis['pct_dolor_3omas']:.1f}%" if kpis["pct_dolor_3omas"] is not None else "-"
        )

    # -------------------------
    # DataFrames agregados
    # -------------------------
    df_daily = build_team_daily_wellness(df_filtrado)
    df_weekly = build_team_weekly_wellness(df_filtrado)
    df_monthly = build_team_monthly_wellness(df_filtrado)
    df_tipo = build_wellness_by_tipo_carga(df_filtrado)

    tabs = st.tabs([
        t("Evolución diaria"),
        t("Evolución semanal"),
        t("Evolución mensual"),
        t("Por tipo de carga"),
    ])

    with tabs[0]:
        plot_wellness_evolucion_grupal(df_daily)

    with tabs[1]:
        if df_weekly.empty:
            st.info(t("No hay datos semanales de wellness para mostrar."))
        else:
            st.dataframe(df_weekly, use_container_width=True, hide_index=True)

    with tabs[2]:
        if df_monthly.empty:
            st.info(t("No hay datos mensuales de wellness para mostrar."))
        else:
            st.dataframe(df_monthly, use_container_width=True, hide_index=True)

    with tabs[3]:
        plot_wellness_por_tipo_carga(df_tipo)



#
# VENTANA DE CALCULO
#
from datetime import timedelta

def build_calculation_window(
    df_base: pd.DataFrame,
    start,
    end,
    lookback_days: int = 56,
) -> pd.DataFrame:
    """
    Devuelve un DataFrame ampliado hacia atrás desde la fecha inicial
    del periodo visible, para que todas las métricas rolling dentro del
    rango tengan histórico suficiente.
    """

    if df_base is None or df_base.empty or start is None or end is None:
        return pd.DataFrame()

    out = df_base.copy()
    out["fecha_sesion"] = pd.to_datetime(out["fecha_sesion"], errors="coerce").dt.date

    start_calculo = start - timedelta(days=lookback_days)

    out = out[
        (out["fecha_sesion"] >= start_calculo) &
        (out["fecha_sesion"] <= end)
    ].copy()

    return out



# -------------
# ALERTAS PIAY
# -------------
def build_group_alerts(grupo: dict, df_players: pd.DataFrame) -> pd.DataFrame:
    """
    Construye una tabla de alertas grupales con valor, umbral y nivel.
    """

    rows = []

    acwr = grupo.get("acwr_medio_42d")
    monotonia = (
        df_players["monotonia"].mean()
        if "monotonia" in df_players.columns and not df_players.empty
        else None
    )
    estado_forma = grupo.get("estado_forma_42d_medio")
    dispersion = grupo.get("dispersion_carga")

    pct_acwr_alto = (
        (df_players["acwr_42d"] > 1.3).mean() * 100
        if "acwr_42d" in df_players.columns and not df_players.empty
        else 0.0
    )

    df_estado_valido = (
        df_players.dropna(subset=["estado_forma_42d"]).copy()
        if "estado_forma_42d" in df_players.columns
        else pd.DataFrame()
    )

    pct_estado_forma_negativo = (
        (df_estado_valido["estado_forma_42d"] < 0).mean() * 100
        if not df_estado_valido.empty
        else 0.0
    )

    # ACWR grupal
    if acwr is None:
        nivel = "⚪ Sin datos"
        interpretacion = "Faltan datos de carga para calcular el ratio."
    elif acwr > 1.5:
        nivel = "🔴 Muy Alto (Peligro)"
        interpretacion = "Riesgo de lesión elevado. Reducción de carga inmediata."
    elif 1.3 <= acwr <= 1.5:
        nivel = "🟠 Alto (Precaución)"
        interpretacion = "Superando la 'zona dulce'. Vigilar fatiga."
    elif 0.8 <= acwr < 1.3:
        nivel = "🟢 Óptimo (Zona Dulce)"
        interpretacion = "Carga equilibrada y adaptaciones positivas."
    else: # acwr < 0.8
        nivel = "🟡 Bajo"
        interpretacion = "Carga insuficiente. Riesgo de desentrenamiento o falta de estímulo."


    rows.append({
        "Indicador": "ACWR grupal 42d",
        "Valor actual": f"{acwr:.2f}" if acwr is not None else "-",
        "Rango objetivo": "0.80 - 1.30",
        "Nivel": nivel,
        "Interpretación": interpretacion,
    })

    # Monotonía
    if monotonia is None:
        nivel = "⚪ Sin datos"
        interpretacion = "No hay datos suficientes."
    elif monotonia > 2.0:
        nivel = "🔴 Alta"
        interpretacion = "Hay poca variabilidad entre sesiones."
    elif monotonia >= 1.5:
        nivel = "🟡 Moderada"
        interpretacion = "Conviene vigilar la repetición del estímulo."
    else:
        nivel = "🟢 Buena"
        interpretacion = "La distribución del estímulo es adecuada."

    rows.append({
        "Indicador": "Monotonía media",
        "Valor actual": f"{monotonia:.2f}" if monotonia is not None else "-",
        "Rango objetivo": "< 1.50",
        "Nivel": nivel,
        "Interpretación": interpretacion,
    })

    # Estado de forma
    if estado_forma is None:
        nivel = "⚪ Sin datos"
        interpretacion = "No hay datos suficientes."
    elif estado_forma < 0:
        nivel = "🔴 Negativo"
        interpretacion = "La fatiga aguda supera la capacidad crónica."
    elif estado_forma == 0:
        nivel = "🟡 Neutro"
        interpretacion = "El grupo está en equilibrio."
    else:
        nivel = "🟢 Positivo"
        interpretacion = "El grupo muestra buena adaptación."

    rows.append({
        "Indicador": "Estado de forma medio 42d",
        "Valor actual": f"{estado_forma:.1f}" if estado_forma is not None else "-",
        "Rango objetivo": "> 0",
        "Nivel": nivel,
        "Interpretación": interpretacion,
    })

    # Dispersión
    if dispersion is None:
        nivel = "⚪ Sin datos"
        interpretacion = "No hay datos suficientes."
    elif dispersion > 400:
        nivel = "🔴 Alta"
        interpretacion = "Hay diferencias marcadas entre jugadoras."
    elif dispersion > 250:
        nivel = "🟡 Moderada"
        interpretacion = "Conviene revisar la homogeneidad del grupo."
    else:
        nivel = "🟢 Estable"
        interpretacion = "La carga está bastante equilibrada."

    rows.append({
        "Indicador": "Dispersión de carga",
        "Valor actual": f"{dispersion:.1f}" if dispersion is not None else "-",
        "Rango objetivo": "< 250",
        "Nivel": nivel,
        "Interpretación": interpretacion,
    })

    # % ACWR alto
    if pct_acwr_alto > 30:
        nivel = "🔴 Alto"
        interpretacion = "Muchas jugadoras están por encima de ACWR 1.3."
    elif pct_acwr_alto > 15:
        nivel = "🟡 Moderado"
        interpretacion = "Empiezan a aparecer perfiles en sobrecarga."
    else:
        nivel = "🟢 Controlado"
        interpretacion = "La mayoría del grupo se mantiene en rango."

    rows.append({
        "Indicador": "% jugadoras con ACWR > 1.3",
        "Valor actual": f"{pct_acwr_alto:.1f}%",
        "Rango objetivo": "< 15%",
        "Nivel": nivel,
        "Interpretación": interpretacion,
    })

    # % estado de forma negativo
    if pct_estado_forma_negativo > 30:
        nivel = "🔴 Alto"
        interpretacion = "Existe fatiga acumulada en una parte importante del grupo."
    elif pct_estado_forma_negativo > 15:
        nivel = "🟡 Moderado"
        interpretacion = "El grupo presenta adaptación desigual."
    else:
        nivel = "🟢 Controlado"
        interpretacion = "La mayoría del grupo mantiene un estado de forma positivo."

    rows.append({
        "Indicador": "% jugadoras con estado de forma negativo",
        "Valor actual": f"{pct_estado_forma_negativo:.1f}%",
        "Rango objetivo": "< 15%",
        "Nivel": nivel,
        "Interpretación": interpretacion,
    })

    return pd.DataFrame(rows)

def render_group_alerts(alertas_df: pd.DataFrame) -> None:
    """
    Muestra la tabla de alertas e interpretación grupal.
    """

    if alertas_df is None or alertas_df.empty:
        st.info("No hay alertas disponibles.")
        return
    
    st.markdown("### Interpretación de las métricas")
    st.dataframe(alertas_df, hide_index=True, use_container_width=True)


