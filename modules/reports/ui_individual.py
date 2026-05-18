import streamlit as st
import pandas as pd
import numpy as np

from modules.db.db_lesiones import get_wellness_pre_lesion
from .metrics import compute_rpe_metrics, RPEFilters, compute_rpe_timeseries, compute_cambio_carga, compute_dias_riesgo 
from modules.util.util import (get_photo, clean_image_url, calcular_edad)
from modules.i18n.i18n import t
from modules.reports.wellness_metrics import (
    build_team_weekly_wellness,
    build_team_monthly_wellness,
    build_wellness_by_tipo_carga,
)
from modules.reports.wellness_metrics import (compute_player_wellness_kpis, build_player_daily_wellness, compute_player_wellness_cards)
from.plots_grupales import (plot_carga_diaria_detalle_base, plot_carga_semanal_base, 
    plot_acwr, plot_monotonia_strain, plot_wellness_evolucion_grupal,plot_wellness_resumen_periodico, plot_wellness_por_tipo_carga)
from .plots_individuales import (
    grafico_wellness_pre_lesion,
    grafico_rpe_ua,
    grafico_duracion_rpe,
    plot_carga_fatiga_recuperacion,
    tabla_wellness_individual,
    plot_wellness_evolucion_individual
)

def player_block_dux(jugadora_seleccionada: dict, unavailable="N/A"):
    """Muestra el bloque visual con la información principal de la jugadora."""

    # Validar jugadora seleccionada
    if not jugadora_seleccionada or not isinstance(jugadora_seleccionada, dict):
        st.info(t("Selecciona una jugadora para continuar."))
        st.stop()
    
    #st.dataframe(jugadora_seleccionada)
    # Extraer información básica
    nombre_completo = jugadora_seleccionada.get("nombre_jugadora", unavailable).strip().upper()
    #apellido = jugadora_seleccionada.get("apellido", "").strip().upper()
    #nombre_completo = f"{nombre.capitalize()}"
    id_jugadora = jugadora_seleccionada.get("id_jugadora", unavailable)
    posicion = jugadora_seleccionada.get("posicion", unavailable)
    pais = jugadora_seleccionada.get("nacionalidad", unavailable)
    fecha_nac = jugadora_seleccionada.get("fecha_nacimiento", unavailable)
    genero = jugadora_seleccionada.get("genero", "")
    competicion = jugadora_seleccionada.get("plantel", "")
    dorsal = jugadora_seleccionada.get("dorsal", "")
    url_drive = jugadora_seleccionada.get("foto_url", "")

    dorsal_number = f":red[/ Dorsal #{int(dorsal)}]" if pd.notna(dorsal) else ""

    # Calcular edad
    edad_texto, fnac = calcular_edad(fecha_nac)

    # Color temático
    #color = "violet" if genero.upper() == "F" else "blue"

    # Icono de género
    if genero.upper() == "F":
        genero_icono = ":material/girl:"
        profile_image = "female"
    elif genero.upper() == "H":
        genero_icono = ":material/boy:"
        profile_image = "male"
    else:
        genero_icono = ""
        profile_image = "profile"

    # Bloque visual
    st.markdown(f"### {nombre_completo.title()} {dorsal_number}")
    #st.markdown(f"##### **_:red[Identificación:]_** _{id_jugadora}_ | **_:red[País:]_** _{pais.upper()}_")

    col1, col2, col3 = st.columns([1.6, 2, 2])

    with col1:
        if pd.notna(url_drive) and url_drive and url_drive != "No Disponible":
            direct_url = clean_image_url(url_drive)
            #st.text(direct_url)
            response = get_photo(direct_url)
            if response and response.status_code == 200 and 'image' in response.headers.get("Content-Type", ""):
                st.image(response.content, width=300)
            else:
                st.image(f"assets/images/{profile_image}.png", width=300)
        else:
            st.image(f"assets/images/{profile_image}.png", width=300)

    with col2:
        #st.markdown(f"**:material/sports_soccer: Competición:** {competicion}")
        #st.markdown(f"**:material/cake: Fecha Nac.:** {fecha_nac}")

        st.metric(label=t(":red[:material/id_card: Identificación]"), value=f"{id_jugadora}", border=True)
        st.metric(label=t(":red[:material/sports_soccer: Plantel]"), value=f"{competicion}", border=True)
        st.metric(label=t(":red[:material/cake: F. Nacimiento]"), value=f"{fecha_nac}", border=True)
                    
    with col3:
        #st.markdown(f"**:material/person: Posición:** {posicion.capitalize()}")
        #st.markdown(f"**:material/favorite: Edad:** {edad if edad != unavailable else 'N/A'} años")

        st.metric(label=t(":red[:material/globe: País]"), value=f"{pais if pais else 'N/A'}", border=True)
        st.metric(label=t(":red[:material/person: Posición]"), value=f"{posicion.capitalize() if posicion else 'N/A'}", border=True)
        st.metric(label=t(":red[:material/favorite: Edad]"), value=f"{edad_texto}", border=True)
          
    #st.divider()

