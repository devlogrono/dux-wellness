
import streamlit as st
import modules.app_config.config as config

from modules.i18n.i18n import t
from modules.ui.ui_components import selection_header
from modules.reports.ui_individual import metricas, graficos_individuales, calcular_semaforo_riesgo, player_block_dux
from modules.reports.ui_grupal import build_calculation_window
from modules.db.db_records import get_records_db
from modules.db.db_players import load_players_db
from modules.db.db_competitions import load_competitions_db

config.init_config()
st.header(t("Análisis :red[individual]"), divider="red")

# Load reference data
jug_df = load_players_db()
comp_df = load_competitions_db()
df = get_records_db()

df_visual, jugadora, tipo, turno, start, end = selection_header(jug_df, comp_df, df, modo="reporte")

if not jugadora:
    st.info(t("Selecciona una jugadora para continuar."))
    st.stop()

if df_visual is None or df_visual.empty:
    st.info(t("No hay registros aún (se requieren Check-out con UA calculado)."))
    st.stop()

# Dataset de cálculo con histórico ampliado
df_jugadora_full = df[df["id_jugadora"] == jugadora["id_jugadora"]].copy()

df_calculo = build_calculation_window(
    df_jugadora_full,
    start=start,
    end=end,
    lookback_days=56,
)

player_block_dux(jugadora)

metricas(df_calculo, jugadora, turno, start, end)

icon, desc, acwr, estado_forma = calcular_semaforo_riesgo(df_calculo)


graficos_individuales(df_visual, df_calculo, start, end)