def metricas(df: pd.DataFrame, jug_sel, turno_sel, start, end) -> None:
    """Página de análisis individual de cargas y RPE por jugadora."""

    # --- Calcular métricas generales ---
    flt = RPEFilters(jugadores=jug_sel or None, turnos=turno_sel or None, start=start, end=end)
    metrics = compute_rpe_metrics(df, flt)

    #st.dataframe(metrics)
    # --- Validar datos ---
    if df is None or df.empty:
        st.info(t("No hay registros disponibles para análisis individual."))
        return

    # --- Resumen general ---
    st.divider()
    st.markdown(t("### **Resumen de carga individual**"))

    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:
        st.metric(
            t("Minutos último día"),
            value=(f"{metrics['minutos_sesion']:.0f}" if pd.notna(metrics["minutos_sesion"]) else "-")
        )
        st.metric(
            t("Carga mes"),
            help=t("Carga acumulada del periodo mensual"),
            value=(f"{metrics['carga_mes']:.0f}" if metrics["carga_mes"] is not None else "-")
        )

    with k2:
        st.metric(
            t("UA último día"),
            help=t("Carga interna del último día registrado"),
            value=(f"{metrics['ua_total_dia']:.0f}" if metrics["ua_total_dia"] is not None else "-")
        )
        st.metric(
            t("Carga del periodo"),
            help=t("Carga acumulada en el periodo seleccionado"),
            value=(f"{metrics['carga_total_periodo']:.0f}" if metrics["carga_total_periodo"] is not None else "-")
        )

    with k3:
        st.metric(
            t("Fatiga aguda (7d)"),
            help=t("Carga media diaria de los últimos 7 días"),
            value=(f"{metrics['fatiga_aguda_7d_media']:.1f}" if metrics["fatiga_aguda_7d_media"] is not None else "-")
        )
        st.metric(
            t("Fatiga crónica (42d)"),
            help=t("Carga media diaria de referencia a 42 días"),
            value=(f"{metrics['fatiga_cronica_42d']:.1f}" if metrics["fatiga_cronica_42d"] is not None else "-")
        )

    with k4:
        st.metric(
            t("Monotonía 7d"),
            help=t("Detecta si la distribución de carga reciente ha sido demasiado uniforme"),
            value=(f"{metrics['monotonia_semana']:.2f}" if metrics["monotonia_semana"] is not None else "-")
        )
        st.metric(
            t("Variabilidad 7d"),
            help=t("Desviación diaria de carga en los últimos 7 días"),
            value=(f"{metrics['variabilidad_semana']:.2f}" if metrics["variabilidad_semana"] is not None else "-")
        )

    with k5:
        st.metric(
            t("ACWR (42d)"),
            help=t("Relación entre carga aguda 7d y carga crónica 42d"),
            value=(f"{metrics['acwr_42d']:.2f}" if metrics["acwr_42d"] is not None else "-")
        )
        st.metric(
            t("Estado de forma (42d)"),
            help=t("Balance entre fatiga crónica y carga aguda reciente"),
            value=(f"{metrics['estado_forma_42d']:.2f}" if metrics["estado_forma_42d"] is not None else "-")
        )

    # with st.expander(t("Fatiga, Adaptación, Recuperacion y ACWR (42d/56d)"), expanded=False):
    #     col1, col2, col3, col4 = st.columns(4)

    #     with col1:
    #         st.metric(t("Fatiga crónica (42d)"), help=t("Nivel de adaptación (Media) 42dias"), value=(f"{metrics['fatiga_cronica_42d']:.1f}" if metrics["fatiga_cronica_42d"] is not None else "-"))
    #         st.metric(t("Fatiga crónica (56d)"), help=t("Nivel de adaptación (Media) 56 dias"), value=(f"{metrics['fatiga_cronica_56d']:.1f}" if metrics["fatiga_cronica_56d"] is not None else "-"))

    #     with col2:
    #         st.metric(t("Adaptación (42d)"), help=t("Balance entre fatiga aguda y crónica"), value=(f"{metrics['adaptacion_42d']:.2f}" if metrics["adaptacion_42d"] is not None else "-"))
    #         st.metric(t("Adaptación (56d)"), help=t("Balance entre fatiga aguda y crónica"), value=(f"{metrics['adaptacion_56d']:.2f}" if metrics["adaptacion_56d"] is not None else "-"))

    #     with col3:
    #         st.metric(t("ACWR (42d)"), help=t("Relación entre fatiga aguda y crónica"), value=(f"{metrics['acwr_42d']:.2f}" if metrics["acwr_42d"] is not None else "-"))
    #         st.metric(t("ACWR (56d)"), help=t("Relación entre fatiga aguda y crónica"), value=(f"{metrics['acwr_56d']:.2f}" if metrics["acwr_56d"] is not None else "-"))

    #     with col4:
    #         st.metric(t("Recuperación (42d)"), help=t("Recuperación 42d"), value=(f"{metrics['recuperacion_42d']:.2f}" if metrics["recuperacion_42d"] is not None else "-"))
    #         st.metric(t("Recuperación (56d)"), help=t("Recuperación 56d"), value=(f"{metrics['recuperacion_56d']:.2f}" if metrics["recuperacion_56d"] is not None else "-"))

    
    resumen = _get_resumen_tecnico_carga(metrics)
    st.markdown(resumen, unsafe_allow_html=True)
    render_player_alerts_table(metrics)

    #st.dataframe(df)
    #tabla_wellness_individual(df)

def _get_resumen_tecnico_carga(metrics: dict) -> str:
    """
    Resumen técnico individual simplificado y alineado con métricas visibles.
    """

    def color_text(text, color):
        return f"<b style='color:{color}'>{text}</b>"

    minutos = metrics.get("minutos_sesion", 0) or 0
    ua_dia = metrics.get("ua_total_dia", 0) or 0
    carga_7d = metrics.get("carga_semana", 0) or 0
    carga_mes = metrics.get("carga_mes", 0) or 0

    fatiga_aguda = metrics.get("fatiga_aguda_7d_media")
    fatiga_cronica = metrics.get("fatiga_cronica_42d")
    estado_forma = metrics.get("estado_forma_42d")
    acwr = metrics.get("acwr_42d")
    monotonia = metrics.get("monotonia_semana")

    # 🔴 Estado de carga reciente
    if carga_7d > 2500:
        carga_txt = color_text("alta", "#E53935")
    elif carga_7d >= 1500:
        carga_txt = color_text("moderada", "#FB8C00")
    else:
        carga_txt = color_text("baja", "#43A047")

    # 🔴 Estado de forma
    if estado_forma is None:
        forma_txt = color_text("no disponible", "#757575")
    elif estado_forma < 0:
        forma_txt = color_text("negativo", "#E53935")
    elif estado_forma == 0:
        forma_txt = color_text("neutro", "#FB8C00")
    else:
        forma_txt = color_text("positivo", "#43A047")

    # 🔴 ACWR
    if acwr is None:
        acwr_txt = color_text("sin datos", "#757575")
    elif acwr > 1.5:
        acwr_txt = color_text("alto riesgo", "#E53935")
    elif acwr < 0.8:
        acwr_txt = color_text("subcarga", "#FB8C00")
    else:
        acwr_txt = color_text("controlado", "#43A047")

    # 🔴 Fatiga aguda vs crónica
    if fatiga_aguda is None or fatiga_cronica is None:
        fatiga_txt = color_text("sin referencia suficiente", "#757575")
    elif fatiga_aguda > fatiga_cronica:
        fatiga_txt = color_text("por encima de la referencia", "#E53935")
    else:
        fatiga_txt = color_text("controlada", "#43A047")

    # 🔴 Monotonía
    if monotonia is None:
        mono_txt = color_text("sin datos", "#757575")
    elif monotonia > 2.0:
        mono_txt = color_text("alta", "#E53935")
    elif monotonia >= 1.5:
        mono_txt = color_text("moderada", "#FB8C00")
    else:
        mono_txt = color_text("adecuada", "#43A047")

    resumen = (
        f"{t(':material/description: **Resumen técnico:**')} "
        f"<div style='text-align: justify;'>"

        f"{t('En el último día se registraron')} "
        f"{color_text(f'{minutos:.0f} min', '#43A047')} "
        f"{t('con una carga de')} "
        f"{color_text(f'{ua_dia:.0f} UA', '#43A047')}. "

        f"{t('La carga acumulada de los últimos 7 días es')} "
        f"{carga_txt} "
        f"({color_text(f'{carga_7d:.0f} UA', '#607D8B')}), "
        f"{t('mientras que la carga mensual asciende a')} "
        f"{color_text(f'{carga_mes:.0f} UA', '#607D8B')}. "

        f"{t('La carga reciente se encuentra')} "
        f"{fatiga_txt} "
        f"{t('respecto a la referencia crónica')} "
        f"({color_text(f'{fatiga_aguda:.1f} vs {fatiga_cronica:.1f} UA/día', '#607D8B') if fatiga_aguda and fatiga_cronica else color_text('-', '#607D8B')}). "

        f"{t('El estado de forma actual es')} "
        f"{forma_txt} "
        f"({color_text(f'{estado_forma:.2f}', '#607D8B') if estado_forma is not None else color_text('-', '#607D8B')}), "

        f"{t('y el ACWR se sitúa en un nivel')} "
        f"{acwr_txt} "
        f"({color_text(f'{acwr:.2f}', '#607D8B') if acwr is not None else color_text('-', '#607D8B')}). "

        f"{t('La distribución de carga reciente presenta una monotonía')} "
        f"{mono_txt}."
        
        f"</div>"
    )

    return resumen

def calcular_semaforo_riesgo(df: pd.DataFrame) -> tuple[str, str, float, float]:
    """
    Calcula un semáforo de riesgo a partir de las métricas de carga:
    - ACWR 42d
    - Estado de forma 42d

    Retorna:
        icono (str)
        descripcion (str)
        acwr (float)
        estado_forma (float)
    """

    if df is None or df.empty:
        return "⚪️", t("Sin datos suficientes para evaluar riesgo."), np.nan, np.nan

    end_day = pd.to_datetime(df["fecha_sesion"], errors="coerce").dt.date.max()

    flt = RPEFilters(
        jugadores=None,
        turnos=None,
        start=None,
        end=end_day
    )

    metrics = compute_rpe_metrics(df, flt)

    acwr = metrics.get("acwr_42d")
    estado_forma = metrics.get("estado_forma_42d")

    if acwr is None and estado_forma is None:
        return "⚪️", t("Sin datos suficientes para evaluar riesgo."), np.nan, np.nan

    # Riesgo alto
    if (acwr is not None and acwr > 1.5) or (estado_forma is not None and estado_forma < 0):
        return (
            "🔴",
            t("Riesgo alto: la carga aguda supera la capacidad crónica o el estado de forma es negativo."),
            acwr if acwr is not None else np.nan,
            estado_forma if estado_forma is not None else np.nan,
        )

    # Riesgo moderado
    if (
        (acwr is not None and (1.3 <= acwr <= 1.5 or acwr < 0.8))
        or (estado_forma is not None and estado_forma == 0)
    ):
        return (
            "🟠",
            t("Riesgo moderado: conviene vigilar la progresión de carga y la respuesta individual."),
            acwr if acwr is not None else np.nan,
            estado_forma if estado_forma is not None else np.nan,
        )

    # Riesgo bajo
    return (
        "🟢",
        t("Riesgo bajo: relación adecuada entre carga aguda y crónica y estado de forma positivo."),
        acwr if acwr is not None else np.nan,
        estado_forma if estado_forma is not None else np.nan,
    )

def build_player_alerts_table(metrics: dict) -> pd.DataFrame:
    """
    Construye una tabla de alertas e interpretación individual
    a partir de las métricas de carga.
    """

    rows = []

    acwr = metrics.get("acwr_42d")
    estado_forma = metrics.get("estado_forma_42d")
    monotonia = metrics.get("monotonia_semana")
    variabilidad = metrics.get("variabilidad_semana")
    fatiga_aguda = metrics.get("fatiga_aguda_7d_media")
    fatiga_cronica = metrics.get("fatiga_cronica_42d")

    # ACWR
    if acwr is None:
        nivel = "⚪ Sin datos"
        interpretacion = "No hay histórico suficiente para calcular el ratio."
    elif acwr > 1.5:
        nivel = "🔴 Alto"
        interpretacion = "La carga aguda supera claramente la capacidad crónica."
    elif acwr < 0.8:
        nivel = "🟡 Bajo"
        interpretacion = "La carga reciente está por debajo del nivel habitual."
    else:
        nivel = "🟢 Controlado"
        interpretacion = "Relación adecuada entre carga reciente y carga de referencia."

    rows.append({
        "Indicador": "ACWR 42d",
        "Valor actual": f"{acwr:.2f}" if acwr is not None else "-",
        "Rango objetivo": "0.80 - 1.30",
        "Nivel": nivel,
        "Interpretación": interpretacion,
    })

    # Estado de forma
    if estado_forma is None:
        nivel = "⚪ Sin datos"
        interpretacion = "No hay datos suficientes para estimar el estado de forma."
    elif estado_forma < 0:
        nivel = "🔴 Negativo"
        interpretacion = "La fatiga aguda supera la capacidad crónica."
    elif estado_forma == 0:
        nivel = "🟡 Neutro"
        interpretacion = "La carga reciente está en equilibrio con la referencia crónica."
    else:
        nivel = "🟢 Positivo"
        interpretacion = "La capacidad crónica supera la carga aguda reciente."

    rows.append({
        "Indicador": "Estado de forma 42d",
        "Valor actual": f"{estado_forma:.2f}" if estado_forma is not None else "-",
        "Rango objetivo": "> 0",
        "Nivel": nivel,
        "Interpretación": interpretacion,
    })

    # Monotonía
    if monotonia is None:
        nivel = "⚪ Sin datos"
        interpretacion = "No hay suficientes días para valorar la variabilidad de carga."
    elif monotonia > 2.0:
        nivel = "🔴 Alta"
        interpretacion = "Distribución de carga muy uniforme; posible acumulación de fatiga."
    elif monotonia >= 1.5:
        nivel = "🟡 Moderada"
        interpretacion = "Conviene vigilar la repetición del estímulo."
    else:
        nivel = "🟢 Buena"
        interpretacion = "La carga presenta una variabilidad adecuada."

    rows.append({
        "Indicador": "Monotonía 7d",
        "Valor actual": f"{monotonia:.2f}" if monotonia is not None else "-",
        "Rango objetivo": "< 1.50",
        "Nivel": nivel,
        "Interpretación": interpretacion,
    })

    # Variabilidad
    if variabilidad is None:
        nivel = "⚪ Sin datos"
        interpretacion = "No hay datos suficientes para valorar dispersión diaria."
    elif variabilidad == 0:
        nivel = "🟡 Nula"
        interpretacion = "No ha habido variación de carga en la ventana observada."
    else:
        nivel = "🟢 Disponible"
        interpretacion = "Muestra cuánto cambia la carga diaria en los últimos 7 días."

    rows.append({
        "Indicador": "Variabilidad 7d",
        "Valor actual": f"{variabilidad:.2f}" if variabilidad is not None else "-",
        "Rango objetivo": "> 0",
        "Nivel": nivel,
        "Interpretación": interpretacion,
    })

    # Fatiga aguda media vs crónica
    if fatiga_aguda is None or fatiga_cronica is None:
        nivel = "⚪ Sin datos"
        interpretacion = "No se puede comparar la carga aguda con la referencia crónica."
    elif fatiga_aguda > fatiga_cronica:
        nivel = "🔴 Superior"
        interpretacion = "La carga reciente está por encima del nivel de referencia."
    elif fatiga_aguda == fatiga_cronica:
        nivel = "🟡 Igualada"
        interpretacion = "La carga reciente está alineada con la referencia crónica."
    else:
        nivel = "🟢 Controlada"
        interpretacion = "La carga reciente se mantiene por debajo de la referencia crónica."

    rows.append({
        "Indicador": "Fatiga aguda media vs crónica",
        "Valor actual": (
            f"{fatiga_aguda:.1f} / {fatiga_cronica:.1f}"
            if fatiga_aguda is not None and fatiga_cronica is not None else "-"
        ),
        "Rango objetivo": "Aguda ≤ Crónica",
        "Nivel": nivel,
        "Interpretación": interpretacion,
    })

    return pd.DataFrame(rows)

def render_player_alerts_table(metrics: dict) -> None:
    """
    Muestra la tabla de alertas e interpretación individual.
    """

    alertas_df = build_player_alerts_table(metrics)

    if alertas_df.empty:
        st.info(t("No hay alertas disponibles."))
        return

    st.markdown(t("### **Alertas e interpretación**"))
    st.dataframe(alertas_df, hide_index=True, use_container_width=True)

def graficos_individuales(
    df_visual: pd.DataFrame,
    df_calculo: pd.DataFrame,
    start=None,
    end=None
):
    """Gráficos individuales para análisis de carga, bienestar y riesgo."""

    if df_visual is None or df_visual.empty:
        st.info("No hay datos disponibles para graficar.")
        return

    df_player_visual = df_visual.copy().sort_values("fecha_sesion")
    df_player_calculo = df_calculo.copy().sort_values("fecha_sesion")

    # =====================================================
    # Serie temporal de carga calculada con histórico ampliado
    # =====================================================
    df_states = compute_rpe_timeseries(df_player_calculo)

    # Recorte visual al rango seleccionado
    if start is not None and end is not None and not df_states.empty:
        df_states_plot = df_states[
            (pd.to_datetime(df_states["fecha_sesion"]).dt.date >= start) &
            (pd.to_datetime(df_states["fecha_sesion"]).dt.date <= end)
        ].copy()
    else:
        df_states_plot = df_states.copy()

    # =====================================================
    # Lesiones previas
    # =====================================================
    id_jugadora = (
        df_player_visual["id_jugadora"].iloc[0]
        if "id_jugadora" in df_player_visual.columns and not df_player_visual.empty
        else None
    )

    pre_lesion = get_wellness_pre_lesion(
        id_jugadora=id_jugadora,
        dias_previos=14,
        as_df=True
    ) if id_jugadora else pd.DataFrame()

    fecha_lesion = None

    if pre_lesion is not None and not pre_lesion.empty:
        fecha_lesion = pd.to_datetime(
            pre_lesion["fecha_lesion"],
            errors="coerce"
        ).max()

    # =====================================================
    # Tabs principales
    # =====================================================
    st.markdown(t("### **Gráficos**"))

    tabs = st.tabs([
        t("Wellness"),
        t("Estado de Carga"),
        t("Carga y esfuerzo"),
        t("ACWR"),
        t(" Montonía y strain"),
        t("RPE y UA"),
        t("Duración vs RPE"),
        t("Wellness + Lesiones")
    ])

    # =====================================================
    # TAB 0 - WELLNESS
    # =====================================================
    with tabs[0]:
        # -------------------------
        # Tarjetas resumen
        # -------------------------
        cards = compute_player_wellness_cards(
            df_player_visual,
            periodo="Mes"
        )

        render_player_wellness_summary_cards(cards)

        st.divider()

        # -------------------------
        # KPIs individuales
        # -------------------------
        wellness_individual_kpis(df_player_visual)

        st.divider()

        # -------------------------
        # DataFrames agregados para gráficos
        # -------------------------
        df_daily = build_player_daily_wellness(df_player_visual)
        df_weekly = build_team_weekly_wellness(df_player_visual)
        df_monthly = build_team_monthly_wellness(df_player_visual)
        df_tipo = build_wellness_by_tipo_carga(df_player_visual)

        tabs_wellness = st.tabs([
            t("Evolución diaria"),
            t("Resumen semanal"),
            t("Resumen mensual"),
            t("Por tipo de carga"),
        ])

        with tabs_wellness[0]:
            plot_wellness_evolucion_grupal(
                df_daily,
                scope="individual"
            )

        with tabs_wellness[1]:
            plot_wellness_resumen_periodico(
                df_weekly,
                periodo_col="semana",
                titulo="Resumen semanal de wellness individual",
                etiqueta_periodo="semana",
                scope="individual"
            )

        with tabs_wellness[2]:
            plot_wellness_resumen_periodico(
                df_monthly,
                periodo_col="mes",
                titulo="Resumen mensual de wellness individual",
                etiqueta_periodo="mes",
                scope="individual"
            )

        with tabs_wellness[3]:
            plot_wellness_por_tipo_carga(
                df_tipo,
                scope="individual"
            )
        
        st.divider()

        # -------------------------
        # Tabla detalle wellness
        # -------------------------
        tabla_wellness_individual(df_player_visual)

    # =====================================================
    # TAB 1 - ESTADO DE CARGA
    # =====================================================
    with tabs[1]:
        # EMA como vista principal
        plot_carga_fatiga_recuperacion(
            df_states_plot,
            metodo="ema"
        )

        # SMA como apoyo técnico
        with st.expander(
            t("Ver versión técnica con media móvil simple (SMA)"),
            expanded=False
        ):
            plot_carga_fatiga_recuperacion(
                df_states_plot,
                metodo="sma"
            )

    # =====================================================
    # TAB 2 - CARGA Y ESFUERZO
    # =====================================================
    with tabs[2]:
        weekly = plot_carga_semanal_base(df_player_visual)

        if start is not None and end is not None:
            n_dias = (end - start).days + 1

            if n_dias <= 7:
                st.divider()

                plot_carga_diaria_detalle_base(
                    df_player_visual,
                    start=start,
                    end=end,
                )

            elif weekly is not None and not weekly.empty:
                semana_sel = st.selectbox(
                    t("Selecciona semana para ver detalle"),
                    options=weekly["rango_semana"].tolist(),
                    index=len(weekly) - 1,
                    key="semana_detalle_individual",
                )

                row = weekly[weekly["rango_semana"] == semana_sel].iloc[0]

                start_week = pd.to_datetime(row["inicio_semana"]).date()
                end_week = pd.to_datetime(row["fin_semana"]).date()

                st.divider()

                plot_carga_diaria_detalle_base(
                    df_player_visual,
                    start=start_week,
                    end=end_week,
                )

    # =====================================================
    # TAB 3 - ACWR
    # =====================================================
    with tabs[3]:
        plot_acwr(
            df_states_plot,
            ventana_cronica=42,
            metodo="sma",
            scope="individual"
        )

    # =====================================================
    # TAB 4 - MONOTONÍA Y STRAIN
    # =====================================================
    with tabs[4]:
        plot_monotonia_strain(
            df_player_visual,
            scope="individual"
        )

    # =====================================================
    # TAB 5 - RPE Y UA
    # =====================================================
    with tabs[5]:
        grafico_rpe_ua(df_player_visual)

    # =====================================================
    # TAB 6 - DURACIÓN VS RPE
    # =====================================================
    with tabs[6]:
        grafico_duracion_rpe(df_player_visual)

    # =====================================================
    # TAB 7 - WELLNESS + LESIONES
    # =====================================================
    with tabs[7]:
        if pre_lesion is not None and not pre_lesion.empty:
            grafico_wellness_pre_lesion(pre_lesion)

            st.divider()

            plot_carga_fatiga_recuperacion(
                df_states,
                metodo="ema",
                fecha_lesion=fecha_lesion,
                window_days=14
            )

            st.divider()

            plot_acwr(
                df_states,
                ventana_cronica=42,
                metodo="ema",
                scope="individual",
                fecha_lesion=fecha_lesion,
                window_days=14
            )

        else:
            st.info("No hay registros de lesiones.")


def selector_ventana_cronica():
    # -------------------------
    # Selector de ventana
    # -------------------------
    with st.columns([1, 3])[0]:
        ventana_cronica = st.selectbox(
            t("Ventana de referencia (días)"),
            options=[28, 42, 56],
            index=1,  # 42d por defecto
            help=t(
                "Selecciona la ventana temporal usada para calcular la fatiga crónica, "
                "recuperación y ACWR."
            ),
            key="ventana_cronica_selector",
        )
    return ventana_cronica


### PIAY
def wellness_individual_kpis(df_player: pd.DataFrame):
    """
    KPIs de wellness para una jugadora ya filtrada.
    """

    if df_player is None or df_player.empty:
        st.info(t("No hay datos de wellness para esta jugadora."))
        return

    kpis = compute_player_wellness_kpis(df_player)

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
            t("% dolor > 3"),
            f"{kpis['pct_dolor>3']:.1f}%" if kpis["pct_dolor>3"] is not None else "-"
        )


def render_player_wellness_summary_cards(summary: dict):
    """
    Renderiza tarjetas-resumen de wellness individual.
    """

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            t("Bienestar promedio"),
            f"{summary['wellness_score_25']}/25" if summary["wellness_score_25"] is not None else "-"
        )

    with c2:
        st.metric(
            t("Esfuerzo percibido prom."),
            f"{summary['rpe_prom']}" if summary["rpe_prom"] is not None else "-"
        )

    with c3:
        st.metric(
            t("Carga interna total (UA)"),
            f"{summary['ua_total']}" if summary["ua_total"] is not None else "-"
        )

    with c4:
        st.metric(
            t("Riesgo actual"),
            summary["riesgo_label"]
        )


def mostrar_resumen_tecnico_wellness_individual(summary: dict):
    """
    Muestra un resumen técnico de wellness individual.
    """

    wellness_score = summary.get("wellness_score_25")
    rpe_prom = summary.get("rpe_prom")
    ua_total = summary.get("ua_total")
    riesgo_label = summary.get("riesgo_label", "Sin datos")
    dolor_mean = summary.get("dolor_mean")
    stress_mean = summary.get("stress_mean")
    energia_mean = summary.get("energia_mean")

    if wellness_score is None:
        st.info(t("No hay datos suficientes para generar el resumen técnico de wellness."))
        return

    estado_bienestar = (
        t("óptimo") if wellness_score > 20 else
        t("moderado") if wellness_score >= 15 else
        t("comprometido")
    )

    if rpe_prom is None or rpe_prom == 0:
        nivel_rpe = t("sin datos")
    elif rpe_prom < 5:
        nivel_rpe = t("bajo")
    elif rpe_prom <= 7:
        nivel_rpe = t("moderado")
    else:
        nivel_rpe = t("alto")

    st.markdown(
        f":material/description: **{t('Resumen técnico')}:** "
        f"{t('La jugadora muestra un estado de bienestar')} **{estado_bienestar}** "
        f"({wellness_score}/25), "
        f"{t('con un esfuerzo percibido')} **{nivel_rpe}** "
        f"(RPE {rpe_prom if rpe_prom is not None else '-'}). "
        f"{t('La carga interna acumulada es de')} **{ua_total if ua_total is not None else '-'} UA** "
        f"{t('y el riesgo actual se clasifica como')} **{riesgo_label}**. "
        f"{t('Los valores medios observados son')} "
        f"{t('energía')}={energia_mean if energia_mean is not None else '-'}, "
        f"{t('stress')}={stress_mean if stress_mean is not None else '-'} "
        f"{t('y dolor')}={dolor_mean if dolor_mean is not None else '-'}."
    )    

def render_player_wellness_summary_cards(cards: dict):
    """
    Renderiza tarjetas-resumen de wellness individual con delta y mini-chart.
    """

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            t("Bienestar promedio"),
            f"{cards['wellness_val']}/25",
            f"{cards['wellness_delta']:+.1f}%",
            chart_data=cards["wellness_chart"],
            chart_type="area",
            border=True,
            help=t("Promedio de bienestar global de la jugadora (escala 25).")
        )

    with c2:
        st.metric(
            t("Esfuerzo percibido prom."),
            f"{cards['rpe_val']}",
            f"{cards['rpe_delta']:+.1f}%",
            chart_data=cards["rpe_chart"],
            chart_type="line",
            border=True,
            delta_color="inverse",
        )

    with c3:
        st.metric(
            t("Carga interna total (UA)"),
            f"{cards['ua_val']}",
            f"{cards['ua_delta']:+.1f}%",
            chart_data=cards["ua_chart"],
            chart_type="area",
            border=True,
        )

    with c4:
        st.metric(
            t("Riesgo actual"),
            cards["riesgo_val"],
            f"{cards['riesgo_delta']:+.1f}%",
            chart_data=cards["riesgo_chart"],
            chart_type="bar",
            border=True,
            delta_color="inverse",
            help=t("Clasificación actual del riesgo a partir de índice de bienestar y del dolor medio de los últimos 4 días.")
        )